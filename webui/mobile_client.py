"""
모바일 클라이언트 웹앱
서버에 API 요청을 보내고 결과를 받아오는 가벼운 클라이언트
"""
import streamlit as st
import requests
import time
import json
import os
from typing import Dict, Any, Optional
import logging

# 모바일 최적화 import
try:
    from webui.mobile_optimization import (
        add_mobile_styles, add_mobile_connection_monitor, 
        show_mobile_progress_tracker, add_mobile_error_recovery
    )
    MOBILE_OPTIMIZATION_AVAILABLE = True
except ImportError:
    MOBILE_OPTIMIZATION_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="📱 AI 영상 생성 모바일",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 모바일 최적화 적용
if MOBILE_OPTIMIZATION_AVAILABLE:
    add_mobile_styles()
    add_mobile_connection_monitor()
    add_mobile_error_recovery()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MobileAPIClient:
    """모바일 API 클라이언트"""
    
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30
    
    def check_server_connection(self) -> bool:
        """서버 연결 확인"""
        try:
            response = self.session.get(f"{self.server_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"서버 연결 실패: {e}")
            return False
    
    def generate_video(self, subject: str, video_type: str = "shorts", 
                      language: str = "ko-KR", **kwargs) -> Optional[str]:
        """단일 영상 생성 요청"""
        try:
            data = {
                "subject": subject,
                "video_type": video_type,
                "language": language,
                **kwargs
            }
            
            response = self.session.post(f"{self.server_url}/api/video/generate", json=data)
            response.raise_for_status()
            
            result = response.json()
            return result.get("task_id")
            
        except Exception as e:
            logger.error(f"영상 생성 요청 실패: {e}")
            return None
    
    def generate_batch_videos(self, titles: list, video_type: str = "shorts",
                            language: str = "ko-KR", **kwargs) -> Optional[str]:
        """배치 영상 생성 요청"""
        try:
            data = {
                "titles": titles,
                "video_type": video_type,
                "language": language,
                **kwargs
            }
            
            response = self.session.post(f"{self.server_url}/api/video/batch", json=data)
            response.raise_for_status()
            
            result = response.json()
            return result.get("task_id")
            
        except Exception as e:
            logger.error(f"배치 영상 생성 요청 실패: {e}")
            return None
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        try:
            response = self.session.get(f"{self.server_url}/api/task/{task_id}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"작업 상태 조회 실패: {e}")
            return None
    
    def download_video(self, task_id: str) -> Optional[bytes]:
        """영상 다운로드"""
        try:
            response = self.session.get(f"{self.server_url}/api/task/{task_id}/download")
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"영상 다운로드 실패: {e}")
            return None
    
    def list_tasks(self) -> Optional[Dict[str, Any]]:
        """작업 목록 조회"""
        try:
            response = self.session.get(f"{self.server_url}/api/tasks")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"작업 목록 조회 실패: {e}")
            return None

# 세션 상태 초기화
if "api_client" not in st.session_state:
    st.session_state.api_client = None
if "server_url" not in st.session_state:
    st.session_state.server_url = "http://localhost:8001"
if "connected" not in st.session_state:
    st.session_state.connected = False

def main():
    """메인 앱"""
    
    # 헤더
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; font-size: 1.8rem;">📱 AI 영상 생성 모바일</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;">서버 연결 방식으로 모바일 부하 제로!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 서버 연결 설정
    with st.expander("🔧 서버 연결 설정", expanded=not st.session_state.connected):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            server_url = st.text_input(
                "서버 주소",
                value=st.session_state.server_url,
                placeholder="http://192.168.1.100:8001",
                help="컴퓨터의 IP 주소와 포트를 입력하세요"
            )
        
        with col2:
            if st.button("🔌 연결", use_container_width=True):
                st.session_state.server_url = server_url
                st.session_state.api_client = MobileAPIClient(server_url)
                
                with st.spinner("서버 연결 확인 중..."):
                    if st.session_state.api_client.check_server_connection():
                        st.session_state.connected = True
                        st.success("✅ 서버 연결 성공!")
                        st.rerun()
                    else:
                        st.session_state.connected = False
                        st.error("❌ 서버 연결 실패!")
    
    # 연결 상태 표시
    if st.session_state.connected:
        st.success(f"🟢 서버 연결됨: {st.session_state.server_url}")
    else:
        st.error("🔴 서버에 연결되지 않음")
        st.info("💡 먼저 컴퓨터에서 API 서버를 실행하고 위에서 연결하세요")
        st.code("python webui/mobile_api_server.py", language="bash")
        return
    
    # 메인 기능 탭
    tab1, tab2, tab3 = st.tabs(["🎬 단일 영상", "🔄 배치 생성", "📋 작업 목록"])
    
    with tab1:
        show_single_video_generation()
    
    with tab2:
        show_batch_video_generation()
    
    with tab3:
        show_task_list()

