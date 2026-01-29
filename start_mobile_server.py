"""
모바일 API 서버 실행 스크립트
컴퓨터에서 실행하여 모바일 클라이언트의 요청을 처리
"""
import os
import sys
import socket
import threading
import time
from loguru import logger

# 프로젝트 루트 경로 추가
root_dir = os.path.dirname(os.path.realpath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

def get_local_ip():
    """로컬 IP 주소 가져오기"""
    try:
        # 외부 서버에 연결을 시도하여 로컬 IP 확인
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def check_port_available(port):
    """포트 사용 가능 여부 확인"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", port))
        s.close()
        return True
    except OSError:
        return False

def main():
    """메인 함수"""
    print("=" * 60)
    print("🎬 AI 영상 생성 모바일 API 서버")
    print("=" * 60)
    
    # 포트 설정
    port = 8001
    if not check_port_available(port):
        print(f"❌ 포트 {port}가 이미 사용 중입니다.")
        for new_port in range(8002, 8010):
            if check_port_available(new_port):
                port = new_port
                print(f"✅ 대신 포트 {port}를 사용합니다.")
                break
        else:
            print("❌ 사용 가능한 포트를 찾을 수 없습니다.")
            return
    
    # IP 주소 확인
    local_ip = get_local_ip()
    
    print(f"\n📡 서버 정보:")
    print(f"   로컬 주소: http://127.0.0.1:{port}")
    print(f"   네트워크 주소: http://{local_ip}:{port}")
    print(f"   포트: {port}")
    
    print(f"\n📱 모바일 연결 방법:")
    print(f"   1. 모바일과 컴퓨터가 같은 WiFi에 연결되어 있는지 확인")
    print(f"   2. 모바일에서 브라우저로 접속: http://{local_ip}:{port}")
    print(f"   3. 또는 모바일 클라이언트 앱에서 서버 주소 입력: http://{local_ip}:{port}")
    
    print(f"\n🔧 방화벽 설정:")
    print(f"   Windows: 방화벽에서 포트 {port} 허용 필요")
    print(f"   macOS: 시스템 환경설정 > 보안 및 개인정보보호 > 방화벽")
    
    print(f"\n🚀 서버 시작 중...")
    
    try:
        # API 서버 시작
        from webui.mobile_api_server import start_api_server
        start_api_server(host="0.0.0.0", port=port)
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️  서버가 중지되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 서버 시작 실패: {e}")
        logger.error(f"서버 시작 실패: {e}")

if __name__ == "__main__":
    main()