"""
유틸리티 함수 모듈
"""

import time
import random
import logging
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style, init

# colorama 초기화 (Windows에서 색상 지원)
init(autoreset=True)


def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """
    로깅 설정
    
    Args:
        log_dir: 로그 파일 저장 디렉토리
        
    Returns:
        로거 객체
    """
    # 로그 디렉토리 생성
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 로그 파일명 (날짜 포함)
    log_file = log_path / f"automation_{datetime.now().strftime('%Y%m%d')}.log"
    
    # 로거 설정
    logger = logging.getLogger('hanjin_automation')
    logger.setLevel(logging.DEBUG)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def random_delay(min_sec: float, max_sec: float):
    """
    랜덤 딜레이
    
    Args:
        min_sec: 최소 딜레이 (초)
        max_sec: 최대 딜레이 (초)
    """
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def print_progress(current: int, total: int, text: str = ""):
    """
    진행 상황 출력
    
    Args:
        current: 현재 진행 번호
        total: 전체 개수
        text: 추가 텍스트
    """
    percentage = (current / total) * 100
    bar_length = 30
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    
    print(f"\r[{bar}] {current}/{total} ({percentage:.1f}%) {text}", end='', flush=True)


def print_success(message: str):
    """성공 메시지 출력 (녹색)"""
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")


def print_error(message: str):
    """에러 메시지 출력 (빨간색)"""
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")


def print_info(message: str):
    """정보 메시지 출력 (파란색)"""
    print(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")


def print_warning(message: str):
    """경고 메시지 출력 (노란색)"""
    print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")









