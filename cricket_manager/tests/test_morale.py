"""Coverage for the dynamic player morale system (docs/CURRENT.md)."""
from __future__ import annotations
import os
import tempfile
import unittest

from src.models.morale import (
    CUP_STAKES_MULTIPLIER, LOSS_MORALE_DELTA, TIE_MORALE_DELTA, WIN_MORALE_DELTA,
    dropped_from_xi, match_result_morale_deltas,
)


def _fresh_db() -> str:
    from database import initialise_database
    path = os.path.join(tempfile.mkdtemp(), "morale.db")
    initialise_database(path)
    return path


class MoraleEventFormulaTests(unittest.TestCase):
    def test_match_result_morale_deltas_rewards_the_winner_and_penalises_the_loser(self) -> None:
        deltas = match_result_morale_deltas(winner_id=1, home_id=1, away_id=2, tied=False)
        self.assertEqual(deltas, {1: WIN_MORALE_DELTA, 2: LOSS_MORALE_DELTA})

    def test_match_result_morale_deltas_handles_the_away_team_winning(self) -> None:
        deltas = match_result_morale_deltas(winner_id=2, home_id=1, away_id=2, tied=False)
        self.assertEqual(deltas, {2: WIN_MORALE_DELTA, 1: LOSS_MORALE_DELTA})

    def test_match_result_morale_deltas_gives_both_teams_a_small_bump_on_a_tie(self) -> None:
        deltas = match_result_morale_deltas(winner_id=None, home_id=1, away_id=2, tied=True)
        self.assertEqual(deltas, {1: TIE_MORALE_DELTA, 2: TIE_MORALE_DELTA})

    def test_cup_fixtures_carry_higher_stakes_than_league_fixtures(self) -> None:
        league = match_result_morale_deltas(winner_id=1, home_id=1, away_id=2, tied=False, is_cup=False)
        cup = match_result_morale_deltas(winner_id=1, home_id=1, away_id=2, tied=False, is_cup=True)
        self.assertEqual(cup[1], round(WIN_MORALE_DELTA * CUP_STAKES_MULTIPLIER))
        self.assertGreater(abs(cup[1]), abs(league[1]))
        self.assertGreater(abs(cup[2]), abs(league[2]))

    def test_dropped_from_xi_finds_only_players_left_out(self) -> None:
        self.assertEqual(dropped_from_xi(previous_xi=[1, 2, 3], new_xi=[1, 2, 3]), [])
        self.assertEqual(dropped_from_xi(previous_xi=[1, 2, 3], new_xi=[1, 2, 4]), [3])
        self.assertEqual(dropped_from_xi(previous_xi=[], new_xi=[1, 2, 3]), [])


class MoralePersistenceTests(unittest.TestCase):
    def test_adjust_players_morale_is_bounded_and_scoped_to_the_given_players(self) -> None:
        from database import adjust_players_morale, fetch_players, fetch_teams
        db = _fresh_db()
        team = fetch_teams(db)[0]
        players = fetch_players(team["id"], db)
        target, untouched = players[0], players[1]
        adjust_players_morale([target["id"]], -30, db)  # move off the ceiling first, deterministically
        after = fetch_players(team["id"], db)
        before = next(p for p in after if p["id"] == target["id"])["mental"]["morale"]
        adjust_players_morale([target["id"]], 100, db)  # push toward the ceiling
        after = fetch_players(team["id"], db)
        target_after = next(p for p in after if p["id"] == target["id"])
        untouched_after = next(p for p in after if p["id"] == untouched["id"])
        self.assertEqual(target_after["mental"]["morale"], 100)
        self.assertGreater(target_after["mental"]["morale"], before)
        self.assertEqual(untouched_after["mental"]["morale"], untouched["mental"]["morale"])

    def test_adjust_players_morale_never_goes_below_zero(self) -> None:
        from database import adjust_players_morale, fetch_players, fetch_teams
        db = _fresh_db()
        team = fetch_teams(db)[0]
        player = fetch_players(team["id"], db)[0]
        adjust_players_morale([player["id"]], -1000, db)
        after = next(p for p in fetch_players(team["id"], db) if p["id"] == player["id"])
        self.assertEqual(after["mental"]["morale"], 0)

    def test_adjust_team_morale_touches_the_whole_squad(self) -> None:
        from database import adjust_team_morale, fetch_players, fetch_teams
        db = _fresh_db()
        team = fetch_teams(db)[0]
        before = {p["id"]: p["mental"]["morale"] for p in fetch_players(team["id"], db)}
        adjust_team_morale(team["id"], 10, db)
        after = {p["id"]: p["mental"]["morale"] for p in fetch_players(team["id"], db)}
        self.assertTrue(all(after[pid] == min(100, before[pid] + 10) for pid in before))

    def test_renew_player_contract_lifts_morale(self) -> None:
        from database import adjust_players_morale, fetch_players, fetch_teams, renew_player_contract
        db = _fresh_db()
        team = fetch_teams(db)[0]
        player = fetch_players(team["id"], db)[0]
        adjust_players_morale([player["id"]], -30, db)  # move off the ceiling first, deterministically
        before = next(p for p in fetch_players(team["id"], db) if p["id"] == player["id"])["mental"]["morale"]
        renew_player_contract(player["id"], player["wage"] + 500, 3, database_path=db)
        after = next(p for p in fetch_players(team["id"], db) if p["id"] == player["id"])
        self.assertEqual(after["mental"]["morale"], min(100, before + 8))

    def test_rollover_season_lifts_promoted_squads_and_dents_relegated_ones(self) -> None:
        from competition import CompetitionEngine
        from database import fetch_players, fetch_teams
        db = _fresh_db()
        engine = CompetitionEngine(db, seed=11)
        engine.ensure_season(2026)
        before = {team["id"]: {p["id"]: p["mental"]["morale"] for p in fetch_players(team["id"], db)}
                 for team in fetch_teams(db)}
        result = engine.rollover_season(2026)
        after_teams = fetch_teams(db)
        for team in after_teams:
            if team["id"] in result["promoted"]:
                sample = fetch_players(team["id"], db)
                if sample:
                    self.assertGreaterEqual(sample[0]["mental"]["morale"], before[team["id"]].get(sample[0]["id"], 0))
            if team["id"] in result["relegated"]:
                sample = fetch_players(team["id"], db)
                if sample:
                    self.assertLessEqual(sample[0]["mental"]["morale"], before[team["id"]].get(sample[0]["id"], 100))


if __name__ == "__main__":
    unittest.main()
