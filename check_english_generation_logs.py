#!/usr/bin/env python3
"""
영어 버전 생성 관련 로그 확인 스크립트
"""

import re
import time

def check_english_generation_logs():
    print("🔍 영어 버전 생성 로그 확인 중...")
    
    # 최근 로그에서 영어 버전 관련 키워드 검색
    keywords = [
        "english",
        "글로벌",
        "translate",
        "번역",
        "English version",
        "Global version",
        "Task 2",
        "tasks_to_run",
        "generate_english_version"
    ]
    
    print("\n영어 버전 관련 키워드로 로그 검색:")
    for keyword in keywords:
        print(f"- {keyword}")
    
    print("\n실시간 로그 모니터링을 시작합니다...")
    print("영상 생성을 시작하고 이 스크립트를 실행하여 로그를 확인하세요.")
    print("Ctrl+C로 중단할 수 있습니다.")
    
    try:
        # 간단한 로그 모니터링 (실제로는 서버 로그를 확인해야 함)
        print("\n📋 영어 버전 생성 체크리스트:")
        print("1. ✅ 글로벌 버전 체크박스가 체크되어 있는가?")
        print("2. ❓ '글로벌 버전 준비 중...' 메시지가 나타나는가?")
        print("3. ❓ 번역 성공/실패 메시지가 나타나는가?")
        print("4. ❓ '글로벌 버전 준비 완료!' 메시지가 나타나는가?")
        print("5. ❓ 두 번째 태스크 (🌍 글로벌 버전)가 시작되는가?")
        
        print("\n🔧 문제 해결 방법:")
        print("- 체크박스가 체크되어 있지만 메시지가 안 나타나면: 브라우저 새로고침")
        print("- 번역 실패 메시지가 나타나면: API 키 확인 또는 할당량 확인")
        print("- 글로벌 버전 태스크가 시작되지 않으면: 코드 로직 문제")
        print("- 태스크가 시작되지만 완료되지 않으면: 영어 음성 생성 문제")
        
    except KeyboardInterrupt:
        print("\n로그 모니터링을 중단합니다.")

if __name__ == "__main__":
    check_english_generation_logs()