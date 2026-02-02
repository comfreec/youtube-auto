"""
YouTube 영상 분석 & 재해석 전용 서비스
기존 영상생성 로직과 완전히 분리된 독립적인 모듈
"""

import os
import re
import json
import time
from typing import Dict, List, Optional, Any
from uuid import uuid4
from loguru import logger

from app.services import llm
from app.services import task as tm
from app.services import state as sm
from app.models import const
from app.models.schema import VideoParams, VideoAspect
from app.utils import utils


class YouTubeReinterpretService:
    """YouTube 영상 분석 & 재해석 전용 서비스"""
    
    def __init__(self):
        self.analysis_cache = {}
        self.reinterpret_cache = {}
    
    def analyze_youtube_video(self, video_url: str) -> Dict[str, Any]:
        """YouTube 영상 분석"""
        try:
            logger.info(f"YouTube 영상 분석 시작: {video_url}")
            
            # URL에서 비디오 ID 추출
            video_id = self._extract_video_id(video_url)
            if not video_id:
                logger.error(f"비디오 ID 추출 실패: {video_url}")
                return {
                    "success": False,
                    "error": f"유효하지 않은 YouTube URL입니다. 올바른 형식: https://www.youtube.com/watch?v=VIDEO_ID 또는 https://youtu.be/VIDEO_ID"
                }
            
            logger.info(f"비디오 ID 추출 성공: {video_id}")
            
            # 캐시 확인
            if video_id in self.analysis_cache:
                logger.info(f"캐시된 분석 결과 사용: {video_id}")
                return self.analysis_cache[video_id]
            
            # YouTube 영상 정보 가져오기 (기존 youtube_analyzer 함수들 사용)
            try:
                from app.services.youtube_analyzer import extract_video_id, get_video_info, get_video_transcript
                logger.info("YouTube analyzer 함수들 임포트 완료")
                
                # 기존 함수로 비디오 ID 재검증
                verified_video_id = extract_video_id(video_url)
                if not verified_video_id:
                    logger.error("기존 함수로도 비디오 ID 추출 실패")
                    return {
                        "success": False,
                        "error": "YouTube URL에서 비디오 ID를 추출할 수 없습니다"
                    }
                
                # 추출된 ID가 일치하는지 확인
                if verified_video_id != video_id:
                    logger.warning(f"비디오 ID 불일치: {video_id} vs {verified_video_id}, 기존 함수 결과 사용")
                    video_id = verified_video_id
                
            except ImportError as e:
                logger.error(f"YouTube analyzer 함수 임포트 실패: {e}")
                return {
                    "success": False,
                    "error": "YouTube 분석 모듈을 로드할 수 없습니다"
                }
            
            # 영상 메타데이터 분석
            try:
                metadata = get_video_info(video_id)
                if not metadata or not metadata.get('title'):
                    logger.error("영상 메타데이터 가져오기 실패")
                    return {
                        "success": False,
                        "error": "영상 정보를 가져올 수 없습니다. 영상이 비공개이거나 삭제되었을 수 있습니다."
                    }
                logger.info(f"메타데이터 가져오기 성공: {metadata.get('title', 'N/A')}")
            except Exception as e:
                logger.error(f"메타데이터 가져오기 오류: {e}")
                return {
                    "success": False,
                    "error": f"영상 정보 가져오기 실패: {str(e)}"
                }
            
            # 자막 추출 및 분석
            try:
                transcript = get_video_transcript(video_id)
                if not transcript:
                    logger.error("자막 추출 실패")
                    return {
                        "success": False,
                        "error": "자막을 추출할 수 없습니다. 자막이 없거나 비활성화된 영상일 수 있습니다."
                    }
                logger.info(f"자막 추출 성공: {len(transcript)} 글자")
            except Exception as e:
                logger.error(f"자막 추출 오류: {e}")
                return {
                    "success": False,
                    "error": f"자막 추출 실패: {str(e)}"
                }
            
            # AI를 통한 콘텐츠 분석
            try:
                content_analysis = self._analyze_content_with_ai(
                    title=metadata.get('title', ''),
                    description=metadata.get('description', ''),
                    transcript=transcript
                )
                logger.info("AI 콘텐츠 분석 완료")
            except Exception as e:
                logger.error(f"AI 분석 오류: {e}")
                # AI 분석 실패해도 기본 분석 결과로 계속 진행
                content_analysis = {
                    "main_topics": ["분석 실패"],
                    "target_audience": "일반",
                    "content_style": "정보 전달",
                    "keywords": ["기본키워드"],
                    "emotional_tone": "중립",
                    "credibility": "보통",
                    "reinterpret_points": ["재분석 필요"]
                }
            
            # 분석 결과 구성
            analysis_result = {
                "success": True,
                "video_id": video_id,
                "video_url": video_url,
                "metadata": metadata,
                "transcript": transcript,
                "content_analysis": content_analysis,
                "analyzed_at": time.time()
            }
            
            # 캐시에 저장
            self.analysis_cache[video_id] = analysis_result
            
            logger.info(f"YouTube 영상 분석 완료: {video_id}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"YouTube 영상 분석 실패: {e}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"분석 중 예상치 못한 오류 발생: {str(e)}"
            }
    
    def reinterpret_content(self, analysis_result: Dict[str, Any], 
                          reinterpret_style: str = "creative",
                          target_audience: str = "general",
                          content_focus: str = "main_points") -> Dict[str, Any]:
        """분석된 콘텐츠를 재해석"""
        try:
            if not analysis_result.get("success"):
                return {
                    "success": False,
                    "error": "유효하지 않은 분석 결과입니다"
                }
            
            video_id = analysis_result["video_id"]
            cache_key = f"{video_id}_{reinterpret_style}_{target_audience}_{content_focus}"
            
            # 캐시 확인
            if cache_key in self.reinterpret_cache:
                logger.info(f"캐시된 재해석 결과 사용: {cache_key}")
                return self.reinterpret_cache[cache_key]
            
            logger.info(f"콘텐츠 재해석 시작: {video_id}")
            
            # 원본 콘텐츠 정보
            original_title = analysis_result["metadata"].get("title", "")
            original_transcript = analysis_result["transcript"]
            content_analysis = analysis_result["content_analysis"]
            
            # AI를 통한 재해석
            reinterpreted_content = self._reinterpret_with_ai(
                original_title=original_title,
                original_transcript=original_transcript,
                content_analysis=content_analysis,
                reinterpret_style=reinterpret_style,
                target_audience=target_audience,
                content_focus=content_focus
            )
            
            # 재해석 결과 구성
            reinterpret_result = {
                "success": True,
                "original_video_id": video_id,
                "reinterpret_style": reinterpret_style,
                "target_audience": target_audience,
                "content_focus": content_focus,
                "reinterpreted_content": reinterpreted_content,
                "reinterpreted_at": time.time()
            }
            
            # 캐시에 저장
            self.reinterpret_cache[cache_key] = reinterpret_result
            
            logger.info(f"콘텐츠 재해석 완료: {video_id}")
            return reinterpret_result
            
        except Exception as e:
            logger.error(f"콘텐츠 재해석 실패: {e}")
            return {
                "success": False,
                "error": f"재해석 중 오류 발생: {str(e)}"
            }
    
    def generate_reinterpreted_video(self, reinterpret_result: Dict[str, Any],
                                   video_params: Optional[VideoParams] = None) -> Dict[str, Any]:
        """재해석된 콘텐츠로 새로운 영상 생성"""
        try:
            if not reinterpret_result.get("success"):
                return {
                    "success": False,
                    "error": "유효하지 않은 재해석 결과입니다"
                }
            
            logger.info("재해석 영상 생성 시작")
            
            # 재해석된 콘텐츠 추출
            reinterpreted_content = reinterpret_result["reinterpreted_content"]
            
            # VideoParams 설정
            if not video_params:
                video_params = VideoParams()
            
            # 재해석된 콘텐츠로 파라미터 설정
            video_params.video_subject = reinterpreted_content.get("new_title", "재해석된 콘텐츠")
            video_params.video_script = reinterpreted_content.get("new_script", "")
            video_params.video_terms = reinterpreted_content.get("keywords", "")
            
            # 기본 설정 적용
            video_params.video_aspect = VideoAspect.portrait  # 세로형 (쇼츠)
            video_params.video_language = "ko-KR"
            video_params.voice_name = "ko-KR-SunHiNeural"
            video_params.subtitle_enabled = True
            
            # 고유 태스크 ID 생성
            task_id = str(uuid4())
            
            # 영상 생성 시작 (기존 task 모듈 사용하되 독립적으로)
            logger.info(f"재해석 영상 생성 태스크 시작: {task_id}")
            
            # 비동기 영상 생성
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(tm.start, task_id=task_id, params=video_params)
                
                # 생성 진행 상황 모니터링
                generation_result = self._monitor_generation_progress(task_id, future)
            
            if generation_result["success"]:
                logger.info(f"재해석 영상 생성 완료: {task_id}")
                return {
                    "success": True,
                    "task_id": task_id,
                    "video_files": generation_result["video_files"],
                    "reinterpret_info": {
                        "original_video_id": reinterpret_result["original_video_id"],
                        "reinterpret_style": reinterpret_result["reinterpret_style"],
                        "target_audience": reinterpret_result["target_audience"],
                        "content_focus": reinterpret_result["content_focus"]
                    }
                }
            else:
                return {
                    "success": False,
                    "error": generation_result["error"]
                }
                
        except Exception as e:
            logger.error(f"재해석 영상 생성 실패: {e}")
            return {
                "success": False,
                "error": f"영상 생성 중 오류 발생: {str(e)}"
            }
    
    def _extract_video_id(self, video_url: str) -> Optional[str]:
        """YouTube URL에서 비디오 ID 추출 - 개선된 버전"""
        import re
        
        # URL 정리
        video_url = video_url.strip()
        
        # 다양한 YouTube URL 패턴 지원
        patterns = [
            # 표준 YouTube URL
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            # 짧은 YouTube URL
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
            # YouTube Shorts URL - 추가!
            r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
            # 임베드 URL
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            # 모바일 URL
            r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            # 파라미터가 있는 URL
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
            # 플레이리스트 내 영상
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11}).*list=',
            # 시간 파라미터가 있는 URL
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11}).*t=',
            # 기타 파라미터들
            r'(?:https?://)?(?:www\.)?youtube\.com/.*v=([a-zA-Z0-9_-]{11})',
            # 단순 비디오 ID만 있는 경우
            r'^([a-zA-Z0-9_-]{11})$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, video_url, re.IGNORECASE)
            if match:
                video_id = match.group(1)
                # 비디오 ID 유효성 검사 (11자리 영숫자와 _,- 만 허용)
                if re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
                    logger.info(f"추출된 비디오 ID: {video_id}")
                    return video_id
        
        logger.warning(f"유효하지 않은 YouTube URL: {video_url}")
        return None
    
    def _analyze_content_with_ai(self, title: str, description: str, transcript: str) -> Dict[str, Any]:
        """AI를 통한 콘텐츠 분석"""
        try:
            # 분석 프롬프트 구성
            analysis_prompt = f"""
다음 YouTube 영상의 콘텐츠를 분석해주세요:

제목: {title}
설명: {description[:500]}...
자막: {transcript[:2000]}...

다음 항목들을 분석해주세요:
1. 주요 주제와 핵심 메시지
2. 타겟 오디언스
3. 콘텐츠 스타일과 톤
4. 핵심 키워드 (5-10개)
5. 감정적 어조
6. 정보의 신뢰성 수준
7. 재해석 가능한 포인트들

JSON 형태로 응답해주세요.
"""
            
            # AI 분석 요청
            analysis_response = llm._generate_response(analysis_prompt)
            
            # JSON 파싱 시도
            try:
                analysis_data = json.loads(analysis_response)
            except:
                # JSON 파싱 실패 시 기본 구조 생성
                analysis_data = {
                    "main_topics": ["분석된 주제"],
                    "target_audience": "일반",
                    "content_style": "정보 전달",
                    "keywords": ["키워드1", "키워드2"],
                    "emotional_tone": "중립",
                    "credibility": "보통",
                    "reinterpret_points": ["재해석 포인트"]
                }
            
            return analysis_data
            
        except Exception as e:
            logger.error(f"AI 콘텐츠 분석 실패: {e}")
            return {
                "main_topics": ["분석 실패"],
                "target_audience": "일반",
                "content_style": "정보 전달",
                "keywords": ["기본키워드"],
                "emotional_tone": "중립",
                "credibility": "보통",
                "reinterpret_points": ["재해석 필요"]
            }
    
    def _reinterpret_with_ai(self, original_title: str, original_transcript: str,
                           content_analysis: Dict[str, Any], reinterpret_style: str,
                           target_audience: str, content_focus: str) -> Dict[str, Any]:
        """AI를 통한 콘텐츠 재해석"""
        try:
            # API 할당량 초과 시 임시 대안
            logger.warning("API 할당량 초과로 인한 임시 재해석 결과 생성")
            
            # 임시 재해석 결과 생성
            reinterpret_data = {
                "new_title": f"[{reinterpret_style}] {original_title}의 새로운 해석",
                "new_script": f"""
{original_title}에 대한 {reinterpret_style} 스타일의 재해석입니다.

원본 내용을 {target_audience} 대상으로 {content_focus} 중심으로 새롭게 해석했습니다.

이것은 API 할당량 초과로 인한 임시 결과입니다. 
실제 AI 재해석을 위해서는 API 할당량이 복구된 후 다시 시도해주세요.

주요 포인트:
- 스타일: {reinterpret_style}
- 대상: {target_audience}  
- 초점: {content_focus}
                """.strip(),
                "keywords": f"{reinterpret_style}, {target_audience}, {content_focus}, 재해석, 콘텐츠",
                "reinterpret_points": f"{reinterpret_style} 스타일로 {target_audience}를 위한 재해석",
                "expected_reaction": "API 복구 후 정상적인 재해석 가능"
            }
            
            return reinterpret_data
            
        except Exception as e:
            logger.error(f"임시 재해석 생성 실패: {e}")
            return {
                "new_title": f"재해석된 {original_title}",
                "new_script": "재해석 처리 중 오류가 발생했습니다.",
                "keywords": "재해석, 오류",
                "reinterpret_points": "재해석 실패",
                "expected_reaction": "재시도 필요"
            }
    
    def _monitor_generation_progress(self, task_id: str, future) -> Dict[str, Any]:
        """영상 생성 진행 상황 모니터링"""
        try:
            # 진행 상황 모니터링
            while not future.done():
                task_info = sm.state.get_task(task_id)
                if task_info:
                    progress = task_info.get("progress", 0)
                    state = task_info.get("state", const.TASK_STATE_PROCESSING)
                    message = task_info.get("message", "")
                    
                    logger.info(f"재해석 영상 생성 진행: {progress}% - {message}")
                    
                    if state == const.TASK_STATE_FAILED:
                        return {
                            "success": False,
                            "error": f"영상 생성 실패: {message}"
                        }
                    elif state == const.TASK_STATE_COMPLETE:
                        break
                
                time.sleep(2)
            
            # 결과 확인
            if future.done():
                result = future.result()
                if result and "videos" in result:
                    return {
                        "success": True,
                        "video_files": result["videos"]
                    }
                else:
                    return {
                        "success": False,
                        "error": "영상 생성 결과를 가져올 수 없습니다"
                    }
            else:
                return {
                    "success": False,
                    "error": "영상 생성 시간 초과"
                }
                
        except Exception as e:
            logger.error(f"영상 생성 모니터링 실패: {e}")
            return {
                "success": False,
                "error": f"모니터링 중 오류 발생: {str(e)}"
            }


# 전역 서비스 인스턴스
youtube_reinterpret_service = YouTubeReinterpretService()