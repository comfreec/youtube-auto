@echo off
title YouTube Shorts 고정 터널
echo 🌐 YouTube Shorts 고정 터널 시작
echo ================================

REM 터널 이름 설정
set TUNNEL_NAME=youtube-shorts-%RANDOM%

echo 터널 이름: %TUNNEL_NAME%
echo 로컬 서버: http://localhost:8501
echo.

REM 고정 터널 실행 (계정 필요)
cloudflared.exe tunnel --url http://localhost:8501 --name %TUNNEL_NAME% --logfile tunnel_fixed.log

pause