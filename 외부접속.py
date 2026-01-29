"""
밖에서 접속 가능한 모바일 서버
ngrok 또는 cloudflare tunnel 사용
"""
import os
import sys
import subprocess
import time
import threading
import socket

def get_local_ip():
    """로컬 IP 확인"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def start_streamlit_server():
    """Streamlit 서버 시작"""
    print("🚀 Streamlit 서버 시작 중...")
    
    # 정적 파일 서버도 함께 시작
    try:
        from webui.static_server import start_static_server_thread
        start_static_server_thread()
        print("📁 PWA 정적 파일 서버 시작됨")
    except Exception as e:
        print(f"⚠️ 정적 파일 서버 시작 실패: {e}")
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "webui/Main.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"
    ])

def start_ngrok():
    """ngrok으로 터널링"""
    print("🌐 ngrok 터널 생성 중...")
    
    # ngrok이 설치되어 있는지 확인
    try:
        result = subprocess.run(["ngrok", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ ngrok이 설치되지 않았습니다.")
            print("💡 설치 방법:")
            print("   1. https://ngrok.com 에서 회원가입")
            print("   2. ngrok 다운로드 및 설치")
            print("   3. ngrok config add-authtoken [토큰]")
            return False
    except FileNotFoundError:
        print("❌ ngrok이 설치되지 않았습니다.")
        print("💡 설치 방법:")
        print("   1. https://ngrok.com 에서 회원가입")
        print("   2. ngrok 다운로드 및 설치")
        print("   3. ngrok config add-authtoken [토큰]")
        return False
    
    # ngrok 실행
    try:
        subprocess.Popen(["ngrok", "http", "8501"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)
        
        # ngrok URL 확인
        try:
            import requests
            response = requests.get("http://localhost:4040/api/tunnels")
            tunnels = response.json()["tunnels"]
            if tunnels:
                public_url = tunnels[0]["public_url"]
                print(f"✅ 외부 접속 주소: {public_url}")
                print(f"📱 모바일에서 이 주소로 접속하세요!")
                return True
        except:
            print("⚠️ ngrok URL을 자동으로 가져올 수 없습니다.")
            print("💡 http://localhost:4040 에서 확인하세요.")
            return True
            
    except Exception as e:
        print(f"❌ ngrok 실행 실패: {e}")
        return False

def start_cloudflare_tunnel():
    """Cloudflare Tunnel 사용"""
    print("🌐 Cloudflare Tunnel 생성 중...")
    
    # cloudflared 확인
    try:
        result = subprocess.run(["cloudflared", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ cloudflared가 설치되지 않았습니다.")
            print("💡 설치 방법:")
            print("   1. https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
            print("   2. cloudflared 다운로드 및 설치")
            return False
    except FileNotFoundError:
        print("❌ cloudflared가 설치되지 않았습니다.")
        return False
    
    # Cloudflare Tunnel 실행
    try:
        process = subprocess.Popen([
            "cloudflared", "tunnel", "--url", "http://localhost:8501"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # URL 찾기
        time.sleep(5)
        for line in process.stderr:
            if "trycloudflare.com" in line:
                url = line.split()[-1]
                print(f"✅ 외부 접속 주소: {url}")
                print(f"📱 모바일에서 이 주소로 접속하세요!")
                break
        
        return True
        
    except Exception as e:
        print(f"❌ Cloudflare Tunnel 실행 실패: {e}")
        return False

def main():
    print("🌍 밖에서 접속 가능한 AI 영상 생성 서버")
    print("=" * 50)
    
    print("\n터널링 방법을 선택하세요:")
    print("1. ngrok (추천)")
    print("2. Cloudflare Tunnel")
    print("3. 로컬만 (같은 WiFi)")
    
    try:
        choice = input("\n선택 (1-3): ").strip()
    except KeyboardInterrupt:
        print("\n\n⏹️ 취소되었습니다.")
        return
    
    # Streamlit 서버를 별도 스레드에서 시작
    server_thread = threading.Thread(target=start_streamlit_server, daemon=True)
    server_thread.start()
    
    time.sleep(3)  # 서버 시작 대기
    
    if choice == "1":
        if start_ngrok():
            print("\n🎉 설정 완료! 위의 주소로 접속하세요.")
        else:
            print("\n❌ ngrok 설정 실패")
            return
            
    elif choice == "2":
        if start_cloudflare_tunnel():
            print("\n🎉 설정 완료! 위의 주소로 접속하세요.")
        else:
            print("\n❌ Cloudflare Tunnel 설정 실패")
            return
            
    elif choice == "3":
        local_ip = get_local_ip()
        print(f"\n📱 로컬 접속 주소: http://{local_ip}:8501")
        print("⚠️ 같은 WiFi에서만 접속 가능합니다.")
        
    else:
        print("❌ 잘못된 선택입니다.")
        return
    
    print("\n" + "=" * 50)
    print("🔥 서버가 실행 중입니다.")
    print("⏹️ 종료하려면 Ctrl+C를 누르세요.")
    print("=" * 50)
    
    try:
        # 메인 스레드에서 대기
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n\n⏹️ 서버가 종료되었습니다.")

if __name__ == "__main__":
    main()