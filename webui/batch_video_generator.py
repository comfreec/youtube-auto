"""
배치 영상 생성 함수
일반 영상 생성 로직을 그대로 사용
"""

import os
import glob
import concurrent.futures
from uuid import uuid4
from loguru import logger
import streamlit as st

from app.models.schema import VideoParams
from app.services import task as tm
from app.services import llm
from app.utils import utils
from app.config import config


def generate_single_video(title: str, video_type: str, language: str, duration: int, style: str, auto_upload: bool = False, task_id: str = None, script: str = None, terms: list = None) -> dict:
    """단일 영상 생성 (일반 영상 생성 로직 그대로 사용)"""
    
    # Task ID 생성 (외부에서 제공되지 않은 경우에만)
    if not task_id:
        task_id = str(uuid4())
    
    try:
        logger.info(f"Starting video generation for: {title} with task_id: {task_id}")
        
        # duration에 따라 paragraph_number 동적 설정
        if video_type == 'longform':
            paragraph_num = 4
        else:  # shorts
            # 60초 쇼츠면 3문단, 30초 이하면 2문단, 15초 이하면 1문단
            if duration >= 60:
                paragraph_num = 3
            elif duration >= 30:
                paragraph_num = 2
            else:
                paragraph_num = 1
        
        logger.info(f"📝 Duration: {duration}초, Video type: {video_type}, Paragraph number: {paragraph_num}")
        
        # 일반 영상 생성과 완전히 동일한 파라미터 설정
        params_dict = {
            'video_subject': title,  # 필수 필드
            'video_script': "",  # 일반 영상처럼 빈 문자열로 설정하여 새로 생성하도록 함
            'video_terms': terms,  # 미리 생성된 키워드가 있으면 사용
            'video_aspect': '9:16' if video_type == 'shorts' else '16:9',
            'video_concat_mode': 'random',
            'video_transition_mode': 'None',  # 문자열로 설정
            'video_clip_duration': 3 if video_type == 'shorts' else 5,
            'video_count': 1,  # 일반 영상과 동일하게 1개만 생성
            'video_source': 'pexels',  # 픽셀즈 사용
            'video_materials': None,
            'use_segment_matching': True,  # 세그먼트 기반 배경영상 매칭 활성화
            'target_segment_count': None,  # 자동 계산
            'custom_audio_file': None,
            'video_language': language,
            'voice_name': 'ko-KR-InJoonNeural' if language == 'ko-KR' else 'en-US-JennyNeural',
            'voice_volume': 1.0,
            'voice_rate': 1.0,
            'bgm_type': 'random',
            'bgm_file': '',
            'bgm_volume': 0.05,  # 성공한 영상과 동일하게 설정
            'subtitle_enabled': True,
            'subtitle_position': 'bottom',
            'custom_position': 75.0,
            'font_name': 'STHeitiMedium.ttc',
            'text_fore_color': '#FFFFFF',
            'text_background_color': True,
            'font_size': 45,  # 성공한 영상과 동일하게 설정
            'stroke_color': '#000000',
            'stroke_width': 1.5,
            'n_threads': 2,
            'paragraph_number': paragraph_num
        }
        
        params = VideoParams(**params_dict)
        
        # 2. API 키 검증 (일반 영상 생성과 동일)
        if params.video_source == "pexels":
            if not config.app.get("pexels_api_keys"):
                if config.app.get("pixabay_api_keys"):
                    params.video_source = "pixabay"
                else:
                    raise Exception("Pexels 또는 Pixabay API 키가 필요합니다")
        
        # 3. 일반 영상 생성과 완전히 동일한 방식으로 영상 생성
        logger.info(f"Starting task execution for: {task_id}")
        logger.info(f"Video params: {params_dict}")
        
        # 일반 영상 생성과 동일한 방식으로 task.start 호출
        try:
            if video_type == "longform":
                result = tm.generate_longform_video(task_id, params)
            else:
                logger.info("Calling task.start...")
                result = tm.start(task_id, params, stop_at="video")
                logger.info(f"task.start completed with result: {result}")
            
            logger.info(f"Task completed successfully: {result}")
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            # 디버깅을 위해 task 디렉토리 내용 확인
            task_dir = utils.task_dir(task_id)
            all_files = glob.glob(os.path.join(task_dir, "*"))
            logger.error(f"Task directory contents: {all_files}")
            
            # 더 자세한 오류 정보 출력
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            raise Exception(f"영상 생성 중 오류 발생: {str(e)}")
        
        # 4. 생성된 파일 찾기 (일반 영상 생성과 동일)
        task_dir = utils.task_dir(task_id)
        logger.info(f"Looking for video files in: {task_dir}")
        
        # 일반 영상 생성과 동일한 패턴으로 검색
        video_patterns = [
            os.path.join(task_dir, f"longform_final_{task_id}.mp4"),  # 롱폼
            os.path.join(task_dir, "final-*.mp4"),                    # 쇼츠
            os.path.join(task_dir, "combined-*.mp4"),                 # 결합된 영상
            os.path.join(task_dir, "*.mp4")                           # 모든 mp4
        ]
        
        video_file = None
        for pattern in video_patterns:
            files = glob.glob(pattern)
            logger.info(f"Pattern {pattern}: found {len(files)} files")
            if files:
                video_file = files[0]
                logger.info(f"Selected video file: {video_file}")
                break
        
        if not video_file or not os.path.exists(video_file):
            # 디버깅 정보
            all_files = glob.glob(os.path.join(task_dir, "*"))
            logger.error(f"No video files found in {task_dir}")
            logger.error(f"Available files: {all_files}")
            raise Exception(f"영상 파일을 찾을 수 없습니다. Task 디렉토리: {task_dir}")
        
        logger.info(f"Found video file: {video_file}")
        
        logger.info(f"Video generation completed successfully for: {title}")
        
        # 반환 전에 필수 정보 검증 및 상세 로깅
        logger.info(f"Final validation - video_file: {video_file}")
        logger.info(f"File exists check: {os.path.exists(video_file) if video_file else False}")
        
        if not video_file:
            logger.error("No video_file path available")
            raise Exception("영상 파일 경로가 없습니다")
        
        if not os.path.exists(video_file):
            logger.error(f"Video file does not exist: {video_file}")
            # 디렉토리 내용 확인
            task_dir = utils.task_dir(task_id)
            try:
                all_files = glob.glob(os.path.join(task_dir, "*"))
                logger.error(f"Task directory contents: {all_files}")
            except:
                pass
            raise Exception(f"영상 파일이 생성되지 않았습니다: {video_file}")
        
        # 파일 크기 확인
        file_size = os.path.getsize(video_file)
        logger.info(f"Video file size: {file_size} bytes")
        
        if file_size == 0:
            logger.error("Video file is empty")
            raise Exception(f"영상 파일이 비어있습니다: {video_file}")
        
        # task.start 결과에서 스크립트와 키워드 추출 (일반 영상과 동일)
        final_script = result.get('script', script) if result else script
        final_terms = result.get('terms', terms) if result else terms
        
        # 배치 생성에서는 YouTube 업로드를 하지 않고 영상 생성만 수행
        # 자동 업로드는 Main.py에서 일반 영상과 동일한 방식으로 처리
        logger.info("Batch generation completed - YouTube upload will be handled separately if enabled")
        
        result = {
            'file_path': video_file,
            'script': final_script or f"주제: {title}",  # 스크립트가 없으면 기본값 사용
            'video_id': None,  # 배치에서는 업로드하지 않음
            'type': video_type,
            'language': language,
            'upload_error': None,  # 업로드 시도하지 않음
            'file_size': file_size,  # 파일 크기 정보 추가
            'auto_upload_requested': auto_upload  # 자동 업로드 요청 여부 저장
        }
        
        logger.info(f"Returning successful result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Video generation failed for {title}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # YouTube 업로드 오류인 경우 영상 파일이 있다면 부분 성공으로 처리
        task_dir = utils.task_dir(task_id)
        video_patterns = [
            os.path.join(task_dir, f"longform_final_{task_id}.mp4"),
            os.path.join(task_dir, "final-*.mp4"),
            os.path.join(task_dir, "combined-*.mp4"),
            os.path.join(task_dir, "*.mp4")
        ]
        
        video_file = None
        for pattern in video_patterns:
            files = glob.glob(pattern)
            if files:
                video_file = files[0]
                break
        
        if video_file and os.path.exists(video_file):
            logger.warning(f"Video file exists despite error, returning partial success: {video_file}")
            return {
                'file_path': video_file,
                'script': script if 'script' in locals() else title,
                'video_id': None,  # 업로드 실패
                'type': video_type,
                'language': language,
                'upload_error': f"영상 생성 중 오류 발생: {str(e)}"
            }
        
        raise Exception(f"영상 생성 실패: {str(e)}")