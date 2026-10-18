import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services import task


class SelectedKoreanVoiceTest(unittest.TestCase):
    def test_injoon_is_not_replaced_with_sunhi(self):
        params = SimpleNamespace(
            custom_audio_file=None,
            voice_name="ko-KR-InJoonNeural",
            video_language="ko-KR",
            voice_rate=1.03,
        )
        captured = {}

        def fake_tts(**kwargs):
            captured.update(kwargs)
            Path(kwargs["voice_file"]).write_bytes(b"test")
            return object()

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(task.utils, "task_dir", return_value=directory),
                patch.object(task.voice, "tts", side_effect=fake_tts),
                patch.object(task.voice, "get_audio_duration", return_value=12.0),
            ):
                audio_file, duration, _ = task.generate_audio("voice-test", params, "테스트 문장")

        self.assertEqual(captured["voice_name"], "ko-KR-InJoonNeural")
        self.assertEqual(captured["voice_rate"], 1.03)
        self.assertEqual(duration, 12)
        self.assertTrue(audio_file.endswith("audio.mp3"))


if __name__ == "__main__":
    unittest.main()
