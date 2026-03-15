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
        세그먼트에서 배경영상 검색용 키워드 생성 (시각적 요소 중심)
        
        Args:
            segment: 대본 세그먼트
            amount: 생성할 키워드 개수
            
        Returns:
            키워드 리스트
        """
        try:
            # 시각적 배경영상에 적합한 키워드 생성을 위한 특별 프롬프트
            prompt = f"""
다음 대본 내용에 가장 잘 어울리는 배경영상을 찾기 위한 검색 키워드를 생성하세요.

대본: {segment}

요구사항:
1. 시각적으로 표현 가능한 구체적인 명사나 장면을 선택하세요
2. 추상적인 개념보다는 실제 촬영 가능한 장면을 우선하세요
3. 영어 키워드로 생성하세요 (Pexels 검색용)
4. {amount}개의 키워드만 생성하세요

좋은 예시:
- "건강한 식습관" → "healthy food", "fresh vegetables", "cooking"
- "아침 루틴" → "morning routine", "sunrise", "coffee"
- "스트레스 해소" → "meditation", "nature walk", "relaxation"
- "운동의 중요성" → "fitness", "gym workout", "running"

{amount}개의 영어 키워드를 쉼표로 구분하여 나열하세요:
"""
            
            response = llm._generate_response(prompt)
            
            if response:
                # 응답 정리
                cleaned = response.strip().lower()
                
                # 불필요한 접두사 제거
                prefixes = ["keywords:", "tags:", "검색어:", "키워드:"]
                for p in prefixes:
                    if cleaned.startswith(p):
                        cleaned = cleaned[len(p):].strip()
                
                # 키워드 추출
                keywords = [k.strip() for k in cleaned.split(",") if k.strip()]
                
                # 유효성 검사 (영어 키워드, 적절한 길이) - 완화된 조건
                valid_keywords = []
                for kw in keywords:
                    # 영어 단어 포함, 1-4단어 길이 (숫자/하이픈 허용)
                    kw_clean = re.sub(r'[^a-z\s\-]', '', kw).strip()
                    if (kw_clean and
                        1 <= len(kw_clean.split()) <= 4 and 
                        len(kw_clean) >= 3):
                        valid_keywords.append(kw_clean)
                
                if valid_keywords:
                    logger.info(f"Generated visual keywords for segment: {valid_keywords[:amount]}")
                    return valid_keywords[:amount]
            
            logger.warning(f"LLM keywords insufficient, using enhanced fallback")
            return self._enhanced_fallback_keywords(segment, amount)
                
        except Exception as e:
            logger.error(f"Failed to generate keywords for segment: {e}")
            return self._enhanced_fallback_keywords(segment, amount)
    
    def _enhanced_fallback_keywords(self, segment: str, amount: int = 3) -> List[str]:
        """
        개선된 폴백 키워드 생성 (시각적 요소 중심)
        """
        # 영어 대본인지 확인
        is_english = bool(re.search(r'[a-zA-Z]', segment)) and not re.search(r'[가-힣]', segment)
        
        if is_english:
            # 영어 대본: 명사/형용사 직접 추출
            stop_words = {'the','a','an','and','or','but','in','on','at','to','for','of',
                         'with','by','from','is','are','was','were','be','been','being',
                         'have','has','had','do','does','did','will','would','should',
                         'could','may','might','can','this','that','these','those','it',
                         'its','you','your','we','our','they','their','not','no','so',
                         'if','as','up','out','about','into','than','then','when','where',
                         'which','who','what','how','all','each','both','more','most'}
            words = re.findall(r'\b[a-zA-Z]{4,}\b', segment.lower())
            word_freq = {}
            for w in words:
                if w not in stop_words:
                    word_freq[w] = word_freq.get(w, 0) + 1
            if word_freq:
                top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
                keywords = [w for w, _ in top_words[:amount]]
                logger.info(f"English fallback keywords extracted: {keywords}")
                return keywords
        
        # 한글 대본: 시각적 키워드 매핑
        # 시각적으로 표현 가능한 키워드 매핑 (한글 → 영어)
        visual_keywords = {
            # 사람/행동
            '사람': ['people', 'person', 'human'],
            '남자': ['man', 'male', 'businessman'],
            '여자': ['woman', 'female', 'businesswoman'],
            '아이': ['child', 'kid', 'children'],
            '가족': ['family', 'parents', 'together'],
            '친구': ['friends', 'friendship', 'social'],
            
            # 운동/건강
            '운동': ['exercise', 'fitness', 'workout'],
            '걷기': ['walking', 'walk', 'pedestrian'],
            '달리기': ['running', 'jogging', 'runner'],
            '요가': ['yoga', 'stretching', 'meditation'],
            '헬스': ['gym', 'fitness', 'training'],
            '건강': ['health', 'wellness', 'healthy'],
            
            # 일상/활동
            '공부': ['studying', 'learning', 'education'],
            '일': ['working', 'office', 'business'],
            '요리': ['cooking', 'kitchen', 'food preparation'],
            '독서': ['reading', 'book', 'library'],
            '회의': ['meeting', 'conference', 'discussion'],
            '쇼핑': ['shopping', 'store', 'retail'],
            
            # 장소
            '집': ['home', 'house', 'interior'],
            '사무실': ['office', 'workplace', 'desk'],
            '카페': ['cafe', 'coffee shop', 'coffee'],
            '공원': ['park', 'outdoor', 'green space'],
            '거리': ['street', 'city', 'urban'],
            '해변': ['beach', 'ocean', 'seaside'],
            
            # 자연
            '하늘': ['sky', 'clouds', 'blue sky'],
            '바다': ['ocean', 'sea', 'water'],
            '산': ['mountain', 'hiking', 'nature'],
            '숲': ['forest', 'trees', 'woods'],
            '나무': ['tree', 'nature', 'green'],
            '꽃': ['flower', 'blossom', 'garden'],
            '햇빛': ['sunlight', 'sunshine', 'bright'],
            '일몰': ['sunset', 'dusk', 'evening'],
            '일출': ['sunrise', 'dawn', 'morning'],
            
            # 음식
            '음식': ['food', 'meal', 'dish'],
            '과일': ['fruit', 'fresh fruit', 'healthy'],
            '야채': ['vegetable', 'fresh vegetables', 'salad'],
            '커피': ['coffee', 'espresso', 'cafe'],
            '식사': ['meal', 'dining', 'eating'],
            
            # 기술/현대
            '컴퓨터': ['computer', 'laptop', 'technology'],
            '스마트폰': ['smartphone', 'mobile', 'phone'],
            '노트북': ['laptop', 'computer', 'working'],
            '태블릿': ['tablet', 'digital', 'device'],
            
            # 감정/분위기
            '행복': ['happiness', 'joy', 'smiling'],
            '평온': ['peaceful', 'calm', 'relaxation'],
            '집중': ['focus', 'concentration', 'working'],
            '휴식': ['rest', 'relaxation', 'leisure'],
            '명상': ['meditation', 'mindfulness', 'zen'],
            
            # 시간대
            '아침': ['morning', 'sunrise', 'breakfast'],
            '저녁': ['evening', 'sunset', 'night'],
            '밤': ['night', 'dark', 'nighttime'],
            
            # 계절/날씨
            '봄': ['spring', 'blossom', 'flowers'],
            '여름': ['summer', 'sunny', 'beach'],
            '가을': ['autumn', 'fall', 'leaves'],
            '겨울': ['winter', 'snow', 'cold'],
            '비': ['rain', 'rainy', 'weather'],
            '눈': ['snow', 'winter', 'snowy']
        }
        
        keywords = []
        segment_lower = segment.lower()
        
        # 세그먼트에서 키워드 찾기
        for korean, english_list in visual_keywords.items():
            if korean in segment:
                # 각 한글 키워드에 대해 가장 적합한 영어 키워드 선택
                keywords.append(english_list[0])
                if len(keywords) >= amount:
                    break
        
        # 키워드가 부족하면 일반적인 시각적 키워드 추가
        if len(keywords) < amount:
            default_visual = ['lifestyle', 'people', 'nature', 'modern', 'daily life', 'city', 'work', 'home']
            for kw in default_visual:
                if kw not in keywords:
                    keywords.append(kw)
                    if len(keywords) >= amount:
                        break
        
        logger.info(f"Enhanced fallback keywords: {keywords[:amount]}")
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
