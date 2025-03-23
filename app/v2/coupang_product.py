import logging
import requests
import time
import sys
import pathlib
from typing import Any, Dict, List

# 현재 디렉토리의 상위 디렉토리(app)를 가져오기
current_dir = pathlib.Path(__file__).parent.parent
# 프로젝트 루트 디렉토리 추가 (app의 상위 디렉토리)
project_root = current_dir.parent
sys.path.append(str(project_root))

from app.utils import load_config, save_results, sleep_with_jitter

# 로깅 설정 (디버깅용)
# http_client.HTTPConnection.debuglevel = 1
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def coupang_product() -> List[Dict[str, Any]]:
    """
    구현해야 할 것:
    - 해당 list를 5번 for문으로 순회(총 100번)
    """
    
    # YAML 설정 파일 불러오기
    config: Dict[str, Any] = load_config('coupang.yaml')
    
    # 설정 파일에서 URL 목록과 요청 설정 가져오기
    product_url_list: List[str] = config.get('product_urls', [])
    request_settings: Dict[str, Any] = config.get('request_settings', {})
    
    # 지연 시간 범위 설정
    min_delay: int = request_settings.get('delay_range', {}).get('min', 1)
    max_delay: int = request_settings.get('delay_range', {}).get('max', 3)

    logger.info(f"product_url_list 길이: {len(product_url_list)}")
    
    # 브라우저처럼 보이는 User-Agent 헤더 설정
    headers: Dict[str, str] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.coupang.com/'
    }
    
    success: int = 0
    fail: int = 0

    # 결과 저장 리스트
    results: List[Dict[str, Any]] = []

    # 5번 반복 실행하도록 for문 사용
    for count in range(5):
        logger.info(f"반복 {count+1}/5 시작")
        
        for i, url in enumerate(product_url_list):
            try:
                logger.info(f"count: {count}, URL {i+1}/{len(product_url_list)}: {url}")
                
                # 요청 시도
                # YAML 설정 파일에서 타임아웃 값 가져오기 (기본값 10초)
                timeout: int = request_settings.get('timeout', 10)
                response: requests.Response = requests.get(url, headers=headers, timeout=timeout)
                status_code: int = response.status_code
                logger.info(f"response.status_code: {status_code}")
                
                if status_code == 200:
                    success += 1
                    logger.info(f"URL 접근 성공: {url}, 상태 코드: {status_code}")
                    results.append({"url": url, "status_code": status_code})
                else:
                    fail += 1
                    logger.warning(f"URL 접근 실패: {url}, 상태 코드: {status_code}")
                    results.append({"url": url, "status_code": status_code, "error": "URL 접근 실패"})
                
                # 요청 간 임의 지연 시간 추가
                sleep_with_jitter(min_delay, max_delay)
                
            except requests.RequestException as e:
                fail += 1
                logger.error(f"요청 예외 발생: {url}, 오류: {str(e)}")
                results.append({"url": url, "status_code": None, "error": str(e)})
                time.sleep(1)  # 오류 발생 시 최소 대기
            except Exception as e:
                fail += 1
                logger.error(f"일반 예외 발생: {url}, 오류: {str(e)}")
                results.append({"url": url, "status_code": None, "error": str(e)})
                time.sleep(1)  # 오류 발생 시 최소 대기
        
        logger.info(f"반복 {count+1}/5 완료, 현재 상태 - 성공: {success}, 실패: {fail}")

    logger.info(f"모든 작업 완료 - 성공: {success}, 실패: {fail}")

    

    # 결과 출력
    logger.info("==== 쿠팡 상품 URL 호출 결과 ====")
    for result in results:
        url = result["url"]
        status_code = result.get("status_code")
        error = result.get("error")
        
        if status_code is not None:
            logger.info(f"URL: {url}, 상태 코드: {status_code}")
        else:
            logger.info(f"URL: {url}, 오류: {error}")
    
    # 결과 저장
    result_file = save_results(results, "coupang_product_urls")
    if result_file:
        logger.info(f"결과를 파일에 저장했습니다: {result_file}")

    return results

if __name__ == "__main__":
    coupang_product()
