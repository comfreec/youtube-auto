@echo off
echo 🌐 고정 터널 생성 중...
echo ================================

echo 1. Cloudflare 로그인 (브라우저에서 인증)
cloudflared.exe tunnel login

echo.
echo 2. 고정 터널 생성
cloudflared.exe tunnel create youtube-shorts-fixed

echo.
echo 3. 터널 정보 확인
cloudflared.exe tunnel list

echo.
echo 4. 터널 실행 (고정 주소 생성됨)
cloudflared.exe tunnel run youtube-shorts-fixed --url http://localhost:8501

pause