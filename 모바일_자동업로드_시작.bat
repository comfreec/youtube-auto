@echo off
chcp 65001 > nul
title 모바일 자동 업로드 서버
color 0A

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║     🎬 모바일 자동 업로드 서버 시작                    ║
echo ╚════════════════════════════════════════════════════════╝
echo.
echo 📱 백그라운드 워커 + 자동 YouTube 업로드 지원
echo.

REM 1단계: 모든 프로세스 완전 종료
echo [1/4] 🔄 기존 프로세스 종료 중...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM ngrok.exe >nul 2>&1
timeout /t 2 /nobreak > nul

REM ngrok 완전 종료 확인
:wait_ngrok
tasklist /FI "IMAGENAME eq ngrok.exe" 2>NUL | find /I /N "ngrok.exe">NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak > nul
    goto wait_ngrok
)
echo       ✅ 기존 프로세스 종료 완료
echo.

REM 2단계: 모바일 API 서버 시작 (포트 8001 강제)
echo [2/4] 🚀 모바일 API 서버 시작 중 (포트 8001)...
start /B python webui/mobile_api_server.py
timeout /t 8 /nobreak > nul

REM 서버 시작 확인
netstat -an | findstr ":8001" >nul
if %ERRORLEVEL% EQU 0 (
    echo       ✅ 서버 시작 완료
) else (
    echo       ⚠️  서버 시작 확인 실패 - 계속 진행합니다
)
echo.

REM 3단계: 추가 대기 (서버 완전 초기화)
echo [3/4] ⏳ 서버 초기화 대기 중...
timeout /t 5 /nobreak > nul
echo       ✅ 초기화 완료
echo.

REM 4단계: ngrok 터널 생성
echo [4/4] 🌐 ngrok 터널 생성 중...
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║  잠시 후 ngrok 주소가 표시됩니다!                      ║
echo ║  그 주소를 모바일 브라우저에서 접속하세요!             ║
echo ║                                                        ║
echo ║  📱 화면을 꺼도 백그라운드에서 계속 작업합니다!        ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM ngrok 실행 (포트 8001)
ngrok.exe http 8001

echo.
echo 서버가 종료되었습니다.
pause
