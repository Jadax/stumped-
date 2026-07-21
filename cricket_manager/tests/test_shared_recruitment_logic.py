"""src/models/recruitment.py + squad_metrics.py — extracted from ui/recruitment.py
so the pygame client and the Godot IPC backend apply identical rules
(docs/GRAPHICS_MIGRATION_PLAN.md Recruitment placeholder note)."""
from __future__ import annotations
import unittest


def player(pid: int, role: str, contract_years_remaining: int = 2) -> dict:
    return {"id": pid, "name": f"Player {pid}", "role": role, "age": 25, "overall": 65, "potential": 70,
           "contract_years_remaining": contract_years_remaining,
           "batting": {"attack": 60}, "bowling": {"pace": 50}, "fielding": {"catching": 55}}


class SquadMetricsTests(unittest.TestCase):
    def test_group_average_and_estimated_value_still_reachable_via_shared_components(self) -> None:
        """Regression: many ui/*.py modules import these from .shared_components —
        moving the definitions to src/models/squad_metrics.py must not break that."""
        from ui.shared_components import estimated_value, group_average
        from src.models.squad_metrics import estimated_value as direct_value, group_average as direct_average
        self.assertIs(group_average, direct_average)
        self.assertIs(estimated_value, direct_value)
        p = player(1, "Batsman")
        self.assertEqual(group_average(p, "batting"), 60)


class RecruitmentLogicTests(unittest.TestCase):
    def test_role_gaps_flags_understrength_roles_only(self) -> None:
        from src.models.recruitment import ROLE_TARGETS, role_gaps
        squad = [player(1, "Wicketkeeper")]
        gaps = dict(role_gaps(squad))
        self.assertEqual(gaps["Wicketkeeper"], 1)
        self.assertLess(gaps["Wicketkeeper"], ROLE_TARGETS["Wicketkeeper"])
        self.assertIn("Bowler", gaps)

    def test_role_gaps_empty_when_every_role_at_target(self) -> None:
        from src.models.recruitment import ROLE_TARGETS, role_gaps
        squad = []
        for role, target in ROLE_TARGETS.items():
            squad += [player(100 + i, role) for i in range(target)]
        self.assertEqual(role_gaps(squad), [])

    def test_weakest_attribute_group_picks_lowest_average(self) -> None:
        from src.models.recruitment import weakest_attribute_group
        squad = [dict(player(1, "Batsman"), batting={"attack": 90}, bowling={"pace": 20}, fielding={"catching": 80})]
        self.assertEqual(weakest_attribute_group(squad), "bowling")

    def test_contract_watch_flags_expiring_and_free_agents(self) -> None:
        from src.models.recruitment import contract_watch
        squad = [player(1, "Batsman", contract_years_remaining=3),
                player(2, "Batsman", contract_years_remaining=1),
                player(3, "Batsman", contract_years_remaining=0)]
        watch = contract_watch(squad)
        self.assertEqual(len(watch), 2)
        statuses = {w["id"]: w["status"] for w in watch}
        self.assertEqual(statuses[2], "Expires this year")
        self.assertEqual(statuses[3], "Free agent")

    def test_pygame_recruitment_screen_delegates_to_shared_role_gaps(self) -> None:
        """Regression: RecruitmentHubScreen._role_gaps() must keep returning
        exactly what src.models.recruitment.role_gaps() returns."""
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame, pygame_gui
        pygame.init()
        from database import fetch_players, fetch_teams, get_team_summary, initialise_database
        import tempfile
        db = os.path.join(tempfile.mkdtemp(), "recruitment_logic.db")
        initialise_database(db)
        team = get_team_summary(fetch_teams(db)[0]["id"], db)
        players = fetch_players(team["id"], db)
        from ui.recruitment import RecruitmentHubScreen
        from src.models.recruitment import role_gaps
        screen = RecruitmentHubScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660),
                                     1.0, {"database_path": db, "team": team, "players": players})
        self.assertEqual(screen._role_gaps(), role_gaps(players))


if __name__ == "__main__":
    unittest.main()