def show_single_video_generation():
    """단일 영상 생성 UI"""
    st.markdown("### 🎬 단일 영상 생성")
    
    with st.form("single_video_form"):
        subject = st.text_input(
            "영상 주제",
            placeholder="예: 건강한 아침 식사 레시피 5가지",
            help="생성할 영상의 주제를 입력하세요"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            video_type = st.selectbox(
                "영상 타입",
                ["shorts", "longform", "timer"],
                format_func=lambda x: {
                    "shorts": "🎬 쇼츠 (60초)",
                    "longform": "📺 롱폼 (5-15분)",
                    "timer": "⏱️ 타이머"
                }[x]
            )
            
            language = st.selectbox(
                "언어",
                ["ko-KR", "en-US"],
                format_func=lambda x: "🇰🇷 한국어" if x == "ko-KR" else "🇺🇸 English"
            )
        
        with col2:
            if video_type == "timer":
                duration = st.slider("타이머 길이 (분)", 5, 60, 20)
            elif video_type == "longform":
                duration = st.slider("영상 길이 (분)", 5, 15, 10)
            else:
                duration = st.slider("영상 길이 (초)", 30, 90, 60)
            
            auto_upload = st.checkbox("📤 자동 업로드", value=False)
        
        submitted = st.form_submit_button("🚀 영상 생성 시작", use_container_width=True, type="primary")
        
        if submitted:
            if not subject.strip():
                st.error("❌ 영상 주제를 입력해주세요!")
                return
            
            # API 요청
            task_id = st.session_state.api_client.generate_video(
                subject=subject,
                video_type=video_type,
                language=language,
                duration=duration,
                auto_upload=auto_upload
            )
            
            if task_id:
                st.success(f"✅ 영상 생성 요청 완료! 작업 ID: {task_id[:8]}...")
                
                # 진행 상황 모니터링
                monitor_task_progress(task_id, subject)
            else:
                st.error("❌ 영상 생성 요청 실패!")

def show_batch_video_generation():
    """배치 영상 생성 UI"""
    st.markdown("### 🔄 배치 영상 생성")
    
    with st.form("batch_video_form"):
        titles_text = st.text_area(
            "영상 제목 리스트",
            placeholder="""예시:
1. 건강한 아침 식사 레시피 5가지
2. 집에서 할 수 있는 간단한 운동
3. 스트레스 해소하는 방법
4. 효율적인 시간 관리 팁
5. 좋은 수면을 위한 습관들""",
            height=150,
            help="한 줄에 하나씩 영상 제목을 입력하세요"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            video_type = st.selectbox(
                "영상 타입",
                ["shorts", "longform", "timer"],
                format_func=lambda x: {
                    "shorts": "🎬 쇼츠 (60초)",
                    "longform": "📺 롱폼 (5-15분)",
                    "timer": "⏱️ 타이머"
                }[x],
                key="batch_video_type"
            )
            
            language = st.selectbox(
                "언어",
                ["ko-KR", "en-US"],
                format_func=lambda x: "🇰🇷 한국어" if x == "ko-KR" else "🇺🇸 English",
                key="batch_language"
            )
        
        with col2:
            if video_type == "timer":
                duration = st.slider("타이머 길이 (분)", 5, 60, 20, key="batch_duration")
            elif video_type == "longform":
                duration = st.slider("영상 길이 (분)", 5, 15, 10, key="batch_duration")
            else:
                duration = st.slider("영상 길이 (초)", 30, 90, 60, key="batch_duration")
            
            auto_upload = st.checkbox("📤 자동 업로드", value=False, key="batch_auto_upload")
        
        submitted = st.form_submit_button("🚀 배치 생성 시작", use_container_width=True, type="primary")
        
        if submitted:
            if not titles_text.strip():
                st.error("❌ 영상 제목 리스트를 입력해주세요!")
                return
            
            # 제목 파싱
            titles = []
            for line in titles_text.strip().split('\n'):
                line = line.strip()
                if line:
                    # 번호나 기호 제거
                    import re
                    clean_title = re.sub(r'^[\d\.\-\*\+\s]+', '', line).strip()
                    if clean_title:
                        titles.append(clean_title)
            
            if not titles:
                st.error("❌ 유효한 영상 제목이 없습니다!")
                return
            
            if len(titles) > 20:
                titles = titles[:20]
                st.warning("⚠️ 최대 20개까지만 처리합니다.")
            
            st.info(f"📊 총 {len(titles)}개 영상을 생성합니다")
            
            # API 요청
            task_id = st.session_state.api_client.generate_batch_videos(
                titles=titles,
                video_type=video_type,
                language=language,
                duration=duration,
                auto_upload=auto_upload
            )
            
            if task_id:
                st.success(f"✅ 배치 생성 요청 완료! 작업 ID: {task_id[:8]}...")
                
                # 진행 상황 모니터링
                monitor_task_progress(task_id, f"{len(titles)}개 배치 영상")
            else:
                st.error("❌ 배치 생성 요청 실패!")

def show_task_list():
    """작업 목록 UI"""
    st.markdown("### 📋 작업 목록")
    
    if st.button("🔄 새로고침", use_container_width=True):
        st.rerun()
    
    # 작업 목록 조회
    tasks_data = st.session_state.api_client.list_tasks()
    
    if not tasks_data or not tasks_data.get("tasks"):
        st.info("📝 진행 중인 작업이 없습니다")
        return
    
    tasks = tasks_data["tasks"]
    
    for task in tasks:
        task_id = task["task_id"]
        status = task["status"]
        progress = task["progress"]
        subject = task["subject"]
        created_at = task["created_at"]
        
        # 상태에 따른 색상
        status_colors = {
            "queued": "🟡",
            "processing": "🔵",
            "completed": "🟢",
            "failed": "🔴",
            "cancelled": "⚫"
        }
        
        status_icon = status_colors.get(status, "⚪")
        
        with st.expander(f"{status_icon} {subject} ({task_id[:8]}...)", expanded=status=="processing"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**상태:** {status}")
                st.write(f"**진행률:** {progress}%")
                st.write(f"**생성 시간:** {created_at}")
                
                if progress > 0:
                    st.progress(progress / 100)
            
            with col2:
                if status == "completed":
                    if st.button("📥 다운로드", key=f"download_{task_id}"):
                        download_task_video(task_id, subject)
                
                if status in ["processing", "queued"]:
                    if st.button("🔄 상태 확인", key=f"refresh_{task_id}"):
                        check_task_status(task_id)

def monitor_task_progress(task_id: str, subject: str):
    """작업 진행 상황 모니터링"""
    progress_container = st.empty()
    status_container = st.empty()
    
    start_time = time.time()
    
    while True:
        # 작업 상태 조회
        status_info = st.session_state.api_client.get_task_status(task_id)
        
        if not status_info:
            status_container.error("❌ 작업 상태를 확인할 수 없습니다")
            break
        
        status = status_info["status"]
        progress = status_info["progress"]
        message = status_info["message"]
        
        elapsed_time = time.time() - start_time
        
        if status == "processing":
            # 모바일 최적화된 진행률 표시
            if MOBILE_OPTIMIZATION_AVAILABLE:
                with progress_container.container():
                    show_mobile_progress_tracker(progress / 100, message, elapsed_time)
            else:
                progress_container.progress(progress / 100, text=f"{progress}% - {message}")
            
            # 2초마다 업데이트
            time.sleep(2)
            
        elif status == "completed":
            progress_container.success("✅ 영상 생성 완료!")
            
            # 다운로드 버튼
            if st.button("📥 영상 다운로드", use_container_width=True):
                download_task_video(task_id, subject)
            break
            
        elif status == "failed":
            error_msg = status_info.get("error", "알 수 없는 오류")
            status_container.error(f"❌ 영상 생성 실패: {error_msg}")
            break
            
        elif status == "queued":
            status_container.info("⏳ 작업 대기 중...")
            time.sleep(2)

def check_task_status(task_id: str):
    """작업 상태 확인"""
    status_info = st.session_state.api_client.get_task_status(task_id)
    
    if status_info:
        st.json(status_info)
    else:
        st.error("❌ 작업 상태를 확인할 수 없습니다")

def download_task_video(task_id: str, subject: str):
    """작업 영상 다운로드"""
    with st.spinner("영상 다운로드 중..."):
        video_data = st.session_state.api_client.download_video(task_id)
        
        if video_data:
            filename = f"{subject}_{task_id[:8]}.mp4"
            st.download_button(
                label="📥 영상 다운로드",
                data=video_data,
                file_name=filename,
                mime="video/mp4",
                use_container_width=True
            )
            st.success("✅ 다운로드 준비 완료!")
        else:
            st.error("❌ 영상 다운로드 실패!")

if __name__ == "__main__":
    main()