# -*- coding: utf-8 -*-
import math
import os.path
import re
from os import path

from loguru import logger

from app.config import config
from app.models import const
from app.models.schema import VideoConcatMode, VideoParams
from app.services import llm, material, subtitle, video, voice
from app.services import state as sm
from app.utils import utils


def _remove_dash_from_subtitle_file(subtitle_path: str):
    """
    자막 파일에서 "-" 문자만 제거 (한국어 버전용)
    """
    try:
        if not os.path.exists(subtitle_path):
            logger.warning(f"Subtitle file not found: {subtitle_path}")
            return
            
        # 자막 파일 읽기
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            logger.warning(f"Subtitle file is empty: {subtitle_path}")
            return
        
        # "-" 문자만 제거 (줄바꿈과 공백은 유지)
        cleaned_content = content.replace('-', '')
        
        # 내용이 변경되었는지 확인
        if cleaned_content != content:
            # 백업 파일 생성
            backup_path = subtitle_path + ".backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 파일에 다시 저장
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
                
            logger.info(f"Removed dash characters from subtitle file: {subtitle_path}")
            logger.debug(f"Backup created: {backup_path}")
        else:
            logger.debug(f"No dash characters found in subtitle file: {subtitle_path}")
        
    except Exception as e:
        logger.error(f"Failed to remove dash characters from subtitle: {str(e)}")
        # 오류 발생 시 원본 파일 복원 시도
        backup_path = subtitle_path + ".backup"
        if os.path.exists(backup_path):
            try:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                with open(subtitle_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                logger.info(f"Restored original subtitle file from backup")
            except Exception as restore_error:
                logger.error(f"Failed to restore subtitle file: {restore_error}")


def generate_script(task_id, params):
    logger.info("\n\n## generating video script")
    # If real-time auto generation is enabled, always use AI to generate script from the subject
    use_auto = config.ui.get("auto_script_enabled", True)
    if use_auto:
        video_script = llm.generate_script(
            video_subject=params.video_subject,
            language=params.video_language,
            paragraph_number=params.paragraph_number,
        )
    else:
        video_script = params.video_script.strip()
        if not video_script:
            video_script = llm.generate_script(
                video_subject=params.video_subject,
                language=params.video_language,
                paragraph_number=params.paragraph_number,
            )
        else:
            logger.debug(f"video script: \n{video_script}")

    if not video_script:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        logger.error("failed to generate video script.")
        return None

    return video_script


def generate_terms(task_id, params, video_script):
    logger.info("\n\n## generating video terms")
    video_terms = params.video_terms
    if not video_terms:
        video_terms = llm.generate_terms(
            video_subject=params.video_subject, video_script=video_script, amount=5
        )
    else:
        if isinstance(video_terms, str):
            video_terms = [term.strip() for term in re.split(r"[,，]", video_terms)]
        elif isinstance(video_terms, list):
            video_terms = [term.strip() for term in video_terms]
        else:
            raise ValueError("video_terms must be a string or a list of strings.")

        logger.debug(f"video terms: {utils.to_json(video_terms)}")

    if not video_terms:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        logger.error("failed to generate video terms.")
        return None

    return video_terms


def save_script_data(task_id, video_script, video_terms, params):
    script_file = path.join(utils.task_dir(task_id), "script.json")
    script_data = {
        "script": video_script,
        "search_terms": video_terms,
        "params": params,
    }

    with open(script_file, "w", encoding="utf-8") as f:
        f.write(utils.to_json(script_data))


def generate_audio(task_id, params, video_script):
    '''
    Generate audio for the video script.
    If a custom audio file is provided, it will be used directly.
    There will be no subtitle maker object returned in this case.
    Otherwise, TTS will be used to generate the audio.
    Returns:
        - audio_file: path to the generated or provided audio file
        - audio_duration: duration of the audio in seconds
        - sub_maker: subtitle maker object if TTS is used, None otherwise
    '''
    logger.info("\n\n## generating audio")
    custom_audio_file = params.custom_audio_file
    if not custom_audio_file or not os.path.exists(custom_audio_file):
        if custom_audio_file:
            logger.warning(
                f"custom audio file not found: {custom_audio_file}, using TTS to generate audio."
            )
        else:
            logger.info("no custom audio file provided, using TTS to generate audio.")
        audio_file = path.join(utils.task_dir(task_id), "audio.mp3")
        sub_maker = voice.tts(
            text=video_script,
            voice_name=voice.parse_voice_name(params.voice_name),
            voice_rate=params.voice_rate,
            voice_file=audio_file,
        )
        if sub_maker is None:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            logger.error(
                """failed to generate audio:
1. check if the language of the voice matches the language of the video script.
2. check if the network is available. If you are in China, it is recommended to use a VPN and enable the global traffic mode.
            """.strip()
            )
            return None, None, None
        audio_duration = math.ceil(voice.get_audio_duration(sub_maker))
        if audio_duration == 0:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            logger.error("failed to get audio duration.")
            return None, None, None
        return audio_file, audio_duration, sub_maker
    else:
        logger.info(f"using custom audio file: {custom_audio_file}")
        audio_duration = voice.get_audio_duration(custom_audio_file)
        if audio_duration == 0:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            logger.error("failed to get audio duration from custom audio file.")
            return None, None, None
        return custom_audio_file, audio_duration, None

def generate_subtitle(task_id, params, video_script, sub_maker, audio_file):
    '''
    Generate subtitle for the video script.
    If subtitle generation is disabled or no subtitle maker is provided, it will return an empty string.
    Otherwise, it will generate the subtitle using the specified provider.
    Returns:
        - subtitle_path: path to the generated subtitle file
    '''
    logger.info("\n\n## generating subtitle")
    if not params.subtitle_enabled:
        return ""

    # 영어 버전은 subtitle_en.srt로 저장
    is_english_version = getattr(params, 'is_english_version', False)
    if is_english_version:
        subtitle_path = path.join(utils.task_dir(task_id), "subtitle_en.srt")
        
        # 한글 자막 복사 (이중 자막용)
        korean_task_id = getattr(params, 'korean_task_id', None)
        if korean_task_id:
            korean_subtitle_path = path.join(utils.task_dir(korean_task_id), "subtitle.srt")
            target_korean_subtitle_path = path.join(utils.task_dir(task_id), "subtitle.srt")
            if os.path.exists(korean_subtitle_path):
                import shutil
                shutil.copy2(korean_subtitle_path, target_korean_subtitle_path)
                logger.info(f"✅ Copied Korean subtitle for dual subtitle: {korean_subtitle_path} -> {target_korean_subtitle_path}")
            else:
                logger.warning(f"⚠️ Korean subtitle not found: {korean_subtitle_path}")
    else:
        subtitle_path = path.join(utils.task_dir(task_id), "subtitle.srt")
    
    # 영어 버전은 항상 영어 음성에 맞는 새로운 자막을 생성 (동기화 보장)
    if getattr(params, 'is_english_version', False):
        logger.info(f"🌍 English version detected, generating fresh subtitle for proper audio sync")
        logger.info(f"Skipping Korean subtitle translation to ensure English audio-subtitle sync")
        # 아래 기존 로직으로 진행하여 영어 음성에 맞는 자막 생성
    
    # 기존 자막 생성 로직 (영어 버전도 여기서 영어 음성에 맞게 새로 생성)
    subtitle_provider = config.app.get("subtitle_provider", "edge").strip().lower()
    
    # 영어 버전인지 확인하여 로그에 표시
    is_english_version = getattr(params, 'is_english_version', False)
    version_info = "🌍 English version" if is_english_version else "🇰🇷 Korean version"
    logger.info(f"\n\n## generating subtitle for {version_info}, provider: {subtitle_provider}")
    logger.info(f"Audio file for subtitle timing: {audio_file}")
    logger.info(f"Video script length: {len(video_script)} characters")

    subtitle_fallback = False
    is_gtts_voice = hasattr(sub_maker, '__class__') and sub_maker.__class__.__name__ == 'GTTSSubMaker'
    
    if sub_maker is None:
        subtitle_fallback = True
    elif is_gtts_voice:
        # gTTS 사용 시 gTTS 전용 자막 생성
        logger.info("Using gTTS-based subtitle generation")
        try:
            from app.services import voice
            # gTTS SubMaker를 사용하여 자막 파일 생성
            voice.create_gtts_subtitle(sub_maker, video_script, subtitle_path)
            if os.path.exists(subtitle_path) and os.path.getsize(subtitle_path) > 0:
                logger.info(f"✅ gTTS subtitle created successfully")
                # 임시로 "-" 문자 제거 비활성화 (테스트용)
                # if not getattr(params, 'is_english_version', False):
                #     logger.info("Removing '-' characters from Korean gTTS subtitle...")
                #     _remove_dash_from_subtitle_file(subtitle_path)
                #     logger.info("✅ Dash characters removed from Korean gTTS subtitle")
            else:
                subtitle_fallback = True
                logger.warning("gTTS subtitle creation failed, fallback to whisper")
        except Exception as e:
            logger.error(f"gTTS subtitle creation error: {str(e)}")
            subtitle_fallback = True
    else:
        # Edge TTS 사용 시 기존 로직
        if subtitle_provider == "edge":
            from app.services import voice
            voice.create_subtitle(
                text=video_script, sub_maker=sub_maker, subtitle_file=subtitle_path
            )
            if not os.path.exists(subtitle_path) or os.path.getsize(subtitle_path) == 0:
                subtitle_fallback = True
                logger.warning("subtitle file not found or empty, fallback to whisper")
            else:
                # 임시로 "-" 문자 제거 비활성화 (테스트용)
                # if not getattr(params, 'is_english_version', False):
                #     logger.info("Removing '-' characters from Korean Edge TTS subtitle...")
                #     _remove_dash_from_subtitle_file(subtitle_path)
                #     logger.info("✅ Dash characters removed from Korean Edge TTS subtitle")
                pass

    if subtitle_provider == "whisper" or subtitle_fallback:
        # Whisper fallback enabled for better subtitle generation
        version_info = "🌍 English version" if getattr(params, 'is_english_version', False) else "🇰🇷 Korean version"
        logger.info(f"Using Whisper for {version_info} subtitle generation...")
        logger.info(f"Audio file to analyze: {audio_file}")
        
        try:
            subtitle.create(audio_file=audio_file, subtitle_file=subtitle_path)
            logger.info(f"✅ Whisper subtitle created for {version_info}")
            logger.info("\n\n## correcting subtitle")
            subtitle.correct(subtitle_file=subtitle_path, video_script=video_script)
            logger.info(f"✅ Subtitle correction completed for {version_info}")
            
            # 임시로 "-" 문자 제거 비활성화 (테스트용)
            # if not getattr(params, 'is_english_version', False):
            #     logger.info("Removing '-' characters from Korean subtitle...")
            #     _remove_dash_from_subtitle_file(subtitle_path)
            #     logger.info("✅ Dash characters removed from Korean subtitle")
            
        except Exception as e:
            logger.error(f"❌ Whisper subtitle generation failed for {version_info}: {str(e)}")
            # Create simple subtitle from script as fallback
            logger.info(f"Creating simple subtitle from script for {version_info}...")
            try:
                from app.services import voice
                # Try to create subtitle using script timing estimation
                voice.create_simple_subtitle_from_script(
                    text=video_script, 
                    subtitle_file=subtitle_path,
                    audio_duration=None  # Will be calculated from audio file
                )
                logger.info(f"✅ Simple subtitle created for {version_info}")
            except Exception as e2:
                logger.error(f"❌ Simple subtitle creation also failed for {version_info}: {str(e2)}")
                return ""

    subtitle_lines = subtitle.file_to_subtitles(subtitle_path)
    if not subtitle_lines:
        logger.warning(f"subtitle file is invalid: {subtitle_path}")
        if os.path.exists(subtitle_path) and os.path.getsize(subtitle_path) > 0:
             return subtitle_path
        return ""

    # 영어 버전인 경우, 한글 자막을 영어 자막 타이밍에 맞춰 조정
    if is_english_version:
        korean_subtitle_path = path.join(utils.task_dir(task_id), "subtitle.srt")
        if os.path.exists(korean_subtitle_path):
            logger.info(f"🔄 Adjusting Korean subtitle timing to match English audio...")
            try:
                _sync_korean_to_english_timing(subtitle_path, korean_subtitle_path)
                logger.info(f"✅ Korean subtitle timing adjusted to English subtitle")
            except Exception as e:
                logger.error(f"❌ Failed to sync subtitle timing: {str(e)}")
                # AI 매칭 실패 시 영어 영상 생성 중단
                raise Exception(f"이중 자막 동기화 실패 (API 할당량 소진 가능성): {str(e)}")

    return subtitle_path


def _sync_korean_to_english_timing(english_srt_path, korean_srt_path):
    """
    한글 자막의 타이밍을 영어 자막에 맞춰 조정 (AI 기반 의미 매칭)
    영어 자막과 한글 자막을 의미 단위로 매칭하여 더 자연스러운 이중 자막 생성
    
    AI 매칭 실패 시 예외 발생 (폴백 없음)
    """
    # 영어 자막 파싱 (타이밍 기준)
    english_subtitles = []
    with open(english_srt_path, 'r', encoding='utf-8') as f:
        content = f.read().strip().split('\n\n')
        for block in content:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                timing = lines[1]
                text = '\n'.join(lines[2:])
                english_subtitles.append((timing, text))
    
    # 한글 자막 파싱 (전체 텍스트)
    korean_subtitles = []
    with open(korean_srt_path, 'r', encoding='utf-8') as f:
        content = f.read().strip().split('\n\n')
        for block in content:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                text = '\n'.join(lines[2:])
                korean_subtitles.append(text)
    
    # AI를 사용하여 영어-한글 자막 매칭
    logger.info(f"🤖 AI 기반 자막 매칭 시작: 영어 {len(english_subtitles)}개, 한글 {len(korean_subtitles)}개")
    
    # 영어 전체 텍스트와 한글 전체 텍스트
    english_full = '\n'.join([text for _, text in english_subtitles])
    korean_full = '\n'.join(korean_subtitles)
    
    # AI에게 매칭 요청
    from app.services import llm
    
    prompt = f"""You are a subtitle synchronization expert. Match Korean subtitles to English subtitles based on meaning.

English subtitles ({len(english_subtitles)} segments):
{english_full}

Korean subtitles (original):
{korean_full}

Task: Split the Korean text into exactly {len(english_subtitles)} segments that match the meaning of each English subtitle.
Return ONLY the Korean text segments, one per line, in order. No numbering, no explanations.
Each line should correspond to one English subtitle segment."""

    response = llm._generate_response(prompt)
    
    if not response or response.startswith("Error"):
        logger.error(f"❌ AI 매칭 실패: API 응답 없음 또는 오류")
        raise Exception("AI 자막 매칭 실패: API 할당량 소진 가능성")
    
    # AI 응답을 줄 단위로 분할
    matched_korean = [line.strip() for line in response.strip().split('\n') if line.strip()]
    
    # 개수가 맞는지 확인
    if len(matched_korean) != len(english_subtitles):
        logger.error(f"❌ AI 매칭 개수 불일치: 예상 {len(english_subtitles)}, 실제 {len(matched_korean)}")
        raise Exception(f"AI 자막 매칭 실패: 세그먼트 개수 불일치 (API 할당량 소진 가능성)")
    
    logger.info(f"✅ AI 매칭 성공: {len(matched_korean)}개 세그먼트")
    
    # 매칭된 한글 자막으로 동기화
    synced_content = []
    for i, (timing, _) in enumerate(english_subtitles):
        if i < len(matched_korean):
            synced_content.append(f"{i+1}\n{timing}\n{matched_korean[i]}")
    
    # 동기화된 한글 자막 저장
    with open(korean_srt_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(synced_content) + '\n')
    
    logger.info(f"✅ 의미 기반 자막 동기화 완료")





def get_video_materials(task_id, params, video_terms, audio_duration, video_script=None):
    # 영어 버전에서 한국어 배경영상 재사용 확인 (korean_task_id가 있으면 재사용)
    if getattr(params, 'korean_task_id', None):
        korean_task_id = params.korean_task_id
        logger.info(f"\n\n## 🔄 Reusing Korean video materials from task: {korean_task_id}")
        
        try:
            # 한국어 태스크의 배경영상 정보 가져오기
            korean_task_info = sm.state.get_task(korean_task_id)
            if korean_task_info and korean_task_info.get("materials"):
                korean_materials = korean_task_info["materials"]
                logger.info(f"✅ Found {len(korean_materials)} Korean video materials to reuse")
                
                # 한국어 배경영상 파일들이 존재하는지 확인
                valid_materials = []
                for material_path in korean_materials:
                    if os.path.exists(material_path):
                        valid_materials.append(material_path)
                        logger.info(f"✅ Reusing Korean material: {os.path.basename(material_path)}")
                    else:
                        logger.warning(f"⚠️ Korean material not found: {material_path}")
                
                if valid_materials:
                    logger.info(f"🎬 Successfully reusing {len(valid_materials)} Korean video materials for English version")
                    return valid_materials
                else:
                    logger.warning("❌ No valid Korean materials found, falling back to new material search")
            else:
                logger.warning("❌ Korean task materials not found, falling back to new material search")
        except Exception as e:
            logger.error(f"❌ Failed to reuse Korean materials: {e}, falling back to new material search")
    
    # 기본 배경영상 검색 로직
    
    if params.video_source == "local":
        logger.info("\n\n## preprocess local materials")
        if not params.video_materials:
            logger.warning("no local materials provided, will use solid background fallback")
            return []
        materials = video.preprocess_video(
            materials=params.video_materials, clip_duration=params.video_clip_duration
        )
        if not materials:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            logger.error(
                "no valid materials found, please check the materials and try again."
            )
            return None
        return [material_info.url for material_info in materials]
    else:
        # 세그먼트 기반 매칭 사용 여부 확인
        use_segment_matching = getattr(params, 'use_segment_matching', True)  # 기본값 True로 복원
        
        if use_segment_matching and video_script:  # video_script가 있을 때만 세그먼트 매칭 사용
            logger.info(f"\n\n## 🎯 Using segment-based video matching")
            from app.services.script_segment_matcher import get_matcher
            
            # 대본을 세그먼트로 분할하고 각 세그먼트에 맞는 키워드 생성
            matcher = get_matcher()
            target_segment_count = getattr(params, 'target_segment_count', None)
            segment_infos = matcher.match_segments_to_videos(
                script=video_script,
                video_duration=audio_duration,
                target_segment_count=target_segment_count
            )
            
            # 세그먼트별로 영상 다운로드
            segment_results = material.download_videos_by_segments(
                task_id=task_id,
                segment_infos=segment_infos,
                source=params.video_source,
                video_aspect=params.video_aspect,
                max_clip_duration=params.video_clip_duration,
            )
            
            # 세그먼트별 영상을 순서대로 합쳐서 반환
            downloaded_videos = []
            for seg_result in segment_results:
                downloaded_videos.extend(seg_result['video_paths'])
            
            if not downloaded_videos:
                logger.warning("⚠️ Segment-based matching failed, falling back to traditional method")
                use_segment_matching = False
            else:
                logger.success(f"✅ Segment-based matching complete: {len(downloaded_videos)} videos")
                # 세그먼트 정보는 로그로만 기록 (저장 기능은 선택적)
                logger.debug(f"Segment results: {len(segment_results)} segments processed")
                return downloaded_videos
        
        # 기존 방식 (폴백 또는 세그먼트 매칭 비활성화 시)
        if not use_segment_matching:
            logger.info(f"\n\n## downloading videos from {params.video_source} (traditional method)")
            downloaded_videos = material.download_videos(
                task_id=task_id,
                search_terms=video_terms,
                source=params.video_source,
                video_aspect=params.video_aspect,
                video_contact_mode=params.video_concat_mode,
                audio_duration=audio_duration * params.video_count,
                max_clip_duration=params.video_clip_duration,
            )
            if not downloaded_videos:
                sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
                logger.error(
                    "failed to download videos, maybe the network is not available. if you are in China, please use a VPN."
                )
                return None
            return downloaded_videos


def generate_final_videos(
    task_id, params, downloaded_videos, audio_file, subtitle_path
):
    final_video_paths = []
    combined_video_paths = []
    video_concat_mode = (
        params.video_concat_mode if params.video_count == 1 else VideoConcatMode.random
    )
    video_transition_mode = params.video_transition_mode

    _progress = 50
    for i in range(params.video_count):
        index = i + 1
        
        sm.state.update_task(task_id, progress=_progress, message=f"영상 클립 병합 중 ({index}/{params.video_count})...")
        
        combined_video_path = path.join(
            utils.task_dir(task_id), f"combined-{index}.mp4"
        )
        logger.info(f"\n\n## combining video: {index} => {combined_video_path}")
        
        # Calculate progress range for this step
        # Total progress allocated for this video's combine step is (50 / params.video_count / 2)
        step_progress_size = 50 / params.video_count / 2
        start_progress = _progress
        
        def combine_progress_callback(percent):
            # percent is 0-100
            current_p = start_progress + (percent / 100) * step_progress_size
            sm.state.update_task(task_id, progress=current_p, message=f"영상 클립 병합 중 ({index}/{params.video_count}) - {percent}%")

        video.combine_videos(
            combined_video_path=combined_video_path,
            video_paths=downloaded_videos,
            audio_file=audio_file,
            video_aspect=params.video_aspect,
            video_concat_mode=video_concat_mode,
            video_transition_mode=video_transition_mode,
            max_clip_duration=params.video_clip_duration,
            threads=params.n_threads,
            progress_callback=combine_progress_callback,
        )

        _progress += step_progress_size
        sm.state.update_task(task_id, progress=_progress, message=f"최종 영상 렌더링 중 ({index}/{params.video_count}) - 몇 분 정도 걸릴 수 있습니다...")

        final_video_path = path.join(utils.task_dir(task_id), f"final-{index}.mp4")

        logger.info(f"\n\n## generating video: {index} => {final_video_path}")
        video.generate_video(
            video_path=combined_video_path,
            audio_path=audio_file,
            subtitle_path=subtitle_path,
            output_file=final_video_path,
            params=params,
        )

        # 쿠팡 파트너스 제품 정보는 설명란과 댓글에만 표시 (영상 오버레이 제거)
        if (hasattr(params, 'coupang_overlay_data') and 
            params.coupang_overlay_data is not None and 
            isinstance(params.coupang_overlay_data, list) and 
            len(params.coupang_overlay_data) > 0):
            logger.info(f"🛒 쿠팡파트너스 제품 정보: {len(params.coupang_overlay_data)}개 (설명란/댓글에만 표시)")
            for i, product in enumerate(params.coupang_overlay_data, 1):
                logger.info(f"  제품 {i}: {product.get('name', 'Unknown')} - {product.get('price', 'N/A')}")

        _progress += 50 / params.video_count / 2
        sm.state.update_task(task_id, progress=_progress, message=f"영상 {index} 준비 완료.")

        final_video_paths.append(final_video_path)
        combined_video_paths.append(combined_video_path)

    return final_video_paths, combined_video_paths


def start(task_id, params: VideoParams, stop_at: str = "video"):
    logger.info(f"start task: {task_id}, stop_at: {stop_at}")
    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=5, message="작업 시작 중...")

    if type(params.video_concat_mode) is str:
        params.video_concat_mode = VideoConcatMode(params.video_concat_mode)

    # 1. Generate script
    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=5, message="영상 대본 생성 중...")
    video_script = generate_script(task_id, params)
    if not video_script or "Error: " in video_script:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED, message="대본 생성 실패")
        return

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=10, message="대본 생성 완료")

    if stop_at == "script":
        sm.state.update_task(
            task_id, state=const.TASK_STATE_COMPLETE, progress=100, script=video_script, message="대본 생성 완료"
        )
        return {"script": video_script}

    # 2. Generate terms
    video_terms = ""
    if params.video_source != "local":
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=12, message="영상 키워드 생성 중...")
        try:
            video_terms = generate_terms(task_id, params, video_script)
        except Exception as e:
            logger.error(f"Failed to generate terms: {e}")
            video_terms = []
        if not video_terms:
            logger.warning("Keywords generation failed, using subject as fallback.")
            video_terms = [params.video_subject]
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=15, message=f"키워드: {', '.join(video_terms[:3])}...")
    else:
        video_terms = [] # Local source doesn't need search terms

    save_script_data(task_id, video_script, video_terms, params)

    if stop_at == "terms":
        sm.state.update_task(
            task_id, state=const.TASK_STATE_COMPLETE, progress=100, terms=video_terms, message="키워드 생성 완료"
        )
        return {"script": video_script, "terms": video_terms}

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=20, message="오디오 생성 중...")

    # 3. Generate audio
    logger.info("Calling generate_audio...")
    audio_file, audio_duration, sub_maker = generate_audio(
        task_id, params, video_script
    )
    logger.info(f"generate_audio returned: {audio_file}, {audio_duration}")
    if not audio_file:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED, message="오디오 생성 실패")
        return

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=30, message="자막 생성 중...")

    if stop_at == "audio":
        sm.state.update_task(
            task_id,
            state=const.TASK_STATE_COMPLETE,
            progress=100,
            audio_file=audio_file,
            message="오디오 생성 완료"
        )
        return {"audio_file": audio_file, "audio_duration": audio_duration}

    # 4. Generate subtitle
    subtitle_path = generate_subtitle(
        task_id, params, video_script, sub_maker, audio_file
    )

    if stop_at == "subtitle":
        sm.state.update_task(
            task_id,
            state=const.TASK_STATE_COMPLETE,
            progress=100,
            subtitle_path=subtitle_path,
            message="자막 생성 완료"
        )
        return {"subtitle_path": subtitle_path}

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=40, message="영상 자료 준비 중...")

    # 5. Get video materials
    downloaded_videos = get_video_materials(
        task_id, params, video_terms, audio_duration, video_script
    )
    if not downloaded_videos:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED, message="자료 준비 실패")
        return

    if stop_at == "materials":
        sm.state.update_task(
            task_id,
            state=const.TASK_STATE_COMPLETE,
            progress=100,
            materials=downloaded_videos,
            message="자료 준비 완료"
        )
        return {"materials": downloaded_videos}

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=50, message="영상 합성 중 (시간이 다소 소요될 수 있습니다)...")

    # 6. Generate final videos
    final_video_paths, combined_video_paths = generate_final_videos(
        task_id, params, downloaded_videos, audio_file, subtitle_path
    )

    if not final_video_paths:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED, message="영상 생성 실패")
        return

    logger.success(
        f"task {task_id} finished, generated {len(final_video_paths)} videos."
    )

    kwargs = {
        "videos": final_video_paths,
        "combined_videos": combined_video_paths,
        "script": video_script,
        "terms": video_terms,
        "audio_file": audio_file,
        "audio_duration": audio_duration,
        "subtitle_path": subtitle_path,
        "materials": downloaded_videos,
    }
    sm.state.update_task(
        task_id, state=const.TASK_STATE_COMPLETE, progress=100, message="영상 생성 완료", **kwargs
    )
    return kwargs


