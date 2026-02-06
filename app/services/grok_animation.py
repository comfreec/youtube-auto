"""
Grok AI를 활용한 애니메이션 생성 서비스
"""
import os
import time
import requests
import json
from typing import Dict, Any, Optional, List
from loguru import logger

from app.config import config
from app.utils import utils


class GrokAnimationService:
    """Grok AI 애니메이션 생성 서비스"""
    
    def __init__(self):
        self.api_key = config.app.get("grok_api_key", "")
        self.base_url = "https://api.x.ai/v1"  # Grok API 엔드포인트
        
    def generate_animation_sequence(self, params: Dict[str, Any]) -> List[str]:
        """애니메이션 시퀀스 생성"""
        
        subject = params.get('subject', '')
        script = params.get('script', '')
        style = params.get('animation_style', '모던 미니멀')
        color = params.get('color_scheme', '블루 그라데이션')
        duration = params.get('duration', 30)
        
        logger.info(f"🎨 Generating Grok animation sequence: {subject}")
        
        try:
            # 1단계: 스크립트를 장면별로 분할
            scenes = self._split_script_to_scenes(script, duration)
            
            # 2단계: 각 장면별 이미지 생성
            image_files = []
            for i, scene in enumerate(scenes):
                image_file = self._generate_scene_image(scene, style, color, i)
                if image_file:
                    image_files.append(image_file)
            
            # 3단계: 이미지들을 애니메이션 영상으로 변환
            animation_files = []
            for image_file in image_files:
                animation_file = self._convert_image_to_animation(image_file, style)
                if animation_file:
                    animation_files.append(animation_file)
            
            return animation_files
            
        except Exception as e:
            logger.error(f"❌ Grok animation generation failed: {e}")
            return []
    
    def _split_script_to_scenes(self, script: str, duration: int) -> List[Dict[str, Any]]:
        """스크립트를 장면별로 분할"""
        
        sentences = [s.strip() for s in script.split('.') if s.strip()]
        scene_duration = duration / max(len(sentences), 1)
        
        scenes = []
        for i, sentence in enumerate(sentences):
            scene = {
                'text': sentence,
                'duration': scene_duration,
                'start_time': i * scene_duration,
                'scene_number': i + 1
            }
            scenes.append(scene)
        
        return scenes
    
    def _generate_scene_image(self, scene: Dict[str, Any], style: str, color: str, scene_num: int) -> Optional[str]:
        """Grok AI로 장면 이미지 생성"""
        
        try:
            # 프롬프트 생성
            prompt = self._create_image_prompt(scene['text'], style, color)
            
            # Grok API 호출
            response = self._call_grok_image_api(prompt)
            
            if response and 'image_url' in response:
                # 이미지 다운로드 및 저장
                image_file = self._download_image(response['image_url'], scene_num)
                return image_file
            
        except Exception as e:
            logger.error(f"❌ Scene image generation failed: {e}")
        
        return None
    
    def _create_image_prompt(self, text: str, style: str, color: str) -> str:
        """이미지 생성 프롬프트 생성"""
        
        # 스타일 매핑
        style_prompts = {
            '모던 미니멀': 'modern minimalist design, clean lines, simple shapes',
            '다이나믹 모션': 'dynamic motion graphics, energetic movement, flowing elements',
            '파티클 이펙트': 'particle effects, glowing particles, magical atmosphere',
            '그라데이션 플로우': 'gradient flow, smooth color transitions, fluid motion',
            '기하학적 패턴': 'geometric patterns, abstract shapes, mathematical precision',
            '네온 사이버': 'neon cyberpunk style, glowing effects, futuristic elements',
            '자연 테마': 'nature theme, organic shapes, natural elements',
            '비즈니스 프로': 'professional business style, corporate design, elegant'
        }
        
        # 컬러 매핑
        color_prompts = {
            '블루 그라데이션': 'blue gradient colors, ocean blue tones',
            '퍼플 드림': 'purple dream colors, violet and lavender tones',
            '오렌지 선셋': 'orange sunset colors, warm golden tones',
            '그린 네이처': 'green nature colors, forest and leaf tones',
            '핑크 바이브': 'pink vibe colors, rose and magenta tones',
            '골드 럭셔리': 'gold luxury colors, metallic golden tones',
            '다크 모드': 'dark mode colors, black and gray tones',
            '레인보우': 'rainbow colors, vibrant multicolor palette'
        }
        
        style_desc = style_prompts.get(style, 'modern design')
        color_desc = color_prompts.get(color, 'blue tones')
        
        prompt = f"""
        Create a stunning visual representation of: "{text}"
        
        Style: {style_desc}
        Colors: {color_desc}
        
        Requirements:
        - 9:16 aspect ratio (vertical, perfect for shorts)
        - High quality, professional look
        - Suitable for video background
        - No text or typography
        - Clean, engaging visual design
        - Perfect for social media content
        """
        
        return prompt.strip()
    
    def _call_grok_image_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Grok API 호출"""
        
        if not self.api_key:
            logger.warning("⚠️ Grok API key not configured")
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'flux-1.1-pro',  # Grok의 이미지 생성 모델
                'prompt': prompt,
                'size': '720x1280',  # 9:16 비율
                'quality': 'hd',
                'n': 1
            }
            
            response = requests.post(
                f"{self.base_url}/images/generations",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Grok image generated successfully")
                return result
            else:
                logger.error(f"❌ Grok API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Grok API call failed: {e}")
        
        return None
    
    def _download_image(self, image_url: str, scene_num: int) -> Optional[str]:
        """이미지 다운로드"""
        
        try:
            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                # 저장 경로
                images_dir = utils.storage_dir("grok_images", create=True)
                image_file = os.path.join(images_dir, f"scene_{scene_num:03d}.png")
                
                with open(image_file, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"✅ Image downloaded: {image_file}")
                return image_file
                
        except Exception as e:
            logger.error(f"❌ Image download failed: {e}")
        
        return None
    
    def _convert_image_to_animation(self, image_file: str, style: str) -> Optional[str]:
        """이미지를 애니메이션으로 변환"""
        
        try:
            # Grok의 이미지-to-비디오 API 호출
            animation_prompt = self._create_animation_prompt(style)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # 이미지 파일을 base64로 인코딩
            import base64
            with open(image_file, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode()
            
            data = {
                'model': 'video-generation-model',  # Grok의 비디오 생성 모델
                'image': image_data,
                'prompt': animation_prompt,
                'duration': 3,  # 3초 애니메이션
                'fps': 30
            }
            
            response = requests.post(
                f"{self.base_url}/videos/generations",
                headers=headers,
                json=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'video_url' in result:
                    # 비디오 다운로드
                    video_file = self._download_video(result['video_url'], image_file)
                    return video_file
            
        except Exception as e:
            logger.error(f"❌ Image to animation conversion failed: {e}")
        
        return None
    
    def _create_animation_prompt(self, style: str) -> str:
        """애니메이션 프롬프트 생성"""
        
        animation_prompts = {
            '모던 미니멀': 'subtle smooth movement, gentle floating elements, minimal motion',
            '다이나믹 모션': 'dynamic movement, energetic motion, flowing transitions',
            '파티클 이펙트': 'floating particles, glowing effects, magical movement',
            '그라데이션 플로우': 'flowing gradients, smooth color transitions, wave-like motion',
            '기하학적 패턴': 'rotating geometric shapes, mathematical precision movement',
            '네온 사이버': 'pulsing neon effects, cyberpunk atmosphere, glowing motion',
            '자연 테마': 'organic movement, natural flow, gentle swaying motion',
            '비즈니스 프로': 'professional subtle movement, elegant transitions'
        }
        
        return animation_prompts.get(style, 'smooth gentle movement')
    
    def _download_video(self, video_url: str, source_image: str) -> Optional[str]:
        """비디오 다운로드"""
        
        try:
            response = requests.get(video_url, timeout=60)
            if response.status_code == 200:
                # 저장 경로
                videos_dir = utils.storage_dir("grok_animations", create=True)
                base_name = os.path.splitext(os.path.basename(source_image))[0]
                video_file = os.path.join(videos_dir, f"{base_name}_animation.mp4")
                
                with open(video_file, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"✅ Animation video downloaded: {video_file}")
                return video_file
                
        except Exception as e:
            logger.error(f"❌ Video download failed: {e}")
        
        return None
    
    def combine_animations(self, animation_files: List[str], output_file: str) -> bool:
        """여러 애니메이션을 하나로 합성"""
        
        try:
            # FFmpeg를 사용한 비디오 합성
            import subprocess
            
            # 임시 파일 리스트 생성
            list_file = output_file.replace('.mp4', '_list.txt')
            with open(list_file, 'w') as f:
                for anim_file in animation_files:
                    f.write(f"file '{anim_file}'\n")
            
            # FFmpeg 명령어
            cmd = [
                'ffmpeg', '-f', 'concat', '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                output_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # 임시 파일 삭제
            if os.path.exists(list_file):
                os.remove(list_file)
            
            if result.returncode == 0:
                logger.info(f"✅ Animations combined: {output_file}")
                return True
            else:
                logger.error(f"❌ FFmpeg error: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Animation combination failed: {e}")
        
        return False


# 전역 인스턴스
grok_animation_service = GrokAnimationService()