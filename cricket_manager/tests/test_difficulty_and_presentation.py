from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.models.difficulty import DifficultyManager


ROOT = Path(__file__).resolve().parents[1]


class DifficultyTests(unittest.TestCase):
    def test_levels_apply_real_ordered_modifiers(self):
        easy, normal, hard = (DifficultyManager(level) for level in ("Easy", "Normal", "Hard"))
        self.assertGreater(easy.ai_mistake_rate, normal.ai_mistake_rate)
        self.assertGreater(normal.ai_mistake_rate, hard.ai_mistake_rate)
        self.assertGreater(easy.user_cash_bonus, normal.user_cash_bonus)
        self.assertGreater(normal.user_cash_bonus, hard.user_cash_bonus)
        self.assertGreater(easy.player_development_rate, hard.player_development_rate)
        self.assertGreater(hard.ai_review_accuracy, easy.ai_review_accuracy)

    def test_invalid_level_is_rejected(self):
        with self.assertRaises(ValueError):
            DifficultyManager("Legendary")


class PresentationDataTests(unittest.TestCase):
    def test_help_and_match_faq_are_comprehensive(self):
        help_data = json.loads((ROOT / "src/data/help_content.json").read_text(encoding="utf-8"))
        faq_data = json.loads((ROOT / "src/data/match_engine_faq.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(help_data["sections"]), 10)
        self.assertGreaterEqual(len(faq_data["questions"]), 10)
        self.assertTrue(all(item["answer"] for item in faq_data["questions"]))

    def test_inter_font_and_license_are_bundled(self):
        self.assertGreater((ROOT / "assets/fonts/Inter-VariableFont_opsz,wght.ttf").stat().st_size, 100_000)
        license_text = (ROOT / "assets/fonts/OFL-Inter.txt").read_text(encoding="utf-8")
        self.assertIn("SIL OPEN FONT LICENSE", license_text)

    def test_donation_language_is_absent_from_runtime(self):
        runtime = (ROOT / "main.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("buy me a coffee", runtime)


if __name__ == "__main__":
    unittest.main()
