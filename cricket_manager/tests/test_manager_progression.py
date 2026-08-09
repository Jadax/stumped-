"""v4.58.0: manager progression — a real XP/level/perk ladder for the
manager themselves, distinct from src/models/career.py's stateless
manager_reputation(). XP is earned at real gameplay hook points (match
wins, season trophies, board objectives met, team talks/press conferences);
each level banks a perk point spendable on a small perk tree that modifies
existing formulas (team talks, press conferences, youth intake, pitch
change delay) at their exact source.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import database
from src.models.manager_progression import PERKS_BY_ID, can_unlock, level_for_xp, points_available
from src.models.press_conference import answer_press_conference
from src.models.team_talks import deliver_team_talk


class ProgressionModelTests(unittest.TestCase):
    def test_level_for_xp_bands(self) -> None:
        self.assertEqual(level_for_xp(0), 1)
        self.assertEqual(level_for_xp(99), 1)
        self.assertEqual(level_for_xp(100), 2)
        self.assertEqual(level_for_xp(250), 3)

    def test_points_available_is_level_minus_one_minus_spent(self) -> None:
        self.assertEqual(points_available(xp=250, unlocked_count=0), 2)
        self.assertEqual(points_available(xp=250, unlocked_count=1), 1)
        self.assertEqual(points_available(xp=0, unlocked_count=0), 0)

    def test_can_unlock_enforces_level_and_points_and_dedupe(self) -> None:
        perk_id = next(iter(PERKS_BY_ID))
        min_level = PERKS_BY_ID[perk_id]["min_level"]
        low_xp = (min_level - 1) * 100 - 1  # one level short
        ok, _ = can_unlock(perk_id, low_xp, set())
        self.assertFalse(ok)
        high_xp = min_level * 100
        ok, _ = can_unlock(perk_id, high_xp, set())
        self.assertTrue(ok)
        ok, reason = can_unlock(perk_id, high_xp, {perk_id})
        self.assertFalse(ok)
        self.assertIn("Already", reason)
        ok, reason = can_unlock("not_a_real_perk", 10_000, set())
        self.assertFalse(ok)


class PerkEffectTests(unittest.TestCase):
    def test_motivational_speaker_widens_team_talk_upside(self) -> None:
        import random
        rng = random.Random(1)
        without = max(deliver_team_talk("Calm", random.Random(seed))["delta"] for seed in range(50))
        with_perk = max(
            deliver_team_talk("Calm", random.Random(seed), perk_ids={"motivational_speaker"})["delta"]
            for seed in range(50)
        )
        self.assertGreaterEqual(with_perk, without)

    def test_squad_harmony_raises_aggressive_floor(self) -> None:
        import random
        worst_without = min(deliver_team_talk("Aggressive", random.Random(seed))["delta"] for seed in range(200))
        worst_with = min(
            deliver_team_talk("Aggressive", random.Random(seed), perk_ids={"squad_harmony"})["delta"]
            for seed in range(200)
        )
        self.assertLess(worst_without, -2)
        self.assertGreaterEqual(worst_with, -2)

    def test_media_trained_softens_critical_tone(self) -> None:
        base = answer_press_conference("Critical")
        softened = answer_press_conference("Critical", perk_ids={"media_trained"})
        self.assertGreater(softened["confidence_delta"], base["confidence_delta"])
        self.assertGreater(softened["morale_delta"], base["morale_delta"])

    def test_calm_head_adds_confidence_bonus(self) -> None:
        base = answer_press_conference("Diplomatic")
        boosted = answer_press_conference("Diplomatic", perk_ids={"calm_head"})
        self.assertEqual(boosted["confidence_delta"], base["confidence_delta"] + 1)


class ManagerProgressPersistenceTests(unittest.TestCase):
    def _db(self) -> str:
        db = os.path.join(tempfile.mkdtemp(), "progress.db")
        database.initialise_database(db)
        return db

    def test_award_manager_xp_accumulates_and_reports_level_up(self) -> None:
        db = self._db()
        first = database.award_manager_xp(60, "test", db)
        self.assertEqual(first["xp"], 60)
        self.assertFalse(first["leveled_up"])
        second = database.award_manager_xp(60, "test", db)
        self.assertEqual(second["xp"], 120)
        self.assertTrue(second["leveled_up"])

    def test_unlock_manager_perk_persists_and_rejects_when_ineligible(self) -> None:
        db = self._db()
        with self.assertRaises(ValueError):
            database.unlock_manager_perk("motivational_speaker", db)
        database.award_manager_xp(100, "test", db)  # level 2, 1 point
        progress = database.unlock_manager_perk("motivational_speaker", db)
        self.assertIn("motivational_speaker", progress["unlocked"])
        self.assertTrue(database.has_manager_perk("motivational_speaker", db))
        self.assertFalse(database.has_manager_perk("calm_head", db))
        with self.assertRaises(ValueError):
            database.unlock_manager_perk("motivational_speaker", db)  # already unlocked

    def test_get_manager_progress_shape(self) -> None:
        db = self._db()
        progress = database.get_manager_progress(db)
        self.assertEqual(progress["xp"], 0)
        self.assertEqual(progress["level"], 1)
        self.assertEqual(progress["points_available"], 0)
        self.assertEqual(len(progress["perks"]), len(PERKS_BY_ID))

    def test_groundsman_friend_perk_shortens_pitch_delay(self) -> None:
        db = self._db()
        game_data = database.load_game(db)
        team_id = game_data["user"]["current_team_id"]
        without = database.set_pitch_selection(team_id, "Dry", db)
        database.award_manager_xp(200, "test", db)
        database.unlock_manager_perk("groundsman_friend", db)
        with_perk = database.set_pitch_selection(team_id, "Dusty", db)
        self.assertEqual(with_perk["days_remaining"], without["days_remaining"] - 1)


class ManagerProgressIpcTests(unittest.TestCase):
    def _context(self) -> dict:
        from database import fetch_players, get_team_summary, initialise_database, load_game
        db = os.path.join(tempfile.mkdtemp(), "ipc_progress.db")
        initialise_database(db)
        game_data = load_game(db)
        team = get_team_summary(game_data["user"]["current_team_id"], db)
        return {"database_path": db, "team": team, "players": fetch_players(team["id"], db), "game_data": game_data}

    def test_get_manager_progress_round_trips_through_ipc(self) -> None:
        import ipc_server
        ctx = self._context()
        result = ipc_server._get_manager_progress({}, ctx)
        self.assertEqual(result["xp"], 0)
        self.assertEqual(result["level"], 1)

    def test_delivering_a_team_talk_awards_xp(self) -> None:
        import ipc_server
        ctx = self._context()
        ipc_server._deliver_team_talk({"tone": "Calm"}, ctx)
        progress = ipc_server._get_manager_progress({}, ctx)
        self.assertGreater(progress["xp"], 0)

    def test_unlock_manager_perk_via_ipc(self) -> None:
        import ipc_server
        ctx = self._context()
        with self.assertRaises(ValueError):
            ipc_server._unlock_manager_perk({"perk_id": "motivational_speaker"}, ctx)
        ipc_server._deliver_team_talk({"tone": "Calm"}, ctx)  # a couple of XP, real hook exercised
        database.award_manager_xp(100, "top-up for test", ctx["database_path"])
        result = ipc_server._unlock_manager_perk({"perk_id": "motivational_speaker"}, ctx)
        self.assertIn("motivational_speaker", result["unlocked"])


if __name__ == "__main__":
    unittest.main()
