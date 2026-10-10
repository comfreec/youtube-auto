import tempfile
import unittest
from pathlib import Path

from app.controllers.v1.video import _safe_path, _safe_upload_name
from app.models.exception import HttpException


class VideoPathSecurityTest(unittest.TestCase):
    def test_safe_path_accepts_child_path(self):
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory, "task", "video.mp4").resolve()
            self.assertEqual(_safe_path(directory, "task/video.mp4"), expected)

    def test_safe_path_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(HttpException):
                _safe_path(directory, "../outside.txt")

    def test_upload_name_rejects_directory_components(self):
        with self.assertRaises(HttpException):
            _safe_upload_name("../track.mp3", ("mp3",))

    def test_upload_extension_is_exact_and_case_insensitive(self):
        self.assertEqual(_safe_upload_name("track.MP3", ("mp3",)), "track.MP3")
        with self.assertRaises(HttpException):
            _safe_upload_name("track.notmp3", ("mp3",))


if __name__ == "__main__":
    unittest.main()
