"""
대본 세그먼트별 배경영상 매칭 시스템

대본을 의미 있는 구간(세그먼트)으로 나누고, 각 구간에 맞는 배경영상을 정확하게 매칭합니다.
"""

import re
from typing import List, Dict, Tuple
from loguru import logger
from app.services import llm


class ScriptSegmentMatcher:
    """대본을 세그먼트로 나누고 각 세그먼트에 맞는 키워드를 생성"""
    
    def __init__(self):
        pass
    
    def split_script_into_segments(self, script: str, target_segment_count: int = 5) -> List[str]:
        """
        대본을 의미 있는 세그먼트로 분할
        
        Args:
            script: 전체 대본
            target_segment_count: 목표 세그먼트 개수
            
        Returns:
            세그먼트 리스트
        """
        # 문장 단위로 분리 (마침표, 느낌표, 물음표 기준)
        sentences = re.split(r'[.!?。！？]\s*', script)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return [script]
        
        # 문장 수가 목표 세그먼트 수보다 적으면 그대로 반환
        if len(sentences) <= target_segment_count:
            return sentences
        
        # 문장들을 균등하게 그룹화
        sentences_per_segment = len(sentences) // target_segment_count
        remainder = len(sentences) % target_segment_count
        
        segments = []
        start_idx = 0
        
        for i in range(target_segment_count):
            # 나머지를 앞쪽 세그먼트에 분배
            segment_size = sentences_per_segment + (1 if i < remainder else 0)
            end_idx = start_idx + segment_size
            
            segment_sentences = sentences[start_idx:end_idx]
            segment_text = '. '.join(segment_sentences) + '.'
            segments.append(segment_text)
            
            start_idx = end_idx
        
        logger.info(f"Split script into {len(segments)} segments")
        for i, seg in enumerate(segments):
            logger.debug(f"Segment {i+1}: {seg[:100]}...")
        
        return segments
    
    def generate_segment_keywords(self, segment: str, amount: int = 3) -> List[str]:
        """
        세그먼트에서 배경영상 검색용 키워드 생성
        
        Args:
            segment: 대본 세그먼트
            amount: 생성할 키워드 개수
            
        Returns:
            키워드 리스트
        """
        try:
            # LLM을 사용하여 세그먼트별 키워드 생성
            keywords = llm.generate_terms(
                video_subject="",  # 세그먼트 자체가 주제
                video_script=segment,
                amount=amount
            )
            
            if keywords and len(keywords) > 0:
                logger.info(f"Generated keywords for segment: {keywords}")
                return keywords
            else:
                logger.warning(f"No keywords generated for segment, using fallback")
                return self._fallback_keywords(segment, amount)
                
        except Exception as e:
            logger.error(f"Failed to generate keywords for segment: {e}")
            return self._fallback_keywords(segment, amount)
    
    def _fallback_keywords(self, segment: str, amount: int = 3) -> List[str]:
        """
        키워드 생성 실패 시 폴백 키워드 생성
        
        Args:
            segment: 대본 세그먼트
            amount: 생성할 키워드 개수
            
        Returns:
            폴백 키워드 리스트
        """
        # 간단한 키워드 추출 (명사 위주)
        common_keywords = {
            # 사람/행동
            '사람': 'people', '남자': 'man', '여자': 'woman', '아이': 'child',
            '운동': 'exercise', '걷기': 'walking', '달리기': 'running',
            '공부': 'studying', '일': 'working', '요리': 'cooking',
            
            # 장소
            '집': 'home', '사무실': 'office', '학교': 'school', '도서관': 'library',
            '공원': 'park', '거리': 'street', '카페': 'cafe', '식당': 'restaurant',
            
            # 자연
            '하늘': 'sky', '바다': 'ocean', '산': 'mountain', '숲': 'forest',
            '나무': 'tree', '꽃': 'flower', '햇빛': 'sunlight', '구름': 'cloud',
            
            # 음식
            '음식': 'food', '과일': 'fruit', '야채': 'vegetable', '식사': 'meal',
            
            # 기술/비즈니스
            '컴퓨터': 'computer', '노트북': 'laptop', '스마트폰': 'smartphone',
            '회의': 'meeting', '프레젠테이션': 'presentation',
            
            # 감정/상태
            '행복': 'happiness', '성공': 'success', '건강': 'health',
            '스트레스': 'stress', '휴식': 'relaxation'
        }
        
        keywords = []
        segment_lower = segment.lower()
        
        for korean, english in common_keywords.items():
            if korean in segment:
                keywords.append(english)
                if len(keywords) >= amount:
                    break
        
        # 키워드가 부족하면 일반적인 키워드 추가
        if len(keywords) < amount:
            default_keywords = ['lifestyle', 'people', 'nature', 'city', 'work']
            keywords.extend(default_keywords[:amount - len(keywords)])
        
        return keywords[:amount]
    
    def match_segments_to_videos(
        self, 
        script: str, 
        video_duration: float,
        target_segment_count: int = None
    ) -> List[Dict]:
        """
        대본을 세그먼트로 나누고 각 세그먼트에 맞는 키워드 생성
        
        Args:
            script: 전체 대본
            video_duration: 전체 영상 길이 (초)
            target_segment_count: 목표 세그먼트 개수 (None이면 자동 계산)
            
        Returns:
            세그먼트 정보 리스트 [{'segment': str, 'keywords': List[str], 'duration': float}, ...]
        """
        # 목표 세그먼트 개수 자동 계산 (3초당 1개 세그먼트)
        if target_segment_count is None:
            target_segment_count = max(3, min(10, int(video_duration / 3)))
        
        logger.info(f"Matching script to videos: duration={video_duration}s, target_segments={target_segment_count}")
        
        # 대본을 세그먼트로 분할
        segments = self.split_script_into_segments(script, target_segment_count)
        
        # 각 세그먼트의 길이 계산
        segment_duration = video_duration / len(segments)
        
        # 각 세그먼트에 대한 키워드 생성
        segment_infos = []
        for i, segment in enumerate(segments):
            keywords = self.generate_segment_keywords(segment, amount=3)
            
            segment_info = {
                'index': i,
                'segment': segment,
                'keywords': keywords,
                'duration': segment_duration,
                'start_time': i * segment_duration,
                'end_time': (i + 1) * segment_duration
            }
            segment_infos.append(segment_info)
            
            logger.info(f"Segment {i+1}/{len(segments)}: keywords={keywords}, duration={segment_duration:.1f}s")
        
        return segment_infos


# 전역 인스턴스
_matcher = None

def get_matcher() -> ScriptSegmentMatcher:
    """싱글톤 매처 인스턴스 반환"""
    global _matcher
    if _matcher is None:
        _matcher = ScriptSegmentMatcher()
    return _matcher
