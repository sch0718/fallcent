import requests
import re
import json
import time
import random
import yaml
import logging
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

def instagram_reels():
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # YAML 설정 파일 불러오기
    with open('configs/instagram.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 설정 파일에서 URL 목록과 API 설정 가져오기
    reels_url = config['reels_urls']
    query_hash = config['api_settings']['query_hash']
    min_delay = config['api_settings']['request_delay']['min']
    max_delay = config['api_settings']['request_delay']['max']
    
    # 지연 시간 증가 (봇 탐지 방지)
    min_delay = min_delay * 2
    max_delay = max_delay * 3
    
    # User-Agent 랜더마이저 생성
    ua = UserAgent(browsers=['chrome', 'firefox', 'safari', 'edge'])
    
    # 세션 생성
    session = requests.Session()
    
    # 사용자 에이전트 목록
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
    
    # 레퍼러 목록
    referrers = [
        "https://www.google.com/search?q=인스타그램+릴스",
        "https://search.naver.com/search.naver?query=인스타그램",
        "https://www.instagram.com/explore/",
        "https://www.instagram.com/"
    ]
    
    # 쿠키 초기화 (인스타그램 홈페이지 방문)
    init_headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }
    
    try:
        logger.info("인스타그램 초기화 중...")
        init_response = session.get("https://www.instagram.com/", headers=init_headers, timeout=20)
        time.sleep(random.uniform(4, 8))
    except Exception as e:
        logger.error(f"초기화 오류: {e}")
    
    # 조회수 결과를 저장할 딕셔너리
    views_results = {}
    
    # 릴스 URL 패턴 추출 (shortcode 추출용)
    reels_pattern = r"https://www\.instagram\.com/reel/([a-zA-Z0-9_-]+)/.*"
    
    # 조회수 추출 방법: HTML, API, GraphQL
    extraction_methods = ["html", "api", "graphql"]
    
    for url in reels_url:
        try:
            # URL에서 릴스 ID(shortcode) 추출
            shortcode_match = re.search(reels_pattern, url)
            if not shortcode_match:
                logger.warning(f"릴스 ID를 찾을 수 없음: {url}")
                views_results[url] = "ID 추출 실패"
                continue
                
            shortcode = shortcode_match.group(1)
            
            # 추출 방법 무작위 선택 (다양한 접근 시도)
            random.shuffle(extraction_methods)
            
            views = None
            
            for method in extraction_methods:
                # 지연 시간 적용
                time.sleep(random.uniform(min_delay, max_delay))
                
                # 무작위 User-Agent 선택
                user_agent = random.choice(desktop_agents if random.random() < 0.8 else mobile_agents)
                
                # 레퍼러 설정
                referer = random.choice(referrers)
                
                if method == "html":
                    # HTML 직접 파싱 방식
                    try:
                        logger.info(f"HTML 방식으로 시도: {url}")
                        
                        html_headers = {
                            "User-Agent": user_agent,
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                            "Referer": referer,
                            "Connection": "keep-alive",
                            "Upgrade-Insecure-Requests": "1"
                        }
                        
                        html_response = session.get(url, headers=html_headers, timeout=20)
                        
                        if html_response.status_code != 200:
                            logger.warning(f"HTML 요청 실패: {url}, 상태 코드: {html_response.status_code}")
                            continue
                        
                        # 정규식으로 조회수 추출 패턴 (여러 패턴 시도)
                        patterns = [
                            r'"video_view_count"\s*:\s*(\d+)',
                            r'"play_count"\s*:\s*(\d+)',
                            r'"viewCount"\s*:\s*"(\d+)"',
                            r'"videoViewCount"\s*:\s*"(\d+)"'
                        ]
                        
                        for pattern in patterns:
                            view_match = re.search(pattern, html_response.text)
                            if view_match:
                                views = int(view_match.group(1))
                                logger.info(f"HTML에서 조회수 추출 성공: {views}")
                                break
                        
                        # BeautifulSoup으로 조회수 정보 찾기
                        if not views:
                            soup = BeautifulSoup(html_response.text, 'html.parser')
                            
                            # JSON 데이터가 포함된 스크립트 태그 찾기
                            scripts = soup.select('script[type="application/ld+json"]')
                            for script in scripts:
                                try:
                                    data = json.loads(script.string)
                                    if "interactionStatistic" in data:
                                        for stat in data["interactionStatistic"]:
                                            if stat.get("interactionType") == "http://schema.org/WatchAction":
                                                views = int(stat.get("userInteractionCount", 0))
                                                break
                                except:
                                    pass
                    except Exception as e:
                        logger.error(f"HTML 파싱 오류: {url}, 오류: {e}")
                
                elif method == "api":
                    # 표준 API 접근 방식
                    try:
                        logger.info(f"API 방식으로 시도: {url}")
                        
                        api_headers = {
                            "User-Agent": user_agent,
                            "Accept": "application/json",
                            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                            "Referer": referer,
                            "x-requested-with": "XMLHttpRequest",
                            "x-ig-app-id": "936619743392459",
                            "Connection": "keep-alive"
                        }
                        
                        # 표준 API URL (퍼블릭 접근)
                        api_url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis"
                        
                        api_response = session.get(api_url, headers=api_headers, timeout=20)
                        
                        if api_response.status_code != 200:
                            logger.warning(f"API 요청 실패: {url}, 상태 코드: {api_response.status_code}")
                            continue
                        
                        try:
                            json_data = api_response.json()
                            
                            # 조회수 데이터를 찾기 위한 여러 경로 탐색
                            if "items" in json_data and len(json_data["items"]) > 0:
                                media_item = json_data["items"][0]
                                if "video_view_count" in media_item:
                                    views = media_item["video_view_count"]
                                elif "play_count" in media_item:
                                    views = media_item["play_count"]
                                elif "view_count" in media_item:
                                    views = media_item["view_count"]
                            elif "graphql" in json_data and "shortcode_media" in json_data["graphql"]:
                                media = json_data["graphql"]["shortcode_media"]
                                if "video_view_count" in media:
                                    views = media["video_view_count"]
                                elif "play_count" in media:
                                    views = media["play_count"]
                            
                            if views:
                                logger.info(f"API에서 조회수 추출 성공: {views}")
                        except:
                            pass
                    except Exception as e:
                        logger.error(f"API 요청 오류: {url}, 오류: {e}")
                
                elif method == "graphql":
                    # GraphQL 방식
                    try:
                        logger.info(f"GraphQL 방식으로 시도: {url}")
                        
                        graphql_headers = {
                            "User-Agent": user_agent,
                            "Accept": "*/*",
                            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                            "Referer": referer,
                            "X-Requested-With": "XMLHttpRequest",
                            "Origin": "https://www.instagram.com",
                            "Connection": "keep-alive",
                            "Sec-Fetch-Dest": "empty",
                            "Sec-Fetch-Mode": "cors",
                            "Sec-Fetch-Site": "same-origin"
                        }
                        
                        # 그래프 API URL 구성 (설정 파일의 query_hash 사용)
                        api_url = f"https://www.instagram.com/graphql/query/?query_hash={query_hash}&variables=%7B%22shortcode%22%3A%22{shortcode}%22%7D"
                        
                        graphql_response = session.get(api_url, headers=graphql_headers, timeout=20)
                        
                        if graphql_response.status_code != 200:
                            logger.warning(f"GraphQL 요청 실패: {url}, 상태 코드: {graphql_response.status_code}")
                            continue
                        
                        try:
                            json_data = graphql_response.json()
                            
                            # 조회수 추출 (경로가 변경될 수 있음)
                            if 'data' in json_data and 'shortcode_media' in json_data['data']:
                                media_data = json_data['data']['shortcode_media']
                                
                                # 조회수 정보 확인 (위치가 다를 수 있음)
                                if 'video_view_count' in media_data:
                                    views = media_data['video_view_count']
                                elif 'play_count' in media_data:
                                    views = media_data['play_count']
                                elif 'edge_media_preview_like' in media_data:
                                    # 조회수가 없는 경우 좋아요 수로 대체
                                    views = media_data['edge_media_preview_like']['count']
                                
                                if views:
                                    logger.info(f"GraphQL에서 조회수 추출 성공: {views}")
                        except:
                            pass
                    except Exception as e:
                        logger.error(f"GraphQL 요청 오류: {url}, 오류: {e}")
                
                # 조회수를 찾았으면 반복 중단
                if views:
                    break
            
            # 결과 저장
            if views:
                views_results[url] = views
                logger.info(f"릴스 URL: {url}, 최종 조회수: {views}")
            else:
                views_results[url] = "조회수를 찾을 수 없음"
                logger.warning(f"조회수를 찾을 수 없음: {url}")
            
        except Exception as e:
            logger.error(f"처리 중 오류 발생: {url}, 오류: {e}")
            views_results[url] = f"처리 오류: {str(e)}"
            
        # 다음 URL 처리 전 대기 (IP 차단 방지)
        time.sleep(random.uniform(min_delay * 1.5, max_delay * 1.5))
            
    # 최종 결과 출력
    logger.info("\n=== 인스타그램 릴스 조회수 결과 ===")
    for url, views in views_results.items():
        logger.info(f"URL: {url}")
        logger.info(f"조회수: {views}")
        logger.info("-" * 50)
    
    # 콘솔 출력
    print("\n=== 인스타그램 릴스 조회수 결과 ===")
    for url, views in views_results.items():
        print(f"URL: {url}")
        print(f"조회수: {views}")
        print("-" * 50)
    
    return views_results