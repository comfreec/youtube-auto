import os
import random
import concurrent.futures
from typing import List
from urllib.parse import urlencode

import requests
from loguru import logger
from moviepy.video.io.VideoFileClip import VideoFileClip

from app.config import config
from app.models.schema import MaterialInfo, VideoAspect, VideoConcatMode
from app.utils import utils

requested_count = 0


def get_api_key(cfg_key: str):
    api_keys = config.app.get(cfg_key)
    if not api_keys:
        raise ValueError(
            f"\n\n##### {cfg_key} is not set #####\n\nPlease set it in the config.toml file: {config.config_file}\n\n"
            f"{utils.to_json(config.app)}"
        )

    # if only one key is provided, return it
    if isinstance(api_keys, str):
        return api_keys

    global requested_count
    requested_count += 1
    return api_keys[requested_count % len(api_keys)]


def get_youtube_audio_library_music():
    """
    Get curated list of YouTube Audio Library style free music
    These are royalty-free music that can be used safely
    """
    # Curated list of royalty-free music from various sources
    free_music_library = {
        "ambient": [
            {
                "name": "Peaceful Ambient",
                "url": "https://www.bensound.com/bensound-music/bensound-relaxing.mp3",
                "duration": 180
            },
            {
                "name": "Calm Meditation", 
                "url": "https://www.bensound.com/bensound-music/bensound-slowmotion.mp3",
                "duration": 210
            }
        ],
        "nature": [
            {
                "name": "Forest Sounds",
                "url": "https://www.bensound.com/bensound-music/bensound-sunny.mp3", 
                "duration": 195
            },
            {
                "name": "Ocean Waves",
                "url": "https://www.bensound.com/bensound-music/bensound-memories.mp3",
                "duration": 225
            }
        ],
        "electronic": [
            {
                "name": "Digital Ambient",
                "url": "https://www.bensound.com/bensound-music/bensound-scifi.mp3",
                "duration": 198
            },
            {
                "name": "Synth Pad",
                "url": "https://www.bensound.com/bensound-music/bensound-futuristic.mp3", 
                "duration": 180
            }
        ],
        "minimal": [
            {
                "name": "Simple Piano",
                "url": "https://www.bensound.com/bensound-music/bensound-pianomoment.mp3",
                "duration": 165
            },
            {
                "name": "Minimal Loop",
                "url": "https://www.bensound.com/bensound-music/bensound-tenderness.mp3",
                "duration": 155
            }
        ]
    }
    
    return free_music_library


def search_free_music(search_term: str = "ambient", minimum_duration: int = 60) -> List[dict]:
    """
    Search for free music from curated library
    """
    try:
        music_library = get_youtube_audio_library_music()
        
        # Find matching category
        category = "ambient"  # default
        if "nature" in search_term.lower() or "forest" in search_term.lower():
            category = "nature"
        elif "electronic" in search_term.lower() or "synth" in search_term.lower():
            category = "electronic" 
        elif "minimal" in search_term.lower():
            category = "minimal"
        
        music_tracks = music_library.get(category, music_library["ambient"])
        
        # Filter by minimum duration
        filtered_tracks = []
        for track in music_tracks:
            if track.get("duration", 0) >= minimum_duration:
                filtered_tracks.append({
                    "provider": "free_library",
                    "url": track["url"],
                    "duration": track["duration"],
                    "name": track["name"],
                    "id": f"free_{category}_{len(filtered_tracks)}"
                })
        
        logger.info(f"Found {len(filtered_tracks)} free music tracks for '{search_term}'")
        return filtered_tracks
        
    except Exception as e:
        logger.error(f"Failed to get free music: {e}")
        return []


