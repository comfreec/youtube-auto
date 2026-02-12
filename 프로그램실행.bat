@echo off
chcp 65001 >nul
title AI 쇼츠 생성기

echo ========================================
echo    AI 쇼츠 생성기
echo ========================================
echo.
echo 프로그램을 시작합니다...
echo.

REM 가상환경 활성화
call venv\Scripts\activate.bat

REM Streamlit 서버 실행
echo 웹 브라우저가 자동으로 열립니다...
echo.
echo 종료하려면 이 창을 닫거나 Ctrl+C를 누르세요.
echo.

python -m streamlit run webui/Main.py --server.port 8501 --server.address localhost

pause
