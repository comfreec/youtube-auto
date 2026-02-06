@echo off
chcp 65001 > nul
title 프로세스 정리
color 0C

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║     🔄 모든 서버 프로세스 정리                         ║
echo ╚════════════════════════════════════════════════════════╝
echo.

echo [1/3] Python 프로세스 종료 중...
taskkill /F /IM python.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo       ✅ Python 프로세스 종료 완료
) else (
    echo       ℹ️  실행 중인 Python 프로세스 없음
)
echo.

echo [2/3] ngrok 프로세스 종료 중...
taskkill /F /IM ngrok.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo       ✅ ngrok 프로세스 종료 완료
) else (
    echo       ℹ️  실행 중인 ngrok 프로세스 없음
)
echo.

echo [3/3] 프로세스 종료 확인 중...
timeout /t 2 /nobreak > nul

REM 남아있는 프로세스 확인
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo       ⚠️  일부 Python 프로세스가 남아있습니다
) else (
    echo       ✅ Python 프로세스 정리 완료
)

tasklist /FI "IMAGENAME eq ngrok.exe" 2>NUL | find /I /N "ngrok.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo       ⚠️  일부 ngrok 프로세스가 남아있습니다
) else (
    echo       ✅ ngrok 프로세스 정리 완료
)

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║     ✅ 프로세스 정리 완료                              ║
echo ║     이제 모바일_자동업로드_시작.bat을 실행하세요!      ║
echo ╚════════════════════════════════════════════════════════╝
echo.

pause
