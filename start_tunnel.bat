@echo off
echo Starting Streamlit...
start /B streamlit run webui/Main.py --server.port 8501
timeout /t 5
echo Starting Ngrok tunnel...
ngrok.exe http 8501
pause