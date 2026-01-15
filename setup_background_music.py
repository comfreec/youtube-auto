#!/usr/bin/env python3
"""
배경음악 시스템 초기 설정 스크립트
"""

import os
import sys
from loguru import logger

# Add the root directory to the path
root_dir = os.path.dirname(os.path.realpath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

def setup_music_system():
    """배경음악 시스템 초기 설정"""
    print("🎵 배경음악 시스템 설정 중...")
    print("=" * 50)
    
    try:
        from app.services.music_manager import setup_background_music
        
        # 배경음악 파일들 다운로드/설정
        setup_background_music()
        
        print("✅ 배경음악 시스템 설정 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 배경음악 시스템 설정 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_emotion_analysis():
    """감정 분석 테스트"""
    print("\n😊 감정 분석 테스트")
    print("=" * 50)
    
    try:
        from app.services.emotion_analyzer import analyze_script_emotion, get_background_music
        
        test_cases = [
            ("성공하는 사람들의 아침 루틴", "성공한 사람들은 매일 아침 5시에 일어나서 운동을 합니다. 목표를 달성하기 위해 즉시 행동에 옮기죠."),
            ("스트레스 해소 명상법", "마음을 편안하게 하고 천천히 호흡하세요. 평온한 상태에서 모든 걱정을 내려놓으세요."),
            ("긴급! 투자 기회", "지금 놓치면 후회할 투자 기회입니다. 서둘러 결정하지 않으면 위험할 수 있습니다."),
        ]
        
        for subject, script in test_cases:
            print(f"\n📝 주제: {subject}")
            
            # 감정 분석
            emotion_data = analyze_script_emotion(script, subject)
            print(f"😊 감정: {emotion_data['emotion']}")
            print(f"🎵 음악 스타일: {emotion_data['music_style']}")
            print(f"🔊 볼륨: {emotion_data['volume']}")
            
            # 배경음악 파일 가져오기
            music_file, volume = get_background_music(script, subject)
            print(f"📁 음악 파일: {music_file}")
        
        print("\n✅ 감정 분석 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 감정 분석 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 설정 실행"""
    print("🚀 배경음악 시스템 종합 설정")
    print("=" * 60)
    
    results = {}
    
    # 1. 배경음악 시스템 설정
    results['music_setup'] = setup_music_system()
    
    # 2. 감정 분석 테스트
    results['emotion_test'] = test_emotion_analysis()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 설정 결과:")
    print(f"🎵 배경음악 시스템: {'✅' if results['music_setup'] else '❌'}")
    print(f"😊 감정 분석: {'✅' if results['emotion_test'] else '❌'}")
    
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n🎯 전체 성공률: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("\n🎉 배경음악 시스템이 성공적으로 설정되었습니다!")
        print("\n📋 이제 다음과 같이 작동합니다:")
        print("• 대본 감정 분석 → 적절한 배경음악 자동 선택")
        print("• 에너지 넘치는 내용 → 업비트 음악")
        print("• 차분한 내용 → 앰비언트 음악")
        print("• 동기부여 내용 → 영감을 주는 음악")
        print("• 교육적 내용 → 깔끔한 기업용 음악")
        print("• 긴급한 내용 → 긴장감 있는 음악")
        print("• 즐거운 내용 → 밝고 경쾌한 음악")
        
    else:
        print("⚠️ 일부 설정에 문제가 있습니다. 위의 오류를 확인하세요.")

if __name__ == "__main__":
    main()