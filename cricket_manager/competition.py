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
    advance_scouting_assignments, age_staff_at_rollover, apply_daily_training, award_manager_xp, clear_expired_injuries,
    complete_due_facility_upgrades, connect, create_inbox_message, evaluate_board_objectives, fetch_player_records,
    fetch_players, generate_ai_transfer_offers, generate_job_offers, get_board_objectives, get_ground_info,
    has_manager_perk, record_board_confidence, record_honour, record_legend, record_player_performance, record_season_stats,
    set_board_objectives, recover_daily_fatigue, recruit_youth, store_job_offers, advance_auctions,
    ensure_weekly_challenge,
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
        # v4.57.0: the per-nation domestic structure (src/models/
        # nations_config.py, v4.56.0) was built but never actually called
        # from anywhere — every season now also gets its real nation
        # competitions generated alongside the existing global pyramid.
        # Additive/coexisting (not yet a replacement — see docs/CURRENT.md):
        # different competition names/ids, and ensure_per_nation_season
        # staggers each nation's own competitions internally so a team is
        # never double-booked within its nation, but a team's global
        # fixtures and its nation fixtures are still two independent
        # schedules layered on the same April-September window.
        self.ensure_per_nation_season(season)

    def _insert_round_robin(self, connection, competition_id: int, teams: list[int], season: int,
                             match_format: str = "T20", start: date | None = None) -> None:
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
        if start is None:
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

    # v4.56.0: per-nation domestic competitions. Each league-playing nation
    # gets its own First Class/Test league, 50-over (List A) competition and
    # T20 competition — the "same league structure as Cricket Captain"
    # feature. Generated additively from src/models/nations_config.py's
    # NATION_COMPETITIONS registry; existing global competitions/saves are
    # untouched, so existing saves keep loading and the old 5-division flow
    # still works. A nation's teams are its own generated clubs (grouped by
    # country_id), playing double round-robins within the nation. Competition
    # names are stored as "Nation Name" (e.g. "England County Championship")
    # so they can never collide with the existing global league rows that
    # reuse the same bare names ("County Championship" is Division 1's
    # existing global league today).
    def ensure_per_nation_season(self, season: int = 2026) -> None:
        from src.models.nations_config import NATION_COMPETITIONS
        from src.models.nations_config import FRANCHISE_LEAGUES
        nation_label = {"england": "England", "australia": "Australia", "india": "India",
                        "pakistan": "Pakistan", "south_africa": "South Africa",
                        "new_zealand": "New Zealand", "sri_lanka": "Sri Lanka",
                        "bangladesh": "Bangladesh", "west_indies": "West Indies",
                        "zimbabwe": "Zimbabwe"}
        with connect(self.database_path) as connection:
            for country_id, competitions in NATION_COMPETITIONS.items():
                teams = [row[0] for row in connection.execute(
                    "SELECT id FROM teams WHERE country_id=? ORDER BY id", (country_id,)
                )]
                if len(teams) < 4:
                    continue
                self._ensure_rivalry(connection, country_id, teams)
                label = nation_label.get(country_id, country_id.title())
                # v4.57.0: each of a nation's own "league"-kind competitions
                # (e.g. a Test-format first-class league AND a separate T20
                # league) used to all start on the same date(season,4,8) —
                # real fixture-clash double-booking for any team playing in
                # more than one. `cursor` staggers each subsequent
                # competition to start after the previous one's longest
                # division finishes (+1 round's gap), so one team is never
                # scheduled twice on the same day.
                # v4.60.3: a real, screenshot-confirmed bug — this cursor
                # used to always start at date(season,4,8), the exact same
                # date the legacy global 5-division pyramid's own fixtures
                # start (see ensure_season). Since a team's global division
                # and its nation league are independently randomized
                # round-robins over overlapping team pools, they could (and
                # did) pick the same opponent for the same team on the same
                # calendar day. Both systems remain deliberately separate
                # (see docs/CURRENT.md — nation leagues are additive, not
                # yet a replacement), but this nation's cursor now starts
                # strictly after every one of its teams' own global-division
                # fixtures for this season have concluded, so the two
                # schedules can never collide on a date for the same team.
                placeholders = ",".join("?" * len(teams))
                latest_global = connection.execute(
                    f"""SELECT MAX(m.date) FROM matches m JOIN competitions c ON c.id = m.competition_id
                        WHERE c.type='League' AND c.season=?
                          AND (m.home_team IN ({placeholders}) OR m.away_team IN ({placeholders}))""",
                    (season, *teams, *teams),
                ).fetchone()[0]
                cursor = date(season, 4, 8)
                if latest_global:
                    cursor = max(cursor, date.fromisoformat(latest_global) + timedelta(days=5))
                for spec in competitions:
                    if spec.get("kind") == "cup":
                        continue
                    comp_name = f"{label} {spec['name']}"
                    row = connection.execute(
                        "SELECT id FROM competitions WHERE name=? AND season=?", (comp_name, season)
                    ).fetchone()
                    if row:
                        existing_count = connection.execute(
                            "SELECT COUNT(*) FROM matches WHERE competition_id=?", (row[0],)
                        ).fetchone()[0]
                        if existing_count:
                            continue
                        comp_id = row[0]
                    else:
                        comp_id = connection.execute(
                            "INSERT INTO competitions (name,type,season) VALUES (?,'League',?)",
                            (comp_name, season),
                        ).lastrowid
                    connection.executemany(
                        "INSERT OR IGNORE INTO league_standings (competition_id,team_id) VALUES (?,?)",
                        [(comp_id, team_id) for team_id in teams],
                    )
                    division_count = max(1, spec.get("divisions", 1))
                    div_teams = self._nation_division_chunks(connection, teams, division_count)
                    max_rounds = 0
                    for chunk in div_teams:
                        if len(chunk) < 2:
                            continue
                        self._insert_round_robin(connection, comp_id, chunk, season, spec["format"], start=cursor)
                        max_rounds = max(max_rounds, 2 * (len(chunk) - 1))
                    if max_rounds:
                        cursor = cursor + timedelta(days=(max_rounds + 1) * 5)
                    connection.execute(
                        """INSERT INTO leagues (country_id,name,format,kind,divisions,promotion,relegation,season)
                           VALUES (?,?,?,?,?,?,?,?)
                           ON CONFLICT(name) DO UPDATE SET format=excluded.format,kind=excluded.kind,
                             divisions=excluded.divisions,promotion=excluded.promotion,
                             relegation=excluded.relegation,season=excluded.season""",
                        (country_id, f"{label} {spec['name']}", spec["format"], spec.get("kind", "league"),
                         division_count, spec.get("promotion", 0), spec.get("relegation", 0), season),
                    )
                # Optional franchise league rows are recorded so the engine
                # can draft shared-pool squads later (v4.56.x follow-up).
                franchise = FRANCHISE_LEAGUES.get(country_id)
                if franchise:
                    connection.execute(
                        """INSERT INTO leagues (country_id,name,format,kind,divisions,promotion,relegation,season)
                           VALUES (?,?,?,?,1,0,0,?)
                           ON CONFLICT(name) DO UPDATE SET season=excluded.season""",
                        (country_id, f"{label} {franchise['name']}", franchise["format"],
                         "franchise", season),
                    )

    def _nation_division_chunks(self, connection, teams: list[int], division_count: int) -> list[list[int]]:
        """Group a nation's teams into `division_count` tiers for its
        multi-division domestic leagues (e.g. County Championship Div 1/2).

        Unlike the old blind `_split_divisions(teams, n)` id-order chunking
        (which re-derived the exact same split every season, so promotion/
        relegation had nothing real to move teams between), this reads each
        team's persisted `teams.nation_division` tier. The first time a
        nation's multi-division league is generated (`nation_division` still
        NULL for these teams), it seeds an initial id-order split and
        persists it — every later season reads back whatever
        `rollover_season`'s nation promotion/relegation last wrote there.
        """
        if division_count <= 1:
            return [teams]
        placeholders = ",".join("?" * len(teams))
        rows = connection.execute(
            f"SELECT id, nation_division FROM teams WHERE id IN ({placeholders})", teams
        ).fetchall()
        assigned = {row[0]: row[1] for row in rows}
        if any(assigned.get(team_id) is None for team_id in teams):
            chunks = _split_divisions(sorted(teams), division_count)
            connection.executemany(
                "UPDATE teams SET nation_division=? WHERE id=?",
                [(tier, team_id) for tier, chunk in enumerate(chunks, start=1) for team_id in chunk],
            )
            return chunks
        tiers: dict[int, list[int]] = {}
        for team_id in teams:
            tiers.setdefault(assigned[team_id], []).append(team_id)
        return [tiers[tier] for tier in sorted(tiers) if len(tiers[tier]) >= 2]

    def _ensure_rivalry(self, connection, country_id: str, team_ids: list[int]) -> None:
        """v4.59.0: seed one derby pairing per nation, once — the two
        highest-cash clubs in that nation's own team pool, a real proxy for
        "big club" already used elsewhere (`_team_quality_modifier`). Purely
        additive/idempotent: does nothing once a nation already has a row."""
        existing = connection.execute("SELECT 1 FROM rivalries WHERE country_id=?", (country_id,)).fetchone()
        if existing:
            return
        placeholders = ",".join("?" * len(team_ids))
        ranked = connection.execute(
            f"SELECT id FROM teams WHERE id IN ({placeholders}) ORDER BY cash DESC LIMIT 2", team_ids
        ).fetchall()
        if len(ranked) < 2:
            return
        team_a, team_b = sorted((ranked[0][0], ranked[1][0]))
        connection.execute(
            "INSERT OR IGNORE INTO rivalries (team_a,team_b,country_id,intensity) VALUES (?,?,?,0)",
            (team_a, team_b, country_id),
        )

    def _record_rivalry_result(self, match, result: dict[str, Any]) -> None:
        """v4.59.0: if the two teams in this fixture are a seeded rivalry
        pairing, bump its intensity and write a permanent narrative event —
        called from both AI-simulated (`simulate_fixture`) and live user
        (`record_played_fixture`) match completion, so a derby means the
        same thing regardless of who played it."""
        from database import fetch_rivalry_for_team, record_narrative_event
        home_id, away_id = int(match["home_team"]), int(match["away_team"])
        rivalry = fetch_rivalry_for_team(home_id, self.database_path)
        if not rivalry or away_id not in (rivalry["team_a"], rivalry["team_b"]):
            return
        with connect(self.database_path) as connection:
            connection.execute("UPDATE rivalries SET intensity=intensity+1 WHERE id=?", (rivalry["id"],))
            names = {row[0]: row[1] for row in connection.execute(
                "SELECT id, name FROM teams WHERE id IN (?,?)", (home_id, away_id))}
        winner = result.get("winner")
        if winner is None:
            summary = f"{names.get(home_id, '?')} and {names.get(away_id, '?')} shared the honours in another tense derby."
        else:
            loser_id = away_id if winner == home_id else home_id
            summary = f"{names.get(winner, '?')} got the better of great rivals {names.get(loser_id, '?')} in this season's derby."
        record_narrative_event(match["date"], "RIVALRY", "Derby day", summary,
                               team_id=home_id, importance=3, database_path=self.database_path)

    def advance_day(self, auto_sim_user: bool = False) -> dict[str, Any]:
        """Advance one date and run every scheduled daily/weekly/monthly hook.

        v4.23.0 fix: the date used to advance unconditionally even when a
        fixture involving the user's own team was sitting unresolved —
        below, a user fixture is only ever flagged in events["user_fixture"]
        for whatever the NEW date happens to be, and never revisited later
        (the daily fixture query is `date=?`, not `date<=?`). A second
        Advance Day press before the user actually played that match moved
        the date past it, permanently orphaning the fixture (real bug: user
        reported the date advancing "but the rest stayed the same"). Now,
        before touching the date at all, block on any already-due,
        unresolved user fixture and hand it back again instead of silently
        skipping over it."""
        with connect(self.database_path) as connection:
            user = connection.execute("SELECT * FROM user_data WHERE id=1").fetchone()
            team_id, old_date = user["current_team_id"], date.fromisoformat(user["current_date"])
            if not auto_sim_user:
                pending = connection.execute(
                    "SELECT * FROM matches WHERE completed=0 AND date<=? AND (home_team=? OR away_team=?) "
                    "ORDER BY date LIMIT 1",
                    (old_date.isoformat(), team_id, team_id),
                ).fetchone()
                if pending:
                    return {"date": old_date.isoformat(), "matches": [], "user_fixture": dict(pending),
                            "training_points": 0, "blocked": True}
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
        # v4.65.0: the Weekly Challenge (roadmap.json's daily_tournaments
        # item) — a fresh optional challenge offered every Monday.
        if new_date.weekday() == 0:
            new_challenge = ensure_weekly_challenge(team_id, new_date.isoformat(), self.database_path)
            if new_challenge:
                create_inbox_message(
                    "LOW", "Weekly Challenge available",
                    f"A new Weekly Challenge is ready — take on {new_challenge['opponent_name']} for a cash "
                    f"reward. Optional, no risk to your real fixtures.",
                    timestamp=f"{new_date.isoformat()} 08:00", database_path=self.database_path)
        # v4.63.0: live player auctions — daily tick so AI bids and
        # deadline resolutions happen on the actual in-game date, not just
        # once a week like the AI transfer-offer sweep above (an auction
        # with a real countdown needs real daily movement).
        for result in advance_auctions(new_date.isoformat(), self.database_path):
            if result["outcome"] == "sold" and team_id in (result.get("seller_team_id"), result.get("buyer_team_id")):
                if team_id == result["seller_team_id"]:
                    create_inbox_message(
                        "HIGH", f"Auction sold: {result['player_name']}",
                        f"{result['player_name']} was sold to {result['buyer_name']} for £{result['fee']:,} "
                        f"when the auction closed.", timestamp=f"{new_date.isoformat()} 17:00",
                        database_path=self.database_path)
                else:
                    create_inbox_message(
                        "HIGH", f"Auction won: {result['player_name']}",
                        f"Your bid won the auction for {result['player_name']} — £{result['fee']:,} "
                        f"paid to {result['seller_name']}.", timestamp=f"{new_date.isoformat()} 17:00",
                        database_path=self.database_path)
            elif result["outcome"] == "unsold" and team_id == result.get("seller_team_id"):
                create_inbox_message(
                    "MEDIUM", f"Auction closed: {result['player_name']} unsold",
                    f"No bid met the reserve price for {result['player_name']}. "
                    f"The player remains transfer-listed if you want to try again.",
                    timestamp=f"{new_date.isoformat()} 17:00", database_path=self.database_path)
        with connect(self.database_path) as connection:
            fixtures = [dict(row) for row in connection.execute(
                "SELECT * FROM matches WHERE date=? AND completed=0", (new_date.isoformat(),)
            ).fetchall()]
        for fixture in fixtures:
            involves_user = team_id in (fixture["home_team"], fixture["away_team"])
            if involves_user and not auto_sim_user:
                events["user_fixture"] = fixture; continue
            # A negative team id is a synthetic national team (see
            # src/models/international.py) — simulate_fixture()'s lightweight
            # AI-only path reads `players.team_id`, which no player ever has
            # set to a negative id, so international fixtures need the full
            # Match-engine path instead (same engine bilateral tours already
            # use, now shared with ICC tournament group/knockout matches).
            if fixture["home_team"] < 0 or fixture["away_team"] < 0:
                result = self._simulate_international_fixture(fixture["id"])
            else:
                result = self.simulate_fixture(fixture["id"])
            events["matches"].append(result)
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
            award_manager_xp(20, "Mid-season objectives on track", self.database_path)
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
        Both now start real dated fixtures (see _start_icc_tournament()/
        _start_bilateral_tour()) simulated day by day via advance_day()'s
        existing fixture loop, same as every other competition type,
        instead of resolving synchronously in one in-memory call. A
        bilateral tour is paused while an ICC tournament is in progress,
        matching real cricket calendars and fixing a real bug: the two
        systems used to silently collide on shared months, dropping the
        tournament entirely that year.
        """
        from datetime import date as _date
        month = _date.fromisoformat(current_date).month
        from src.models.international import get_tour_for_month, get_tournament_for_month
        tournament = get_tournament_for_month(month)
        if tournament is not None:
            with connect(self.database_path) as connection:
                already = connection.execute(
                    "SELECT 1 FROM competitions WHERE name LIKE ? AND season=?",
                    (f"{tournament['name']} {season}%", season),
                ).fetchone()
            if not already:
                self._start_icc_tournament(tournament, season)
            return None
        tour = get_tour_for_month(month)
        if tour is None:
            return None
        if self._icc_tournament_in_progress(season):
            return None
        return self._start_bilateral_tour(tour, season, current_date, user_team_id)

    def _start_bilateral_tour(self, tour: dict[str, Any], season: int, current_date: str,
                              user_team_id: int) -> dict[str, Any] | None:
        """Creates a real, dated fixture per game in the series (type=
        'International' competition, round_name 'Match 1'..'Match N') instead
        of resolving the whole tour synchronously in one in-memory loop —
        each match is then simulated day by day through advance_day()'s
        existing fixture loop, same as everything else, leaving a real
        result history behind instead of just a one-off inbox summary.
        The call-up announcement fires immediately (the selection is real
        news the day the tour is announced); the series-result summary
        fires once every match is actually complete, via
        _advance_tour_if_ready()."""
        from database import select_national_xi
        from src.models.international import national_team
        event_name = tour["name"]
        with connect(self.database_path) as connection:
            already = connection.execute(
                "SELECT 1 FROM competitions WHERE name=? AND season=?", (f"{event_name} {season}", season)
            ).fetchone()
        if already:
            return None
        home_nat, away_nat = tour["home"], tour["away"]
        series_length = tour["length"]
        match_format = tour["format"]
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
        # Real cricket tour pacing: a Test needs a rest day either side of
        # up to 5 days' play; ODIs/T20Is turn around faster.
        gap_days = {"Test": 7, "ODI": 4, "T20": 3}.get(match_format, 4)
        start_date = date.fromisoformat(current_date)
        with connect(self.database_path) as connection:
            comp_id = connection.execute(
                "INSERT INTO competitions (name,type,season) VALUES (?,?,?)",
                (f"{event_name} {season}", "International", season),
            ).lastrowid
            for game_index in range(series_length):
                match_date = start_date + timedelta(days=game_index * gap_days)
                venue = self._venue_for_team(connection, home_team["id"])
                connection.execute(
                    """INSERT INTO matches
                       (home_team,away_team,format,date,venue,completed,result_json,
                        competition_id,round_name)
                       VALUES (?,?,?,?,?,0,'{}',?,?)""",
                    (home_team["id"], away_team["id"], match_format, match_date.isoformat(), venue,
                     comp_id, f"Match {game_index + 1}"),
                )
        if user_call_ups:
            home_xi_ids = {p["id"] for p in home_xi}
            lines = []
            for player in user_call_ups:
                represents = home_team["name"] if player["id"] in home_xi_ids else away_team["name"]
                opponent = away_team["name"] if player["id"] in home_xi_ids else home_team["name"]
                lines.append(f"{player['name']} has been called up to represent {represents} against {opponent}.")
            create_inbox_message(
                "HIGH", f"{event_name} — call-up!",
                "\n".join(lines) + f" The {series_length}-match {match_format} series begins today.",
                timestamp=f"{current_date} 09:00", database_path=self.database_path)
        else:
            create_inbox_message(
                "LOW", f"{event_name} begins",
                f"{home_team['name']} host {away_team['name']} in a {series_length}-match {match_format} series, "
                "starting today.",
                timestamp=f"{current_date} 09:00", database_path=self.database_path)
        return {"home": home_team["name"], "away": away_team["name"], "event": event_name}

    def _advance_tour_if_ready(self, competition_id: int, current_date: str) -> None:
        """Once every match in a bilateral tour's series is complete,
        tally the result from the persisted matches.result_json rows and
        post the series-result summary — mirrors the announcement this
        project already made when tours resolved synchronously, just
        triggered by real match completion instead of an in-memory loop."""
        with connect(self.database_path) as connection:
            comp = connection.execute("SELECT name, type FROM competitions WHERE id=?", (competition_id,)).fetchone()
            if not comp or comp["type"] != "International":
                return
            matches = connection.execute(
                "SELECT home_team, away_team, format, completed, result_json FROM matches WHERE competition_id=?",
                (competition_id,),
            ).fetchall()
        if not matches or any(not row["completed"] for row in matches):
            return
        from src.models.international import NATIONAL_TEAM_NAMES_BY_ID
        home_id, away_id = matches[0]["home_team"], matches[0]["away_team"]
        home_name = NATIONAL_TEAM_NAMES_BY_ID.get(home_id, "Home")
        away_name = NATIONAL_TEAM_NAMES_BY_ID.get(away_id, "Away")
        home_wins = away_wins = 0
        for row in matches:
            result = json.loads(row["result_json"])
            if result.get("winner") == home_id: home_wins += 1
            elif result.get("winner") == away_id: away_wins += 1
        series_result = (f"{home_name} won the series {home_wins}-{away_wins}" if home_wins > away_wins
                         else f"{away_name} won the series {away_wins}-{home_wins}" if away_wins > home_wins
                         else "The series was drawn")
        create_inbox_message(
            "MEDIUM", f"{comp['name']} — series result",
            f"{home_name} played {away_name} in a {len(matches)}-match {matches[0]['format']} series. "
            f"{series_result}.",
            timestamp=f"{current_date} 18:00", database_path=self.database_path)

    def _national_xi_strength(self, nationality: str) -> float:
        """Average overall of a nation's current best XI — used only to
        rank the 2 nations that sit out the Champions Trophy, mirroring
        real ODI-ranking-based qualification without needing a real
        ranking system of our own."""
        from database import select_national_xi
        xi = select_national_xi(nationality, self.database_path)
        return sum(p.get("overall", 0) for p in xi) / len(xi) if xi else 0.0

    def _icc_tournament_in_progress(self, season: int) -> bool:
        """True if any of this season's ICC tournament competitions
        (group or knockout) still has an unplayed match — used to pause
        bilateral tours while a World Cup/Champions Trophy is running."""
        from src.models.international import ICC_TOURNAMENTS
        with connect(self.database_path) as connection:
            for tournament_def in ICC_TOURNAMENTS:
                rows = connection.execute(
                    "SELECT id FROM competitions WHERE name LIKE ? AND season=?",
                    (f"{tournament_def['name']} {season}%", season),
                ).fetchall()
                if not rows:
                    continue
                comp_ids = [row[0] for row in rows]
                placeholders = ",".join("?" for _ in comp_ids)
                unfinished = connection.execute(
                    f"SELECT COUNT(*) FROM matches WHERE competition_id IN ({placeholders}) AND completed=0",
                    comp_ids,
                ).fetchone()[0]
                if unfinished > 0:
                    return True
        return False

    def _start_icc_tournament(self, tournament_def: dict[str, Any], season: int) -> None:
        """Create a real group stage for an ICC tournament: group-per-
        competition (type='League', so the existing standings pipeline
        just works), league_standings seeded, and dated round-robin
        fixtures — the same shape database.py's create_custom_tournament
        already uses for club teams, adapted for the negative national
        team ids. Actual match simulation happens later via advance_day()'s
        existing daily fixture loop, not synchronously here."""
        from database import _generate_round_robin
        from src.models.international import INTERNATIONAL_NATIONALITIES, NATIONAL_TEAM_IDS
        team_count = tournament_def["team_count"]
        group_count = tournament_def["group_count"]
        match_format = tournament_def["format"]
        tournament_name = tournament_def["name"]
        if team_count < len(INTERNATIONAL_NATIONALITIES):
            nationalities = sorted(INTERNATIONAL_NATIONALITIES,
                                   key=lambda nat: -self._national_xi_strength(nat))[:team_count]
        else:
            nationalities = list(INTERNATIONAL_NATIONALITIES)
        self.rng.shuffle(nationalities)
        team_ids = [NATIONAL_TEAM_IDS[nat] for nat in nationalities]
        groups: dict[int, list[int]] = {i: [] for i in range(group_count)}
        for index, team_id in enumerate(team_ids):
            groups[index % group_count].append(team_id)
        start_date = date(season, tournament_def["month"], 1)
        with connect(self.database_path) as connection:
            for group_index, group_team_ids in groups.items():
                group_label = chr(65 + group_index) if group_count > 1 else None
                round_label = f"Group {group_label}" if group_label else "Group Stage"
                comp_name = f"{tournament_name} {season} — {round_label}"
                comp_id = connection.execute(
                    "INSERT INTO competitions (name, type, season) VALUES (?, 'League', ?)",
                    (comp_name, season),
                ).lastrowid
                # No league_standings seed here — its team_id column has a
                # real FK to teams(id), which a negative national id can
                # never satisfy (and creating fake "team" rows for nations
                # would leak them into every real club-oriented screen:
                # Transfer Market, Career Team Selection, etc.). Group
                # standings are instead computed live from match results —
                # see _international_group_standings(), the same "derive
                # from matches.result_json, don't store a duplicate table"
                # approach fetch_club_records() already uses for real clubs.
                for pair_index, (home, away) in enumerate(_generate_round_robin(group_team_ids, home_away=False)):
                    match_date = start_date + timedelta(days=pair_index * 2)
                    venue = self._venue_for_team(connection, home)
                    connection.execute(
                        """INSERT INTO matches
                           (home_team,away_team,format,date,venue,completed,result_json,
                            competition_id,round_name)
                           VALUES (?,?,?,?,?,0,'{}',?,?)""",
                        (home, away, match_format, match_date.isoformat(), venue, comp_id, round_label),
                    )
        create_inbox_message(
            "MEDIUM", f"{tournament_name} {season} begins",
            f"The {tournament_name} gets underway today with {len(team_ids)} nations competing across "
            f"{group_count} group{'s' if group_count > 1 else ''}. Follow results on the National Team screen.",
            timestamp=f"{start_date.isoformat()} 09:00", database_path=self.database_path)

    @staticmethod
    def _international_group_standings(connection, competition_id: int) -> list[int]:
        """Team ids for an ICC tournament group, ranked by points then net
        run rate, computed live from completed match results — see the
        comment in _start_icc_tournament for why this doesn't use the
        league_standings table the way a real club competition would."""
        matches = connection.execute(
            "SELECT home_team, away_team, result_json FROM matches WHERE competition_id=? AND completed=1",
            (competition_id,),
        ).fetchall()
        points: dict[int, int] = {}
        nrr: dict[int, float] = {}
        for row in matches:
            result = json.loads(row["result_json"])
            overs = max(1, result.get("overs", 1))
            for team_id, is_home in ((row["home_team"], True), (row["away_team"], False)):
                points.setdefault(team_id, 0)
                nrr.setdefault(team_id, 0.0)
                if result.get("winner") == team_id:
                    points[team_id] += 2
                elif result.get("tied"):
                    points[team_id] += 1
                team_runs = result["home_runs"] if is_home else result["away_runs"]
                opp_runs = result["away_runs"] if is_home else result["home_runs"]
                nrr[team_id] += (team_runs - opp_runs) / overs
        return sorted(points.keys(), key=lambda team_id: (-points[team_id], -nrr[team_id]))

    def _advance_icc_group_stage_if_ready(self, competition_id: int, completed_date: str) -> None:
        """Once every group in an ICC tournament has finished, seed the
        knockout bracket from each group's top finishers (by
        league_standings order) as a new 'Cup'-type competition — from
        there, the existing _advance_cup_if_ready() (already fixed to
        handle negative national ids) takes over the rest of the bracket
        for free, exactly as it does for the Domestic Knockout Cup."""
        from database import _knockout_round_name
        from src.models.international import ICC_TOURNAMENTS
        with connect(self.database_path) as connection:
            comp_row = connection.execute(
                "SELECT name, season, type FROM competitions WHERE id=?", (competition_id,)
            ).fetchone()
            if not comp_row or comp_row["type"] != "League":
                return
            season = comp_row["season"]
            tournament_def = next(
                (t for t in ICC_TOURNAMENTS if comp_row["name"].startswith(f"{t['name']} {season}")), None)
            if tournament_def is None:
                return
            prefix = f"{tournament_def['name']} {season}"
            sibling_rows = connection.execute(
                "SELECT id FROM competitions WHERE name LIKE ? AND season=? AND type='League'",
                (f"{prefix}%", season),
            ).fetchall()
            sibling_ids = [row[0] for row in sibling_rows]
            placeholders = ",".join("?" for _ in sibling_ids)
            unfinished = connection.execute(
                f"SELECT COUNT(*) FROM matches WHERE competition_id IN ({placeholders}) AND completed=0",
                sibling_ids,
            ).fetchone()[0]
            if unfinished > 0:
                return
            if connection.execute(
                "SELECT 1 FROM competitions WHERE name=? AND season=?", (f"{prefix} — Knockout", season)
            ).fetchone():
                return
            qualifiers: list[int] = []
            for comp_id in sibling_ids:
                ranked = self._international_group_standings(connection, comp_id)
                qualifiers.extend(ranked[:tournament_def["advance_per_group"]])
            if len(qualifiers) < 2:
                return
            self.rng.shuffle(qualifiers)
            knockout_comp_id = connection.execute(
                "INSERT INTO competitions (name, type, season) VALUES (?, 'Cup', ?)",
                (f"{prefix} — Knockout", season),
            ).lastrowid
            round_name = _knockout_round_name(len(qualifiers))
            knockout_date = date.fromisoformat(completed_date) + timedelta(days=7)
            for index in range(0, len(qualifiers), 2):
                if index + 1 >= len(qualifiers):
                    break
                home, away = qualifiers[index], qualifiers[index + 1]
                venue = self._venue_for_team(connection, home)
                connection.execute(
                    """INSERT INTO matches
                       (home_team,away_team,format,date,venue,completed,result_json,
                        competition_id,round_name)
                       VALUES (?,?,?,?,?,0,'{}',?,?)""",
                    (home, away, tournament_def["format"], knockout_date.isoformat(), venue,
                     knockout_comp_id, round_name),
                )
        create_inbox_message(
            "MEDIUM", f"{tournament_def['name']} — group stage complete",
            f"The group stage is over. {round_name} fixtures have been confirmed.",
            timestamp=f"{completed_date} 09:00", database_path=self.database_path)

    def _announce_icc_champion_if_final(self, competition_id: int, round_name: str, home_team: dict[str, Any],
                                        away_team: dict[str, Any], result: dict[str, Any], current_date: str) -> None:
        """Posts a champion-crowned inbox message once an ICC tournament's
        Final actually completes — the one piece of real "progression" an
        instant single-match hack could never have shown."""
        if round_name != "Final":
            return
        with connect(self.database_path) as connection:
            comp = connection.execute("SELECT name, type FROM competitions WHERE id=?", (competition_id,)).fetchone()
        if not comp or comp["type"] != "Cup" or "— Knockout" not in comp["name"]:
            return
        champion = (home_team["name"] if result["winner"] == home_team["id"]
                   else away_team["name"] if result["winner"] == away_team["id"] else None)
        if not champion:
            return
        runner_up = away_team["name"] if champion == home_team["name"] else home_team["name"]
        tournament_label = comp["name"].replace(" — Knockout", "")
        create_inbox_message(
            "HIGH", f"{tournament_label} champions: {champion}!",
            f"{champion} have won the {tournament_label}, beating {runner_up} in the final "
            f"({result['home_runs']}-{result['home_wickets']} vs {result['away_runs']}-{result['away_wickets']}).",
            timestamp=f"{current_date} 20:00", database_path=self.database_path)

    def _simulate_international_fixture(self, match_id: int) -> dict[str, Any]:
        """Runs a real Match for a persisted international fixture (home/
        away are the negative synthetic national ids from
        src.models.international — see NATIONAL_TEAM_IDS), then persists
        it through the same record_played_fixture() pipeline every other
        match type already uses (standings update if League, automatic
        next-round creation via _advance_cup_if_ready if Cup) instead of
        duplicating that logic."""
        from database import select_national_xi
        from match_engine import Match
        from src.models.international import NATIONAL_TEAM_IDS, national_team, INTERNATIONAL_CALLUP_MORALE_BONUS
        with connect(self.database_path) as connection:
            match_row = connection.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()
        if not match_row or match_row["completed"]:
            return {}
        home_id, away_id = int(match_row["home_team"]), int(match_row["away_team"])
        id_to_nationality = {team_id: nat for nat, team_id in NATIONAL_TEAM_IDS.items()}
        home_nat, away_nat = id_to_nationality.get(home_id), id_to_nationality.get(away_id)
        if not home_nat or not away_nat:
            return {}
        home_team, away_team = national_team(home_nat), national_team(away_nat)
        home_xi = select_national_xi(home_nat, self.database_path)
        away_xi = select_national_xi(away_nat, self.database_path)
        if len(home_xi) < 11 or len(away_xi) < 11:
            return {}
        match = Match(home_team, away_team, home_xi, away_xi, match_row["format"],
                      seed=self.rng.randint(0, 2**31), ground_info=get_ground_info(home_id, self.database_path))
        match.simulate()
        totals = match.team_totals
        wickets = {team_id: sum(i.wickets for i in match.innings if i.batting_team == team_id)
                  for team_id in (home_id, away_id)}
        result = {"home_runs": totals[home_id], "home_wickets": wickets[home_id],
                 "away_runs": totals[away_id], "away_wickets": wickets[away_id],
                 "winner": match.winner_id, "tied": match.winner_id is None, "overs": match.overs_limit()}
        current_date = match_row["date"]
        from src.models.player_records import format_context
        record_context = format_context(match_row["format"], international=True)
        for innings in match.innings:
            for player in innings.batting_order:
                line = innings.batters[int(player["id"])]
                if line.balls or line.dismissal != "did not bat":
                    record_player_performance(int(player["id"]), current_date, record_context,
                                              batting=vars(line).copy(), database_path=self.database_path)
            for player in innings.bowling_squad:
                line = innings.bowlers[int(player["id"])]
                if line.balls:
                    record_player_performance(int(player["id"]), current_date, record_context,
                                              bowling=vars(line).copy(), database_path=self.database_path)
        adjust_players_morale([int(p["id"]) for p in home_xi + away_xi],
                              INTERNATIONAL_CALLUP_MORALE_BONUS, self.database_path)
        self.record_played_fixture(match_id, result)
        competition_id = int(match_row["competition_id"])
        self._advance_icc_group_stage_if_ready(competition_id, current_date)
        self._announce_icc_champion_if_final(competition_id, match_row["round_name"],
                                             home_team, away_team, result, current_date)
        self._advance_tour_if_ready(competition_id, current_date)
        return result

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
        # v4.53.0: this lightweight simulator has no day/session/declaration
        # concept at all, so a genuine First-Class draw (very common in real
        # cricket — a Test running out of time with neither side bowled out)
        # previously had ~0% chance of ever happening here (winner=None only
        # when the two gaussian run totals landed exactly equal). Give Test-
        # format matches a real, if simplified, draw chance instead —
        # matches roughly how often an actual County Championship match ends
        # unresolved, without simulating the full match to find out.
        drawn = match["format"] == "Test" and self.rng.random() < 0.35
        winner = None if drawn else (
            match["home_team"] if home_runs > away_runs else match["away_team"] if away_runs > home_runs else None)
        result = {"home_runs": home_runs, "home_wickets": home_wickets, "away_runs": away_runs,
                  "away_wickets": away_wickets, "winner": winner, "tied": winner is None and not drawn,
                  "drawn": drawn, "overs": overs}
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
        if competition and competition["type"] == "League":
            self._record_rivalry_result(match, result)
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
            payload.setdefault("drawn", False)
            payload.setdefault("tied", payload["winner"] is None and not payload["drawn"])
            payload.setdefault("overs", {"T10": 10, "T20": 20, "Hundred": 20, "ODI": 50}.get(match["format"], 50))
            connection.execute("UPDATE matches SET completed=1,result_json=? WHERE id=?", (json.dumps(payload), match_id))
            competition = connection.execute("SELECT type FROM competitions WHERE id=?", (match["competition_id"],)).fetchone()
            if competition and competition["type"] == "League":
                self._update_table(connection, match, payload)
        if competition and competition["type"] == "Cup":
            self._advance_cup_if_ready(match["competition_id"], match["round_name"], match["date"])
        if competition and competition["type"] == "League":
            self._record_rivalry_result(match, payload)
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
                # A negative home id is a synthetic national team (see
                # src/models/international.py) — it has no row in `teams`,
                # so the normal venue lookup would crash with a None result.
                venue = self._venue_for_team(connection, home)
                connection.execute(
                    """INSERT INTO matches
                       (home_team,away_team,format,date,venue,completed,result_json,competition_id,round_name)
                       VALUES (?,?,'ODI',?,?,0,'{}',?,?)""",
                    (home, away, next_date.isoformat(), venue, competition_id, next_name),
                )

    @staticmethod
    def _venue_for_team(connection, team_id: int) -> str:
        """A ground name for either a real club or a synthetic national
        team id — see the NATIONAL_TEAM_IDS note in _advance_cup_if_ready."""
        if team_id < 0:
            from src.models.international import NATIONAL_TEAM_NAMES_BY_ID
            return NATIONAL_TEAM_NAMES_BY_ID.get(team_id, "International") + " National Ground"
        row = connection.execute("SELECT name FROM teams WHERE id=?", (team_id,)).fetchone()
        return (row[0] if row else "Neutral") + " Ground"

    ## Simplified County Championship-style batting bonus points — real ECB
    ## rules only award these from a team's first 130 overs of their FIRST
    ## innings; this engine's result payload only ever exposes match-
    ## aggregate runs/wickets (not a per-innings breakdown that's reliably
    ## available across both the interactive ball-by-ball engine AND the
    ## lightweight AI-only simulate_fixture() path), so thresholds are
    ## applied to the team's whole-match total instead — a real, working
    ## bonus-point system, just not an ECB-exact one. Test format only
    ## (First Class); limited-overs divisions never award these.
    BATTING_BONUS_THRESHOLDS = (200, 250, 300, 350)

    @staticmethod
    def _batting_bonus_points(runs: int) -> int:
        return sum(1 for threshold in CompetitionEngine.BATTING_BONUS_THRESHOLDS if runs >= threshold)

    @staticmethod
    def _bowling_bonus_points(wickets_taken: int) -> int:
        if wickets_taken >= 10: return 5
        if wickets_taken >= 9: return 4
        if wickets_taken >= 7: return 3
        if wickets_taken >= 5: return 2
        if wickets_taken >= 3: return 1
        return 0

    @staticmethod
    def _update_table(connection, match, result: dict[str, Any]) -> None:
        is_first_class = match["format"] == "Test"
        for team_id, is_home in ((match["home_team"], True), (match["away_team"], False)):
            drawn = int(result.get("drawn", False))
            won = int(result["winner"] == team_id and not drawn)
            tied = int(result["tied"] and not drawn)
            lost = int(not won and not tied and not drawn)
            team_runs = result["home_runs"] if is_home else result["away_runs"]
            opp_runs = result["away_runs"] if is_home else result["home_runs"]
            opp_wickets = result.get("away_wickets" if is_home else "home_wickets", 0)
            nrr_delta = (team_runs - opp_runs) / max(1, result["overs"])
            bat_bonus = CompetitionEngine._batting_bonus_points(team_runs) if is_first_class else 0
            bowl_bonus = CompetitionEngine._bowling_bonus_points(opp_wickets) if is_first_class else 0
            bonus_total = bat_bonus + bowl_bonus
            connection.execute(
                """UPDATE league_standings SET played=played+1,won=won+?,lost=lost+?,tied=tied+?,drawn=drawn+?,
                   bat_bonus=bat_bonus+?,bowl_bonus=bowl_bonus+?,
                   points=points+?,net_run_rate=net_run_rate+? WHERE competition_id=? AND team_id=?""",
                (won, lost, tied, drawn, bat_bonus, bowl_bonus,
                 won * 2 + tied + bonus_total, nrr_delta, match["competition_id"], team_id),
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
                award_manager_xp(100, title, self.database_path)
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
            # v4.57.0: real promotion/relegation for the per-nation domestic
            # leagues (e.g. County Championship Div 1/2), generalized off
            # `leagues.promotion`/`relegation`/`divisions` instead of the
            # hardcoded 5-division scheme above — most nations are a single
            # table (nothing to move), multi-division ones (currently
            # England/India/Bangladesh) get a real top-tier<->lower-tier
            # swap each season, tracked via `teams.nation_division`.
            # Restricted to each nation's primary Test-format competition:
            # `nation_division` is one shared column per team, and England
            # (for example) has TWO independently-divisioned competitions
            # (County Championship AND T20 Blast) — letting both drive
            # promotion/relegation off the same column in one pass caused a
            # real bug found by this version's own tests, where T20 Blast's
            # mostly-tied standings immediately re-shuffled teams straight
            # back, undoing what County Championship had just decided.
            nation_promoted: list[int] = []
            nation_relegated: list[int] = []
            nation_leagues = connection.execute(
                "SELECT country_id, name, divisions, promotion, relegation FROM leagues "
                "WHERE kind='league' AND divisions>1 AND format='Test'"
            ).fetchall()
            for country_id, league_name, n_divisions, promotion_n, relegation_n in nation_leagues:
                if promotion_n <= 0 and relegation_n <= 0:
                    continue
                competition = connection.execute(
                    "SELECT id FROM competitions WHERE name=? AND season=?", (league_name, season)
                ).fetchone()
                if not competition:
                    continue
                tier_teams: dict[int, list[int]] = {}
                for team_id, tier in connection.execute(
                    """SELECT t.id, COALESCE(t.nation_division,1) AS tier FROM league_standings s
                       JOIN teams t ON t.id = s.team_id
                       WHERE s.competition_id=?
                       ORDER BY COALESCE(t.nation_division,1), s.points DESC, s.won DESC, s.net_run_rate DESC""",
                    (competition[0],),
                ):
                    tier_teams.setdefault(tier, []).append(team_id)
                for tier in range(2, n_divisions + 1):
                    lower = tier_teams.get(tier, [])
                    upper = tier_teams.get(tier - 1, [])
                    promote_n = min(promotion_n, len(lower) // 2) if lower else 0
                    relegate_n = min(relegation_n, len(upper) // 2) if upper else 0
                    promote_up = lower[:promote_n]
                    relegate_down = upper[-relegate_n:] if relegate_n else []
                    nation_promoted += promote_up
                    nation_relegated += relegate_down
                    connection.executemany("UPDATE teams SET nation_division=? WHERE id=?",
                                           [(tier - 1, tid) for tid in promote_up])
                    connection.executemany("UPDATE teams SET nation_division=? WHERE id=?",
                                           [(tier, tid) for tid in relegate_down])
            connection.execute("UPDATE players SET age=age+1")
            # v4.64.0: real academy graduation — a genuine bug found while
            # scoping roadmap.json's "expanded development paths": nothing
            # anywhere ever cleared `academy_squad` once set (either at
            # world-seed time for under-20s, or on every recruit_youth
            # signing), so a player stayed listed as a Youth Academy
            # "prospect" forever, even at 30+ (_academy_eligible includes
            # anyone with the flag set, not just real under-20s). Clears at
            # 21 — the same age recruit_youth's 16-year-olds would
            # realistically graduate a first-team-ready academy product by.
            graduated = [dict(row) for row in connection.execute(
                "SELECT id, name, team_id, overall, potential FROM players WHERE academy_squad=1 AND age>20"
            )]
            if graduated:
                connection.execute("UPDATE players SET academy_squad=0 WHERE academy_squad=1 AND age>20")
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
        for team_id in nation_promoted: adjust_team_morale(team_id, PROMOTION_MORALE_BONUS, self.database_path)
        for team_id in nation_relegated: adjust_team_morale(team_id, RELEGATION_MORALE_PENALTY, self.database_path)
        with connect(self.database_path) as connection:
            squad_sizes = dict(connection.execute("SELECT team_id, COUNT(*) FROM players GROUP BY team_id").fetchall())
            team_ids = [row[0] for row in connection.execute("SELECT id FROM teams ORDER BY id")]
        # v4.58.0: the "Eye for Talent" manager perk finds one extra academy
        # prospect each season — only for the user's own club (AI clubs have
        # no manager progression), still subject to the squad-size cap.
        eye_for_talent = has_manager_perk("eye_for_talent", self.database_path)
        for team_id in team_ids:
            room = self.SQUAD_SIZE_CAP - squad_sizes.get(team_id, 0)
            if room > 0:
                base_intake = 4 if (team_id == user_team_id and eye_for_talent) else 3
                recruit_youth(team_id, count=min(base_intake, room), database_path=self.database_path)
        staff_result = age_staff_at_rollover(season, self.database_path)
        self.ensure_season(season + 1)
        with connect(self.database_path) as connection:
            connection.execute("UPDATE user_data SET current_date=? WHERE id=1", (date(season + 1, 4, 1).isoformat(),))
        self._announce_season_rollover(season, user_team_id, promoted, relegated, retirees, team_names)
        self._announce_academy_graduations(season, user_team_id, graduated, team_names)
        if user_team_id in nation_promoted or user_team_id in nation_relegated:
            stamp = f"{date(season, 9, 30).isoformat()} 18:05"
            verb = "promoted" if user_team_id in nation_promoted else "relegated"
            create_inbox_message(
                "HIGH", f"Nation league: {verb.title()}",
                f"{team_names.get(user_team_id, 'Your club')} finished the season {verb} in its domestic "
                f"nation league.", timestamp=stamp, database_path=self.database_path)
        return {"promoted": promoted, "relegated": relegated, "retired": [p["name"] for p in retirees],
               "staff_retired": staff_result["retired"],
               "nation_promoted": nation_promoted, "nation_relegated": nation_relegated}

    def _announce_academy_graduations(self, season: int, user_team_id: int,
                                      graduated: list[dict[str, Any]], team_names: dict[int, str]) -> None:
        """v4.64.0: a real graduation moment — scoped to the user's own
        club, matching the existing precedent (Legends/season records also
        only track the user's team). Posts both an inbox message and a
        permanent narrative event (v4.59.0's story feed), so a genuine
        academy product making the step up is a moment worth noticing,
        not just a silent flag flip."""
        from database import record_narrative_event
        stamp = f"{date(season, 9, 30).isoformat()} 18:10"
        for player in graduated:
            if player["team_id"] != user_team_id:
                continue
            create_inbox_message(
                "MEDIUM", f"{player['name']} graduates from the academy",
                f"{player['name']} has turned 21 and is no longer a Youth Academy prospect — "
                f"they're a full member of the first-team squad now (overall {player['overall']}, "
                f"potential {player['potential']}).",
                timestamp=stamp, database_path=self.database_path)
            record_narrative_event(
                date(season, 9, 30).isoformat(), "MILESTONE", f"{player['name']} graduates from the academy",
                f"{team_names.get(user_team_id, 'The club')}'s academy product {player['name']} has come "
                f"through to the first team.",
                team_id=user_team_id, player_id=player["id"], importance=1, database_path=self.database_path)

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


def _split_divisions(team_ids: list[int], divisions: int) -> list[list[int]]:
    """Split a team id list into `divisions` roughly equal integer-sized
    chunks (list-of-lists), dropping any chunk smaller than 2 teams."""
    base, extra = divmod(len(team_ids), max(1, divisions))
    sizes = [base + (1 if i < extra else 0) for i in range(divisions)]
    out, offset = [], 0
    for size in sizes:
        if size < 2:
            continue
        out.append(team_ids[offset:offset + size])
        offset += size
    return out