def save_music(music_url: str, save_dir: str = "") -> str:
    """
    Download and save music file
    """
    if not save_dir:
        save_dir = utils.storage_dir("cache_music")

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    url_without_query = music_url.split("?")[0]
    url_hash = utils.md5(url_without_query)
    music_id = f"music-{url_hash}"
    music_path = f"{save_dir}/{music_id}.mp3"

    # if music already exists, return the path
    if os.path.exists(music_path) and os.path.getsize(music_path) > 0:
        logger.info(f"music already exists: {music_path}")
        return music_path

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    try:
        # Download the music file
        with open(music_path, "wb") as f:
            response = requests.get(
                music_url,
                headers=headers,
                proxies=config.proxy,
                verify=False,
                timeout=(20, 60),
            )
            response.raise_for_status()
            f.write(response.content)

        if os.path.exists(music_path) and os.path.getsize(music_path) > 0:
            logger.info(f"music downloaded successfully: {music_path}")
            return music_path
        else:
            logger.error(f"downloaded music file is empty: {music_path}")
            return ""
    except Exception as e:
        logger.error(f"failed to download music: {str(e)}")
        try:
            if os.path.exists(music_path):
                os.remove(music_path)
        except Exception:
            pass
        return ""


def get_free_music_urls():
    """
    Get free music URLs from various sources
    Returns list of direct download URLs for royalty-free music
    """
    # Curated list of royalty-free music URLs (Creative Commons / Public Domain)
    # Using more reliable sources
    free_music_urls = {
        "ambient": [
            "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav",
            "https://www.soundjay.com/misc/sounds/wind-chimes-1.wav",
            "https://www.soundjay.com/misc/sounds/meditation-bell-1.wav",
        ],
        "nature": [
            "https://www.soundjay.com/nature/sounds/rain-01.wav",
            "https://www.soundjay.com/nature/sounds/wind-1.wav",
            "https://www.soundjay.com/nature/sounds/birds-1.wav",
        ],
        "electronic": [
            "https://www.soundjay.com/misc/sounds/beep-07a.wav",
            "https://www.soundjay.com/misc/sounds/beep-10.wav",
        ],
        "minimal": [
            "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav",
            "https://www.soundjay.com/misc/sounds/meditation-bell-1.wav",
        ]
    }
    
    return free_music_urls


