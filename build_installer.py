"""
Windows 설치 파일 빌드 스크립트
PyInstaller를 사용하여 실행 파일 생성
"""

import subprocess
import sys
import os
from pathlib import Path

def build_executable():
    """실행 파일 빌드"""
    print("=" * 60)
    print("송장번호 일괄 처리 시스템 - 빌드 시작")
    print("=" * 60)
    
    # PyInstaller 설치 확인
    try:
        import PyInstaller
        print("✓ PyInstaller 설치 확인됨")
    except ImportError:
        print("✗ PyInstaller가 설치되지 않았습니다.")
        print("설치 중: pip install pyinstaller")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller 설치 완료")
    
    # 빌드 실행
    spec_file = Path(__file__).parent / "build_installer.spec"
    
    if not spec_file.exists():
        print(f"✗ 스펙 파일을 찾을 수 없습니다: {spec_file}")
        return False
    
    print(f"\n빌드 시작: {spec_file}")
    print("-" * 60)
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            "--clean",
            str(spec_file)
        ])
        print("\n" + "=" * 60)
        print("✓ 빌드 완료!")
        print("=" * 60)
        print(f"\n실행 파일 위치: dist/송장번호일괄처리시스템.exe")
        print("\n다음 단계:")
        print("1. dist/송장번호일괄처리시스템.exe 파일 확인")
        print("2. Inno Setup으로 설치 프로그램 생성")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 빌드 실패: {e}")
        return False

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)










