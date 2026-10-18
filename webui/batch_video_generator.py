"""
諛곗튂 ?곸긽 ?앹꽦 ?⑥닔
?쇰컲 ?곸긽 ?앹꽦 濡쒖쭅??洹몃?濡??ъ슜
"""

import os
import glob
import concurrent.futures
from uuid import uuid4
from loguru import logger
import streamlit as st

from app.models.schema import VideoParams
from app.services import task as tm
from app.services import llm
from app.utils import utils
from app.config import config


def generate_single_video(
    title: str,
    video_type: str,
    language: str,
    duration: int,
    style: str,
    auto_upload: bool = False,
    task_id: str = None,
    script: str = None,
    terms: list = None,
    ui_params: VideoParams = None,
) -> dict:
    """?⑥씪 ?곸긽 ?앹꽦 (?쇰컲 ?곸긽 ?앹꽦 濡쒖쭅 洹몃?濡??ъ슜)"""

    # Task ID ?앹꽦 (?몃??먯꽌 ?쒓났?섏? ?딆? 寃쎌슦?먮쭔)
    if not task_id:
        task_id = str(uuid4())

    try:
        logger.info(f"Starting video generation for: {title} with task_id: {task_id}")

        # duration???곕씪 paragraph_number ?숈쟻 ?ㅼ젙
        if video_type == 'longform':
            paragraph_num = 4
        else:  # shorts
            # 60珥??쇱툩硫?3臾몃떒, 30珥??댄븯硫?2臾몃떒, 15珥??댄븯硫?1臾몃떒
            if duration >= 60:
                paragraph_num = 3
            elif duration >= 30:
                paragraph_num = 2
            else:
                paragraph_num = 1

        logger.info(f"?뱷 Duration: {duration}珥? Video type: {video_type}, Paragraph number: {paragraph_num}")

        # Start with the normal-video settings so batch generation uses the
        # same background, subtitle, BGM and rendering options.
        if ui_params is None:
            params_dict = {}
        elif hasattr(ui_params, "model_dump"):
            params_dict = ui_params.model_dump()
        elif hasattr(ui_params, "dict"):
            params_dict = ui_params.dict()
        elif isinstance(ui_params, dict):
            params_dict = dict(ui_params)
        else:
            raise TypeError("ui_params must be VideoParams, dict, or None")

        configured_source = str(config.app.get("video_source", "pexels")).lower()
        if configured_source not in {"pexels", "pixabay", "animation", "ai_image"}:
            configured_source = "pexels"

        # Values that belong to the current batch item must override the copied
        # UI settings. Korean/English voices intentionally remain independent.
        params_dict.update({
            'video_subject': title,  # ?꾩닔 ?꾨뱶
            'video_script': script or "",
            'video_terms': terms,
            'video_aspect': '9:16' if video_type == 'shorts' else '16:9',
            'video_source': configured_source,
            'custom_audio_file': None,
            'video_language': language,
            'voice_name': 'ko-KR-SunHiNeural' if language == 'ko-KR' else 'en-US-JennyNeural',
            'voice_rate': 1.12 if language == 'ko-KR' else 1.0,
            'paragraph_number': paragraph_num
        })

        # Local uploads only live in the current normal-video form and cannot
        # safely be reused for a multi-item batch after a Streamlit rerun.
        params_dict['video_materials'] = None

        params = VideoParams(**params_dict)

        # 2. API ??寃利?(?쇰컲 ?곸긽 ?앹꽦怨??숈씪)
        if params.video_source == "pexels":
            if not config.app.get("pexels_api_keys"):
                if config.app.get("pixabay_api_keys"):
                    params.video_source = "pixabay"
                else:
                    raise RuntimeError("A Pexels or Pixabay API key is required")
        elif params.video_source == "pixabay" and not config.app.get("pixabay_api_keys"):
            if config.app.get("pexels_api_keys"):
                params.video_source = "pexels"
            else:
                raise RuntimeError("A Pixabay or Pexels API key is required")

        # 3. ?쇰컲 ?곸긽 ?앹꽦怨??꾩쟾???숈씪??諛⑹떇?쇰줈 ?곸긽 ?앹꽦
        logger.info(f"Starting task execution for: {task_id}")
        logger.info(f"Video params: {params_dict}")

        # ?쇰컲 ?곸긽 ?앹꽦怨??숈씪??諛⑹떇?쇰줈 task.start ?몄텧
        try:
            if video_type == "longform":
                result = tm.generate_longform_video(task_id, params)
            else:
                logger.info("Calling task.start...")
                result = tm.start(task_id, params, stop_at="video")
                logger.info(f"task.start completed with result: {result}")

            logger.info(f"Task completed successfully: {result}")
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            # ?붾쾭源낆쓣 ?꾪빐 task ?붾젆?좊━ ?댁슜 ?뺤씤
            task_dir = utils.task_dir(task_id)
            all_files = glob.glob(os.path.join(task_dir, "*"))
            logger.error(f"Task directory contents: {all_files}")

            # ???먯꽭???ㅻ쪟 ?뺣낫 異쒕젰
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            raise Exception(f"?곸긽 ?앹꽦 以??ㅻ쪟 諛쒖깮: {str(e)}")

        # 4. ?앹꽦???뚯씪 李얘린 (?쇰컲 ?곸긽 ?앹꽦怨??숈씪)
        task_dir = utils.task_dir(task_id)
        logger.info(f"Looking for video files in: {task_dir}")

        video_patterns = [
            os.path.join(task_dir, f"longform_final_{task_id}.mp4"),  # 濡깊뤌
            os.path.join(task_dir, "final-*.mp4"),                    # ?쇱툩
            os.path.join(task_dir, "combined-*.mp4"),                 # 寃고빀???곸긽
            os.path.join(task_dir, "*.mp4")                           # 紐⑤뱺 mp4
        ]

        video_file = None
        for pattern in video_patterns:
            files = glob.glob(pattern)
            logger.info(f"Pattern {pattern}: found {len(files)} files")
            if files:
                video_file = files[0]
                logger.info(f"Selected video file: {video_file}")
                break

        if not video_file or not os.path.exists(video_file):
            # ?붾쾭源??뺣낫
            all_files = glob.glob(os.path.join(task_dir, "*"))
            logger.error(f"No video files found in {task_dir}")
            logger.error(f"Available files: {all_files}")
            raise Exception(f"?곸긽 ?뚯씪??李얠쓣 ???놁뒿?덈떎. Task ?붾젆?좊━: {task_dir}")

        logger.info(f"Found video file: {video_file}")

        logger.info(f"Video generation completed successfully for: {title}")

        # 諛섑솚 ?꾩뿉 ?꾩닔 ?뺣낫 寃利?諛??곸꽭 濡쒓퉭
        logger.info(f"Final validation - video_file: {video_file}")
        logger.info(f"File exists check: {os.path.exists(video_file) if video_file else False}")

        if not video_file:
            logger.error("No video_file path available")
            raise Exception("?곸긽 ?뚯씪 寃쎈줈媛 ?놁뒿?덈떎")

        if not os.path.exists(video_file):
            logger.error(f"Video file does not exist: {video_file}")
            # ?붾젆?좊━ ?댁슜 ?뺤씤
            task_dir = utils.task_dir(task_id)
            try:
                all_files = glob.glob(os.path.join(task_dir, "*"))
                logger.error(f"Task directory contents: {all_files}")
            except:
                pass
            raise Exception(f"?곸긽 ?뚯씪???앹꽦?섏? ?딆븯?듬땲?? {video_file}")

        # ?뚯씪 ?ш린 ?뺤씤
        file_size = os.path.getsize(video_file)
        logger.info(f"Video file size: {file_size} bytes")

        if file_size == 0:
            logger.error("Video file is empty")
            raise Exception(f"?곸긽 ?뚯씪??鍮꾩뼱?덉뒿?덈떎: {video_file}")

        # task.start 寃곌낵?먯꽌 ?ㅽ겕由쏀듃? ?ㅼ썙??異붿텧 (?쇰컲 ?곸긽怨??숈씪)
        final_script = result.get('script', script) if result else script
        final_terms = result.get('terms', terms) if result else terms

        # 諛곗튂 ?앹꽦?먯꽌??YouTube ?낅줈?쒕? ?섏? ?딄퀬 ?곸긽 ?앹꽦留??섑뻾
        # ?먮룞 ?낅줈?쒕뒗 Main.py?먯꽌 ?쇰컲 ?곸긽怨??숈씪??諛⑹떇?쇰줈 泥섎━
        logger.info("Batch generation completed - YouTube upload will be handled separately if enabled")

        result = {
            'file_path': video_file,
            'script': final_script or f"二쇱젣: {title}",  # ?ㅽ겕由쏀듃媛 ?놁쑝硫?湲곕낯媛??ъ슜
            'video_id': None,  # 諛곗튂?먯꽌???낅줈?쒗븯吏 ?딆쓬
            'type': video_type,
            'language': language,
            'upload_error': None,  # ?낅줈???쒕룄?섏? ?딆쓬
            'file_size': file_size,  # ?뚯씪 ?ш린 ?뺣낫 異붽?
            'auto_upload_requested': auto_upload,
        }

        logger.info(f"Returning successful result: {result}")
        return result

    except Exception as e:
        logger.error(f"Video generation failed for {title}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

        # YouTube ?낅줈???ㅻ쪟??寃쎌슦 ?곸긽 ?뚯씪???덈떎硫?遺遺??깃났?쇰줈 泥섎━
        task_dir = utils.task_dir(task_id)
        video_patterns = [
            os.path.join(task_dir, f"longform_final_{task_id}.mp4"),
            os.path.join(task_dir, "final-*.mp4"),
            os.path.join(task_dir, "combined-*.mp4"),
            os.path.join(task_dir, "*.mp4")
        ]

        video_file = None
        for pattern in video_patterns:
            files = glob.glob(pattern)
            if files:
                video_file = files[0]
                break

        if video_file and os.path.exists(video_file):
            logger.warning(f"Video file exists despite error, returning partial success: {video_file}")
            return {
                'file_path': video_file,
                'script': script if 'script' in locals() else title,
                'video_id': None,  # ?낅줈???ㅽ뙣
                'type': video_type,
                'language': language,
                'upload_error': f"?곸긽 ?앹꽦 以??ㅻ쪟 諛쒖깮: {str(e)}"
            }

        raise Exception(f"?곸긽 ?앹꽦 ?ㅽ뙣: {str(e)}")
