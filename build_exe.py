"""
실행 파일 빌드 스크립트
PyInstaller를 사용하여 GUI 프로그램을 단일 실행 파일로 패키징합니다.
"""

import PyInstaller.__main__
import sys
from pathlib import Path

def build_executable():
    """실행 파일 빌드"""
    project_root = Path(__file__).parent
    
    # PyInstaller 옵션
    options = [
        'src/gui_app.py',  # 메인 파일
        '--name=송장번호일괄처리시스템',  # 실행 파일 이름
        '--onefile',  # 단일 실행 파일로 생성
        '--windowed',  # 콘솔 창 숨김 (GUI만 표시)
        '--icon=NONE',  # 아이콘은 나중에 추가 가능
        '--add-data=config;config',  # config 폴더 포함
        '--hidden-import=openpyxl',  # 명시적 import
        '--hidden-import=pyserial',  # 명시적 import
        '--hidden-import=tkinter',  # 명시적 import
        '--hidden-import=tkinter.ttk',  # 명시적 import
        '--hidden-import=tkinter.messagebox',  # 명시적 import
        '--hidden-import=tkinter.filedialog',  # 명시적 import
        '--collect-all=openpyxl',  # openpyxl 의존성 수집
        '--noconfirm',  # 기존 빌드 덮어쓰기
        '--clean',  # 빌드 전 캐시 정리
    ]
    
    print("=" * 60)
    print("실행 파일 빌드 시작...")
    print("=" * 60)
    
    try:
        PyInstaller.__main__.run(options)
        print("\n" + "=" * 60)
        print("빌드 완료!")
        print(f"실행 파일 위치: {project_root / 'dist' / '송장번호일괄처리시스템.exe'}")
        print("=" * 60)
    except Exception as e:
        print(f"\n빌드 실패: {e}")
        print("\nPyInstaller가 설치되어 있는지 확인하세요:")
        print("  pip install pyinstaller")
        sys.exit(1)

if __name__ == "__main__":
    build_executable()

