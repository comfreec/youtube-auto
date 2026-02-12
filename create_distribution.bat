@echo off
chcp 65001 >nul
title 배포 패키지 생성

echo ========================================
echo    배포 패키지 생성
echo ========================================
echo.

set DIST_FOLDER=AI쇼츠생성기_배포판
set VERSION=v1.0
set ZIP_NAME=AI쇼츠생성기_%VERSION%.zip

echo 버전: %VERSION%
echo.
pause

echo.
echo [1/5] 기존 폴더 정리 중...
if exist "%DIST_FOLDER%" (
    rmdir /s /q "%DIST_FOLDER%"
    echo ✅ 기존 폴더 삭제 완료
)

echo.
echo [2/5] 새 폴더 생성 중...
mkdir "%DIST_FOLDER%"
echo ✅ 폴더 생성 완료

echo.
echo [3/5] 필수 파일 복사 중...

REM 프로그램 코드
xcopy /E /I /Q app "%DIST_FOLDER%\app" >nul
xcopy /E /I /Q webui "%DIST_FOLDER%\webui" >nul

REM 리소스 파일 (있는 경우)
if exist "resource" (
    xcopy /E /I /Q resource "%DIST_FOLDER%\resource" >nul
)

REM 실행 파일
copy setup_for_customer.bat "%DIST_FOLDER%\" >nul
copy 프로그램실행.bat "%DIST_FOLDER%\" >nul
copy 외부접속.bat "%DIST_FOLDER%\" >nul
copy 외부접속.py "%DIST_FOLDER%\" >nul

REM 문서
copy 고객용_README.md "%DIST_FOLDER%\README.md" >nul

REM 설정 파일
copy requirements.txt "%DIST_FOLDER%\" >nul
copy config.example.toml "%DIST_FOLDER%\" >nul

REM 외부 도구
if exist "ngrok.exe" (
    copy ngrok.exe "%DIST_FOLDER%\" >nul
)

REM 라이선스
if exist "LICENSE" (
    copy LICENSE "%DIST_FOLDER%\" >nul
)

REM 필수 Python 파일들
copy main.py "%DIST_FOLDER%\" >nul
copy mobile_server_simple.py "%DIST_FOLDER%\" >nul

echo ✅ 파일 복사 완료

echo.
echo [4/5] 불필요한 파일 제거 중...

REM __pycache__ 폴더 제거
for /d /r "%DIST_FOLDER%" %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

REM .pyc 파일 제거
del /s /q "%DIST_FOLDER%\*.pyc" >nul 2>&1

REM 테스트 파일 제거
del /q "%DIST_FOLDER%\test_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\debug_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\check_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\fix_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\restart_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\restore_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\apply_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\reset_*.py" >nul 2>&1

REM 개발자 전용 파일 제거
del /q "%DIST_FOLDER%\license_generator_gui.py" >nul 2>&1
del /q "%DIST_FOLDER%\activate_developer_license.py" >nul 2>&1
del /q "%DIST_FOLDER%\generate_license.py" >nul 2>&1
del /q "%DIST_FOLDER%\view_license.py" >nul 2>&1
del /q "%DIST_FOLDER%\create_distribution.bat" >nul 2>&1
del /q "%DIST_FOLDER%\판매자용_배포가이드.md" >nul 2>&1

REM 개발 문서 제거
del /q "%DIST_FOLDER%\LICENSE_GUIDE.md" >nul 2>&1
del /q "%DIST_FOLDER%\대본_배경영상_매칭_개선_완성.md" >nul 2>&1
del /q "%DIST_FOLDER%\배경음악_자동_추가_시스템_완성.md" >nul 2>&1
del /q "%DIST_FOLDER%\MOBILE_*.md" >nul 2>&1
del /q "%DIST_FOLDER%\mobile_app_options.md" >nul 2>&1
del /q "%DIST_FOLDER%\tunnel_options.md" >nul 2>&1

REM 설정 스크립트 제거
del /q "%DIST_FOLDER%\setup_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\create_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\download_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\list_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\cleanup_*.py" >nul 2>&1

