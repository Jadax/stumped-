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


class LongCareerBalanceTests(SavedWorldTest):
    """v5.3.1: a 30-season day-by-day soak exposed four slow leaks."""

    def test_regens_use_the_nationality_national_teams_select_from(self) -> None:
        from database import recruit_youth
        from src.models.international import INTERNATIONAL_NATIONALITIES
        team = self.query("SELECT id FROM teams WHERE id>0 ORDER BY id LIMIT 1")[0][0]
        created = recruit_youth(team, count=4, database_path=self.database)
        self.assertTrue(created)
        for player in created:
            self.assertIn(player["nationality"], INTERNATIONAL_NATIONALITIES)

    def test_old_saves_fold_country_names_back_to_demonyms(self) -> None:
        player_id = self.query("SELECT id FROM players LIMIT 1")[0][0]
        with connect(self.database) as connection:
            connection.execute("UPDATE players SET nationality='Australia' WHERE id=?", (player_id,))
        initialise_database(self.database)
        self.assertEqual(self.query("SELECT nationality FROM players WHERE id=?", player_id)[0][0], "Australian")

    def test_academy_calibre_follows_club_tier(self) -> None:
        from database import _youth_current_and_potential
        def mean_potential(division: int) -> float:
            rng = random.Random(division)
            values = [_youth_current_and_potential(2, rng, division)[1] for _ in range(1500)]
            return sum(values) / len(values)
        self.assertGreater(mean_potential(1) - mean_potential(5), 20)
        rng = random.Random(9)
        gems = [p for _, p in (_youth_current_and_potential(2, rng, 5) for _ in range(3000)) if p >= 85]
        self.assertTrue(gems, "a rare gem can still come through a small club")

    def test_central_funding_never_exceeds_a_clubs_own_costs(self) -> None:
        from src.models.club_economy import club_central_funding, funding_floor
        self.assertEqual(club_central_funding(500_000, 120_000, 400_000, 1), 120_000)
        self.assertEqual(club_central_funding(500_000, 900_000, 400_000, 1), 500_000)
        self.assertEqual(club_central_funding(500_000, 0, 400_000, 1), funding_floor(400_000, 1))

    def test_rich_ai_clubs_reinvest_surplus_cash(self) -> None:
        from src.models.club_economy import ai_weekly_reinvestment, AI_CASH_RESERVE
        self.assertEqual(ai_weekly_reinvestment(AI_CASH_RESERVE[5], 5), 0)
        self.assertGreater(ai_weekly_reinvestment(AI_CASH_RESERVE[5] + 10_000_000, 5), 0)

    def test_full_ai_squads_still_trade(self) -> None:
        user = self.query("SELECT current_team_id FROM user_data")[0][0]
        before = dict(self.query("SELECT team_id, COUNT(*) FROM players WHERE team_id>0 GROUP BY team_id"))
        # Every squad at the cap except a handful of lower-tier clubs with room.
        roomy = [row[0] for row in self.query(
            "SELECT id FROM teams WHERE division=5 AND id!=? ORDER BY id LIMIT 6", user)]
        with connect(self.database) as connection:
            for club in roomy:
                connection.execute("DELETE FROM players WHERE id IN (SELECT id FROM players WHERE team_id=? "
                                   "ORDER BY overall LIMIT 4)", (club,))
        deals = []
        for week in range(6):
            deals += run_ai_transfer_market(f"2026-05-{week * 4 + 3:02d}", user, max(before.values()),
                                            self.database, random.Random(week + 70))
        self.assertTrue(deals, "clubs at the squad cap must still be able to sign players")
        sizes = dict(self.query("SELECT team_id, COUNT(*) FROM players WHERE team_id>0 GROUP BY team_id"))
        self.assertLessEqual(max(sizes.values()), max(before.values()))

    def test_prime_players_do_not_drop_down_the_pyramid(self) -> None:
        user = self.query("SELECT current_team_id FROM user_data")[0][0]
        divisions = dict(self.query("SELECT id, division FROM teams WHERE id>0"))
        with connect(self.database) as connection:
            connection.execute("UPDATE teams SET cash=500000000 WHERE division>=3")
            connection.execute("UPDATE players SET transfer_listed=0, contract_years_remaining=3")
        deals = []
        for week in range(8):
            deals += run_ai_transfer_market(f"2026-06-{week * 3 + 1:02d}", user, 30, self.database,
                                            random.Random(week + 40))
        ages = dict(self.query("SELECT id, age FROM players"))
        for deal in deals:
            if ages.get(deal["player_id"], 40) < 30:
                self.assertLessEqual(divisions[deal["to_team"]], divisions[deal["from_team"]], deal)


