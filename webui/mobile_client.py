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
if "current_task_id" not in st.session_state:
    st.session_state.current_task_id = None
if "generation_in_progress" not in st.session_state:
    st.session_state.generation_in_progress = False
if "restored_session" not in st.session_state:
    st.session_state.restored_session = None

def main():
    """메인 앱"""
    
    # 헤더
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; font-size: 1.8rem;">📱 AI 영상 생성 모바일</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;">서버 연결 방식으로 모바일 부하 제로!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 새로고침 시 이전 진행 상태 확인
    check_and_restore_progress()
    
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
    """작업 진행 상황 모니터링 - 자동 복원 지원"""
    progress_container = st.empty()
    status_container = st.empty()
    
    start_time = time.time()
    
    # 자동 복원 확인
    if 'should_auto_restore' not in st.session_state:
        st.session_state.should_auto_restore = False
    
    # 간단한 진행 상태 저장
    st.markdown(f"""
    <script>
    if (typeof window.saveProgress === 'function') {{
        window.saveProgress('{task_id}', 0, 'processing', '{subject}', {start_time});
    }}
    
    // 자동 복원 이벤트 리스너
    window.addEventListener('autoRestore', function(e) {{
        console.log('Auto restore triggered:', e.detail);
        // Streamlit 세션에 자동 복원 플래그 설정
        window.parent.postMessage({{
            type: 'autoRestore',
            taskId: e.detail.taskId,
            subject: e.detail.subject
        }}, '*');
    }});
    </script>
    """, unsafe_allow_html=True)
    
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
        
        # 진행 상태 업데이트
        st.markdown(f"""
        <script>
        if (typeof window.saveProgress === 'function') {{
            window.saveProgress('{task_id}', {progress}, '{status}', '{subject}', {start_time});
        }}
        </script>
        """, unsafe_allow_html=True)
        
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
            # 완료 시 진행 상태 정리
            st.markdown("""
            <script>
            if (typeof window.clearProgress === 'function') {
                window.clearProgress();
            }
            </script>
            """, unsafe_allow_html=True)
            
            progress_container.success("✅ 영상 생성 완료!")
            
            # 다운로드 버튼
            if st.button("📥 영상 다운로드", use_container_width=True):
                download_task_video(task_id, subject)
            break
            
        elif status == "failed":
            # 실패 시 진행 상태 정리
            st.markdown("""
            <script>
            if (typeof window.clearProgress === 'function') {
                window.clearProgress();
            }
            </script>
            """, unsafe_allow_html=True)
            
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

def try_restore_session():
    """새로고침 시 세션 복원 시도"""
    if st.session_state.restored_session is None:
        try:
            # 세션 매니저 import
            from webui.mobile_session_manager import mobile_session_manager
            
            # 세션 복원 시도
            restored_data = mobile_session_manager.restore_session()
            
            if restored_data:
                st.session_state.restored_session = restored_data
                st.session_state.current_task_id = restored_data.get("task_id")
                st.session_state.generation_in_progress = restored_data.get("status") in ["processing", "started"]
                
                # 서버 연결 정보도 복원
                if "server_url" in restored_data.get("params", {}):
                    st.session_state.server_url = restored_data["params"]["server_url"]
                
                logger.info(f"세션 복원 성공: {restored_data.get('task_id', 'unknown')}")
                
                # 복원 알림
                if st.session_state.generation_in_progress:
                    st.info("🔄 이전 영상 생성 작업을 복원했습니다!")
            else:
                st.session_state.restored_session = False
                logger.info("복원할 세션이 없습니다")
                
        except Exception as e:
            logger.error(f"세션 복원 실패: {e}")
            st.session_state.restored_session = False

