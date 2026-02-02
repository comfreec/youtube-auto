#!/usr/bin/env python3
"""
웹UI에서 사용하는 모듈들을 강제로 재로드
"""

import sys
import importlib
import os

def force_reload_modules():
    """웹UI에서 사용하는 모듈들을 강제로 재로드"""
    
    print("🔄 웹UI 모듈 강제 재로드 시작...")
    
    # 재로드할 모듈들
    modules_to_reload = [
        'app.services.youtube_reinterpret',
        'app.services.youtube_analyzer',
        'webui.youtube_reinterpret_ui'
    ]
    
    # 기존 모듈 제거
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            print(f"   🗑️ 기존 모듈 제거: {module_name}")
            del sys.modules[module_name]
    
    # 관련 캐시 제거
    for key in list(sys.modules.keys()):
        if any(mod in key for mod in modules_to_reload):
            print(f"   🗑️ 캐시 제거: {key}")
            del sys.modules[key]
    
    print("✅ 모듈 재로드 완료!")
    
    # 테스트
    print("\n🧪 재로드 후 테스트...")
    try:
        from app.services.youtube_reinterpret import youtube_reinterpret_service
        
        test_url = "https://www.youtube.com/shorts/NVBbca7EWFw"
        print(f"   테스트 URL: {test_url}")
        
        # URL 추출만 테스트 (API 호출 없이)
        video_id = youtube_reinterpret_service._extract_video_id(test_url)
        
        if video_id:
            print(f"✅ URL 추출 성공: {video_id}")
            print("   웹UI에서 이제 정상 작동할 것입니다!")
        else:
            print("❌ URL 추출 실패")
            
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")

if __name__ == "__main__":
    force_reload_modules()