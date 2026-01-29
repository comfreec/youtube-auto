"""
모바일 클라이언트 실행 스크립트
모바일 브라우저에서 접속할 수 있는 가벼운 웹앱 실행
"""
import os
import sys
import socket
import streamlit.web.cli as stcli

# 프로젝트 루트 경로 추가
root_dir = os.path.dirname(os.path.realpath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

def get_local_ip():
    """로컬 IP 주소 가져오기"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def main():
    """메인 함수"""
    print("=" * 60)
    print("📱 AI 영상 생성 모바일 클라이언트")
    print("=" * 60)
    
    local_ip = get_local_ip()
    client_port = 8501
    
    print(f"\n📱 모바일 클라이언트 정보:")
    print(f"   로컬 주소: http://127.0.0.1:{client_port}")
    print(f"   모바일 접속 주소: http://{local_ip}:{client_port}")
    
    print(f"\n🔧 사용 방법:")
    print(f"   1. 먼저 API 서버를 실행하세요: python start_mobile_server.py")
    print(f"   2. 모바일에서 브라우저로 접속: http://{local_ip}:{client_port}")
    print(f"   3. 클라이언트에서 API 서버 주소를 설정하세요")
    
    print(f"\n🚀 클라이언트 시작 중...")
    
    # Streamlit 앱 실행
    sys.argv = [
        "streamlit",
        "run",
        "webui/mobile_client.py",
        "--server.port", str(client_port),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--theme.base", "dark"
    ]
    
    stcli.main()

if __name__ == "__main__":
    main()