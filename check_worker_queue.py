"""
백그라운드 워커 큐 상태 확인
"""
import os
import sys
from loguru import logger

# 프로젝트 루트 경로 추가
root_dir = os.path.dirname(os.path.realpath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.services.background_worker import get_background_worker

def check_queue():
    """큐 상태 확인"""
    worker = get_background_worker()
    
    logger.info("=" * 60)
    logger.info("백그라운드 워커 큐 상태")
    logger.info("=" * 60)
    logger.info(f"워커 실행 중: {worker.running}")
    logger.info(f"대기 중인 작업: {worker.get_queue_size()}")
    logger.info(f"실행 중인 작업: {worker.get_active_task_count()}")
    logger.info(f"활성 작업 목록: {list(worker.active_tasks.keys())}")
    logger.info("=" * 60)

if __name__ == "__main__":
    check_queue()
