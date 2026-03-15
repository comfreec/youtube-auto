"""
모바일 부하 최소화를 위한 서버 모드 - API 서버 연동
"""
import streamlit as st
import requests
import time
import os
from typing import Dict, Any, Optional
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MobileAPIConnector:
    """모바일 API 서버 연결기"""
    
    def __init__(self, api_server_url: str = None):
        self.api_server_url = api_server_url or os.getenv("DEFAULT_API_SERVER", "http://localhost:8001")
        self.session = requests.Session()
        self.session.timeout = 30
    
    def is_server_available(self) -> bool:
        """API 서버 사용 가능 여부 확인"""
        try:
            response = self.session.get(f"{self.api_server_url}/health")
            return response.status_code == 200
        except Exception:
            return False
    
    def start_video_generation(self, subject: str, video_type: str = "shorts", **kwargs) -> Optional[str]:
        """영상 생성 시작"""
        try:
            data = {
                "subject": subject,
                "video_type": video_type,
                **kwargs
            }
            
            response = self.session.post(f"{self.api_server_url}/api/video/generate", json=data)
            response.raise_for_status()
            
            result = response.json()
            return result.get("task_id")
            
        except Exception as e:
            logger.error(f"영상 생성 요청 실패: {e}")
            return None
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        try:
            response = self.session.get(f"{self.api_server_url}/api/task/{task_id}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"작업 상태 조회 실패: {e}")
            return None

# 전역 API 연결기
mobile_api = MobileAPIConnector()

def detect_mobile_environment() -> Dict[str, Any]:
    """모바일 환경 감지"""
    # 실제로는 JavaScript로 더 정확한 정보를 얻을 수 있음
    return {
        "is_mobile": True,  # 실제로는 user agent 확인 필요
        "has_api_server": mobile_api.is_server_available(),
        "server_url": mobile_api.api_server_url
    }

def start_mobile_optimized_generation(subject: str, video_type: str = "shorts", **kwargs) -> Optional[str]:
    """모바일 최적화된 영상 생성"""
    env_info = detect_mobile_environment()
    
    if env_info["has_api_server"]:
        # API 서버 사용 (권장)
        st.info("🌐 API 서버를 통한 영상 생성")
        return mobile_api.start_video_generation(subject, video_type, **kwargs)
    else:
        # 로컬 처리 (fallback)
        st.warning("📱 로컬 모바일 처리 (성능 제한)")
        return start_local_mobile_generation(subject, video_type, **kwargs)

def start_local_mobile_generation(subject: str, video_type: str = "shorts", **kwargs) -> Optional[str]:
    """로컬 모바일 처리 (fallback)"""
    try:
        import uuid
        from app.services import task as tm
        from app.models.schema import VideoParams
        
        task_id = str(uuid.uuid4())
        
        # 모바일 최적화 매개변수
        params = VideoParams(
            video_subject=subject,
            video_type=video_type,
            video_language=kwargs.get("language", "ko-KR")
        )
        
        # 모바일 환경에서는 제한된 설정
        if hasattr(params, 'video_resolution'):
            params.video_resolution = "720p"
        if hasattr(params, 'video_clip_duration'):
            params.video_clip_duration = min(kwargs.get("duration", 3), 3)
        
        # 백그라운드에서 처리
        import threading
        def process():
            try:
                tm.start(task_id, params)
            except Exception as e:
                logger.error(f"로컬 모바일 처리 실패: {e}")
        
        thread = threading.Thread(target=process, daemon=True)
        thread.start()
        
        return task_id
        
    except Exception as e:
        logger.error(f"로컬 모바일 생성 실패: {e}")
        return None

def monitor_mobile_task(task_id: str, subject: str):
    """모바일 작업 모니터링"""
    env_info = detect_mobile_environment()
    
    if env_info["has_api_server"]:
        # API 서버 모니터링
        monitor_api_task(task_id, subject)
    else:
        # 로컬 모니터링
        monitor_local_task(task_id, subject)

def monitor_api_task(task_id: str, subject: str):
    """API 서버 작업 모니터링"""
    progress_container = st.empty()
    status_container = st.empty()
    
    start_time = time.time()
    
    while True:
        status_info = mobile_api.get_task_status(task_id)
        
        if not status_info:
            status_container.error("❌ 작업 상태를 확인할 수 없습니다")
            break
        
        status = status_info["status"]
        progress = status_info["progress"]
        message = status_info["message"]
        elapsed_time = time.time() - start_time
        
        if status == "processing":
            # 모바일 최적화된 진행률 표시
            try:
                from webui.mobile_optimization import show_mobile_progress_tracker
                with progress_container.container():
                    show_mobile_progress_tracker(progress / 100, message, elapsed_time)
            except ImportError:
                progress_container.progress(progress / 100, text=f"{progress}% - {message}")
            
            time.sleep(2)
            
        elif status == "completed":
            progress_container.success("✅ 영상 생성 완료!")
            
            # 다운로드 버튼
            if st.button("📥 영상 다운로드", use_container_width=True):
                download_api_video(task_id, subject)
            break
            
        elif status == "failed":
            error_msg = status_info.get("error", "알 수 없는 오류")
            status_container.error(f"❌ 영상 생성 실패: {error_msg}")
            break
            
        elif status == "queued":
            status_container.info("⏳ 작업 대기 중...")
            time.sleep(2)

def monitor_local_task(task_id: str, subject: str):
    """로컬 작업 모니터링"""
    try:
        from app.services import state as sm
        from app.models import const
        
        progress_container = st.empty()
        status_container = st.empty()
        
        start_time = time.time()
        
        while True:
            task_info = sm.state.get_task(task_id)
            
            if not task_info:
                time.sleep(1)
                continue
            
            progress = task_info.get("progress", 0)
            state = task_info.get("state", const.TASK_STATE_PROCESSING)
            message = task_info.get("message", "")
            elapsed_time = time.time() - start_time
            
            if state == const.TASK_STATE_PROCESSING:
                try:
                    from webui.mobile_optimization import show_mobile_progress_tracker
                    with progress_container.container():
                        show_mobile_progress_tracker(progress / 100, message, elapsed_time)
                except ImportError:
                    progress_container.progress(progress / 100, text=f"{progress}% - {message}")
                
                time.sleep(2)
                
            elif state == const.TASK_STATE_COMPLETE:
                progress_container.success("✅ 영상 생성 완료!")
                
                # 결과 표시
                result = task_info.get("result")
                if result and result.get("file_path"):
                    video_path = result["file_path"]
                    if os.path.exists(video_path):
                        st.video(video_path)
                        
                        with open(video_path, "rb") as file:
                            st.download_button(
                                label="📥 영상 다운로드",
                                data=file.read(),
                                file_name=os.path.basename(video_path),
                                mime="video/mp4",
                                use_container_width=True
                            )
                break
                
            elif state == const.TASK_STATE_FAILED:
                status_container.error(f"❌ 영상 생성 실패: {message}")
                break
                
    except Exception as e:
        st.error(f"❌ 모니터링 오류: {e}")

def download_api_video(task_id: str, subject: str):
    """API 서버에서 영상 다운로드"""
    try:
        video_data = mobile_api.session.get(f"{mobile_api.api_server_url}/api/task/{task_id}/download")
        video_data.raise_for_status()
        
        filename = f"{subject}_{task_id[:8]}.mp4"
        st.download_button(
            label="📥 영상 다운로드",
            data=video_data.content,
            file_name=filename,
            mime="video/mp4",
            use_container_width=True
        )
        st.success("✅ 다운로드 준비 완료!")
        
    except Exception as e:
        st.error(f"❌ 영상 다운로드 실패: {e}")

def show_mobile_server_status():
    """모바일 서버 상태 표시"""
    env_info = detect_mobile_environment()
    
    if env_info["has_api_server"]:
        st.success(f"🟢 API 서버 연결됨: {env_info['server_url']}")
        
        # 서버 정보 표시
        try:
            response = mobile_api.session.get(f"{mobile_api.api_server_url}/")
            if response.status_code == 200:
                server_info = response.json()
                st.info(f"📊 활성 작업: {server_info.get('active_tasks', 0)}개")
        except:
            pass
    else:
        st.warning(f"🟡 API 서버 연결 안됨: {env_info['server_url']}")
        st.info("💡 로컬 모바일 처리로 동작합니다 (성능 제한)")

# 하위 호환성을 위한 기존 함수들
def start_mobile_video_generation(subject: str, video_type: str = "shorts", **kwargs) -> Optional[str]:
    """모바일 영상 생성 (하위 호환성)"""
    return start_mobile_optimized_generation(subject, video_type, **kwargs)

def show_mobile_generation_progress(task_id: str, subject: str = "영상"):
    """모바일 진행 상황 표시 (하위 호환성)"""
    monitor_mobile_task(task_id, subject)