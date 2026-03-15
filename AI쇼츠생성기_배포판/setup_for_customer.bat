@echo off
chcp 65001 >nul
title AI 쇼츠 생성기 - 자동 설치

echo ========================================
echo    AI 쇼츠 생성기 자동 설치
echo ========================================
echo.
echo 설치를 시작합니다...
echo 약 5-10분 정도 소요됩니다.
echo.
pause

echo.
echo [1/5] Python 설치 확인 중...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Python이 설치되어 있지 않습니다!
    echo.
    echo Python 3.10 이상을 설치해주세요:
    echo https://www.python.org/downloads/
    echo.
    echo 설치 시 "Add Python to PATH" 옵션을 꼭 체크하세요!
    echo.
    pause
    exit /b 1
)
echo ✅ Python 설치 확인 완료

echo.
echo [2/5] 가상환경 생성 중...
if not exist "venv" (
    python -m venv venv
    echo ✅ 가상환경 생성 완료
) else (
    echo ✅ 가상환경이 이미 존재합니다
)

echo.
echo [3/5] 가상환경 활성화 중...
call venv\Scripts\activate.bat
echo ✅ 가상환경 활성화 완료

echo.
echo [4/5] 필수 패키지 설치 중...
echo (시간이 좀 걸립니다. 기다려주세요...)
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ❌ 패키지 설치 중 오류가 발생했습니다.
    echo 인터넷 연결을 확인하고 다시 시도해주세요.
    echo.
    pause
    exit /b 1
)
echo ✅ 패키지 설치 완료

echo.
echo [5/5] 설정 파일 생성 중...
if not exist "config.toml" (
    copy config.example.toml config.toml >nul 2>&1
    echo ✅ 설정 파일 생성 완료
) else (
    echo ✅ 설정 파일이 이미 존재합니다
)

echo.
echo ========================================
echo    설치 완료!
echo ========================================
echo.
echo 다음 단계:
echo 1. "프로그램실행.bat" 파일을 더블클릭하여 실행
echo 2. 라이선스 키를 입력
echo 3. 웹 브라우저가 자동으로 열립니다
echo.
echo 문제가 있으면 README.md 파일을 참고하세요.
echo.
pause
