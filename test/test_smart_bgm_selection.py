import os
import unittest

from app.services import video


class SmartBgmSelectionTest(unittest.TestCase):
    def test_life_advice_uses_reflection_mood(self):
        self.assertEqual(
            video.classify_bgm_mood("후회 없는 인생을 위한 세 가지 교훈과 조언"),
            "reflection",
        )

    def test_health_content_uses_health_mood(self):
        self.assertEqual(
            video.classify_bgm_mood("건강을 지키는 음식과 운동 방법"),
            "health",
        )

    def test_smart_selection_only_uses_matching_pool(self):
        files = [
            os.path.join("songs", "Resolution Or Reflection - Artist.mp3"),
            os.path.join("songs", "Pulsar - Artist.mp3"),
        ]
        selected = video._select_smart_bgm(files, "인생 교훈과 삶의 지혜")
        self.assertIn("Resolution Or Reflection", selected)

    def test_smart_selection_is_stable_for_same_script(self):
        files = [os.path.join("songs", f"{name}.mp3") for name in ("A Stroll", "Time")]
        first = video._select_smart_bgm(files, "인생 조언")
        second = video._select_smart_bgm(files, "인생 조언")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
