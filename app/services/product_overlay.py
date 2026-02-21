"""
제품 오버레이 시스템 - 영상에 쿠팡 제품 이미지 자동 추가
"""
import os
from typing import List, Dict, Optional, Tuple
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip, TextClip
from loguru import logger
from PIL import Image, ImageDraw, ImageFont
import tempfile


class ProductOverlayManager:
    """제품 오버레이 관리자"""
    
    def __init__(self):
        self.overlay_size = (180, 180)  # 오버레이 크기 증가 (더 눈에 띄게)
        self.overlay_position = ('center', 'bottom')  # 하단 중앙으로 변경
        self.overlay_margin = (0, 150)  # 여백 (x는 중앙이므로 0, y는 자막 위)
        self.display_duration = 5.0  # 표시 시간 (초)
        
    def create_product_overlay_image(
        self, 
        product_image_path: str, 
        product_name: str, 
        product_price: str,
        overlay_size: Tuple[int, int] = None
    ) -> str:
        """
        제품 이미지를 오버레이용으로 간단하게 처리 (이미지만 표시)
        
        Args:
            product_image_path: 제품 이미지 파일 경로
            product_name: 제품명 (사용 안 함)
            product_price: 가격 (사용 안 함)
            overlay_size: 오버레이 크기 (width, height)
            
        Returns:
            생성된 오버레이 이미지 파일 경로
        """
        if overlay_size is None:
            overlay_size = self.overlay_size
            
        try:
            logger.info(f"제품 오버레이 이미지 생성 중 (이미지만): {product_name}")
            
            # 제품 이미지 로드 및 리사이즈
            product_img = Image.open(product_image_path)
            product_img = product_img.convert('RGBA')
            
            # 정사각형으로 크롭 (중앙 기준)
            width, height = product_img.size
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            product_img = product_img.crop((left, top, left + size, top + size))
            
            # 오버레이 크기로 리사이즈
            product_img = product_img.resize(overlay_size, Image.Resampling.LANCZOS)
            
            # 완전한 원형 마스크 생성
            overlay_img = Image.new('RGBA', overlay_size, (0, 0, 0, 0))
            
            # 원형 마스크 생성
            mask = Image.new('L', overlay_size, 0)
            draw = ImageDraw.Draw(mask)
            # 완전한 원 그리기
            draw.ellipse([0, 0, overlay_size[0], overlay_size[1]], fill=255)
            
            # 제품 이미지에 마스크 적용
            overlay_img.paste(product_img, (0, 0), mask)
            
            # 흰색 테두리 추가 (더 두껍게)
            draw = ImageDraw.Draw(overlay_img)
            draw.ellipse(
                [2, 2, overlay_size[0]-3, overlay_size[1]-3], 
                outline=(255, 255, 255, 255),
                width=4
            )
            
            # 쇼핑백 아이콘 제거 (깔끔하게)
            
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
        logger.info(f"🎬 add_product_overlays_to_video 호출됨")
        logger.info(f"  - video_path: {video_path}")
        logger.info(f"  - output_path: {output_path}")
        logger.info(f"  - product_overlays 개수: {len(product_overlays) if product_overlays else 0}")
        logger.info(f"  - video_duration: {video_duration}")
        
        if not product_overlays:
            logger.info("제품 오버레이가 없어 원본 영상 반환")
            return video_path
        
        try:
            logger.info(f"🎨 영상에 제품 오버레이 추가 중: {len(product_overlays)}개 제품")
            logger.info(f"제품 목록:")
            for i, p in enumerate(product_overlays, 1):
                logger.info(f"  {i}. {p.get('name', 'Unknown')} - {p.get('price', 'N/A')}")
            
            # 원본 영상 로드
            logger.info(f"원본 영상 로드 중: {video_path}")
            main_video = VideoFileClip(video_path)
            logger.info(f"원본 영상 로드 완료 - 크기: {main_video.size}, 길이: {main_video.duration}초")
            
            # 오버레이 클립들 생성
            overlay_clips = []
            
            # 제품이 1개인 경우: 영상 전체에 표시
            if len(product_overlays) == 1:
                product_data = product_overlays[0]
                if product_data.get('image_path'):
                    # 제품 오버레이 이미지 생성
                    overlay_image_path = self.create_product_overlay_image(
                        product_data['image_path'],
                        product_data['name'],
                        product_data['price']
                    )
                    
                    if overlay_image_path:
                        # 영상 전체 길이 동안 표시
                        overlay_clip = (ImageClip(overlay_image_path)
                                      .with_duration(video_duration)
                                      .with_start(0)
                                      .with_position(self._calculate_overlay_position(main_video.size)))
                        
                        overlay_clips.append(overlay_clip)
                        logger.info(f"오버레이 추가: 0.0s - {video_duration:.1f}s (영상 전체)")
            
            # 제품이 여러 개인 경우: 순차적으로 표시하되 더 길게
            else:
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
                    
                    # 오버레이 표시 시간 계산 (각 제품당 최소 10초)
                    display_time = max(10.0, video_duration / len(product_overlays))
                    start_time = (video_duration / len(product_overlays)) * i
                    end_time = min(start_time + display_time, video_duration)
                    
                    # 이미지 클립 생성 (MoviePy v2 API)
                    overlay_clip = (ImageClip(overlay_image_path)
                                  .with_duration(end_time - start_time)
                                  .with_start(start_time)
                                  .with_position(self._calculate_overlay_position(main_video.size)))
                    
                    overlay_clips.append(overlay_clip)
                    
                    logger.info(f"오버레이 {i+1} 추가: {start_time:.1f}s - {end_time:.1f}s")
            
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
        """오버레이 위치 계산 - 하단 중앙"""
        video_width, video_height = video_size
        
        # 하단 중앙 배치
        x = (video_width - self.overlay_size[0]) // 2  # 중앙 정렬
        y = video_height - self.overlay_size[1] - self.overlay_margin[1]  # 하단에서 여백
        
        return (x, y)


# 전역 인스턴스
_overlay_manager = None

def get_overlay_manager() -> ProductOverlayManager:
    """싱글톤 오버레이 매니저 반환"""
    global _overlay_manager
    if _overlay_manager is None:
        _overlay_manager = ProductOverlayManager()
    return _overlay_manager