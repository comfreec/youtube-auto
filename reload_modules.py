#!/usr/bin/env python3
"""
모듈 강제 재로드 스크립트
"""

import sys
import importlib

def reload_youtube_modules():
    """YouTube 관련 모듈들을 강제로 재로드"""
    
    modules_to_reload = [
        'app.services.youtube_reinterpret',
        'app.services.youtube_analyzer'
    ]
    
    print("🔄 YouTube 관련 모듈 재로드 중...")
    
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            print(f"   재로드: {module_name}")
            importlib.reload(sys.modules[module_name])
        else:
            print(f"   로드되지 않음: {module_name}")
    
    print("✅ 모듈 재로드 완료!")
    
    # 테스트
    print("\n🧪 재로드 후 테스트...")
    from app.services.youtube_reinterpret import youtube_reinterpret_service
    
    test_url = "https://www.youtube.com/shorts/NVBbca7EWFw"
    result = youtube_reinterpret_service.analyze_youtube_video(test_url)
    
    if result.get("success"):
        print("✅ 테스트 성공!")
        print(f"   비디오 ID: {result.get('video_id')}")
        print(f"   제목: {result.get('metadata', {}).get('title', 'N/A')}")
    else:
        print("❌ 테스트 실패!")
        print(f"   오류: {result.get('error')}")

if __name__ == "__main__":
    reload_youtube_modules()