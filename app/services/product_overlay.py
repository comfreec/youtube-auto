"""
제품 오버레이 시스템 - 영상에 쿠팡 제품 이미지 자동 추가
"""
import os
from typing import List, Dict, Optional, Tuple
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, TextClip
from moviepy.video.fx.resize import resize
from loguru import logger
from PIL import Image, ImageDraw, ImageFont
import tempfile


class ProductOverlayManager:
    """제품 오버레이 관리자"""
    
    def __init__(self):
        self.overlay_size = (120, 120)  # 오버레이 크기 (픽셀)
        self.overlay_position = ('right', 'bottom')  # 위치
        self.overlay_margin = (20, 100)  # 여백 (x, y)
        self.display_duration = 5.0  # 표시 시간 (초)
        
    def create_product_overlay_image(
        self, 
        product_image_path: str, 
        product_name: str, 
        product_price: str,
        overlay_size: Tuple[int, int] = None
    ) -> str:
        """
        제품 이미지와 정보를 합쳐서 오버레이용 이미지 생성
        
        Args:
            product_image_path: 제품 이미지 파일 경로
            product_name: 제품명
            product_price: 가격
            overlay_size: 오버레이 크기 (width, height)
            
        Returns:
            생성된 오버레이 이미지 파일 경로
        """
        if overlay_size is None:
            overlay_size = self.overlay_size
            
        try:
            logger.info(f"제품 오버레이 이미지 생성 중: {product_name}")
            
            # 제품 이미지 로드 및 리사이즈
            product_img = Image.open(product_image_path)
            product_img = product_img.convert('RGBA')
            
            # 정사각형으로 크롭 (중앙 기준)
            width, height = product_img.size
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            product_img = product_img.crop((left, top, left + size, top + size))
            
            # 오버레이 크기로 리사이즈 (상품 이미지는 전체의 70% 크기)
            product_size = int(overlay_size[0] * 0.7)
            product_img = product_img.resize((product_size, product_size), Image.Resampling.LANCZOS)
            
            # 오버레이 배경 생성 (둥근 모서리)
            overlay_img = Image.new('RGBA', overlay_size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay_img)
            
            # 반투명 배경 (둥근 사각형)
            corner_radius = 15
            draw.rounded_rectangle(
                [0, 0, overlay_size[0], overlay_size[1]], 
                radius=corner_radius,
                fill=(255, 255, 255, 200)  # 반투명 흰색
            )
            
            # 테두리 추가
            draw.rounded_rectangle(
                [0, 0, overlay_size[0], overlay_size[1]], 
                radius=corner_radius,
                outline=(200, 200, 200, 255),
                width=2
            )
            
            # 제품 이미지 붙이기 (중앙 상단)
            product_x = (overlay_size[0] - product_size) // 2
            product_y = 10
            overlay_img.paste(product_img, (product_x, product_y), product_img)
            
            # 텍스트 추가 (제품명과 가격)
            try:
                # 시스템 폰트 사용 시도
                font_small = ImageFont.truetype("arial.ttf", 10)
                font_price = ImageFont.truetype("arial.ttf", 12)
            except:
                # 기본 폰트 사용
                font_small = ImageFont.load_default()
                font_price = ImageFont.load_default()
            
            # 제품명 (줄임표 처리)
            name_text = product_name[:15] + "..." if len(product_name) > 15 else product_name
            text_y = product_y + product_size + 5
            
            # 텍스트 배경 (가독성 향상)
            text_bbox = draw.textbbox((0, 0), name_text, font=font_small)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = (overlay_size[0] - text_width) // 2
            
            draw.text((text_x, text_y), name_text, fill=(50, 50, 50, 255), font=font_small)
            
            # 가격 (강조)
            price_text = product_price
            price_bbox = draw.textbbox((0, 0), price_text, font=font_price)
            price_width = price_bbox[2] - price_bbox[0]
            price_x = (overlay_size[0] - price_width) // 2
            price_y = text_y + 15
            
            draw.text((price_x, price_y), price_text, fill=(255, 100, 100, 255), font=font_price)
            
            # 클릭 유도 아이콘 (🛒)
            cart_text = "🛒"
            cart_x = overlay_size[0] - 25
            cart_y = 5
            draw.text((cart_x, cart_y), cart_text, fill=(50, 150, 50, 255))
            
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                overlay_img.save(temp_file.name, 'PNG')
                temp_path = temp_file.name
            
            logger.info(f"제품 오버레이 이미지 생성 완료: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"제품 오버레이 이미지 생성 실패: {str(e)}")
            return None
    
    def add_product_overlays_to_video(
        self, 
        video_path: str, 
        output_path: str,
        product_overlays: List[Dict],
        video_duration: float
    ) -> str:
        """
        영상에 제품 오버레이 추가
        
        Args:
            video_path: 원본 영상 파일 경로
            output_path: 출력 영상 파일 경로
            product_overlays: 제품 오버레이 데이터 리스트
            video_duration: 영상 총 길이
            
        Returns:
            오버레이가 추가된 영상 파일 경로
        """
        if not product_overlays:
            logger.info("제품 오버레이가 없어 원본 영상 반환")
            return video_path
        
        try:
            logger.info(f"영상에 제품 오버레이 추가 중: {len(product_overlays)}개 제품")
            
            # 원본 영상 로드
            main_video = VideoFileClip(video_path)
            
            # 오버레이 클립들 생성
            overlay_clips = []
            
            for i, product_data in enumerate(product_overlays):
                if not product_data.get('image_path'):
                    continue
                
                # 제품 오버레이 이미지 생성
                overlay_image_path = self.create_product_overlay_image(
                    product_data['image_path'],
                    product_data['name'],
                    product_data['price']
                )
                
                if not overlay_image_path:
                    continue
                
                # 오버레이 표시 시간 계산
                start_time = (video_duration / len(product_overlays)) * i
                end_time = min(start_time + self.display_duration, video_duration)
                
                # 이미지 클립 생성
                overlay_clip = (ImageClip(overlay_image_path)
                              .set_duration(end_time - start_time)
                              .set_start(start_time)
                              .set_position(self._calculate_overlay_position(main_video.size)))
                
                overlay_clips.append(overlay_clip)
                
                logger.info(f"오버레이 {i+1} 추가: {start_time:.1f}s - {end_time:.1f}s")
            
            # 마지막 10초간 모든 제품 표시 (작게)
            if len(product_overlays) > 1 and video_duration > 10:
                final_start = video_duration - 10
                
                for i, product_data in enumerate(product_overlays):
                    if not product_data.get('image_path'):
                        continue
                    
                    # 작은 크기로 오버레이 생성
                    small_overlay_path = self.create_product_overlay_image(
                        product_data['image_path'],
                        product_data['name'],
                        product_data['price'],
                        overlay_size=(80, 80)
                    )
                    
                    if small_overlay_path:
                        # 여러 제품을 세로로 배치
                        position = ('right', 'bottom')
                        y_offset = i * 90 + 20
                        
                        small_clip = (ImageClip(small_overlay_path)
                                    .set_duration(10)
                                    .set_start(final_start)
                                    .set_position((main_video.w - 100, main_video.h - 100 - y_offset)))
                        
                        overlay_clips.append(small_clip)
            
            # 최종 영상 합성
            if overlay_clips:
                final_video = CompositeVideoClip([main_video] + overlay_clips)
                
                # 영상 저장
                final_video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True,
                    logger=None
                )
                
                # 리소스 정리
                main_video.close()
                final_video.close()
                for clip in overlay_clips:
                    clip.close()
                
                logger.info(f"제품 오버레이 추가 완료: {output_path}")
                return output_path
            else:
                logger.warning("유효한 오버레이가 없어 원본 영상 반환")
                return video_path
                
        except Exception as e:
            logger.error(f"제품 오버레이 추가 실패: {str(e)}")
            return video_path
    
    def _calculate_overlay_position(self, video_size: Tuple[int, int]) -> Tuple[int, int]:
        """오버레이 위치 계산"""
        video_width, video_height = video_size
        
        # 우하단 배치
        x = video_width - self.overlay_size[0] - self.overlay_margin[0]
        y = video_height - self.overlay_size[1] - self.overlay_margin[1]
        
        return (x, y)


# 전역 인스턴스
_overlay_manager = None

def get_overlay_manager() -> ProductOverlayManager:
    """싱글톤 오버레이 매니저 반환"""
    global _overlay_manager
    if _overlay_manager is None:
        _overlay_manager = ProductOverlayManager()
    return _overlay_manager