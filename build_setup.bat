@echo off
chcp 65001 >nul
echo ======================================================================
echo 송장번호 일괄 처리 시스템 - 배포용 SETUP 프로그램 빌드
echo ======================================================================
echo.

REM Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python 3.8 이상을 설치해주세요.
    pause
    exit /b 1
)

REM 빌드 스크립트 실행
python build_setup.py

if errorlevel 1 (
    echo.
    echo [오류] 빌드 중 오류가 발생했습니다.
    pause
    exit /b 1
)

echo.
echo 빌드가 완료되었습니다!
pause