def download_free_music(search_term: str = "ambient", save_dir: str = "") -> str:
    """
    Download free music from curated URLs
    """
    try:
        if not save_dir:
            save_dir = utils.storage_dir("cache_music")
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # Get music URLs
        music_urls = get_free_music_urls()
        
        # Find matching category
        category = "ambient"  # default
        if "nature" in search_term.lower() or "forest" in search_term.lower():
            category = "nature"
        elif "electronic" in search_term.lower() or "synth" in search_term.lower():
            category = "electronic"
        elif "minimal" in search_term.lower():
            category = "minimal"
        
        urls = music_urls.get(category, music_urls["ambient"])
        if not urls:
            return ""
        
        # Select random URL
        selected_url = random.choice(urls)
        
        # Create filename
        url_hash = utils.md5(selected_url)
        music_filename = f"free_music_{category}_{url_hash}.mp3"
        music_path = os.path.join(save_dir, music_filename)
        
        # Check if already downloaded
        if os.path.exists(music_path) and os.path.getsize(music_path) > 0:
            logger.info(f"Music already exists: {music_path}")
            return music_path
        
        # Download the music
        logger.info(f"Downloading free music from: {selected_url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(selected_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        with open(music_path, "wb") as f:
            f.write(response.content)
        
        if os.path.exists(music_path) and os.path.getsize(music_path) > 0:
            logger.info(f"Free music downloaded successfully: {music_path}")
            return music_path
        else:
            logger.error(f"Downloaded music file is empty: {music_path}")
            return ""
            
    except Exception as e:
        logger.error(f"Failed to download free music: {e}")
        return ""


def search_videos_pexels(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
) -> List[MaterialInfo]:
    aspect = VideoAspect(video_aspect)
    video_orientation = aspect.name
    video_width, video_height = aspect.to_resolution()
    api_key = get_api_key("pexels_api_keys")
    headers = {
        "Authorization": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    }
    # Build URL
    params = {"query": search_term, "per_page": 20, "orientation": video_orientation}
    query_url = f"https://api.pexels.com/videos/search?{urlencode(params)}"
    logger.info(f"searching videos: {query_url}, with proxies: {config.proxy}")

    try:
        r = requests.get(
            query_url,
            headers=headers,
            proxies=config.proxy,
            verify=False,
            timeout=(10, 20),
        )
        response = r.json()
        video_items = []
        if "videos" not in response:
            logger.error(f"search videos failed: {response}")
            return video_items
        videos = response["videos"]
        # loop through each video in the result
        for v in videos:
            duration = v["duration"]
            # check if video has desired minimum duration
            if duration < minimum_duration:
                continue
            video_files = v["video_files"]
            # loop through each url to determine the best quality
            for video in video_files:
                w = int(video["width"])
                h = int(video["height"])
                if w == video_width and h == video_height:
                    item = MaterialInfo()
                    item.provider = "pexels"
                    item.url = video["link"]
                    item.duration = duration
                    video_items.append(item)
                    break
        return video_items
    except Exception as e:
        logger.error(f"search videos failed: {str(e)}")

    return []


def search_videos_pixabay(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
) -> List[MaterialInfo]:
    aspect = VideoAspect(video_aspect)

    video_width, video_height = aspect.to_resolution()

    api_key = get_api_key("pixabay_api_keys")
    # Build URL
    params = {
        "q": search_term,
        "video_type": "all",  # Accepted values: "all", "film", "animation"
        "per_page": 50,
        "key": api_key,
    }
    query_url = f"https://pixabay.com/api/videos/?{urlencode(params)}"
    logger.info(f"searching videos: {query_url}, with proxies: {config.proxy}")

    try:
        r = requests.get(
            query_url, proxies=config.proxy, verify=False, timeout=(10, 20)
        )
        response = r.json()
        video_items = []
        if "hits" not in response:
            logger.error(f"search videos failed: {response}")
            return video_items
        videos = response["hits"]
        # loop through each video in the result
        for v in videos:
            duration = v["duration"]
            # check if video has desired minimum duration
            if duration < minimum_duration:
                continue
            video_files = v["videos"]
            # loop through each url to determine the best quality
            for video_type in video_files:
                video = video_files[video_type]
                w = int(video["width"])
                # h = int(video["height"])
                if w >= video_width:
                    item = MaterialInfo()
                    item.provider = "pixabay"
                    item.url = video["url"]
                    item.duration = duration
                    video_items.append(item)
                    break
        return video_items
    except Exception as e:
        logger.error(f"search videos failed: {str(e)}")

    return []


def save_video(video_url: str, save_dir: str = "") -> str:
    if not save_dir:
        save_dir = utils.storage_dir("cache_videos")

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    url_without_query = video_url.split("?")[0]
    url_hash = utils.md5(url_without_query)
    video_id = f"vid-{url_hash}"
    video_path = f"{save_dir}/{video_id}.mp4"

    # if video already exists, return the path
    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        logger.info(f"video already exists: {video_path}")
        return video_path

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    # if video does not exist, download it
    with open(video_path, "wb") as f:
        f.write(
            requests.get(
                video_url,
                headers=headers,
                proxies=config.proxy,
                verify=False,
                timeout=(20, 60),
            ).content
        )

    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        try:
            clip = VideoFileClip(video_path)
            duration = clip.duration
            fps = clip.fps
            clip.close()
            if duration > 0 and fps > 0:
                return video_path
        except Exception as e:
            try:
                os.remove(video_path)
            except Exception:
                pass
            logger.warning(f"invalid video file: {video_path} => {str(e)}")
    return ""


def download_videos(
    task_id: str,
    search_terms: List[str],
    source: str = "pexels",
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_contact_mode: VideoConcatMode = VideoConcatMode.random,
    audio_duration: float = 0.0,
    max_clip_duration: int = 5,
) -> List[str]:
    valid_video_items = []
    valid_video_urls = []
    found_duration = 0.0
    search_videos = search_videos_pexels
    if source == "pixabay":
        search_videos = search_videos_pixabay

    for search_term in search_terms:
        video_items = search_videos(
            search_term=search_term,
            minimum_duration=max_clip_duration,
            video_aspect=video_aspect,
        )
        logger.info(f"found {len(video_items)} videos for '{search_term}'")

        if not video_items:
            logger.warning(f"No videos found for '{search_term}', trying translation to English...")
            try:
                translated_term = llm.translate_to_english(search_term)
                if translated_term and "Error" not in translated_term and translated_term != search_term:
                    logger.info(f"Translated '{search_term}' to '{translated_term}'")
                    video_items = search_videos(
                        search_term=translated_term,
                        minimum_duration=max_clip_duration,
                        video_aspect=video_aspect,
                    )
                    logger.info(f"found {len(video_items)} videos for '{translated_term}'")
                else:
                    logger.warning(f"Translation returned invalid result: {translated_term}")
            except Exception as e:
                logger.error(f"Translation failed: {str(e)}")

        for item in video_items:
            if item.url not in valid_video_urls:
                valid_video_items.append(item)
                valid_video_urls.append(item.url)
                found_duration += item.duration

    logger.info(
        f"found total videos: {len(valid_video_items)}, required duration: {audio_duration} seconds, found duration: {found_duration} seconds"
    )
    video_paths = []

    material_directory = config.app.get("material_directory", "").strip()
    if material_directory == "task":
        material_directory = utils.task_dir(task_id)
    elif material_directory and not os.path.isdir(material_directory):
        material_directory = ""

    if video_contact_mode.value == VideoConcatMode.random.value:
        random.shuffle(valid_video_items)

    total_duration = 0.0
    video_paths = []

    # Helper function for parallel download
    def download_task(item):
        try:
            logger.info(f"downloading video: {item.url}")
            path = save_video(video_url=item.url, save_dir=material_directory)
            if path:
                return item, path
        except Exception as e:
            logger.error(f"failed to download video: {utils.to_json(item)} => {str(e)}")
        return item, None

    # Parallel download for the first batch
    # Estimate needed count: audio_duration / 3s (conservative min duration) + buffer
    # Or just try to download a generous amount in parallel to ensure speed
    estimated_needed = int(audio_duration / 3) + 3
    candidates = valid_video_items[:estimated_needed]
    max_workers = 5

    logger.info(f"downloading {len(candidates)} videos in parallel (max_workers={max_workers})...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        if video_contact_mode.value == VideoConcatMode.sequential.value:
            # Preserve order for sequential mode
            futures = [executor.submit(download_task, item) for item in candidates]
            for future in futures:
                item, path = future.result()
                if path:
                    logger.info(f"video saved: {path}")
                    video_paths.append(path)
                    seconds = min(max_clip_duration, item.duration)
                    total_duration += seconds
                    if total_duration > audio_duration:
                        break
        else:
            # Random mode: order within candidates doesn't strictly matter as they are already shuffled
            # process as completed for speed
            future_to_item = {executor.submit(download_task, item): item for item in candidates}
            for future in concurrent.futures.as_completed(future_to_item):
                item, path = future.result()
                if path:
                    logger.info(f"video saved: {path}")
                    video_paths.append(path)
                    seconds = min(max_clip_duration, item.duration)
                    total_duration += seconds
                    if total_duration > audio_duration:
                        break

    # If still not enough duration, fallback to sequential for the rest
    if total_duration <= audio_duration and len(candidates) < len(valid_video_items):
        logger.info(f"still need more duration ({total_duration}/{audio_duration}), downloading more sequentially...")
        remaining_items = valid_video_items[len(candidates):]
        for item in remaining_items:
            try:
                logger.info(f"downloading video: {item.url}")
                saved_video_path = save_video(
                    video_url=item.url, save_dir=material_directory
                )
                if saved_video_path:
                    logger.info(f"video saved: {saved_video_path}")
                    video_paths.append(saved_video_path)
                    seconds = min(max_clip_duration, item.duration)
                    total_duration += seconds
                    if total_duration > audio_duration:
                        logger.info(
                            f"total duration of downloaded videos: {total_duration} seconds, skip downloading more"
                        )
                        break
            except Exception as e:
                logger.error(f"failed to download video: {utils.to_json(item)} => {str(e)}")

    logger.success(f"downloaded {len(video_paths)} videos")
    return video_paths


if __name__ == "__main__":
    download_videos(
        "test123", ["Money Exchange Medium"], audio_duration=100, source="pixabay"
    )
