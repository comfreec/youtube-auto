"""
ngrok 주소 자동 업데이트 시스템
주소가 바뀌어도 모바일에서 자동으로 새 주소 찾기
"""
import os
import sys
import subprocess
import time
import requests
import json
import threading
from datetime import datetime

class NgrokAddressManager:
    """ngrok 주소 관리자"""
    
    def __init__(self):
        self.current_url = None
        self.address_file = "current_ngrok_address.txt"
        self.qr_file = "ngrok_qr.png"
    
    def get_ngrok_url(self):
        """현재 ngrok URL 가져오기"""
        try:
            response = requests.get("http://localhost:4040/api/tunnels")
            tunnels = response.json()["tunnels"]
            if tunnels:
                public_url = tunnels[0]["public_url"]
                return public_url
        except Exception as e:
            print(f"ngrok URL 가져오기 실패: {e}")
            return None
    
    def save_address(self, url):
        """주소를 파일에 저장"""
        try:
            with open(self.address_file, 'w', encoding='utf-8') as f:
                f.write(url)
            print(f"✅ 주소 저장됨: {url}")
            
            # QR 코드도 생성
            self.generate_qr_code(url)
            
        except Exception as e:
            print(f"주소 저장 실패: {e}")
    
    def generate_qr_code(self, url):
        """QR 코드 생성"""
        try:
            import qrcode
            from PIL import Image
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(self.qr_file)
            print(f"📱 QR 코드 생성됨: {self.qr_file}")
            
        except ImportError:
            print("⚠️ QR 코드 생성을 위해 qrcode 패키지를 설치하세요: pip install qrcode[pil]")
        except Exception as e:
            print(f"QR 코드 생성 실패: {e}")
    
    def monitor_address_changes(self):
        """주소 변경 모니터링"""
        print("🔍 ngrok 주소 모니터링 시작...")
        
        while True:
            try:
                new_url = self.get_ngrok_url()
                
                if new_url and new_url != self.current_url:
                    self.current_url = new_url
                    self.save_address(new_url)
                    
                    print(f"\n🎉 새로운 접속 주소:")
                    print(f"   {new_url}")
                    print(f"📱 모바일에서 이 주소로 접속하세요!")
                    print(f"📄 주소는 {self.address_file} 파일에도 저장됩니다.")
                    
                    # 알림 표시
                    self.show_notification(new_url)
                
                time.sleep(5)  # 5초마다 확인
                
            except Exception as e:
                print(f"모니터링 오류: {e}")
                time.sleep(10)
    
    def show_notification(self, url):
        """시스템 알림 표시"""
        try:
            if os.name == 'nt':  # Windows
                import win10toast
                toaster = win10toast.ToastNotifier()
                toaster.show_toast(
                    "AI 영상 생성기",
                    f"새로운 접속 주소: {url}",
                    duration=10
                )
        except ImportError:
            pass
        except Exception as e:
            print(f"알림 표시 실패: {e}")

def start_with_address_monitoring():
    """주소 모니터링과 함께 서버 시작"""
    print("🚀 고정 주소 시스템으로 서버 시작")
    print("=" * 50)
    
    # ngrok 주소 관리자 생성
    manager = NgrokAddressManager()
    
    # 서버 시작
    def start_server():
        from 외부접속 import start_streamlit_server
        start_streamlit_server()
    
    # ngrok 시작
    def start_ngrok():
        try:
            subprocess.Popen(["ngrok", "http", "8501"], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
            time.sleep(3)  # ngrok 시작 대기
        except Exception as e:
            print(f"ngrok 시작 실패: {e}")
    
    # 백그라운드에서 서버 시작
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # ngrok 시작
    ngrok_thread = threading.Thread(target=start_ngrok, daemon=True)
    ngrok_thread.start()
    
    # 주소 모니터링 시작 (메인 스레드)
    time.sleep(5)  # 서버들이 시작될 때까지 대기
    manager.monitor_address_changes()

def get_current_address():
    """현재 저장된 주소 가져오기"""
    try:
        with open("current_ngrok_address.txt", 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "주소 파일이 없습니다. 서버를 먼저 시작하세요."
    except Exception as e:
        return f"주소 읽기 실패: {e}"

def main():
    """메인 함수"""
    print("📱 AI 영상 생성기 - 고정 주소 시스템")
    print("=" * 40)
    
    print("\n선택하세요:")
    print("1. 서버 시작 (주소 모니터링 포함)")
    print("2. 현재 주소 확인")
    print("3. QR 코드 보기")
    
    try:
        choice = input("\n선택 (1-3): ").strip()
    except KeyboardInterrupt:
        print("\n\n⏹️ 취소되었습니다.")
        return
    
    if choice == "1":
        start_with_address_monitoring()
    elif choice == "2":
        address = get_current_address()
        print(f"\n📱 현재 접속 주소:")
        print(f"   {address}")
    elif choice == "3":
        if os.path.exists("ngrok_qr.png"):
            print(f"\n📱 QR 코드: ngrok_qr.png")
            print("파일 탐색기에서 열어서 모바일로 스캔하세요!")
            
            # Windows에서 자동으로 이미지 열기
            if os.name == 'nt':
                os.startfile("ngrok_qr.png")
        else:
            print("❌ QR 코드 파일이 없습니다. 서버를 먼저 시작하세요.")
    else:
        print("❌ 잘못된 선택입니다.")

if __name__ == "__main__":
    main()