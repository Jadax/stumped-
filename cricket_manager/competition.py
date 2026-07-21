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
    DEFAULT_DATABASE_PATH, add_financial_transaction, age_staff_at_rollover, apply_daily_training,
    clear_expired_injuries, complete_due_facility_upgrades, connect, create_inbox_message, fetch_players,
    record_honour, recruit_youth,
)
from src.models.career import board_confidence, season_awards


class CompetitionEngine:
    """Own fixture creation, date advancement, tables, and season rollover."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_PATH, seed: int = 26042026):
        self.database_path = Path(database_path)
        self.rng = random.Random(seed)

    def ensure_season(self, season: int = 2026) -> None:
        """Create two league schedules and a knockout opening round once."""
        with connect(self.database_path) as connection:
            competition_ids = {}
            for division in (1, 2):
                name = f"Domestic Division {division}"
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
                    self._insert_round_robin(connection, competition_id, teams, season)
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
                # A 24-club competition needs eight seeded byes to create a
                # conventional 16-team second round. The remaining sixteen
                # clubs contest the opening round.
                bye_teams, teams = teams[:8], teams[8:]
                connection.execute(
                    "INSERT OR REPLACE INTO game_state (key,value_json) VALUES (?,?)",
                    (f"cup_byes_{cup_id}", json.dumps(bye_teams)),
                )
                for index in range(0, len(teams), 2):
                    home, away = teams[index:index + 2]
                    venue = connection.execute("SELECT name FROM teams WHERE id=?", (home,)).fetchone()[0] + " Ground"
                    connection.execute(
                        """INSERT INTO matches
                           (home_team,away_team,format,date,venue,completed,result_json,competition_id,round_name)
                           VALUES (?,?,'ODI',?,?,0,'{}',?,'Round of 32')""",
                        (home, away, cup_date.isoformat(), venue, cup_id),
                    )

    def _insert_round_robin(self, connection, competition_id: int, teams: list[int], season: int) -> None:
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
                       VALUES (?,?,'T20',?,?,0,'{}',?,?)""",
                    (home, away, match_date.isoformat(), venue, competition_id, f"League Round {round_index + 1}"),
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
        clear_expired_injuries(new_date.isoformat(), self.database_path)
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

    def simulate_fixture(self, match_id: int) -> dict[str, Any]:
        with connect(self.database_path) as connection:
            match = connection.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()
            if not match or match["completed"]: return {}
            home_rating = connection.execute("SELECT AVG(overall) FROM players WHERE team_id=?", (match["home_team"],)).fetchone()[0]
            away_rating = connection.execute("SELECT AVG(overall) FROM players WHERE team_id=?", (match["away_team"],)).fetchone()[0]
        overs = 20 if match["format"] == "T20" else 50
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
            payload.setdefault("overs", 20 if match["format"] == "T20" else 50)
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

    def _award_season_honours(self, season: int, divisions: dict[int, list[int]],
                              cup_final, user_team_id: int) -> None:
        """Record champions in the honours cabinet and brief the user's inbox."""
        awarded_on = date(season, 9, 30).isoformat()
        stamp = f"{awarded_on} 10:00"
        winners: list[tuple[int, str]] = []
        if divisions.get(1): winners.append((int(divisions[1][0]), "Division 1 Champions"))
        if divisions.get(2): winners.append((int(divisions[2][0]), "Division 2 Champions"))
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
        if position is not None:
            cash = int(budget_row[0] if budget_row and budget_row[0] is not None else 0)
            verdict = board_confidence(position, 12, 6, cash)
            texts = {"Delighted": "An outstanding season. The board could not be happier with your leadership.",
                     "Content": "A solid season. The board looks forward to further progress next year.",
                     "Under pressure": "A disappointing season. The board expects a clear improvement next year.",
                     "Ultimatum": "An unacceptable season. The board demands immediate results — your position is under review."}
            create_inbox_message("HIGH" if verdict["score"] < 40 else "MEDIUM", "Board season review",
                                 f"Final position: {position}. {texts[verdict['label']]}",
                                 timestamp=stamp, database_path=self.database_path)

    def rollover_season(self, season: int) -> dict[str, Any]:
        """Promote/relegate, age careers, retire declining veterans, and intake youth."""
        with connect(self.database_path) as connection:
            divisions = {}
            for division in (1, 2):
                competition = connection.execute(
                    "SELECT id FROM competitions WHERE name=? AND season=?", (f"Domestic Division {division}", season)
                ).fetchone()
                if competition:
                    divisions[division] = [row[0] for row in connection.execute(
                        "SELECT team_id FROM league_standings WHERE competition_id=? ORDER BY points DESC,net_run_rate DESC",
                        (competition[0],),
                    )]
            promoted = divisions.get(2, [])[:2]; relegated = divisions.get(1, [])[-2:]
            user_team_id = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()[0]
            cup_final = connection.execute(
                """SELECT m.result_json FROM matches m JOIN competitions c ON c.id = m.competition_id
                   WHERE c.type='Cup' AND c.season=? AND m.round_name LIKE '%Final%' AND m.completed=1
                   ORDER BY m.date DESC LIMIT 1""", (season,)
            ).fetchone()
        self._award_season_honours(season, divisions, cup_final, int(user_team_id))
        with connect(self.database_path) as connection:
            for team_id in promoted: connection.execute("UPDATE teams SET division=1 WHERE id=?", (team_id,))
            for team_id in relegated: connection.execute("UPDATE teams SET division=2 WHERE id=?", (team_id,))
            connection.execute("UPDATE players SET age=age+1")
            retirees = [dict(row) for row in connection.execute("SELECT id,name FROM players WHERE age>40 OR overall<20")]
            if retirees:
                connection.executemany("DELETE FROM players WHERE id=?", [(player["id"],) for player in retirees])
        with connect(self.database_path) as connection:
            team_ids = [row[0] for row in connection.execute("SELECT id FROM teams ORDER BY id")]
        for team_id in team_ids: recruit_youth(team_id, count=3, database_path=self.database_path)
        age_staff_at_rollover(season, self.database_path)
        self.ensure_season(season + 1)
        with connect(self.database_path) as connection:
            connection.execute("UPDATE user_data SET current_date=? WHERE id=1", (date(season + 1, 4, 1).isoformat(),))
        return {"promoted": promoted, "relegated": relegated, "retired": [p["name"] for p in retirees]}
