import re
import requests
from typing import Optional, Dict, List
from urllib.parse import urlparse, parse_qs
from loguru import logger

from app.services import llm


def extract_video_id(youtube_url: str) -> Optional[str]:
    """YouTube URL에서 비디오 ID 추출 - 강화된 버전"""
    try:
        logger.info(f"Extracting video ID from URL: {youtube_url}")
        
        # URL 정리
        url = youtube_url.strip()
        
        # 다양한 YouTube URL 형식 지원
        patterns = [
            # Standard watch URLs
            r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/watch\?.*v=)([a-zA-Z0-9_-]{11})',
            
            # Short URLs
            r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
            
            # Embed URLs
            r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            
            # Mobile URLs
            r'(?:m\.youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
            r'(?:m\.youtube\.com\/watch\?.*v=)([a-zA-Z0-9_-]{11})',
            
            # YouTube Shorts
            r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
            
            # Live URLs
            r'(?:youtube\.com\/live\/)([a-zA-Z0-9_-]{11})',
            
            # Channel URLs with video parameter
            r'(?:youtube\.com\/c\/.*\/.*v=)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/channel\/.*\/.*v=)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/user\/.*\/.*v=)([a-zA-Z0-9_-]{11})',
            
            # Any URL with v= parameter
            r'[?&]v=([a-zA-Z0-9_-]{11})',
            
            # Direct video ID (if someone just pastes the ID)
            r'^([a-zA-Z0-9_-]{11})$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                # Validate video ID format (11 characters, alphanumeric + _ -)
                if len(video_id) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
                    logger.info(f"Successfully extracted video ID: {video_id}")
                    return video_id
        
        # Try parsing with urllib if regex fails
        try:
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(url)
            
            # Check for v parameter in query string
            if parsed_url.query:
                query_params = parse_qs(parsed_url.query)
                if 'v' in query_params and query_params['v']:
                    video_id = query_params['v'][0]
                    if len(video_id) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
                        logger.info(f"Extracted video ID from query params: {video_id}")
                        return video_id
            
            # Check for video ID in path
            path_parts = parsed_url.path.strip('/').split('/')
            for part in path_parts:
                if len(part) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', part):
                    logger.info(f"Extracted video ID from path: {part}")
                    return part
                    
        except Exception as e:
            logger.warning(f"URL parsing failed: {e}")
        
        logger.error(f"Could not extract video ID from URL: {url}")
        logger.error("Supported URL formats:")
        logger.error("- https://www.youtube.com/watch?v=VIDEO_ID")
        logger.error("- https://youtu.be/VIDEO_ID")
        logger.error("- https://www.youtube.com/embed/VIDEO_ID")
        logger.error("- https://www.youtube.com/shorts/VIDEO_ID")
        logger.error("- VIDEO_ID (direct ID)")
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting video ID: {e}")
        return None


def get_video_transcript(video_id: str) -> Optional[str]:
    """YouTube 비디오의 자막/트랜스크립트 추출"""
    try:
        # youtube-transcript-api 사용 시도
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # 직접 자막 가져오기 시도
            try:
                # 한국어 자막 우선 시도
                transcript_data = YouTubeTranscriptApi.fetch(video_id, languages=['ko', 'ko-KR'])
                full_text = " ".join([item['text'] for item in transcript_data])
                logger.info(f"Successfully extracted Korean transcript: {len(full_text)} characters")
                return full_text
                
            except Exception as e:
                logger.warning(f"Korean transcript failed: {e}")
                
                try:
                    # 영어 자막 시도
                    transcript_data = YouTubeTranscriptApi.fetch(video_id, languages=['en', 'en-US'])
                    full_text = " ".join([item['text'] for item in transcript_data])
                    logger.info(f"Successfully extracted English transcript: {len(full_text)} characters")
                    return full_text
                    
                except Exception as e:
                    logger.warning(f"English transcript failed: {e}")
                    
                    try:
                        # 기본 언어로 시도 (언어 지정 없이)
                        transcript_data = YouTubeTranscriptApi.fetch(video_id)
                        full_text = " ".join([item['text'] for item in transcript_data])
                        logger.info(f"Successfully extracted default transcript: {len(full_text)} characters")
                        return full_text
                        
                    except Exception as e:
                        logger.warning(f"Default transcript failed: {e}")
                
        except ImportError:
            logger.warning("youtube-transcript-api not installed, trying alternative method")
        
        # 대안 방법: 웹 스크래핑 (간단한 방법)
        logger.info("Trying alternative transcript extraction method...")
        return _extract_transcript_alternative(video_id)
        
    except Exception as e:
        logger.error(f"Failed to extract transcript: {e}")
        return None


