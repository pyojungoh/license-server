"""
배포용 SETUP 프로그램 자동 빌드 스크립트
PyInstaller로 실행 파일 생성 → Inno Setup으로 설치 프로그램 생성
"""

import subprocess
import sys
import os
from pathlib import Path
import shutil

# 버전 정보 로드
def get_version():
    """version.txt에서 버전 읽기"""
    version_file = Path(__file__).parent / "version.txt"
    if version_file.exists():
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return "1.0.0"

def check_pyinstaller():
    """PyInstaller 설치 확인"""
    try:
        import PyInstaller
        print("✓ PyInstaller 설치 확인됨")
        return True
    except ImportError:
        print("✗ PyInstaller가 설치되지 않았습니다.")
        print("설치 중...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✓ PyInstaller 설치 완료")
            return True
        except subprocess.CalledProcessError:
            print("✗ PyInstaller 설치 실패")
            return False

def check_inno_setup():
    """Inno Setup 설치 확인"""
    # 일반적인 Inno Setup 설치 경로들
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            print(f"✓ Inno Setup 발견: {path}")
            return path
    
    print("⚠ Inno Setup을 찾을 수 없습니다.")
    print("다운로드: https://jrsoftware.org/isdl.php")
    return None

def build_executable():
    """PyInstaller로 실행 파일 빌드"""
    print("\n" + "=" * 70)
    print("Step 1: 실행 파일 빌드 (PyInstaller)")
    print("=" * 70)
    
    spec_file = Path(__file__).parent / "build_installer.spec"
    
    if not spec_file.exists():
        print(f"✗ 스펙 파일을 찾을 수 없습니다: {spec_file}")
        return False
    
    # 기존 빌드 폴더 정리
    dist_dir = Path(__file__).parent / "dist"
    build_dir = Path(__file__).parent / "build"
    
    if dist_dir.exists():
        print("기존 dist 폴더 정리 중...")
        shutil.rmtree(dist_dir, ignore_errors=True)
    
    if build_dir.exists():
        print("기존 build 폴더 정리 중...")
        shutil.rmtree(build_dir, ignore_errors=True)
    
    print(f"\n빌드 시작: {spec_file}")
    print("-" * 70)
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            str(spec_file)
        ])
        
        exe_path = dist_dir / "송장번호일괄처리시스템.exe"
        if exe_path.exists():
            print("\n✓ 실행 파일 빌드 완료!")
            print(f"  위치: {exe_path}")
            file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
            print(f"  크기: {file_size:.2f} MB")
            return True
        else:
            print("\n✗ 실행 파일이 생성되지 않았습니다.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 빌드 실패: {e}")
        return False

def build_installer(inno_path):
    """Inno Setup으로 설치 프로그램 생성"""
    print("\n" + "=" * 70)
    print("Step 2: 설치 프로그램 생성 (Inno Setup)")
    print("=" * 70)
    
    iss_file = Path(__file__).parent / "installer.iss"
    
    if not iss_file.exists():
        print(f"✗ Inno Setup 스크립트를 찾을 수 없습니다: {iss_file}")
        return False
    
    # 버전 정보 업데이트
    version = get_version()
    print(f"버전: {version}")
    
    # installer 폴더 생성
    installer_dir = Path(__file__).parent / "installer"
    installer_dir.mkdir(exist_ok=True)
    
    print(f"\n컴파일 시작: {iss_file}")
    print("-" * 70)
    
    try:
        subprocess.check_call([
            inno_path,
            str(iss_file)
        ])
        
        # 생성된 설치 파일 찾기
        setup_files = list(installer_dir.glob("*.exe"))
        if setup_files:
            setup_file = setup_files[0]
            print("\n✓ 설치 프로그램 생성 완료!")
            print(f"  위치: {setup_file}")
            file_size = setup_file.stat().st_size / (1024 * 1024)  # MB
            print(f"  크기: {file_size:.2f} MB")
            return True
        else:
            print("\n✗ 설치 프로그램이 생성되지 않았습니다.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 설치 프로그램 생성 실패: {e}")
        return False

def main():
    """메인 빌드 프로세스"""
    print("=" * 70)
    print("송장번호 일괄 처리 시스템 - 배포용 SETUP 프로그램 빌드")
    print("=" * 70)
    
    # 1. PyInstaller 확인
    if not check_pyinstaller():
        return 1
    
    # 2. Inno Setup 확인
    inno_path = check_inno_setup()
    if not inno_path:
        print("\n⚠ Inno Setup이 설치되지 않았습니다.")
        print("설치 프로그램 생성 단계를 건너뜁니다.")
        print("실행 파일만 빌드합니다.")
        build_executable_only = True
    else:
        build_executable_only = False
    
    # 3. 실행 파일 빌드
    if not build_executable():
        return 1
    
    # 4. 설치 프로그램 생성 (Inno Setup이 있는 경우)
    if not build_executable_only:
        if not build_installer(inno_path):
            print("\n⚠ 설치 프로그램 생성에 실패했지만 실행 파일은 빌드되었습니다.")
            print("  실행 파일 위치: dist/송장번호일괄처리시스템.exe")
            return 1
    
    # 완료
    print("\n" + "=" * 70)
    print("✓ 빌드 완료!")
    print("=" * 70)
    
    version = get_version()
    if not build_executable_only:
        print(f"\n설치 프로그램: installer/송장번호 일괄 처리 시스템_Setup_v{version}.exe")
    
    print(f"실행 파일: dist/송장번호일괄처리시스템.exe")
    print("\n배포 준비 완료!")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n빌드가 취소되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)