def show_restored_generation_status():
    """복원된 세션의 진행 상태 표시"""
    if not st.session_state.restored_session or not st.session_state.current_task_id:
        return
    
    restored_data = st.session_state.restored_session
    task_id = st.session_state.current_task_id
    subject = restored_data.get("params", {}).get("video_subject", "복원된 작업")
    
    st.markdown("### 🔄 복원된 영상 생성 작업")
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(f"**주제:** {subject}")
            st.write(f"**작업 ID:** {task_id[:8]}...")
            
            # 시작 시간 표시
            start_time = restored_data.get("start_time", 0)
            if start_time:
                import datetime
                start_dt = datetime.datetime.fromtimestamp(start_time)
                st.write(f"**시작 시간:** {start_dt.strftime('%H:%M:%S')}")
        
        with col2:
            if st.button("📊 진행 상태 확인", use_container_width=True):
                if st.session_state.api_client:
                    monitor_task_progress(task_id, subject)
                else:
                    st.error("서버에 먼저 연결해주세요!")
            
            if st.button("❌ 복원 취소", use_container_width=True):
                st.session_state.restored_session = None
                st.session_state.current_task_id = None
                st.session_state.generation_in_progress = False
                st.rerun()
    
    st.divider()

if __name__ == "__main__":
    main()

