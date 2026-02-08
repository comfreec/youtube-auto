"""
Main.py를 제대로 복원
"""
import subprocess
import sys

# Git에서 파일 가져오기
result = subprocess.run(
    ['git', 'show', '02614d0:webui/Main.py'],
    capture_output=True,
    env={'GIT_OPTIONAL_LOCKS': '0'}
)

if result.returncode == 0:
    # UTF-8로 디코딩 시도
    try:
        content = result.stdout.decode('utf-8')
    except UnicodeDecodeError:
        # 실패하면 latin-1로 디코딩 후 UTF-8로 재인코딩
        content = result.stdout.decode('latin-1')
    
    # UTF-8 BOM 추가 (인코딩 선언)
    if not content.startswith('# -*- coding: utf-8 -*-'):
        content = '# -*- coding: utf-8 -*-\n' + content
    
    # 파일 저장
    with open('webui/Main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Main.py 복원 완료!")
    print(f"   파일 크기: {len(content)} bytes")
else:
    print(f"❌ Git 명령 실패: {result.stderr.decode()}")
    sys.exit(1)
