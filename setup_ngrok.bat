@echo off
title YouTube Shorts ngrok 터널
echo 🚀 ngrok으로 고정 터널 설정
echo ===============================

echo.
echo ngrok 설치 확인 중...
where ngrok >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ ngrok이 설치되지 않았습니다.
    echo 다음 링크에서 다운로드하세요: https://ngrok.com/download
    echo.
    echo 설치 후 다음 명령어로 인증하세요:
    echo ngrok authtoken [YOUR_TOKEN]
    pause
    exit /b 1
)

echo ✅ ngrok 설치됨
echo.
echo 🌐 터널 시작 중... (Ctrl+C로 중지)
echo 고정 주소를 얻으려면 ngrok 계정이 필요합니다.
echo.

REM ngrok으로 터널 시작
ngrok http 8501 --log=stdout

pause