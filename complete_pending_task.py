"""
미완성 작업을 완료하는 스크립트
"""
import os
import sys
from loguru import logger

# 프로젝트 루트 경로 추가
root_dir = os.path.dirname(os.path.realpath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.services import task as tm
from app.models.schema import VideoParams

def complete_task(task_id: str):
    """작업 완료"""
    logger.info(f"작업 완료 시도: {task_id}")
    
    # 작업 폴더 확인
    task_dir = os.path.join("storage", "tasks", task_id)
    if not os.path.exists(task_dir):
        logger.error(f"작업 폴더가 없습니다: {task_dir}")
        return False
    
    # script.json 읽기
    import json
    script_file = os.path.join(task_dir, "script.json")
    if not os.path.exists(script_file):
        logger.error(f"script.json이 없습니다: {script_file}")
        return False
    
    with open(script_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # VideoParams 생성
    params_dict = data.get('params', {})
    params = VideoParams(**params_dict)
    
    logger.info(f"작업 재개: {params.video_subject} ({params.video_language})")
    
    # 작업 실행
    try:
        tm.start(task_id=task_id, params=params)
        logger.info(f"✅ 작업 완료: {task_id}")
        return True
    except Exception as e:
        logger.error(f"❌ 작업 실패: {task_id} - {e}")
        return False

if __name__ == "__main__":
    # 한국어 버전
    korean_task_id = "e9084a20-27c1-4b00-9aff-7a6227afd487"
    logger.info(f"한국어 작업 완료 시작: {korean_task_id}")
    complete_task(korean_task_id)
    
    # 영어 버전
    english_task_id = "e9084a20-27c1-4b00-9aff-7a6227afd487_english"
    logger.info(f"영어 작업 완료 시작: {english_task_id}")
    complete_task(english_task_id)