if __name__ == "__main__":
    task_id = "task_id"
    params = VideoParams(
        video_subject="金钱的作用",
        voice_name="zh-CN-XiaoyiNeural-Female",
        voice_rate=1.0,
    )
    start(task_id, params, stop_at="video")

def generate_longform_video(task_id, params):
    """롱폼 영상 생성 메인 함수"""
    logger.info(f"\n\n## Starting long-form video generation for task: {task_id}")
    
    try:
        # 1. 롱폼 대본 생성
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=10, message="롱폼 대본 생성 중...")
        
        longform_script = llm.generate_longform_script(
            video_subject=params.video_subject,
            language=params.video_language,
            duration_minutes=getattr(params, 'longform_duration', 10)
        )
        
        if not longform_script or "실패" in longform_script:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED, message="롱폼 대본 생성 실패")
            return None
        
        # 2. 대본을 세그먼트로 분할
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=20, message="대본 세그먼트 분할 중...")
        
        segments = llm.split_longform_script(longform_script, segment_duration=3)
        logger.info(f"Created {len(segments)} segments for long-form video")
        
        # 3. 각 세그먼트별로 영상 생성
        segment_videos = []
        segment_audios = []
        
        for i, segment in enumerate(segments):
            logger.info(f"\n## Processing segment {i+1}/{len(segments)}")
            sm.state.update_task(
                task_id, 
                state=const.TASK_STATE_PROCESSING, 
                progress=30 + (i * 50 // len(segments)), 
                message=f"세그먼트 {i+1}/{len(segments)} 처리 중..."
            )
            
            # 세그먼트별 파라미터 생성
            segment_params = params.copy()
            segment_params.video_script = segment
            segment_params.paragraph_number = 1  # 세그먼트는 이미 분할됨
            
            # 세그먼트별 배경 키워드 생성
            bg_keywords = llm.generate_longform_background_keywords(
                params.video_subject, segment, i+1
            )
            segment_params.video_terms = bg_keywords
            
            # 세그먼트 영상 생성
            segment_task_id = f"{task_id}_segment_{i+1}"
            segment_result = generate_single_segment(segment_task_id, segment_params, segment)
            
            if segment_result:
                segment_videos.append(segment_result['video'])
                segment_audios.append(segment_result['audio'])
            else:
                logger.error(f"Failed to generate segment {i+1}")
                sm.state.update_task(task_id, state=const.TASK_STATE_FAILED, message=f"세그먼트 {i+1} 생성 실패")
                return None
        
        # 4. 모든 세그먼트 병합
        sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=85, message="세그먼트 병합 중...")
        
        final_video = merge_longform_segments(task_id, segment_videos, params)
        
        if final_video:
            sm.state.update_task(
                task_id, 
                state=const.TASK_STATE_COMPLETE, 
                progress=100, 
                videos=[final_video],
                message="롱폼 영상 생성 완료"
            )
            logger.success(f"Long-form video generation completed: {final_video}")
            return final_video
        else:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED, message="세그먼트 병합 실패")
            return None
            
    except Exception as e:
        logger.error(f"Long-form video generation failed: {e}")
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED, message=f"롱폼 영상 생성 오류: {e}")
        return None


