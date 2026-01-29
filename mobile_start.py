"""
모바일 접속 - 초간단 버전
1. 이 파일 실행
2. 나오는 주소로 모바일에서 접속
3. 끝!
"""
import os
import sys
import socket
import subprocess
import time

def get_ip():
    """컴퓨터 IP 주소 가져오기"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def main():
    print("🎬 AI 영상 생성 모바일 접속")
    print("=" * 40)
    
    # IP 주소 확인
    ip = get_ip()
    port = 8501
    
    print(f"\n📱 모바일에서 이 주소로 접속하세요:")
    print(f"   http://{ip}:{port}")
    print(f"\n💡 같은 WiFi에 연결되어 있어야 합니다!")
    print(f"\n🚀 서버 시작 중...")
    
    # 기존 Main.py를 모바일 최적화해서 실행
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "webui/Main.py",
            "--server.port", str(port),
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print(f"\n\n⏹️  서버가 중지되었습니다.")

if __name__ == "__main__":
    main()