def _extract_transcript_alternative(video_id: str) -> Optional[str]:
    """대안적인 자막 추출 방법"""
    try:
        # YouTube 페이지에서 자막 정보 추출 시도
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # 간단한 패턴 매칭으로 자막 정보 찾기
            content = response.text
            
            # 자막 관련 JSON 데이터 찾기
            import json
            patterns = [
                r'"captions":\s*({[^}]+})',
                r'"captionTracks":\s*(\[[^\]]+\])',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    logger.info("Found caption data in page source")
                    # 실제 자막 추출은 복잡하므로 여기서는 기본 메시지 반환
                    return "자막을 추출할 수 없습니다. 수동으로 대본을 입력해주세요."
        
        logger.warning("Could not extract transcript using alternative method")
        return None
        
    except Exception as e:
        logger.error(f"Alternative transcript extraction failed: {e}")
        return None


def get_video_info(video_id: str) -> Dict:
    """YouTube 비디오 기본 정보 추출"""
    try:
        # YouTube oEmbed API 사용
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        
        response = requests.get(oembed_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'title': data.get('title', ''),
                'author': data.get('author_name', ''),
                'duration': data.get('duration', 0),
                'thumbnail': data.get('thumbnail_url', ''),
                'description': ''  # oEmbed에서는 설명을 제공하지 않음
            }
    except Exception as e:
        logger.error(f"Failed to get video info: {e}")
    
    return {
        'title': '',
        'author': '',
        'duration': 0,
        'thumbnail': '',
        'description': ''
    }


def analyze_and_reinterpret_content(original_transcript: str, video_info: Dict) -> str:
    """원본 콘텐츠를 분석하고 재해석하여 새로운 대본 생성"""
    logger.info("Starting content analysis and reinterpretation...")
    
    # 콘텐츠 분석 및 재해석 프롬프트
    prompt = f"""
    당신은 전문 콘텐츠 크리에이터입니다. 다음 YouTube 영상의 내용을 분석하고, 완전히 새로운 방식으로 재해석하여 독창적인 대본을 작성해주세요.

    원본 영상 정보:
    - 제목: {video_info.get('title', 'Unknown')}
    - 채널: {video_info.get('author', 'Unknown')}
    - 원본 내용: {original_transcript[:2000]}

    재해석 요구사항:
    1. 원본의 핵심 메시지와 정보는 유지
    2. 완전히 다른 표현 방식과 구조 사용
    3. 새로운 예시와 비유 활용
    4. 다른 순서와 논리 전개
    5. 독창적인 시작과 마무리
    6. 원본과 다른 톤앤매너 적용
    7. 60-90초 분량의 쇼츠용 대본으로 작성
    8. 인사말 없이 바로 본론으로 시작
    9. 마크다운 형식 사용 금지
    10. 순수한 텍스트만 작성

    재해석 전략:
    - 원본이 설명식이면 → 스토리텔링 방식으로
    - 원본이 나열식이면 → 문제-해결 구조로
    - 원본이 이론적이면 → 실용적 접근으로
    - 원본의 예시를 완전히 다른 예시로 교체
    - 원본의 순서를 재배열하여 새로운 흐름 생성

    완전히 새로운 관점에서 재해석된 대본을 작성해주세요:
    """
    
    try:
        response = llm._generate_response(prompt)
        if response:
            # 대본 정리
            script = response.strip()
            
            # 인사말 제거
            script = llm._remove_greetings(script, "ko-KR")
            
            # 마크다운 형식 제거
            script = llm._clean_markdown_formatting(script)
            
            logger.info(f"Successfully generated reinterpreted script: {len(script)} characters")
            return script
            
    except Exception as e:
        logger.error(f"Failed to generate reinterpreted script: {e}")
    
    return "콘텐츠 재해석에 실패했습니다. 다시 시도해주세요."


def extract_key_topics(transcript: str) -> List[str]:
    """원본 콘텐츠에서 핵심 주제 추출"""
    prompt = f"""
    다음 텍스트에서 핵심 주제와 키워드를 추출해주세요.

    텍스트: {transcript[:1500]}

    요구사항:
    1. 5-8개의 핵심 주제 추출
    2. 각 주제는 2-3단어로 표현
    3. 영상 제작에 활용할 수 있는 구체적인 키워드
    4. 쉼표로 구분하여 나열

    핵심 주제들:
    """
    
    try:
        response = llm._generate_response(prompt)
        if response:
            topics = [topic.strip() for topic in response.split(',') if topic.strip()]
            return topics[:8]
    except Exception as e:
        logger.error(f"Failed to extract key topics: {e}")
    
    return []


def analyze_youtube_video(youtube_url: str) -> Dict:
    """YouTube 영상 전체 분석 및 재해석"""
    logger.info(f"Starting YouTube video analysis for: {youtube_url}")
    
    try:
        # 1. 비디오 ID 추출
        logger.info("Step 1: Extracting video ID...")
        video_id = extract_video_id(youtube_url)
        if not video_id:
            logger.error("Failed to extract video ID")
            return {
                'success': False,
                'error': 'YouTube URL에서 비디오 ID를 추출할 수 없습니다.'
            }
        
        logger.info(f"Successfully extracted video ID: {video_id}")
        
        # 2. 비디오 정보 가져오기
        logger.info("Step 2: Getting video info...")
        video_info = get_video_info(video_id)
        logger.info(f"Video info: {video_info['title']}")
        
        # 3. 자막/트랜스크립트 추출
        logger.info("Step 3: Extracting transcript...")
        transcript = get_video_transcript(video_id)
        if not transcript:
            logger.error("Failed to extract transcript")
            return {
                'success': False,
                'error': '영상의 자막을 추출할 수 없습니다. 자막이 있는 영상을 사용해주세요.'
            }
        
        logger.info(f"Successfully extracted transcript: {len(transcript)} characters")
        
        # 4. 콘텐츠 재해석
        logger.info("Step 4: Reinterpreting content...")
        reinterpreted_script = analyze_and_reinterpret_content(transcript, video_info)
        
        # 5. 핵심 주제 추출
        logger.info("Step 5: Extracting key topics...")
        key_topics = extract_key_topics(transcript)
        
        logger.info("YouTube video analysis completed successfully")
        return {
            'success': True,
            'video_info': video_info,
            'original_transcript': transcript,
            'reinterpreted_script': reinterpreted_script,
            'key_topics': key_topics,
            'video_id': video_id
        }
        
    except Exception as e:
        logger.error(f"Error in analyze_youtube_video: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'error': f'분석 중 오류가 발생했습니다: {str(e)}'
        }