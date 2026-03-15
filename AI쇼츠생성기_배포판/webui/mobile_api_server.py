"""
모바일 클라이언트를 위한 API 서버
컴퓨터(서버)에서 모든 영상 처리를 담당하고, 모바일은 단순 클라이언트 역할
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uvicorn
import asyncio
import threading
import time
import os
import json
import uuid
from datetime import datetime
import logging

# 프로젝트 루트 경로 추가
import sys
root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.services import task as tm, state as sm, llm
from app.models.schema import VideoParams
from app.models import const

# FastAPI 앱 생성
app = FastAPI(
    title="AI 영상 생성 모바일 API",
    description="모바일 클라이언트를 위한 영상 생성 API 서버",
    version="1.0.0"
)

# CORS 설정 (모바일 앱에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포시에는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 전역 작업 저장소
active_tasks: Dict[str, Dict[str, Any]] = {}

# 요청 모델들
class VideoGenerationRequest(BaseModel):
    subject: str
    video_type: str = "shorts"  # shorts, longform, timer
    language: str = "ko-KR"
    duration: Optional[int] = None
    style: Optional[str] = None
    auto_upload: bool = False

class BatchVideoRequest(BaseModel):
    titles: List[str]
    video_type: str = "shorts"
    language: str = "ko-KR"
    duration: Optional[int] = None
    style: Optional[str] = None
    auto_upload: bool = False
    create_global: bool = False

# 응답 모델들
class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    """API 서버 상태 확인"""
    return {
        "message": "AI 영상 생성 모바일 API 서버",
        "status": "running",
        "version": "1.0.0",
        "active_tasks": len(active_tasks)
    }

@app.get("/health")
async def health_check():
    """서버 상태 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len(active_tasks)
    }

@app.post("/api/video/generate", response_model=TaskResponse)
async def generate_video(request: VideoGenerationRequest, background_tasks: BackgroundTasks):
    """단일 영상 생성 요청"""
    task_id = str(uuid.uuid4())
    
    logger.info(f"새 영상 생성 요청: {task_id} - {request.subject}")
    
    # 작업 정보 초기화
    active_tasks[task_id] = {
        "status": "queued",
        "progress": 0,
        "message": "작업 대기 중...",
        "request": request.dict(),
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None
    }
    
    # 백그라운드에서 영상 생성 시작
    background_tasks.add_task(process_single_video, task_id, request)
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        message="영상 생성 작업이 시작되었습니다"
    )

@app.post("/api/video/batch", response_model=TaskResponse)
async def generate_batch_videos(request: BatchVideoRequest, background_tasks: BackgroundTasks):
    """배치 영상 생성 요청"""
    task_id = str(uuid.uuid4())
    
    logger.info(f"배치 영상 생성 요청: {task_id} - {len(request.titles)}개 영상")
    
    # 작업 정보 초기화
    active_tasks[task_id] = {
        "status": "queued",
        "progress": 0,
        "message": "배치 작업 대기 중...",
        "request": request.dict(),
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None,
        "batch_results": []
    }
    
    # 백그라운드에서 배치 영상 생성 시작
    background_tasks.add_task(process_batch_videos, task_id, request)
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        message=f"{len(request.titles)}개 영상 배치 생성 작업이 시작되었습니다"
    )

@app.get("/api/task/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """작업 상태 조회"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    task_info = active_tasks[task_id]
    
    # 실제 작업 상태 확인 (state manager에서)
    try:
        real_task_info = sm.state.get_task(task_id)
        if real_task_info:
            task_info["progress"] = real_task_info.get("progress", task_info["progress"])
            task_info["message"] = real_task_info.get("message", task_info["message"])
            
            # 상태 동기화
            state = real_task_info.get("state", const.TASK_STATE_PROCESSING)
            if state == const.TASK_STATE_COMPLETE:
                task_info["status"] = "completed"
            elif state == const.TASK_STATE_FAILED:
                task_info["status"] = "failed"
                task_info["error"] = real_task_info.get("message", "알 수 없는 오류")
    except Exception as e:
        logger.warning(f"실제 작업 상태 확인 실패: {e}")
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task_info["status"],
        progress=task_info["progress"],
        message=task_info["message"],
        result=task_info.get("result"),
        error=task_info.get("error")
    )

@app.get("/api/task/{task_id}/download")
async def download_video(task_id: str):
    """완성된 영상 다운로드"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    task_info = active_tasks[task_id]
    
    if task_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="영상이 아직 완성되지 않았습니다")
    
    result = task_info.get("result")
    if not result or not result.get("file_path"):
        raise HTTPException(status_code=404, detail="영상 파일을 찾을 수 없습니다")
    
    file_path = result["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="영상 파일이 존재하지 않습니다")
    
    filename = os.path.basename(file_path)
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="video/mp4"
    )

@app.get("/api/tasks")
async def list_tasks():
    """모든 작업 목록 조회"""
    return {
        "tasks": [
            {
                "task_id": task_id,
                "status": info["status"],
                "progress": info["progress"],
                "message": info["message"],
                "created_at": info["created_at"],
                "subject": info["request"].get("subject") or f"{len(info['request'].get('titles', []))}개 배치"
            }
            for task_id, info in active_tasks.items()
        ]
    }

@app.delete("/api/task/{task_id}")
async def cancel_task(task_id: str):
    """작업 취소"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    # 작업 취소 처리
    active_tasks[task_id]["status"] = "cancelled"
    active_tasks[task_id]["message"] = "사용자에 의해 취소됨"
    
    return {"message": "작업이 취소되었습니다"}

