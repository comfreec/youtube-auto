@echo off
chcp 65001 >nul
title AI 쇼츠 생성기 - 원클릭 설치
cd /d "%~dp0"

echo ========================================
echo    AI 쇼츠 생성기 원클릭 설치
echo ========================================
echo.
echo Python이 없으면 Windows 패키지 관리자로 자동 설치합니다.
echo 인터넷 속도에 따라 10~30분 정도 걸릴 수 있습니다.
echo.
pause

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_customer.ps1"
if errorlevel 1 (
    echo.
    echo 설치에 실패했습니다. 위 오류 내용을 고객지원에 전달해주세요.
    pause
    exit /b 1
)

echo.
echo 설치가 완료되었습니다. 프로그램을 실행합니다.
start "" "%~dp0프로그램실행.bat"
exit /b 0
