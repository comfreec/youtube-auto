import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from loguru import logger

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'  # 댓글 작성을 위한 권한
]

def get_authenticated_service(client_secrets_file, token_file='token.pickle'):
    creds = None

    # 쓰기 가능한 대체 토큰 파일 경로
    import tempfile
    alt_token_file = os.path.join(tempfile.gettempdir(), 'yt_token.pickle')

    # 프로그램 폴더의 채널 토큰을 먼저 확인합니다.
    if os.path.exists(token_file):
        try:
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
            logger.info("✅ YouTube 토큰 파일 로드 성공")
        except Exception:
            creds = None

    # 프로그램 폴더에 쓸 수 없었던 이전 버전의 임시 토큰도 호환합니다.
    if not creds or not creds.valid:
        if os.path.exists(alt_token_file):
            try:
                with open(alt_token_file, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("✅ 임시 YouTube 토큰 파일 로드 성공")
            except Exception:
                creds = None

    # 이전 버전에서 임시 폴더에만 저장된 유효한 토큰을 정상 위치로 복구합니다.
    if creds and creds.valid and not os.path.exists(token_file):
        try:
            token_parent = os.path.dirname(os.path.abspath(token_file))
            os.makedirs(token_parent, exist_ok=True)
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
            logger.info(f"✅ 임시 YouTube 토큰 복구: {token_file}")
        except Exception as e:
            logger.warning(f"⚠️ YouTube 토큰 복구 실패: {e}")
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("🔄 YouTube 토큰 만료 - 자동 갱신 중...")
            creds.refresh(Request())
            logger.info("✅ 토큰 갱신 성공")
        else:
            if not os.path.exists(client_secrets_file):
                raise FileNotFoundError(f"Client secrets file not found: {client_secrets_file}")
                
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 다음 실행에도 자동 업로드할 수 있도록 프로그램 폴더에 저장합니다.
        try:
            token_parent = os.path.dirname(os.path.abspath(token_file))
            os.makedirs(token_parent, exist_ok=True)
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
            logger.info(f"✅ YouTube 토큰 저장: {token_file}")
        except Exception as e:
            logger.warning(f"⚠️ 기본 토큰 저장 실패: {e}")

        # 설치 폴더 권한 문제에 대비해 임시 폴더에도 보조 저장합니다.
        try:
            with open(alt_token_file, 'wb') as token:
                pickle.dump(creds, token)
            logger.info(f"✅ 토큰 대체 파일에 저장: {alt_token_file}")
        except Exception as e:
            logger.warning(f"⚠️ 토큰 저장 실패: {e} - 이번 세션에서만 사용")

    return build('youtube', 'v3', credentials=creds)

def upload_video(youtube, file_path, title, description, category="22", keywords="", privacy_status="private", progress_callback=None, default_language=None, default_audio_language=None):
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
        
        snippet = {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category
        }
        if default_language:
            snippet['defaultLanguage'] = default_language
        if default_audio_language:
            snippet['defaultAudioLanguage'] = default_audio_language
            logger.info(f"🌐 Setting defaultAudioLanguage: {default_audio_language}")

        body = {
            'snippet': snippet,
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


def add_pinned_comment(youtube, video_id, comment_text):
    """
    영상에 고정 댓글 추가
    
    Args:
        youtube: The authenticated YouTube service object
        video_id: YouTube video ID
        comment_text: 댓글 내용
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # 댓글 추가
        comment_insert_response = youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_text
                        }
                    }
                }
            }
        ).execute()
        
        comment_id = comment_insert_response['id']
        logger.info(f"✅ 댓글 추가 성공: {comment_id}")
        
        # 댓글 고정 (moderationStatus를 published로 설정)
        # 참고: 댓글 고정은 YouTube Studio에서만 가능하며 API로는 직접 고정 불가
        # 대신 채널 소유자가 첫 댓글로 작성하면 자동으로 상단에 표시됨
        
        logger.info(f"💡 댓글이 추가되었습니다. YouTube Studio에서 수동으로 고정해주세요.")
        return True
        
    except Exception as e:
        logger.error(f"댓글 추가 실패: {e}")
        return False
