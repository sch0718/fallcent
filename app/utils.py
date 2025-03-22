from typing import List, Dict, Any, Optional
import yaml
import random
import logging
import os
import json
from datetime import datetime
import asyncio
import time

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_user_agents(config_path: str) -> List[str]:
    """설정 파일에서 사용자 에이전트 목록을 가져옵니다."""
    config = load_config(config_path)
    return config.get("user_agents", [])

def load_config(config_path: str) -> Dict:
    """설정 파일을 로드합니다.
    
    Args:
        config_path: 설정 파일 경로 (상대 또는 절대 경로)
        
    Returns:
        설정 정보가 포함된 딕셔너리
    """
    try:
        # 상대 경로가 제공된 경우 절대 경로로 변환
        if not os.path.isabs(config_path):
            # 프로젝트 루트 디렉토리를 기준으로 경로 해석
            project_root = find_project_root()
            absolute_path = os.path.join(project_root, config_path)
            if os.path.exists(absolute_path):
                config_path = absolute_path
            else:
                logger.warning(f"설정 파일을 찾을 수 없습니다: {absolute_path}")
                
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        logger.error(f"설정 파일 로드 중 오류 발생: {e}")
        # 기본 설정 반환
        return {
            "reels_urls": [], 
            "api_settings": {"request_delay": {"min": 1, "max": 3}},
            "user_agents": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ]
        }
    
def get_random_user_agent(config_path: str) -> str:
    """무작위 사용자 에이전트를 반환합니다."""
    user_agents = get_user_agents(config_path)
    if not user_agents:
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    return random.choice(user_agents)

def find_project_root() -> str:
    """프로젝트 루트 디렉토리를 찾습니다."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # app 디렉토리의 부모 디렉토리가 프로젝트 루트
    return os.path.dirname(current_dir)

def save_results(results: List[Dict[str, Any]], filename: str) -> str:
    """결과를 JSON 파일로 저장합니다.
    
    Args:
        results: 저장할 결과 데이터 리스트
        filename: 파일 이름 접두사
        
    Returns:
        저장된 파일의 경로
    """
    if not results:
        logger.warning("저장할 결과가 없습니다.")
        return ""
    
    # 결과 디렉토리 생성
    output_dir = os.path.join(find_project_root(), "results")
    os.makedirs(output_dir, exist_ok=True)
    
    # 타임스탬프를 파일 이름에 추가
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = f"{filename}_{timestamp}.json"
    filepath = os.path.join(output_dir, full_filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"결과가 성공적으로 저장되었습니다: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"결과 저장 중 오류 발생: {e}")
        return ""

async def sleep_with_jitter(min_delay: float = 1.0, max_delay: float = 3.0) -> None:
    """asyncio를 사용하여 무작위 지연을 수행합니다.
    
    Args:
        min_delay: 최소 지연 시간(초)
        max_delay: 최대 지연 시간(초)
    """
    delay = random.uniform(min_delay, max_delay)
    logger.debug(f"지연 시간: {delay:.2f}초")
    await asyncio.sleep(delay)

def sleep_with_jitter(min_delay: float = 1.0, max_delay: float = 3.0) -> None:
    """무작위 지연을 수행합니다.
    
    Args:
        min_delay: 최소 지연 시간(초)
        max_delay: 최대 지연 시간(초)
    """
    delay = random.uniform(min_delay, max_delay)
    logger.debug(f"지연 시간: {delay:.2f}초")
    time.sleep(delay) 