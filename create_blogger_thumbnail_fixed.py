#!/usr/bin/env python3
"""
블로거 솔루션 썸네일 생성기 - 한글 폰트 지원
"""

from PIL import Image, ImageDraw, ImageFont
import os
import urllib.request

def download_korean_font():
    """나눔고딕 폰트 다운로드"""
    font_url = "https://github.com/naver/nanumfont/raw/master/fonts/NanumGothic.ttf"
    font_path = "NanumGothic.ttf"
    
    if not os.path.exists(font_path):
        try:
            print("📥 한글 폰트 다운로드 중...")
            urllib.request.urlretrieve(font_url, font_path)
            print("✅ 나눔고딕 폰트 다운로드 완료!")
            return font_path
        except Exception as e:
            print(f"⚠️ 폰트 다운로드 실패: {e}")
            return None
    else:
        print("✅ 나눔고딕 폰트 이미 존재함")
        return font_path

def get_korean_font(size):
    """한글을 지원하는 폰트 찾기"""
    # 먼저 다운로드된 나눔고딕 폰트 시도
    downloaded_font = "NanumGothic.ttf"
    if os.path.exists(downloaded_font):
        try:
            return ImageFont.truetype(downloaded_font, size)
        except:
            pass
    
    korean_fonts = [
        # Windows 한글 폰트
        "malgun.ttf",           # 맑은 고딕
        "gulim.ttc",            # 굴림
        "batang.ttc",           # 바탕
        "dotum.ttc",            # 돋움
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/gulim.ttc",
        "C:/Windows/Fonts/NanumGothic.ttf",
        # macOS 한글 폰트
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NanumGothic.ttf",
        # Linux 한글 폰트
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    
    for font_path in korean_fonts:
        try:
            font = ImageFont.truetype(font_path, size)
            print(f"✅ 폰트 로드 성공: {font_path} (크기: {size})")
            return font
        except Exception as e:
            continue
    
    # 모든 폰트가 실패하면 기본 폰트 사용
    print(f"⚠️ 한글 폰트를 찾을 수 없어 기본 폰트를 사용합니다 (크기: {size})")
    try:
        return ImageFont.load_default()
    except:
        return None

def create_blogger_thumbnail():
    """블로거 솔루션 썸네일 생성"""
    
    # 썸네일 크기 (YouTube 표준)
    width, height = 1280, 720
    
    # 배경 그라데이션 생성
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # 그라데이션 배경 (파란색 -> 보라색)
    for y in range(height):
        # 그라데이션 계산
        ratio = y / height
        r = int(102 + (118 - 102) * ratio)  # 102 -> 118
        g = int(126 + (75 - 126) * ratio)   # 126 -> 75  
        b = int(234 + (162 - 234) * ratio)  # 234 -> 162
        
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # 반투명 오버레이
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 50))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # 한글 폰트 설정
    title_font = get_korean_font(80)
    subtitle_font = get_korean_font(40)
    small_font = get_korean_font(30)
    
    # 메인 제목
    title = "블로거 솔루션"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = 150
    
    # 제목 그림자
    draw.text((title_x + 3, title_y + 3), title, font=title_font, fill=(0, 0, 0, 128))
    # 제목 텍스트
    draw.text((title_x, title_y), title, font=title_font, fill='white')
    
    # 부제목
    subtitle = "AI 기반 자동 콘텐츠 생성"
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    subtitle_y = title_y + 100
    
    # 부제목 그림자
    draw.text((subtitle_x + 2, subtitle_y + 2), subtitle, font=subtitle_font, fill=(0, 0, 0, 128))
    # 부제목 텍스트
    draw.text((subtitle_x, subtitle_y), subtitle, font=subtitle_font, fill='white')
    
    # 기능 리스트
    features = [
        "🎬 자동 영상 생성",
        "📝 스마트 대본 작성", 
        "🎵 음성 & 자막 생성",
        "📱 모바일 최적화"
    ]
    
    # 기능 리스트 배치
    feature_start_y = subtitle_y + 80
    feature_spacing = 50
    
    for i, feature in enumerate(features):
        feature_bbox = draw.textbbox((0, 0), feature, font=small_font)
        feature_width = feature_bbox[2] - feature_bbox[0]
        feature_x = (width - feature_width) // 2
        feature_y = feature_start_y + (i * feature_spacing)
        
        # 기능 그림자
        draw.text((feature_x + 1, feature_y + 1), feature, font=small_font, fill=(0, 0, 0, 128))
        # 기능 텍스트
        draw.text((feature_x, feature_y), feature, font=small_font, fill='white')
    
    # 장식 요소 추가
    # 좌상단 원
    draw.ellipse([50, 50, 150, 150], fill=(255, 255, 255, 50))
    # 우하단 원
    draw.ellipse([width-150, height-150, width-50, height-50], fill=(255, 255, 255, 30))
    
    # 하단 브랜딩
    brand_text = "MoneyPrinterTurbo"
    brand_bbox = draw.textbbox((0, 0), brand_text, font=small_font)
    brand_width = brand_bbox[2] - brand_bbox[0]
    brand_x = (width - brand_width) // 2
    brand_y = height - 80
    
    # 브랜딩 그림자
    draw.text((brand_x + 1, brand_y + 1), brand_text, font=small_font, fill=(0, 0, 0, 128))
    # 브랜딩 텍스트
    draw.text((brand_x, brand_y), brand_text, font=small_font, fill='white')
    
    return img

