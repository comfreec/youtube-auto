"""
간단한 모바일 영상 생성 서버
- 기존 task.py의 start() 함수를 그대로 사용
- ngrok으로 외부 접속 가능
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import os
import sys
import re
from pathlib import Path
from uuid import uuid4
from loguru import logger

# 프로젝트 루트 추가
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from app.services import task as tm
from app.services import llm
from app.models.schema import VideoParams, VideoAspect, VideoConcatMode, VideoTransitionMode
from app.config import config
from app.utils import utils
from app.utils.youtube import get_authenticated_service, upload_video
from app.services.license import license_manager

app = FastAPI(title="AI 영상 생성 모바일 서버")

# 라이선스 검증
is_valid, message = license_manager.verify_license()
if not is_valid:
    logger.error(f"❌ 라이선스 검증 실패: {message}")
    print("\n" + "=" * 60)
    print("❌ 라이선스 인증이 필요합니다")
    print("=" * 60)
    print(f"\n{message}\n")
    print("라이선스 키를 활성화하려면 웹 UI를 실행하세요:")
    print("  streamlit run webui/Main.py")
    print("\n" + "=" * 60)
    sys.exit(1)
else:
    logger.info(f"✅ 라이선스 검증 성공: {message}")

# 요청 모델
class VideoRequest(BaseModel):
    subject: str
    auto_upload: bool = True  # 기본값: 자동 업로드
    create_global: bool = True  # 기본값: 글로벌 버전 생성

# 전역 작업 저장소
tasks = {}

def run_video_generation(task_id: str, params: VideoParams, auto_upload: bool = True, create_global: bool = True):
    """백그라운드에서 영상 생성 실행"""
    from app.services import state as sm
    from app.config import config
    
    try:
        # 원래 subtitle_provider 설정 유지
        original_subtitle_provider = config.app.get("subtitle_provider", "edge")
        logger.info(f"🎯 Using subtitle_provider: {original_subtitle_provider}")
        
        try:
            # Task 디렉토리 가져오기
            task_dir = utils.task_dir(task_id)
            
            # 작업 정보 업데이트
            tasks[task_id] = {
                "status": "processing",
                "progress": 0,
                "message": "영상 생성 중...",
                "task_dir": task_dir
            }
            
            # 기존 task.start() 함수 그대로 사용 (한국어 버전)
            tm.start(task_id, params, stop_at="video")
            
            # 한국어 영상 생성 후 대본 및 키워드 검증
            logger.info("🔍 Validating Korean video generation...")
            script_file = os.path.join(task_dir, "script.json")
            
            if os.path.exists(script_file):
                import json
                with open(script_file, 'r', encoding='utf-8') as f:
                    script_data = json.load(f)
                
                script = script_data.get('script', '')
                search_terms = script_data.get('search_terms', [])
                
                # 대본 검증
                if not script or len(script) < 50:
                    logger.error(f"❌ Korean script too short: {len(script)} characters")
                    
                    # 생성된 영상 파일 삭제
                    import shutil
                    if os.path.exists(task_dir):
                        shutil.rmtree(task_dir, ignore_errors=True)
                    
                    tasks[task_id]["status"] = "failed"
                    tasks[task_id]["message"] = "⚠️ Gemini API 할당량 소진 - 대본 생성 실패"
                    sm.state.update_task(task_id, state="failed", message="❌ Gemini API 할당량 소진\n잠시 후 다시 시도하거나 API 키를 확인하세요", progress=0)
                    return
                
                # 키워드 검증 (fallback 키워드 체크)
                fallback_keywords = ["lifestyle", "people", "modern", "daily life", "professional", "habits", "success", "achievement", "tired", "exhausted", "energy"]
                
                # 검색 키워드 중 3개 이상이 fallback 키워드면 실패로 간주
                fallback_count = sum(1 for term in search_terms if term in fallback_keywords)
                
                if fallback_count >= 3:
                    logger.error(f"❌ Korean video using fallback keywords: {search_terms}")
                    logger.error(f"   Fallback count: {fallback_count}/{len(search_terms)}")
                    logger.error(f"   This indicates API quota exhaustion")
                    
                    # 생성된 영상 파일 삭제
                    import shutil
                    if os.path.exists(task_dir):
                        shutil.rmtree(task_dir, ignore_errors=True)
                    
                    tasks[task_id]["status"] = "failed"
                    tasks[task_id]["message"] = "⚠️ Gemini API 할당량 소진 - 키워드 생성 실패"
                    sm.state.update_task(task_id, state="failed", message="❌ Gemini API 할당량 소진\n잠시 후 다시 시도하거나 API 키를 확인하세요", progress=0)
                    return
                
                logger.info(f"✅ Korean video validated")
                logger.info(f"   - Script length: {len(script)} characters")
                logger.info(f"   - Keywords: {search_terms}")
            
            # 완료 상태 업데이트
            tasks[task_id]["status"] = "complete"
            tasks[task_id]["progress"] = 100
            tasks[task_id]["message"] = "한국어 영상 생성 완료!"
        
        finally:
            pass
        
        # 한국어 버전 자동 업로드 수행
        if auto_upload:
            try:
                logger.info("🚀 Starting auto upload to YouTube (Korean)...")
                tasks[task_id]["message"] = "유튜브 업로드 준비 중 (한국어)..."
                tasks[task_id]["upload_progress"] = 0
                
                sm.state.update_task(task_id, state="processing", message="📤 유튜브 업로드 준비 중 (한국어)...", progress=0)
                
                video_path = os.path.join(task_dir, "final-1.mp4")
                
                if not os.path.exists(video_path):
                    logger.error(f"Video file not found: {video_path}")
                    tasks[task_id]["upload_error"] = "영상 파일을 찾을 수 없습니다"
                    return
                
                token_file = os.path.join(root_dir, "token.pickle")
                client_secrets_file = os.path.join(root_dir, "client_secrets.json")
                
                if not os.path.exists(token_file) or not os.path.exists(client_secrets_file):
                    logger.warning("YouTube authentication files not found")
                    tasks[task_id]["upload_error"] = "YouTube 인증이 필요합니다"
                    return
                
                youtube = get_authenticated_service(client_secrets_file, token_file)
                
                title_subject = params.video_subject
                upload_title = f"#Shorts {title_subject}"
                description = f"Generated youtube-auto AI\n\nSubject: {title_subject}"
                
                # 태그 생성
                script = params.video_script or ""
                try:
                    # 한글 영상은 처음부터 한글 태그 생성
                    korean_terms = llm.generate_korean_terms(title_subject, script, 10) or []
                    
                    if korean_terms:
                        keywords = ", ".join(korean_terms + [str(title_subject).strip()])
                        logger.info(f"🇰🇷 Generated Korean tags: {keywords}")
                    else:
                        fallback_terms = ["정보", "팁", "노하우", "가이드", "도움"]
                        keywords = ", ".join(fallback_terms + [str(title_subject).strip()])
                        logger.info(f"🇰🇷 Using fallback Korean tags: {keywords}")
                        
                    logger.info(f"🏷️ Final Korean tags: {keywords}")
                except Exception as e:
                    logger.warning(f"Tag generation failed: {e}")
                    fallback_terms = ["정보", "팁", "노하우", "가이드", "도움"]
                    keywords = ", ".join(fallback_terms + [str(title_subject).strip()])
                    logger.info(f"🏷️ Using fallback keywords: {keywords}")
                
                tasks[task_id]["message"] = "유튜브 업로드 중 (한국어)..."
                tasks[task_id]["upload_progress"] = 50
                sm.state.update_task(task_id, state="processing", message="📤 유튜브 업로드 중 (한국어)...", progress=50)
                
                def upload_progress_callback(progress_percent):
                    tasks[task_id]["upload_progress"] = progress_percent
                    sm.state.update_task(task_id, state="processing", message=f"📤 유튜브 업로드 중 (한국어)... {progress_percent}%", progress=progress_percent)
                
                vid_id = upload_video(
                    youtube, 
                    video_path, 
                    title=upload_title[:100],
                    description=description,
                    category="22",
                    keywords=keywords,
                    privacy_status="private",
                    progress_callback=upload_progress_callback
                )
                
                if vid_id:
                    tasks[task_id]['video_id'] = vid_id
                    video_url = f"https://youtube.com/watch?v={vid_id}"
                    tasks[task_id]["message"] = f"한국어 버전 업로드 완료! {video_url}"
                    tasks[task_id]["upload_progress"] = 100
                    sm.state.update_task(task_id, state="complete", message=f"✅ 한국어 버전 업로드 완료!", progress=100)
                    logger.success(f"🎉 Korean version auto upload success! Video ID: {vid_id}")
                else:
                    tasks[task_id]['upload_error'] = "YouTube 업로드 실패"
                    tasks[task_id]["message"] = "한국어 영상 생성 완료 (업로드 실패)"
                    sm.state.update_task(task_id, state="complete", message="⚠️ 한국어 영상 생성 완료 (업로드 실패)", progress=100)
                    logger.error("YouTube upload failed")
                    
            except Exception as upload_error:
                import traceback
                error_detail = traceback.format_exc()
                logger.error(f"Upload error: {error_detail}")
                tasks[task_id]["upload_error"] = str(upload_error)
                tasks[task_id]["message"] = f"한국어 영상 생성 완료 (업로드 오류: {str(upload_error)})"
        
        # 글로벌 버전(영어) 생성 - batch_processor 로직 사용
        if create_global:
            try:
                logger.info("🌍 Starting English version generation using batch_processor logic...")
                tasks[task_id]["message"] = "영어 버전 생성 시작..."
                tasks[task_id]["english_status"] = "processing"
                sm.state.update_task(task_id, state="processing", message="🌍 영어 버전 생성 시작...", progress=0)
                
                # batch_processor와 동일한 방식으로 영어 제목 생성
                korean_title = params.video_subject
                # 영어 버전 생성 로직 (batch_processor.py와 동일하게 수정)
                eng_title = None
                eng_script = None
                
                # 1. 제목을 영어로 번역 시도
                try:
                    logger.info(f"🌍 Translating Korean title to English: '{korean_title}'")
                    eng_title = llm.translate_to_english(korean_title)
                    logger.info(f"🌍 Translation result: '{eng_title}'")
                    
                    # 번역 성공 여부 확인
                    if not eng_title or eng_title == korean_title or re.search(r'[가-힣]', str(eng_title)):
                        logger.warning("❌ Title translation failed or returned Korean text")
                        eng_title = None
                except Exception as e:
                    logger.warning(f"❌ Translation exception: {e}")
                    eng_title = None
                
                # 2. 번역 실패 시 키워드 기반 영어 제목 생성
                if not eng_title:
                    logger.info("🔄 Attempting keyword-based English title generation...")
                    try:
                        ko_script_file = os.path.join(task_dir, "script.json")
                        if os.path.exists(ko_script_file):
                            import json
                            with open(ko_script_file, 'r', encoding='utf-8') as f:
                                ko_script_data = json.load(f)
                            ko_script = ko_script_data.get('script', '')
                            
                            # 한국어 대본을 영어로 번역 시도
                            if ko_script:
                                logger.info("🔄 Translating Korean script to get English title...")
                                eng_script_temp = llm.translate_to_english(ko_script)
                                
                                if eng_script_temp and not re.search(r'[가-힣]', eng_script_temp):
                                    # 번역된 대본의 첫 문장을 제목으로 사용
                                    first_sentence = eng_script_temp.split('.')[0].strip()
                                    if len(first_sentence) > 10 and len(first_sentence) < 100:
                                        eng_title = first_sentence
                                        logger.info(f"✅ Generated title from translated script: {eng_title}")
                            
                            # 여전히 실패하면 키워드 기반
                            if not eng_title:
                                # 한국어 대본에서 키워드 추출
                                terms_en = llm.generate_terms(video_subject=korean_title, video_script=ko_script, amount=5) or []
                                
                                if terms_en:
                                    # 영어 키워드만 필터링
                                    english_terms = [t for t in terms_en if t and not re.search(r'[가-힣]', t)]
                                    if english_terms:
                                        eng_title = " · ".join(english_terms[:3])
                                        logger.info(f"✅ Generated title from keywords: {eng_title}")
                                    else:
                                        logger.warning("❌ No valid English keywords found")
                                else:
                                    logger.warning("❌ No keywords generated")
                    except Exception as e:
                        logger.warning(f"❌ Keyword-based title generation failed: {e}")
                
                # 3. 키워드 기반 제목이 생성되었는지 확인 (API 할당량 소진 의미)
                if eng_title and " · " in eng_title:
                    logger.error(f"❌ English title is keyword-based: '{eng_title}'")
                    logger.error(f"   This indicates API quota exhaustion")
                    tasks[task_id]["english_status"] = "skipped"
                    tasks[task_id]["english_error"] = "API 할당량 소진으로 영어 버전 생성 불가"
                    tasks[task_id]["message"] = "한국어 영상만 생성 완료 (API 할당량 소진)"
                    sm.state.update_task(task_id, state="complete", message="⚠️ 한국어 영상만 생성 완료 (API 할당량 소진)", progress=100)
                    return
                
                # 4. 모든 방법 실패 시 영어 버전 생성 중단
                if not eng_title:
                    logger.error(f"❌ Failed to generate English title for '{korean_title}'. Skipping English version.")
                    tasks[task_id]["english_status"] = "skipped"
                    tasks[task_id]["english_error"] = "제목 번역 실패 (API 할당량 소진 가능성)"
                    tasks[task_id]["message"] = "한국어 영상만 생성 완료 (영어 제목 생성 실패)"
                    sm.state.update_task(task_id, state="complete", message="⚠️ 한국어 영상만 생성 완료", progress=100)
                    return
                
                logger.info(f"✅ English title confirmed: {eng_title}")
                
                # 4. 한국어 대본을 영어로 번역 (더 정확함)
                logger.info(f"🌍 Translating Korean script to English...")
                try:
                    ko_script_file = os.path.join(task_dir, "script.json")
                    if os.path.exists(ko_script_file):
                        import json
                        with open(ko_script_file, 'r', encoding='utf-8') as f:
                            ko_script_data = json.load(f)
                        ko_script = ko_script_data.get('script', '')
                        
                        if ko_script:
                            # 한국어 대본을 영어로 번역
                            eng_script = llm.translate_to_english(ko_script)
                            
                            # 번역 검증
                            if eng_script and eng_script != ko_script and not re.search(r'[가-힣]', eng_script):
                                logger.info(f"✅ Korean script translated to English: {len(eng_script)} characters")
                            else:
                                logger.warning("❌ Script translation failed, trying generate_english_script...")
                                eng_script = None
                        else:
                            logger.warning("❌ No Korean script found")
                            eng_script = None
                    else:
                        logger.warning("❌ Korean script file not found")
                        eng_script = None
                except Exception as e:
                    logger.error(f"❌ Script translation failed: {e}")
                    eng_script = None
                
                # 5. 번역 실패 시 generate_english_script 사용 (fallback)
                if not eng_script:
                    logger.info(f"🔄 Fallback: Generating English script for title: '{eng_title}'")
                    try:
                        eng_script = llm.generate_english_script(
                            video_subject=eng_title,
                            paragraph_number=3
                        )
                        logger.info(f"🌍 English script generated: {len(eng_script) if eng_script else 0} characters")
                    except Exception as e:
                        logger.error(f"❌ English script generation failed: {e}")
                        eng_script = None
                
                # 6. 대본 검증
                if not eng_script or len(eng_script) < 100:
                    logger.error(f"❌ English script too short or empty (length: {len(eng_script) if eng_script else 0})")
                    tasks[task_id]["english_status"] = "skipped"
                    tasks[task_id]["english_error"] = "대본 생성 실패 (API 할당량 소진 가능성)"
                    tasks[task_id]["message"] = "한국어 영상만 생성 완료 (영어 대본 생성 실패)"
                    sm.state.update_task(task_id, state="complete", message="⚠️ 한국어 영상만 생성 완료", progress=100)
                    return
                
                if re.search(r'[가-힣]', eng_script):
                    logger.error(f"❌ English script contains Korean characters")
                    tasks[task_id]["english_status"] = "skipped"
                    tasks[task_id]["english_error"] = "대본에 한글 포함"
                    tasks[task_id]["message"] = "한국어 영상만 생성 완료 (영어 대본 검증 실패)"
                    sm.state.update_task(task_id, state="complete", message="⚠️ 한국어 영상만 생성 완료", progress=100)
                    return
                
                logger.info(f"✅ English script validated: {len(eng_script)} characters")
                logger.info(f"   Script preview: {eng_script[:150]}...")
                
                # 한국어 영상에서 사용한 키워드 가져오기 (같은 배경영상 사용) - 최우선
                eng_terms = []
                korean_keywords = []
                try:
                    # 한국어 script.json에서 search_terms 가져오기
                    korean_script_file = os.path.join(task_dir, "script.json")
                    if os.path.exists(korean_script_file):
                        import json
                        with open(korean_script_file, 'r', encoding='utf-8') as f:
                            korean_data = json.load(f)
                            korean_keywords = korean_data.get("search_terms", [])
                            if korean_keywords:
                                logger.info(f"🎬 Reusing Korean keywords for same background videos: {korean_keywords}")
                                # 한국어 키워드를 영어로 번역 (필요시)
                                try:
                                    for ko_term in korean_keywords:
                                        if re.search(r'[가-힣]', ko_term):
                                            # 한글이면 번역
                                            en_term = llm.translate_to_english(ko_term)
                                            if en_term and not re.search(r'[가-힣]', en_term):
                                                eng_terms.append(en_term)
                                            else:
                                                eng_terms.append(ko_term)
                                        else:
                                            # 이미 영어면 그대로 사용
                                            eng_terms.append(ko_term)
                                    logger.info(f"   ✅ Using Korean keywords (translated): {eng_terms}")
                                except Exception as e:
                                    logger.warning(f"   Translation failed, using original: {e}")
                                    eng_terms = korean_keywords
                except Exception as e:
                    logger.warning(f"⚠️ Failed to get Korean keywords: {e}")
                
                # 한국어 키워드가 없으면 영어 키워드 생성
                if not eng_terms:
                    logger.info(f"🌍 Generating English keywords from script...")
                    eng_terms = llm.generate_terms(video_subject=eng_title, video_script=eng_script, amount=5)
                    
                    # 키워드 검증 (한글 포함 여부 체크)
                    if eng_terms:
                        eng_terms = [t for t in eng_terms if t and not re.search(r'[가-힣]', t)]
                    
                    # 키워드가 없으면 대본에서 직접 추출
                    if not eng_terms:
                        logger.warning("❌ No valid English keywords generated, extracting from script...")
                        # 대본 전체에서 주요 명사/형용사 추출 (더 다양한 키워드)
                        # 불용어 제외
                        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'it', 'its', 'you', 'your', 'we', 'our', 'they', 'their'}
                        
                        # 대본에서 모든 단어 추출
                        words = re.findall(r'\b[a-zA-Z]{4,}\b', eng_script.lower())
                        # 불용어 제외하고 빈도수 계산
                        word_freq = {}
                        for word in words:
                            if word not in stop_words:
                                word_freq[word] = word_freq.get(word, 0) + 1
                        
                        # 빈도수 높은 순으로 정렬하여 상위 5개 선택
                        if word_freq:
                            eng_terms = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
                            eng_terms = [word for word, freq in eng_terms]
                            logger.info(f"   Extracted keywords from script: {eng_terms}")
                        else:
                            # 제목에서 키워드 추출 (최후의 수단)
                            title_words = re.findall(r'\b[a-zA-Z]{4,}\b', eng_title.lower())
                            eng_terms = [w for w in title_words if w not in stop_words][:5]
                            logger.warning(f"   Using title keywords: {eng_terms}")
                
                # 여전히 키워드가 없으면 영상 생성 중단 (API 할당량 소진 가능성)
                if not eng_terms or len(eng_terms) < 2:
                    logger.error("❌ Failed to generate English keywords - API quota likely exhausted")
                    tasks[task_id]["english_status"] = "skipped"
                    tasks[task_id]["english_error"] = "키워드 생성 실패 (API 할당량 소진 가능성)"
                    tasks[task_id]["message"] = "한국어 영상만 생성 완료 (영어 키워드 생성 실패)"
                    sm.state.update_task(task_id, state="complete", message="⚠️ 한국어 영상만 생성 완료", progress=100)
                    return
                
                logger.info(f"✅ Final English keywords: {eng_terms}")
                
                # 영어 버전 VideoParams 생성
                eng_task_id = str(uuid4())
                
                logger.info(f"🌍 Creating English VideoParams")
                logger.info(f"   - English script length: {len(eng_script)} characters")
                logger.info(f"   - English script preview: {eng_script[:100]}...")
                logger.info(f"   - English title: {eng_title}")
                logger.info(f"   - Using keywords: {eng_terms}")
                
                eng_params = VideoParams(
                    video_subject=eng_title,
                    video_aspect=VideoAspect.portrait,
                    video_concat_mode=VideoConcatMode.sequential,
                    video_transition_mode=VideoTransitionMode.none,
                    video_count=1,
                    video_clip_duration=5,
                    video_script=eng_script,  # 영어 스크립트 사용 (중요!)
                    video_terms=", ".join(eng_terms),
                    video_language="en-GB",  # 영국 영어
                    voice_name="gtts:en-gb",  # gTTS 영국 영어 음성
                    voice_rate=1.0,  # 1.0배속 (정상 속도)
                    voice_volume=1.0,
                    bgm_type="random",
                    bgm_file="",
                    bgm_volume=0.05,  # 배경 음악 볼륨 (0.1 → 0.05)
                    subtitle_enabled=True,
                    subtitle_position="custom",
                    custom_position=75.0,
                    font_name="STHeitiMedium.ttc",
                    text_fore_color="#FFFFFF",
                    text_background_color=True,
                    font_size=60,
                    stroke_color="#000000",
                    stroke_width=1.5,
                    n_threads=2,
                    paragraph_number=3,  # 60초 분량으로 증가 (1 → 3)
                    video_source="pexels",
                    use_segment_matching=True  # 대본과 어울리는 배경영상 매칭 활성화
                )
                
                # 영어 버전 플래그 설정 (중요!)
                eng_params.is_english_version = True
                eng_params.korean_task_id = task_id  # 한글 task_id 전달 (이중 자막용)
                
                logger.info(f"🌍 English VideoParams created:")
                logger.info(f"   - language: {eng_params.video_language}")
                logger.info(f"   - voice: {eng_params.voice_name}")
                logger.info(f"   - is_english_version: {eng_params.is_english_version}")
                logger.info(f"   - korean_task_id: {eng_params.korean_task_id}")
                logger.info(f"   - script is English: {not any(ord(c) > 127 and ord(c) < 0x4e00 or 0xac00 <= ord(c) <= 0xd7a3 for c in eng_params.video_script[:100])}")
                logger.info(f"   - subtitle_provider will be: whisper (for accurate English subtitles)")
                
                # 영어 버전 생성 (진행률 모니터링)
                logger.info(f"🌍 Starting English video generation with task_id: {eng_task_id}")
                logger.info(f"🌍 Using original subtitle_provider: {original_subtitle_provider}")
                
                # 백그라운드에서 영어 버전 생성 시작
                import threading
                
                def generate_english_video():
                    try:
                        # 원래 subtitle_provider 설정 그대로 사용
                        logger.info(f"🌍 Starting English video generation")
                        tm.start(eng_task_id, eng_params, stop_at="video")
                    except Exception as e:
                        logger.error(f"English video generation failed: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        tasks[task_id]["english_status"] = "failed"
                        tasks[task_id]["english_error"] = str(e)
                
                # 영어 버전 생성 스레드 시작
                eng_thread = threading.Thread(target=generate_english_video)
                eng_thread.start()
                
                # 영어 버전 진행률 모니터링
                import time
                while eng_thread.is_alive():
                    eng_task_info = sm.state.get_task(eng_task_id)
                    if eng_task_info:
                        eng_progress = eng_task_info.get("progress", 0)
                        eng_state = eng_task_info.get("state", "processing")
                        eng_message = eng_task_info.get("message", "")
                        
                        # 한국어 task에 영어 버전 진행률 반영
                        tasks[task_id]["message"] = f"영어 버전 생성 중... ({int(eng_progress)}%)"
                        sm.state.update_task(task_id, state="processing", message=f"영어 버전 생성 중... ({int(eng_progress)}%)", progress=int(eng_progress))
                        
                        if eng_state == "complete":
                            break
                        elif eng_state == "failed":
                            tasks[task_id]["english_status"] = "failed"
                            tasks[task_id]["english_error"] = eng_message
                            break
                    
                    time.sleep(2)  # 2초마다 체크
                
                # 스레드 종료 대기
                eng_thread.join()
                
                tasks[task_id]["english_status"] = "complete"
                tasks[task_id]["message"] = "영어 버전 생성 완료!"
                task_info = sm.state.get_task(task_id)
                current_progress = task_info.get("progress", 100) if task_info else 100
                sm.state.update_task(task_id, state="complete", message="영어 버전 생성 완료!", progress=100)
                logger.success("🌍 English version generation complete!")
                
                # 영어 버전 자동 업로드
                if auto_upload:
                    try:
                        logger.info("🚀 Starting auto upload to YouTube (English)...")
                        tasks[task_id]["message"] = "유튜브 업로드 준비 중 (영어)..."
                        tasks[task_id]["english_upload_progress"] = 0
                        sm.state.update_task(task_id, state="processing", message="📤 유튜브 업로드 준비 중 (영어)...", progress=0)
                        
                        eng_task_dir = utils.task_dir(eng_task_id)
                        eng_video_path = os.path.join(eng_task_dir, "final-1.mp4")
                        
                        if not os.path.exists(eng_video_path):
                            logger.error(f"English video file not found: {eng_video_path}")
                            tasks[task_id]["english_upload_error"] = "영어 영상 파일을 찾을 수 없습니다"
                            return
                        
                        token_file = os.path.join(root_dir, "token.pickle")
                        client_secrets_file = os.path.join(root_dir, "client_secrets.json")
                        
                        if os.path.exists(token_file) and os.path.exists(client_secrets_file):
                            youtube = get_authenticated_service(client_secrets_file, token_file)
                            
                            eng_upload_title = f"#Shorts {eng_title}"
                            eng_description = f"Generated youtube-auto AI\n\nSubject: {eng_title}"
                            eng_keywords = ", ".join(eng_terms + [str(eng_title).strip()])
                            
                            tasks[task_id]["message"] = "유튜브 업로드 중 (영어)..."
                            tasks[task_id]["english_upload_progress"] = 50
                            sm.state.update_task(task_id, state="processing", message="📤 유튜브 업로드 중 (영어)...", progress=50)
                            
                            # 유튜브 업로드 (progress callback 추가)
                            def eng_upload_progress_callback(progress_percent):
                                # 업로드 진행률을 실시간으로 업데이트 (0-100%)
                                tasks[task_id]["english_upload_progress"] = progress_percent
                                sm.state.update_task(task_id, state="processing", message=f"📤 유튜브 업로드 중 (영어)... {progress_percent}%", progress=progress_percent)
                            
                            eng_vid_id = upload_video(
                                youtube,
                                eng_video_path,
                                title=eng_upload_title[:100],
                                description=eng_description,
                                category="22",
                                keywords=eng_keywords,
                                privacy_status="private",
                                progress_callback=eng_upload_progress_callback
                            )
                            
                            if eng_vid_id:
                                tasks[task_id]['english_video_id'] = eng_vid_id
                                eng_video_url = f"https://youtube.com/watch?v={eng_vid_id}"
                                tasks[task_id]["message"] = f"모든 버전 업로드 완료! 한국어: {tasks[task_id].get('video_id', 'N/A')}, 영어: {eng_vid_id}"
                                tasks[task_id]["english_upload_progress"] = 100
                                sm.state.update_task(task_id, state="complete", message="🎉 모든 버전 업로드 완료!", progress=100)
                                logger.success(f"🎉 English version auto upload success! Video ID: {eng_vid_id}")
                            else:
                                tasks[task_id]['english_upload_error'] = "영어 버전 YouTube 업로드 실패"
                                sm.state.update_task(task_id, state="complete", message="⚠️ 한국어 업로드 완료, 영어 업로드 실패", progress=100)
                                logger.error("English YouTube upload failed")
                        else:
                            tasks[task_id]["english_upload_error"] = "YouTube 인증이 필요합니다"
                            
                    except Exception as eng_upload_error:
                        import traceback
                        error_detail = traceback.format_exc()
                        logger.error(f"English upload error: {error_detail}")
                        tasks[task_id]["english_upload_error"] = str(eng_upload_error)
                        
            except Exception as eng_error:
                import traceback
                error_detail = traceback.format_exc()
                logger.error(f"English version generation error: {error_detail}")
                tasks[task_id]["english_status"] = "failed"
                tasks[task_id]["english_error"] = str(eng_error)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"ERROR in background task: {error_detail}")
        
        # 에러 상태 업데이트
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["message"] = f"생성 실패: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def home():
    """모바일 UI 제공"""
    html_path = root_dir / "webui" / "mobile_simple.html"
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/generate")
async def generate_video(request: VideoRequest, background_tasks: BackgroundTasks):
    """영상 생성 (기존 로직 그대로 사용)"""
    try:
        # Task ID 생성
        task_id = str(uuid4())
        
        # VideoParams 생성 (기본 설정)
        params = VideoParams(
            video_subject=request.subject,
            video_aspect=VideoAspect.portrait,  # 세로 (쇼츠)
            video_concat_mode=VideoConcatMode.sequential,
            video_transition_mode=VideoTransitionMode.none,
            video_count=1,
            video_clip_duration=5,
            video_script="",  # LLM이 자동 생성
            video_terms="",  # LLM이 자동 생성
            video_language="ko-KR",  # 한국어 명시
            voice_name="gtts:ko-한국어",  # gTTS 한국어 음성
            voice_rate=1.3,  # 1.3배속 (이전 사용 속도)
            voice_volume=1.0,
            bgm_type="random",
            bgm_file="",
            bgm_volume=0.05,  # 배경 음악 볼륨 (0.1 → 0.05)
            subtitle_enabled=True,
            subtitle_position="custom",
            custom_position=75.0,
            font_name="STHeitiMedium.ttc",
            text_fore_color="#FFFFFF",
            text_background_color=True,
            font_size=60,
            stroke_color="#000000",
            stroke_width=1.5,
            n_threads=2,
            paragraph_number=3,  # 60초 분량으로 증가 (1 → 3)
            video_source="pexels",
            use_segment_matching=True
        )
        
        # 백그라운드에서 영상 생성 실행
        background_tasks.add_task(run_video_generation, task_id, params, request.auto_upload, request.create_global)
        
        # 즉시 응답 반환
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "영상 생성이 시작되었습니다"
        }
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"ERROR: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """작업 상태 조회"""
    from app.services import state as sm
    
    try:
        # state manager에서 실제 상태 가져오기
        task_info = sm.state.get_task(task_id)
        
        if not task_info:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
        
        status = task_info.get("state", "processing")
        progress = task_info.get("progress", 0)
        message = task_info.get("message", "처리 중...")
        
        # 상태 변환
        if status == "complete":
            status = "complete"
        elif status == "failed":
            status = "failed"
        else:
            status = "processing"
        
        # 결과 파일 경로
        result = None
        video_id = None
        upload_error = None
        english_video_id = None
        english_status = None
        english_error = None
        english_upload_error = None
        
        if status == "complete":
            task_dir = tasks.get(task_id, {}).get("task_dir", "")
            if task_dir:
                video_path = os.path.join(task_dir, "final-1.mp4")
                if os.path.exists(video_path):
                    result = {"videos": [video_path]}
            
            # 업로드 정보 추가
            video_id = tasks.get(task_id, {}).get("video_id")
            upload_error = tasks.get(task_id, {}).get("upload_error")
            
            # 영어 버전 정보 추가
            english_video_id = tasks.get(task_id, {}).get("english_video_id")
            english_status = tasks.get(task_id, {}).get("english_status")
            english_error = tasks.get(task_id, {}).get("english_error")
            english_upload_error = tasks.get(task_id, {}).get("english_upload_error")
            
            # 업로드 상태에 따라 메시지 업데이트
            if video_id and english_video_id:
                message = tasks.get(task_id, {}).get("message", f"모든 버전 업로드 완료! 한국어: {video_id}, 영어: {english_video_id}")
            elif video_id:
                message = tasks.get(task_id, {}).get("message", f"한국어 버전 업로드 완료! https://youtube.com/watch?v={video_id}")
            elif upload_error:
                message = tasks.get(task_id, {}).get("message", f"영상 생성 완료 (업로드 오류: {upload_error})")
        
        return {
            "task_id": task_id,
            "status": status,
            "progress": int(progress),
            "message": message,
            "result": result,
            "video_id": video_id,
            "upload_error": upload_error,
            "english_video_id": english_video_id,
            "english_status": english_status,
            "english_error": english_error,
            "english_upload_error": english_upload_error,
            "error": task_info.get("error")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────
# 판매자 전용: 라이선스 생성 페이지
# ─────────────────────────────────────────────
ADMIN_PASSWORD = "0070"

@app.get("/admin/license", response_class=HTMLResponse)
async def license_admin_page():
    """라이선스 생성 관리 페이지"""
    html = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>라이선스 생성기</title>
<style>
  body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; margin: 0; padding: 20px; }
  .container { max-width: 500px; margin: 0 auto; }
  h2 { color: #a78bfa; text-align: center; margin-bottom: 30px; }
  .card { background: #16213e; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
  label { display: block; margin-bottom: 6px; color: #a78bfa; font-size: 14px; }
  input, select { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #334; background: #0f3460; color: #fff; font-size: 15px; box-sizing: border-box; margin-bottom: 16px; }
  button { width: 100%; padding: 12px; background: #7c3aed; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
  button:hover { background: #6d28d9; }
  .result { background: #0f3460; border-radius: 8px; padding: 16px; margin-top: 16px; display: none; }
  .key { font-size: 22px; font-weight: bold; color: #34d399; letter-spacing: 2px; text-align: center; margin: 10px 0; }
  .info { font-size: 13px; color: #94a3b8; text-align: center; }
  .copy-btn { background: #059669; margin-top: 10px; }
  .copy-btn:hover { background: #047857; }
  .history { max-height: 300px; overflow-y: auto; }
  .history-item { border-bottom: 1px solid #334; padding: 10px 0; font-size: 13px; }
  .history-key { color: #34d399; font-weight: bold; }
  .error { color: #f87171; text-align: center; margin-top: 10px; }
</style>
</head>
<body>
<div class="container">
  <h2>🔑 라이선스 생성기</h2>

  <div class="card" id="loginCard">
    <label>관리자 비밀번호</label>
    <input type="password" id="password" placeholder="비밀번호 입력" onkeydown="if(event.key==='Enter') login()">
    <button onclick="login()">로그인</button>
    <div class="error" id="loginError"></div>
  </div>

  <div class="card" id="mainCard" style="display:none">
    <label>고객명</label>
    <input type="text" id="customerName" placeholder="홍길동">
    <label>유효 기간</label>
    <select id="days">
      <option value="30">30일 (1개월)</option>
      <option value="90">90일 (3개월)</option>
      <option value="180">180일 (6개월)</option>
      <option value="365" selected>365일 (1년)</option>
      <option value="730">730일 (2년)</option>
    </select>
    <label>메모 (선택)</label>
    <input type="text" id="memo" placeholder="결제 채널, 금액 등">
    <button onclick="generateKey()">🔑 라이선스 키 생성</button>

    <div class="result" id="result">
      <div class="info" id="resultInfo"></div>
      <div class="key" id="resultKey"></div>
      <button class="copy-btn" onclick="copyKey()">📋 키 복사</button>
    </div>
  </div>

  <div class="card" id="historyCard" style="display:none">
    <b style="color:#a78bfa">생성 기록</b>
    <div class="history" id="historyList"></div>
  </div>
</div>

<script>
let token = '';

async function login() {
  const pw = document.getElementById('password').value;
  const res = await fetch('/admin/license/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({password: pw})
  });
  const data = await res.json();
  if (data.ok) {
    token = pw;
    document.getElementById('loginCard').style.display = 'none';
    document.getElementById('mainCard').style.display = 'block';
    document.getElementById('historyCard').style.display = 'block';
    loadHistory();
  } else {
    document.getElementById('loginError').textContent = '비밀번호가 틀렸습니다';
  }
}

async function generateKey() {
  const customerName = document.getElementById('customerName').value.trim();
  const days = parseInt(document.getElementById('days').value);
  const memo = document.getElementById('memo').value.trim();

  const res = await fetch('/admin/license/generate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({password: token, customer_name: customerName, days: days, memo: memo})
  });
  const data = await res.json();
  if (data.license_key) {
    document.getElementById('resultKey').textContent = data.license_key;
    document.getElementById('resultInfo').textContent = `${customerName || '(이름없음)'} · ${days}일 · 만료: ${data.expiry_date}`;
    document.getElementById('result').style.display = 'block';
    loadHistory();
  }
}

function copyKey() {
  const key = document.getElementById('resultKey').textContent;
  navigator.clipboard.writeText(key).then(() => alert('복사됨: ' + key));
}

async function loadHistory() {
  const res = await fetch('/admin/license/history?password=' + token);
  const data = await res.json();
  const list = document.getElementById('historyList');
  list.innerHTML = data.licenses.slice().reverse().map(l =>
    `<div class="history-item">
      <span class="history-key">${l.license_key}</span><br>
      ${l.customer_name || '(이름없음)'} · ${l.days}일 · 만료: ${l.expiry_date}<br>
      <span style="color:#64748b">${l.created_at}${l.memo ? ' · ' + l.memo : ''}</span>
    </div>`
  ).join('');
}
</script>
</body>
</html>"""
    return html


