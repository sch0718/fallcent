# 로깅 설정
import logging
from typing import Any, Dict, List
import requests
import re
import json
import random
from bs4 import BeautifulSoup
import time
import sys
import os
import pathlib
import urllib.parse

# 현재 디렉토리의 상위 디렉토리(app)를 가져오기
current_dir = pathlib.Path(__file__).parent.parent
# 프로젝트 루트 디렉토리 추가 (app의 상위 디렉토리)
project_root = current_dir.parent
sys.path.append(str(project_root))

# 이제 utils.py를 임포트
from app.utils import load_config, get_random_user_agent, sleep_with_jitter, save_results, find_project_root

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def instagram_reels() -> List[Dict[str, Any]]:
    """인스타그램 릴스 조회수 추출 메인 함수"""
    
    try:
        # 설정 로드
        config = load_config("instagram.yaml")
        
        # 설정에서 값 추출
        reels_urls = config.get("reels_urls", [])
        user_agents = config.get("user_agents", [])
        cookie_settings = config.get("cookie_settings", {})
        parsing_settings = config.get("parsing_settings", {})
        request_delay_settings = config.get("request_delay", {"min": 1, "max": 3})
        login_settings = config.get("login_settings", {"enabled": False})
        request_settings = config.get("request_settings", {"timeout": 30, "max_retries": 3})
        
        # 필수 값 검증
        if not reels_urls:
            logger.error("URL 목록이 비어 있습니다. configs/instagram.yaml 파일을 확인하세요.")
            return None
        
        # 사용자 에이전트가 없는 경우 기본값 사용
        if not user_agents:
            user_agents = [get_random_user_agent()]
        
        # 지연시간 설정
        min_delay = request_delay_settings.get("min", 1)
        max_delay = request_delay_settings.get("max", 3)
        
        # 시간 초과 및 재시도 설정
        timeout = request_settings.get("timeout", 30)
        max_retries = request_settings.get("max_retries", 3)
        retry_delay = request_settings.get("retry_delay", {"min": 2, "max": 5})
        referrers = request_settings.get("referrers", ["https://www.instagram.com/"])
        
        # 파싱 설정
        additional_patterns = parsing_settings.get("additional_patterns", [])
        
        # 세션 생성
        session = requests.Session()
        
        # 세션 설정 (재시도 횟수)
        retry_adapter = requests.adapters.HTTPAdapter(max_retries=max_retries)
        session.mount('https://', retry_adapter)
        session.mount('http://', retry_adapter)
        
        # 쿠키 스토어 (초기화)
        cookies_store = {}
        
        # 쿠키 파일 설정
        cookies_file = None
        if cookie_settings.get("save_cookies", False):
            cookies_file = cookie_settings.get("cookies_file", "instagram_cookies.json")
            cookies_file = os.path.join(find_project_root(), cookies_file)
            # 기존 쿠키 로드
            if os.path.exists(cookies_file):
                try:
                    with open(cookies_file, 'r') as f:
                        saved_cookies = json.load(f)
                        cookies_store.update(saved_cookies)
                        logger.info(f"저장된 쿠키 로드: {len(saved_cookies)} 개")
                        for cookie_name, cookie_value in saved_cookies.items():
                            session.cookies.set(cookie_name, cookie_value)
                except Exception as e:
                    logger.error(f"쿠키 파일 로드 중 오류: {e}")
                
        # 세션 초기화
        init_session(session, user_agents, cookie_settings, min_delay, max_delay)
        
        # 로그인 시도 (설정된 경우)
        if login_settings.get("enabled", False):
            login_success = login_instagram(session, login_settings, user_agents, referrers, timeout, retry_delay)
            if not login_success and login_settings.get("login_required", True):
                logger.error("인스타그램 로그인 실패. 작업을 중단합니다.")
                return None
        
        # 릴스 URL 패턴
        reels_pattern = r'reel\/([A-Za-z0-9_-]+)'
        
        # 결과 저장 리스트
        results: List[Dict[str, Any]] = []
        
        # 조회수 추출 패턴 (확장 가능)
        view_count_patterns = [
            r'"playCount":\s*(\d+)',
            r'"viewCount":\s*(\d+)',
            r'\"play_count\":(\d+)',
            r'\"video_view_count\":(\d+)',
            r'\"viewCount\":(\d+)',
            r'playCount\":\"(\d+)\"',
            r'viewCount\":\"(\d+)\"',
            r'play_count=(\d+)',
            r'video_play_count=(\d+)',
            r'count\":(\d+),\"played\"',
            r'statistics\":{\"viewCount\":\"(\d+)\"',
            r'countOfPlay\":\s*(\d+)',
            r'videoPlays\":\s*(\d+)'
        ]
        
        # 설정 파일의 추가 패턴 적용
        if additional_patterns:
            view_count_patterns.extend(additional_patterns)
        
        # 각 URL 처리
        for url in reels_urls:
            try:
                # URL에서 shortcode 추출
                shortcode_match = re.search(reels_pattern, url)
                if not shortcode_match:
                    logger.warning(f"릴스 ID를 찾을 수 없음: {url}")
                    results.append({"url": url, "views": None, "error": "ID 추출 실패"})
                    continue
                
                shortcode = shortcode_match.group(1)
                logger.info(f"처리 중인 릴스 ID: {shortcode}")
                
                # 조회수 추출 결과
                views = None
                error = None
                
                views = try_html_method(session, url, user_agents, referrers, view_count_patterns, cookies_store, 
                                      timeout)
                
                sleep_with_jitter(min_delay, max_delay)
                
                # 결과 추가
                if views:
                    results.append({"url": url, "views": views})
                else:
                    error = "조회수를 추출할 수 없음"
                    logger.warning(f"{url}에서 조회수를 추출할 수 없음")
                    results.append({"url": url, "views": None, "error": error})
                
                # 지연 시간 추가 (지연 시간 증가)
                sleep_with_jitter(min_delay * 2, max_delay * 3)
                
            except Exception as e:
                logger.error(f"URL 처리 중 오류 발생: {url}, 오류: {e}")
                results.append({"url": url, "views": None, "error": str(e)})
                sleep_with_jitter(min_delay * 2, max_delay * 2)
        
        # 쿠키 저장 (설정된 경우)
        if cookie_settings.get("save_cookies", False) and cookies_file:
            try:
                with open(cookies_file, 'w') as f:
                    json.dump(cookies_store, f)
                logger.info(f"쿠키를 파일에 저장했습니다: {cookies_file}")
            except Exception as e:
                logger.error(f"쿠키 저장 중 오류: {e}")
        
        # 결과 출력
        logger.info("==== 인스타그램 릴스 조회수 결과 ====")
        for result in results:
            url = result["url"]
            views = result.get("views")
            error = result.get("error")
            
            if views is not None:
                logger.info(f"URL: {url}, 조회수: {views}")
            else:
                logger.info(f"URL: {url}, 오류: {error}")
        
        # 결과 저장
        result_file = save_results(results, "instagram_reels_views")
        if result_file:
            logger.info(f"결과를 파일에 저장했습니다: {result_file}")
        
        return results
    
    except Exception as e:
        logger.error(f"전체 처리 중 오류 발생: {e}")
        return None

