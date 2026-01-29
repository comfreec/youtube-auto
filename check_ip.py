"""
컴퓨터 IP 주소 확인 스크립트
"""
import socket
import subprocess
import platform

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

def get_all_ips():
    """모든 네트워크 인터페이스 IP 확인"""
    system = platform.system()
    
    if system == "Windows":
        try:
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, shell=True)
            return result.stdout
        except:
            return "ipconfig 실행 실패"
    else:
        try:
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            return result.stdout
        except:
            return "ifconfig 실행 실패"

def main():
    print("=" * 60)
    print("🌐 컴퓨터 IP 주소 확인")
    print("=" * 60)
    
    # 메인 IP 주소
    local_ip = get_local_ip()
    print(f"\n📡 메인 IP 주소: {local_ip}")
    
    # 모바일 접속 주소들
    print(f"\n📱 모바일 클라이언트 접속 주소:")
    print(f"   http://{local_ip}:8501")
    
    print(f"\n🔧 API 서버 주소 (클라이언트에서 설정할 주소):")
    print(f"   http://{local_ip}:8001")
    
    print(f"\n💡 사용 방법:")
    print(f"   1. 모바일과 컴퓨터를 같은 WiFi에 연결")
    print(f"   2. 모바일 브라우저에서 접속: http://{local_ip}:8501")
    print(f"   3. 클라이언트에서 서버 주소 설정: http://{local_ip}:8001")
    
    # 상세 네트워크 정보
    print(f"\n🔍 상세 네트워크 정보:")
    print("-" * 40)
    network_info = get_all_ips()
    
    # Windows에서 IPv4 주소만 추출
    if platform.system() == "Windows":
        lines = network_info.split('\n')
        for line in lines:
            if 'IPv4' in line and '192.168' in line:
                ip = line.split(':')[-1].strip()
                print(f"   WiFi IP: {ip}")
                print(f"   모바일 접속: http://{ip}:8501")
    
    print(f"\n⚠️  주의사항:")
    print(f"   - 모바일과 컴퓨터가 같은 WiFi 네트워크에 있어야 함")
    print(f"   - 방화벽에서 포트 8001, 8501 허용 필요")
    print(f"   - 공유기 설정에서 AP 격리 비활성화 필요")

if __name__ == "__main__":
    main()