"""v5.3.0 living-world continuity: a multi-season, day-by-day soak test of
the real advance_day path found that most of the world never actually
played — fixtures dated past the 30 September rollover, broken cup brackets,
eternal contracts, no AI transfers, and a rollover crash once any
transferred player retired. Each test pins one of those fixes."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import json
import random
import shutil
import tempfile
import unittest

from competition import CompetitionEngine, _cup_opening_round
from database import (connect, initialise_database, process_contract_expiries, run_ai_transfer_market,
                      get_cup_bracket)
from src.models.international import ICC_TOURNAMENTS, get_tournament_for_month, tournament_held_in

_TEMPLATE: Path | None = None


def _fresh_save(directory: str) -> Path:
    """Copy one seeded world per test module (seeding takes seconds)."""
    global _TEMPLATE
    if _TEMPLATE is None:
        template_dir = tempfile.mkdtemp()
        _TEMPLATE = Path(template_dir) / "template.db"
        initialise_database(_TEMPLATE)
    target = Path(directory) / "save.db"
    shutil.copy(_TEMPLATE, target)
    return target


class SavedWorldTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = _fresh_save(self.directory.name)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def query(self, sql: str, *args):
        with connect(self.database) as connection:
            return [tuple(row) for row in connection.execute(sql, args).fetchall()]


class SeasonScheduleTests(SavedWorldTest):
    @classmethod
    def setUpClass(cls) -> None:
        cls._dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.shared = _fresh_save(cls._dir.name)
        CompetitionEngine(cls.shared, seed=3).ensure_season(2026)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._dir.cleanup()

    def shared_query(self, sql: str, *args):
        with connect(self.shared) as connection:
            return [tuple(row) for row in connection.execute(sql, args).fetchall()]

    def test_every_domestic_fixture_falls_inside_the_playable_season(self) -> None:
        late = self.shared_query(
            "SELECT c.name, COUNT(*) FROM matches m JOIN competitions c ON c.id=m.competition_id "
            "WHERE c.season=2026 AND m.date>'2026-09-30' GROUP BY c.id")
        self.assertEqual(late, [], "fixtures after the 30 September rollover are never played")

    def test_no_club_is_ever_double_booked_on_one_day(self) -> None:
        clashes = self.shared_query(
            "SELECT t, d FROM (SELECT home_team t, date d FROM matches UNION ALL "
            "SELECT away_team, date FROM matches) WHERE t>0 GROUP BY t, d HAVING COUNT(*)>1 LIMIT 5")
        self.assertEqual(clashes, [])

    def test_nation_competitions_are_scheduled_in_season(self) -> None:
        nation = self.shared_query(
            "SELECT COUNT(*), MAX(m.date) FROM matches m JOIN competitions c ON c.id=m.competition_id "
            "JOIN leagues l ON l.name=c.name WHERE c.season=2026")
        self.assertGreater(nation[0][0], 0)
        self.assertLessEqual(nation[0][1], "2026-09-30")


class CupBracketTests(SavedWorldTest):
    def test_opening_round_plus_byes_is_a_power_of_two(self) -> None:
        for size in (5, 11, 16, 28, 100):
            playing, byes, _ = _cup_opening_round(list(range(size)))
            self.assertEqual(len(playing) % 2, 0)
            field = len(playing) // 2 + len(byes)
            self.assertEqual(field & (field - 1), 0, f"{size} clubs -> {field} is not a power of two")
            self.assertEqual(len(playing) + len(byes), size, "nobody may be dropped from the draw")

    def test_hundred_club_cup_reaches_exactly_one_final_with_byes_playing(self) -> None:
        engine = CompetitionEngine(self.database, seed=5)
        engine.ensure_season(2026)
        cup = self.query("SELECT id FROM competitions WHERE name='Domestic Knockout Cup' AND season=2026")[0][0]
        byes = json.loads(self.query("SELECT value_json FROM game_state WHERE key=?", f"cup_byes_{cup}")[0][0])
        for _ in range(10):
            pending = [row[0] for row in self.query(
                "SELECT id FROM matches WHERE competition_id=? AND completed=0", cup)]
            if not pending:
                break
            for match_id in pending:
                engine.simulate_fixture(match_id)
        finals = self.query("SELECT COUNT(*) FROM matches WHERE competition_id=? AND round_name='Final'", cup)
        self.assertEqual(finals[0][0], 1)
        played_by_byes = self.query(
            f"SELECT COUNT(*) FROM matches WHERE competition_id=? AND round_name!='Preliminary Round' "
            f"AND (home_team IN ({','.join('?' * len(byes))}) OR away_team IN ({','.join('?' * len(byes))}))",
            cup, *byes, *byes)
        self.assertGreater(played_by_byes[0][0], 0, "bye teams must re-enter the draw")
        self.assertEqual(get_cup_bracket(self.database)["rounds"][-1], "Final")

    def test_later_rounds_keep_the_competition_format(self) -> None:
        engine = CompetitionEngine(self.database, seed=6)
        engine.ensure_season(2026)
        cup = self.query("SELECT id FROM competitions WHERE name='T20 Cup' AND season=2026")[0][0]
        for match_id, in self.query("SELECT id FROM matches WHERE competition_id=?", cup):
            engine.simulate_fixture(match_id)
        formats = {row[0] for row in self.query("SELECT format FROM matches WHERE competition_id=?", cup)}
        self.assertEqual(formats, {"T20"})


class IccCadenceTests(unittest.TestCase):
    def test_real_world_cycle(self) -> None:
        by_name = {t["name"]: t for t in ICC_TOURNAMENTS}
        self.assertTrue(tournament_held_in(by_name["ICC T20 World Cup"], 2026))
        self.assertFalse(tournament_held_in(by_name["ICC T20 World Cup"], 2027))
        held_odi = [y for y in range(2026, 2035) if tournament_held_in(by_name["ICC World Cup"], y)]
        self.assertEqual(held_odi, [2027, 2031])
        self.assertIsNone(get_tournament_for_month(by_name["ICC Champions Trophy"]["month"], 2026))

    def test_every_tournament_group_stage_ends_inside_the_season(self) -> None:
        for tournament in ICC_TOURNAMENTS:
            size = tournament["team_count"] // tournament["group_count"]
            matches = size * (size - 1) // 2
            last_day = date(2026, tournament["month"], 1).toordinal() + matches * tournament.get("day_gap", 2)
            self.assertLess(last_day + 21, date(2026, 9, 30).toordinal(), tournament["name"])


class ContractLifecycleTests(SavedWorldTest):
    def user_team(self) -> int:
        return self.query("SELECT current_team_id FROM user_data")[0][0]

    def test_contracts_run_down_each_rollover(self) -> None:
        before = dict(self.query("SELECT id, contract_years_remaining FROM players "
                                 "WHERE team_id IS NOT NULL AND academy_squad=0 AND contract_years_remaining>=3"))
        process_contract_expiries(2026, self.user_team(), 30, self.database, random.Random(1))
        after = dict(self.query("SELECT id, contract_years_remaining FROM players"))
        sample = [pid for pid in before if pid in after][:20]
        self.assertTrue(sample)
        for pid in sample:
            self.assertEqual(after[pid], before[pid] - 1)

    def test_users_unrenewed_player_leaves_and_renewed_player_stays(self) -> None:
        user = self.user_team()
        leaving, staying = [row[0] for row in self.query(
            "SELECT id FROM players WHERE team_id=? AND academy_squad=0 ORDER BY id LIMIT 2", user)]
        with connect(self.database) as connection:
            connection.execute("UPDATE players SET contract_years_remaining=1 WHERE id=?", (leaving,))
            connection.execute("UPDATE players SET contract_years_remaining=3 WHERE id=?", (staying,))
        report = process_contract_expiries(2026, user, 30, self.database, random.Random(2))
        owners = dict(self.query("SELECT id, team_id FROM players WHERE id IN (?,?)", leaving, staying))
        self.assertNotEqual(owners.get(leaving), user)
        self.assertEqual(owners[staying], user)
        self.assertTrue(report["user_departures"])

    def test_no_senior_contract_is_left_at_zero(self) -> None:
        with connect(self.database) as connection:
            connection.execute("UPDATE players SET contract_years_remaining=1 WHERE id % 3 = 0")
        process_contract_expiries(2026, self.user_team(), 30, self.database, random.Random(3))
        self.assertEqual(self.query(
            "SELECT COUNT(*) FROM players WHERE team_id IS NOT NULL AND contract_years_remaining<=0")[0][0], 0)


class TransferredPlayerRetirementTests(SavedWorldTest):
    def test_rollover_survives_a_transferred_player_retiring(self) -> None:
        engine = CompetitionEngine(self.database, seed=1)
        engine.ensure_season(2026)
        player_id, team_id = self.query("SELECT id, team_id FROM players WHERE team_id IS NOT NULL LIMIT 1")[0]
        with connect(self.database) as connection:
            connection.execute("INSERT INTO transfers (player_id, from_team, to_team, fee, date, status) "
                               "VALUES (?,?,?,0,'2026-05-01','COMPLETED')", (player_id, team_id, team_id))
            connection.execute("UPDATE players SET age=44 WHERE id=?", (player_id,))
        engine.rollover_season(2026)
        self.assertEqual(self.query("SELECT COUNT(*) FROM players WHERE id=?", player_id)[0][0], 0)
        self.assertEqual(self.query(
            "SELECT COUNT(*) FROM transfers WHERE player_id IS NULL AND date='2026-05-01'")[0][0], 1,
            "the transfer history row survives with the player archived")


class AiTransferMarketTests(SavedWorldTest):
    def test_ai_clubs_complete_real_transfers_through_the_ledger(self) -> None:
        user = self.query("SELECT current_team_id FROM user_data")[0][0]
        deals = []
        for week in range(6):
            deals += run_ai_transfer_market(f"2026-05-{week * 4 + 3:02d}", user, 30, self.database,
                                            random.Random(week))
        self.assertTrue(deals, "the AI world should trade players")
        for deal in deals:
            self.assertNotIn(user, (deal["from_team"], deal["to_team"]))
        ledger = self.query("SELECT COUNT(*) FROM financial_log WHERE category='Transfers'")[0][0]
        self.assertEqual(ledger, 2 * len(deals))


class AdvanceDayCatchUpTests(SavedWorldTest):
    def test_ai_fixture_on_the_rollover_landing_day_is_played(self) -> None:
        engine = CompetitionEngine(self.database, seed=2)
        current, user = self.query('SELECT "current_date", current_team_id FROM user_data')[0]
        home, away = [row[0] for row in self.query(
            "SELECT id FROM teams WHERE id NOT IN (?) ORDER BY id DESC LIMIT 2", user)]
        with connect(self.database) as connection:
            match_id = connection.execute(
                "INSERT INTO matches (home_team, away_team, format, date, venue, round_name) "
                "VALUES (?,?,'T20',?,'Test Ground','Friendly')", (home, away, current)).lastrowid
        engine.advance_day()
        self.assertEqual(self.query("SELECT completed FROM matches WHERE id=?", match_id)[0][0], 1)

    def test_previous_season_orphans_never_block_the_manager(self) -> None:
        engine = CompetitionEngine(self.database, seed=4)
        current, user = self.query('SELECT "current_date", current_team_id FROM user_data')[0]
        last_october = date(date.fromisoformat(current).year - 1, 10, 15).isoformat()
        opponent = self.query("SELECT id FROM teams WHERE id!=? LIMIT 1", user)[0][0]
        with connect(self.database) as connection:
            connection.execute("DELETE FROM matches WHERE completed=0")
            connection.execute("INSERT INTO matches (home_team, away_team, format, date, venue) "
                               "VALUES (?,?,'T20',?,'Old Ground')", (user, opponent, last_october))
        events = engine.advance_day()
        self.assertFalse(events.get("blocked"))
        self.assertEqual(self.query("SELECT COUNT(*) FROM matches WHERE date=?", last_october)[0][0], 0)


if __name__ == "__main__":
    unittest.main()
