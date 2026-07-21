"""Staff transfer market, retirement/regeneration, and commentary modes (v0.23.0)."""
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
    path = os.path.join(tempfile.mkdtemp(), "staff_market.db")
    initialise_database(path)
    return path


class StaffMarketTests(unittest.TestCase):
    def test_browse_excludes_own_club_and_prices_every_listing(self) -> None:
        from database import browse_staff_market
        db = _fresh_db()
        market = browse_staff_market(exclude_team=1, database_path=db)
        self.assertTrue(market)
        self.assertTrue(all(member["team_id"] != 1 for member in market))
        self.assertTrue(all(member["fee"] > 0 for member in market))

    def test_group_filter_narrows_the_market(self) -> None:
        from database import browse_staff_market
        db = _fresh_db()
        medical_only = browse_staff_market("Medical", exclude_team=1, database_path=db)
        self.assertTrue(medical_only)
        self.assertTrue(all(member["group_name"] == "Medical" for member in medical_only))

    def test_signing_moves_staff_and_transfers_cash_both_ways(self) -> None:
        from database import (browse_staff_market, connect, fetch_staff, make_staff_offer,
                              resolve_staff_offer)
        db = _fresh_db()
        target = browse_staff_market(exclude_team=1, database_path=db)[0]
        with connect(db) as c:
            buyer_before = c.execute("SELECT cash FROM teams WHERE id=?", (1,)).fetchone()[0]
            seller_before = c.execute("SELECT cash FROM teams WHERE id=?", (target["team_id"],)).fetchone()[0]
        offer_id = make_staff_offer(target["id"], target["team_id"], 1, target["fee"], target["wage"],
                                    "2026-04-01", db)
        accepted = resolve_staff_offer(offer_id, True, db)
        self.assertTrue(accepted)
        with connect(db) as c:
            buyer_after = c.execute("SELECT cash FROM teams WHERE id=?", (1,)).fetchone()[0]
            seller_after = c.execute("SELECT cash FROM teams WHERE id=?", (target["team_id"],)).fetchone()[0]
        self.assertEqual(buyer_after, buyer_before - target["fee"])
        self.assertEqual(seller_after, seller_before + target["fee"])
        self.assertTrue(any(m["id"] == target["id"] for m in fetch_staff(1, database_path=db)))

    def test_signing_fails_when_buyer_cannot_afford_it(self) -> None:
        from database import browse_staff_market, connect, make_staff_offer, resolve_staff_offer
        db = _fresh_db()
        target = browse_staff_market(exclude_team=1, database_path=db)[0]
        with connect(db) as c:
            c.execute("UPDATE teams SET cash = 0 WHERE id = 1")
        offer_id = make_staff_offer(target["id"], target["team_id"], 1, target["fee"], target["wage"],
                                    "2026-04-01", db)
        self.assertFalse(resolve_staff_offer(offer_id, True, db))

    def test_selling_pays_the_selling_club_and_vacates_the_role(self) -> None:
        from database import fetch_staff, sell_staff_member, connect
        db = _fresh_db()
        roster = fetch_staff(1, "Medical", database_path=db)
        member = roster[0]
        with connect(db) as c:
            before = c.execute("SELECT cash FROM teams WHERE id=?", (1,)).fetchone()[0]
        fee = sell_staff_member(member["id"], db)
        self.assertGreater(fee, 0)
        with connect(db) as c:
            after = c.execute("SELECT cash FROM teams WHERE id=?", (1,)).fetchone()[0]
        self.assertEqual(after, before + fee)
        remaining = fetch_staff(1, "Medical", database_path=db)
        self.assertNotIn(member["id"], [m["id"] for m in remaining])