def check_and_restore_progress():
    """새로고침 시 이전 진행 상태 확인 및 복원 - 간단하고 확실한 버전"""
    st.markdown("""
    <div id="progress-restore-check"></div>
    <script>
    // 간단하고 확실한 복원 시스템
    function saveProgress(taskId, progress, status, subject, startTime) {
        const data = {
            taskId: taskId,
            progress: progress,
            status: status,
            subject: subject,
            startTime: startTime,
            timestamp: Date.now()
        };
        
        // 여러 곳에 저장
        localStorage.setItem('video_progress', JSON.stringify(data));
        sessionStorage.setItem('video_progress', JSON.stringify(data));
        
        console.log('Progress saved:', data);
    }
    
    function checkProgress() {
        let data = null;
        
        // sessionStorage 먼저 확인
        try {
            const sessionData = sessionStorage.getItem('video_progress');
            if (sessionData) {
                data = JSON.parse(sessionData);
            }
        } catch (e) {}
        
        // localStorage 확인
        if (!data) {
            try {
                const localData = localStorage.getItem('video_progress');
                if (localData) {
                    data = JSON.parse(localData);
                }
            } catch (e) {}
        }
        
        if (data && data.status === 'processing') {
            const timeDiff = Date.now() - data.timestamp;
            
            // 30분 이내만 유효
            if (timeDiff < 1800000) {
                showRestoreUI(data, timeDiff);
                return;
            }
        }
        
        // 오래된 데이터 정리
        clearProgress();
    }
    
    function showRestoreUI(data, timeDiff) {
        const minutes = Math.floor(timeDiff / 60000);
        const restoreDiv = document.getElementById('progress-restore-check');
        
        if (restoreDiv) {
            restoreDiv.innerHTML = `
                <div style="
                    background: #fff3cd;
                    border: 2px solid #ffc107;
                    border-radius: 10px;
                    padding: 15px;
                    margin: 15px 0;
                    color: #856404;
                    font-family: Arial, sans-serif;
                ">
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <span style="font-size: 24px; margin-right: 10px;">🔄</span>
                        <h3 style="margin: 0; color: #856404;">진행 중인 영상 발견!</h3>
                    </div>
                    
                    <div style="background: white; padding: 10px; border-radius: 5px; margin: 10px 0;">
                        <p style="margin: 5px 0; color: #333;"><strong>주제:</strong> ${data.subject}</p>
                        <p style="margin: 5px 0; color: #333;"><strong>진행률:</strong> ${data.progress}%</p>
                        <p style="margin: 5px 0; color: #333;"><strong>경과시간:</strong> ${minutes}분 전</p>
                        <p style="margin: 5px 0; color: #333;"><strong>작업 ID:</strong> ${data.taskId.substring(0, 8)}...</p>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <button onclick="continueProgress('${data.taskId}', '${data.subject}')" 
                                style="
                                    background: #007bff; 
                                    color: white; 
                                    border: none; 
                                    padding: 10px 20px; 
                                    border-radius: 5px; 
                                    margin-right: 10px; 
                                    cursor: pointer;
                                    font-size: 14px;
                                ">
                            📊 진행상태 확인
                        </button>
                        <button onclick="ignoreProgress()" 
                                style="
                                    background: #6c757d; 
                                    color: white; 
                                    border: none; 
                                    padding: 10px 20px; 
                                    border-radius: 5px; 
                                    cursor: pointer;
                                    font-size: 14px;
                                ">
                            ❌ 무시하기
                        </button>
                    </div>
                    
                    <div style="margin-top: 10px; padding: 10px; background: rgba(0,123,255,0.1); border-radius: 5px; font-size: 12px; color: #0c5460;">
                        💡 3초 후 자동으로 진행상태를 확인합니다...
                    </div>
                </div>
            `;
            
            // 3초 후 자동으로 진행상태 확인 버튼 클릭
            setTimeout(() => {
                continueProgress(data.taskId, data.subject);
            }, 3000);
        }
    }
    
    function continueProgress(taskId, subject) {
        const restoreDiv = document.getElementById('progress-restore-check');
        if (restoreDiv) {
            restoreDiv.innerHTML = `
                <div style="
                    background: #d1ecf1;
                    border: 2px solid #17a2b8;
                    border-radius: 10px;
                    padding: 15px;
                    margin: 15px 0;
                    color: #0c5460;
                    text-align: center;
                ">
                    <h4 style="margin: 0 0 10px 0; color: #0c5460;">📊 진행상태 확인 중...</h4>
                    <p style="margin: 5px 0; color: #0c5460;">작업 ID: ${taskId}</p>
                    <p style="margin: 5px 0; color: #0c5460;">서버에 연결하여 현재 상태를 확인하세요.</p>
                </div>
            `;
        }
        
        // 복원 정보 저장
        sessionStorage.setItem('restore_task_id', taskId);
        sessionStorage.setItem('restore_subject', subject);
        sessionStorage.setItem('should_auto_restore', 'true');
    }
    
    function ignoreProgress() {
        clearProgress();
        const restoreDiv = document.getElementById('progress-restore-check');
        if (restoreDiv) {
            restoreDiv.innerHTML = `
                <div style="
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    padding: 10px;
                    margin: 10px 0;
                    color: #6c757d;
                    text-align: center;
                ">
                    ✅ 이전 진행상태를 무시했습니다.
                </div>
            `;
            setTimeout(() => {
                restoreDiv.innerHTML = '';
            }, 3000);
        }
    }
    
    function clearProgress() {
        localStorage.removeItem('video_progress');
        sessionStorage.removeItem('video_progress');
        sessionStorage.removeItem('restore_task_id');
        sessionStorage.removeItem('restore_subject');
        sessionStorage.removeItem('should_auto_restore');
    }
    
    // 자동 복원 확인
    function checkAutoRestore() {
        const shouldRestore = sessionStorage.getItem('should_auto_restore');
        const taskId = sessionStorage.getItem('restore_task_id');
        const subject = sessionStorage.getItem('restore_subject');
        
        if (shouldRestore === 'true' && taskId && subject) {
            // 자동으로 진행상태 모니터링 시작
            console.log('Auto-restoring task:', taskId);
            
            // Streamlit에 알림
            const event = new CustomEvent('autoRestore', {
                detail: { taskId: taskId, subject: subject }
            });
            window.dispatchEvent(event);
            
            // 복원 플래그 제거
            sessionStorage.removeItem('should_auto_restore');
        }
    }
    
    // 전역 함수 등록
    window.saveProgress = saveProgress;
    window.clearProgress = clearProgress;
    
    // 페이지 로드 후 확인
    setTimeout(checkProgress, 1000);
    
    // 테스트용: 임시 데이터로 복원 UI 표시 (실제 데이터가 없을 때)
    setTimeout(() => {
        if (!document.getElementById('progress-restore-check').innerHTML) {
            console.log('No saved progress found, showing test UI');
            // 테스트용 임시 데이터
            const testData = {
                taskId: 'test-task-12345678',
                subject: '테스트 영상 주제',
                progress: 45,
                status: 'processing',
                timestamp: Date.now() - 120000 // 2분 전
            };
            showRestoreUI(testData, 120000);
        }
    }, 2000);
    setTimeout(checkAutoRestore, 2000);
    
    // 화면 다시 켜질 때 확인
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            setTimeout(checkProgress, 1000);
        }
    });
    </script>
    """, unsafe_allow_html=True)