# 백그라운드 작업 함수들
async def process_single_video(task_id: str, request: VideoGenerationRequest):
    """단일 영상 생성 처리"""
    try:
        active_tasks[task_id]["status"] = "processing"
        active_tasks[task_id]["message"] = "영상 생성 시작..."
        
        # VideoParams 객체 생성
        params = VideoParams(
            video_subject=request.subject,
            video_type=request.video_type,
            video_language=request.language
        )
        
        # 추가 매개변수 설정
        if request.duration:
            if request.video_type == "timer":
                params.timer_duration = request.duration
            else:
                params.video_duration = request.duration
        
        if request.style:
            params.video_style = request.style
        
        if request.auto_upload:
            params.auto_upload = True
        
        # 실제 영상 생성 (기존 시스템 사용)
        result = await asyncio.get_event_loop().run_in_executor(
            None, tm.start, task_id, params
        )
        
        # 결과 저장
        active_tasks[task_id]["status"] = "completed"
        active_tasks[task_id]["progress"] = 100
        active_tasks[task_id]["message"] = "영상 생성 완료!"
        active_tasks[task_id]["result"] = result
        
        logger.info(f"영상 생성 완료: {task_id}")
        
    except Exception as e:
        logger.error(f"영상 생성 실패: {task_id} - {e}")
        active_tasks[task_id]["status"] = "failed"
        active_tasks[task_id]["error"] = str(e)
        active_tasks[task_id]["message"] = f"영상 생성 실패: {str(e)}"

async def process_batch_videos(task_id: str, request: BatchVideoRequest):
    """배치 영상 생성 처리"""
    try:
        active_tasks[task_id]["status"] = "processing"
        active_tasks[task_id]["message"] = "배치 영상 생성 시작..."
        
        total_videos = len(request.titles)
        completed_videos = []
        failed_videos = []
        
        for i, title in enumerate(request.titles):
            current_progress = int((i / total_videos) * 100)
            active_tasks[task_id]["progress"] = current_progress
            active_tasks[task_id]["message"] = f"영상 생성 중... ({i+1}/{total_videos}) {title}"
            
            try:
                # 개별 영상 생성
                individual_task_id = str(uuid.uuid4())
                
                params = VideoParams(
                    video_subject=title,
                    video_type=request.video_type,
                    video_language=request.language
                )
                
                # 추가 매개변수 설정
                if request.duration:
                    if request.video_type == "timer":
                        params.timer_duration = request.duration
                    else:
                        params.video_duration = request.duration
                
                if request.style:
                    params.video_style = request.style
                
                if request.auto_upload:
                    params.auto_upload = True
                
                # 영상 생성
                result = await asyncio.get_event_loop().run_in_executor(
                    None, tm.start, individual_task_id, params
                )
                
                if result:
                    completed_videos.append({
                        "title": title,
                        "result": result,
                        "task_id": individual_task_id
                    })
                    logger.info(f"배치 영상 완료: {title}")
                else:
                    failed_videos.append({
                        "title": title,
                        "error": "결과 없음"
                    })
                    logger.warning(f"배치 영상 실패: {title}")
                
            except Exception as e:
                failed_videos.append({
                    "title": title,
                    "error": str(e)
                })
                logger.error(f"배치 영상 오류: {title} - {e}")
        
        # 최종 결과
        active_tasks[task_id]["status"] = "completed"
        active_tasks[task_id]["progress"] = 100
        active_tasks[task_id]["message"] = f"배치 생성 완료! 성공: {len(completed_videos)}, 실패: {len(failed_videos)}"
        active_tasks[task_id]["result"] = {
            "completed": completed_videos,
            "failed": failed_videos,
            "total": total_videos
        }
        
        logger.info(f"배치 영상 생성 완료: {task_id} - 성공: {len(completed_videos)}, 실패: {len(failed_videos)}")
        
    except Exception as e:
        logger.error(f"배치 영상 생성 실패: {task_id} - {e}")
        active_tasks[task_id]["status"] = "failed"
        active_tasks[task_id]["error"] = str(e)
        active_tasks[task_id]["message"] = f"배치 생성 실패: {str(e)}"

def start_api_server(host: str = "0.0.0.0", port: int = 8001):
    """API 서버 시작"""
    logger.info(f"모바일 API 서버 시작: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    start_api_server()