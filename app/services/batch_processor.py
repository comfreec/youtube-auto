"""
배치 영상 생성 시스템
여러 영상 제목을 입력받아 자동으로 연속 생성
"""

import time
import asyncio
from typing import List, Dict, Optional, Callable
from loguru import logger
from datetime import datetime

from app.services import task, llm
from app.utils.youtube import get_authenticated_service, upload_video
import os


class BatchVideoProcessor:
    """배치 영상 생성 프로세서"""
    
    def __init__(self):
        self.is_processing = False
        self.current_progress = 0
        self.total_videos = 0
        self.current_video_index = 0
        self.current_video_title = ""
        self.results = []
        self.errors = []
        
    def get_status(self) -> Dict:
        """현재 처리 상태 반환"""
        return {
            'is_processing': self.is_processing,
            'current_progress': self.current_progress,
            'total_videos': self.total_videos,
            'current_video_index': self.current_video_index,
            'current_video_title': self.current_video_title,
            'completed_count': len(self.results),
            'error_count': len(self.errors),
            'results': self.results,
            'errors': self.errors
        }
    
    def parse_video_list(self, video_list_text: str) -> List[str]:
        """영상 제목 리스트 파싱"""
        lines = video_list_text.strip().split('\n')
        titles = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 번호가 있는 경우 제거 (1. 제목, 1) 제목, - 제목 등)
            import re
            line = re.sub(r'^\d+[\.\)\-\s]+', '', line)
            line = re.sub(r'^[\-\*\•]\s*', '', line)
            
            if line:
                titles.append(line)
        
        return titles
    
    async def process_batch_videos(
        self, 
        video_titles: List[str],
        video_params: Dict,
        progress_callback: Optional[Callable] = None,
        auto_upload: bool = False
    ) -> Dict:
        """배치로 영상들을 생성"""
        
        if self.is_processing:
            return {'success': False, 'error': '이미 배치 처리가 진행 중입니다.'}
        
        self.is_processing = True
        self.current_progress = 0
        self.total_videos = len(video_titles)
        self.current_video_index = 0
        self.results = []
        self.errors = []
        
        logger.info(f"Starting batch video processing: {self.total_videos} videos")
        
        try:
            # YouTube 서비스 준비 (자동 업로드가 활성화된 경우)
            youtube_service = None
            if auto_upload:
                try:
                    client_secrets_file = "client_secrets.json"
                    token_file = "token.pickle"
                    if os.path.exists(client_secrets_file) and os.path.exists(token_file):
                        youtube_service = get_authenticated_service(client_secrets_file, token_file)
                        logger.info("YouTube service authenticated for batch upload")
                except Exception as e:
                    logger.warning(f"YouTube authentication failed: {e}")
            
            for i, title in enumerate(video_titles):
                self.current_video_index = i + 1
                self.current_video_title = title
                self.current_progress = int((i / self.total_videos) * 100)
                
                if progress_callback:
                    progress_callback(self.get_status())
                
                logger.info(f"Processing video {i+1}/{self.total_videos}: {title}")
                
                try:
                    # 개별 영상 생성
                    result = await self._process_single_video(
                        title, 
                        video_params, 
                        youtube_service if auto_upload else None
                    )
                    
                    self.results.append({
                        'index': i + 1,
                        'title': title,
                        'success': True,
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    logger.info(f"✅ Video {i+1} completed: {title}")
                    
                except Exception as e:
                    error_msg = str(e)
                    self.errors.append({
                        'index': i + 1,
                        'title': title,
                        'error': error_msg,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    logger.error(f"❌ Video {i+1} failed: {title} - {error_msg}")
                
                # 영상 간 간격 (서버 부하 방지)
                if i < len(video_titles) - 1:
                    await asyncio.sleep(2)
            
            self.current_progress = 100
            if progress_callback:
                progress_callback(self.get_status())
            
            logger.info(f"Batch processing completed: {len(self.results)} success, {len(self.errors)} errors")
            
            return {
                'success': True,
                'total_videos': self.total_videos,
                'completed_count': len(self.results),
                'error_count': len(self.errors),
                'results': self.results,
                'errors': self.errors
            }
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return {'success': False, 'error': str(e)}
        
        finally:
            self.is_processing = False
    
    async def _process_single_video(self, title: str, video_params: Dict, youtube_service=None) -> Dict:
        """개별 영상 생성 처리"""
        
        # 비디오 타입에 따른 처리
        video_type = video_params.get('video_type', 'shorts')
        create_global_version = video_params.get('create_global_version', False)
        
        results = []
        
        # 한국어 버전 생성
        if video_type == 'shorts':
            ko_result = await self._process_shorts_video(title, video_params, youtube_service)
            results.append(ko_result)
        elif video_type == 'longform':
            ko_result = await self._process_longform_video(title, video_params, youtube_service)
            results.append(ko_result)
        elif video_type == 'timer':
            ko_result = await self._process_timer_video(title, video_params, youtube_service)
            results.append(ko_result)
        else:
            raise ValueError(f"Unsupported video type: {video_type}")
        
        # 영어 버전 생성 (글로벌 버전이 활성화된 경우)
        if create_global_version and video_type in ['shorts', 'longform']:
            logger.info(f"Creating global (English) version for: {title}")
            
            # 영어 버전용 파라미터 생성
            eng_params = video_params.copy()
            eng_params['language'] = 'en-US'
            
            try:
                if video_type == 'shorts':
                    eng_result = await self._process_shorts_video(title, eng_params, youtube_service)
                    eng_result['version'] = 'english'
                    results.append(eng_result)
                elif video_type == 'longform':
                    eng_result = await self._process_longform_video(title, eng_params, youtube_service)
                    eng_result['version'] = 'english'
                    results.append(eng_result)
                
                logger.info(f"✅ Global version created for: {title}")
                
            except Exception as e:
                logger.error(f"❌ Failed to create global version for {title}: {e}")
                # 영어 버전 실패해도 한국어 버전은 유지
        
        return {
            'korean_version': results[0] if results else None,
            'english_version': results[1] if len(results) > 1 else None,
            'total_versions': len(results)
        }
    
    async def _process_shorts_video(self, title: str, video_params: Dict, youtube_service=None) -> Dict:
        """쇼츠 영상 생성"""
        
        # 대본 생성
        script = llm.generate_script(
            video_subject=title,
            language=video_params.get('language', 'ko-KR'),
            paragraph_number=1
        )
        
        if not script:
            raise Exception("대본 생성 실패")
        
        # 영상 생성 (기존 웹UI 로직 사용)
        result_file = await self._generate_video_with_task(
            script=script,
            video_params={**video_params, 'title': title},
            video_type='shorts'
        )
        
        if not result_file or not os.path.exists(result_file):
            raise Exception("영상 생성 실패")
        
        # 자동 업로드
        video_id = None
        if youtube_service:
            try:
                # 제목과 설명 생성
                video_title = title
                description = f"AI가 생성한 쇼츠 영상입니다.\n\n주제: {title}"
                tags = llm.generate_terms(title, script, 10)
                
                video_id = upload_video(
                    youtube=youtube_service,
                    file_path=result_file,
                    title=video_title,
                    description=description,
                    keywords=",".join(tags) if tags else "",
                    privacy_status="private"
                )
                
                logger.info(f"Video uploaded to YouTube: {video_id}")
                
            except Exception as e:
                logger.warning(f"YouTube upload failed: {e}")
        
        return {
            'file_path': result_file,
            'script': script,
            'video_id': video_id,
            'type': 'shorts'
        }
    
    async def _process_longform_video(self, title: str, video_params: Dict, youtube_service=None) -> Dict:
        """롱폼 영상 생성"""
        
        # 롱폼 대본 생성
        script = llm.generate_longform_script(
            video_subject=title,
            language=video_params.get('language', 'ko-KR'),
            duration_minutes=video_params.get('duration_minutes', 10)
        )
        
        if not script:
            raise Exception("롱폼 대본 생성 실패")
        
        # 롱폼 영상 생성 (기존 웹UI 로직 사용)
        result_file = await self._generate_longform_video_with_task(
            script=script,
            video_params={**video_params, 'title': title}
        )
        
        if not result_file or not os.path.exists(result_file):
            raise Exception("롱폼 영상 생성 실패")
        
        # 자동 업로드
        video_id = None
        if youtube_service:
            try:
                video_title = title
                description = f"AI가 생성한 롱폼 영상입니다.\n\n주제: {title}"
                tags = llm.generate_terms(title, script, 10)
                
                video_id = upload_video(
                    youtube=youtube_service,
                    file_path=result_file,
                    title=video_title,
                    description=description,
                    keywords=",".join(tags) if tags else "",
                    privacy_status="private"
                )
                
                logger.info(f"Longform video uploaded to YouTube: {video_id}")
                
            except Exception as e:
                logger.warning(f"YouTube upload failed: {e}")
        
        return {
            'file_path': result_file,
            'script': script,
            'video_id': video_id,
            'type': 'longform'
        }
    
    async def _process_timer_video(self, title: str, video_params: Dict, youtube_service=None) -> Dict:
        """타이머 영상 생성"""
        
        # 타이머 영상 생성 (task.py의 실제 함수 사용)
        result_file = await self._generate_timer_with_task(
            duration_minutes=video_params.get('duration_minutes', 20),
            timer_style=video_params.get('timer_style', 'modern'),
            background_music=video_params.get('background_music', True),
            title=title
        )
        
        if not result_file or not os.path.exists(result_file):
            raise Exception("타이머 영상 생성 실패")
        
        # 자동 업로드
        video_id = None
        if youtube_service:
            try:
                video_id = upload_video(
                    youtube=youtube_service,
                    file_path=result_file,
                    title=title,
                    description=f"{video_params.get('duration_minutes', 20)}분 타이머 영상",
                    keywords="타이머,집중,공부,명상,휴식",
                    privacy_status="private"
                )
                
                logger.info(f"Timer video uploaded to YouTube: {video_id}")
                
            except Exception as e:
                logger.warning(f"YouTube upload failed: {e}")
        
        return {
            'file_path': result_file,
            'video_id': video_id,
            'type': 'timer'
        }
    
    async def _generate_video_with_task(self, script: str, video_params: Dict, video_type: str) -> str:
        """기존 웹UI의 영상 생성 로직을 사용하여 실제 영상 생성"""
        
        from uuid import uuid4
        from app.models.schema import VideoParams
        from app.services import task
        import os
        
        # 임시 task_id 생성
        task_id = str(uuid4())
        
        # VideoParams 객체 생성 (필수 필드 포함)
        params = VideoParams(
            video_subject=video_params.get('title', ''),  # 필수 필드
            video_script=script,
            video_language=video_params.get('language', 'ko-KR'),
            voice_name=video_params.get('voice_style', 'casual'),
            bgm_type='random',
            bgm_volume=0.2,
            subtitle_enabled=video_params.get('subtitle_enabled', True),
            subtitle_position='bottom',
            video_source='pexels',
            video_aspect='9:16' if video_type == 'shorts' else '16:9',
            video_concat_mode='random',
            video_clip_duration=3,
            video_count=5,
            font_size=60,
            stroke_width=1.5,
            n_threads=2,
            paragraph_number=1
        )
        
        try:
            logger.info(f"Starting video generation for task: {task_id}")
            logger.info(f"Video params: {params_dict}")
            
            # 동기 함수를 비동기 환경에서 실행
            import asyncio
            import concurrent.futures
            
            def run_task():
                return task.start(task_id, params, stop_at="video")
            
            # 별도 스레드에서 동기 함수 실행
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_task)
                result = future.result(timeout=300)  # 5분 타임아웃
            
            logger.info(f"Task completed: {result}")
            
            # 생성된 영상 파일 찾기
            import glob
            from app.utils import utils
            
            task_dir = utils.task_dir(task_id)
            logger.info(f"Looking for video files in: {task_dir}")
            
            # 다양한 파일명 패턴으로 검색
            video_patterns = [
                os.path.join(task_dir, "final-*.mp4"),      # 일반 영상
                os.path.join(task_dir, "combined-*.mp4"),   # 결합된 영상
                os.path.join(task_dir, "*.mp4")             # 모든 mp4 파일
            ]
            
            video_files = []
            for pattern in video_patterns:
                files = glob.glob(pattern)
                logger.info(f"Pattern {pattern}: found {len(files)} files")
                if files:
                    video_files.extend(files)
                    break  # 첫 번째 패턴에서 파일을 찾으면 중단
            
            if video_files:
                result_file = video_files[0]  # 첫 번째 파일 사용
                logger.info(f"Video generated successfully: {result_file}")
                return result_file
            else:
                # 디버깅을 위해 task 디렉토리의 모든 파일 나열
                all_files = glob.glob(os.path.join(task_dir, "*"))
                logger.error(f"No video files found in {task_dir}")
                logger.error(f"Available files: {all_files}")
                raise Exception(f"영상 파일을 찾을 수 없습니다. Task 디렉토리: {task_dir}")
                
        except Exception as e:
            logger.error(f"Video generation failed for task {task_id}: {e}")
            raise e
    
    async def _generate_longform_video_with_task(self, script: str, video_params: Dict) -> str:
        """롱폼 영상 생성 (기존 웹UI 로직 사용)"""
        
        from uuid import uuid4
        from app.models.schema import VideoParams
        from app.services import task
        
        # 임시 task_id 생성
        task_id = str(uuid4())
        
        # VideoParams 객체 생성 (롱폼용 설정)
        params = VideoParams(
            video_subject=video_params.get('title', ''),  # 필수 필드
            video_script=script,
            video_language=video_params.get('language', 'ko-KR'),
            voice_name=video_params.get('voice_style', 'professional'),
            bgm_type='random',
            bgm_volume=0.2,
            subtitle_enabled=video_params.get('subtitle_enabled', True),
            subtitle_position='bottom',
            video_source='pexels',
            video_aspect='16:9',  # 롱폼용
            video_concat_mode='sequential',
            video_clip_duration=5,
            video_count=10,
            font_size=60,
            stroke_width=1.5,
            n_threads=2,
            paragraph_number=4
        )
        
        try:
            logger.info(f"Starting longform video generation for task: {task_id}")
            
            # 롱폼 영상 생성 함수 사용
            task.generate_longform_video(task_id, params)
            
            # 생성된 영상 파일 찾기
            import glob
            from app.utils import utils
            
            task_dir = utils.task_dir(task_id)
            
            # 롱폼 영상 파일 패턴으로 검색
            video_patterns = [
                os.path.join(task_dir, f"longform_final_{task_id}.mp4"),  # 롱폼 전용
                os.path.join(task_dir, "*_longform.mp4"),                 # 롱폼 패턴
                os.path.join(task_dir, "final-*.mp4"),                    # 일반 final 패턴
                os.path.join(task_dir, "*.mp4")                           # 모든 mp4 파일
            ]
            
            video_files = []
            for pattern in video_patterns:
                files = glob.glob(pattern)
                if files:
                    video_files.extend(files)
                    break  # 첫 번째 패턴에서 파일을 찾으면 중단
            
            if video_files:
                result_file = video_files[0]
                logger.info(f"Longform video generated successfully: {result_file}")
                return result_file
            else:
                # 디버깅을 위해 task 디렉토리의 모든 파일 나열
                all_files = glob.glob(os.path.join(task_dir, "*"))
                logger.error(f"No longform video files found in {task_dir}")
                logger.error(f"Available files: {all_files}")
                raise Exception(f"롱폼 영상 파일을 찾을 수 없습니다. Task 디렉토리: {task_dir}")
                
        except Exception as e:
            logger.error(f"Longform video generation failed for task {task_id}: {e}")
            raise e
    
    async def _generate_timer_with_task(self, duration_minutes: int, timer_style: str, background_music: bool, title: str) -> str:
        """타이머 영상 생성 (기존 웹UI 로직 사용)"""
        
        # 타이머 영상 생성은 복잡하므로 일단 예외 발생
        # 실제로는 웹UI의 타이머 생성 로직을 완전히 복사해야 합니다
        logger.warning("Timer video batch generation is not implemented yet")
        raise Exception("타이머 영상 배치 생성은 아직 구현되지 않았습니다. 개별 생성을 사용해주세요.")


# 전역 배치 프로세서 인스턴스
batch_processor = BatchVideoProcessor()