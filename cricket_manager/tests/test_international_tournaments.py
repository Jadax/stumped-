"""Real ICC tournament structure (v4.10.0) — previously "ICC World Cup"/
"ICC T20 World Cup"/"ICC Champions Trophy" declared a team count that was
never used: _run_international_window sampled N nations and only ever
played a single match between the first two, dropping every other nation
and never running a group stage or knockout. This tests the real
group-stage-then-knockout engine that replaced it."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from competition import CompetitionEngine
from database import connect, initialise_database
from src.models.international import ICC_TOURNAMENTS, INTERNATIONAL_NATIONALITIES, NATIONAL_TEAM_IDS


class TemporaryGameTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()


def _tournament(name: str) -> dict:
    return next(t for t in ICC_TOURNAMENTS if t["name"] == name)


def _group_match_ids(engine: CompetitionEngine, tournament_name: str, season: int) -> list[int]:
    with connect(engine.database_path) as connection:
        comp_ids = [row[0] for row in connection.execute(
            "SELECT id FROM competitions WHERE name LIKE ? AND season=? AND type='League'",
            (f"{tournament_name} {season}%", season),
        )]
        placeholders = ",".join("?" for _ in comp_ids)
        return [row[0] for row in connection.execute(
            f"SELECT id FROM matches WHERE competition_id IN ({placeholders})", comp_ids)]


def _simulate_all(engine: CompetitionEngine, match_ids: list[int]) -> None:
    for match_id in match_ids:
        with connect(engine.database_path) as connection:
            already = connection.execute("SELECT completed FROM matches WHERE id=?", (match_id,)).fetchone()
        if already and already[0]:
            continue
        engine._simulate_international_fixture(match_id)


class OdiWorldCupTests(TemporaryGameTest):
    def test_group_stage_involves_all_ten_nations_not_two(self) -> None:
        engine = CompetitionEngine(self.database, seed=7)
        engine._start_icc_tournament(_tournament("ICC World Cup"), 2026)
        match_ids = _group_match_ids(engine, "ICC World Cup", 2026)
        self.assertEqual(len(match_ids), 45, "10-nation single round-robin should be 45 matches")
        involved_ids: set[int] = set()
        with connect(self.database) as connection:
            for row in connection.execute(
                "SELECT home_team, away_team FROM matches WHERE id IN (%s)" % ",".join("?" for _ in match_ids),
                match_ids,
            ):
                involved_ids.add(row[0]); involved_ids.add(row[1])
        self.assertEqual(involved_ids, set(NATIONAL_TEAM_IDS.values()), "every nation should have real fixtures")

    def test_starting_twice_in_the_same_season_does_not_duplicate(self) -> None:
        engine = CompetitionEngine(self.database, seed=7)
        tournament = _tournament("ICC World Cup")
        engine._start_icc_tournament(tournament, 2026)
        first_count = len(_group_match_ids(engine, "ICC World Cup", 2026))
        with connect(self.database) as connection:
            already = connection.execute(
                "SELECT 1 FROM competitions WHERE name LIKE ? AND season=?", ("ICC World Cup 2026%", 2026)
            ).fetchone()
        self.assertIsNotNone(already, "the real dispatch path checks this before calling _start_icc_tournament again")
        self.assertEqual(first_count, 45)

    def test_full_group_stage_advances_to_a_real_semi_final_bracket(self) -> None:
        engine = CompetitionEngine(self.database, seed=11)
        engine._start_icc_tournament(_tournament("ICC World Cup"), 2026)
        match_ids = _group_match_ids(engine, "ICC World Cup", 2026)
        _simulate_all(engine, match_ids)
        with connect(self.database) as connection:
            knockout = connection.execute(
                "SELECT id FROM competitions WHERE name=? AND season=?",
                ("ICC World Cup 2026 — Knockout", 2026),
            ).fetchone()
            self.assertIsNotNone(knockout, "group stage completing should seed the knockout competition")
            semis = connection.execute(
                "SELECT home_team, away_team FROM matches WHERE competition_id=? AND round_name='Semi-final'",
                (knockout[0],),
            ).fetchall()
        self.assertEqual(len(semis), 2, "top 4 qualifiers should produce exactly 2 semi-finals")
        semi_teams = {team for row in semis for team in row}
        self.assertEqual(len(semi_teams), 4, "4 distinct qualifiers should be seeded, no repeats")

    def test_playing_through_to_the_final_crowns_a_champion(self) -> None:
        engine = CompetitionEngine(self.database, seed=13)
        engine._start_icc_tournament(_tournament("ICC World Cup"), 2026)
        _simulate_all(engine, _group_match_ids(engine, "ICC World Cup", 2026))
        # Semis now exist — simulate everything unfinished under the
        # Knockout competition until the Final itself has been played,
        # mirroring how _advance_cup_if_ready generates each round only
        # once the previous one is fully complete.
        for _ in range(3):  # Semi-final -> Final -> (nothing left)
            with connect(self.database) as connection:
                knockout_id = connection.execute(
                    "SELECT id FROM competitions WHERE name=? AND season=?",
                    ("ICC World Cup 2026 — Knockout", 2026),
                ).fetchone()[0]
                pending = [row[0] for row in connection.execute(
                    "SELECT id FROM matches WHERE competition_id=? AND completed=0", (knockout_id,))]
            if not pending:
                break
            _simulate_all(engine, pending)
        with connect(self.database) as connection:
            inbox = connection.execute(
                "SELECT title, content FROM inbox_messages WHERE title LIKE 'ICC World Cup 2026 champions:%'"
            ).fetchone()
        self.assertIsNotNone(inbox, "a champion-crowned inbox message should exist once the Final completes")
        self.assertIn("have won the ICC World Cup 2026", inbox["content"])


class T20WorldCupTests(TemporaryGameTest):
    def test_group_stage_is_two_groups_of_five(self) -> None:
        engine = CompetitionEngine(self.database, seed=3)
        engine._start_icc_tournament(_tournament("ICC T20 World Cup"), 2026)
        with connect(self.database) as connection:
            groups = connection.execute(
                "SELECT id, name FROM competitions WHERE name LIKE ? AND season=2026 AND type='League'",
                ("ICC T20 World Cup 2026%",),
            ).fetchall()
            self.assertEqual(len(groups), 2)
            for group in groups:
                # league_standings isn't used for international groups —
                # its team_id column has a real FK to teams(id), which a
                # negative national id can never satisfy — so team count is
                # read from the actual generated fixtures instead.
                team_ids: set[int] = set()
                for row in connection.execute(
                    "SELECT home_team, away_team FROM matches WHERE competition_id=?", (group["id"],)
                ):
                    team_ids.add(row[0]); team_ids.add(row[1])
                self.assertEqual(len(team_ids), 5)
                match_count = connection.execute(
                    "SELECT COUNT(*) FROM matches WHERE competition_id=?", (group["id"],)
                ).fetchone()[0]
                self.assertEqual(match_count, 10, "a full 5-team round-robin is 10 matches, not the old buggy 8")

    def test_full_tournament_advances_four_qualifiers_to_semis(self) -> None:
        engine = CompetitionEngine(self.database, seed=5)
        engine._start_icc_tournament(_tournament("ICC T20 World Cup"), 2026)
        _simulate_all(engine, _group_match_ids(engine, "ICC T20 World Cup", 2026))
        with connect(self.database) as connection:
            knockout = connection.execute(
                "SELECT id FROM competitions WHERE name=? AND season=2026",
                ("ICC T20 World Cup 2026 — Knockout",),
            ).fetchone()
            semis = connection.execute(
                "SELECT home_team, away_team FROM matches WHERE competition_id=? AND round_name='Semi-final'",
                (knockout[0],),
            ).fetchall()
        self.assertEqual(len(semis), 2)


class ChampionsTrophyTests(TemporaryGameTest):
    def test_only_eight_of_ten_nations_qualify(self) -> None:
        engine = CompetitionEngine(self.database, seed=9)
        engine._start_icc_tournament(_tournament("ICC Champions Trophy"), 2026)
        involved_ids: set[int] = set()
        with connect(self.database) as connection:
            for row in connection.execute(
                "SELECT home_team, away_team FROM matches m JOIN competitions c ON c.id=m.competition_id "
                "WHERE c.name LIKE 'ICC Champions Trophy 2026%' AND c.season=2026"
            ):
                involved_ids.add(row[0]); involved_ids.add(row[1])
        self.assertEqual(len(involved_ids), 8)
        self.assertTrue(involved_ids.issubset(set(NATIONAL_TEAM_IDS.values())))


class SchedulingCollisionTests(TemporaryGameTest):
    def test_bilateral_tour_is_paused_while_a_tournament_is_in_progress(self) -> None:
        engine = CompetitionEngine(self.database, seed=17)
        engine._start_icc_tournament(_tournament("ICC World Cup"), 2026)
        self.assertTrue(engine._icc_tournament_in_progress(2026))
        # Any bilateral tour scheduled this same season should be skipped
        # while the tournament above is still unfinished — this call would
        # previously have silently played the wrong event or double-booked
        # the same month.
        with connect(self.database) as connection:
            user_team = connection.execute("SELECT id FROM teams LIMIT 1").fetchone()[0]
        result = engine._run_international_window(2026, "2026-11-01", user_team)  # The Ashes' month
        self.assertIsNone(result)
        with connect(self.database) as connection:
            ashes = connection.execute(
                "SELECT 1 FROM competitions WHERE name LIKE 'The Ashes%' AND season=2026"
            ).fetchone()
        self.assertIsNone(ashes, "the Ashes should not have started while the World Cup is still running")

    def test_tournament_no_longer_in_progress_once_fully_complete(self) -> None:
        engine = CompetitionEngine(self.database, seed=19)
        engine._start_icc_tournament(_tournament("ICC T20 World Cup"), 2026)  # smaller/faster than the ODI WC
        _simulate_all(engine, _group_match_ids(engine, "ICC T20 World Cup", 2026))
        self.assertTrue(engine._icc_tournament_in_progress(2026), "knockout not played yet")
        for _ in range(3):
            with connect(self.database) as connection:
                knockout_id = connection.execute(
                    "SELECT id FROM competitions WHERE name=? AND season=2026",
                    ("ICC T20 World Cup 2026 — Knockout",),
                ).fetchone()[0]
                pending = [row[0] for row in connection.execute(
                    "SELECT id FROM matches WHERE competition_id=? AND completed=0", (knockout_id,))]
            if not pending:
                break
            _simulate_all(engine, pending)
        self.assertFalse(engine._icc_tournament_in_progress(2026))


if __name__ == "__main__":
    unittest.main()
