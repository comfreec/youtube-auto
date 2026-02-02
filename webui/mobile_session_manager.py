"""
모바일 세션 관리자 - 백그라운드 작업 상태 복원
"""
import json
import os
import time
from typing import Dict, Any, Optional
from loguru import logger
import streamlit as st

from app.services import state as sm
from app.models import const
from app.utils import utils


class MobileSessionManager:
    """모바일 세션 관리 클래스"""
    
    def __init__(self):
        self.session_dir = utils.storage_dir("mobile_sessions", create=True)
        
    def get_session_id(self) -> str:
        """브라우저 세션 기반 일관된 세션 ID 생성 - 화면 껐다 켜기 대응 강화"""
        if "mobile_session_id" not in st.session_state:
            import hashlib
            
            try:
                # 브라우저 세션 기반 일관된 ID 생성 전략
                session_info = []
                
                # 1. 브라우저 세션 스토리지 기반 고유 키 생성
                # 새로고침해도 유지되는 브라우저 세션 정보 활용
                try:
                    # Streamlit 세션 컨텍스트에서 안정적인 정보 추출
                    from streamlit.runtime.scriptrunner import get_script_run_ctx
                    from streamlit.runtime import get_instance
                    
                    ctx = get_script_run_ctx()
                    if ctx and hasattr(ctx, 'session_id'):
                        # Streamlit 내부 세션 ID 사용 (가장 안정적)
                        base_session_id = str(ctx.session_id)
                        session_info.append(base_session_id)
                        logger.info(f"Using Streamlit session ID: {base_session_id}")
                    else:
                        # 런타임에서 세션 정보 가져오기
                        runtime = get_instance()
                        if runtime and hasattr(runtime, '_session_mgr'):
                            sessions = runtime._session_mgr.list_sessions()
                            if sessions:
                                # 가장 최근 세션 사용
                                latest_session = sessions[-1]
                                session_info.append(str(latest_session.id))
                                logger.info(f"Using runtime session ID: {latest_session.id}")
                
                except Exception as e:
                    logger.warning(f"Could not get Streamlit session ID: {e}")
                
                # 2. 화면 껐다 켜기 대응: 더 안정적인 식별자 추가
                if not session_info:
                    try:
                        # 사용자 에이전트와 현재 시간 기반 (하루 단위로 변경)
                        import time
                        import streamlit.web.server.websocket_headers as wsh
                        
                        # 하루 단위 시드 (같은 날에는 같은 값)
                        day_seed = int(time.time() // 86400)  # 86400초 = 1일
                        session_info.append(str(day_seed))
                        
                        # 브라우저 정보 추가
                        headers = wsh.get_websocket_headers()
                        if headers and 'user-agent' in headers:
                            ua_hash = hashlib.md5(headers['user-agent'].encode()).hexdigest()[:8]
                            session_info.append(ua_hash)
                            
                        # IP 주소 기반 추가 식별 (ngrok 환경 고려)
                        if headers:
                            # X-Forwarded-For 헤더 확인 (ngrok 사용 시)
                            client_ip = headers.get('x-forwarded-for', headers.get('x-real-ip', 'unknown'))
                            if client_ip and client_ip != 'unknown':
                                ip_hash = hashlib.md5(client_ip.encode()).hexdigest()[:6]
                                session_info.append(ip_hash)
                                logger.info(f"Using client IP hash: {ip_hash}")
                            
                        logger.info(f"Using fallback session info: day={day_seed}, ua_hash={ua_hash if 'ua_hash' in locals() else 'none'}")
                        
                    except Exception as e:
                        logger.warning(f"Could not get browser info: {e}")
                
                # 3. 최종 폴백: 고정된 기본 세션 (화면 껐다 켜기에도 유지)
                if not session_info:
                    # 개발/테스트 환경에서 사용할 고정 세션
                    # 날짜 기반으로 하루마다 변경되지만 같은 날에는 유지
                    import datetime
                    today = datetime.date.today().strftime("%Y%m%d")
                    default_session = f"mobile_session_{today}"
                    session_info.append(default_session)
                    logger.warning(f"Using date-based default session: {default_session}")
                
                # 세션 ID 생성
                session_data = "_".join(session_info)
                session_id = hashlib.md5(session_data.encode()).hexdigest()[:16]
                
            except Exception as e:
                # 최종 폴백: 날짜 기반 고정 ID (화면 껐다 켜기에도 복원 가능)
                logger.error(f"Session ID generation failed: {e}")
                import datetime
                today = datetime.date.today().strftime("%Y%m%d")
                session_id = f"mobile_fallback_{today}"
            
            st.session_state["mobile_session_id"] = session_id
            logger.info(f"Generated mobile session ID: {session_id}")
        
        return st.session_state["mobile_session_id"]
    
    def save_generation_state(self, task_id: str, params: Dict[str, Any]):
        """영상 생성 상태를 파일에 저장 - ngrok 환경 최적화"""
        try:
            session_id = self.get_session_id()
            session_file = os.path.join(self.session_dir, f"{session_id}.json")
            
            # ngrok URL 정보 저장 (세션 복원 시 참고용)
            server_info = {}
            try:
                import streamlit as st
                if hasattr(st, 'get_option'):
                    base_url = st.get_option("server.baseUrlPath")
                    if base_url and "ngrok" in base_url:
                        server_info["ngrok_url"] = base_url
                        server_info["is_ngrok"] = True
            except:
                pass
            
            session_data = {
                "session_id": session_id,
                "task_id": task_id,
                "start_time": time.time(),
                "params": {
                    "video_subject": str(params.get("video_subject", "")),
                    "video_type": str(params.get("video_type", "shorts")),
                    "video_language": str(params.get("video_language", "ko-KR")),
                    "voice_name": str(params.get("voice_name", "")),
                },
                "status": "started",
                "last_update": time.time(),
                "server_info": server_info,  # ngrok 정보 추가
                "retry_count": 0  # 재시도 횟수 추가
            }
            
            # 안전한 파일 쓰기 (ngrok 환경에서 더 안정적)
            temp_file = session_file + ".tmp"
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2)
                
                # 원자적 파일 이동
                if os.path.exists(temp_file):
                    if os.path.exists(session_file):
                        os.remove(session_file)
                    os.rename(temp_file, session_file)
                    
                logger.info(f"Saved generation state for session {session_id}, task {task_id} (ngrok optimized)")
                
            except Exception as e:
                logger.error(f"Failed to write session file: {e}")
                # 임시 파일 정리
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
            
            # 세션 상태에도 저장 (메모리 백업)
            st.session_state["current_task_id"] = task_id
            st.session_state["generation_in_progress"] = True
            st.session_state["generation_start_time"] = session_data["start_time"]
            st.session_state["ngrok_session_backup"] = session_data  # ngrok용 백업
            
        except Exception as e:
            logger.error(f"Failed to save generation state: {e}")
            # 오류가 발생해도 영상 생성은 계속 진행되도록 함
    
    def update_generation_progress(self, task_id: str, progress: int, status: str):
        """영상 생성 진행 상태 업데이트"""
        try:
            session_id = self.get_session_id()
            session_file = os.path.join(self.session_dir, f"{session_id}.json")
            
            if os.path.exists(session_file):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    session_data.update({
                        "progress": int(progress),
                        "status": str(status),
                        "last_update": time.time()
                    })
                    
                    # 안전한 파일 쓰기
                    temp_file = session_file + ".tmp"
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(session_data, f, ensure_ascii=False, indent=2)
                    
                    if os.path.exists(temp_file):
                        if os.path.exists(session_file):
                            os.remove(session_file)
                        os.rename(temp_file, session_file)
                    
                except Exception as e:
                    logger.error(f"Failed to update session file: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to update generation progress: {e}")
            # 오류가 발생해도 영상 생성은 계속 진행되도록 함
    
    def complete_generation(self, task_id: str, video_file: str = None, error: str = None):
        """영상 생성 완료 처리"""
        try:
            session_id = self.get_session_id()
            session_file = os.path.join(self.session_dir, f"{session_id}.json")
            
            if os.path.exists(session_file):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    session_data.update({
                        "status": "completed" if video_file else "failed",
                        "video_file": str(video_file) if video_file else None,
                        "error": str(error) if error else None,
                        "completion_time": time.time(),
                        "last_update": time.time()
                    })
                    
                    # 안전한 파일 쓰기
                    temp_file = session_file + ".tmp"
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(session_data, f, ensure_ascii=False, indent=2)
                    
                    if os.path.exists(temp_file):
                        if os.path.exists(session_file):
                            os.remove(session_file)
                        os.rename(temp_file, session_file)
                    
                    # 세션 상태 업데이트
                    st.session_state["generation_in_progress"] = False
                    if video_file:
                        st.session_state["completed_video_file"] = video_file
                    
                    logger.info(f"Completed generation for session {session_id}, task {task_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to update session file: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to complete generation: {e}")
            # 오류가 발생해도 영상 생성은 계속 진행되도록 함
    
    def restore_session(self) -> Optional[Dict[str, Any]]:
        """이전 세션 상태 복원 - 화면 껐다 켜기 대응 강화"""
        try:
            session_id = self.get_session_id()
            session_file = os.path.join(self.session_dir, f"{session_id}.json")
            
            # 1. 정확한 세션 ID로 복구 시도
            if os.path.exists(session_file):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    # 24시간 이내의 세션만 복원
                    start_time = session_data.get("start_time", 0)
                    current_time = time.time()
                    time_diff = current_time - start_time
                    
                    if time_diff < 86400:  # 24시간
                        logger.info(f"Exact session restored: {session_id}")
                        return session_data
                    else:
                        logger.info(f"Session too old, removing: {session_id}")
                        os.remove(session_file)
                        
                except Exception as e:
                    logger.error(f"Failed to load exact session file: {e}")
                    try:
                        os.remove(session_file)
                    except:
                        pass
            
            # 2. 화면 껐다 켜기 대응: 더 적극적인 스마트 복구
            if not os.path.exists(self.session_dir):
                return None
            
            # 모든 활성 세션 수집
            active_sessions = []
            current_time = time.time()
            
            for filename in os.listdir(self.session_dir):
                if not filename.endswith('.json'):
                    continue
                    
                try:
                    filepath = os.path.join(self.session_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    start_time = data.get('start_time', 0)
                    age_hours = (current_time - start_time) / 3600
                    
                    # 24시간 이내의 세션만 고려
                    if age_hours < 24:
                        active_sessions.append({
                            'file': filename,
                            'session_id': data.get('session_id', 'unknown'),
                            'task_id': data.get('task_id', 'unknown'),
                            'status': data.get('status', 'unknown'),
                            'start_time': start_time,
                            'age_hours': age_hours,
                            'data': data,
                            'server_info': data.get('server_info', {}),  # ngrok 정보
                            'last_update': data.get('last_update', start_time)
                        })
                    else:
                        # 오래된 세션 파일 삭제
                        try:
                            os.remove(filepath)
                        except:
                            pass
                            
                except Exception as e:
                    logger.error(f"Error processing session file {filename}: {e}")
                    # 손상된 파일 삭제
                    try:
                        os.remove(os.path.join(self.session_dir, filename))
                    except:
                        pass
            
            if not active_sessions:
                return None
            
            # 3. 화면 껐다 켜기 상황에서 가장 적합한 세션 선택
            # 우선순위: 진행중 > 최근 업데이트 > 같은 ngrok URL > 최신
            
            # 진행 중인 세션 우선 (더 넓은 범위로 검색)
            in_progress_sessions = [s for s in active_sessions if 
                                  ('processing' in s['status'].lower() or 
                                   'generating' in s['status'].lower() or 
                                   'started' in s['status'].lower() or
                                   '진행' in s['status'] or 
                                   '%' in s['status'] or
                                   s['status'] == 'started')]
            
            if in_progress_sessions:
                # 가장 최근에 업데이트된 진행 중인 세션
                best_session = max(in_progress_sessions, key=lambda x: x['last_update'])
                logger.info(f"Restoring in-progress session (screen wake): {best_session['session_id']}")
                
                # 현재 세션 ID를 복구된 세션 ID로 업데이트
                st.session_state["mobile_session_id"] = best_session['session_id']
                
                return best_session['data']
            
            # 진행 중인 세션이 없으면 최근 세션 (화면 껐다 켜기 대응으로 시간 범위 확대)
            # 6시간 이내의 최근 세션까지 복구 (기존 1시간에서 확대)
            recent_sessions = [s for s in active_sessions if s['age_hours'] < 6.0]
            
            if recent_sessions:
                # 가장 최근에 업데이트된 세션
                latest_session = max(recent_sessions, key=lambda x: x['last_update'])
                logger.info(f"Restoring recent session (screen wake, extended range): {latest_session['session_id']}")
                
                # 현재 세션 ID를 복구된 세션 ID로 업데이트
                st.session_state["mobile_session_id"] = latest_session['session_id']
                
                return latest_session['data']
            
            # 마지막 시도: 오늘 생성된 모든 세션 중 가장 최근 것
            today_sessions = [s for s in active_sessions if s['age_hours'] < 24.0]
            if today_sessions:
                latest_today = max(today_sessions, key=lambda x: x['last_update'])
                logger.info(f"Restoring today's session (last resort): {latest_today['session_id']}")
                
                # 현재 세션 ID를 복구된 세션 ID로 업데이트
                st.session_state["mobile_session_id"] = latest_today['session_id']
                
                return latest_today['data']
                
        except Exception as e:
            logger.error(f"Failed to restore session: {e}")
        
        return None
    
    def get_active_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """활성 작업의 현재 상태 가져오기"""
        try:
            # 1. 메모리/Redis에서 작업 상태 확인
            task_info = sm.state.get_task(task_id)
            if task_info:
                return {
                    "progress": task_info.get("progress", 0),
                    "state": task_info.get("state", const.TASK_STATE_PROCESSING),
                    "message": task_info.get("message", ""),
                    "is_active": task_info.get("state") == const.TASK_STATE_PROCESSING,
                    "video_file": task_info.get("videos", [None])[0] if task_info.get("videos") else None
                }
            
            # 2. 작업 디렉토리에서 파일 확인
            task_dir = utils.task_dir(task_id)
            if os.path.exists(task_dir):
                # 완료된 영상 파일 확인
                import glob
                video_patterns = [
                    os.path.join(task_dir, "final-*.mp4"),
                    os.path.join(task_dir, "combined-*.mp4"),
                    os.path.join(task_dir, "*.mp4")
                ]
                
                for pattern in video_patterns:
                    files = glob.glob(pattern)
                    if files:
                        return {
                            "progress": 100,
                            "state": const.TASK_STATE_COMPLETE,
                            "message": "영상 생성 완료",
                            "is_active": False,
                            "video_file": files[0]
                        }
                
                # 3. 진행 중인 작업으로 추정 (디렉토리는 있지만 완료 파일이 없음)
                # 오디오 파일이나 스크립트 파일이 있으면 진행 중으로 판단
                audio_file = os.path.join(task_dir, "audio.mp3")
                script_file = os.path.join(task_dir, "script.json")
                
                if os.path.exists(audio_file) or os.path.exists(script_file):
                    # 진행률 추정 (파일 존재 여부로)
                    estimated_progress = 20  # 기본값
                    if os.path.exists(audio_file):
                        estimated_progress = 40
                    if os.path.exists(os.path.join(task_dir, "subtitle.srt")):
                        estimated_progress = 60
                    
                    return {
                        "progress": estimated_progress,
                        "state": const.TASK_STATE_PROCESSING,
                        "message": f"영상 생성 진행 중... (추정 {estimated_progress}%)",
                        "is_active": True,
                        "video_file": None
                    }
            
        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
        
        return None
    
    def cleanup_old_sessions(self):
        """오래된 세션 파일 정리 (24시간 이상)"""
        try:
            current_time = time.time()
            for filename in os.listdir(self.session_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.session_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            session_data = json.load(f)
                        
                        if current_time - session_data.get("start_time", 0) > 86400:
                            os.remove(filepath)
                            logger.info(f"Cleaned up old session: {filename}")
                            
                    except Exception:
                        # 손상된 파일 삭제
                        os.remove(filepath)
                        
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")


# 전역 세션 매니저 인스턴스
mobile_session_manager = MobileSessionManager()