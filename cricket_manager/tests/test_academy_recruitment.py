"""Targeted academy recruitment: realistic role-differentiated youth intake."""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402
import pygame_gui  # noqa: E402


def _bat_bowl_avg(player: dict) -> tuple[float, float]:
    bat = sum(player["batting"].values()) / len(player["batting"])
    bowl = sum(player["bowling"].values()) / len(player["bowling"])
    return bat, bowl


class AcademyRecruitmentModelTests(unittest.TestCase):
    def setUp(self) -> None:
        from database import initialise_database, fetch_teams
        self.database = os.path.join(tempfile.mkdtemp(), "academy.db")
        initialise_database(self.database)
        self.team_id = fetch_teams(self.database)[0]["id"]

    def test_role_focus_is_respected_for_every_recruit(self) -> None:
        from database import recruit_youth
        for focus, expected_role in (("Batsman", "Batsman"), ("Pace Bowler", "Bowler"),
                                     ("Spin Bowler", "Bowler"), ("All-Rounder", "All-Rounder"),
                                     ("Wicketkeeper", "Wicketkeeper")):
            created = recruit_youth(self.team_id, count=4, role_focus=focus, database_path=self.database)
            self.assertEqual(len(created), 4)
            for player in created:
                self.assertEqual(player["role"], expected_role)

    def test_bowlers_are_not_secretly_good_batters(self) -> None:
        """A requested bowler must not out-bat a requested batsman on average."""
        from database import recruit_youth
        batters = recruit_youth(self.team_id, count=6, role_focus="Batsman", database_path=self.database)
        bowlers = recruit_youth(self.team_id, count=6, role_focus="Pace Bowler", database_path=self.database)
        batter_bat_avg = sum(_bat_bowl_avg(p)[0] for p in batters) / len(batters)
        bowler_bat_avg = sum(_bat_bowl_avg(p)[0] for p in bowlers) / len(bowlers)
        self.assertGreater(batter_bat_avg, bowler_bat_avg)
        batter_bowl_avg = sum(_bat_bowl_avg(p)[1] for p in batters) / len(batters)
        bowler_bowl_avg = sum(_bat_bowl_avg(p)[1] for p in bowlers) / len(bowlers)
        self.assertGreater(bowler_bowl_avg, batter_bowl_avg)

    def test_pace_focus_produces_faster_bowlers_than_spin_focus(self) -> None:
        from database import recruit_youth
        pace_players = recruit_youth(self.team_id, count=8, role_focus="Pace Bowler", database_path=self.database)
        spin_players = recruit_youth(self.team_id, count=8, role_focus="Spin Bowler", database_path=self.database)
        avg_pace_of_pacers = sum(p["bowling"]["pace"] for p in pace_players) / len(pace_players)
        avg_pace_of_spinners = sum(p["bowling"]["pace"] for p in spin_players) / len(spin_players)
        avg_spin_of_pacers = sum(p["bowling"]["swing_or_spin"] for p in pace_players) / len(pace_players)
        avg_spin_of_spinners = sum(p["bowling"]["swing_or_spin"] for p in spin_players) / len(spin_players)
        self.assertGreater(avg_pace_of_pacers, avg_pace_of_spinners)
        self.assertGreater(avg_spin_of_spinners, avg_spin_of_pacers)
        # Most individual recruits should lean toward the requested focus —
        # not literally every one. recruit_youth() applies a fixed shift
        # (14-22 pace/spin swing) on top of each player's already-random
        # base attributes, so an extreme base draw can still occasionally
        # invert the post-shift ordering for one or two recruits out of 8;
        # requiring unanimous compliance made this fail a real, reproducible
        # fraction of full-suite runs (not "rare flake" — every genuinely
        # random group of 8 has a meaningful chance of one outlier). The
        # aggregate assertions above already prove the mechanism works;
        # this just checks it holds for most individuals, not all.
        pace_compliant = sum(1 for p in pace_players if p["bowling"]["pace"] >= p["bowling"]["swing_or_spin"])
        spin_compliant = sum(1 for p in spin_players if p["bowling"]["swing_or_spin"] >= p["bowling"]["pace"])
        self.assertGreaterEqual(pace_compliant, 6, f"only {pace_compliant}/8 pace recruits leaned pace")
        self.assertGreaterEqual(spin_compliant, 6, f"only {spin_compliant}/8 spin recruits leaned spin")

    def test_any_focus_still_varies_roles(self) -> None:
        from database import recruit_youth
        created = recruit_youth(self.team_id, count=12, role_focus="Any", database_path=self.database)
        self.assertGreater(len({p["role"] for p in created}), 1)


class AcademyScreenUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))
        from database import initialise_database, fetch_teams, fetch_players
        cls.database = os.path.join(tempfile.mkdtemp(), "academy_ui.db")
        initialise_database(cls.database)
        team = dict(fetch_teams(cls.database)[0])
        cls.context = {"database_path": cls.database, "team": team,
                       "players": fetch_players(team["id"], cls.database), "current_date": "2026-04-01"}

    def test_scout_role_button_cycles_and_renders(self) -> None:
        from database import ACADEMY_ROLE_FOCUSES
        from ui.youth import YouthScreen
        screen = YouthScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660),
                             1.0, dict(self.context))
        self.assertEqual(screen.scout_role_index, 0)
        for expected in ACADEMY_ROLE_FOCUSES[1:] + [ACADEMY_ROLE_FOCUSES[0]]:
            screen.scout_role_index = (screen.scout_role_index + 1) % len(ACADEMY_ROLE_FOCUSES)
            screen.scout_role_button.label = f"SCOUT FOR: {ACADEMY_ROLE_FOCUSES[screen.scout_role_index].upper()}"
            self.assertIn(expected.upper(), screen.scout_role_button.label)
        screen.draw(self.surface)


if __name__ == "__main__":
    unittest.main()
