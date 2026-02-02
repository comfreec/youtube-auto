#!/usr/bin/env python3
"""
간단한 블로거 솔루션 썸네일 생성기
"""

from PIL import Image, ImageDraw, ImageFont
import os

def get_korean_font(size):
    """한글을 지원하는 폰트 찾기"""
    korean_fonts = [
        # Windows 한글 폰트
        "malgun.ttf",           # 맑은 고딕
        "gulim.ttc",            # 굴림
        "batang.ttc",           # 바탕
        "dotum.ttc",            # 돋움
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/gulim.ttc",
        # macOS 한글 폰트
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NanumGothic.ttf",
        # Linux 한글 폰트
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    
    for font_path in korean_fonts:
        try:
            font = ImageFont.truetype(font_path, size)
            print(f"✅ 폰트 로드 성공: {font_path} (크기: {size})")
            return font
        except:
            continue
    
    # 모든 폰트가 실패하면 기본 폰트 사용
    print(f"⚠️ 한글 폰트를 찾을 수 없어 기본 폰트를 사용합니다")
    try:
        return ImageFont.load_default()
    except:
        return None

def create_simple_blogger_thumbnail():
    """간단한 블로거 솔루션 썸네일 생성"""
    
    # 썸네일 크기 (YouTube 표준)
    width, height = 1280, 720
    
    # 배경 그라데이션 생성 (파란색 -> 보라색)
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    for y in range(height):
        ratio = y / height
        r = int(102 + (118 - 102) * ratio)  # 102 -> 118
        g = int(126 + (75 - 126) * ratio)   # 126 -> 75  
        b = int(234 + (162 - 234) * ratio)  # 234 -> 162
        
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # 반투명 오버레이
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 30))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # 폰트 설정
    title_font = get_korean_font(120)  # 더 큰 폰트
    
    # 메인 제목 "블로거 솔루션"
    title = "블로거 솔루션"
    
    # 텍스트 크기 계산
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    
    # 중앙 배치
    title_x = (width - title_width) // 2
    title_y = (height - title_height) // 2
    
    # 제목 그림자 (더 진하게)
    shadow_offset = 4
    draw.text((title_x + shadow_offset, title_y + shadow_offset), title, 
              font=title_font, fill=(0, 0, 0, 180))
    
    # 제목 텍스트 (흰색)
    draw.text((title_x, title_y), title, font=title_font, fill='white')
    
    # 장식 요소 추가
    # 좌상단 원
    draw.ellipse([60, 60, 200, 200], fill=(255, 255, 255, 40))
    # 우하단 원
    draw.ellipse([width-200, height-200, width-60, height-60], fill=(255, 255, 255, 40))
    
    # 좌하단 작은 원
    draw.ellipse([80, height-180, 180, height-80], fill=(255, 255, 255, 25))
    # 우상단 작은 원
    draw.ellipse([width-180, 80, width-80, 180], fill=(255, 255, 255, 25))
    
    return img

def create_color_variations():
    """다양한 색상의 썸네일 생성"""
    
    color_schemes = [
        {
            "name": "파란색",
            "colors": [(102, 126, 234), (118, 75, 162)],
            "filename": "blogger_solution_blue.png"
        },
        {
            "name": "빨간색",
            "colors": [(255, 107, 107), (255, 142, 83)],
            "filename": "blogger_solution_red.png"
        },
        {
            "name": "초록색",
            "colors": [(72, 187, 120), (34, 197, 94)],
            "filename": "blogger_solution_green.png"
        },
        {
            "name": "보라색",
            "colors": [(168, 85, 247), (236, 72, 153)],
            "filename": "blogger_solution_purple.png"
        },
        {
            "name": "주황색",
            "colors": [(251, 146, 60), (249, 115, 22)],
            "filename": "blogger_solution_orange.png"
        }
    ]
    
    for scheme in color_schemes:
        img = create_colored_thumbnail(scheme["colors"])
        img.save(scheme["filename"], "PNG", quality=95)
        print(f"✅ {scheme['name']} 썸네일 생성: {scheme['filename']}")

def create_colored_thumbnail(colors):
    """특정 색상의 썸네일 생성"""
    
    width, height = 1280, 720
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # 그라데이션 배경
    for y in range(height):
        ratio = y / height
        r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
        g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
        b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
        
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # 반투명 오버레이
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 30))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # 폰트 설정
    title_font = get_korean_font(120)
    
    # 메인 제목
    title = "블로거 솔루션"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    
    title_x = (width - title_width) // 2
    title_y = (height - title_height) // 2
    
    # 그림자
    shadow_offset = 4
    draw.text((title_x + shadow_offset, title_y + shadow_offset), title, 
              font=title_font, fill=(0, 0, 0, 180))
    
    # 텍스트
    draw.text((title_x, title_y), title, font=title_font, fill='white')
    
    # 장식 요소
    draw.ellipse([60, 60, 200, 200], fill=(255, 255, 255, 40))
    draw.ellipse([width-200, height-200, width-60, height-60], fill=(255, 255, 255, 40))
    draw.ellipse([80, height-180, 180, height-80], fill=(255, 255, 255, 25))
    draw.ellipse([width-180, 80, width-80, 180], fill=(255, 255, 255, 25))
    
    return img

if __name__ == "__main__":
    print("🎨 간단한 블로거 솔루션 썸네일 생성 시작...")
    
    try:
        # 기본 썸네일 생성
        basic_thumbnail = create_simple_blogger_thumbnail()
        basic_thumbnail.save("blogger_solution_simple.png", "PNG", quality=95)
        print("✅ 기본 썸네일 생성: blogger_solution_simple.png")
        
        # 색상 변형 생성
        create_color_variations()
        
        print("\n🎉 모든 썸네일 생성 완료!")
        print("\n생성된 파일:")
        print("- blogger_solution_simple.png (기본)")
        print("- blogger_solution_blue.png (파란색)")
        print("- blogger_solution_red.png (빨간색)")
        print("- blogger_solution_green.png (초록색)")
        print("- blogger_solution_purple.png (보라색)")
        print("- blogger_solution_orange.png (주황색)")
        
    except Exception as e:
        print(f"❌ 썸네일 생성 실패: {e}")
        import traceback
        traceback.print_exc()