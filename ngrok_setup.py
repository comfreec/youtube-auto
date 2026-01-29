"""
ngrok 자동 설치 및 설정
"""
import os
import sys
import subprocess
import requests
import zipfile
import platform

def download_ngrok():
    """ngrok 다운로드"""
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    if system == "windows":
        if "64" in arch or "amd64" in arch:
            url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
        else:
            url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-386.zip"
    elif system == "darwin":  # macOS
        url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-amd64.zip"
    else:  # Linux
        url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip"
    
    print(f"📥 ngrok 다운로드 중... ({system})")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        with open("ngrok.zip", "wb") as f:
            f.write(response.content)
        
        # 압축 해제
        with zipfile.ZipFile("ngrok.zip", "r") as zip_ref:
            zip_ref.extractall(".")
        
        # 실행 권한 부여 (Unix 계열)
        if system != "windows":
            os.chmod("ngrok", 0o755)
        
        # 임시 파일 삭제
        os.remove("ngrok.zip")
        
        print("✅ ngrok 다운로드 완료!")
        return True
        
    except Exception as e:
        print(f"❌ ngrok 다운로드 실패: {e}")
        return False

def setup_ngrok():
    """ngrok 설정"""
    print("🔧 ngrok 설정")
    print("=" * 30)
    
    # ngrok 설치 확인
    try:
        result = subprocess.run(["ngrok", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ngrok이 이미 설치되어 있습니다.")
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        print("📥 ngrok을 다운로드합니다...")
        if not download_ngrok():
            return False
    
    # 인증 토큰 설정
    print("\n🔑 ngrok 인증 토큰이 필요합니다.")
    print("1. https://ngrok.com 에서 무료 회원가입")
    print("2. Dashboard에서 인증 토큰 복사")
    print("3. 아래에 붙여넣기")
    
    token = input("\n인증 토큰을 입력하세요: ").strip()
    
    if not token:
        print("❌ 토큰이 입력되지 않았습니다.")
        return False
    
    try:
        # 토큰 설정
        result = subprocess.run(["ngrok", "config", "add-authtoken", token], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ ngrok 설정 완료!")
            return True
        else:
            print(f"❌ 토큰 설정 실패: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ ngrok 설정 실패: {e}")
        return False

def main():
    print("🌐 ngrok 자동 설치 및 설정")
    print("=" * 40)
    
    if setup_ngrok():
        print("\n🎉 설정 완료!")
        print("이제 '외부접속.bat'을 실행하여 밖에서 접속할 수 있습니다.")
    else:
        print("\n❌ 설정 실패")
        print("수동으로 설정해주세요:")
        print("1. https://ngrok.com 에서 ngrok 다운로드")
        print("2. ngrok config add-authtoken [토큰]")

if __name__ == "__main__":
    main()