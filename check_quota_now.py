"""현재 API 할당량 상태 확인"""
import sys
import os

root_dir = os.path.dirname(os.path.realpath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.services import llm

print("=" * 60)
print("🔍 API 할당량 상태 확인")
print("=" * 60)

quota_status = llm.check_api_quota_status()

print("\n📊 Gemini API 키 상태:")
print("-" * 60)

gemini_keys = quota_status.get("gemini_keys", [])
available_count = 0

for key_info in gemini_keys:
    key_num = key_info.get("key_num")
    key_preview = key_info.get("key_preview")
    available = key_info.get("available", False)
    status = key_info.get("status")
    
    if key_preview != "미설정":
        status_icon = "✅" if available else "❌"
        print(f"{status_icon} 키 #{key_num}: {key_preview} - {status}")
        if available:
            available_count += 1

print("-" * 60)
print(f"\n📈 요약: {available_count}/{len([k for k in gemini_keys if k.get('key_preview') != '미설정'])}개 키 사용 가능")

if available_count > 0:
    print(f"✅ {available_count}개 키로 영상 생성 가능합니다!")
else:
    print("❌ 모든 키 할당량 초과 - 내일 UTC 자정(한국 시간 오전 9시)에 리셋됩니다")

print("=" * 60)