def login_instagram(session, login_settings, user_agents, referrers, timeout, retry_delay) -> bool:
    """인스타그램에 로그인합니다."""
    try:
        username = login_settings.get("username")
        password = login_settings.get("password")
        two_factor_enabled = login_settings.get("two_factor_enabled", False)
        
        if not username or not password:
            logger.error("로그인 설정에 사용자 이름 또는 비밀번호가 없습니다.")
            return False
        
        logger.info(f"인스타그램 로그인 시도: {username}")
        
        # 랜덤 사용자 에이전트 및 레퍼러 선택
        user_agent = random.choice(user_agents)
        referer = random.choice(referrers) if referrers else "https://www.instagram.com/"
        
        # CSRF 토큰 가져오기
        csrf_token = None
        for cookie in session.cookies:
            if cookie.name == "csrftoken":
                csrf_token = cookie.value
                break
        
        if not csrf_token:
            # CSRF 토큰이 없는 경우 홈페이지 방문하여 얻기
            home_headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            home_response = session.get("https://www.instagram.com/", headers=home_headers, timeout=timeout)
            
            # CSRF 토큰 확인
            for cookie in session.cookies:
                if cookie.name == "csrftoken":
                    csrf_token = cookie.value
                    break
        
        if not csrf_token:
            logger.error("CSRF 토큰을 가져올 수 없습니다.")
            return False
        
        # 로그인 요청 헤더
        login_headers = {
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "X-CSRFToken": csrf_token,
            "X-Instagram-AJAX": "1",
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "198387",
            "X-IG-WWW-Claim": "0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.instagram.com",
            "Referer": "https://www.instagram.com/accounts/login/",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
        
        # 로그인 데이터
        login_data = {
            "username": username,
            "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}",
            "queryParams": "{}",
            "optIntoOneTap": "false",
            "stopDeletionNonce": "",
            "trustedDeviceRecords": "{}"
        }
        
        # 로그인 시도
        login_response = session.post(
            "https://www.instagram.com/api/v1/web/accounts/login/ajax/", 
            headers=login_headers, 
            data=login_data,
            timeout=timeout
        )
        
       # 응답 확인
        response_data = login_response.json()

        logger.info(f"로그인 응답: {response_data}")
        
        # 2단계 인증 필요한 경우
        if response_data.get("two_factor_required", False) and two_factor_enabled:
            logger.info("2단계 인증이 필요합니다.")
            two_factor_method = login_settings.get("two_factor_method", "sms")
            two_factor_id = response_data.get("two_factor_info", {}).get("two_factor_identifier")
            
            if not two_factor_id:
                logger.error("2단계 인증 식별자를 가져올 수 없습니다.")
                return False
            
            # 사용자에게 2단계 인증 코드 입력 요청
            security_code = input("2단계 인증 코드를 입력하세요: ")
            
            # 2단계 인증 데이터
            two_factor_data = {
                "username": username,
                "verificationCode": security_code,
                "identifier": two_factor_id,
                "queryParams": "{}"
            }
            
            # 2단계 인증 요청
            two_factor_response = session.post(
                "https://www.instagram.com/api/v1/web/accounts/two_factor_login/ajax/",
                headers=login_headers,
                data=two_factor_data,
                timeout=timeout
            )
            
            # 응답 확인
            two_factor_result = two_factor_response.json()
            if two_factor_result.get("authenticated", False):
                logger.info("2단계 인증 성공. 로그인 완료.")
                return True
            else:
                logger.error("2단계 인증 실패.")
                return False
        
        # 로그인 성공 확인
        if response_data.get("authenticated", False):
            logger.info("인스타그램 로그인 성공.")
            return True
        else:
            logger.error(f"로그인 실패: {response_data.get('error_type', '알 수 없는 오류')}")
            return False
    
    except Exception as e:
        logger.error(f"로그인 중 오류 발생: {e}")
        return False

def init_session(session, user_agents, cookie_settings, min_delay, max_delay):
    """인스타그램 세션을 초기화하고 쿠키를 설정합니다."""
    try:
        # 랜덤 사용자 에이전트 선택
        user_agent = random.choice(user_agents)
        
        init_headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "TE": "trailers"
        }
        logger.info("인스타그램 초기화 중...")
        
        # 인스타그램 홈페이지 방문
        init_response = session.get("https://www.instagram.com/", headers=init_headers, timeout=20)
        
        # 쿠키 설정 활성화된 경우 중요 쿠키 저장
        if cookie_settings.get('enabled', False):
            cookies = session.cookies.get_dict()
            logger.info(f"인스타그램 초기 쿠키 수신: {len(cookies)} 개")
            
            # 중요 쿠키 헤더 추가
            usage_headers = cookie_settings.get('usage_headers', [])
            for header in usage_headers:
                if header in cookies:
                    logger.info(f"중요 쿠키 설정: {header}")
        
        sleep_with_jitter(min_delay, max_delay)
        
        # 추가 세션 강화: 인스타그램 탐색 페이지 방문
        explore_headers = init_headers.copy()
        explore_headers["Referer"] = "https://www.instagram.com/"
        session.get("https://www.instagram.com/explore/", headers=explore_headers, timeout=20)
        
        sleep_with_jitter(min_delay, max_delay)
        
        return True
    except Exception as e:
        logger.error(f"세션 초기화 중 오류 발생: {e}")
        return False