@app.post("/admin/license/login")
async def license_login(data: dict):
    if data.get("password") != ADMIN_PASSWORD:
        return {"ok": False}
    return {"ok": True}


@app.post("/admin/license/generate")
async def license_generate(data: dict):
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="인증 실패")

    from app.services.license import generate_license_key
    from datetime import datetime, timedelta
    import json
    from pathlib import Path

    days = int(data.get("days", 365))
    customer_name = data.get("customer_name", "")
    memo = data.get("memo", "")

    license_key = generate_license_key(days, customer_name)
    expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    # 기록 저장
    db_path = Path("license_database.json")
    licenses = []
    if db_path.exists():
        try:
            licenses = json.loads(db_path.read_text(encoding="utf-8"))
        except:
            pass
    licenses.append({
        "license_key": license_key,
        "customer_name": customer_name,
        "days": days,
        "expiry_date": expiry_date,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "memo": memo
    })
    db_path.write_text(json.dumps(licenses, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"license_key": license_key, "expiry_date": expiry_date}


@app.get("/admin/license/history")
async def license_history(password: str = ""):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="인증 실패")

    from pathlib import Path
    import json

    db_path = Path("license_database.json")
    licenses = []
    if db_path.exists():
        try:
            licenses = json.loads(db_path.read_text(encoding="utf-8"))
        except:
            pass
    return {"licenses": licenses}


@app.post("/admin/license/delete")
async def license_delete(data: dict):
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="인증 실패")

    from pathlib import Path
    import json

    license_key = data.get("license_key", "")
    db_path = Path("license_database.json")
    licenses = []
    if db_path.exists():
        try:
            licenses = json.loads(db_path.read_text(encoding="utf-8"))
        except:
            pass

    licenses = [l for l in licenses if l.get("license_key") != license_key]
    db_path.write_text(json.dumps(licenses, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True}


if __name__ == "__main__":
    print("=" * 60)
    print("🎬 AI 영상 생성 모바일 서버 시작")
    print("=" * 60)
    print(f"📱 로컬 접속: http://localhost:8000")
    print(f"🔑 라이선스 생성: http://localhost:8000/admin/license")
    print(f"🌐 외부 접속: ngrok http 8000 실행 후 URL 사용")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
