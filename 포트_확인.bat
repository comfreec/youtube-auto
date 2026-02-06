@echo off
chcp 65001 > nul
title 포트 확인
color 0B

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║     🔍 서버 포트 상태 확인                             ║
echo ╚════════════════════════════════════════════════════════╝
echo.

echo [포트 8001] 모바일 API 서버 (백그라운드 워커 + 자동 업로드)
netstat -an | findstr ":8001" >nul
if %ERRORLEVEL% EQU 0 (
    echo       ✅ 실행 중
    netstat -ano | findstr ":8001" | findstr "LISTENING"
) else (
    echo       ❌ 실행 안 됨
)
echo.

echo [포트 8501] Streamlit 서버 (일반 UI)
netstat -an | findstr ":8501" >nul
if %ERRORLEVEL% EQU 0 (
    echo       ✅ 실행 중
    netstat -ano | findstr ":8501" | findstr "LISTENING"
) else (
    echo       ❌ 실행 안 됨
)
echo.

echo [포트 8502] PWA 정적 파일 서버
netstat -an | findstr ":8502" >nul
if %ERRORLEVEL% EQU 0 (
    echo       ✅ 실행 중
    netstat -ano | findstr ":8502" | findstr "LISTENING"
) else (
    echo       ❌ 실행 안 됨
)
echo.

echo ╔════════════════════════════════════════════════════════╗
echo ║     💡 모바일 자동 업로드는 8001 포트를 사용합니다!    ║
echo ╚════════════════════════════════════════════════════════╝
echo.

pause
