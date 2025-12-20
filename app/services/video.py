import glob
import itertools
import os
import random
import gc
import shutil
import subprocess
from typing import List
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from loguru import logger
from imageio_ffmpeg import get_ffmpeg_exe
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    afx,
    concatenate_videoclips,
)
from moviepy.video.tools.subtitles import SubtitlesClip
from PIL import ImageFont

from app.models import const
from app.models.schema import (
    MaterialInfo,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.services.utils import video_effects
from app.utils import utils

class SubClippedVideoClip:
    def __init__(self, file_path, start_time=None, end_time=None, width=None, height=None, duration=None):
        self.file_path = file_path
        self.start_time = start_time
        self.end_time = end_time
        self.width = width
        self.height = height
        if duration is None:
            self.duration = end_time - start_time
        else:
            self.duration = duration

    def __str__(self):
        return f"SubClippedVideoClip(file_path={self.file_path}, start_time={self.start_time}, end_time={self.end_time}, duration={self.duration}, width={self.width}, height={self.height})"


audio_codec = "aac"
video_codec = "libx264"
fps = 30

def parse_srt(file_path):
    subtitles = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
            
        # Index (skip)
        if line.isdigit():
            i += 1
            if i >= len(lines): break
            line = lines[i].strip()
            
        # Time
        if '-->' in line:
            times = line.split('-->')
            if len(times) == 2:
                start_str = times[0].strip()
                end_str = times[1].strip()
                
                def time_to_seconds(t_str):
                    t_str = t_str.replace(',', '.')
                    parts = t_str.split(':')
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                
                start = time_to_seconds(start_str)
                end = time_to_seconds(end_str)
                
                # Text
                text_lines = []
                i += 1
                while i < len(lines):
                    text_line = lines[i].strip()
                    if not text_line:
                        break
                    text_lines.append(text_line)
                    i += 1
                
                text = "\n".join(text_lines)
                subtitles.append(((start, end), text))
            else:
                i += 1
        else:
            i += 1
            
    return subtitles

def close_clip(clip):
    if clip is None:
        return
        
    try:
        # close main resources
        if hasattr(clip, 'reader') and clip.reader is not None:
            clip.reader.close()
            
        # close audio resources
        if hasattr(clip, 'audio') and clip.audio is not None:
            if hasattr(clip.audio, 'reader') and clip.audio.reader is not None:
                clip.audio.reader.close()
            del clip.audio
            
        # close mask resources
        if hasattr(clip, 'mask') and clip.mask is not None:
            if hasattr(clip.mask, 'reader') and clip.mask.reader is not None:
                clip.mask.reader.close()
            del clip.mask
            
        # handle child clips in composite clips
        if hasattr(clip, 'clips') and clip.clips:
            for child_clip in clip.clips:
                if child_clip is not clip:  # avoid possible circular references
                    close_clip(child_clip)
            
        # clear clip list
        if hasattr(clip, 'clips'):
            clip.clips = []
            
    except Exception as e:
        logger.error(f"failed to close clip: {str(e)}")
    
    del clip
    gc.collect()

def delete_files(files: List[str] | str):
    if isinstance(files, str):
        files = [files]
        
    for file in files:
        try:
            os.remove(file)
        except:
            pass

def get_bgm_file(bgm_type: str = "random", bgm_file: str = ""):
    if not bgm_type:
        return ""

    if bgm_file and os.path.exists(bgm_file):
        return bgm_file

    if bgm_type == "random":
        suffix = "*.mp3"
        song_dir = utils.song_dir()
        files = glob.glob(os.path.join(song_dir, suffix))
        return random.choice(files)

    return ""


def combine_videos(
    combined_video_path: str,
    video_paths: List[str],
    audio_file: str,
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_concat_mode: VideoConcatMode = VideoConcatMode.random,
    video_transition_mode: VideoTransitionMode = None,
    max_clip_duration: int = 5,
    threads: int = 2,
) -> str:
    audio_clip = AudioFileClip(audio_file)
    audio_duration = audio_clip.duration
    logger.info(f"audio duration: {audio_duration} seconds")
    aspect = VideoAspect(video_aspect)
    video_width, video_height = aspect.to_resolution()
    # Fallback: no materials provided → generate solid background video
    if not video_paths:
        logger.warning("no input video materials provided, generating solid background")
        bg = ColorClip(size=(video_width, video_height), color=(0, 0, 0)).with_duration(audio_duration)
        try:
            bg.write_videofile(
                combined_video_path,
                logger=None,
                fps=fps,
                codec=video_codec,
                preset="ultrafast",
                threads=threads,
                audio=False,
                ffmpeg_params=["-pix_fmt", "yuv420p"],
            )
        except Exception as e:
            logger.error(f"failed to write solid background video: {str(e)}")
            raise e
        return combined_video_path
    # Required duration of each clip
    req_dur = max_clip_duration
    logger.info(f"maximum clip duration: {req_dur} seconds")
    logger.info(f"video transition mode: {video_transition_mode}")
    output_dir = os.path.dirname(combined_video_path)

    processed_clips = []
    subclipped_items = []
    video_duration = 0
    for video_path in video_paths:
        clip = VideoFileClip(video_path)
        clip_duration = clip.duration
        clip_w, clip_h = clip.size
        close_clip(clip)
        
        start_time = 0

        while start_time < clip_duration:
            end_time = min(start_time + max_clip_duration, clip_duration)            
            if clip_duration - start_time >= max_clip_duration:
                subclipped_items.append(SubClippedVideoClip(file_path= video_path, start_time=start_time, end_time=end_time, width=clip_w, height=clip_h))
            start_time = end_time    
            if video_concat_mode.value == VideoConcatMode.sequential.value:
                break

    # random subclipped_items order
    if video_concat_mode.value == VideoConcatMode.random.value:
        random.shuffle(subclipped_items)
        
    logger.debug(f"total subclipped items: {len(subclipped_items)}")
    
    # Add downloaded clips over and over until the duration of the audio (max_duration) has been reached
    for i, subclipped_item in enumerate(subclipped_items):
        if video_duration > audio_duration:
            break
        
        logger.debug(f"processing clip {i+1}: {subclipped_item.width}x{subclipped_item.height}, current duration: {video_duration:.2f}s, remaining: {audio_duration - video_duration:.2f}s")
        
        try:
            clip = VideoFileClip(subclipped_item.file_path).subclipped(subclipped_item.start_time, subclipped_item.end_time)
            clip_duration = clip.duration
            # Not all videos are same size, so we need to resize them
            clip_w, clip_h = clip.size
            if clip_w != video_width or clip_h != video_height:
                clip_ratio = clip.w / clip.h
                video_ratio = video_width / video_height
                logger.debug(f"resizing clip, source: {clip_w}x{clip_h}, ratio: {clip_ratio:.2f}, target: {video_width}x{video_height}, ratio: {video_ratio:.2f}")
                
                if clip_ratio == video_ratio:
                    clip = clip.resized(new_size=(video_width, video_height))
                else:
                    # Logic for Portrait (Shorts) - Crop to Fill
                    if aspect == VideoAspect.portrait:
                        if clip_ratio > video_ratio:
                            # Source is wider than target (e.g. Landscape -> Portrait)
                            # Scale height to match target height
                            new_height = video_height
                            new_width = int(clip_w * (video_height / clip_h))
                            clip = clip.resized(new_size=(new_width, new_height))
                            # Crop center
                            x_center = new_width / 2
                            clip = clip.cropped(
                                x1=int(x_center - video_width / 2),
                                y1=0,
                                width=video_width,
                                height=video_height
                            )
                        else:
                            # Source is taller than target (e.g. Ultra-tall -> Portrait)
                            # Scale width to match target width
                            new_width = video_width
                            new_height = int(clip_h * (video_width / clip_w))
                            clip = clip.resized(new_size=(new_width, new_height))
                            # Crop center
                            y_center = new_height / 2
                            clip = clip.cropped(
                                x1=0,
                                y1=int(y_center - video_height / 2),
                                width=video_width,
                                height=video_height
                            )
                    else:
                        # Logic for Landscape/Square - Fit with Black Bars (Original)
                        if clip_ratio > video_ratio:
                            scale_factor = video_width / clip_w
                        else:
                            scale_factor = video_height / clip_h

                        new_width = int(clip_w * scale_factor)
                        new_height = int(clip_h * scale_factor)

                        background = ColorClip(size=(video_width, video_height), color=(0, 0, 0)).with_duration(clip_duration)
                        clip_resized = clip.resized(new_size=(new_width, new_height)).with_position("center")
                        clip = CompositeVideoClip([background, clip_resized])
                    
            shuffle_side = random.choice(["left", "right", "top", "bottom"])
            if video_transition_mode.value == VideoTransitionMode.none.value:
                clip = clip
            elif video_transition_mode.value == VideoTransitionMode.fade_in.value:
                clip = video_effects.fadein_transition(clip, 1)
            elif video_transition_mode.value == VideoTransitionMode.fade_out.value:
                clip = video_effects.fadeout_transition(clip, 1)
            elif video_transition_mode.value == VideoTransitionMode.slide_in.value:
                clip = video_effects.slidein_transition(clip, 1, shuffle_side)
            elif video_transition_mode.value == VideoTransitionMode.slide_out.value:
                clip = video_effects.slideout_transition(clip, 1, shuffle_side)
            elif video_transition_mode.value == VideoTransitionMode.shuffle.value:
                transition_funcs = [
                    lambda c: video_effects.fadein_transition(c, 1),
                    lambda c: video_effects.fadeout_transition(c, 1),
                    lambda c: video_effects.slidein_transition(c, 1, shuffle_side),
                    lambda c: video_effects.slideout_transition(c, 1, shuffle_side),
                ]
                shuffle_transition = random.choice(transition_funcs)
                clip = shuffle_transition(clip)

            if clip.duration > max_clip_duration:
                clip = clip.subclipped(0, max_clip_duration)
                
            # wirte clip to temp file
            clip_file = f"{output_dir}/temp-clip-{i+1}.mp4"
            # Optimization: Remove audio from temp clips to prevent hangs and improve speed
            clip.without_audio().write_videofile(
                clip_file,
                logger=None,
                fps=fps,
                codec=video_codec,
                preset="ultrafast",
                threads=2, # Reduced threads to avoid deadlocks during clip generation
                audio=False,
                ffmpeg_params=["-pix_fmt", "yuv420p"]
            )
            
            close_clip(clip)
        
            processed_clips.append(SubClippedVideoClip(file_path=clip_file, duration=clip.duration, width=clip_w, height=clip_h))
            video_duration += clip.duration
            
        except Exception as e:
            logger.error(f"failed to process clip: {str(e)}")
    
    # loop processed clips until the video duration matches or exceeds the audio duration.
    if video_duration < audio_duration:
        logger.warning(f"video duration ({video_duration:.2f}s) is shorter than audio duration ({audio_duration:.2f}s), looping clips to match audio length.")
        base_clips = processed_clips.copy()
        for clip in itertools.cycle(base_clips):
            if video_duration >= audio_duration:
                break
            processed_clips.append(clip)
            video_duration += clip.duration
        logger.info(f"video duration: {video_duration:.2f}s, audio duration: {audio_duration:.2f}s, looped {len(processed_clips)-len(base_clips)} clips")
     
    # merge video clips progressively, avoid loading all videos at once to avoid memory overflow
    logger.info("starting clip merging process")
    if not processed_clips:
        logger.warning("no clips available for merging")
        return combined_video_path
    
    # Check if we need to use MoviePy for transitions (if transition mode is active)
    # ffmpeg concat demuxer does not support overlapping transitions, so we use MoviePy if transitions are requested.
    # However, our current transition implementation (SlideIn/FadeIn) applies to the clip itself (entering/fading),
    # so simple concatenation might be sufficient if "over black" is acceptable.
    # But to ensure best compatibility with effects, we can use concatenate_videoclips.
    # Given the user reported "not applied", we switch to MoviePy composition for transition modes.
    
    use_moviepy_concat = False
    if video_transition_mode and video_transition_mode.value != VideoTransitionMode.none.value:
        use_moviepy_concat = True
        logger.info(f"Transition mode {video_transition_mode} active, using MoviePy concatenate_videoclips")

    if use_moviepy_concat:
        try:
            clips_to_concat = []
            for clip_data in processed_clips:
                if os.path.exists(clip_data.file_path) and os.path.getsize(clip_data.file_path) > 0:
                    # Load clip from temp file
                    # We must use VideoFileClip to load the encoded temp file with effects baked in?
                    # Wait, if we used write_videofile previously, the effects are in the file.
                    # So loading it is fine.
                    clip = VideoFileClip(clip_data.file_path)
                    clips_to_concat.append(clip)
            
            if not clips_to_concat:
                 logger.error("no valid clips to merge")
                 return combined_video_path

            # Use method='compose' to handle any alpha/transparency or effects better
            final_clip = concatenate_videoclips(clips_to_concat, method="compose")
            
            final_clip.write_videofile(
                combined_video_path,
                logger=None,
                fps=30, # Default fps
                codec="libx264",
                preset="ultrafast",
                threads=threads,
                audio_codec="aac"
            )
            
            # Close clips
            for clip in clips_to_concat:
                close_clip(clip)
            close_clip(final_clip)
            
            logger.info("MoviePy concatenation completed")
            
            # Verify output
            if not os.path.exists(combined_video_path) or os.path.getsize(combined_video_path) == 0:
                 raise Exception("MoviePy produced empty or missing file")
                 
        except Exception as e:
            logger.error(f"MoviePy concatenation failed: {e}")
            # Fallback to ffmpeg concat if MoviePy fails?
            logger.info("Falling back to ffmpeg concat")
            use_moviepy_concat = False

    if not use_moviepy_concat:
        try:
            # Create concat list file for ffmpeg
        concat_list_path = os.path.join(output_dir, "concat_list.txt")
        valid_clips_count = 0
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for clip_data in processed_clips:
                if os.path.exists(clip_data.file_path) and os.path.getsize(clip_data.file_path) > 0:
                    # Escape path for ffmpeg concat demuxer
                    path = clip_data.file_path.replace("\\", "/")
                    f.write(f"file '{path}'\n")
                    valid_clips_count += 1
                else:
                    logger.warning(f"skipping invalid clip: {clip_data.file_path}")

        if valid_clips_count == 0:
            logger.error("no valid clips to merge")
            return combined_video_path

        logger.info(f"concatenating {valid_clips_count} clips using ffmpeg: {concat_list_path}")
        
        ffmpeg_exe = get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            combined_video_path
        ]
        
        # Run ffmpeg
        logger.info(f"running ffmpeg command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode != 0:
            logger.error(f"ffmpeg concatenation failed: {result.stderr}")
            raise Exception(f"ffmpeg concatenation failed: {result.stderr}")
            
        logger.info("ffmpeg concatenation completed")
        
        # Verify output
        if not os.path.exists(combined_video_path) or os.path.getsize(combined_video_path) == 0:
             logger.error("ffmpeg produced empty or missing file")
             raise Exception("ffmpeg produced empty or missing file")

    except Exception as e:
        logger.error(f"failed to merge clips: {str(e)}")
        raise e

    # clean temp files
    clip_files = [clip.file_path for clip in processed_clips]
    delete_files(clip_files)
            
    return combined_video_path


def wrap_text(text, max_width, font="Arial", fontsize=60):
    # Create ImageFont
    font = ImageFont.truetype(font, fontsize)

    def get_text_size(inner_text):
        inner_text = inner_text.strip()
        left, top, right, bottom = font.getbbox(inner_text)
        return right - left, bottom - top

    width, height = get_text_size(text)
    if width <= max_width:
        return text, height

    processed = True

    _wrapped_lines_ = []
    words = text.split(" ")
    _txt_ = ""
    for word in words:
        _before = _txt_
        _txt_ += f"{word} "
        _width, _height = get_text_size(_txt_)
        if _width <= max_width:
            continue
        else:
            if _txt_.strip() == word.strip():
                processed = False
                break
            _wrapped_lines_.append(_before)
            _txt_ = f"{word} "
    _wrapped_lines_.append(_txt_)
    if processed:
        _wrapped_lines_ = [line.strip() for line in _wrapped_lines_]
        result = "\n".join(_wrapped_lines_).strip()
        height = len(_wrapped_lines_) * height
        return result, height

    _wrapped_lines_ = []
    chars = list(text)
    _txt_ = ""
    for word in chars:
        _txt_ += word
        _width, _height = get_text_size(_txt_)
        if _width <= max_width:
            continue
        else:
            _wrapped_lines_.append(_txt_)
            _txt_ = ""
    _wrapped_lines_.append(_txt_)
    result = "\n".join(_wrapped_lines_).strip()
    height = len(_wrapped_lines_) * height
    return result, height


def generate_video(
    video_path: str,
    audio_path: str,
    subtitle_path: str,
    output_file: str,
    params: VideoParams,
):
    aspect = VideoAspect(params.video_aspect)
    video_width, video_height = aspect.to_resolution()

    logger.info(f"generating video: {video_width} x {video_height}")
    logger.info(f"  ① video: {video_path}")
    logger.info(f"  ② audio: {audio_path}")
    logger.info(f"  ③ subtitle: {subtitle_path}")
    logger.info(f"  ④ output: {output_file}")

    # https://github.com/harry0703/MoneyPrinterTurbo/issues/217
    # PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'final-1.mp4.tempTEMP_MPY_wvf_snd.mp3'
    # write into the same directory as the output file
    output_dir = os.path.dirname(output_file)

    font_path = ""
    if params.subtitle_enabled or params.video_subject:
        # Force Malgun Gothic for Korean support to avoid squares
        # This overrides other settings to ensure Korean text works on Windows
        system_font_path = "C:/Windows/Fonts/malgun.ttf"
        
        # Linux/Docker font paths (Noto Sans CJK)
        linux_font_paths = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJKsc-Regular.otf"
        ]
        
        if os.path.exists(system_font_path):
            font_path = system_font_path
            logger.info(f"Forced Korean font: {font_path}")
        else:
            found_linux_font = False
            for path in linux_font_paths:
                if os.path.exists(path):
                    font_path = path
                    found_linux_font = True
                    logger.info(f"Forced Korean font (Linux): {font_path}")
                    break
            
            if not found_linux_font:
                if not params.font_name:
                    params.font_name = "STHeitiMedium.ttc"
                
                font_path = os.path.join(utils.font_dir(), params.font_name)
                if os.name == "nt":
                    font_path = font_path.replace("\\", "/")
        
        logger.info(f"  ⑤ font: {font_path}")

    def create_text_clip(subtitle_item):
        params.font_size = int(params.font_size)
        # Removed 1.3x multiplier for Shorts to prevent oversized text
        # if aspect == VideoAspect.portrait:
        #      params.font_size = int(params.font_size * 1.3) 

        params.stroke_width = max(3, int(params.stroke_width)) # Ensure visible outline
        params.stroke_color = params.stroke_color or "#000000" # Default to black outline
        phrase = subtitle_item[1]
        max_width = video_width * 0.9
        wrapped_txt, txt_height = wrap_text(
            phrase, max_width=max_width, font=font_path, fontsize=params.font_size
        )

        # Use PIL to create text image (avoiding ImageMagick dependency)
        font = ImageFont.truetype(font_path, params.font_size)
        dummy_img = Image.new('RGBA', (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        # Calculate bounding box
        bbox = draw.multiline_textbbox((0, 0), wrapped_txt, font=font, stroke_width=params.stroke_width, align='center', spacing=15)
        w = bbox[2] - bbox[0] + 40  # Add padding
        h = bbox[3] - bbox[1] + 40
        
        img = Image.new('RGBA', (int(w), int(h)), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.multiline_text((20, 20), wrapped_txt, font=font, fill=params.text_fore_color, stroke_width=params.stroke_width, stroke_fill=params.stroke_color, align='center', spacing=15)
        
        _clip = ImageClip(np.array(img))
        duration = subtitle_item[0][1] - subtitle_item[0][0]
        _clip = _clip.with_start(subtitle_item[0][0])
        _clip = _clip.with_end(subtitle_item[0][1])
        _clip = _clip.with_duration(duration)
        if params.subtitle_position == "bottom":
            # Adjust for Shorts style (higher up to avoid UI)
            if aspect == VideoAspect.portrait:
                 _clip = _clip.with_position(("center", video_height * 0.75))
            else:
                 _clip = _clip.with_position(("center", video_height * 0.92 - _clip.h))
        elif params.subtitle_position == "top":
            _clip = _clip.with_position(("center", video_height * 0.05))
        elif params.subtitle_position == "custom":
            # Ensure the subtitle is fully within the screen bounds
            margin = 10  # Additional margin, in pixels
            max_y = video_height - _clip.h - margin
            min_y = margin
            custom_y = (video_height - _clip.h) * (params.custom_position / 100)
            custom_y = max(
                min_y, min(custom_y, max_y)
            )  # Constrain the y value within the valid range
            _clip = _clip.with_position(("center", custom_y))
        else:  # center
            _clip = _clip.with_position(("center", "center"))
        return _clip

    bgm_file = get_bgm_file(bgm_type=params.bgm_type, bgm_file=params.bgm_file)

    # Separate audio and video rendering to avoid hangs and improve speed
    # OPTIMIZATION: Use pure ffmpeg for final rendering to avoid MoviePy hangs and improve speed (10x faster)
    logger.info("Starting FFmpeg direct rendering...")
    
    # Prepare ffmpeg command
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Prepare inputs
    inputs = []
    filters = []
    
    # Input 0: Video (concatenated clips)
    inputs.extend(["-i", video_path])
    
    # Input 1: Audio (TTS)
    inputs.extend(["-i", audio_path])
    
    # Audio mixing logic
    audio_map = "[1:a]" # Default to just TTS
    
    bgm_input_index = -1
    bgm_file = get_bgm_file(bgm_type=params.bgm_type, bgm_file=params.bgm_file)
    if bgm_file:
        inputs.extend(["-i", bgm_file])
        bgm_input_index = 2
        # Mix TTS (1.0) and BGM (0.2)
        # BGM loops indefinitely
        filters.append(f"[{bgm_input_index}:a]volume={params.bgm_volume},aloop=loop=-1:size=2e+09[bgm]")
        filters.append(f"[1:a]volume={params.voice_volume}[tts]")
        filters.append(f"[tts][bgm]amix=inputs=2:duration=first[a_out]")
        audio_map = "[a_out]"
    else:
         filters.append(f"[1:a]volume={params.voice_volume}[a_out]")
         audio_map = "[a_out]"

    # Video filters (Subtitles + Title)
    video_filter_chain = []
    
    # Common Font Settings
    import platform
    import shutil
    
    system = platform.system()
    font_name = "Malgun Gothic"
    # Default Windows font path
    source_font_path = "C:/Windows/Fonts/malgun.ttf"
    
    if system == "Linux":
        font_name = "Noto Sans CJK SC"
        source_font_path = "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc" # Example path, adjust as needed

    task_dir = os.path.dirname(output_file)
    
    # Copy font to task directory to avoid path issues
    local_font_name = "font.ttf"
    local_font_path = os.path.join(task_dir, local_font_name)
    
    try:
        if os.path.exists(source_font_path):
            if not os.path.exists(local_font_path):
                shutil.copy2(source_font_path, local_font_path)
            logger.info(f"Copied font to {local_font_path}")
        else:
            logger.warning(f"Font file not found at {source_font_path}, subtitles might fail or use default font")
    except Exception as e:
        logger.error(f"Failed to copy font: {e}")

    # 1. Subtitles
    if params.subtitle_enabled and subtitle_path and os.path.exists(subtitle_path):
        sub_filename = os.path.basename(subtitle_path)
        
        # Shorts vs Landscape styling
        font_size = 20
        margin_v = 20 # Slightly lower for landscape
        if aspect == VideoAspect.portrait:
            font_size = 16
            margin_v = 70 # Adjusted for portrait (lower than before)
        else:
            margin_v = 20

        # FFmpeg style string (ASS format)
        # Force Malgun Gothic and ensure it uses the local file by setting fontsdir
        style = f"Fontname={font_name},FontSize={font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV={margin_v},Bold=1"
        
        # Use relative path '.' for fontsdir since we run in task_dir
        # NOTE: fontsdir='.' tells ffmpeg to look for fonts in the current directory
        video_filter_chain.append(f"subtitles='{sub_filename}':fontsdir='.':charenc=UTF-8:force_style='{style}'")
        logger.info(f"Adding subtitles: {sub_filename} with style: {style}")

    # 2. Title Overlay
    title_overlay_filter = ""
    if params.video_subject:
        logger.info(f"  Adding title: {params.video_subject}")
        title_text = params.video_subject
        
        # Hardcode font size to 130
        title_font_size = 130
        
        # Use wrap_text to handle long titles
        wrapped_title, _ = wrap_text(title_text, max_width=video_width * 0.9, font=font_path, fontsize=title_font_size)
        
        # Create title image using PIL for better control over alignment and spacing
        try:
            # Create a transparent image matching video size
            title_img = Image.new('RGBA', (video_width, video_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(title_img)
            
            # Load font
            try:
                font = ImageFont.truetype(font_path, title_font_size)
            except Exception:
                # Fallback to default if font load fails
                font = ImageFont.load_default()
            
            # Draw text with stroke and shadow
            # Calculate position to center horizontally and place at 10% from top
            # We draw centered text, so x should be video_width / 2, and anchor='ma' (middle ascender/top)
            
            # Shadow/Stroke settings
            text_color = "#FFD700" # Gold
            stroke_color = "black"
            stroke_width = 3
            shadow_color = (0, 0, 0, 150) # Semi-transparent black
            shadow_offset = (3, 3)
            
            # Line spacing - reduce it to bring lines closer
            # spacing in PIL is pixels between lines. Negative values reduce the gap.
            # For 130px font, we want tight spacing.
            line_spacing = -20
            
            # Draw shadow first (by drawing text multiple times or offset)
            # PIL doesn't have built-in shadow for text, so we simulate it
            draw.multiline_text(
                (video_width / 2 + shadow_offset[0], video_height * 0.10 + shadow_offset[1]),
                wrapped_title,
                font=font,
                fill=shadow_color,
                align="center",
                anchor="ma",
                spacing=line_spacing
            )
            
            # Draw main text with stroke
            draw.multiline_text(
                (video_width / 2, video_height * 0.10),
                wrapped_title,
                font=font,
                fill=text_color,
                align="center",
                anchor="ma",
                spacing=line_spacing,
                stroke_width=stroke_width,
                stroke_fill=stroke_color
            )
            
            # Save to file
            title_img_path = os.path.join(task_dir, "title.png")
            title_img.save(title_img_path)
            logger.info(f"Generated title image at {title_img_path}")
            
            # Add overlay filter
            # Use 'movie' source to load the image
            # [v_in][title]overlay=0:0[v_out]
            # We assume the image is same size as video, so 0:0 is correct
            title_overlay_filter = f"movie='title.png'[title];[v_subbed][title]overlay=0:0"
            
        except Exception as e:
            logger.error(f"Failed to generate title image: {e}")
            # Fallback to old drawtext if PIL fails?
            # For now, just log error. The video will be generated without title if this fails.

    # Combine video filters
    # Logic:
    # 1. subtitles (if any) -> [v_subbed]
    # 2. title (if any) -> takes [v_subbed] (or [0:v] if no subtitles), outputs [v_out]
    
    current_stream = "0:v"
    
    if video_filter_chain:
        # If we have filters (subtitles), apply them
        filters.append(f"[{current_stream}]{','.join(video_filter_chain)}[v_subbed]")
        current_stream = "v_subbed"
    
    if title_overlay_filter:
        # If we have title, apply overlay
        # Note: title_overlay_filter string constructed above assumes [v_subbed] input
        # We need to adjust it to use {current_stream}
        title_overlay_filter = title_overlay_filter.replace("[v_subbed]", f"[{current_stream}]")
        filters.append(f"{title_overlay_filter}[v_out]")
        video_map = "[v_out]"
    else:
        if current_stream == "0:v":
            video_map = "0:v"
        else:
            video_map = f"[{current_stream}]"

    # Construct complete command
    cmd = [ffmpeg_exe, "-y"]
    cmd.extend(inputs)
    
    if filters:
        cmd.extend(["-filter_complex", ";".join(filters)])
    
    cmd.extend([
        "-map", video_map,
        "-map", audio_map,
        "-c:v", "libx264",
        "-preset", "ultrafast", # Max speed
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest", # Stop when shortest input ends (usually video)
        output_file
    ])
    
    logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
    
    # Run FFmpeg from the task directory
    # This ensures relative paths for subtitles and title.txt work correctly
    cwd = task_dir
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, cwd=cwd)
        logger.success("FFmpeg rendering completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg rendering failed: {e.stderr.decode('utf-8')}")
        raise e
        
    return
    
    # Legacy MoviePy code (commented out/unreachable)
    video_clip = video_clip.with_audio(audio_clip)



def preprocess_video(materials: List[MaterialInfo], clip_duration=4):
    for material in materials:
        if not material.url:
            continue

        ext = utils.parse_extension(material.url)
        try:
            clip = VideoFileClip(material.url)
        except Exception:
            clip = ImageClip(material.url)

        width = clip.size[0]
        height = clip.size[1]
        if width < 480 or height < 480:
            logger.warning(f"low resolution material: {width}x{height}, minimum 480x480 required")
            continue

        if ext in const.FILE_TYPE_IMAGES:
            logger.info(f"processing image: {material.url}")
            # Create an image clip and set its duration to 3 seconds
            clip = (
                ImageClip(material.url)
                .with_duration(clip_duration)
                .with_position("center")
            )
            # Apply a zoom effect using the resize method.
            # A lambda function is used to make the zoom effect dynamic over time.
            # The zoom effect starts from the original size and gradually scales up to 120%.
            # t represents the current time, and clip.duration is the total duration of the clip (3 seconds).
            # Note: 1 represents 100% size, so 1.2 represents 120% size.
            zoom_clip = clip.resized(
                lambda t: 1 + (clip_duration * 0.03) * (t / clip.duration)
            )

            # Optionally, create a composite video clip containing the zoomed clip.
            # This is useful when you want to add other elements to the video.
            final_clip = CompositeVideoClip([zoom_clip])

            # Output the video to a file.
            video_file = f"{material.url}.mp4"
            final_clip.write_videofile(video_file, fps=30, logger=None, codec="libx264", ffmpeg_params=["-pix_fmt", "yuv420p"])
            close_clip(clip)
            material.url = video_file
            logger.success(f"image processed: {video_file}")
    return materials