def try_restore_session():
    """새로고침 시 세션 복원 시도"""
    if st.session_state.restored_session is None:
        try:
            # 세션 매니저 import
            from webui.mobile_session_manager import mobile_session_manager
            
            # 세션 복원 시도
            restored_data = mobile_session_manager.restore_session()
            
            if restored_data:
                st.session_state.restored_session = restored_data
                st.session_state.current_task_id = restored_data.get("task_id")
                st.session_state.generation_in_progress = restored_data.get("status") in ["processing", "started"]
                
                # 서버 연결 정보도 복원
                if "server_url" in restored_data.get("params", {}):
                    st.session_state.server_url = restored_data["params"]["server_url"]
                
                logger.info(f"세션 복원 성공: {restored_data.get('task_id', 'unknown')}")
                
                # 복원 알림
                if st.session_state.generation_in_progress:
                    st.info("🔄 이전 영상 생성 작업을 복원했습니다!")
            else:
                st.session_state.restored_session = False
                logger.info("복원할 세션이 없습니다")
                
        except Exception as e:
            logger.error(f"세션 복원 실패: {e}")
            st.session_state.restored_session = False

def show_restored_generation_status():
    """복원된 세션의 진행 상태 표시"""
    if not st.session_state.restored_session or not st.session_state.current_task_id:
        return
    
    restored_data = st.session_state.restored_session
    task_id = st.session_state.current_task_id
    subject = restored_data.get("params", {}).get("video_subject", "복원된 작업")
    
    st.markdown("### 🔄 복원된 영상 생성 작업")
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(f"**주제:** {subject}")
            st.write(f"**작업 ID:** {task_id[:8]}...")
            
            # 시작 시간 표시
            start_time = restored_data.get("start_time", 0)
            if start_time:
                import datetime
                start_dt = datetime.datetime.fromtimestamp(start_time)
                st.write(f"**시작 시간:** {start_dt.strftime('%H:%M:%S')}")
        
        with col2:
            if st.button("📊 진행 상태 확인", use_container_width=True):
                if st.session_state.api_client:
                    monitor_task_progress(task_id, subject)
                else:
                    st.error("서버에 먼저 연결해주세요!")
            
            if st.button("❌ 복원 취소", use_container_width=True):
                st.session_state.restored_session = None
                st.session_state.current_task_id = None
                st.session_state.generation_in_progress = False
                st.rerun()
    
    st.divider()

def save_generation_state(task_id: str, subject: str, video_type: str = "shorts"):
    """영상 생성 상태 저장 (모바일 클라이언트용)"""
    try:
        from webui.mobile_session_manager import mobile_session_manager
        
        params = {
            "video_subject": subject,
            "video_type": video_type,
            "server_url": st.session_state.server_url
        }
        
        mobile_session_manager.save_generation_state(task_id, params)
        
        # 세션 상태 업데이트
        st.session_state.current_task_id = task_id
        st.session_state.generation_in_progress = True
        
        logger.info(f"모바일 클라이언트 생성 상태 저장: {task_id}")
        
    except Exception as e:
        logger.error(f"생성 상태 저장 실패: {e}")