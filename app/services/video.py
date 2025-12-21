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
    VideoClip,
    afx,
    concatenate_videoclips,
)
from moviepy import vfx
from moviepy.video.tools.subtitles import SubtitlesClip
from PIL import ImageFont
from proglog import ProgressBarLogger

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

class TaskProgressLogger(ProgressBarLogger):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def bars_callback(self, bar, attr, value, old_value=None):
        if bar == 't' and self.callback:
            total = self.bars[bar]['total']
            if total > 0:
                # Map 0-100% of write process to 90-100% of total task
                p = 90 + int((value / total) * 10)
                # Ensure we don't exceed 99% until fully done
                p = min(p, 99)
                self.callback(p)

    def log(self, message):
        pass

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
    progress_callback=None,
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
    total_subclips = len(subclipped_items)
    for i, subclipped_item in enumerate(subclipped_items):
        if video_duration > audio_duration:
            break
        
        # Report progress (0-80% of this phase)
        if progress_callback:
            # We estimate we might use all clips, or loop. 
            # Let's just map the processed count against total available clips for now, 
            # or better, against target audio duration if possible. 
            # But simpler: map i to total_subclips.
            current_progress = int((i / total_subclips) * 90) # Reserve 10% for concatenation
            progress_callback(current_progress)

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
    if progress_callback:
        progress_callback(90) # Clips prepared, starting merge

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
            
            # Setup logger if callback is provided
            write_logger = None
            if progress_callback:
                write_logger = TaskProgressLogger(progress_callback)

            final_clip.write_videofile(
                combined_video_path,
                logger=write_logger,
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
    
    try:
        # Load the combined video
        # We need to close these clips properly
        video_clip = VideoFileClip(video_path)
        
        # Audio setup
        final_audio = AudioFileClip(audio_path)
        bgm_clip = None
        
        if bgm_file:
            bgm_clip = AudioFileClip(bgm_file)
            if bgm_clip.duration < final_audio.duration:
                # Use effects instead of afx.audio_loop for v2
                bgm_clip = bgm_clip.with_effects([afx.AudioLoop(duration=final_audio.duration)])
            else:
                bgm_clip = bgm_clip.subclipped(0, final_audio.duration)
                
            bgm_clip = bgm_clip.with_volume_scaled(params.bgm_volume)
            final_audio = CompositeAudioClip([final_audio, bgm_clip])
        
        # 1. Export Audio First (Fastest)
        logger.info("writing final video (audio track)...")
        temp_audio_file = output_file.replace(".mp4", "_temp_audio.m4a")
        logger.info(f"Exporting audio to {temp_audio_file}")
        try:
            final_audio.write_audiofile(temp_audio_file, fps=44100, codec="aac", logger=None)
            logger.info("Audio export successful")
        except Exception as e:
            logger.error(f"Audio export failed: {e}")
            raise e
        
        # 2. Merge Audio and Video (and Subtitles) using FFmpeg
        # Optimization: Skip MoviePy video re-encoding. Use the source video_path directly.
        logger.info("merging video, audio, and subtitles...")
        ffmpeg_exe = get_ffmpeg_exe()
        
        cmd = [
            ffmpeg_exe, "-y",
            "-i", video_path,
            "-i", temp_audio_file
        ]
        
        # Check for subtitles
        has_subtitles = False
        if params.subtitle_enabled and os.path.exists(subtitle_path):
            has_subtitles = True
            logger.info(f"Burning subtitles from {subtitle_path}")
            
            # Escape path for FFmpeg filter
            # Windows: Replace \ with / and escape : as \:
            sub_path_escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")
            
            # Subtitle Style
            # Use Malgun Gothic for Korean support
            # Fontsize 16 is good for 1080p width roughly, adjust if needed
            style = "Fontname=Malgun Gothic,FontSize=16,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=1,Outline=1,Shadow=0,MarginV=25,Alignment=2"
            
            cmd.extend(["-vf", f"subtitles='{sub_path_escaped}':force_style='{style}',drawtext=fontfile='C\\:/Windows/Fonts/malgunbd.ttf':text='{params.video_subject}':fontcolor=yellow:fontsize=120:x=(w-text_w)/2:y=100:borderw=5:bordercolor=black"])
            
            # Re-encode is required for burning subtitles
            cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23"])
        else:
            # Check if we need to draw text even without subtitles
            if params.video_subject:
                 logger.info(f"Drawing title: {params.video_subject}")
                 cmd.extend(["-vf", f"drawtext=fontfile='C\\:/Windows/Fonts/malgunbd.ttf':text='{params.video_subject}':fontcolor=yellow:fontsize=120:x=(w-text_w)/2:y=100:borderw=5:bordercolor=black"])
                 cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23"])
            else:
                 # Copy stream if no subtitles and no title
                 cmd.extend(["-c:v", "copy"])
            
        cmd.extend([
            "-c:a", "copy", # Audio copy is fine (already encoded in step 1)
            "-map", "0:v",
            "-map", "1:a",
            "-shortest", 
            output_file
        ])
        
        logger.info(f"Running merge command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Cleanup
        if os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)
        
        # Close resources
        try:
            video_clip.close()
            final_audio.close()
            if bgm_clip:
                bgm_clip.close()
            # final_clip is alias to video_clip now, so no need to close separately
        except Exception:
            pass
            
    except Exception as e:
        logger.error(f"failed to generate final video: {str(e)}")
        raise e

    return output_file


def generate_timer_video(duration_seconds: int, output_file: str, font_path: str = None, fontsize: int = 150, bg_video_path: str = None, bg_music_path: str = None):
    """
    Generates a video with a countdown timer centered on a background using FFmpeg directly for performance.
    """
    # Default font path if not provided
    if not font_path:
        # Try common Windows fonts
        candidates = [
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/seguiemj.ttf"
        ]
        for f in candidates:
            if os.path.exists(f):
                font_path = f
                break
        if not font_path:
             font_path = "arial.ttf" # Fallback hope system finds it

    # Video dimensions (Portrait for Shorts: 1080x1920)
    width, height = 1080, 1920
    
    logger.info(f"Generating timer video (FFmpeg): {duration_seconds}s, output: {output_file}")
    
    ffmpeg_exe = get_ffmpeg_exe()
    
    # Escape font path for FFmpeg filter
    # Windows: Replace \ with / and escape : as \:
    # Example: C:/Windows/Fonts/arial.ttf -> C\:/Windows/Fonts/arial.ttf
    font_path_filter = font_path.replace("\\", "/").replace(":", "\\:")
    
    cmd = [ffmpeg_exe, "-y"]
    
    # Input 0: Background Video (or black color)
    if bg_video_path and os.path.exists(bg_video_path):
        logger.info(f"Using background video: {bg_video_path}")
        cmd.extend(["-stream_loop", "-1", "-i", bg_video_path])
    else:
        logger.info("Using black background")
        cmd.extend(["-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:d={duration_seconds}"])
        
    # Input 1: Background Music (if exists)
    has_audio = False
    if bg_music_path and os.path.exists(bg_music_path):
        logger.info(f"Using background music: {bg_music_path}")
        cmd.extend(["-stream_loop", "-1", "-i", bg_music_path])
        has_audio = True
    
    # Filter Complex
    filter_chains = []
    
    # [0:v] -> [bg]
    # Scale/Crop to 1080x1920
    filter_chains.append(f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1[bg]")
    
    # Text
    # Time expression: %{eif:(duration-t)/60:d}:%{eif:(duration-t)%60:d:2}
    # Use textfile to avoid escaping hell
    text_expression = f"%{{eif:({duration_seconds}-t)/60:d}}:%{{eif:({duration_seconds}-t)%60:d:2}}"
    
    # Use a safe filename in the same directory
    temp_text_file = os.path.join(os.path.dirname(output_file), f"timer_text_{os.path.basename(output_file)}.txt")
    with open(temp_text_file, "w", encoding="utf-8") as f:
        f.write(text_expression)
        
    # Escape path for FFmpeg
    text_file_filter = temp_text_file.replace("\\", "/").replace(":", "\\:")
    
    # Draw text
    drawtext = (
        f"drawtext=fontfile='{font_path_filter}':"
        f"textfile='{text_file_filter}':"
        f"fontcolor=white:fontsize={fontsize}:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"borderw=4:bordercolor=black"
    )
    
    filter_chains.append(f"[bg]{drawtext}[outv]")
    
    cmd.extend(["-filter_complex", ";".join(filter_chains)])
    
    # Mapping
    cmd.extend(["-map", "[outv]"])
    if has_audio:
        cmd.extend(["-map", "1:a"])
        
    # Duration and Output
    cmd.extend(["-t", str(duration_seconds)])
    cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"])
    
    # Check if NVIDIA GPU is available (optional optimization, risky if not present)
    # cmd.extend(["-c:v", "h264_nvenc"]) 
    
    cmd.extend([output_file])
    
    logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
    
    try:
        # Run FFmpeg
        # Capture output to log if needed, but for now just check=True
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.success(f"Video generated successfully: {output_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e.stderr.decode() if e.stderr else str(e)}")
        raise e
    finally:
        if os.path.exists(temp_text_file):
            os.remove(temp_text_file)
        
    return output_file


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
