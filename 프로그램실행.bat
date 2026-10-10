@echo off
chcp 65001 >nul
title AI 쇼츠 생성기
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo 프로그램 설치가 필요합니다. 원클릭 설치를 시작합니다.
    call "%~dp0setup_for_customer.bat"
    exit /b %errorlevel%
)

echo AI 쇼츠 생성기를 시작합니다.
echo 브라우저가 열리지 않으면 http://localhost:8501 로 접속하세요.
echo 종료하려면 이 창에서 Ctrl+C를 누르세요.
echo.

"%~dp0venv\Scripts\python.exe" -m streamlit run "%~dp0webui\Main.py" --server.port 8501 --server.address localhost
if errorlevel 1 (
    echo.
    echo 실행 중 오류가 발생했습니다. 화면 내용을 고객지원에 전달해주세요.
)

pause
