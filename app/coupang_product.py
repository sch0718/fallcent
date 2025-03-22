import requests
import time
import random
import yaml
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from fake_useragent import UserAgent
import logging
from datetime import datetime
import http.client as http_client
import urllib.parse
import os
from bs4 import BeautifulSoup

def coupang_product():
    
    # 로깅 설정 (디버깅용)
    # http_client.HTTPConnection.debuglevel = 1
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # YAML 설정 파일 불러오기
    with open('configs/coupang.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 설정 파일에서 URL 목록과 요청 설정 가져오기
    product_url_list = config['product_urls']
    
    # 설정에서 세션 수 가져오기
    sessions_count = config['request_settings']['sessions_count']
    
    # 설정에서 재시도 전략 가져오기
    retry_total = config['request_settings']['retry']['total']
    retry_status_forcelist = config['request_settings']['retry']['status_forcelist']
    retry_backoff_factor = config['request_settings']['retry']['backoff_factor']
    
    # 설정에서 지연 시간 범위 가져오기
    delay_min = config['request_settings']['delay_range']['min']
    delay_max = config['request_settings']['delay_range']['max']
    
    # 지연 시간 증가 (봇 탐지 방지)
    delay_min = delay_min * 3
    delay_max = delay_max * 5
    delay_range = (delay_min, delay_max)
    
    # HTTP 세션 설정
    sessions = []
    
    # 여러 세션 생성 (IP 분산 시뮬레이션)
    for i in range(sessions_count):
        session = requests.Session()
        retry_strategy = Retry(
            total=retry_total,
            status_forcelist=retry_status_forcelist,
            allowed_methods=["GET"],
            backoff_factor=retry_backoff_factor,
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        sessions.append(session)
    
    # 여러 쿠키 컬렉션 유지
    cookies_collection = [{} for _ in range(len(sessions))]
    
    # User-Agent 생성기
    ua = UserAgent(browsers=['chrome', 'firefox', 'safari', 'edge'])
    
    count = 0
    success = 0
    fail = 0
    
    # 로봇이 아닌 실제 사용자처럼 보이는 헤더 확장
    mobile_agents = [
        f"Mozilla/5.0 (iPhone; CPU iPhone OS {random.randint(13, 15)}_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{random.randint(13, 15)}.0 Mobile/15E148 Safari/604.1",
        f"Mozilla/5.0 (Linux; Android {random.randint(10, 13)}; SM-G{random.randint(900, 999)}0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 110)}.0.{random.randint(4000, 5000)}.{random.randint(100, 200)} Mobile Safari/537.36"
    ]
    
    desktop_agents = [
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 110)}.0.{random.randint(4000, 5000)}.{random.randint(100, 200)} Safari/537.36",
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randint(13, 15)}_{random.randint(1, 6)}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 110)}.0.{random.randint(4000, 5000)}.{random.randint(100, 200)} Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{random.randint(90, 110)}.0) Gecko/20100101 Firefox/{random.randint(90, 110)}.0",
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randint(13, 15)}_{random.randint(1, 6)}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{random.randint(13, 15)}.{random.randint(1, 6)} Safari/605.1.15"
    ]
    
    # HTTP 세션 초기화
    for i, session in enumerate(sessions):
        try:
            init_url = random.choice([
                "https://www.coupang.com/",
                "https://www.coupang.com/np/categories/186764",
                "https://www.coupang.com/np/search?component=&q=인기상품"
            ])
            
            # 초기 헤더 설정
            init_headers = {
                "User-Agent": ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0"
            }
            
            logger.info(f"HTTP 세션 {i+1} 초기화 중...")
            init_response = session.get(init_url, headers=init_headers, timeout=30)
            
            # 쿠키 저장
            if init_response.cookies:
                cookies_collection[i].update(dict(init_response.cookies))
                
            # 메타 정보 추출 및 저장 (쿠키 강화)
            if init_response.status_code == 200:
                # CSRF 토큰 추출 (있는 경우)
                csrf_pattern = r'name="csrf-token" content="([^"]+)"'
                csrf_match = re.search(csrf_pattern, init_response.text)
                if csrf_match:
                    cookies_collection[i]['csrf_token'] = csrf_match.group(1)
                    
                # 사용자 식별자 추출 (있는 경우)
                user_id_pattern = r'"userIdentity":"([^"]+)"'
                user_id_match = re.search(user_id_pattern, init_response.text)
                if user_id_match:
                    cookies_collection[i]['userIdentity'] = user_id_match.group(1)
                
                # 카테고리 페이지 탐색 (사용자 시뮬레이션)
                try:
                    soup = BeautifulSoup(init_response.text, 'html.parser')
                    category_links = soup.select('a[href*="/np/categories"]')
                    
                    if category_links:
                        category_url = "https://www.coupang.com" + category_links[random.randint(0, min(5, len(category_links)-1))]['href']
                        logger.info(f"카테고리 페이지 방문: {category_url}")
                        
                        # 카테고리 방문 헤더
                        category_headers = init_headers.copy()
                        category_headers["Referer"] = init_url
                        
                        # 카테고리 페이지 방문
                        category_response = session.get(
                            category_url, 
                            headers=category_headers,
                            cookies=cookies_collection[i],
                            timeout=30
                        )
                        
                        # 새 쿠키 저장
                        if category_response.cookies:
                            cookies_collection[i].update(dict(category_response.cookies))
                            
                        time.sleep(random.uniform(3, 6))
                except Exception as e:
                    logger.warning(f"카테고리 페이지 탐색 중 오류: {e}")
            
            # 세션 초기화를 위한 지연
            time.sleep(random.uniform(5, 10))
            
        except Exception as e:
            logger.error(f"세션 {i+1} 초기화 오류: {e}")
    
    # 상품 URL 무작위 셔플 (패턴 방지)
    random.shuffle(product_url_list)
    
    error_limit = 5  # 연속 오류 제한
    error_count = 0  # 연속 오류 카운터
    rotate_count = 0  # URL 회전 카운터
    
    # 검색 페이지를 통한 간접 접근 함수
    def access_via_search(session, product_id, session_idx):
        try:
            search_terms = ["생활용품", "식품", "가전제품", "패션", "화장품", "주방용품"]
            search_url = f"https://www.coupang.com/np/search?component=&q={urllib.parse.quote(random.choice(search_terms))}"
            
            headers = {
                "User-Agent": ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                "Referer": "https://www.coupang.com/",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            # 검색 페이지 접근
            search_response = session.get(search_url, headers=headers, cookies=cookies_collection[session_idx], timeout=30)
            
            # 쿠키 업데이트
            if search_response.cookies:
                cookies_collection[session_idx].update(dict(search_response.cookies))
                
            time.sleep(random.uniform(5, 10))
            
            # 제품 페이지 직접 접근
            product_url = f"https://www.coupang.com/vp/products/{product_id}"
            headers["Referer"] = search_url
            product_response = session.get(product_url, headers=headers, cookies=cookies_collection[session_idx], timeout=30)
            
            return product_response
        except Exception as e:
            logger.error(f"검색을 통한 접근 오류: {e}")
            return None
    
    # 메인 크롤링 로직
    while count < 5 and success < 20:  # 성공 횟수나 시도 횟수 제한
        current_hour = datetime.now().hour
        
        # 시간에 따른 지연 조정
        if 1 <= current_hour <= 5:
            actual_delay_range = (delay_range[0] * 0.8, delay_range[1] * 0.8)
        elif 9 <= current_hour <= 18:
            actual_delay_range = (delay_range[0] * 1.2, delay_range[1] * 1.2)
        else:
            actual_delay_range = delay_range
            
        # URL 목록을 다시 섞어 패턴 방지
        if rotate_count >= len(product_url_list):
            random.shuffle(product_url_list)
            rotate_count = 0
            
        # HTTP 세션으로 접근
        for i, url in enumerate(product_url_list[rotate_count:rotate_count+3]):
            session_idx = i % len(sessions)
            session = sessions[session_idx]
            cookies = cookies_collection[session_idx]
            
            try:
                # 자연스러운 지연
                time.sleep(random.uniform(*actual_delay_range))
                
                # 제품 ID 추출
                product_id_match = re.search(r'/products/(\d+)', url)
                product_id = product_id_match.group(1) if product_id_match else None
                
                # 접근 방식 결정 (직접 또는 검색 페이지 경유)
                indirect_access = random.random() < 0.7  # 70% 확률로 간접 접근
                
                if indirect_access and product_id:
                    # 접근 경로 다양화
                    access_path = random.choice([
                        "search",  # 검색을 통한 접근
                        "category", # 카테고리를 통한 접근
                        "home"  # 홈페이지를 통한 접근
                    ])
                    
                    if access_path == "search":
                        # 검색 페이지를 통한 접근
                        logger.info(f"검색을 통한 간접 접근: {url}")
                        response = access_via_search(session, product_id, session_idx)
                    elif access_path == "category":
                        # 카테고리를 통한 접근
                        try:
                            category_url = random.choice([
                                "https://www.coupang.com/np/categories/186764",
                                "https://www.coupang.com/np/categories/194276",
                                "https://www.coupang.com/np/categories/115573"
                            ])
                            
                            # 카테고리 페이지 방문
                            category_headers = {
                                "User-Agent": ua.random,
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                                "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                                "Referer": "https://www.coupang.com/",
                                "Connection": "keep-alive",
                                "Upgrade-Insecure-Requests": "1"
                            }
                            
                            logger.info(f"카테고리를 통한 간접 접근: {url}")
                            category_response = session.get(category_url, headers=category_headers, cookies=cookies, timeout=30)
                            
                            # 쿠키 업데이트
                            if category_response.cookies:
                                cookies.update(dict(category_response.cookies))
                                
                            time.sleep(random.uniform(4, 8))
                            
                            # 제품 페이지 접근
                            product_headers = category_headers.copy()
                            product_headers["Referer"] = category_url
                            response = session.get(url, headers=product_headers, cookies=cookies, timeout=30)
                        except Exception as e:
                            logger.error(f"카테고리 접근 오류: {e}")
                            response = None
                    else:  # home
                        # 홈페이지를 통한 접근
                        try:
                            home_url = "https://www.coupang.com/"
                            
                            # 홈페이지 방문
                            home_headers = {
                                "User-Agent": ua.random,
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                                "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                                "Referer": random.choice([
                                    "https://www.google.com/search?q=쿠팡+쇼핑",
                                    "https://search.naver.com/search.naver?query=쿠팡몰"
                                ]),
                                "Connection": "keep-alive",
                                "Upgrade-Insecure-Requests": "1"
                            }
                            
                            logger.info(f"홈페이지를 통한 간접 접근: {url}")
                            home_response = session.get(home_url, headers=home_headers, cookies=cookies, timeout=30)
                            
                            # 쿠키 업데이트
                            if home_response.cookies:
                                cookies.update(dict(home_response.cookies))
                                
                            time.sleep(random.uniform(4, 8))
                            
                            # 제품 페이지 접근
                            product_headers = home_headers.copy()
                            product_headers["Referer"] = home_url
                            response = session.get(url, headers=product_headers, cookies=cookies, timeout=30)
                        except Exception as e:
                            logger.error(f"홈페이지 접근 오류: {e}")
                            response = None
                else:
                    # 직접 접근
                    headers = {
                        "User-Agent": random.choice(desktop_agents) if random.random() < 0.8 else random.choice(mobile_agents),
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Cache-Control": "max-age=0",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1"
                    }
                    
                    # 레퍼러 추가
                    if random.random() < 0.8:
                        referrers = [
                            "https://www.google.com/search?q=쿠팡+인기상품",
                            "https://search.naver.com/search.naver?query=쿠팡몰",
                            "https://www.coupang.com/np/search?component=&q=인기상품",
                            "https://www.coupang.com/"
                        ]
                        headers["Referer"] = random.choice(referrers)
                    
                    logger.info(f"직접 접근: {url}")
                    response = session.get(
                        url, 
                        headers=headers, 
                        cookies=cookies, 
                        timeout=30,
                        allow_redirects=True
                    )
                
                # 쿠키 업데이트
                if response and response.cookies:
                    cookies.update(dict(response.cookies))
                
                if response and response.status_code == 200:
                    # 캡차 체크
                    if response.text and ("captcha" in response.text.lower() or "보안문자" in response.text):
                        logger.warning(f"캡차 감지됨: {url}")
                        time.sleep(random.uniform(60, 120))  # 더 긴 대기 시간 적용
                        fail += 1
                    else:
                        # 성공 처리
                        logger.info(f"성공적으로 접근: {url}")
                        
                        # 페이지 콘텐츠 분석 (필요한 경우)
                        try:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            title = soup.select_one('h2.prod-buy-header__title')
                            
                            if title:
                                logger.info(f"상품 제목: {title.text.strip()}")
                            
                            # 추가 페이지 요소 접근 (실제 사용자 흉내)
                            if random.random() < 0.3:  # 30% 확률로 리뷰 탭 접근
                                review_url = f"{url}&component=reviews"
                                review_headers = headers.copy()
                                review_headers["Referer"] = url
                                
                                logger.info(f"리뷰 페이지 접근: {review_url}")
                                session.get(
                                    review_url,
                                    headers=review_headers,
                                    cookies=cookies,
                                    timeout=30
                                )
                                
                                time.sleep(random.uniform(3, 6))
                        except Exception as e:
                            logger.warning(f"페이지 분석 오류: {e}")
                        
                        success += 1
                        error_count = 0
                elif response and response.status_code == 429:
                    logger.warning(f"속도 제한 (429): {url}")
                    time.sleep(random.uniform(90, 180))  # 매우 긴 대기 시간 적용
                    fail += 1
                    error_count += 1
                elif response and response.status_code in [403, 503]:
                    logger.warning(f"접근 차단 ({response.status_code}): {url}")
                    time.sleep(random.uniform(120, 240))  # 매우 긴 대기 시간 적용
                    fail += 1
                    error_count += 1
                    
                    # 세션 재생성
                    sessions[session_idx] = requests.Session()
                    retry_strategy = Retry(
                        total=retry_total,
                        status_forcelist=retry_status_forcelist,
                        allowed_methods=["GET"],
                        backoff_factor=retry_backoff_factor,
                        respect_retry_after_header=True
                    )
                    adapter = HTTPAdapter(max_retries=retry_strategy)
                    sessions[session_idx].mount("https://", adapter)
                    sessions[session_idx].mount("http://", adapter)
                    cookies_collection[session_idx] = {}
                    
                    # 세션 재초기화 (홈페이지 방문)
                    try:
                        init_headers = {
                            "User-Agent": ua.random,
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                            "Accept-Encoding": "gzip, deflate, br",
                            "Connection": "keep-alive",
                            "Upgrade-Insecure-Requests": "1"
                        }
                        
                        init_response = sessions[session_idx].get(
                            "https://www.coupang.com/",
                            headers=init_headers,
                            timeout=30
                        )
                        
                        if init_response.cookies:
                            cookies_collection[session_idx].update(dict(init_response.cookies))
                    except Exception as e:
                        logger.error(f"세션 재초기화 오류: {e}")
                else:
                    status_code = response.status_code if response else "연결 실패"
                    logger.warning(f"접근 실패: {url} (상태 코드: {status_code})")
                    fail += 1
                    error_count += 1
                
                # 연속 오류 처리
                if error_count >= error_limit:
                    logger.warning(f"연속 {error_count}회 오류 발생 - 장시간 대기")
                    time.sleep(random.uniform(240, 360))  # 4-6분 대기
                    
                    # 모든 세션 재생성
                    for i in range(len(sessions)):
                        sessions[i] = requests.Session()
                        adapter = HTTPAdapter(max_retries=retry_strategy)
                        sessions[i].mount("https://", adapter)
                        sessions[i].mount("http://", adapter)
                        cookies_collection[i] = {}
                        
                        # 기본 쿠키 획득
                        try:
                            init_response = sessions[i].get(
                                "https://www.coupang.com/",
                                headers={"User-Agent": ua.random},
                                timeout=30
                            )
                            
                            if init_response.cookies:
                                cookies_collection[i].update(dict(init_response.cookies))
                                
                            time.sleep(random.uniform(10, 15))
                        except Exception as e:
                            logger.error(f"세션 {i+1} 재초기화 오류: {e}")
                    
                    error_count = 0
            
            except Exception as e:
                logger.error(f"예상치 못한 오류: {e}")
                fail += 1
                error_count += 1
                time.sleep(random.uniform(30, 60))
        
        rotate_count += 3  # 다음 URL 세트로 이동
        count += 1
        logger.info(f"반복 {count} 완료 (성공: {success}, 실패: {fail})")
        
        # 반복 사이 휴식
        time.sleep(random.uniform(30, 60))

    total_requests = success + fail
    success_rate = (success / total_requests * 100) if total_requests > 0 else 0
    logger.info(f"최종 결과: 성공: {success}, 실패: {fail}, 성공률: {success_rate:.2f}%")
    print(f"최종 결과: 성공: {success}, 실패: {fail}, 성공률: {success_rate:.2f}%")