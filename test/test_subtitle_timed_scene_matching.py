import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.script_segment_matcher import ScriptSegmentMatcher


class SubtitleTimedSceneMatchingTest(unittest.TestCase):
    def test_uses_subtitle_boundaries_and_preserves_total_duration(self):
        srt = """1
00:00:00,000 --> 00:00:03,100
아침에는 물을 마십니다.

2
00:00:03,100 --> 00:00:07,000
수분은 몸의 균형을 돕습니다.

3
00:00:07,000 --> 00:00:08,200
그리고 움직이세요.

4
00:00:08,200 --> 00:00:13,500
가벼운 걷기는 건강에 도움이 됩니다.

5
00:00:13,500 --> 00:00:20,000
저녁에는 충분히 쉬는 것이 좋습니다.

"""
        with tempfile.TemporaryDirectory() as directory:
            subtitle_path = Path(directory) / "subtitle.srt"
            subtitle_path.write_text(srt, encoding="utf-8")
            matcher = ScriptSegmentMatcher()
            with patch.object(matcher, "generate_segment_keywords", return_value=["health"]):
                result = matcher.match_segments_to_subtitle_timing(
                    script="아침에는 물을 마십니다. 수분은 몸의 균형을 돕습니다. 그리고 움직이세요. 가벼운 걷기는 건강에 도움이 됩니다. 저녁에는 충분히 쉬는 것이 좋습니다.",
                    subtitle_path=str(subtitle_path),
                    video_duration=20.0,
                    target_segment_count=5,
                    minimum_duration=3.0,
                )

        self.assertEqual(result[0]["start_time"], 0.0)
        self.assertEqual(result[-1]["end_time"], 20.0)
        self.assertAlmostEqual(sum(item["duration"] for item in result), 20.0, places=3)
        self.assertTrue(all(item["duration"] >= 3.0 for item in result))
        self.assertIn("움직이세요", " ".join(item["segment"] for item in result))


if __name__ == "__main__":
    unittest.main()
