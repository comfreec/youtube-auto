#!/usr/bin/env python3
"""
영상 생성 재시작 및 자막 문제 해결
"""

import os
import sys
import time
import glob
import shutil

def restart_streamlit_server():
    """Streamlit 서버 재시작"""
    print("🔄 서버 재시작 중...")
    
    # 기존 프로세스 종료 시도
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'streamlit' in proc.info['name'].lower():
                    proc.terminate()
                    print(f"✅ Streamlit 프로세스 종료: PID {proc.info['pid']}")
            except:
                pass
    except ImportError:
        print("⚠️ psutil 모듈이 없어 수동으로 프로세스를 확인하세요")
    
    time.sleep(2)
    
    # 새 서버 시작
    print("🚀 새 서버 시작...")
    os.system("streamlit run webui/Main.py --server.port 8501 --server.address 0.0.0.0")

def clear_all_temp_data():
    """모든 임시 데이터 정리"""
    print("🧹 전체 임시 데이터 정리 중...")
    
    temp_paths = [
        "storage/temp",
        "storage/cache", 
        "storage/tasks/*/temp*",
        "storage/tasks/*/audio_*.wav",
        "storage/tasks/*/*.srt"
    ]
    
    for pattern in temp_paths:
        try:
            files = glob.glob(pattern)
            for file_path in files:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"🗑️ 파일 삭제: {file_path}")
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    print(f"📁 폴더 삭제: {file_path}")
        except Exception as e:
            print(f"⚠️ 정리 중 오류: {e}")
    
    print("✅ 임시 데이터 정리 완료")

def check_system_resources():
    """시스템 리소스 확인"""
    print("💻 시스템 리소스 확인...")
    
    # 디스크 공간 확인
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        free_gb = free // (1024**3)
        print(f"💾 사용 가능한 디스크 공간: {free_gb}GB")
        
        if free_gb < 2:
            print("⚠️ 경고: 디스크 공간이 부족합니다 (최소 2GB 권장)")
        else:
            print("✅ 디스크 공간 충분")
    except:
        print("⚠️ 디스크 공간 확인 실패")
    
    # 메모리 확인
    try:
        import psutil
        memory = psutil.virtual_memory()
        available_gb = memory.available // (1024**3)
        print(f"🧠 사용 가능한 메모리: {available_gb}GB")
        
        if available_gb < 2:
            print("⚠️ 경고: 메모리가 부족합니다 (최소 2GB 권장)")
        else:
            print("✅ 메모리 충분")
    except:
        print("⚠️ 메모리 확인 실패")

if __name__ == "__main__":
    print("🔧 영상 생성 재시작 도구")
    print("=" * 50)
    
    # 1. 시스템 리소스 확인
    check_system_resources()
    
    print("\n" + "=" * 50)
    
    # 2. 임시 데이터 정리
    clear_all_temp_data()
    
    print("\n" + "=" * 50)
    
    # 3. 사용자 안내
    print("🎯 다음 단계:")
    print("1. 웹 브라우저에서 http://192.168.25.14:8501 접속")
    print("2. 페이지 새로고침 (F5)")
    print("3. 더 짧은 대본으로 테스트 (1-2문장)")
    print("4. 자막 생성을 비활성화하고 테스트")
    
    print("\n💡 자막 문제 해결 팁:")
    print("- 영상 생성 시 '자막 생성' 체크박스를 해제")
    print("- 더 간단한 내용으로 먼저 테스트")
    print("- 인터넷 연결 상태 확인")
    
    print("\n🚀 준비 완료! 이제 영상 생성을 다시 시도하세요.")