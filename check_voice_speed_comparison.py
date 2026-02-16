"""
한국어 vs 영어 음성 속도 비교
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from app.services import voice
from loguru import logger
from moviepy import AudioFileClip

# 같은 내용의 한국어/영어 텍스트
korean_text = "안녕하세요. 오늘은 건강한 식습관에 대해 이야기하겠습니다. 규칙적인 식사와 균형 잡힌 영양 섭취가 중요합니다."
english_text = "Hello. Today, I will talk about healthy eating habits. Regular meals and balanced nutrition are important."

logger.info("=" * 60)
logger.info("한국어 vs 영어 음성 속도 비교")
logger.info("=" * 60)

# 한국어 음성 생성 (1.3배속)
logger.info("\n🇰🇷 한국어 음성 생성 중...")
korean_voice_file = "test_korean_voice.mp3"
korean_result = voice.gtts_synthesize(korean_text, "gtts:ko-한국어", korean_voice_file, 1.3)

if korean_result:
    korean_audio = AudioFileClip(korean_voice_file)
    korean_duration = korean_audio.duration
    korean_audio.close()
    
    logger.info(f"  - 텍스트 길이: {len(korean_text)} 글자")
    logger.info(f"  - 음성 길이: {korean_duration:.2f}초")
    logger.info(f"  - 속도: {len(korean_text) / korean_duration:.2f} 글자/초")
    logger.info(f"  - 설정 속도: 1.3배속")
else:
    logger.error("한국어 음성 생성 실패")
    sys.exit(1)

# 영어 음성 생성 (1.0배속)
logger.info("\n🇺🇸 영어 음성 생성 중...")
english_voice_file = "test_english_voice.mp3"
english_result = voice.gtts_synthesize(english_text, "gtts:en-gb", english_voice_file, 1.0)

if english_result:
    english_audio = AudioFileClip(english_voice_file)
    english_duration = english_audio.duration
    english_audio.close()
    
    logger.info(f"  - 텍스트 길이: {len(english_text)} 글자")
    logger.info(f"  - 음성 길이: {english_duration:.2f}초")
    logger.info(f"  - 속도: {len(english_text) / english_duration:.2f} 글자/초")
    logger.info(f"  - 설정 속도: 1.0배속")
else:
    logger.error("영어 음성 생성 실패")
    sys.exit(1)

# 비교 분석
logger.info("\n" + "=" * 60)
logger.info("📊 비교 분석")
logger.info("=" * 60)

# 실제 재생 속도 비교 (1.3배속 보정)
korean_actual_speed = korean_duration / 1.3  # 1.3배속 보정
speed_ratio = english_duration / korean_actual_speed

logger.info(f"한국어 음성 (1.3배속 보정 전): {korean_duration:.2f}초")
logger.info(f"한국어 음성 (1.3배속 보정 후): {korean_actual_speed:.2f}초")
logger.info(f"영어 음성 (1.0배속): {english_duration:.2f}초")
logger.info(f"")
logger.info(f"영어 음성이 한국어 대비: {speed_ratio:.2f}배")

if speed_ratio < 0.8:
    logger.warning(f"⚠️ 영어 음성이 한국어보다 {(1-speed_ratio)*100:.1f}% 빠릅니다!")
elif speed_ratio > 1.2:
    logger.info(f"✅ 영어 음성이 한국어보다 {(speed_ratio-1)*100:.1f}% 느립니다")
else:
    logger.success(f"✅ 영어 음성과 한국어 음성의 속도가 비슷합니다")

logger.info("\n" + "=" * 60)
