"""모바일 영상 생성 실시간 모니터링"""
import time
import os
import sys

root_dir = os.path.dirname(os.path.realpath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.services.background_worker import get_background_worker

print("=" * 80)
print("🎬 모바일 영상 생성 실시간 모니터링")
print("=" * 80)
print("\n⏳ 영상 생성 요청을 기다리는 중...")
print("💡 모바일에서 영상 생성 버튼을 누르세요!\n")

worker = get_background_worker()
last_task_count = 0
monitored_tasks = set()

try:
    while True:
        # 큐 상태 확인
        queue_size = worker.task_queue.qsize()
        active_count = len(worker.active_tasks)
        
        # 새로운 작업 감지
        if queue_size > 0 or active_count > 0:
            current_time = time.strftime("%H:%M:%S")
            
            if queue_size != last_task_count:
                print(f"\n[{current_time}] 📊 큐 상태: {queue_size}개 대기 중, {active_count}개 실행 중")
                last_task_count = queue_size
            
            # 활성 작업 상태 표시
            for task_id, task_info in list(worker.active_tasks.items()):
                if task_id not in monitored_tasks:
                    monitored_tasks.add(task_id)
                    params = task_info.get("params")
                    subject = params.video_subject if params else "알 수 없음"
                    language = params.video_language if params else "알 수 없음"
                    
                    print(f"\n{'='*80}")
                    print(f"🚀 새 작업 시작!")
                    print(f"   Task ID: {task_id}")
                    print(f"   주제: {subject}")
                    print(f"   언어: {language}")
                    print(f"   시작 시간: {current_time}")
                    print(f"{'='*80}")
                
                # 작업 상태 확인
                status = task_info.get("status", "unknown")
                if status == "completed":
                    print(f"\n✅ [{current_time}] 작업 완료: {task_id[:8]}...")
                elif status == "failed":
                    error = task_info.get("error", "알 수 없는 오류")
                    print(f"\n❌ [{current_time}] 작업 실패: {task_id[:8]}... - {error}")
        
        time.sleep(2)
        
except KeyboardInterrupt:
    print("\n\n⏹️  모니터링 종료")
    print("=" * 80)
