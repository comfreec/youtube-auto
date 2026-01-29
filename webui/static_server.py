"""
정적 파일 서빙을 위한 간단한 서버
PWA 매니페스트와 아이콘 파일들을 서빙
"""
import os
import mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

class PWAStaticHandler(SimpleHTTPRequestHandler):
    """PWA 정적 파일 핸들러"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="webui/static", **kwargs)
    
    def end_headers(self):
        # CORS 헤더 추가
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

def start_static_server(port=8502):
    """정적 파일 서버 시작"""
    try:
        server = HTTPServer(('0.0.0.0', port), PWAStaticHandler)
        print(f"📁 정적 파일 서버 시작: http://localhost:{port}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ 정적 파일 서버 오류: {e}")

def start_static_server_thread():
    """백그라운드에서 정적 파일 서버 시작"""
    thread = threading.Thread(target=start_static_server, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    start_static_server()