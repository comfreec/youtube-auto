#!/usr/bin/env python3
"""
배치 영상 영어 제목 로그 확인 가이드
"""

def show_log_guide():
    print("🔍 배치 영상 영어 제목 로그 확인 가이드")
    print("=" * 70)
    
    print("📋 이제 배치 영상 생성 시 다음 로그를 확인하세요:")
    print()
    
    print("1️⃣ 영어 버전 생성 시:")
    print("   ✅ Generated English title: [영어 제목]")
    print("   ✅ English title in result: [영어 제목]")
    print()
    
    print("2️⃣ 업로드 준비 시:")
    print("   🔍 DEBUG: eng_version keys: ['file_path', 'script', 'video_id', 'type', 'title', 'english_title', 'version']")
    print("   🔍 DEBUG: eng_version.get('title'): [여기가 중요!]")
    print("   🔍 DEBUG: eng_version.get('english_title'): [여기도 중요!]")
    print("   🔍 DEBUG: result['title']: [한국어 제목]")
    print()
    
    print("3️⃣ 제목 선택 과정:")
    print("   🔍 Step 1 - eng_title from 'title': [값 확인]")
    print("   🔍 Step 2 - eng_title from 'english_title': [Step 1이 None이면 실행]")
    print("   🔍 Step 3 - eng_title from translation: [Step 2도 None이면 실행]")
    print("   🔍 Step 4 - eng_title from keywords: [번역 실패 시 실행]")
    print()
    
    print("4️⃣ 최종 결과:")
    print("   ✅ Final English title for upload: [최종 영어 제목]")
    print("   📺 YouTube Upload - Title: #Shorts [최종 영어 제목]")
    print("   📺 YouTube Upload - Description: Generated youtube-auto AI")
    print("                                     Subject: [최종 영어 제목]")
    print()
    
    print("🎯 확인해야 할 것:")
    print("- Step 1에서 한글이 나오면: eng_version['title']이 한글")
    print("- Step 2에서 한글이 나오면: eng_version['english_title']이 한글")
    print("- Step 3이 실행되면: 둘 다 None이었다는 뜻")
    print("- Step 4가 실행되면: 번역도 실패했다는 뜻")
    print()
    
    print("💡 예상 시나리오:")
    print()
    print("시나리오 A (정상):")
    print("  🔍 Step 1 - eng_title from 'title': Success Habits")
    print("  ✅ Final English title: Success Habits")
    print("  → 성공! ✅")
    print()
    
    print("시나리오 B (title이 한글):")
    print("  🔍 Step 1 - eng_title from 'title': 성공하는 습관")
    print("  🔍 Step 2 - eng_title from 'english_title': Success Habits")
    print("  ✅ Final English title: Success Habits")
    print("  → 성공! ✅")
    print()
    
    print("시나리오 C (둘 다 한글):")
    print("  🔍 Step 1 - eng_title from 'title': 성공하는 습관")
    print("  🔍 Step 2 - eng_title from 'english_title': 성공하는 습관")
    print("  ⚠️ No English title found, translating: 성공하는 습관")
    print("  🔍 Step 3 - eng_title from translation: Success Habits")
    print("  ✅ Final English title: Success Habits")
    print("  → 번역으로 해결 ✅")
    print()
    
    print("시나리오 D (모두 실패):")
    print("  🔍 Step 1 - eng_title from 'title': None")
    print("  🔍 Step 2 - eng_title from 'english_title': None")
    print("  ⚠️ No English title found, translating: 성공하는 습관")
    print("  🔍 Step 3 - eng_title from translation: 성공하는 습관 (번역 실패)")
    print("  🔍 Step 4 - eng_title from keywords: Motivational Content")
    print("  ✅ Final English title: Motivational Content")
    print("  → 기본값 사용 ⚠️")
    print()
    
    print("📝 다음 단계:")
    print("1. 배치 영상 생성 시도")
    print("2. 터미널에서 위의 로그 찾기")
    print("3. 어느 Step에서 한글이 나오는지 확인")
    print("4. 로그 내용을 알려주시면 정확한 해결책 제시")

if __name__ == "__main__":
    show_log_guide()