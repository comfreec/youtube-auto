"""
백그라운드에서 모바일 서버 실행
창을 닫아도 계속 실행됨
"""
import os
import sys
import subprocess
import time
import threading
from datetime import datetime

def run_in_background():
    """백그라운드에서 서버 실행"""
    print("🚀 백그라운드 모바일 서버 시작")
    print("=" * 40)
    
    # 로그 파일 설정
    log_file = "mobile_server.log"
    
    try:
        # 외부접속.py를 백그라운드에서 실행
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] 모바일 서버 시작\n")
            
            process = subprocess.Popen([
                sys.executable, "외부접속.py"
            ], stdout=f, stderr=f, creationflags=subprocess.CREATE_NO_WINDOW)
            
            print(f"✅ 백그라운드 서버 시작됨 (PID: {process.pid})")
            print(f"📄 로그 파일: {log_file}")
            print(f"📱 모바일에서 접속 가능!")
            
            # PID 파일에 저장
            with open("mobile_server.pid", 'w') as pid_file:
                pid_file.write(str(process.pid))
            
            return process.pid
            
    except Exception as e:
        print(f"❌ 백그라운드 실행 실패: {e}")
        return None

def stop_background_server():
    """백그라운드 서버 중지"""
    try:
        with open("mobile_server.pid", 'r') as f:
            pid = int(f.read().strip())
        
        # 프로세스 종료
        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
        
        # PID 파일 삭제
        os.remove("mobile_server.pid")
        
        print(f"✅ 백그라운드 서버 중지됨 (PID: {pid})")
        
    except FileNotFoundError:
        print("❌ 실행 중인 백그라운드 서버가 없습니다.")
    except Exception as e:
        print(f"❌ 서버 중지 실패: {e}")

def check_server_status():
    """서버 상태 확인"""
    try:
        with open("mobile_server.pid", 'r') as f:
            pid = int(f.read().strip())
        
        # 프로세스 존재 확인
        result = subprocess.run(f"tasklist /FI \"PID eq {pid}\"", 
                              shell=True, capture_output=True, text=True)
        
        if str(pid) in result.stdout:
            print(f"🟢 백그라운드 서버 실행 중 (PID: {pid})")
            
            # 로그 파일 확인
            if os.path.exists("mobile_server.log"):
                print(f"📄 로그 파일: mobile_server.log")
                
                # 최근 로그 몇 줄 표시
                with open("mobile_server.log", 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print("📋 최근 로그:")
                        for line in lines[-5:]:  # 마지막 5줄
                            print(f"   {line.strip()}")
            
            return True
        else:
            print("🔴 백그라운드 서버가 실행되지 않음")
            return False
            
    except FileNotFoundError:
        print("🔴 백그라운드 서버가 실행되지 않음")
        return False
    except Exception as e:
        print(f"❌ 상태 확인 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("🖥️ AI 영상 생성 백그라운드 서버 관리")
    print("=" * 45)
    
    print("\n선택하세요:")
    print("1. 백그라운드에서 서버 시작")
    print("2. 서버 상태 확인")
    print("3. 서버 중지")
    print("4. 로그 보기")
    
    try:
        choice = input("\n선택 (1-4): ").strip()
    except KeyboardInterrupt:
        print("\n\n⏹️ 취소되었습니다.")
        return
    
    if choice == "1":
        if check_server_status():
            print("⚠️ 이미 서버가 실행 중입니다.")
        else:
            pid = run_in_background()
            if pid:
                print(f"\n🎉 백그라운드 서버 시작 완료!")
                print(f"💡 이제 창을 닫아도 모바일에서 계속 사용 가능합니다.")
                print(f"🛑 서버 중지: python 백그라운드실행.py (선택 3번)")
                
    elif choice == "2":
        check_server_status()
        
    elif choice == "3":
        stop_background_server()
        
    elif choice == "4":
        if os.path.exists("mobile_server.log"):
            print("\n📄 서버 로그:")
            print("-" * 40)
            with open("mobile_server.log", 'r', encoding='utf-8') as f:
                print(f.read())
        else:
            print("❌ 로그 파일이 없습니다.")
            
    else:
        print("❌ 잘못된 선택입니다.")

if __name__ == "__main__":
    main()