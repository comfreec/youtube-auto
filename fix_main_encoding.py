"""
Main.py 인코딩 문제 수정
"""

# 파일 읽기
with open('webui/Main.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# 1209번 라인 수정
fixed_lines = []
for i, line in enumerate(lines, 1):
    if i == 1209:
        # 문자열이 닫히지 않은 라인 수정
        fixed_lines.append('    st.success("✅ Gemini 2.5 Flash 사용중")\n')
    elif i == 1210:
        fixed_lines.append('    st.info("⚡ 고속 생성 모드 준비완료")\n')
    else:
        fixed_lines.append(line)

# 저장
with open('webui/Main.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("✅ Main.py 수정 완료!")
