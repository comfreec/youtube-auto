@echo off
echo 🚀 Cloudflare 고정 터널 설정
echo ================================

echo.
echo 1단계: Cloudflare 로그인
cloudflared.exe tunnel login

echo.
echo 2단계: 터널 생성 (이름: youtube-shorts-tunnel)
cloudflared.exe tunnel create youtube-shorts-tunnel

echo.
echo 3단계: DNS 레코드 생성
set /p DOMAIN="도메인을 입력하세요 (예: myapp.example.com): "
cloudflared.exe tunnel route dns youtube-shorts-tunnel %DOMAIN%

echo.
echo 4단계: 설정 파일 생성
echo tunnel: youtube-shorts-tunnel > config.yml
echo credentials-file: C:\Users\%USERNAME%\.cloudflared\[TUNNEL-ID].json >> config.yml
echo ingress: >> config.yml
echo   - hostname: %DOMAIN% >> config.yml
echo     service: http://localhost:8501 >> config.yml
echo   - service: http_status:404 >> config.yml

echo.
echo 5단계: 터널 실행
cloudflared.exe tunnel --config config.yml run youtube-shorts-tunnel

pause