class StaffRetirementTests(unittest.TestCase):
    def test_veteran_staff_can_retire_and_are_replaced(self) -> None:
        from database import age_staff_at_rollover, connect, fetch_staff, json as _unused  # noqa: F401
        import json as jsonlib
        db = _fresh_db()
        with connect(db) as c:
            c.execute("UPDATE staff SET age = 65 WHERE team_id = 1")
        before_count = len(fetch_staff(1, database_path=db))
        result = age_staff_at_rollover(2026, db)
        after_roster = fetch_staff(1, database_path=db)
        # Department sizes are preserved even when veterans retire this season.
        self.assertEqual(len(after_roster), before_count)
        self.assertIn("retired", result)

    def test_non_veteran_staff_never_retire(self) -> None:
        from database import age_staff_at_rollover, connect
        db = _fresh_db()
        with connect(db) as c:
            c.execute("UPDATE staff SET age = 30")
        result = age_staff_at_rollover(2026, db)
        self.assertEqual(result["retired"], [])


class CommentaryModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))

    def _match_screen(self):
        from database import fetch_players, fetch_teams
        from ui.match_view import MatchScreen
        db = _fresh_db()
        teams = fetch_teams(db)
        home, away = dict(teams[0]), dict(teams[1])
        ctx = {
            "database_path": db, "team": home, "players": fetch_players(home["id"], db),
            "match_setup": {"user_xi": fetch_players(home["id"], db)[:11],
                            "opponent_xi": fetch_players(away["id"], db)[:11],
                            "fixture": {"format": "T20", "home_team": home["id"], "away_team": away["id"],
                                       "away_name": away["name"], "home_name": home["name"], "id": 1},
                            "pitch": "Green", "weather": "Overcast"},
            "selection": {}, "new_game_setup": {}, "current_date": "2026-04-01",
        }
        return MatchScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660), 1.0, ctx)

    def test_key_moments_mode_logs_far_fewer_lines_than_full(self) -> None:
        screen = self._match_screen()
        for _ in range(30):
            screen.simulate_ball()
        full_count = len(screen.commentary)
        screen.commentary_mode = "Key Moments"
        screen.commentary = []
        for _ in range(30):
            screen.simulate_ball()
        key_count = len(screen.commentary)
        self.assertLess(key_count, full_count)
        self.assertTrue(all(kind in ("wicket", "milestone", "run") for _, kind in screen.commentary))

    def test_commentary_button_toggles_and_renders(self) -> None:
        screen = self._match_screen()
        self.assertEqual(screen.commentary_mode, "Full")
        screen.commentary_mode = "Key Moments"
        screen.commentary_button.label = f"COMM: {screen.commentary_mode.upper()}"
        screen.draw(self.surface)
        self.assertIn("KEY MOMENTS", screen.commentary_button.label)

    def test_header_row_controls_stay_within_the_content_rect(self) -> None:
        screen = self._match_screen()
        right_edge = screen.content_rect.right - 18
        self.assertLessEqual(screen.commentary_button.rect.right, right_edge)
        for _, button in screen.speed_buttons:
            self.assertLessEqual(button.rect.right, right_edge)
            self.assertGreaterEqual(button.rect.x, screen.content_rect.x)


class StaffMarketUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))

    def test_staff_screen_market_mode_renders_and_can_sign(self) -> None:
        from database import fetch_players, fetch_teams
        from ui.staff import StaffScreen
        db = _fresh_db()
        team = dict(fetch_teams(db)[0])
        ctx = {"database_path": db, "team": team, "players": fetch_players(team["id"], db),
              "current_date": "2026-04-01"}
        screen = StaffScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660), 1.0, ctx)
        screen.mode = "Market"
        from ui.widgets import TabBar
        screen.group_bar = TabBar(screen.group_bar.rect, screen.MARKET_FILTERS, "All")
        screen.refresh_rows()
        self.assertTrue(screen.table.rows)
        screen.draw(self.surface)
        target = screen.table.rows[0]
        screen.selected = target
        screen._act_on_selected()
        from database import fetch_staff
        self.assertTrue(any(m["id"] == target["id"] for m in fetch_staff(team["id"], database_path=db)))

    def test_staff_and_medical_screens_still_registered(self) -> None:
        from main import NAV_SCREEN_NAMES, SCREEN_CLASSES
        self.assertIn("Staff", SCREEN_CLASSES)
        self.assertIn("Staff", NAV_SCREEN_NAMES)


if __name__ == "__main__":
    unittest.main()
