@echo off
chcp 65001 >nul
title 판매자 전용 라이선스 서버
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_seller_license_server.ps1"
pause
