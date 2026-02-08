"""
origin/main (원격 저장소 최신 버전)으로 복원
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

commit = 'origin/main'

for file_path in files_to_restore:
    print(f"복원 중: {file_path}")
    
    result = subprocess.run(
        ['git', 'show', f'{commit}:{file_path}'],
        capture_output=True,
        env={'GIT_OPTIONAL_LOCKS': '0'}
    )
    
    if result.returncode == 0:
        try:
            content = result.stdout.decode('utf-8')
        except UnicodeDecodeError:
            content = result.stdout.decode('latin-1')
        
        if file_path.endswith('.py') and not content.startswith('# -*- coding: utf-8 -*-'):
            content = '# -*- coding: utf-8 -*-\n' + content
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ 완료: {len(content)} bytes")
    else:
        print(f"  ❌ 실패")

print("\n✅ origin/main 버전으로 복원 완료!")
print("이 버전은 원격 저장소의 최신 안정 버전입니다.")
