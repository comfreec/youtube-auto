import os
import sys
import requests
# Add current directory to sys.path
sys.path.append(os.getcwd())

from app.services import material
from app.models.schema import VideoAspect

def download_file(url, filepath):
    response = requests.get(url, stream=True, verify=False)
    if response.status_code == 200:
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    return False

def main():
    print("Searching for rollercoaster video...")
    # Search for vertical video
    videos = material.search_videos_pexels("rollercoaster pov", minimum_duration=15, video_aspect=VideoAspect.portrait)
    
    if not videos:
        print("No videos found with 'rollercoaster pov'. Trying 'roller coaster'...")
        videos = material.search_videos_pexels("roller coaster", minimum_duration=15, video_aspect=VideoAspect.portrait)

    if videos:
        video_url = videos[0].url
        print(f"Found video: {video_url}")
        
        output_dir = "resource/materials"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "rollercoaster_timer_bg.mp4")
        
        print(f"Downloading to {output_path}...")
        if download_file(video_url, output_path):
            print("Download successful.")
        else:
            print("Download failed.")
    else:
        print("No videos found.")

if __name__ == "__main__":
    main()
