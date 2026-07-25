@echo off
chcp 65001 > nul
echo ============================================
echo 폴더 권한 수정 중...
echo ============================================

REM 현재 폴더의 소유권을 현재 사용자에게 변경
takeown /f "C:\Users\dev\youtube-auto" /r /d y

REM 현재 사용자에게 모든 권한 부여
icacls "C:\Users\dev\youtube-auto" /grant "%USERNAME%:(F)" /t /c

echo ============================================
echo 완료! 이제 서버실행.bat을 실행하세요.
echo ============================================
pause
