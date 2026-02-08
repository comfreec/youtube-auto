"""
voice.py에 1.3배속 적용
"""
import re

# voice.py 읽기
with open('app/services/voice.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# gtts_synthesize 함수 찾기
pattern = r'(def gtts_synthesize\(text: str, voice_name: str, voice_file: str\).*?)(logger\.info\(f"gTTS synthesis started.*?\))(.*?)(audio_duration = _get_audio_duration_from_mp3\(voice_file\))(.*?)(sub_maker\.create_sub\(text, audio_duration\))'

def replacement(match):
    return f'''{match.group(1)}# 속도 배율 설정 (1.3배속)
        speed_multiplier = 1.3
        
        {match.group(2).replace('len(text)}', 'len(text)}, Speed: {{speed_multiplier}}x')}
        
{match.group(3)}{match.group(4)}
        
        # 속도 배율을 적용한 실제 재생 시간 계산
        adjusted_duration = audio_duration / speed_multiplier
        logger.info(f"gTTS synthesis completed - Original: {{audio_duration:.2f}}s, Adjusted ({{speed_multiplier}}x): {{adjusted_duration:.2f}}s")
        
{match.group(5)}sub_maker.create_sub(text, adjusted_duration)'''

# 정규식으로 교체
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# 저장
with open('app/services/voice.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ 1.3배속 적용 완료!")
