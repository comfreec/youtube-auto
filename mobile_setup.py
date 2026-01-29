"""
모바일 시스템 통합 설정 및 실행 스크립트
서버와 클라이언트를 동시에 실행하고 설정을 도와주는 스크립트
"""
import os
import sys
import socket
import subprocess
import threading
import time
import webbrowser
from loguru import logger

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

def check_port_available(port):
    """포트 사용 가능 여부 확인"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", port))
        s.close()
        return True
    except OSError:
        return False

def find_available_port(start_port, end_port):
    """사용 가능한 포트 찾기"""
    for port in range(start_port, end_port):
        if check_port_available(port):
            return port
    return None

def run_api_server(port):
    """API 서버 실행"""
    try:
        logger.info(f"API 서버 시작: 포트 {port}")
        subprocess.run([
            sys.executable, "start_mobile_server.py"
        ], env={**os.environ, "API_PORT": str(port)})
    except Exception as e:
        logger.error(f"API 서버 실행 실패: {e}")

def run_client_app(port, api_port):
    """클라이언트 앱 실행"""
    try:
        logger.info(f"클라이언트 앱 시작: 포트 {port}")
        
        # 환경 변수로 API 서버 주소 전달
        env = os.environ.copy()
        env["DEFAULT_API_SERVER"] = f"http://localhost:{api_port}"
        
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "webui/mobile_client.py",
            "--server.port", str(port),
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--theme.base", "dark"
        ], env=env)
    except Exception as e:
        logger.error(f"클라이언트 앱 실행 실패: {e}")

def generate_qr_code(url):
    """QR 코드 생성 (선택사항)"""
    try:
        import qrcode
        from io import BytesIO
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 임시 파일로 저장
        qr_path = "mobile_qr.png"
        img.save(qr_path)
        return qr_path
    except ImportError:
        return None
    except Exception as e:
        logger.error(f"QR 코드 생성 실패: {e}")
        return None

def show_setup_instructions(local_ip, api_port, client_port):
    """설정 안내 출력"""
    print("\n" + "=" * 80)
    print("🎬 AI 영상 생성 모바일 시스템 설정 완료!")
    print("=" * 80)
    
    print(f"\n📡 API 서버 (컴퓨터에서 영상 처리):")
    print(f"   주소: http://{local_ip}:{api_port}")
    print(f"   상태: http://{local_ip}:{api_port}/health")
    
    print(f"\n📱 모바일 클라이언트 (모바일에서 접속):")
    print(f"   주소: http://{local_ip}:{client_port}")
    
    print(f"\n🔧 모바일 연결 방법:")
    print(f"   1. 모바일과 컴퓨터가 같은 WiFi 네트워크에 연결되어 있는지 확인")
    print(f"   2. 모바일 브라우저에서 접속: http://{local_ip}:{client_port}")
    print(f"   3. 클라이언트에서 API 서버 주소 설정: http://{local_ip}:{api_port}")
    print(f"   4. 연결 버튼을 클릭하여 서버 연결 확인")
    
    print(f"\n⚠️  방화벽 설정 (필요시):")
    print(f"   Windows: 제어판 > 시스템 및 보안 > Windows Defender 방화벽")
    print(f"   포트 {api_port}, {client_port} 인바운드 규칙 허용")
    
    print(f"\n🌐 네트워크 문제 해결:")
    print(f"   - 컴퓨터 IP: {local_ip}")
    print(f"   - 모바일에서 ping 테스트: ping {local_ip}")
    print(f"   - 라우터 설정에서 AP 격리 비활성화 확인")
    
    # QR 코드 생성 시도
    client_url = f"http://{local_ip}:{client_port}"
    qr_path = generate_qr_code(client_url)
    if qr_path:
        print(f"\n📱 QR 코드로 빠른 접속:")
        print(f"   QR 코드 파일: {qr_path}")
        print(f"   모바일에서 QR 코드를 스캔하여 바로 접속하세요!")
    
    print(f"\n🚀 사용법:")
    print(f"   1. 모바일에서 클라이언트 접속")
    print(f"   2. 서버 연결 설정")
    print(f"   3. 영상 주제 입력 후 생성 버튼 클릭")
    print(f"   4. 모바일은 가벼운 UI만 담당, 실제 처리는 컴퓨터에서!")
    
    print("\n" + "=" * 80)

def main():
    """메인 함수"""
    print("🎬 AI 영상 생성 모바일 시스템 설정")
    print("=" * 50)
    
    # IP 주소 확인
    local_ip = get_local_ip()
    print(f"📡 컴퓨터 IP 주소: {local_ip}")
    
    # 포트 확인 및 할당
    api_port = find_available_port(8001, 8010)
    client_port = find_available_port(8501, 8510)
    
    if not api_port or not client_port:
        print("❌ 사용 가능한 포트를 찾을 수 없습니다.")
        return
    
    print(f"🔌 API 서버 포트: {api_port}")
    print(f"🔌 클라이언트 포트: {client_port}")
    
    # 실행 방식 선택
    print(f"\n실행 방식을 선택하세요:")
    print(f"1. 통합 실행 (서버 + 클라이언트 동시 실행)")
    print(f"2. API 서버만 실행")
    print(f"3. 클라이언트만 실행")
    print(f"4. 설정 정보만 표시")
    
    try:
        choice = input("\n선택 (1-4): ").strip()
    except KeyboardInterrupt:
        print("\n\n⏹️  설정이 취소되었습니다.")
        return
    
    if choice == "1":
        # 통합 실행
        print(f"\n🚀 통합 실행 시작...")
        
        # API 서버를 별도 스레드에서 실행
        api_thread = threading.Thread(
            target=run_api_server,
            args=(api_port,),
            daemon=True
        )
        api_thread.start()
        
        # 서버 시작 대기
        print("⏳ API 서버 시작 대기 중...")
        time.sleep(3)
        
        # 설정 안내 표시
        show_setup_instructions(local_ip, api_port, client_port)
        
        # 클라이언트 실행 (메인 스레드)
        print(f"\n🚀 클라이언트 앱 시작...")
        run_client_app(client_port, api_port)
        
    elif choice == "2":
        # API 서버만 실행
        show_setup_instructions(local_ip, api_port, client_port)
        print(f"\n🚀 API 서버만 실행...")
        run_api_server(api_port)
        
    elif choice == "3":
        # 클라이언트만 실행
        show_setup_instructions(local_ip, api_port, client_port)
        print(f"\n🚀 클라이언트만 실행...")
        run_client_app(client_port, api_port)
        
    elif choice == "4":
        # 설정 정보만 표시
        show_setup_instructions(local_ip, api_port, client_port)
        
    else:
        print("❌ 잘못된 선택입니다.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⏹️  프로그램이 종료되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 오류 발생: {e}")
        logger.error(f"프로그램 오류: {e}")