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

    subtitle_path = path.join(utils.task_dir(task_id), "subtitle.srt")
    subtitle_provider = config.app.get("subtitle_provider", "edge").strip().lower()
    logger.info(f"\n\n## generating subtitle, provider: {subtitle_provider}")

    subtitle_fallback = False
    if sub_maker is None:
        subtitle_fallback = True
    else:
        if subtitle_provider == "edge":
            voice.create_subtitle(
                text=video_script, sub_maker=sub_maker, subtitle_file=subtitle_path
            )
            if not os.path.exists(subtitle_path) or os.path.getsize(subtitle_path) == 0:
                subtitle_fallback = True
                logger.warning("subtitle file not found or empty, fallback to whisper")

    if subtitle_provider == "whisper" or subtitle_fallback:
        # Whisper fallback disabled for stability
        logger.warning("Whisper subtitle generation skipped to prevent system hang.")
        return ""
        # subtitle.create(audio_file=audio_file, subtitle_file=subtitle_path)
        # logger.info("\n\n## correcting subtitle")
        # subtitle.correct(subtitle_file=subtitle_path, video_script=video_script)

    subtitle_lines = subtitle.file_to_subtitles(subtitle_path)
    if not subtitle_lines:
        logger.warning(f"subtitle file is invalid: {subtitle_path}")
        if os.path.exists(subtitle_path) and os.path.getsize(subtitle_path) > 0:
             return subtitle_path
        return ""

    return subtitle_path


def get_video_materials(task_id, params, video_terms, audio_duration, script=None):
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
        logger.info(f"\n\n## downloading videos from {params.video_source}")
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
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        
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