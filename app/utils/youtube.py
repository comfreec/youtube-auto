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

def upload_video(youtube, file_path, title, description, category="22", keywords="", privacy_status="private"):
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
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
        )

        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                logger.info(f"Uploaded {int(status.progress() * 100)}%")

        logger.success(f"Video uploaded successfully! Video ID: {response['id']}")
        return response['id']

    except Exception as e:
        logger.error(f"An error occurred during video upload: {e}")
        return None
