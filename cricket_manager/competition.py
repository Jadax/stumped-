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
    DEFAULT_DATABASE_PATH, add_financial_transaction, advance_scouting_assignments, age_staff_at_rollover,
    apply_daily_training, clear_expired_injuries, complete_due_facility_upgrades, connect, create_inbox_message,
    evaluate_board_objectives, fetch_players, generate_ai_transfer_offers, generate_job_offers,
    get_board_objectives, record_board_confidence, record_honour, set_board_objectives, recover_daily_fatigue,
    recruit_youth, store_job_offers,
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
        with connect(self.database_path) as connection:
            divisions = {}
            for division in (1, 2):
                competition = connection.execute(
                    "SELECT id FROM competitions WHERE name=? AND season=?", (f"Domestic Division {division}", season)
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
            promotion_slots = min(2, len(divisions.get(2, [])) // 2)
            relegation_slots = min(2, len(divisions.get(1, [])) // 2)
            promoted = divisions.get(2, [])[:promotion_slots]
            relegated = divisions.get(1, [])[-relegation_slots:] if relegation_slots else []
            user_team_id = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()[0]
            cup_final = connection.execute(
                """SELECT m.result_json FROM matches m JOIN competitions c ON c.id = m.competition_id
                   WHERE c.type='Cup' AND c.season=? AND m.round_name LIKE '%Final%' AND m.completed=1
                   ORDER BY m.date DESC LIMIT 1""", (season,)
            ).fetchone()
        self._award_season_honours(season, divisions, cup_final, int(user_team_id))
        with connect(self.database_path) as connection:
            team_names = {row[0]: row[1] for row in connection.execute("SELECT id, name FROM teams")}
            for team_id in promoted: connection.execute("UPDATE teams SET division=1 WHERE id=?", (team_id,))
            for team_id in relegated: connection.execute("UPDATE teams SET division=2 WHERE id=?", (team_id,))
            connection.execute("UPDATE players SET age=age+1")
            retirees = [dict(row) for row in connection.execute(
                "SELECT id,name,team_id FROM players WHERE age>40 OR overall<20")]
            if retirees:
                connection.executemany("DELETE FROM players WHERE id=?", [(player["id"],) for player in retirees])
        with connect(self.database_path) as connection:
            team_ids = [row[0] for row in connection.execute("SELECT id FROM teams ORDER BY id")]
        for team_id in team_ids: recruit_youth(team_id, count=3, database_path=self.database_path)
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
        user_retirees = [player["name"] for player in retirees if player["team_id"] == user_team_id]
        if user_retirees:
            create_inbox_message("HIGH", "Players have left your club",
                                 f"{', '.join(user_retirees)} {'has' if len(user_retirees) == 1 else 'have'} "
                                 f"retired or been released at the end of the season. Check your squad on the "
                                 f"Squad screen.", timestamp=stamp, database_path=self.database_path)
