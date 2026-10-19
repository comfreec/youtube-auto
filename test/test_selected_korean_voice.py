import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services import task


class SelectedKoreanVoiceTest(unittest.TestCase):
    def test_life_advice_automatically_uses_injoon(self):
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
                audio_file, duration, _ = task.generate_audio(
                    "voice-test", params, "후회 없는 인생을 위한 교훈과 조언"
                )

        self.assertEqual(captured["voice_name"], "ko-KR-InJoonNeural")
        self.assertEqual(captured["voice_rate"], 1.03)
        self.assertEqual(duration, 12)
        self.assertTrue(audio_file.endswith("audio.mp3"))

    def test_health_information_uses_sunhi(self):
        self.assertEqual(
            task.select_korean_voice("건강을 지키는 음식과 운동 방법"),
            "ko-KR-SunHiNeural",
        )

    def test_general_explanation_uses_hyunsu(self):
        self.assertEqual(
            task.select_korean_voice("새로운 기술의 작동 원리를 설명합니다"),
            "ko-KR-HyunsuMultilingualNeural",
        )


if __name__ == "__main__":
    unittest.main()