def try_html_method(session, url, user_agents, referrers, view_count_patterns, cookies_store, 
                  timeout):
    """HTML 방식으로 조회수 추출을 시도합니다."""
    try:
        logger.info(f"HTML 방식으로 시도: {url}")
        
        # 랜덤 사용자 에이전트 및 레퍼러 선택
        user_agent = random.choice(user_agents)
        referer = random.choice(referrers) if referrers else "https://www.instagram.com/"
        
        html_headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
            "Referer": referer,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache"
            # Accept-Encoding 헤더 제거하여 자동 압축 방지
            # "Accept-Encoding": "gzip, deflate, br"
        }
        
        # 저장된 쿠키가 있으면 추가
        if cookies_store:
            for cookie_name, cookie_value in cookies_store.items():
                session.cookies.set(cookie_name, cookie_value)
        
        # URL에서 쿼리 파라미터 인코딩 처리
        try:
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            safe_query = urllib.parse.urlencode(query_params, doseq=True)
            safe_url = urllib.parse.urlunparse(
                (parsed_url.scheme, parsed_url.netloc, parsed_url.path, 
                parsed_url.params, safe_query, parsed_url.fragment)
            )
        except:
            safe_url = url
        
        # 요청 전송 (stream=True로 설정하여 즉시 디코딩하지 않음)
        html_response = session.get(safe_url, headers=html_headers, timeout=timeout, stream=True)
        
        # 응답 쿠키 저장
        for cookie_name, cookie_value in session.cookies.get_dict().items():
            cookies_store[cookie_name] = cookie_value
        
        if html_response.status_code == 200:
            # 응답 내용 확인 및 인코딩 처리
            try:
                # 응답 인코딩 확인
                encoding = html_response.encoding
                logger.debug(f"응답 인코딩: {encoding}")
                
                # Content-Type 확인
                content_type = html_response.headers.get('Content-Type', '')
                logger.debug(f"응답 Content-Type: {content_type}")
                
                # Content-Encoding 확인
                content_encoding = html_response.headers.get('Content-Encoding', '')
                logger.debug(f"응답 Content-Encoding: {content_encoding}")
                
                # 압축 응답인 경우 requests가 자동으로 처리
                
                # 바이너리로 내용 읽기
                raw_content = html_response.content
                
                # 인코딩 추측
                try:
                    # 1. headers의 Content-Type에서 charset 확인
                    charset = None
                    if 'charset=' in content_type:
                        charset = content_type.split('charset=')[-1].split(';')[0].strip()
                        logger.debug(f"Content-Type에서 감지된 charset: {charset}")
                    
                    # 2. HTML에서 meta 태그로 확인
                    if not charset:
                        meta_charset_match = re.search(b'<meta[^>]*charset=["\']?([^"\'>]+)', raw_content)
                        if meta_charset_match:
                            charset = meta_charset_match.group(1).decode('ascii', errors='ignore')
                            logger.debug(f"Meta 태그에서 감지된 charset: {charset}")
                    
                    # 3. HTML doctype 확인
                    if not charset:
                        doctype_match = re.search(b'<!DOCTYPE[^>]*>', raw_content)
                        if doctype_match and b'html' in doctype_match.group(0).lower():
                            # HTML 문서로 보임
                            charset = 'utf-8'  # 대부분의 현대 웹 페이지는 UTF-8
                            logger.debug("DOCTYPE 기반으로 HTML 감지, UTF-8 인코딩 가정")
                    
                    # 4. 기본 인코딩 사용
                    if not charset:
                        charset = encoding if encoding else 'utf-8'
                        logger.debug(f"인코딩 감지 실패, 기본값 사용: {charset}")
                    
                    # 인코딩으로 디코딩 시도
                    content = raw_content.decode(charset, errors='replace')
                    
                except Exception as enc_error:
                    logger.warning(f"인코딩 감지 오류: {enc_error}, UTF-8로 폴백")
                    content = raw_content.decode('utf-8', errors='replace')
                
                # 응답 길이 로깅
                logger.info(f"응답 길이: {len(content)} 바이트")
                
                # 응답 미리보기 로깅 (처음 150자만)
                preview = content[:150].replace('\n', ' ').strip()
                logger.info(f"응답 미리보기: {preview}...")
                
                # HTML 유효성 확인
                is_valid_html = content.strip().startswith(('<', '<!')) or '<html' in content[:1000].lower()
                if not is_valid_html:
                    logger.warning("응답이 유효한 HTML이 아닌 것으로 보입니다.")
                
                # HTML 디버깅용 파일 저장
                project_root = find_project_root()
                debug_dir = os.path.join(project_root, 'debug')
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, f"instagram_response_{int(time.time())}.html")
                
                try:
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        # 원본 내용 저장 
                        f.write(content)
                    logger.info(f"HTML 응답 저장됨: {debug_file}")
                    
                    # 이진 형식 파일도 저장 (디버깅용)
                    bin_debug_file = os.path.join(debug_dir, f"instagram_response_binary_{int(time.time())}.bin")
                    with open(bin_debug_file, 'wb') as f:
                        f.write(raw_content)
                    logger.debug(f"바이너리 응답 저장됨: {bin_debug_file}")
                except Exception as e:
                    logger.error(f"HTML 응답 저장 실패: {e}")
            
            except Exception as e:
                logger.error(f"응답 처리 중 오류: {e}")
                # 실패한 경우 바이너리 데이터를 직접 저장
                try:
                    project_root = find_project_root()
                    debug_dir = os.path.join(project_root, 'debug')
                    os.makedirs(debug_dir, exist_ok=True)
                    binary_debug_file = os.path.join(debug_dir, f"instagram_response_binary_{int(time.time())}.bin")
                    with open(binary_debug_file, 'wb') as f:
                        f.write(html_response.content)
                    logger.info(f"바이너리 응답 저장됨: {binary_debug_file}")
                    
                    # 바이너리를 ASCII로 변환하여 로깅
                    content = html_response.content.decode('ascii', errors='replace')
                except Exception as binary_err:
                    logger.error(f"바이너리 저장 실패: {binary_err}")
                    content = "응답 처리 실패"
            
            # 1. 정규식으로 조회수 추출 시도 (여러 패턴)
            for pattern in view_count_patterns:
                view_match = re.search(pattern, content)
                if view_match:
                    views = int(view_match.group(1))
                    logger.info(f"HTML에서 조회수 추출 성공 (패턴: {pattern}): {views}")
                    return views
            
            # 2. BeautifulSoup으로 JSON-LD 데이터 추출
            try:
                soup = BeautifulSoup(content, 'html.parser')
                
                # JSON-LD 스크립트 찾기
                scripts = soup.select('script[type="application/ld+json"]')
                for script in scripts:
                    try:
                        if script.string:
                            data = json.loads(script.string)
                            if "interactionStatistic" in data:
                                for stat in data["interactionStatistic"]:
                                    if stat.get("interactionType") == "http://schema.org/WatchAction":
                                        views = int(stat.get("userInteractionCount", 0))
                                        logger.info(f"LD+JSON에서 조회수 추출 성공: {views}")
                                        return views
                    except Exception as e:
                        logger.debug(f"JSON-LD 파싱 중 오류: {e}")
                
                # 3. 추가: Instagram의 고급 JSON-LD 검색
                all_scripts = soup.find_all('script')
                for script in all_scripts:
                    if script.string and ('viewCount' in script.string or 'view_count' in script.string or 'play_count' in script.string):
                        for pattern in view_count_patterns:
                            match = re.search(pattern, script.string)
                            if match:
                                views = int(match.group(1))
                                logger.info(f"스크립트에서 조회수 추출 성공: {views}")
                                return views
                
                # 4. 특정 데이터 구조 검색
                # Instagram의 additionalDataLoaded 구조 검색
                data_loaded_pattern = r'window\.__additionalDataLoaded\s*\([^,]+,\s*({.*?})\);</script>'
                data_loaded_match = re.search(data_loaded_pattern, content, re.DOTALL)
                if data_loaded_match:
                    try:
                        data_loaded = json.loads(data_loaded_match.group(1))
                        # graphql 데이터 검색
                        if 'graphql' in data_loaded and 'shortcode_media' in data_loaded['graphql']:
                            media = data_loaded['graphql']['shortcode_media']
                            if 'video_view_count' in media:
                                views = int(media['video_view_count'])
                                logger.info(f"additionalDataLoaded에서 조회수 추출 성공: {views}")
                                return views
                            elif 'play_count' in media:
                                views = int(media['play_count'])
                                logger.info(f"additionalDataLoaded에서 재생 수 추출 성공: {views}")
                                return views
                    except json.JSONDecodeError:
                        pass
                
                # 5. script 태그 내 데이터 구조 직접 검색
                for script in all_scripts:
                    if script.string:
                        # 모바일 버전의 숨겨진 JSON 데이터 검색
                        mobile_json_pattern = r'window\._sharedData\s*=\s*({.*?});</script>'
                        mobile_match = re.search(mobile_json_pattern, script.string, re.DOTALL)
                        if mobile_match:
                            try:
                                mobile_data = json.loads(mobile_match.group(1))
                                if 'entry_data' in mobile_data and 'PostPage' in mobile_data['entry_data']:
                                    for post in mobile_data['entry_data']['PostPage']:
                                        if 'graphql' in post and 'shortcode_media' in post['graphql']:
                                            media = post['graphql']['shortcode_media']
                                            if 'video_view_count' in media:
                                                views = media['video_view_count']
                                                logger.info(f"모바일 JSON에서 조회수 추출 성공: {views}")
                                                return views
                            except:
                                pass
                
                # 6. 텍스트 패턴 검색 (메타 설명에서 조회수 추출)
                meta_desc = soup.find('meta', attrs={'property': 'og:description'})
                if meta_desc and meta_desc.get('content'):
                    view_pattern = r'(\d{1,3}(,\d{3})*)\s*(views|조회)'
                    view_match = re.search(view_pattern, meta_desc.get('content'))
                    if view_match:
                        try:
                            views_str = view_match.group(1).replace(',', '')
                            views = int(views_str)
                            logger.info(f"메타 설명에서 조회수 추출 성공: {views}")
                            return views
                        except:
                            pass
            except Exception as e:
                logger.error(f"HTML 파싱 오류: {e}")
            
            logger.warning(f"HTML 응답에서 조회수를 찾을 수 없음 (응답 길이: {len(content)})")
        else:
            logger.warning(f"HTML 요청 실패: 상태 코드 {html_response.status_code}")
    except Exception as e:
        logger.error(f"HTML 파싱 오류: {e}")
    
    return None

if __name__ == "__main__":
    instagram_reels()