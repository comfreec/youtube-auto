#!/usr/bin/env python3
"""
세션 상태 초기화 및 속도 설정 강제 적용 스크립트
"""

def reset_session_speed():
    print("🔄 세션 상태 초기화 및 속도 설정 강제 적용...")
    
    # Main.py에 세션 초기화 코드 추가
    main_py_path = "webui/Main.py"
    
    try:
        with open(main_py_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 세션 초기화 코드 추가 (기존 코드 앞에)
        reset_code = '''
# 음성 속도 설정 강제 초기화 (임시)
if "force_speed_reset" not in st.session_state:
    st.session_state["settings_korean_speed_boost"] = 1.3
    st.session_state["settings_english_speed_boost"] = 1.1
    st.session_state["force_speed_reset"] = True
    print("🔄 음성 속도 설정 강제 초기화 완료: 한국어 1.3배속, 영어 1.1배속")

'''
        
        # 첫 번째 import 문 뒤에 추가
        import_end = content.find('\n\n')
        if import_end != -1:
            new_content = content[:import_end] + reset_code + content[import_end:]
            
            with open(main_py_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            print("✅ 세션 초기화 코드 추가 완료")
            print("📝 서버 재시작 후 브라우저에서 새로고침하면 새로운 속도가 적용됩니다")
            
        else:
            print("❌ 적절한 위치를 찾을 수 없음")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    reset_session_speed()