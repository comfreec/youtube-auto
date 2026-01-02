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
        self.prog_callback = callback

    def bars_callback(self, bar, attr, value, old_value=None):
        if bar == 't' and self.prog_callback:
            total = self.bars[bar]['total']
            if total > 0:
                # Map 0-100% of write process to 90-100% of total task
                p = 90 + int((value / total) * 10)
                # Ensure we don't exceed 99% until fully done
                p = min(p, 99)
                self.prog_callback(p)

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

# Enhanced video encoding settings for better compatibility
video_encoding_params = [
    "-pix_fmt", "yuv420p",  # Ensure compatibility with all players
    "-movflags", "+faststart",  # Enable progressive download
    "-profile:v", "baseline",  # Use baseline profile for maximum compatibility
    "-level", "3.0",  # H.264 level for mobile compatibility
    "-r", "30",  # Force frame rate
    "-g", "60",  # GOP size (2 seconds at 30fps)
    "-keyint_min", "30",  # Minimum keyframe interval
    "-sc_threshold", "0",  # Disable scene change detection
]

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
                preset="medium",  # Changed from ultrafast for better quality
                threads=2,
                audio=False,
                ffmpeg_params=video_encoding_params
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
    
    # CHANGED: Default to ffmpeg for better stability, only use MoviePy if absolutely necessary
    use_moviepy_concat = False
    if video_transition_mode and video_transition_mode.value != VideoTransitionMode.none.value:
        # Try ffmpeg first, fallback to MoviePy only if needed
        logger.info(f"Transition mode {video_transition_mode} active, but trying ffmpeg first for stability")
        use_moviepy_concat = False  # Start with ffmpeg

    if use_moviepy_concat:
        try:
            clips_to_concat = []
            for clip_data in processed_clips:
                if os.path.exists(clip_data.file_path) and os.path.getsize(clip_data.file_path) > 0:
                    # Load clip from temp file
                    clip = VideoFileClip(clip_data.file_path)
                    clips_to_concat.append(clip)
            
            if not clips_to_concat:
                 logger.error("no valid clips to merge")
                 return combined_video_path

            logger.info(f"Concatenating {len(clips_to_concat)} clips with MoviePy")
            
            # Use method='compose' to handle any alpha/transparency or effects better
            # Add timeout and memory management
            try:
                final_clip = concatenate_videoclips(clips_to_concat, method="compose")
                
                # Setup logger if callback is provided
                write_logger = None
                if progress_callback:
                    write_logger = TaskProgressLogger(progress_callback)

                logger.info("Starting final video write...")
                final_clip.write_videofile(
                    combined_video_path,
                    logger=write_logger,
                    fps=fps,
                    codec=video_codec,
                    preset="medium",
                    threads=min(2, threads),  # Limit threads to prevent deadlock
                    audio_codec=audio_codec,
                    ffmpeg_params=video_encoding_params,
                    temp_audiofile=None,  # Let MoviePy handle temp files
                    remove_temp=True
                )
                
                logger.info("MoviePy video write completed")
                
            except Exception as write_error:
                logger.error(f"MoviePy write failed: {write_error}")
                raise write_error
            finally:
                # Always close clips to free memory
                for clip in clips_to_concat:
                    try:
                        close_clip(clip)
                    except:
                        pass
                try:
                    close_clip(final_clip)
                except:
                    pass
                # Force garbage collection
                import gc
                gc.collect()
            
            logger.info("MoviePy concatenation completed")
            
            # Verify output
            if not os.path.exists(combined_video_path) or os.path.getsize(combined_video_path) == 0:
                 raise Exception("MoviePy produced empty or missing file")
                 
        except Exception as e:
            logger.error(f"MoviePy concatenation failed: {e}")
            # Fallback to ffmpeg concat if MoviePy fails
            logger.info("Falling back to ffmpeg concat due to MoviePy failure")
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
                "-y",  # Overwrite output file
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c:v", video_codec,
                "-preset", "medium",
                "-crf", "23",
                "-c:a", audio_codec,
                "-b:a", "128k",
                "-r", str(fps),
                "-avoid_negative_ts", "make_zero",  # Handle timestamp issues
                "-fflags", "+genpts",  # Generate presentation timestamps
            ] + video_encoding_params + [combined_video_path]
            
            # Run ffmpeg with timeout
            logger.info(f"running ffmpeg command: {' '.join(cmd)}")
            
            import subprocess
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("FFmpeg process timed out")
            
            try:
                # Set timeout for ffmpeg process (10 minutes max)
                if hasattr(signal, 'SIGALRM'):  # Unix systems
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(600)  # 10 minutes timeout
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=600  # 10 minutes timeout
                )
                
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)  # Cancel alarm
                
            except (subprocess.TimeoutExpired, TimeoutError) as e:
                logger.error(f"ffmpeg process timed out: {e}")
                raise Exception("Video processing timed out - try reducing video length or complexity")
            except Exception as e:
                logger.error(f"ffmpeg process failed: {e}")
                raise e
            
            if result.returncode != 0:
                logger.error(f"ffmpeg concatenation failed: {result.stderr}")
                # Try to provide more helpful error message
                if "Invalid data found" in result.stderr:
                    raise Exception("Video file corruption detected - try regenerating with different settings")
                elif "No space left" in result.stderr:
                    raise Exception("Insufficient disk space for video processing")
                else:
                    raise Exception(f"Video processing failed: {result.stderr}")
                
            logger.info("ffmpeg concatenation completed successfully")
            
            # Verify output
            if not os.path.exists(combined_video_path) or os.path.getsize(combined_video_path) == 0:
                 logger.error("ffmpeg produced empty or missing file")
                 raise Exception("Video processing produced empty file - check available disk space")

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

    # Enhanced text wrapping for better readability
    processed = True
    _wrapped_lines_ = []
    words = text.split(" ")
    _txt_ = ""
    
    # Try to keep lines balanced and avoid very short last lines
    for word in words:
        _before = _txt_
        _txt_ += f"{word} "
        _width, _height = get_text_size(_txt_)
        
        if _width <= max_width:
            continue
        else:
            if _txt_.strip() == word.strip():
                # Single word is too long, need character-level wrapping
                processed = False
                break
            
            # Check if we should break here or try to balance lines
            remaining_words = words[words.index(word):]
            remaining_text = " ".join(remaining_words)
            remaining_width, _ = get_text_size(remaining_text)
            
            # If remaining text is much shorter than current line, try to balance
            if len(_wrapped_lines_) == 0 and remaining_width < max_width * 0.6:
                # Try to move one word to next line for better balance
                words_in_current = _before.strip().split()
                if len(words_in_current) > 2:  # Only if we have enough words
                    last_word = words_in_current[-1]
                    balanced_line = " ".join(words_in_current[:-1])
                    _wrapped_lines_.append(balanced_line)
                    _txt_ = f"{last_word} {word} "
                    continue
            
            _wrapped_lines_.append(_before.strip())
            _txt_ = f"{word} "
    
    if _txt_.strip():
        _wrapped_lines_.append(_txt_.strip())
    
    if processed:
        _wrapped_lines_ = [line.strip() for line in _wrapped_lines_ if line.strip()]
        result = "\n".join(_wrapped_lines_).strip()
        
        # Calculate total height with line spacing
        line_height = height
        total_height = len(_wrapped_lines_) * line_height + (len(_wrapped_lines_) - 1) * 15  # 15px spacing
        return result, total_height

    # Fallback to character-level wrapping for very long words
    _wrapped_lines_ = []
    chars = list(text)
    _txt_ = ""
    for char in chars:
        _txt_ += char
        _width, _height = get_text_size(_txt_)
        if _width <= max_width:
            continue
        else:
            _wrapped_lines_.append(_txt_[:-1])  # Don't include the character that made it too wide
            _txt_ = char
    
    if _txt_:
        _wrapped_lines_.append(_txt_)
    
    result = "\n".join(_wrapped_lines_).strip()
    line_height = height
    total_height = len(_wrapped_lines_) * line_height + (len(_wrapped_lines_) - 1) * 15
    return result, total_height

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
        
        # Dynamic subtitle positioning based on text height and language
        subtitle_height = _clip.h
        
        if params.subtitle_position == "bottom":
            # Adjust for Shorts style (higher up to avoid UI)
            if aspect == VideoAspect.portrait:
                # For portrait videos, place at 75% to avoid YouTube UI overlay
                # This is optimal for YouTube Shorts
                default_y = video_height * 0.75
                
                # If subtitle is too tall, adjust position but keep it reasonable
                if subtitle_height > video_height * 0.15:  # If subtitle is more than 15% of screen height
                    adjusted_y = max(video_height * 0.6, default_y - (subtitle_height - video_height * 0.1))
                else:
                    adjusted_y = default_y
                    
                _clip = _clip.with_position(("center", adjusted_y))
            else:
                _clip = _clip.with_position(("center", video_height * 0.92 - subtitle_height))
        elif params.subtitle_position == "top":
            # For top position, ensure it doesn't overlap with title
            if aspect == VideoAspect.portrait:
                # Start after title area (top 15% reserved for title)
                min_top_y = video_height * 0.15
                _clip = _clip.with_position(("center", min_top_y))
            else:
                _clip = _clip.with_position(("center", video_height * 0.05))
        elif params.subtitle_position == "custom":
            # Ensure the subtitle is fully within the screen bounds
            margin = 10  # Additional margin, in pixels
            max_y = video_height - subtitle_height - margin
            min_y = margin
            
            # For portrait, respect title area
            if aspect == VideoAspect.portrait:
                min_y = max(min_y, video_height * 0.15)  # Don't overlap with title
                
            custom_y = (video_height - subtitle_height) * (params.custom_position / 100)
            custom_y = max(min_y, min(custom_y, max_y))
            _clip = _clip.with_position(("center", custom_y))
        else:  # center
            # For center position in portrait, avoid title area
            if aspect == VideoAspect.portrait:
                # Center in the middle area (between title and bottom UI)
                available_height = video_height * 0.6  # 60% of screen (15% top + 25% bottom reserved)
                center_y = video_height * 0.15 + (available_height - subtitle_height) / 2
                _clip = _clip.with_position(("center", center_y))
            else:
                _clip = _clip.with_position(("center", "center"))
        return _clip

    bgm_file = get_bgm_file(bgm_type=params.bgm_type, bgm_file=params.bgm_file)

    # Separate audio and video rendering to avoid hangs and improve speed
    # OPTIMIZATION: Use pure ffmpeg for final rendering to avoid MoviePy hangs and improve speed (10x faster)
    
    try:
        # Load the combined video
        # We need to close these clips properly
        video_clip = VideoFileClip(video_path)
        
        # --- TITLE OVERLAY (Image Generation for FFmpeg) ---
        title_image_path = ""
        if params.video_subject:
            try:
                # Use project font
                font_path_title = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resource", "fonts", "NanumGothic-Bold.ttf")
                
                # Wrap text manually
                font_size = 96
                font = ImageFont.truetype(font_path_title, font_size)
                max_width = video_width * 0.85 # 15% margin
                
                wrapped_text, text_h = wrap_text(params.video_subject, max_width, font=font_path_title, fontsize=font_size)
                
                # Draw Text Image
                dummy_img = Image.new('RGBA', (1, 1))
                draw = ImageDraw.Draw(dummy_img)
                # increased spacing for better readability
                bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, stroke_width=5, align='center', spacing=20)
                w = bbox[2] - bbox[0] + 40
                h = bbox[3] - bbox[1] + 40
                
                img = Image.new('RGBA', (int(w), int(h)), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.multiline_text((20, 20), wrapped_text, font=font, fill="yellow", stroke_width=5, stroke_fill="black", align='center', spacing=20)
                
                # Save to temp file
                title_image_path = output_file.replace(".mp4", "_title.png")
                img.save(title_image_path)
                logger.info(f"Title overlay image created: {title_image_path}")
                
            except Exception as e:
                logger.error(f"Failed to create title overlay image: {e}")

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
        
        logger.info("merging video, audio, and subtitles...")
        ffmpeg_exe = get_ffmpeg_exe()
        
        cmd = [ffmpeg_exe, "-y"]
        inputs = ["-i", video_path, "-i", temp_audio_file]
        
        filter_complex = []
        current_v = "0:v"
        
        # Add Title Overlay
        if title_image_path and os.path.exists(title_image_path):
            inputs.extend(["-i", title_image_path])
            # Overlay title image on video
            # (W-w)/2:160 centers horizontally and puts it 160px from top (moved down by 40px)
            filter_complex.append(f"[{current_v}][2:v]overlay=(W-w)/2:160[v_titled]")
            current_v = "v_titled"
            
        # Add Subtitles
        has_subtitles = params.subtitle_enabled and os.path.exists(subtitle_path)
        if has_subtitles:
            sub_path_escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")
            margin_v = 40 if aspect != VideoAspect.portrait else 120
            style = f"Fontname=Malgun Gothic,FontSize=16,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=1,Outline=1,Shadow=0,MarginV={margin_v},Alignment=2"
            # Use current_v as input for subtitles
            filter_complex.append(f"[{current_v}]subtitles='{sub_path_escaped}':force_style='{style}'[v_out]")
            current_v = "v_out"
            
        cmd.extend(inputs)
        
        if filter_complex:
            cmd.extend(["-filter_complex", ";".join(filter_complex)])
            cmd.extend(["-map", f"[{current_v}]"])
            cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23"])
        else:
            cmd.extend(["-map", "0:v"])
            cmd.extend(["-c:v", "copy"])
            
        cmd.extend([
            "-map", "1:a",
            "-c:a", "copy",
            "-shortest", 
            output_file
        ])
        
        logger.info(f"Running merge command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Cleanup
        if os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)
        if title_image_path and os.path.exists(title_image_path):
            os.remove(title_image_path)
        
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


def generate_timer_video(duration_seconds: int, output_file: str, font_path: str = None, fontsize: int = 250, bg_video_path: str = None, bg_music_path: str = None, fast_mode: bool = False, timer_style: str = "minimal", progress_callback=None):
    logger.info(f"Generating timer video (MoviePy): {duration_seconds}s")
    logger.info(f"Timer style received: '{timer_style}'")
    logger.info(f"Background video path: {bg_video_path}")
    logger.info(f"Fast mode: {fast_mode}")
    
    try:
        target_w, target_h = (720, 1280) if fast_mode else (1080, 1920)
        
        # Background setup
        if bg_video_path and os.path.exists(bg_video_path):
            try:
                logger.info(f"Loading background video: {bg_video_path}")
                # Check if it's an image
                ext = os.path.splitext(bg_video_path)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
                    bg_clip = ImageClip(bg_video_path)
                else:
                    bg_clip = VideoFileClip(bg_video_path)
                    # Test if we can read frames safely
                    try:
                        test_frame = bg_clip.get_frame(0)
                        logger.info(f"Background video loaded successfully, duration: {bg_clip.duration}s")
                    except Exception as frame_error:
                        logger.error(f"Cannot read frames from video: {frame_error}")
                        bg_clip.close()
                        raise frame_error
                    
                ratio = bg_clip.w / bg_clip.h
                target_ratio = target_w / target_h
                if ratio > target_ratio:
                    bg_clip = bg_clip.resized(height=target_h)
                    bg_clip = bg_clip.cropped(x1=(bg_clip.w - target_w)/2, width=target_w)
                else:
                    bg_clip = bg_clip.resized(width=target_w)
                    bg_clip = bg_clip.cropped(y1=(bg_clip.h - target_h)/2, height=target_h)
                bg_clip = bg_clip.with_duration(duration_seconds)
                
                # Loop video if shorter (only for video clips) - FIXED LOOP ISSUE
                if ext not in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
                    if hasattr(bg_clip, 'duration') and bg_clip.duration < duration_seconds:
                        logger.info(f"Background video duration ({bg_clip.duration}s) shorter than timer ({duration_seconds}s), creating seamless loop")
                        # Calculate how many loops we need
                        loops_needed = int(duration_seconds / bg_clip.duration) + 1
                        logger.info(f"Creating {loops_needed} loops of background video")
                        
                        # Create multiple copies and concatenate them
                        clips_to_loop = []
                        for i in range(loops_needed):
                            clips_to_loop.append(bg_clip.copy())
                        
                        # Concatenate all clips
                        from moviepy import concatenate_videoclips
                        looped_clip = concatenate_videoclips(clips_to_loop)
                        
                        # Trim to exact duration needed
                        bg_clip = looped_clip.subclipped(0, duration_seconds)
                        
                        # Clean up temporary clips
                        for clip in clips_to_loop:
                            try:
                                close_clip(clip)
                            except:
                                pass
                        try:
                            close_clip(looped_clip)
                        except:
                            pass
                    else:
                        # Just set duration if video is long enough
                        bg_clip = bg_clip.with_duration(duration_seconds)
                        
            except Exception as e:
                logger.error(f"Failed to load BG video/image: {e}")
                logger.info("Creating gradient background as fallback instead of black")
                # Create a gradient background instead of pure black using PIL
                from PIL import Image as PILImage
                img = PILImage.new('RGB', (target_w, target_h))
                pixels = img.load()
                for y in range(target_h):
                    # Create a vertical gradient from dark blue to dark purple
                    ratio = y / target_h
                    r = int(20 + ratio * 30)  # Red: 20-50
                    g = int(10 + ratio * 20)  # Green: 10-30  
                    b = int(40 + ratio * 60)  # Blue: 40-100
                    for x in range(target_w):
                        pixels[x, y] = (r, g, b)
                
                # Convert PIL image to numpy array for MoviePy
                gradient = np.array(img)
                bg_clip = ImageClip(gradient, duration=duration_seconds)
        else:
            logger.info(f"No background video specified, creating {timer_style} style background")
            # Create background based on timer style using PIL
            from PIL import Image as PILImage
            
            if "자연" in timer_style or "nature" in timer_style.lower():
                # Nature-inspired gradient (green to blue)
                img = PILImage.new('RGB', (target_w, target_h))
                pixels = img.load()
                for y in range(target_h):
                    ratio = y / target_h
                    r = int(10 + ratio * 20)   # Red: 10-30
                    g = int(60 + ratio * 40)   # Green: 60-100
                    b = int(30 + ratio * 50)   # Blue: 30-80
                    for x in range(target_w):
                        pixels[x, y] = (r, g, b)
            elif "추상" in timer_style or "abstract" in timer_style.lower():
                # Abstract gradient (purple to pink)
                img = PILImage.new('RGB', (target_w, target_h))
                pixels = img.load()
                for y in range(target_h):
                    ratio = y / target_h
                    r = int(80 + ratio * 60)   # Red: 80-140
                    g = int(20 + ratio * 40)   # Green: 20-60
                    b = int(100 + ratio * 50)  # Blue: 100-150
                    for x in range(target_w):
                        pixels[x, y] = (min(255, r), min(255, g), min(255, b))
            else:
                # Minimal style (dark gradient)
                img = PILImage.new('RGB', (target_w, target_h))
                pixels = img.load()
                for y in range(target_h):
                    ratio = y / target_h
                    r = int(20 + ratio * 30)   # Red: 20-50
                    g = int(10 + ratio * 20)   # Green: 10-30  
                    b = int(40 + ratio * 60)   # Blue: 40-100
                    for x in range(target_w):
                        pixels[x, y] = (r, g, b)
            
            # Convert PIL image to numpy array for MoviePy
            gradient = np.array(img)
            bg_clip = ImageClip(gradient, duration=duration_seconds)

        # Font setup with fallback
        if not font_path or not os.path.exists(font_path):
            # Try multiple font paths
            possible_fonts = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resource", "fonts", "NanumGothic-Bold.ttf"),
                "C:/Windows/Fonts/malgun.ttf",  # Windows Korean font
                "C:/Windows/Fonts/arial.ttf",   # Windows fallback
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux
            ]
            
            font_path = None
            for path in possible_fonts:
                if os.path.exists(path):
                    font_path = path
                    break
            
            if not font_path:
                raise Exception("No suitable font found for timer video")
        
        try:
            font = ImageFont.truetype(font_path, fontsize)
        except Exception as e:
            logger.error(f"Failed to load font {font_path}: {e}")
            # Use default font as last resort
            font = ImageFont.load_default()

        # Use make_frame with caching to optimize rendering
        memo = {}
        
        def make_frame(t):
            # Calculate remaining time more precisely
            # We want to show the countdown from duration_seconds down to 0
            remaining_time = duration_seconds - t
            
            # Round down to get the current second to display
            remaining = max(0, int(remaining_time))
            
            # Use remaining as cache key
            if remaining in memo:
                return memo[remaining]
                
            mins = remaining // 60
            s = remaining % 60
            text = f"{mins}:{s:02d}"
            
            img = Image.new('RGBA', (target_w, target_h), (0,0,0,0))
            draw = ImageDraw.Draw(img)
            
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            except:
                # Fallback for older PIL versions
                text_w, text_h = draw.textsize(text, font=font)
            
            x = (target_w - text_w) // 2
            y = (target_h - text_h) // 2
            padding = 40
            
            # Style-based text appearance
            if "자연" in timer_style or "nature" in timer_style.lower():
                # Nature style: Green-tinted background with white text
                box_coords = (x - padding, y - padding, x + text_w + padding, y + text_h + padding)
                draw.rectangle(box_coords, fill=(20, 60, 30, 180))  # Semi-transparent green
                text_color = "white"
                stroke_color = "darkgreen"
            elif "추상" in timer_style or "abstract" in timer_style.lower():
                # Abstract style: Colorful background with white text
                box_coords = (x - padding, y - padding, x + text_w + padding, y + text_h + padding)
                draw.rectangle(box_coords, fill=(80, 20, 100, 180))  # Semi-transparent purple
                text_color = "white"
                stroke_color = "purple"
            else:
                # Minimal style: Simple dark background
                box_coords = (x - padding, y - padding, x + text_w + padding, y + text_h + padding)
                draw.rectangle(box_coords, fill=(0, 0, 0, 128))  # Semi-transparent black
                text_color = "white"
                stroke_color = "black"
            
            try:
                draw.text((x, y), text, font=font, fill=text_color, stroke_width=5, stroke_fill=stroke_color)
            except:
                # Fallback without stroke
                draw.text((x, y), text, font=font, fill=text_color)
            
            # Clear cache occasionally to prevent memory leak
            if len(memo) > 10:
                memo.clear()
                
            frame = np.array(img)
            memo[remaining] = frame
            
            # Update progress directly from frame generation
            # Removed progress_callback to avoid NoSessionContext error in Streamlit
                    
            return frame

        timer_overlay = VideoClip(make_frame, duration=duration_seconds)
        final_clip = CompositeVideoClip([bg_clip, timer_overlay])

        # Audio setup
        if bg_music_path and os.path.exists(bg_music_path):
            try:
                logger.info(f"Loading background music: {bg_music_path}")
                audio = AudioFileClip(bg_music_path)
                logger.info(f"Audio duration: {audio.duration}s, needed: {duration_seconds}s")
                
                if audio.duration < duration_seconds:
                    logger.info("Looping audio to match video duration")
                    audio = audio.with_effects([afx.AudioLoop(duration=duration_seconds)])
                else:
                    logger.info("Trimming audio to match video duration")
                    audio = audio.subclipped(0, duration_seconds)
                
                # Set audio volume (reduce to 30% for background music)
                audio = audio.with_volume_scaled(0.3)
                final_clip = final_clip.with_audio(audio)
                logger.info("Background music successfully added to timer video")
                
            except Exception as e:
                logger.error(f"Failed to load or attach audio: {e}")
                logger.warning("Continuing without background music")
        else:
            if bg_music_path:
                logger.warning(f"Background music file not found: {bg_music_path}")
            else:
                logger.info("No background music specified")
                
        # Write video file
        final_clip.write_videofile(
            output_file,
            fps=fps,
            codec=video_codec,
            audio_codec=audio_codec,
            threads=1,
            preset="medium",
            logger=None,
            ffmpeg_params=video_encoding_params
        )

        # Cleanup
        try:
            close_clip(bg_clip)
            close_clip(timer_overlay)
            close_clip(final_clip)
        except:
            pass
        
        # Final progress update - removed to avoid NoSessionContext error
            
        logger.info(f"Timer video generated successfully: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Timer video generation failed: {e}")
        raise e


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
