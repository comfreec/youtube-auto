"""
모든 주요 파일을 02614d0 버전으로 복원
"""
import subprocess
import os

files_to_restore = [
    'app/services/voice.py',
    'app/services/video.py',
    'app/services/task.py',
    'app/services/subtitle.py',
    'webui/Main.py'
]

for file_path in files_to_restore:
    print(f"복원 중: {file_path}")
    
    # Git에서 파일 가져오기
    result = subprocess.run(
        ['git', 'show', f'02614d0:{file_path}'],
        capture_output=True,
        env={'GIT_OPTIONAL_LOCKS': '0'}
    )
    
    if result.returncode == 0:
        # UTF-8로 디코딩 시도
        try:
            content = result.stdout.decode('utf-8')
        except UnicodeDecodeError:
            # 실패하면 latin-1로 디코딩
            content = result.stdout.decode('latin-1')
        
        # UTF-8 인코딩 선언 추가 (Python 파일인 경우)
        if file_path.endswith('.py') and not content.startswith('# -*- coding: utf-8 -*-'):
            content = '# -*- coding: utf-8 -*-\n' + content
        
        # 디렉토리 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ 완료: {len(content)} bytes")
    else:
        print(f"  ❌ 실패: {result.stderr.decode()}")

print("\n모든 파일 복원 완료!")
