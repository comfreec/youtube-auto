#!/usr/bin/env python3
"""
현재 음성 속도 설정 확인 스크립트
"""

def check_current_speed_settings():
    print("🔍 현재 음성 속도 설정 확인 중...")
    
    # 1. Main.py에서 기본 설정 확인
    print("\n1. Main.py 기본 설정 확인...")
    try:
        with open("webui/Main.py", "r", encoding="utf-8") as f:
            main_content = f.read()
        
        # 쇼츠 최적화 기본 설정
        if 'st.session_state["settings_korean_speed_boost"] = 1.3' in main_content:
            print("✅ 기본 한국어 속도: 1.3배속")
        elif 'st.session_state["settings_korean_speed_boost"] = 1.4' in main_content:
            print("❌ 기본 한국어 속도: 1.4배속 (수정 필요)")
        else:
            print("❓ 기본 한국어 속도 설정을 찾을 수 없음")
            
        if 'st.session_state["settings_english_speed_boost"] = 1.1' in main_content:
            print("✅ 기본 영어 속도: 1.1배속")
        elif 'st.session_state["settings_english_speed_boost"] = 1.2' in main_content:
            print("❌ 기본 영어 속도: 1.2배속 (수정 필요)")
        else:
            print("❓ 기본 영어 속도 설정을 찾을 수 없음")
            
        # 쇼츠 최적화 버튼 설정
        if 'st.session_state["settings_korean_speed_boost"] = 1.3  # 한국어 1.3배속' in main_content:
            print("✅ 쇼츠 최적화 한국어: 1.3배속")
        else:
            print("❌ 쇼츠 최적화 한국어 설정 확인 필요")
            
        if 'st.session_state["settings_english_speed_boost"] = 1.1  # 영어 1.1배속' in main_content:
            print("✅ 쇼츠 최적화 영어: 1.1배속")
        else:
            print("❌ 쇼츠 최적화 영어 설정 확인 필요")
            
        # UI 기본값 확인
        if 'index=3,  # 1.3 기본값' in main_content:
            print("✅ UI 한국어 기본값: 1.3배속")
        else:
            print("❌ UI 한국어 기본값 확인 필요")
            
        if 'index=1,  # 1.1 기본값' in main_content:
            print("✅ UI 영어 기본값: 1.1배속")
        else:
            print("❌ UI 영어 기본값 확인 필요")
            
    except Exception as e:
        print(f"❌ Main.py 확인 실패: {e}")
    
    # 2. voice.py에서 실제 적용 설정 확인
    print("\n2. voice.py 실제 적용 설정 확인...")
    try:
        with open("app/services/voice.py", "r", encoding="utf-8") as f:
            voice_content = f.read()
        
        # Streamlit 세션 기본값
        if 'st.session_state.get("settings_korean_speed_boost", 1.3)' in voice_content:
            print("✅ voice.py 한국어 세션 기본값: 1.3배속")
        elif 'st.session_state.get("settings_korean_speed_boost", 1.4)' in voice_content:
            print("❌ voice.py 한국어 세션 기본값: 1.4배속 (수정 필요)")
        else:
            print("❓ voice.py 한국어 세션 기본값을 찾을 수 없음")
            
        if 'st.session_state.get("settings_english_speed_boost", 1.1)' in voice_content:
            print("✅ voice.py 영어 세션 기본값: 1.1배속")
        elif 'st.session_state.get("settings_english_speed_boost", 1.2)' in voice_content:
            print("❌ voice.py 영어 세션 기본값: 1.2배속 (수정 필요)")
        else:
            print("❓ voice.py 영어 세션 기본값을 찾을 수 없음")
            
        # 세션 없을 때 기본값
        if 'speed_multiplier = 1.3  # 한국어 1.3배속' in voice_content:
            print("✅ voice.py 한국어 fallback 기본값: 1.3배속")
        elif 'speed_multiplier = 1.4  # 한국어 1.4배속' in voice_content:
            print("❌ voice.py 한국어 fallback 기본값: 1.4배속 (수정 필요)")
        else:
            print("❓ voice.py 한국어 fallback 기본값을 찾을 수 없음")
            
        if 'speed_multiplier = 1.1  # 영어 1.1배속' in voice_content:
            print("✅ voice.py 영어 fallback 기본값: 1.1배속")
        elif 'speed_multiplier = 1.2  # 영어 1.2배속' in voice_content:
            print("❌ voice.py 영어 fallback 기본값: 1.2배속 (수정 필요)")
        else:
            print("❓ voice.py 영어 fallback 기본값을 찾을 수 없음")
            
    except Exception as e:
        print(f"❌ voice.py 확인 실패: {e}")
    
    print("\n📋 요약:")
    print("- 한국어 속도: 1.4 → 1.3 (0.1 감소)")
    print("- 영어 속도: 1.2 → 1.1 (0.1 감소)")
    print("- 모든 설정이 ✅로 표시되면 정상적으로 적용됨")

if __name__ == "__main__":
    check_current_speed_settings()