def create_custom_thumbnail(title, subtitle, color_variant=1):
    """커스텀 썸네일 생성"""
    
    width, height = 1280, 720
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # 색상 변형
    color_schemes = [
        [(102, 126, 234), (118, 75, 162)],  # 파란색 -> 보라색
        [(255, 107, 107), (255, 142, 83)], # 빨간색 -> 주황색
        [(72, 187, 120), (34, 197, 94)],   # 초록색 -> 라임
        [(168, 85, 247), (236, 72, 153)]   # 보라색 -> 핑크
    ]
    
    colors = color_schemes[color_variant % len(color_schemes)]
    
    # 그라데이션 배경
    for y in range(height):
        ratio = y / height
        r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
        g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
        b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
        
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # 한글 폰트 설정
    title_font = get_korean_font(80)
    subtitle_font = get_korean_font(40)
    small_font = get_korean_font(30)
    
    # 제목
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = 200
    
    draw.text((title_x + 3, title_y + 3), title, font=title_font, fill=(0, 0, 0, 128))
    draw.text((title_x, title_y), title, font=title_font, fill='white')
    
    # 부제목
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    subtitle_y = title_y + 100
    
    draw.text((subtitle_x + 2, subtitle_y + 2), subtitle, font=subtitle_font, fill=(0, 0, 0, 128))
    draw.text((subtitle_x, subtitle_y), subtitle, font=subtitle_font, fill='white')
    
    # 장식 요소
    draw.ellipse([80, 80, 180, 180], fill=(255, 255, 255, 40))
    draw.ellipse([width-180, height-180, width-80, height-80], fill=(255, 255, 255, 40))
    
    # 브랜딩
    brand_text = "AI Video Studio"
    brand_bbox = draw.textbbox((0, 0), brand_text, font=small_font)
    brand_width = brand_bbox[2] - brand_bbox[0]
    brand_x = (width - brand_width) // 2
    brand_y = height - 60
    
    draw.text((brand_x + 1, brand_y + 1), brand_text, font=small_font, fill=(0, 0, 0, 128))
    draw.text((brand_x, brand_y), brand_text, font=small_font, fill='white')
    
    return img

def create_multiple_thumbnails():
    """다양한 스타일의 썸네일 생성"""
    
    # 기본 썸네일
    thumbnail1 = create_blogger_thumbnail()
    thumbnail1.save("blogger_solution_thumbnail_1_fixed.png", "PNG", quality=95)
    print("✅ 기본 썸네일 생성 완료: blogger_solution_thumbnail_1_fixed.png")
    
    # 변형 썸네일들 생성
    variations = [
        {
            "title": "AI 블로거",
            "subtitle": "자동 콘텐츠 생성 솔루션",
            "filename": "blogger_solution_thumbnail_2_fixed.png"
        },
        {
            "title": "스마트 블로깅",
            "subtitle": "AI가 만드는 전문 콘텐츠",
            "filename": "blogger_solution_thumbnail_3_fixed.png"
        },
        {
            "title": "콘텐츠 자동화",
            "subtitle": "블로거를 위한 AI 도구",
            "filename": "blogger_solution_thumbnail_4_fixed.png"
        }
    ]
    
    for i, variation in enumerate(variations):
        img = create_custom_thumbnail(
            variation["title"], 
            variation["subtitle"],
            i + 1  # 색상 변형을 위한 인덱스
        )
        img.save(variation["filename"], "PNG", quality=95)
        print(f"✅ 변형 썸네일 생성 완료: {variation['filename']}")

if __name__ == "__main__":
    print("🎨 블로거 솔루션 썸네일 생성 시작...")
    
    try:
        # 한글 폰트 다운로드 시도
        download_korean_font()
        
        # 썸네일 생성
        create_multiple_thumbnails()
        
        print("\n🎉 모든 썸네일 생성 완료!")
        print("\n생성된 파일:")
        print("- blogger_solution_thumbnail_1_fixed.png (기본)")
        print("- blogger_solution_thumbnail_2_fixed.png (AI 블로거)")
        print("- blogger_solution_thumbnail_3_fixed.png (스마트 블로깅)")
        print("- blogger_solution_thumbnail_4_fixed.png (콘텐츠 자동화)")
        
    except Exception as e:
        print(f"❌ 썸네일 생성 실패: {e}")
        print("💡 PIL(Pillow) 라이브러리가 필요합니다: pip install Pillow")