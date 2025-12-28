#!/usr/bin/env python3
"""
배경 이미지 생성 스크립트
타이머 영상용 배경 이미지들을 생성합니다.
"""

import os
import numpy as np
from PIL import Image, ImageDraw

def create_gradient_background(width, height, colors, filename):
    """그라데이션 배경 이미지 생성"""
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)
    
    # 세로 그라데이션 생성
    for y in range(height):
        ratio = y / height
        
        # 색상 보간
        r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
        g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
        b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
        
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    image.save(filename)
    print(f"Created: {filename}")

def create_nature_background(width, height, filename):
    """자연 느낌의 배경 생성"""
    # 초록색 그라데이션 (숲 느낌)
    colors = [(34, 139, 34), (0, 100, 0)]  # Forest green to dark green
    create_gradient_background(width, height, colors, filename)

def create_abstract_background(width, height, filename):
    """추상적인 배경 생성"""
    # 보라색-파란색 그라데이션
    colors = [(75, 0, 130), (25, 25, 112)]  # Indigo to midnight blue
    create_gradient_background(width, height, colors, filename)

def create_sunset_background(width, height, filename):
    """석양 느낌의 배경 생성"""
    # 주황색-빨간색 그라데이션
    colors = [(255, 140, 0), (220, 20, 60)]  # Dark orange to crimson
    create_gradient_background(width, height, colors, filename)

def main():
    # 세로형 비디오 해상도
    width, height = 1080, 1920
    
    # 배경 이미지 저장 경로
    materials_dir = os.path.join(os.path.dirname(__file__), "resource", "materials")
    os.makedirs(materials_dir, exist_ok=True)
    
    # 다양한 배경 이미지 생성
    create_nature_background(width, height, os.path.join(materials_dir, "nature_bg.jpg"))
    create_abstract_background(width, height, os.path.join(materials_dir, "abstract_bg.jpg"))
    create_sunset_background(width, height, os.path.join(materials_dir, "sunset_bg.jpg"))
    
    # 추가 그라데이션 배경들
    create_gradient_background(width, height, [(30, 30, 30), (60, 60, 60)], 
                             os.path.join(materials_dir, "dark_gradient_bg.jpg"))
    create_gradient_background(width, height, [(0, 50, 100), (0, 20, 40)], 
                             os.path.join(materials_dir, "blue_gradient_bg.jpg"))
    
    print("모든 배경 이미지가 생성되었습니다!")

if __name__ == "__main__":
    main()