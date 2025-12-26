@echo off
echo ========================================
echo 라이선스 서버 시작
echo ========================================
cd /d %~dp0
python license_server.py
pause