class ClubEcosystemTests(SavedWorldTest):
    """v5.3.1: injuries, squad turnover, sponsorship and running costs for
    every club, not just the manager's."""

    def user(self) -> int:
        return self.query("SELECT current_team_id FROM user_data")[0][0]

    def test_ai_matches_cause_injuries(self) -> None:
        engine = CompetitionEngine(self.database, seed=5)
        engine.AI_INJURY_CHANCE = {key: 1.0 for key in engine.AI_INJURY_CHANCE}
        home, away = [row[0] for row in self.query(
            "SELECT id FROM teams WHERE id>0 AND id!=? ORDER BY id LIMIT 2", self.user())]
        with connect(self.database) as connection:
            match_id = connection.execute(
                "INSERT INTO matches (home_team, away_team, format, date, venue, round_name) "
                "VALUES (?,?,'T20','2026-05-01','Ground','Friendly')", (home, away)).lastrowid
        engine.simulate_fixture(match_id)
        injured_teams = {row[0] for row in self.query(
            "SELECT p.team_id FROM injuries i JOIN players p ON p.id=i.player_id WHERE i.active=1")}
        self.assertTrue({home, away} <= injured_teams)

    def test_injured_players_sit_out_the_ai_xi(self) -> None:
        engine = CompetitionEngine(self.database, seed=5)
        team = self.query("SELECT id FROM teams WHERE id>0 AND id!=? LIMIT 1", self.user())[0][0]
        best = self.query("SELECT id FROM players WHERE team_id=? AND academy_squad=0 ORDER BY overall DESC LIMIT 1",
                          team)[0][0]
        with connect(self.database) as connection:
            connection.execute("INSERT INTO injuries (player_id, severity, start_date, return_date, active) "
                               "VALUES (?, 'Major', '2026-04-01', '2026-08-01', 1)", (best,))
            xi = engine._available_xi(connection, team)
        self.assertNotIn(best, [p["id"] for p in xi])

    def test_ai_squads_are_trimmed_to_a_realistic_size(self) -> None:
        from database import AI_SQUAD_TARGET, manage_ai_squads, recruit_youth
        team = self.query("SELECT id FROM teams WHERE id>0 AND id!=? LIMIT 1", self.user())[0][0]
        for _ in range(3):
            recruit_youth(team, count=5, database_path=self.database)
        with connect(self.database) as connection:
            connection.execute("UPDATE players SET academy_squad=0 WHERE team_id=?", (team,))
        report = manage_ai_squads(2026, self.user(), 30, self.database, random.Random(3))
        self.assertGreater(report["released"], 0)
        self.assertLessEqual(self.query("SELECT COUNT(*) FROM players WHERE team_id=?", team)[0][0], AI_SQUAD_TARGET)
        user_size = self.query("SELECT COUNT(*) FROM players WHERE team_id=?", self.user())[0][0]
        self.assertGreater(user_size, 0, "the manager's own squad is never trimmed by the AI")

    def test_clubs_in_debt_cut_their_most_expensive_veterans(self) -> None:
        from database import manage_ai_squads
        team = self.query("SELECT id FROM teams WHERE id>0 AND id!=? LIMIT 1", self.user())[0][0]
        with connect(self.database) as connection:
            connection.execute("UPDATE teams SET cash=-5000000 WHERE id=?", (team,))
            connection.execute("UPDATE players SET age=31 WHERE id IN (SELECT id FROM players WHERE team_id=? "
                               "AND academy_squad=0 ORDER BY wage DESC LIMIT 2)", (team,))
        earners = [row[0] for row in self.query(
            "SELECT id FROM players WHERE team_id=? AND academy_squad=0 ORDER BY wage DESC LIMIT 2", team)]
        manage_ai_squads(2026, self.user(), 30, self.database, random.Random(4))
        remaining = {row[0] for row in self.query("SELECT id FROM players WHERE team_id=?", team)}
        self.assertFalse(set(earners) & remaining)

    def test_every_club_has_a_sponsor_worth_more_higher_up(self) -> None:
        from database import ensure_sponsorship_deals
        ensure_sponsorship_deals(2026, renew=True, database_path=self.database)
        by_division = dict(self.query(
            "SELECT t.division, AVG(s.monthly_value) FROM sponsorships s JOIN teams t ON t.id=s.team_id "
            "WHERE s.status='ACTIVE' GROUP BY t.division"))
        self.assertEqual(self.query("SELECT COUNT(*) FROM teams t WHERE t.id>0 AND NOT EXISTS "
                                    "(SELECT 1 FROM sponsorships s WHERE s.team_id=t.id AND s.status='ACTIVE')")[0][0], 0)
        self.assertGreater(by_division[1], 3 * by_division[5])

    def test_weekly_finances_charge_facility_upkeep(self) -> None:
        engine = CompetitionEngine(self.database, seed=5)
        engine._run_weekly_club_finances(self.user(), date(2026, 4, 6))
        self.assertEqual(self.query("SELECT COUNT(*) FROM financial_log WHERE team_id=? AND category='Facilities Upkeep'",
                                    self.user())[0][0], 1)


if __name__ == "__main__":
    unittest.main()
