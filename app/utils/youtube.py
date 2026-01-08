import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from loguru import logger

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service(client_secrets_file, token_file='token.pickle'):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secrets_file):
                raise FileNotFoundError(f"Client secrets file not found: {client_secrets_file}")
                
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)

def upload_video(youtube, file_path, title, description, category="22", keywords="", privacy_status="private", progress_callback=None):
    """
    Uploads a video to YouTube.
    
    Args:
        youtube: The authenticated YouTube service object.
        file_path: Path to the video file.
        title: Video title.
        description: Video description.
        category: Video category ID (22 is People & Blogs, 28 is Science & Technology, etc.).
        keywords: Comma-separated list of tags.
        privacy_status: "public", "private", or "unlisted".
        progress_callback: Optional callback function(progress_percent)
    
    Returns:
        The uploaded video ID if successful, None otherwise.
    """
    try:
        tags = [tag.strip() for tag in keywords.split(',')] if keywords else []
        
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False, 
            }
        }

        # Call the API's videos.insert method to create and upload the video.
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=MediaFileUpload(file_path, chunksize=1024*1024, resumable=True)
        )

        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Uploaded {progress}%")
                if progress_callback:
                    progress_callback(progress)

        video_id = response['id']
        logger.success(f"Video uploaded successfully! Video ID: {video_id}")
        
        # 업로드 후 검증 (30초 대기 후 확인)
        logger.info("업로드 검증 중... (30초 대기)")
        import time
        time.sleep(30)
        
        try:
            # YouTube에서 실제 영상 확인
            video_info = youtube.videos().list(part="snippet,status", id=video_id).execute()
            if video_info['items']:
                video_data = video_info['items'][0]
                upload_status = video_data['status']['uploadStatus']
                logger.info(f"✅ 업로드 검증 성공 - 상태: {upload_status}")
                return video_id
            else:
                logger.warning("⚠️ 업로드 지연 처리 중 - 5분 후 재확인 예정")
                # 5분 후 재확인
                time.sleep(300)  # 5분 대기
                video_info = youtube.videos().list(part="snippet,status", id=video_id).execute()
                if video_info['items']:
                    logger.info("✅ 지연된 업로드 완료 확인")
                    return video_id
                else:
                    logger.error("❌ 업로드 실패 - 수동 업로드 권장")
                    return None
        except Exception as verify_error:
            logger.warning(f"⚠️ 업로드 검증 실패 (하지만 업로드는 성공): {verify_error}")
            return video_id  # 검증 실패해도 업로드는 성공으로 처리
        
        return video_id

    except Exception as e:
        logger.error(f"An error occurred during video upload: {e}")
        return None
