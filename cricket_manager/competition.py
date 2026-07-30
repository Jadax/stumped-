"""Domestic league, cup, calendar, and season progression engine.

Phase 3 deliberately keeps match simulation statistical; the dedicated match
engine can later replace ``_simulate_result`` without changing competition data.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from database import (
    DEFAULT_DATABASE_PATH, add_financial_transaction, adjust_players_morale, adjust_team_morale,
    advance_scouting_assignments, age_staff_at_rollover, apply_daily_training, clear_expired_injuries,
    complete_due_facility_upgrades, connect, create_inbox_message, evaluate_board_objectives, fetch_player_records,
    fetch_players, generate_ai_transfer_offers, generate_job_offers, get_board_objectives, get_ground_info,
    record_board_confidence, record_honour, record_legend, record_player_performance, record_season_stats,
    set_board_objectives, recover_daily_fatigue, recruit_youth, store_job_offers,
)
from src.models.career import board_confidence, season_awards


class CompetitionEngine:
    """Own fixture creation, date advancement, tables, and season rollover."""

    #: Long-save stability (Phase 8): unconditional `recruit_youth(count=3)`
    #: every rollover with no size check made squads grow without bound —
    #: a 20-season stress test showed a 25-player squad reaching 59.
    #: Real clubs stop signing academy prospects once the squad is full;
    #: intake is now clamped so a squad never grows past this many.
    SQUAD_SIZE_CAP = 30

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_PATH, seed: int = 26042026):
        self.database_path = Path(database_path)
        self.rng = random.Random(seed)

    def ensure_season(self, season: int = 2026) -> None:
        """Create five league schedules and a knockout opening round once."""
        with connect(self.database_path) as connection:
            competition_ids = {}
            from src.models.league_config import LEAGUE_NAMES, LEAGUE_FORMATS
            for division in (1, 2, 3, 4, 5):
                name = LEAGUE_NAMES.get(division, f"Division {division}")
                row = connection.execute("SELECT id FROM competitions WHERE name=? AND season=?", (name, season)).fetchone()
                if row: competition_id = row[0]
                else:
                    competition_id = connection.execute(
                        "INSERT INTO competitions (name,type,season) VALUES (?,'League',?)", (name, season)
                    ).lastrowid
                competition_ids[division] = competition_id
                teams = [row[0] for row in connection.execute("SELECT id FROM teams WHERE division=? ORDER BY id", (division,))]
                connection.executemany(
                    "INSERT OR IGNORE INTO league_standings (competition_id,team_id) VALUES (?,?)",
                    [(competition_id, team_id) for team_id in teams],
                )
                existing = connection.execute("SELECT COUNT(*) FROM matches WHERE competition_id=?", (competition_id,)).fetchone()[0]
                if not existing:
                    match_format = LEAGUE_FORMATS.get(division, "T20")
                    self._insert_round_robin(connection, competition_id, teams, season, match_format)
                # Phase 2 seeded the opening user fixture on April 4. Keep the
                # first generated league round four days later to avoid a clash.
                connection.execute(
                    "UPDATE matches SET date=? WHERE competition_id=? AND date=? AND completed=0",
                    (date(season, 4, 8).isoformat(), competition_id, date(season, 4, 4).isoformat()),
                )

            cup_name = "Domestic Knockout Cup"
            cup = connection.execute("SELECT id FROM competitions WHERE name=? AND season=?", (cup_name, season)).fetchone()
            cup_id = cup[0] if cup else connection.execute(
                "INSERT INTO competitions (name,type,season) VALUES (?,'Cup',?)", (cup_name, season)
            ).lastrowid
            if connection.execute("SELECT COUNT(*) FROM matches WHERE competition_id=?", (cup_id,)).fetchone()[0] == 0:
                teams = [row[0] for row in connection.execute("SELECT id FROM teams ORDER BY id")]
                self.rng.shuffle(teams)
                cup_date = date(season, 5, 6)
                # Seed top teams with byes; remainder play opening round.
                # Ensure even number for pairing.
                bye_count = min(8, len(teams) // 4)
                bye_teams, teams = teams[:bye_count], teams[bye_count:]
                if len(teams) % 2:
                    teams = teams[:-1]  # drop one to make even
                connection.execute(
                    "INSERT OR REPLACE INTO game_state (key,value_json) VALUES (?,?)",
                    (f"cup_byes_{cup_id}", json.dumps(bye_teams)),
                )
                round_name = f"Round of {len(bye_teams) * 2}" if bye_teams else "Opening Round"
                for index in range(0, len(teams), 2):
                    home, away = teams[index:index + 2]
                    venue = connection.execute("SELECT name FROM teams WHERE id=?", (home,)).fetchone()[0] + " Ground"
                    connection.execute(
                        """INSERT INTO matches
                           (home_team,away_team,format,date,venue,completed,result_json,competition_id,round_name)
                           VALUES (?,?,'ODI',?,?,0,'{}',?,?)""",
                            (home, away, cup_date.isoformat(), venue, cup_id, round_name),
                    )
            # T20 Cup (additional knockout competition)
            t20_cup_name = "T20 Cup"
            t20_cup = connection.execute("SELECT id FROM competitions WHERE name=? AND season=?", (t20_cup_name, season)).fetchone()
            t20_cup_id = t20_cup[0] if t20_cup else connection.execute(
                "INSERT INTO competitions (name,type,season) VALUES (?,'Cup',?)", (t20_cup_name, season)
            ).lastrowid
            if connection.execute("SELECT COUNT(*) FROM matches WHERE competition_id=?", (t20_cup_id,)).fetchone()[0] == 0:
                t20_teams = [row[0] for row in connection.execute("SELECT id FROM teams ORDER BY id")]
                self.rng.shuffle(t20_teams)
                t20_date = date(season, 6, 15)
                bye_count = min(8, len(t20_teams) // 4)
                bye_teams, t20_teams = t20_teams[:bye_count], t20_teams[bye_count:]
                if len(t20_teams) % 2:
                    t20_teams = t20_teams[:-1]
                connection.execute(
                    "INSERT OR REPLACE INTO game_state (key,value_json) VALUES (?,?)",
                    (f"cup_byes_{t20_cup_id}", json.dumps(bye_teams)),
                )
                round_name = f"Round of {len(bye_teams) * 2}" if bye_teams else "Opening Round"
                for index in range(0, len(t20_teams), 2):
                    home, away = t20_teams[index:index + 2]
                    venue = connection.execute("SELECT name FROM teams WHERE id=?", (home,)).fetchone()[0] + " Ground"
                    connection.execute(
                        """INSERT INTO matches
                           (home_team,away_team,format,date,venue,completed,result_json,competition_id,round_name)
                           VALUES (?,?,'T20',?,?,0,'{}',?,?)""",
                            (home, away, t20_date.isoformat(), venue, t20_cup_id, round_name),
                    )

            user_team_id = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()[0]
            existing_objectives = connection.execute(
                "SELECT value_json FROM game_state WHERE key=?",
                (f"board_objectives_{user_team_id}",)
            ).fetchone()
            if not existing_objectives:
                rng = random.Random(f"board_objectives:{season}")
                target = rng.randint(4, 8)
                cash_min = rng.choice([75_000, 100_000, 150_000, 200_000])
                objectives = {"league_position": target, "minimum_cash": cash_min, "youth_developed": 0}
                obj_key = f"board_objectives_{user_team_id}"
                connection.execute(
                    """INSERT INTO game_state (key, value_json, updated_at)
                       VALUES (?, ?, CURRENT_TIMESTAMP)
                       ON CONFLICT(key) DO UPDATE SET
                           value_json = excluded.value_json,
                           updated_at = CURRENT_TIMESTAMP""",
                    (obj_key, json.dumps(objectives)),
                )
                _inbox_target = target
                _inbox_cash_min = cash_min
                _inbox_season = season
                _needs_objectives_message = True
            else:
                _needs_objectives_message = False
        if _needs_objectives_message:
            create_inbox_message(
                "HIGH", "Board expectations set",
                f"The board has outlined the following objectives for the {_inbox_season} season:\n\n"
                f"• Finish {_inbox_target} or higher in the league\n"
                f"• Maintain a minimum cash balance of £{_inbox_cash_min:,}\n\n"
                f"Meeting these targets will keep board confidence high. "
                f"Missing them will put your position under review.",
                timestamp=f"{date(_inbox_season, 4, 1).isoformat()} 09:00",
                database_path=self.database_path)

    def _insert_round_robin(self, connection, competition_id: int, teams: list[int], season: int, match_format: str = "T20") -> None:
        rotation = list(teams); rounds = []
        for round_index in range(len(teams) - 1):
            pairs = []
            for i in range(len(teams) // 2):
                home, away = rotation[i], rotation[-1 - i]
                if round_index % 2: home, away = away, home
                pairs.append((home, away))
            rounds.append(pairs)
            rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
        rounds += [[(away, home) for home, away in pairs] for pairs in rounds]
        start = date(season, 4, 8)
        for round_index, pairs in enumerate(rounds):
            match_date = start + timedelta(days=round_index * 5)
            for home, away in pairs:
                venue = connection.execute("SELECT name FROM teams WHERE id=?", (home,)).fetchone()[0] + " Ground"
                connection.execute(
                    """INSERT INTO matches
                       (home_team,away_team,format,date,venue,completed,result_json,competition_id,round_name)
                       VALUES (?,?,?,?,?,0,'{}',?,?)""",
                    (home, away, match_format, match_date.isoformat(), venue, competition_id, f"League Round {round_index + 1}"),
                )

    def advance_day(self, auto_sim_user: bool = False) -> dict[str, Any]:
        """Advance one date and run every scheduled daily/weekly/monthly hook."""
        with connect(self.database_path) as connection:
            user = connection.execute("SELECT * FROM user_data WHERE id=1").fetchone()
            team_id, old_date = user["current_team_id"], date.fromisoformat(user["current_date"])
            new_date = old_date + timedelta(days=1)
            connection.execute("UPDATE user_data SET current_date=? WHERE id=1", (new_date.isoformat(),))
        events: dict[str, Any] = {"date": new_date.isoformat(), "matches": [], "user_fixture": None, "training_points": 0}
        events["training_points"] = apply_daily_training(team_id, new_date.isoformat(), self.database_path)
        recover_daily_fatigue(self.database_path)
        clear_expired_injuries(new_date.isoformat(), self.database_path)
        for report in advance_scouting_assignments(new_date.isoformat(), self.database_path):
            create_inbox_message(
                "MEDIUM", f"Scouting report: {report['target_name']}",
                f"Your scout's assessment is in — estimated overall {report['estimated_overall']}, "
                f"potential {report['estimated_potential']} ({report['confidence']}% confidence).",
                timestamp=f"{new_date.isoformat()} 09:00", database_path=self.database_path)
        completed = complete_due_facility_upgrades(team_id, new_date.isoformat(), self.database_path)
        for facility in completed:
            create_inbox_message("MEDIUM", f"{facility} upgrade complete",
                                 f"The {facility.lower()} upgrade is complete and its benefits are now active.",
                                 timestamp=f"{new_date.isoformat()} 08:00", database_path=self.database_path)
        if new_date.weekday() == 0:
            with connect(self.database_path) as connection:
                wages = connection.execute("SELECT COALESCE(SUM(wage),0) FROM players WHERE team_id=?", (team_id,)).fetchone()[0]
            add_financial_transaction(team_id, new_date.isoformat(), "Wages", "EXPENSE", wages, "Weekly player wages", self.database_path)
        if new_date.day == 1:
            with connect(self.database_path) as connection:
                sponsor = connection.execute("SELECT monthly_value FROM sponsorships WHERE team_id=? AND status='ACTIVE' ORDER BY id DESC LIMIT 1", (team_id,)).fetchone()
            if sponsor:
                add_financial_transaction(team_id, new_date.isoformat(), "Sponsorships", "INCOME", sponsor[0], "Monthly sponsorship payment", self.database_path)
            self._send_monthly_pnl_report(team_id, new_date)
        if new_date.month == 7 and new_date.day == 15:
            self._mid_season_board_review(team_id, new_date)
        if new_date.day == 1:
            self._run_international_window(new_date.year, new_date.isoformat(), team_id)
        if new_date.weekday() == 6:
            for offer in generate_ai_transfer_offers(new_date.isoformat(), team_id, self.database_path):
                create_inbox_message(
                    "HIGH", f"Transfer offer: {offer['player_name']}",
                    f"{offer['to_team_name']} have offered £{offer['fee']:,} for {offer['player_name']} "
                    f"(£{offer['wage']:,}/week). You can accept or reject via the Offers screen.",
                    timestamp=f"{new_date.isoformat()} 10:00", database_path=self.database_path)
        with connect(self.database_path) as connection:
            fixtures = [dict(row) for row in connection.execute(
                "SELECT * FROM matches WHERE date=? AND completed=0", (new_date.isoformat(),)
            ).fetchall()]
        for fixture in fixtures:
            involves_user = team_id in (fixture["home_team"], fixture["away_team"])
            if involves_user and not auto_sim_user:
                events["user_fixture"] = fixture; continue
            result = self.simulate_fixture(fixture["id"]); events["matches"].append(result)
        if new_date > date(new_date.year, 9, 30):
            events["season_rollover"] = self.rollover_season(new_date.year)
        return events

    def _mid_season_board_review(self, team_id: int, current_date) -> None:
        """Send a mid-season progress update against board objectives."""
        evaluation = evaluate_board_objectives(team_id, self.database_path)
        objectives = evaluation["objectives"]
        progress = evaluation["progress"]
        lines = ["The board has reviewed the club's mid-season progress:\n"]
        league = progress["league_position"]
        if league["current"] is not None:
            status = "on track" if league["met"] else "behind target"
            lines.append(f"• League position: {league['current']} (target: {league['target']} or higher) — {status}")
        else:
            lines.append(f"• League position: No standings data yet (target: {league['target']} or higher)")
        cash = progress["cash_balance"]
        cash_status = "healthy" if cash["met"] else "below minimum"
        lines.append(f"• Cash balance: £{cash['current']:,} (minimum: £{cash['target']:,}) — {cash_status}")
        met_count = sum(1 for v in progress.values() if v.get("met"))
        total = len(progress)
        if met_count == total:
            lines.append("\nThe board is pleased with progress. Keep up the good work.")
            priority = "LOW"
        elif met_count == 0:
            lines.append("\nThe board is concerned about progress. Significant improvement is needed.")
            priority = "HIGH"
        else:
            lines.append("\nThe board urges improvement on targets that are behind schedule.")
            priority = "MEDIUM"
        create_inbox_message(priority, "Mid-season board review",
                             "\n".join(lines),
                             timestamp=f"{current_date.isoformat()} 09:00",
                             database_path=self.database_path)
        confidence = board_confidence(
            progress["league_position"]["current"] or 6, 12,
            objectives.get("league_position", 6),
            progress["cash_balance"]["current"]
        )
        record_board_confidence(team_id, confidence["score"], confidence["label"],
                                current_date.isoformat(), self.database_path)

    def _run_international_window(self, season: int, current_date: str, user_team_id: int) -> dict[str, Any] | None:
        """International cricket: bilateral tours and ICC tournaments.

        Runs at specific months defined in BILATERAL_TOURS and ICC_TOURNAMENTS.
        Each tour/tournament auto-selects the best XI per nation, plays out
        the full series, records performances, and notifies the user if any
        of their players were called up.
        """
        from datetime import date as _date
        month = _date.fromisoformat(current_date).month
        from database import select_national_xi
        from match_engine import Match
        from src.models.international import (INTERNATIONAL_CALLUP_MORALE_BONUS, national_team,
                                               get_tour_for_month, get_tournament_for_month)
        tour = get_tour_for_month(month)
        tournament = get_tournament_for_month(month)
        if not tour and not tournament:
            return None
        event_name = tour["name"] if tour else tournament["name"]
        with connect(self.database_path) as connection:
            already = connection.execute(
                "SELECT 1 FROM competitions WHERE name=? AND season=?", (f"{event_name} {season}", season)
            ).fetchone()
            if already:
                return None
            connection.execute("INSERT INTO competitions (name,type,season) VALUES (?,?,?)",
                               (f"{event_name} {season}", "International", season))
        if tour:
            home_nat, away_nat = tour["home"], tour["away"]
            series_length = tour["length"]
            match_format = tour["format"]
        else:
            from src.models.international import INTERNATIONAL_NATIONALITIES
            nations = self.rng.sample(INTERNATIONAL_NATIONALITIES, tournament["teams"])
            home_nat, away_nat = nations[0], nations[1]
            series_length = 1
            match_format = tournament["format"]
        home_team, away_team = national_team(home_nat), national_team(away_nat)
        home_xi = select_national_xi(home_nat, self.database_path)
        away_xi = select_national_xi(away_nat, self.database_path)
        if len(home_xi) < 11 or len(away_xi) < 11:
            return None
        called_up = home_xi + away_xi
        with connect(self.database_path) as connection:
            user_players = {row[0] for row in connection.execute(
                "SELECT id FROM players WHERE team_id=?", (user_team_id,)
            )}
        user_call_ups = [p for p in called_up if p["id"] in user_players]
        home_wins = away_wins = 0
        for game in range(series_length):
            match = Match(home_team, away_team, home_xi, away_xi, match_format, seed=self.rng.randint(0, 2**31),
                           ground_info=get_ground_info(home_team["id"], self.database_path))
            match.simulate()
            if match.winner_id == home_team["id"]: home_wins += 1
            elif match.winner_id == away_team["id"]: away_wins += 1
            for innings in match.innings:
                for player in innings.batting_order:
                    line = innings.batters[int(player["id"])]
                    if line.balls or line.dismissal != "did not bat":
                        record_player_performance(int(player["id"]), current_date, "International",
                                                  batting=vars(line).copy(), database_path=self.database_path)
                for player in innings.bowling_squad:
                    line = innings.bowlers[int(player["id"])]
                    if line.balls:
                        record_player_performance(int(player["id"]), current_date, "International",
                                                  bowling=vars(line).copy(), database_path=self.database_path)
        adjust_players_morale([p["id"] for p in called_up], INTERNATIONAL_CALLUP_MORALE_BONUS, self.database_path)
        series_result = (f"{home_team['name']} won the series {home_wins}-{away_wins}" if home_wins > away_wins
                         else f"{away_team['name']} won the series {away_wins}-{home_wins}" if away_wins > home_wins
                         else "The series was drawn")
        if user_call_ups:
            home_xi_ids = {p["id"] for p in home_xi}
            lines = []
            for player in user_call_ups:
                represents = home_team["name"] if player["id"] in home_xi_ids else away_team["name"]
                opponent = away_team["name"] if player["id"] in home_xi_ids else home_team["name"]
                lines.append(f"{player['name']} was called up to represent {represents} against {opponent}.")
            create_inbox_message(
                "HIGH", f"{event_name} — call-up!",
                "\n".join(lines) + f" {series_length}-match {match_format} series result: {series_result}.",
                timestamp=f"{current_date} 09:00", database_path=self.database_path)
        else:
            create_inbox_message(
                "LOW", f"{event_name} result",
                f"{home_team['name']} played {away_team['name']} in a {series_length}-match "
                f"{match_format} series. {series_result}.",
                timestamp=f"{current_date} 09:00", database_path=self.database_path)
        return {"home": home_team["name"], "away": away_team["name"], "home_wins": home_wins, "away_wins": away_wins,
                "event": event_name}

    def simulate_fixture(self, match_id: int) -> dict[str, Any]:
        with connect(self.database_path) as connection:
            match = connection.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()
            if not match or match["completed"]: return {}
            home_rating = connection.execute("SELECT AVG(overall) FROM players WHERE team_id=?", (match["home_team"],)).fetchone()[0]
            away_rating = connection.execute("SELECT AVG(overall) FROM players WHERE team_id=?", (match["away_team"],)).fetchone()[0]
        # The Hundred uses twenty five-ball sets. The lightweight simulator
        # stores completed length in sets, matching the live engine.
        overs = {"T10": 10, "T20": 20, "Hundred": 20, "ODI": 50}.get(match["format"], 50)
        home_runs = max(40, int(self.rng.gauss(overs * 6.8 + (home_rating - 60) * 1.7, overs * 1.2)))
        away_runs = max(40, int(self.rng.gauss(overs * 6.8 + (away_rating - 60) * 1.7, overs * 1.2)))
        home_wickets, away_wickets = self.rng.randint(2, 10), self.rng.randint(2, 10)
        winner = match["home_team"] if home_runs > away_runs else match["away_team"] if away_runs > home_runs else None
        result = {"home_runs": home_runs, "home_wickets": home_wickets, "away_runs": away_runs,
                  "away_wickets": away_wickets, "winner": winner, "tied": winner is None, "overs": overs}
        with connect(self.database_path) as connection:
            competition = connection.execute("SELECT type FROM competitions WHERE id=?", (match["competition_id"],)).fetchone()
            if competition and competition["type"] == "Cup" and result["tied"]:
                result["winner"] = self.rng.choice([match["home_team"], match["away_team"]]); result["tied"] = False
                if result["winner"] == match["home_team"]: result["home_runs"] += 1
                else: result["away_runs"] += 1
            connection.execute("UPDATE matches SET completed=1,result_json=? WHERE id=?", (json.dumps(result), match_id))
            if competition and competition["type"] == "League":
                self._update_table(connection, match, result)
        if competition and competition["type"] == "Cup":
            self._advance_cup_if_ready(match["competition_id"], match["round_name"], match["date"])
        return result

    def record_played_fixture(self, match_id: int, result: dict[str, Any]) -> dict[str, Any]:
        """Persist a result produced by the interactive ball-by-ball engine.

        ``simulate_fixture`` is intentionally lightweight for AI-only games;
        this companion method lets the live match use the same standings and
        cup progression pipeline without simulating the fixture a second time.
        """
        with connect(self.database_path) as connection:
            match = connection.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()
            if not match or match["completed"]:
                return {}
            payload = dict(result)
            payload.setdefault("winner", None)
            payload.setdefault("tied", payload["winner"] is None)
            payload.setdefault("overs", {"T10": 10, "T20": 20, "Hundred": 20, "ODI": 50}.get(match["format"], 50))
            connection.execute("UPDATE matches SET completed=1,result_json=? WHERE id=?", (json.dumps(payload), match_id))
            competition = connection.execute("SELECT type FROM competitions WHERE id=?", (match["competition_id"],)).fetchone()
            if competition and competition["type"] == "League":
                self._update_table(connection, match, payload)
        if competition and competition["type"] == "Cup":
            self._advance_cup_if_ready(match["competition_id"], match["round_name"], match["date"])
        return payload

    def _advance_cup_if_ready(self, competition_id: int, round_name: str, completed_date: str) -> None:
        next_names = {"Round of 32": "Round of 16", "Round of 16": "Quarter-final", "Quarter-final": "Semi-final", "Semi-final": "Final"}
        next_name = next_names.get(round_name)
        if not next_name: return
        with connect(self.database_path) as connection:
            matches = connection.execute(
                "SELECT * FROM matches WHERE competition_id=? AND round_name=?", (competition_id, round_name)
            ).fetchall()
            if not matches or any(not row["completed"] for row in matches): return
            if connection.execute("SELECT 1 FROM matches WHERE competition_id=? AND round_name=?", (competition_id, next_name)).fetchone(): return
            winners = [json.loads(row["result_json"]).get("winner") for row in matches]
            winners = [winner for winner in winners if winner]
            if round_name == "Round of 32":
                bye = connection.execute("SELECT value_json FROM game_state WHERE key=?", (f"cup_byes_{competition_id}",)).fetchone()
                if bye:
                    winners.extend(json.loads(bye[0]))
                    self.rng.shuffle(winners)
            next_date = date.fromisoformat(completed_date) + timedelta(days=14)
            for index in range(0, len(winners), 2):
                if index + 1 >= len(winners): break
                home, away = winners[index], winners[index + 1]
                venue = connection.execute("SELECT name FROM teams WHERE id=?", (home,)).fetchone()[0] + " Ground"
                connection.execute(
                    """INSERT INTO matches
                       (home_team,away_team,format,date,venue,completed,result_json,competition_id,round_name)
                       VALUES (?,?,'ODI',?,?,0,'{}',?,?)""",
                    (home, away, next_date.isoformat(), venue, competition_id, next_name),
                )

    @staticmethod
    def _update_table(connection, match, result: dict[str, Any]) -> None:
        for team_id, is_home in ((match["home_team"], True), (match["away_team"], False)):
            won = int(result["winner"] == team_id); tied = int(result["tied"]); lost = int(not won and not tied)
            team_runs = result["home_runs"] if is_home else result["away_runs"]
            opp_runs = result["away_runs"] if is_home else result["home_runs"]
            nrr_delta = (team_runs - opp_runs) / max(1, result["overs"])
            connection.execute(
                """UPDATE league_standings SET played=played+1,won=won+?,lost=lost+?,tied=tied+?,
                   points=points+?,net_run_rate=net_run_rate+? WHERE competition_id=? AND team_id=?""",
                (won, lost, tied, won * 2 + tied, nrr_delta, match["competition_id"], team_id),
            )

    def schedule_friendly(self, home_team: int, away_team: int, match_date: str, match_format: str = "T20") -> int:
        with connect(self.database_path) as connection:
            venue = connection.execute("SELECT name FROM teams WHERE id=?", (home_team,)).fetchone()[0] + " Ground"
            cursor = connection.execute(
                """INSERT INTO matches
                   (home_team,away_team,format,date,venue,completed,result_json,round_name)
                   VALUES (?,?,?,?,?,0,'{}','Friendly')""",
                (home_team, away_team, match_format, match_date, venue),
            )
            return int(cursor.lastrowid)

    def _send_monthly_pnl_report(self, team_id: int, new_date: date) -> None:
        """Deeper finances: a monthly profit-and-loss inbox digest."""
        month_end = new_date - timedelta(days=1)
        month_start = month_end.replace(day=1)
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """SELECT category, kind, SUM(amount) AS total FROM financial_log
                   WHERE team_id=? AND date BETWEEN ? AND ?
                   GROUP BY category, kind ORDER BY total DESC""",
                (team_id, month_start.isoformat(), month_end.isoformat()),
            ).fetchall()
            cash = connection.execute("SELECT cash FROM teams WHERE id=?", (team_id,)).fetchone()
        if not rows:
            return
        income = sum(r["total"] for r in rows if r["kind"] == "INCOME")
        expense = sum(r["total"] for r in rows if r["kind"] == "EXPENSE")
        net = income - expense
        lines = "\n".join(f"• {r['category']}: {'+' if r['kind'] == 'INCOME' else '-'}£{r['total']:,}" for r in rows)
        create_inbox_message(
            "MEDIUM", f"Monthly accounts — {month_start.strftime('%B %Y')}",
            f"Income £{income:,} • Expenses £{expense:,} • Net {'+' if net >= 0 else ''}£{net:,}\n"
            f"{lines}\nClosing balance: £{int(cash[0] if cash else 0):,}",
            timestamp=f"{new_date.isoformat()} 08:30", database_path=self.database_path)

    def _record_season_stats(self, season: int, user_team_id: int, position: int | None) -> None:
        """This season's leading run-scorer/wicket-taker, found by diffing
        cumulative player_records against a baseline snapshot taken at the
        previous rollover — avoids touching every match-recording call site
        just to tag performances with a season number."""
        baseline_key = f"season_baseline_{user_team_id}"
        with connect(self.database_path) as connection:
            squad = [dict(row) for row in connection.execute(
                "SELECT id, name FROM players WHERE team_id=?", (user_team_id,))]
            baseline_row = connection.execute(
                "SELECT value_json FROM game_state WHERE key=?", (baseline_key,)).fetchone()
            standings_row = connection.execute(
                """SELECT ls.played, ls.won, ls.lost FROM league_standings ls
                   JOIN competitions c ON c.id = ls.competition_id
                   WHERE c.season=? AND c.type='League' AND ls.team_id=?""",
                (season, user_team_id)).fetchone()
        baseline = json.loads(baseline_row[0]) if baseline_row else {}
        top_scorer_name, top_scorer_runs = "", 0
        top_wicket_name, top_wickets = "", 0
        new_baseline: dict[str, dict[str, int]] = {}
        for player in squad:
            totals = fetch_player_records(player["id"], self.database_path)
            runs = sum(int(context.get("runs", 0)) for context in totals.values())
            wickets = sum(int(context.get("wickets", 0)) for context in totals.values())
            new_baseline[str(player["id"])] = {"runs": runs, "wickets": wickets}
            prior = baseline.get(str(player["id"]), {})
            season_runs = runs - int(prior.get("runs", 0))
            season_wickets = wickets - int(prior.get("wickets", 0))
            if season_runs > top_scorer_runs:
                top_scorer_name, top_scorer_runs = player["name"], season_runs
            if season_wickets > top_wickets:
                top_wicket_name, top_wickets = player["name"], season_wickets
        with connect(self.database_path) as connection:
            connection.execute(
                """INSERT INTO game_state (key, value_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=CURRENT_TIMESTAMP""",
                (baseline_key, json.dumps(new_baseline)))
        played = standings_row["played"] if standings_row else 0
        won = standings_row["won"] if standings_row else 0
        lost = standings_row["lost"] if standings_row else 0
        record_season_stats(user_team_id, season, position, played, won, lost, top_scorer_name, top_scorer_runs,
                            top_wicket_name, top_wickets, date(season, 9, 30).isoformat(), self.database_path)

    def _award_season_honours(self, season: int, divisions: dict[int, list[int]],
                              cup_final, user_team_id: int) -> None:
        """Record champions in the honours cabinet and brief the user's inbox."""
        awarded_on = date(season, 9, 30).isoformat()
        stamp = f"{awarded_on} 10:00"
        winners: list[tuple[int, str]] = []
        if divisions.get(1): winners.append((int(divisions[1][0]), "Division 1 Champions"))
        if divisions.get(2): winners.append((int(divisions[2][0]), "Division 2 Champions"))
        if divisions.get(3): winners.append((int(divisions[3][0]), "Division 3 Champions"))
        if divisions.get(4): winners.append((int(divisions[4][0]), "Division 4 Champions"))
        if divisions.get(5): winners.append((int(divisions[5][0]), "Division 5 Champions"))
        if cup_final:
            try:
                cup_winner = json.loads(cup_final[0]).get("winner")
            except (ValueError, TypeError):
                cup_winner = None
            if cup_winner: winners.append((int(cup_winner), "Knockout Cup Winners"))
        for team_id, title in winners:
            record_honour(team_id, title, season, awarded_on, self.database_path)
            if team_id == user_team_id:
                create_inbox_message("HIGH", f"Silverware: {title}!",
                                     f"The board and supporters celebrate — the club are {title.lower()} "
                                     f"for the {season} season. The trophy joins the cabinet.",
                                     timestamp=stamp, database_path=self.database_path)
        with connect(self.database_path) as connection:
            teams = {row["id"]: row["name"] for row in connection.execute("SELECT id, name FROM teams")}
            budget_row = connection.execute("SELECT cash FROM teams WHERE id=?", (user_team_id,)).fetchone()
        pool: list[dict[str, Any]] = []
        for team_id, team_name in teams.items():
            for player in fetch_players(team_id, self.database_path):
                player["team_name"] = team_name
                pool.append(player)
        awards = season_awards(pool)
        if awards:
            lines = "\n".join(f"• {title}: {w['name']} ({w['team']})" for title, w in awards.items())
            create_inbox_message("MEDIUM", f"{season} Season Awards",
                                 f"The season's individual honours have been announced.\n{lines}",
                                 timestamp=stamp, database_path=self.database_path)
        position = None
        for division_teams in divisions.values():
            if user_team_id in division_teams:
                position = division_teams.index(user_team_id) + 1
                break
        self._record_season_stats(season, user_team_id, position)
        if position is not None:
            cash = int(budget_row[0] if budget_row and budget_row[0] is not None else 0)
            objectives = get_board_objectives(user_team_id, self.database_path)
            target = objectives.get("league_position", 6)
            verdict = board_confidence(position, 12, target, cash)
            texts = {"Delighted": "An outstanding season. The board could not be happier with your leadership.",
                     "Content": "A solid season. The board looks forward to further progress next year.",
                     "Under pressure": "A disappointing season. The board expects a clear improvement next year.",
                     "Ultimatum": "An unacceptable season. The board demands immediate results — your position is under review."}
            met_targets = []
            missed_targets = []
            if position <= target:
                met_targets.append(f"League position: {position} (target: {target} or higher)")
            else:
                missed_targets.append(f"League position: {position} (target: {target} or higher)")
            if cash >= objectives.get("minimum_cash", 0):
                met_targets.append(f"Cash balance: £{cash:,} (minimum: £{objectives.get('minimum_cash', 0):,})")
            else:
                missed_targets.append(f"Cash balance: £{cash:,} (minimum: £{objectives.get('minimum_cash', 0):,})")
            summary_parts = []
            if met_targets:
                summary_parts.append("Targets met:\n" + "\n".join(f"  ✓ {t}" for t in met_targets))
            if missed_targets:
                summary_parts.append("Targets missed:\n" + "\n".join(f"  ✗ {t}" for t in missed_targets))
            summary = "\n\n".join(summary_parts) if summary_parts else ""
            create_inbox_message("HIGH" if verdict["score"] < 40 else "MEDIUM", "Board season review",
                                 f"Final position: {position} of 12. {texts[verdict['label']]}\n\n{summary}",
                                 timestamp=stamp, database_path=self.database_path)
            record_board_confidence(user_team_id, verdict["score"], verdict["label"], stamp,
                                    self.database_path)
            from src.models.career import manager_reputation
            from database import fetch_honours as _fh
            with connect(self.database_path) as conn2:
                stats = conn2.execute(
                    "SELECT COALESCE(SUM(played),0) AS p, COALESCE(SUM(won),0) AS w FROM league_standings WHERE team_id=?",
                    (user_team_id,)
                ).fetchone()
            trophies = len(_fh(user_team_id, self.database_path))
            rep = manager_reputation(stats["p"], stats["w"], trophies)
            offers = generate_job_offers(user_team_id, rep["score"], self.database_path)
            if offers:
                store_job_offers(user_team_id, offers, self.database_path)
                create_inbox_message(
                    "MEDIUM", "Job offers available",
                    f"You have received {len(offers)} job offer{'s' if len(offers) != 1 else ''} "
                    f"from other clubs. Review them in the Career screen.",
                    timestamp=stamp, database_path=self.database_path)

    def rollover_season(self, season: int) -> dict[str, Any]:
        """Promote/relegate, age careers, retire declining veterans, and intake youth."""
        from src.models.league_config import LEAGUE_NAMES
        with connect(self.database_path) as connection:
            divisions = {}
            for division in (1, 2, 3, 4, 5):
                name = LEAGUE_NAMES.get(division, f"Division {division}")
                competition = connection.execute(
                    "SELECT id FROM competitions WHERE name=? AND season=?", (name, season)
                ).fetchone()
                if competition:
                    divisions[division] = [row[0] for row in connection.execute(
                        "SELECT team_id FROM league_standings WHERE competition_id=? "
                        "ORDER BY points DESC,won DESC,net_run_rate DESC",
                        (competition[0],),
                    )]
            # Guard against a division too small for a clean 2-up-2-down swap
            # (e.g. a modified league size) — promoting/relegating more teams
            # than exist, or the same team appearing in both lists, would
            # otherwise silently corrupt the standings on the next season.
            # Division 1 ↔ Division 2
            promotion_slots_d2 = min(2, len(divisions.get(2, [])) // 2)
            relegation_slots_d1 = min(2, len(divisions.get(1, [])) // 2)
            promoted_to_d1 = divisions.get(2, [])[:promotion_slots_d2]
            relegated_from_d1 = divisions.get(1, [])[-relegation_slots_d1:] if relegation_slots_d1 else []
            # Division 2 ↔ Division 3
            promotion_slots_d3 = min(2, len(divisions.get(3, [])) // 2)
            relegation_slots_d2 = min(2, len(divisions.get(2, [])) // 2)
            promoted_to_d2 = divisions.get(3, [])[:promotion_slots_d3]
            relegated_from_d2 = divisions.get(2, [])[-relegation_slots_d2:] if relegation_slots_d2 else []
            # Division 3 ↔ Division 4
            promotion_slots_d4 = min(2, len(divisions.get(4, [])) // 2)
            relegation_slots_d3 = min(2, len(divisions.get(3, [])) // 2)
            promoted_to_d3 = divisions.get(4, [])[:promotion_slots_d4]
            relegated_from_d3 = divisions.get(3, [])[-relegation_slots_d3:] if relegation_slots_d3 else []
            # Division 4 ↔ Division 5
            promotion_slots_d5 = min(2, len(divisions.get(5, [])) // 2)
            relegation_slots_d4 = min(2, len(divisions.get(4, [])) // 2)
            promoted_to_d4 = divisions.get(5, [])[:promotion_slots_d5]
            relegated_from_d4 = divisions.get(4, [])[-relegation_slots_d4:] if relegation_slots_d4 else []
            promoted = promoted_to_d1 + promoted_to_d2 + promoted_to_d3 + promoted_to_d4
            relegated = relegated_from_d1 + relegated_from_d2 + relegated_from_d3 + relegated_from_d4
            user_team_id = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()[0]
            cup_final = connection.execute(
                """SELECT m.result_json FROM matches m JOIN competitions c ON c.id = m.competition_id
                   WHERE c.type='Cup' AND c.season=? AND m.round_name LIKE '%Final%' AND m.completed=1
                   ORDER BY m.date DESC LIMIT 1""", (season,)
            ).fetchone()
        self._award_season_honours(season, divisions, cup_final, int(user_team_id))
        from src.models.morale import PROMOTION_MORALE_BONUS, RELEGATION_MORALE_PENALTY
        with connect(self.database_path) as connection:
            team_names = {row[0]: row[1] for row in connection.execute("SELECT id, name FROM teams")}
            # Apply promotions/relegations (order matters: move relegated first to avoid conflicts)
            for team_id in relegated_from_d1: connection.execute("UPDATE teams SET division=2 WHERE id=?", (team_id,))
            for team_id in relegated_from_d2: connection.execute("UPDATE teams SET division=3 WHERE id=?", (team_id,))
            for team_id in relegated_from_d3: connection.execute("UPDATE teams SET division=4 WHERE id=?", (team_id,))
            for team_id in relegated_from_d4: connection.execute("UPDATE teams SET division=5 WHERE id=?", (team_id,))
            for team_id in promoted_to_d1: connection.execute("UPDATE teams SET division=1 WHERE id=?", (team_id,))
            for team_id in promoted_to_d2: connection.execute("UPDATE teams SET division=2 WHERE id=?", (team_id,))
            for team_id in promoted_to_d3: connection.execute("UPDATE teams SET division=3 WHERE id=?", (team_id,))
            for team_id in promoted_to_d4: connection.execute("UPDATE teams SET division=4 WHERE id=?", (team_id,))
            connection.execute("UPDATE players SET age=age+1")
            candidates = [dict(row) for row in connection.execute(
                "SELECT id,name,nationality,role,overall,team_id,age FROM players")]
        # Real age-curve retirement (replacing a hard age>40 cutoff): negligible
        # before 33, rising through the late 30s, forced at 45 (players.age's
        # own CHECK constraint caps there, so this must never be optional).
        # overall<20 is a separate release path — a club releasing a player
        # who was never good enough, not a personal retirement decision.
        retirees = []
        for player in candidates:
            age, overall = player["age"], player["overall"]
            if overall < 20:
                player["reason"] = "released"
            elif age >= 45 or self.rng.random() < self._retirement_probability(age):
                player["reason"] = "retired"
            else:
                continue
            retirees.append(player)
        # Archived (and, for some retirees, converted to a staff role) before
        # the players row is deleted — player_records cascades on that
        # delete, so record_legend() must run first to snapshot it.
        for player in retirees:
            became_staff = False
            if player["reason"] == "retired" and player["team_id"] and self.rng.random() < .15:
                became_staff = self._convert_retiree_to_staff(player)
            player["became_staff"] = became_staff
            record_legend(player, team_names.get(player["team_id"], ""), player["age"], season,
                         date(season, 9, 30).isoformat(), player["reason"], became_staff, self.database_path)
        if retirees:
            with connect(self.database_path) as connection:
                connection.executemany("DELETE FROM players WHERE id=?", [(player["id"],) for player in retirees])
        # Every promoted/relegated squad, not just the user's — an AI club
        # that goes up or down should feel it too.
        for team_id in promoted: adjust_team_morale(team_id, PROMOTION_MORALE_BONUS, self.database_path)
        for team_id in relegated: adjust_team_morale(team_id, RELEGATION_MORALE_PENALTY, self.database_path)
        with connect(self.database_path) as connection:
            squad_sizes = dict(connection.execute("SELECT team_id, COUNT(*) FROM players GROUP BY team_id").fetchall())
            team_ids = [row[0] for row in connection.execute("SELECT id FROM teams ORDER BY id")]
        for team_id in team_ids:
            room = self.SQUAD_SIZE_CAP - squad_sizes.get(team_id, 0)
            if room > 0:
                recruit_youth(team_id, count=min(3, room), database_path=self.database_path)
        staff_result = age_staff_at_rollover(season, self.database_path)
        self.ensure_season(season + 1)
        with connect(self.database_path) as connection:
            connection.execute("UPDATE user_data SET current_date=? WHERE id=1", (date(season + 1, 4, 1).isoformat(),))
        self._announce_season_rollover(season, user_team_id, promoted, relegated, retirees, team_names)
        return {"promoted": promoted, "relegated": relegated, "retired": [p["name"] for p in retirees],
               "staff_retired": staff_result["retired"]}

    def _announce_season_rollover(self, season: int, user_team_id: int, promoted: list[int],
                                  relegated: list[int], retirees: list[dict[str, Any]],
                                  team_names: dict[int, str]) -> None:
        """Post the end-of-season summary to the inbox — previously computed
        by rollover_season and returned to the caller, but never actually
        shown to the user anywhere (promotion, relegation, and retirements
        all happened silently)."""
        stamp = f"{date(season, 9, 30).isoformat()} 18:00"
        if user_team_id in promoted:
            create_inbox_message("HIGH", "Promoted to Division 1!",
                                 f"{team_names.get(user_team_id, 'Your club')} finished in a promotion spot and "
                                 f"will play in Division 1 next season.", timestamp=stamp, database_path=self.database_path)
        elif user_team_id in relegated:
            create_inbox_message("HIGH", "Relegated to Division 2",
                                 f"{team_names.get(user_team_id, 'Your club')} finished in a relegation spot and "
                                 f"will play in Division 2 next season.", timestamp=stamp, database_path=self.database_path)
        if promoted or relegated:
            lines = []
            if promoted: lines.append("Promoted: " + ", ".join(team_names.get(t, "?") for t in promoted))
            if relegated: lines.append("Relegated: " + ", ".join(team_names.get(t, "?") for t in relegated))
            create_inbox_message("MEDIUM", "League promotion & relegation confirmed", " • ".join(lines),
                                 timestamp=stamp, database_path=self.database_path)
        user_departures = [player for player in retirees if player["team_id"] == user_team_id]
        if user_departures:
            retired = [p["name"] for p in user_departures if p["reason"] == "retired"]
            released = [p["name"] for p in user_departures if p["reason"] == "released"]
            became_staff = [p["name"] for p in user_departures if p.get("became_staff")]
            lines = []
            if retired: lines.append(f"Retired: {', '.join(retired)}")
            if released: lines.append(f"Released (below first-team standard): {', '.join(released)}")
            if became_staff: lines.append(f"Staying at the club in a coaching role: {', '.join(became_staff)}")
            lines.append("Check the Legends screen for their career record, and your squad for the gaps left.")
            create_inbox_message("HIGH", "Players have left your club", " • ".join(lines),
                                 timestamp=stamp, database_path=self.database_path)

    @staticmethod
    def _retirement_probability(age: int) -> float:
        """Real age curve, not a hard cutoff: negligible before 33, rising
        through the late 30s, effectively certain by 44 — 45 is a separate
        hard force in rollover_season (players.age's own CHECK constraint
        caps there, so that one must never be left to chance)."""
        if age < 33:
            return 0.0
        if age >= 44:
            return 0.95
        return min(0.95, ((age - 32) / 12) ** 1.6)

    def _convert_retiree_to_staff(self, player: dict[str, Any]) -> bool:
        """A retiring player occasionally stays on at their last club in a
        backroom role — real cricket precedent for recently retired players
        moving straight into coaching. Role is picked from their playing
        role, quality scaled from their final overall rather than a
        generic average appointment."""
        from src.models.staff import ROLES, generate_staff_member
        role_name = {"Batsman": "Batting Coach", "Bowler": "Bowling Coach",
                    "Wicketkeeper": "Fielding Coach", "All-Rounder": "Head Coach"}.get(player["role"], "Batting Coach")
        group = next(group for name, group, _ in ROLES if name == role_name)
        club_quality = 6.0 + player["overall"] * .08
        member = generate_staff_member(role_name, group, player["nationality"], player["name"],
                                       self.rng, club_quality)
        member["age"] = player["age"]
        with connect(self.database_path) as connection:
            connection.execute(
                """INSERT INTO staff (team_id, name, age, nationality, role, group_name,
                                      attributes_json, wage, contract_years_remaining)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (player["team_id"], member["name"], member["age"], member["nationality"], member["role"],
                 member["group_name"], json.dumps(member["attributes"]), member["wage"],
                 member["contract_years_remaining"]),
            )
        return True
