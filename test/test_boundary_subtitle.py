import re
import tempfile
import unittest
from pathlib import Path

from app.services.voice import SubMaker, create_boundary_subtitle


class BoundarySubtitleTest(unittest.TestCase):
    def test_korean_boundaries_keep_text_and_monotonic_timing(self):
        text = "우리 주변에서 흔히 볼 수 있는 솔잎은 건강에 도움을 줍니다. 섭취 방법도 중요합니다."
        spoken = ["우리", "주변에서", "흔히", "볼", "수", "있는", "솔잎은", "건강에", "도움을", "줍니다", "섭취", "방법도", "중요합니다"]
        maker = SubMaker()
        current = 100_000
        for token in spoken:
            maker.create_sub((current, 4_000_000), token)
            current += 4_500_000

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory, "subtitle.srt")
            self.assertTrue(create_boundary_subtitle(maker, text, str(output)))
            content = output.read_text(encoding="utf-8")

        times = re.findall(r"(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})", content)
        self.assertGreater(len(times), 1)
        self.assertNotIn("00:00:00,000 --> 00:00:00,000", content)
        self.assertIn("우리 주변에서", content)
        self.assertIn("섭취 방법도 중요합니다", content)

    def test_transformed_number_boundary_does_not_discard_exact_timing(self):
        text = "오늘 준비하세요. 10년 뒤에도 삶은 계속됩니다."
        spoken = ["오늘", "준비하세요", "십년", "뒤에도", "삶은", "계속됩니다"]
        maker = SubMaker()
        current = 100_000
        for token in spoken:
            maker.create_sub((current, 4_000_000), token)
            current += 4_500_000

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory, "subtitle.srt")
            self.assertTrue(create_boundary_subtitle(maker, text, str(output)))
            content = output.read_text(encoding="utf-8")

        self.assertIn("10년 뒤에도", content)
        self.assertNotIn("00:00:00,000 --> 00:00:00,000", content)


if __name__ == "__main__":
    unittest.main()
