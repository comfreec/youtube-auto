"""
간단하게 속도 수정
"""

# 파일 읽기
with open('app/services/voice.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 수정할 라인 찾기
new_lines = []
in_gtts_function = False
added_speed = False
adjusted_duration_added = False

for i, line in enumerate(lines):
    if 'def gtts_synthesize(' in line:
        in_gtts_function = True
    
    # logger.info 라인 찾아서 속도 추가
    if in_gtts_function and 'logger.info(f"gTTS synthesis started' in line and not added_speed:
        # 속도 변수 추가
        indent = ' ' * 8
        new_lines.append(f'{indent}# 속도 배율 설정 (1.3배속)\n')
        new_lines.append(f'{indent}speed_multiplier = 1.3\n')
        new_lines.append(f'{indent}\n')
        # 로그에 속도 추가
        new_line = line.replace('len(text)}")', 'len(text)}, Speed: {speed_multiplier}x")')
        new_lines.append(new_line)
        added_speed = True
        continue
    
    # audio_duration 계산 후 adjusted_duration 추가
    if in_gtts_function and 'audio_duration = _get_audio_duration_from_mp3(voice_file)' in line:
        new_lines.append(line)
        indent = ' ' * 8
        new_lines.append(f'{indent}\n')
        new_lines.append(f'{indent}# 속도 배율을 적용한 실제 재생 시간 계산\n')
        new_lines.append(f'{indent}adjusted_duration = audio_duration / speed_multiplier\n')
        adjusted_duration_added = True
        continue
    
    # logger.info 수정
    if in_gtts_function and adjusted_duration_added and 'logger.info(f"gTTS synthesis completed' in line:
        indent = ' ' * 8
        new_lines.append(f'{indent}logger.info(f"gTTS synthesis completed - Original: {{audio_duration:.2f}}s, Adjusted ({{speed_multiplier}}x): {{adjusted_duration:.2f}}s")\n')
        continue
    
    # create_sub 수정
    if in_gtts_function and 'sub_maker.create_sub(text, audio_duration)' in line:
        new_line = line.replace('audio_duration', 'adjusted_duration')
        new_lines.append(new_line)
        in_gtts_function = False
        continue
    
    new_lines.append(line)

# 저장
with open('app/services/voice.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ 속도 수정 완료!")
print(f"   - 속도 변수 추가: {added_speed}")
print(f"   - adjusted_duration 추가: {adjusted_duration_added}")