def generate_single_segment(task_id, params, script):
    """단일 세그먼트 영상 생성"""
    logger.info(f"Generating single segment: {task_id}")
    
    try:
        # 1. 오디오 생성
        audio_file, audio_duration, sub_maker = generate_audio(task_id, params, script)
        if not audio_file:
            return None
        
        # 2. 자막 생성
        subtitle_path = generate_subtitle(task_id, params, script, sub_maker, audio_file)
        
        # 3. 배경 영상 다운로드
        video_terms = getattr(params, 'video_terms', [])
        downloaded_videos = get_video_materials(task_id, params, video_terms, audio_duration, script)
        if not downloaded_videos:
            return None
        
        # 4. 최종 영상 생성
        final_videos = generate_final_videos(
            task_id, params, downloaded_videos, audio_file, subtitle_path
        )
        
        if final_videos:
            return {
                'video': final_videos[0],
                'audio': audio_file,
                'duration': audio_duration
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Single segment generation failed: {e}")
        return None


def merge_longform_segments(task_id, segment_videos, params):
    """롱폼 세그먼트들을 하나의 영상으로 병합"""
    logger.info(f"Merging {len(segment_videos)} segments into long-form video")
    
    try:
        from moviepy import VideoFileClip, concatenate_videoclips
        
        # 세그먼트 영상들 로드
        clips = []
        for video_path in segment_videos:
            if os.path.exists(video_path):
                clip = VideoFileClip(video_path)
                clips.append(clip)
            else:
                logger.warning(f"Segment video not found: {video_path}")
        
        if not clips:
            logger.error("No valid segment clips found")
            return None
        
        # 영상 병합
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # 출력 파일 경로
        output_path = os.path.join(utils.task_dir(task_id), f"longform_final_{task_id}.mp4")
        
        # 영상 저장
        final_clip.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )
        
        # 리소스 정리
        for clip in clips:
            clip.close()
        final_clip.close()
        
        logger.success(f"Long-form video merged successfully: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to merge long-form segments: {e}")
        return None