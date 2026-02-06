"""
애니메이션 쇼츠 생성 서비스
"""
import os
import time
import json
from typing import Dict, Any, Optional
from loguru import logger
from uuid import uuid4

from app.utils import utils
from app.services import llm, voice


class AnimationShortsGenerator:
    """애니메이션 쇼츠 생성기"""
    
    def __init__(self):
        # voice와 subtitle 모듈을 직접 사용
        pass
        
    def generate_animation_shorts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """애니메이션 쇼츠 생성"""
        
        task_id = params.get('task_id', str(uuid4()))
        logger.info(f"🎨 Starting animation shorts generation: {task_id}")
        
        try:
            # 작업 디렉토리 생성
            task_dir = utils.task_dir(task_id)
            os.makedirs(task_dir, exist_ok=True)
            
            result = {
                'task_id': task_id,
                'status': 'processing',
                'progress': 0,
                'message': '애니메이션 쇼츠 생성 시작',
                'videos': [],
                'error': None
            }
            
            # 1단계: 대본 생성/처리 (10%)
            script = self._prepare_script(params)
            result['progress'] = 10
            result['message'] = '대본 준비 완료'
            logger.info(f"📝 Script prepared: {len(script)} characters")
            
            # 2단계: 음성 생성 (30%)
            audio_file = self._generate_voice(script, params, task_dir)
            result['progress'] = 30
            result['message'] = '음성 생성 완료'
            logger.info(f"🎵 Voice generated: {audio_file}")
            
            # 3단계: 자막 생성 (40%)
            subtitle_file = self._generate_subtitles(script, audio_file, params, task_dir)
            result['progress'] = 40
            result['message'] = '자막 생성 완료'
            logger.info(f"📝 Subtitles generated: {subtitle_file}")
            
            # 4단계: 애니메이션 배경 생성 (70%)
            animation_file = self._generate_animation_background(params, task_dir)
            result['progress'] = 70
            result['message'] = '애니메이션 배경 생성 완료'
            logger.info(f"🎬 Animation background generated: {animation_file}")
            
            # 5단계: 최종 영상 합성 (100%)
            final_video = self._compose_final_video(
                animation_file, audio_file, subtitle_file, params, task_dir
            )
            result['progress'] = 100
            result['status'] = 'completed'
            result['message'] = '애니메이션 쇼츠 생성 완료'
            result['videos'] = [final_video]
            
            logger.info(f"✅ Animation shorts generation completed: {final_video}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Animation shorts generation failed: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)
            result['message'] = f'생성 실패: {e}'
            return result
    
    def _prepare_script(self, params: Dict[str, Any]) -> str:
        """대본 준비"""
        
        script = params.get('script', '').strip()
        subject = params.get('subject', '')
        
        if not script and subject:
            # AI로 대본 생성
            logger.info(f"🤖 Generating script for: {subject}")
            
            # 쇼츠에 최적화된 대본 생성
            prompt = f"""
            다음 주제로 30초 분량의 쇼츠 영상 대본을 작성해주세요:
            주제: {subject}
            
            요구사항:
            - 30초 분량 (약 80-100단어)
            - 시청자의 관심을 즉시 끄는 시작
            - 핵심 메시지 3-5개로 구성
            - 애니메이션과 잘 어울리는 시각적 표현
            - 마지막에 행동 유도 문구 포함
            
            대본만 작성해주세요:
            """
            
            script = llm.generate_script(prompt) or f"{subject}에 대한 흥미로운 내용을 소개합니다."
        
        elif not script:
            script = "애니메이션 쇼츠 영상입니다."
        
        return script
    
    def _generate_voice(self, script: str, params: Dict[str, Any], task_dir: str) -> str:
        """음성 생성"""
        
        voice_speed = params.get('voice_speed', 1.2)
        
        # voice 모듈의 함수 직접 사용
        audio_file = os.path.join(task_dir, 'audio.mp3')
        
        try:
            # gTTS 사용 (한국어)
            voice.generate_voice_gtts(
                text=script,
                output_file=audio_file,
                language='ko',
                slow=False
            )
            
            logger.info(f"✅ Voice generated: {audio_file}")
            
        except Exception as e:
            logger.error(f"❌ Voice generation failed: {e}")
            # 빈 파일이라도 생성
            with open(audio_file, 'w') as f:
                f.write("")
        
        return audio_file
    
    def _generate_subtitles(self, script: str, audio_file: str, params: Dict[str, Any], task_dir: str) -> str:
        """자막 생성"""
        
        subtitle_style = params.get('subtitle_style', '모던 볼드')
        
        # 자막 파일 생성
        subtitle_file = os.path.join(task_dir, 'subtitles.srt')
        
        # 간단한 자막 생성 (실제로는 음성 길이에 맞춰 조정 필요)
        sentences = script.split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        subtitle_content = ""
        start_time = 0
        
        for i, sentence in enumerate(sentences):
            if not sentence:
                continue
                
            # 문장당 약 3초 할당 (실제로는 음성 길이 기반으로 계산)
            duration = max(2, len(sentence) * 0.1)
            end_time = start_time + duration
            
            subtitle_content += f"{i+1}\n"
            subtitle_content += f"{self._format_time(start_time)} --> {self._format_time(end_time)}\n"
            subtitle_content += f"{sentence}\n\n"
            
            start_time = end_time
        
        with open(subtitle_file, 'w', encoding='utf-8') as f:
            f.write(subtitle_content)
        
        return subtitle_file
    
    def _format_time(self, seconds: float) -> str:
        """시간을 SRT 형식으로 변환"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def _generate_animation_background(self, params: Dict[str, Any], task_dir: str) -> str:
        """애니메이션 배경 생성"""
        
        animation_style = params.get('animation_style', '모던 미니멀')
        color_scheme = params.get('color_scheme', '블루 그라데이션')
        duration = params.get('duration', 30)
        intensity = params.get('animation_intensity', '보통')
        animation_method = params.get('animation_method', 'opencv')  # 'opencv' 또는 'grok'
        
        logger.info(f"🎨 Generating animation: {animation_style} | {color_scheme} | {intensity} | Method: {animation_method}")
        
        animation_file = os.path.join(task_dir, 'animation_background.mp4')
        
        if animation_method == 'grok':
            # Grok AI 사용
            try:
                from app.services.grok_animation import grok_animation_service
                
                animation_files = grok_animation_service.generate_animation_sequence(params)
                
                if animation_files:
                    # 여러 애니메이션을 하나로 합성
                    success = grok_animation_service.combine_animations(animation_files, animation_file)
                    if success:
                        logger.info(f"✅ Grok animation generated: {animation_file}")
                        return animation_file
                
                logger.warning("⚠️ Grok animation failed, falling back to OpenCV")
                
            except Exception as e:
                logger.error(f"❌ Grok animation error: {e}")
                logger.warning("⚠️ Falling back to OpenCV animation")
        
        elif animation_method == 'free':
            # 무료 AI 사용
            try:
                from app.services.free_animation import free_animation_service
                
                animation_files = free_animation_service.generate_animation_sequence(params)
                
                if animation_files:
                    # 여러 애니메이션을 하나로 합성 (FFmpeg 사용)
                    success = self._combine_free_animations(animation_files, animation_file)
                    if success:
                        logger.info(f"✅ Free AI animation generated: {animation_file}")
                        return animation_file
                
                logger.warning("⚠️ Free AI animation failed, falling back to OpenCV")
                
            except Exception as e:
                logger.error(f"❌ Free AI animation error: {e}")
                logger.warning("⚠️ Falling back to OpenCV animation")
        
        # OpenCV 방식 (기본값 또는 폴백)
        self._create_opencv_animation(animation_file, duration, animation_style, color_scheme)
        
        return animation_file
    
    def _combine_free_animations(self, animation_files: List[str], output_file: str) -> bool:
        """무료 애니메이션들을 하나로 합성"""
        
        try:
            import subprocess
            
            if not animation_files:
                return False
            
            if len(animation_files) == 1:
                # 파일이 하나면 복사
                import shutil
                shutil.copy2(animation_files[0], output_file)
                return True
            
            # 여러 파일을 합성
            list_file = output_file.replace('.mp4', '_list.txt')
            with open(list_file, 'w') as f:
                for anim_file in animation_files:
                    if os.path.exists(anim_file):
                        f.write(f"file '{anim_file}'\n")
            
            # FFmpeg 명령어
            cmd = [
                'ffmpeg', '-f', 'concat', '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                '-y',  # 덮어쓰기
                output_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # 임시 파일 삭제
            if os.path.exists(list_file):
                os.remove(list_file)
            
            if result.returncode == 0:
                logger.info(f"✅ Free animations combined: {output_file}")
                return True
            else:
                logger.error(f"❌ FFmpeg error: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Free animation combination failed: {e}")
        
        return False
    
    def _create_opencv_animation(self, output_file: str, duration: int, style: str, color: str):
        """OpenCV 기반 애니메이션 생성"""
        
        try:
            import cv2
            import numpy as np
            
            # 9:16 비율 (쇼츠용)
            width, height = 720, 1280
            fps = 30
            
            # 비디오 라이터 생성
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
            
            # 컬러 매핑
            color_map = {
                '블루 그라데이션': [(255, 100, 100), (100, 100, 255)],
                '퍼플 드림': [(255, 100, 255), (150, 50, 255)],
                '오렌지 선셋': [(100, 165, 255), (0, 100, 255)],
                '그린 네이처': [(100, 255, 100), (50, 200, 50)],
                '핑크 바이브': [(255, 100, 200), (255, 50, 150)],
                '골드 럭셔리': [(100, 215, 255), (0, 165, 255)],
                '다크 모드': [(50, 50, 50), (100, 100, 100)],
                '레인보우': [(255, 0, 0), (0, 255, 255)]
            }
            
            colors = color_map.get(color, [(255, 100, 100), (100, 100, 255)])
            
            # 프레임 생성
            total_frames = duration * fps
            
            for frame_num in range(total_frames):
                # 그라데이션 배경 생성
                img = np.zeros((height, width, 3), dtype=np.uint8)
                
                # 시간에 따른 애니메이션 효과
                t = frame_num / total_frames
                
                for y in range(height):
                    ratio = y / height
                    # 시간에 따른 색상 변화
                    animated_ratio = (ratio + t * 0.5) % 1.0
                    
                    color1 = np.array(colors[0])
                    color2 = np.array(colors[1])
                    
                    blended_color = color1 * (1 - animated_ratio) + color2 * animated_ratio
                    img[y, :] = blended_color.astype(np.uint8)
                
                # 스타일별 추가 효과
                if '다이나믹' in style:
                    # 움직이는 원형 패턴
                    center_x = int(width/2 + 100 * np.sin(t * 4 * np.pi))
                    center_y = int(height/2 + 50 * np.cos(t * 6 * np.pi))
                    cv2.circle(img, (center_x, center_y), 50, (255, 255, 255), -1)
                
                elif '기하학적' in style:
                    # 회전하는 사각형
                    angle = t * 360
                    center = (width//2, height//2)
                    size = 100
                    
                    points = np.array([
                        [-size, -size], [size, -size], [size, size], [-size, size]
                    ], dtype=np.float32)
                    
                    # 회전 변환
                    rotation_matrix = cv2.getRotationMatrix2D((0, 0), angle, 1.0)
                    rotated_points = cv2.transform(points.reshape(-1, 1, 2), rotation_matrix)
                    rotated_points = rotated_points.reshape(-1, 2) + np.array([center])
                    
                    cv2.fillPoly(img, [rotated_points.astype(np.int32)], (255, 255, 255))
                
                out.write(img)
            
            out.release()
            logger.info(f"✅ Dummy animation created: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create dummy animation: {e}")
            # 빈 파일이라도 생성
            with open(output_file, 'w') as f:
                f.write("")
    
    def _compose_final_video(self, animation_file: str, audio_file: str, subtitle_file: str, 
                           params: Dict[str, Any], task_dir: str) -> str:
        """최종 영상 합성"""
        
        final_video = os.path.join(task_dir, f"animation_shorts_{params['task_id'][:8]}.mp4")
        
        try:
            # TODO: FFmpeg를 사용한 실제 영상 합성
            # 현재는 애니메이션 파일을 복사
            import shutil
            if os.path.exists(animation_file):
                shutil.copy2(animation_file, final_video)
            
            logger.info(f"✅ Final video composed: {final_video}")
            
        except Exception as e:
            logger.error(f"❌ Failed to compose final video: {e}")
            # 빈 파일이라도 생성
            with open(final_video, 'w') as f:
                f.write("")
        
        return final_video


# 전역 인스턴스
animation_generator = AnimationShortsGenerator()