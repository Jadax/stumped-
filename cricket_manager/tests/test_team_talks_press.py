"""Team talks + press conferences (Phase 6): pure-function unit tests."""
from __future__ import annotations

import random
import unittest

from src.models.press_conference import RESPONSE_TONES, answer_press_conference, press_conference_question
from src.models.team_talks import TEAM_TALK_TONES, deliver_team_talk


class TeamTalkTests(unittest.TestCase):
    def test_unknown_tone_raises(self) -> None:
        with self.assertRaises(ValueError):
            deliver_team_talk("Furious")

    def test_delta_stays_within_the_tone_s_declared_range(self) -> None:
        rng = random.Random(1)
        for tone, (low, high) in TEAM_TALK_TONES.items():
            for _ in range(50):
                result = deliver_team_talk(tone, rng)
                self.assertEqual(result["tone"], tone)
                self.assertGreaterEqual(result["delta"], low)
                self.assertLessEqual(result["delta"], high)
                self.assertTrue(result["reaction"])

    def test_aggressive_can_genuinely_backfire(self) -> None:
        rng = random.Random(1)
        deltas = [deliver_team_talk("Aggressive", rng)["delta"] for _ in range(200)]
        self.assertTrue(any(d < 0 for d in deltas), "Aggressive should sometimes backfire")
        self.assertTrue(any(d > 5 for d in deltas), "Aggressive should sometimes land big")


class PressConferenceTests(unittest.TestCase):
    def test_unknown_tone_raises(self) -> None:
        with self.assertRaises(ValueError):
            answer_press_conference("Sarcastic")

    def test_known_tones_have_deltas_and_a_quote(self) -> None:
        for tone in RESPONSE_TONES:
            result = answer_press_conference(tone)
            self.assertEqual(result["tone"], tone)
            self.assertIsInstance(result["confidence_delta"], int)
            self.assertIsInstance(result["morale_delta"], int)
            self.assertTrue(result["quote"])

    def test_question_flavour_changes_with_league_position(self) -> None:
        top = press_conference_question(1, 12)
        bottom = press_conference_question(11, 12)
        mid = press_conference_question(6, 12)
        no_position = press_conference_question(None)
        self.assertNotEqual(top, bottom)
        self.assertNotEqual(top, mid)
        self.assertTrue(no_position)


if __name__ == "__main__":
    unittest.main()
