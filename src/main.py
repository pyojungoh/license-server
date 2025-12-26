"""
한진택배 송장번호 자동 등록 시스템 - 메인 프로그램
"""

import json
import time
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from bluetooth_controller import BluetoothController
from excel_reader import ExcelReader
from utils import (
    setup_logging, random_delay, print_progress,
    print_success, print_error, print_info, print_warning
)
from colorama import Fore, Style


def load_config(config_path: str = "config/settings.json") -> Dict[str, Any]:
    """
    설정 파일 로드
    
    Args:
        config_path: 설정 파일 경로
        
    Returns:
        설정 딕셔너리
    """
    # 프로젝트 루트 기준으로 경로 찾기
    project_root = Path(__file__).parent.parent
    config_file = project_root / config_path
    
    if not config_file.exists():
        print_warning(f"설정 파일을 찾을 수 없습니다: {config_file}")
        print_info("기본 설정을 사용합니다.")
        return get_default_config()
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print_success(f"설정 파일 로드: {config_path}")
        return config
    except Exception as e:
        print_error(f"설정 파일 로드 실패: {e}")
        print_info("기본 설정을 사용합니다.")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """기본 설정 반환"""
    return {
        "serial": {
            "port": "COM3",
            "baudrate": 115200,
            "timeout": 1.0
        },
        "delays": {
            "min_between": 2.0,
            "max_between": 3.0
        },
        "retry": {
            "max_attempts": 3,
            "retry_delay": 2.0
        },
        "excel": {
            "file_path": "data/invoices.xlsx",
            "column_name": "InvoiceNumber",
            "sheet_name": "Sheet1"
        }
    }


def countdown(seconds: int = 3):
    """카운트다운"""
    print_info(f"{seconds}초 후 시작합니다...")
    for i in range(seconds, 0, -1):
        print(f"\r  {i}...", end='', flush=True)
        time.sleep(1)
    print("\r  시작!  ")


def main():
    """메인 함수"""
    print("=" * 60)
    print("한진택배 송장번호 자동 등록 시스템")
    print("=" * 60)
    print()
    
    # 로깅 설정
    logger = setup_logging()
    logger.info("프로그램 시작")
    
    # 설정 로드
    config = load_config()
    
    # BLT AI 로봇 연결
    print_info("BLT AI 로봇 연결 중...")
    controller = BluetoothController(
        port=config["serial"]["port"],
        baudrate=config["serial"]["baudrate"],
        timeout=config["serial"].get("timeout", 1.0)
    )
    
    if not controller.connect():
        print_error("BLT AI 로봇 연결 실패!")
        print_info("다음을 확인하세요:")
        print("  1. BLT AI 로봇이 PC에 연결되어 있는지")
        print(f"  2. COM 포트 번호가 올바른지 (현재: {config['serial']['port']})")
        print("  3. 다른 프로그램에서 포트를 사용 중이 아닌지")
        logger.error("BLT AI 로봇 연결 실패")
        return 1
    
    print_success("BLT AI 로봇 연결 성공!")
    logger.info("BLT AI 로봇 연결 성공")
    
    # 블루투스 연결 확인 안내
    print()
    print_info("⚠ 중요: 모바일 기기와 블루투스 연결을 확인하세요!")
    print("  1. 모바일에서 '한진택배 스캐너'가 연결되어 있는지 확인")
    print("  2. 한진택배 앱이 열려 있고 입력 필드가 활성화되어 있는지 확인")
    print()
    response = input("모바일과 블루투스 연결이 완료되었나요? (y/n): ").strip().lower()
    if response != 'y':
        print_warning("블루투스 연결 후 다시 실행하세요.")
        controller.disconnect()
        return 1
    
    # 엑셀 파일 읽기
    try:
        # 엑셀 파일 경로를 프로젝트 루트 기준으로 변환
        excel_path = config["excel"]["file_path"]
        if not Path(excel_path).is_absolute():
            project_root = Path(__file__).parent.parent
            excel_path = project_root / excel_path
        
        reader = ExcelReader(
            file_path=str(excel_path),
            sheet_name=config["excel"].get("sheet_name", "Sheet1")
        )
        
        print_info("엑셀 파일 읽기 중...")
        invoices = reader.read_invoices()
        total = len(invoices)
        
        if total == 0:
            print_error("읽은 송장번호가 없습니다.")
            logger.error("송장번호가 없음")
            controller.disconnect()
            return 1
        
        print_success(f"총 {total}건의 송장번호를 읽었습니다.")
        logger.info(f"송장번호 {total}건 읽기 완료")
        
    except FileNotFoundError as e:
        print_error(f"엑셀 파일을 찾을 수 없습니다: {e}")
        logger.error(f"엑셀 파일 없음: {e}")
        controller.disconnect()
        return 1
    except Exception as e:
        print_error(f"엑셀 파일 읽기 실패: {e}")
        logger.error(f"엑셀 읽기 실패: {e}")
        controller.disconnect()
        return 1
    
    # 사용자 확인
    print()
    print_info("다음 작업을 수행합니다:")
    print(f"  - 총 {total}건의 송장번호 처리")
    print(f"  - 건당 딜레이: {config['delays']['min_between']}~{config['delays']['max_between']}초")
    print()
    response = input("계속하시겠습니까? (y/n): ").strip().lower()
    if response != 'y':
        print_info("취소되었습니다.")
        controller.disconnect()
        return 0
    
    # 카운트다운
    print()
    countdown(3)
    print()
    
    # 자동화 실행
    success_count = 0
    fail_count = 0
    failed_invoices = []
    
    logger.info("자동화 시작")
    
    try:
        for idx, invoice in enumerate(invoices, 1):
            print_progress(idx, total, f"처리 중: {invoice}")
            
            # 텍스트 전송
            retry_count = 0
            max_retries = config["retry"].get("max_attempts", 3)
            success = False
            
            while retry_count < max_retries and not success:
                if controller.send_text(invoice):
                    success = True
                    success_count += 1
                    logger.info(f"[{idx}/{total}] 성공: {invoice}")
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"[{idx}/{total}] 재시도 {retry_count}/{max_retries}: {invoice}")
                        time.sleep(config["retry"].get("retry_delay", 2.0))
            
            if not success:
                fail_count += 1
                failed_invoices.append(invoice)
                logger.error(f"[{idx}/{total}] 실패: {invoice}")
            
            # 딜레이 (마지막 항목 제외)
            if idx < total:
                delay_min = config["delays"]["min_between"]
                delay_max = config["delays"]["max_between"]
                random_delay(delay_min, delay_max)
        
        print()  # 진행 바 다음 줄
        print()
        
    except KeyboardInterrupt:
        print()
        print_warning("사용자에 의해 중단되었습니다.")
        logger.warning("사용자 중단")
    
    # 결과 출력
    print("=" * 60)
    print("처리 완료!")
    print("=" * 60)
    print(f"성공: {Fore.GREEN}{success_count}건{Style.RESET_ALL}")
    if fail_count > 0:
        print(f"실패: {Fore.RED}{fail_count}건{Style.RESET_ALL}")
    print(f"전체: {total}건")
    print()
    
    # 실패한 항목 저장
    if failed_invoices:
        failed_file = Path("logs") / f"failed_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(failed_file, 'w', encoding='utf-8') as f:
            for invoice in failed_invoices:
                f.write(f"{invoice}\n")
        print_info(f"실패한 송장번호 저장: {failed_file}")
        logger.info(f"실패 항목 {len(failed_invoices)}건 저장: {failed_file}")
    
    # 연결 종료
    controller.disconnect()
    logger.info("프로그램 종료")
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print_error(f"예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

