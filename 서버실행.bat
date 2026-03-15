@echo off
chcp 65001 > nul
echo ============================================
echo 🎬 AI 영상 생성 서버 시작
echo ============================================
echo.

REM 새 터미널 창에서 Streamlit 실행
start "Streamlit 웹 UI" cmd /k "streamlit run webui/Main.py --server.port 8501"
timeout /t 2 /nobreak > nul

REM 새 터미널 창에서 모바일 서버 실행
start "모바일 서버" cmd /k "python mobile_server_simple.py"
timeout /t 2 /nobreak > nul

REM 새 터미널 창에서 ngrok 실행
start "ngrok 터널" cmd /k "ngrok http 8000"
timeout /t 3 /nobreak > nul

echo.
echo ✅ 모든 서버가 시작되었습니다!
echo.
echo 📱 웹 UI: http://localhost:8501
echo 🌐 모바일: http://localhost:8000
echo 🔗 ngrok: http://127.0.0.1:4040 (관리 페이지)
echo.
echo 💡 각 서버는 별도 창에서 실행됩니다.
echo 💡 서버를 종료하려면 각 창을 닫으세요.
echo.
pause