REM 모바일 관련 불필요 파일 제거
del /q "%DIST_FOLDER%\mobile_setup.py" >nul 2>&1
del /q "%DIST_FOLDER%\mobile_start.py" >nul 2>&1
del /q "%DIST_FOLDER%\start_mobile_*.py" >nul 2>&1
del /q "%DIST_FOLDER%\ngrok_setup.py" >nul 2>&1

REM 기타 불필요 파일
del /q "%DIST_FOLDER%\고정주소.py" >nul 2>&1
del /q "%DIST_FOLDER%\자동주소찾기.py" >nul 2>&1
del /q "%DIST_FOLDER%\백그라운드실행.py" >nul 2>&1
del /q "%DIST_FOLDER%\백그라운드실행.bat" >nul 2>&1
del /q "%DIST_FOLDER%\모바일*.bat" >nul 2>&1

REM 민감한 파일 제거
del /q "%DIST_FOLDER%\license.dat" >nul 2>&1
del /q "%DIST_FOLDER%\license_database.json" >nul 2>&1
del /q "%DIST_FOLDER%\token.pickle" >nul 2>&1
del /q "%DIST_FOLDER%\token_timer.pickle" >nul 2>&1
del /q "%DIST_FOLDER%\client_secrets.json" >nul 2>&1
del /q "%DIST_FOLDER%\config.toml" >nul 2>&1

REM 로그 및 임시 파일
del /q "%DIST_FOLDER%\*.log" >nul 2>&1
del /q "%DIST_FOLDER%\*.pid" >nul 2>&1
del /q "%DIST_FOLDER%\*.txt" >nul 2>&1
del /q "%DIST_FOLDER%\*.mp3" >nul 2>&1
del /q "%DIST_FOLDER%\*.mp4" >nul 2>&1

REM requirements.txt는 다시 복사 (위에서 삭제됨)
copy requirements.txt "%DIST_FOLDER%\" >nul

echo ✅ 정리 완료

echo.
echo [5/5] 배포 패키지 검증 중...

REM 필수 파일 확인
set MISSING=0

if not exist "%DIST_FOLDER%\setup_for_customer.bat" (
    echo ❌ setup_for_customer.bat 누락
    set MISSING=1
)
if not exist "%DIST_FOLDER%\프로그램실행.bat" (
    echo ❌ 프로그램실행.bat 누락
    set MISSING=1
)
if not exist "%DIST_FOLDER%\requirements.txt" (
    echo ❌ requirements.txt 누락
    set MISSING=1
)
if not exist "%DIST_FOLDER%\app" (
    echo ❌ app 폴더 누락
    set MISSING=1
)
if not exist "%DIST_FOLDER%\webui" (
    echo ❌ webui 폴더 누락
    set MISSING=1
)

if %MISSING%==1 (
    echo.
    echo ❌ 필수 파일이 누락되었습니다!
    pause
    exit /b 1
)

echo ✅ 모든 필수 파일 확인 완료

echo.
echo ========================================
echo    배포 패키지 생성 완료!
echo ========================================
echo.
echo 폴더: %DIST_FOLDER%
echo.
echo 포함된 파일:
echo - 프로그램 코드 (app, webui)
echo - 실행 스크립트 (setup, 실행, 외부접속)
echo - 사용 설명서 (README.md)
echo - 필수 설정 파일
echo.
echo 제외된 파일:
echo - 테스트 파일 (test_*.py, debug_*.py)
echo - 개발자 도구 (라이선스생성기 등)
echo - 민감한 정보 (license.dat, token 등)
echo - 개발 문서
echo.
echo 다음 단계:
echo 1. %DIST_FOLDER% 폴더를 ZIP으로 압축
echo 2. 고객에게 전달
echo 3. 라이선스 키 생성 (dist\라이선스생성기.exe)
echo.
echo 압축 방법:
echo - %DIST_FOLDER% 폴더 우클릭
echo - "보내기" → "압축(ZIP) 폴더"
echo - 파일명: %ZIP_NAME%
echo.
pause
