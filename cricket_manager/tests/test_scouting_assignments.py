"""Active scouting assignments — send a scout, wait N days, get a report (v0.27.0)."""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402
import pygame_gui  # noqa: E402


def _fresh_db() -> str:
    from database import initialise_database
    path = os.path.join(tempfile.mkdtemp(), "scouting.db")
    initialise_database(path)
    return path


class ScoutingAssignmentDatabaseTests(unittest.TestCase):
    def test_create_assignment_requires_own_scout(self) -> None:
        from database import create_scouting_assignment, fetch_players, fetch_staff
        db = _fresh_db()
        other_team_scout = fetch_staff(2, "Scouting", db)[0]
        target = fetch_players(2, db)[0]
        with self.assertRaises(ValueError):
            create_scouting_assignment(1, other_team_scout["id"], target["id"], 5, "2026-04-01", db)

    def test_scout_cannot_hold_two_assignments_at_once(self) -> None:
        from database import create_scouting_assignment, fetch_players, fetch_staff
        db = _fresh_db()
        scout = fetch_staff(1, "Scouting", db)[0]
        targets = fetch_players(2, db)
        create_scouting_assignment(1, scout["id"], targets[0]["id"], 5, "2026-04-01", db)
        with self.assertRaises(ValueError):
            create_scouting_assignment(1, scout["id"], targets[1]["id"], 5, "2026-04-01", db)

    def test_assignment_completes_after_total_days_and_reports_an_estimate(self) -> None:
        from database import advance_scouting_assignments, create_scouting_assignment, fetch_players, fetch_scouting_assignments, fetch_staff
        db = _fresh_db()
        scout = fetch_staff(1, "Scouting", db)[0]
        target = fetch_players(2, db)[0]
        create_scouting_assignment(1, scout["id"], target["id"], 3, "2026-04-01", db)
        for day in range(2):
            self.assertEqual(advance_scouting_assignments(f"2026-04-0{2 + day}", db), [])
        completed = advance_scouting_assignments("2026-04-04", db)
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["target_name"], target["name"])
        stored = fetch_scouting_assignments(1, db)[0]
        self.assertEqual(stored["status"], "COMPLETE")
        self.assertIsNotNone(stored["estimated_overall"])
        self.assertIsNotNone(stored["confidence"])

    def test_advance_day_files_an_inbox_report_when_an_assignment_completes(self) -> None:
        from competition import CompetitionEngine
        from database import (create_scouting_assignment, fetch_inbox_messages, fetch_players,
                              fetch_staff, load_game)
        db = _fresh_db()
        engine = CompetitionEngine(db)
        user = load_game(db)["user"]
        engine.ensure_season(2026)
        scout = fetch_staff(user["current_team_id"], "Scouting", db)[0]
        target = next(p for p in fetch_players(2, db))
        create_scouting_assignment(user["current_team_id"], scout["id"], target["id"], 1, user["current_date"], db)
        engine.advance_day()
        messages = fetch_inbox_messages(20, db)
        self.assertTrue(any("Scouting report" in m["title"] for m in messages))


class ScoutingAssignmentUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))

    def _context(self) -> dict:
        from database import fetch_players, fetch_teams
        db = _fresh_db()
        team = dict(fetch_teams(db)[0])
        return {"database_path": db, "team": team, "players": fetch_players(team["id"], db),
               "current_date": "2026-04-01"}

    def test_send_scout_button_creates_an_assignment(self) -> None:
        from database import fetch_scouting_assignments
        from ui.transfers import TransfersScreen
        screen = TransfersScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660),
                                 1.0, self._context())
        self.assertTrue(screen.scout_button.enabled)
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": screen.scout_button.rect.center, "button": 1})
        screen.process_event(event)
        assignments = fetch_scouting_assignments(screen.team_id, screen.db)
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]["status"], "ACTIVE")

    def test_recruitment_hub_renders_scouting_assignments_tile(self) -> None:
        from database import create_scouting_assignment, fetch_players, fetch_staff
        from ui.recruitment import RecruitmentHubScreen
        ctx = self._context()
        scout = fetch_staff(ctx["team"]["id"], "Scouting", ctx["database_path"])[0]
        target = fetch_players(2, ctx["database_path"])[0]
        create_scouting_assignment(ctx["team"]["id"], scout["id"], target["id"], 5, "2026-04-01", ctx["database_path"])
        screen = RecruitmentHubScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660), 1.0, ctx)
        self.assertEqual(len(screen.assignments), 1)
        screen.draw(self.surface)


if __name__ == "__main__":
    unittest.main()
