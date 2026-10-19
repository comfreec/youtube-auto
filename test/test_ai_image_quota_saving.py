import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from app.services import ai_image_background


class AIImageQuotaSavingTest(unittest.TestCase):
    def test_text_rejection_retries_at_most_twice_by_default(self):
        candidate = Image.new("RGB", (16, 16), "white")
        with (
            patch.object(ai_image_background, "_download_image", return_value=candidate) as download,
            patch.object(ai_image_background, "_contains_visible_text", return_value=True),
        ):
            with self.assertRaises(ai_image_background.AIImageServiceError):
                ai_image_background._download_text_free_image("test prompt")

        self.assertEqual(download.call_count, 2)

    def test_quota_error_stops_all_later_generation_requests(self):
        candidate = Image.new("RGB", (16, 16), "white")
        segments = [
            {"index": index, "segment": f"scene {index}", "keywords": [], "duration": 1.0}
            for index in range(3)
        ]
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(ai_image_background.utils, "task_dir", return_value=directory),
                patch("app.services.llm.translate_to_english", side_effect=lambda value: value),
                patch.object(
                    ai_image_background,
                    "_download_text_free_image",
                    side_effect=[candidate, ai_image_background.AIImageQuotaError("quota")],
                ) as download,
                patch.object(ai_image_background, "_render_motion_clip"),
            ):
                results = ai_image_background.generate_videos_by_segments(
                    "quota-test", segments, "9:16", minimum_clip_duration=1.0
                )

        self.assertEqual(download.call_count, 2)
        self.assertEqual(len(results), 3)


if __name__ == "__main__":
    unittest.main()
