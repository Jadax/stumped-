"""JSON-RPC-over-stdio backend for the Godot client (docs/GRAPHICS_MIGRATION_PLAN.md).

Wraps existing database/competition functions; contains no simulation
logic of its own. Protocol: one JSON object per line on stdin
({"id": N, "method": "...", "params": {...}}), one JSON object per line
back on stdout ({"id": N, "result": ...} or {"id": N, "error": "..."}).
Runs headless — never touches pygame.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import date, timedelta
from typing import Any, Callable

from database import (add_financial_transaction, adjust_players_morale, adjust_team_morale,
                      apply_daily_training, apply_match_player_updates,
                      browse_staff_market, check_sacking, create_inbox_message, evaluate_board_objectives,
                      fetch_active_injuries, fetch_club_records, fetch_facility_upgrades, fetch_financial_log,
                      fetch_honours, fetch_inbox_messages, fetch_league_standings, fetch_legends, fetch_next_fixture,
                      fetch_players, fetch_scouting_assignments, fetch_season_records, fetch_staff,
                      fetch_training_assignments, fetch_transfer_offers, get_board_confidence_history,
                      get_board_objectives, get_cup_bracket, get_custom_tournament, get_custom_tournaments,
                      get_job_offers, get_onboarding_state, get_opposition_report,
                      get_pitch_selection, get_team_summary, get_tournament_bracket,
                      get_tournament_standings, advance_onboarding as _advance_onboarding,
                      dismiss_onboarding as _dismiss_onboarding,
                      initialise_database, load_game, make_staff_offer, mark_inbox_read,
                      ONBOARDING_STEPS, PITCH_DESCRIPTIONS, PITCH_TYPES,
                      record_board_confidence, record_player_match_events, record_player_performance, recruit_youth,
                      resolve_staff_offer, resolve_transfer_offer, save_game,
                      scout_players, sell_staff_member, accept_job_offer as _accept_job_offer,
                      create_custom_tournament as _create_custom_tournament,
                      advance_tournament_to_knockout as _advance_tournament_to_knockout,
                      decline_job_offer as _decline_job_offer,
                      set_pitch_selection, set_training_focus,
                      set_training_schedule, start_facility_upgrade, submit_transfer_offer,
                      unread_inbox_count, update_user_settings)
from match_engine import Match
from src.controllers.game_controller import GameController
from src.models.career import CONFIDENCE_LABELS
from src.models.currency import currency_options, format_money
from src.models.manager import Manager, VALID_BACKGROUNDS
from src.models.morale import DROPPED_MORALE_PENALTY, dropped_from_xi, match_result_morale_deltas
from src.models.player import natural_batting_aggression
from src.models.press_conference import RESPONSE_TONES, answer_press_conference, press_conference_question
from src.models.recruitment import contract_watch, role_gaps, weakest_attribute_group
from src.models.squad_metrics import group_average
from src.models.team_talks import TEAM_TALK_TONES, deliver_team_talk
from src.utilities.launcher import app_version, get_launch_paths, prepare_environment

BATTING_STYLES = ["Silly", "Blitz", "Build", "Rotate"]
TRAINING_FOCUSES = ["None", "Batting Focus", "Bowling Focus", "Fielding Focus", "Fitness", "All-Round"]
TRAINING_INTENSITIES = ["Light", "Normal", "Heavy"]
TRAINING_DAY_PATTERNS = [[0, 2, 4], [1, 3], [0, 1, 3, 4]]
ACADEMY_FOCUSES = ["Balanced", "Batting", "Bowling", "Fielding"]
ACADEMY_FOCUS_PROGRAMMES = {"Balanced": "All-Round", "Batting": "Batting Focus",
                            "Bowling": "Bowling Focus", "Fielding": "Fielding Focus"}
ACADEMY_ROLE_FOCUSES = ["Any", "Batsman", "Pace Bowler", "Spin Bowler", "All-Rounder", "Wicketkeeper"]
ACADEMY_RECRUITMENT_FEE = 50_000
MAX_BALLS_PER_SIMULATE_CALL = 400
BALL_EVENT_KEYS = ("result", "runs", "legal", "wicket", "fielder", "commentary", "kind",
                  "over", "reviewable", "innings_complete", "match_complete", "chance",
                  "shot", "delivery")
FIELD_PRESETS = ["Aggressive", "Neutral", "Defensive"]
BATTING_STYLE_VALUES = {"Silly": 10, "Blitz": 8, "Build": 5, "Rotate": 3}
DEFAULT_MATCH_TACTICS = {"batting_aggression": 5, "bowling_aggression": 5, "field_preset": "Neutral"}

Handler = Callable[[dict[str, Any], dict[str, Any]], Any]
METHODS: dict[str, Handler] = {}


def method(name: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        METHODS[name] = fn
        return fn
    return register


def _team_id(ctx: dict) -> int:
    return ctx["team"]["id"]


def _db(ctx: dict) -> str:
    return ctx["database_path"]


@method("ping")
def _ping(_params: dict, _ctx: dict) -> dict:
    return {"pong": True, "version": app_version()}


## New-game/startup flow. Ports src/views/screens/new_game_setup.py's field
## set and src/controllers/game_controller.py's validation 1:1 by reusing
## the same GameController instance (stashed on ctx by build_context()) that
## pygame's main.py already owns — no reimplemented validation logic.
@method("get_new_game_options")
def _get_new_game_options_ipc(_params: dict, ctx: dict) -> dict:
    controller = ctx["game_controller"]
    countries = [c for c in controller.countries if c["domestic_leagues"]]
    return {"countries": countries, "backgrounds": list(VALID_BACKGROUNDS),
           "modes": ["Career", "World Cup", "Tournament"], "difficulties": ["Easy", "Normal", "Hard"]}


@method("save_new_game_setup")
def _save_new_game_setup_ipc(params: dict, ctx: dict) -> dict:
    manager = Manager(params.get("name", ""), params.get("nationality", ""), params.get("background", "Coach"))
    controller = ctx["game_controller"]
    draft = controller.save_new_game_setup(
        manager, params.get("mode", "Career"), params.get("difficulty", "Normal"),
        params.get("enabled_countries", []), params.get("primary_country"),
    )
    controller.continue_from_setup(draft)
    ctx["game_data"] = load_game(_db(ctx))
    return {"draft": draft, "destination": ctx.pop("_pending_navigation", "Dashboard")}


@method("get_selectable_teams")
def _get_selectable_teams_ipc(_params: dict, ctx: dict) -> dict:
    # Same club-shortlist filter as src/views/screens/career_team_selection.py's
    # build(): narrow to the chosen primary country, else any enabled country,
    # falling back to every team if the filter would otherwise be empty.
    all_teams = ctx["game_controller"].selectable_teams()
    setup = ctx.get("new_game_setup", {})
    enabled = set(setup.get("enabled_countries", []))
    primary = setup.get("primary_country")
    if primary:
        teams = [t for t in all_teams if t.get("country_id") == primary]
    else:
        teams = [t for t in all_teams if not enabled or t.get("country_id") in enabled]
    teams = teams or all_teams
    return {"teams": [{**t, "cash_display": format_money(t["cash"])} for t in teams]}


@method("confirm_career_team")
def _confirm_career_team_ipc(params: dict, ctx: dict) -> dict:
    team_id = int(params["team_id"])
    ctx["game_controller"].confirm_career_team(team_id)
    ctx["team"] = get_team_summary(team_id, _db(ctx))
    ctx["players"] = fetch_players(team_id, _db(ctx))
    ctx["game_data"] = load_game(_db(ctx))
    return {"team": ctx["team"], "destination": ctx.pop("_pending_navigation", "Dashboard")}


@method("confirm_world_cup_team")
def _confirm_world_cup_team_ipc(params: dict, ctx: dict) -> dict:
    ctx["game_controller"].confirm_world_cup_team(params.get("country_id", ""))
    ctx["game_data"] = load_game(_db(ctx))
    return {"team": ctx["team"], "destination": ctx.pop("_pending_navigation", "Dashboard")}


@method("confirm_custom_tournament")
def _confirm_custom_tournament_ipc(params: dict, ctx: dict) -> dict:
    ctx["game_controller"].confirm_custom_tournament(
        sorted(params.get("country_ids", [])), params.get("format", "T20"))
    ctx["game_data"] = load_game(_db(ctx))
    return {"team": ctx["team"], "destination": ctx.pop("_pending_navigation", "Dashboard")}


## Ports ui/settings.py's field set (game speed, sound, volume, resolution
## preference, currency, autosave, reduced motion, colour-blind glyphs, UI
## scale) at the data-persistence layer. Godot has no audio/theme system of
## its own yet to apply these live to — that's a later visual-polish pass —
## but every value round-trips through the same update_user_settings() the
## pygame client uses, so a save stays consistent across both clients.
@method("get_user_settings")
def _get_user_settings_ipc(_params: dict, ctx: dict) -> dict:
    return {"settings": ctx["game_data"]["user"], "currencies": currency_options()}


@method("update_user_settings")
def _update_user_settings_ipc(params: dict, ctx: dict) -> dict:
    update_user_settings(params, _db(ctx))
    ctx["game_data"] = load_game(_db(ctx))
    return {"ok": True}


## Ports src/views/screens/help_screen.py's exact content sourcing (same two
## JSON files, same "Engine FAQ" section appended from match_engine_faq.json)
## so Godot's Help screen shows identical content without a second copy of
## the manual text living in the Godot project.
@method("get_help_content")
def _get_help_content_ipc(_params: dict, _ctx: dict) -> dict:
    data_root = Path(__file__).resolve().parent / "src" / "data"
    sections = json.loads((data_root / "help_content.json").read_text(encoding="utf-8"))["sections"]
    faq = json.loads((data_root / "match_engine_faq.json").read_text(encoding="utf-8"))
    sections.append({"id": "engine_faq", "title": "Engine FAQ",
                     "articles": [{"title": item["question"], "body": item["answer"]}
                                  for item in faq["questions"]]})
    return {"sections": sections}


@method("get_squad")
def _get_squad(_params: dict, ctx: dict) -> dict:
    # Adds batting/bowling/fielding/mental group averages so the Godot
    # Squad screen's "Attributes" tab can show them alongside General
    # Info without a second IPC round trip — same data, different columns.
    # "freshness" (not raw fatigue) so the bar-column colour scheme reads
    # correctly — high=good already means green/gold everywhere else, and
    # a raw fatigue bar would show an exhausted player as "green".
    players = [{**p, "batting_avg": group_average(p, "batting"), "bowling_avg": group_average(p, "bowling"),
               "fielding_avg": group_average(p, "fielding"), "mental_avg": group_average(p, "mental"),
               "wage_display": format_money(p["wage"]), "freshness": 100 - int(p.get("fatigue", 0))}
              for p in ctx["players"]]
    return {"team": ctx["team"], "players": players}


def _selection_view(ctx: dict) -> dict:
    """Players are returned XI-first in batting order (mirroring
    ui/selection.py's self.xi array, whose order *is* the batting order),
    then the rest of the squad — so table_screen.gd's row list is directly
    reorderable by move_batting_up/down without any client-side sorting."""
    selection = ctx["game_data"].get("state", {}).get("selection", {})
    xi_ids = list(selection.get("xi", []))
    xi_set = set(xi_ids)
    captain_id, keeper_id = selection.get("captain"), selection.get("keeper")
    # ui/selection.py's dicts are keyed by int player id in memory but arrive
    # here re-loaded from JSON, where dict keys are always strings.
    batting_styles = selection.get("batting_styles", {})
    batting_aggression = selection.get("batting_aggression", {})
    by_id = {p["id"]: p for p in ctx["players"]}
    ordered = [by_id[pid] for pid in xi_ids if pid in by_id]
    ordered += [p for p in ctx["players"] if p["id"] not in xi_set]
    players = []
    for p in ordered:
        tags = []
        if p["id"] in xi_set:
            tags.append(str(xi_ids.index(p["id"]) + 1))
            if p["id"] == captain_id: tags.append("C")
            if p["id"] == keeper_id: tags.append("WK")
        style = batting_styles.get(str(p["id"]), "Build")
        aggression = batting_aggression.get(str(p["id"]), natural_batting_aggression(p))
        players.append({**p, "selected": p["id"] in xi_set, "xi_status": "/".join(tags),
                       "batting_style": style, "batting_aggression": aggression,
                       "freshness": 100 - int(p.get("fatigue", 0))})
    return {"players": players, "xi_count": len(xi_set), "captain_id": captain_id, "keeper_id": keeper_id}


def _set_leadership_role(ctx: dict, role_key: str, player_id: int) -> dict:
    """Shared by set_captain/set_keeper: toggle a role, only within the XI —
    mirrors ui/selection.py's captain/keeper cycle buttons, which only
    cycle through self.xi."""
    selection = dict(ctx["game_data"].get("state", {}).get("selection", {}))
    if player_id not in selection.get("xi", []):
        raise ValueError(f"{role_key.title()} must be part of the starting XI.")
    selection[role_key] = None if selection.get(role_key) == player_id else player_id
    save_game({"selection": selection}, _db(ctx))
    ctx["game_data"].setdefault("state", {})["selection"] = selection
    return _selection_view(ctx)


@method("get_selection")
def _get_selection(_params: dict, ctx: dict) -> dict:
    return _selection_view(ctx)


@method("toggle_xi")
def _toggle_xi(params: dict, ctx: dict) -> dict:
    """Add/remove a player from the starting XI (max 11) — the same
    ``selection.xi`` save-state key ui/selection.py already writes, so
    picking an XI in either client is visible in the other."""
    player_id = int(params["player_id"])
    selection = dict(ctx["game_data"].get("state", {}).get("selection", {}))
    xi = list(selection.get("xi", []))
    if player_id in xi:
        xi.remove(player_id)
    elif len(xi) >= 11:
        raise ValueError("The starting XI already has 11 players.")
    else:
        xi.append(player_id)
    selection["xi"] = xi
    save_game({"selection": selection}, _db(ctx))
    ctx["game_data"].setdefault("state", {})["selection"] = selection
    return _selection_view(ctx)


@method("set_captain")
def _set_captain(params: dict, ctx: dict) -> dict:
    return _set_leadership_role(ctx, "captain", int(params["player_id"]))


@method("set_keeper")
def _set_keeper(params: dict, ctx: dict) -> dict:
    return _set_leadership_role(ctx, "keeper", int(params["player_id"]))


def _move_in_xi(ctx: dict, player_id: int, delta: int) -> dict:
    """Swap a player with their batting-order neighbour — mirrors
    ui/selection.py's arrow-click handling (lines ~181-182), which swaps
    adjacent entries in self.xi the same way. A no-op at either end of the
    order, same as the pygame version's bounds checks."""
    selection = dict(ctx["game_data"].get("state", {}).get("selection", {}))
    xi = list(selection.get("xi", []))
    if player_id not in xi:
        raise ValueError("Player must be part of the starting XI to reorder batting position.")
    i = xi.index(player_id)
    j = i + delta
    if 0 <= j < len(xi):
        xi[i], xi[j] = xi[j], xi[i]
    selection["xi"] = xi
    save_game({"selection": selection}, _db(ctx))
    ctx["game_data"].setdefault("state", {})["selection"] = selection
    return _selection_view(ctx)


@method("move_batting_up")
def _move_batting_up(params: dict, ctx: dict) -> dict:
    return _move_in_xi(ctx, int(params["player_id"]), -1)


@method("move_batting_down")
def _move_batting_down(params: dict, ctx: dict) -> dict:
    return _move_in_xi(ctx, int(params["player_id"]), 1)


@method("cycle_batting_style")
def _cycle_batting_style(params: dict, ctx: dict) -> dict:
    """Mirrors ui/selection.py's style-cycle click zone: steps a player's
    batting style through BATTING_STYLES and snaps their aggression to
    that style's default, only within the XI."""
    player_id = int(params["player_id"])
    selection = dict(ctx["game_data"].get("state", {}).get("selection", {}))
    if player_id not in selection.get("xi", []):
        raise ValueError("Player must be part of the starting XI to set a batting style.")
    styles = dict(selection.get("batting_styles", {}))
    aggression = dict(selection.get("batting_aggression", {}))
    current = styles.get(str(player_id), "Build")
    next_style = BATTING_STYLES[(BATTING_STYLES.index(current) + 1) % len(BATTING_STYLES)]
    styles[str(player_id)] = next_style
    aggression[str(player_id)] = {"Silly": 10, "Blitz": 8, "Build": 5, "Rotate": 3}[next_style]
    selection["batting_styles"] = styles
    selection["batting_aggression"] = aggression
    save_game({"selection": selection}, _db(ctx))
    ctx["game_data"].setdefault("state", {})["selection"] = selection
    return _selection_view(ctx)


@method("cycle_batting_aggression")
def _cycle_batting_aggression(params: dict, ctx: dict) -> dict:
    """Mirrors ui/selection.py's aggression-cycle click zone: steps a
    player's aggression 1-10 (wrapping), independent of their batting
    style, only within the XI."""
    player_id = int(params["player_id"])
    selection = dict(ctx["game_data"].get("state", {}).get("selection", {}))
    if player_id not in selection.get("xi", []):
        raise ValueError("Player must be part of the starting XI to set aggression.")
    player = next(p for p in ctx["players"] if p["id"] == player_id)
    aggression = dict(selection.get("batting_aggression", {}))
    base = aggression.get(str(player_id), natural_batting_aggression(player))
    aggression[str(player_id)] = base % 10 + 1
    selection["batting_aggression"] = aggression
    save_game({"selection": selection}, _db(ctx))
    ctx["game_data"].setdefault("state", {})["selection"] = selection
    return _selection_view(ctx)


@method("get_match_preview")
def _get_match_preview(_params: dict, ctx: dict) -> dict:
    """Pre-match hub: next fixture plus the currently-selected XI, so the
    Match screen can show a real lineup and ground view without a live
    ball-by-ball feed (that's a separate, much bigger piece of work — see
    docs/GRAPHICS_MIGRATION_PLAN.md)."""
    fixture = fetch_next_fixture(_team_id(ctx), _db(ctx))
    selection = _selection_view(ctx)
    return {"fixture": fixture, "team": ctx["team"],
            "xi": [p for p in selection["players"] if p["selected"]],
            "xi_count": selection["xi_count"], "captain_id": selection["captain_id"],
            "keeper_id": selection["keeper_id"]}


@method("get_opposition_report")
def _get_opposition_report(_params: dict, ctx: dict) -> dict:
    """Pre-match scouting summary of the next opponent: key players,
    strengths/weaknesses, squad composition, and recent form."""
    report = get_opposition_report(_team_id(ctx), _db(ctx))
    if report is None:
        return {"report": None, "message": "No upcoming fixture found."}
    return {"report": report}


def _best_xi(players: list[dict]) -> list[dict]:
    """Mirrors ui/pre_match.py's fallback when the manager hasn't set a
    full XI on Selection: the best-rated keeper first, then the rest by
    overall, same as pygame does before a live match can start."""
    keepers = [p for p in players if p.get("role") == "Wicketkeeper"]
    rest = [p for p in players if p not in keepers[:1]]
    return (keepers[:1] + sorted(rest, key=lambda p: p.get("overall", 0), reverse=True))[:11]


def _match_state(match: Match, ctx: dict) -> dict:
    """A lightweight live snapshot for the Godot HUD/scorecard — deliberately
    not match.to_dict() (that also computes performance_updates(), meant for
    once-per-match persistence, not once-per-ball polling)."""
    innings = None if match.completed else match.current_innings
    striker = innings.striker_player if innings else None
    non_striker = innings.non_striker_player if innings else None
    bowler = (next((p for p in innings.bowling_squad if int(p["id"]) == innings.current_bowler_id), None)
             if innings and innings.current_bowler_id is not None else None)
    eligible_bowlers = ([{"id": int(p["id"]), "name": p["name"]} for p in match._eligible_bowlers()]
                        if innings else [])
    return {"format": match.format, "completed": match.completed, "result": match.result,
           "status": match.match_status(), "pitch": match.pitch, "weather": match.weather,
           "home_team": match.home_team_id, "away_team": match.away_team_id,
           "current_innings_index": match.current_innings_index,
           "innings": [match.scorecard(i) for i in range(len(match.innings))],
           "striker": {"id": striker["id"], "name": striker["name"]} if striker else None,
           "non_striker": {"id": non_striker["id"], "name": non_striker["name"]} if non_striker else None,
           "bowler": {"id": bowler["id"], "name": bowler["name"], "fatigue": int(bowler.get("fatigue", 0))} if bowler else None,
           "last_six": list(match.last_six), "field_preset": match.field_setting,
           "reviews_remaining": match.reviews.get(_team_id(ctx), 0),
           "eligible_bowlers": eligible_bowlers,
           "batting_aggression": _match_tactics(ctx)["batting_aggression"],
           "bowling_aggression": _match_tactics(ctx)["bowling_aggression"]}


def _match_tactics(ctx: dict) -> dict:
    return ctx.setdefault("_match_tactics", dict(DEFAULT_MATCH_TACTICS))


def _apply_tactics_to_next_ball(ctx: dict, match: Match) -> None:
    """Mirrors ui/match_view.py's simulate_ball(): pushes the manager's
    live batting/bowling aggression sliders and field preset onto the
    engine right before each delivery — batting aggression is averaged
    with the striker's Selection-screen batting style (same STYLES
    weighting pygame uses), bowling aggression is applied directly."""
    tactics = _match_tactics(ctx)
    match.set_field(tactics["field_preset"])
    innings = match.current_innings
    striker = innings.striker_player
    bowler = next((p for p in innings.bowling_squad if int(p["id"]) == innings.current_bowler_id), None)
    selection = ctx["game_data"].get("state", {}).get("selection", {})
    style = selection.get("batting_styles", {}).get(str(striker["id"]), "Build")
    style_value = BATTING_STYLE_VALUES.get(style, 5)
    striker["batting_aggression"] = round((tactics["batting_aggression"] + style_value) / 2)
    if bowler is not None:
        bowler["bowling_aggression"] = round(tactics["bowling_aggression"])


def _finalise_match(ctx: dict, match: Match) -> None:
    """Mirrors ui/match_view.py's _record_result(): persists the fixture
    result into the same standings/cup pipeline advance_day uses, applies
    bounded player form/overall progression and injuries, records career
    batting/bowling lines, and stores spatial shot/delivery events —
    everything the pygame client does on match completion, so a match
    played in Godot has identical downstream effects."""
    fixture = ctx.get("_active_fixture")
    if not fixture or not fixture.get("id"):
        return
    from competition import CompetitionEngine
    competition = CompetitionEngine(_db(ctx))
    home_id, away_id = int(fixture["home_team"]), int(fixture["away_team"])
    totals = match.team_totals
    wickets = {team_id: sum(i.wickets for i in match.innings if i.batting_team == team_id)
              for team_id in (home_id, away_id)}
    result = {"home_runs": totals[home_id], "home_wickets": wickets[home_id],
             "away_runs": totals[away_id], "away_wickets": wickets[away_id],
             "winner": match.winner_id, "tied": match.winner_id is None,
             "overs": match.overs_limit(), "summary": match.result,
             "scorecards": match.to_dict()["innings"]}
    competition.record_played_fixture(int(fixture["id"]), result)
    current_date = ctx["game_data"]["user"]["current_date"]
    apply_match_player_updates(match.performance_updates(), match.injuries, current_date, _db(ctx))
    is_cup = fixture.get("competition_type") == "Cup"
    for team_id, delta in match_result_morale_deltas(match.winner_id, home_id, away_id,
                                                      match.winner_id is None, is_cup).items():
        adjust_team_morale(team_id, delta, _db(ctx))
    # Remembered so the *next* start_match can tell who's been dropped —
    # see the dropped_from_xi() call in _start_match.
    user_xi_ids = [int(p["id"]) for p in (match.lineups[home_id] if home_id == _team_id(ctx) else match.lineups[away_id])]
    last_match_xi = {"team_id": _team_id(ctx), "xi": user_xi_ids}
    save_game({"last_match_xi": last_match_xi}, _db(ctx))
    ctx["game_data"].setdefault("state", {})["last_match_xi"] = last_match_xi
    record_context = ("Cup" if fixture.get("competition_type") == "Cup" else
                      "Friendly" if not fixture.get("competition_id") else "League")
    career_lines: dict[int, dict[str, list[dict]]] = {}
    for innings in match.innings:
        for player in innings.batting_order:
            line = innings.batters[int(player["id"])]
            if line.balls or line.dismissal != "did not bat":
                career_lines.setdefault(int(player["id"]), {"batting": [], "bowling": []})["batting"].append(vars(line).copy())
        for player in innings.bowling_squad:
            line = innings.bowlers[int(player["id"])]
            if line.balls:
                career_lines.setdefault(int(player["id"]), {"batting": [], "bowling": []})["bowling"].append(vars(line).copy())
    for player_id, lines in career_lines.items():
        record_player_performance(player_id, current_date, record_context,
                                  lines["batting"] or None, lines["bowling"] or None, database_path=_db(ctx))
    record_player_match_events(int(fixture["id"]), 1, match.shot_events, match.bowling_events, _db(ctx))
    ctx["team"] = get_team_summary(_team_id(ctx), _db(ctx))
    ctx["players"] = fetch_players(_team_id(ctx), _db(ctx))


def _apply_dropped_from_xi_morale(ctx: dict, new_xi_ids: list[int]) -> None:
    """Mirrors the real-world "unhappy to be dropped" case: a player who
    played last match but isn't in this one's XI takes a small morale
    hit. Uses the "last_match_xi" game_state key _finalise_match writes,
    scoped to the user's own team (only the user picks an XI; AI clubs
    don't go through this flow)."""
    last = ctx["game_data"].get("state", {}).get("last_match_xi")
    if not last or last.get("team_id") != _team_id(ctx):
        return
    dropped = dropped_from_xi(last.get("xi", []), new_xi_ids)
    adjust_players_morale(dropped, DROPPED_MORALE_PENALTY, _db(ctx))


@method("start_match")
def _start_match(_params: dict, ctx: dict) -> dict:
    """Mirrors ui/pre_match.py's START MATCH handoff: builds the real
    match_engine.Match from the manager's selected XI (or the same
    best-XI fallback pygame uses) and the opponent's squad, then keeps it
    live in ctx between IPC calls — simulate_balls steps it forward."""
    fixture = fetch_next_fixture(_team_id(ctx), _db(ctx))
    if fixture is None:
        raise ValueError("No fixture scheduled — nothing to play.")
    selection = ctx["game_data"].get("state", {}).get("selection", {})
    xi_ids = list(selection.get("xi", []))
    by_id = {p["id"]: p for p in ctx["players"]}
    user_xi = [by_id[pid] for pid in xi_ids if pid in by_id]
    if len(user_xi) != 11:
        user_xi = _best_xi(ctx["players"])
    _apply_dropped_from_xi_morale(ctx, [int(p["id"]) for p in user_xi])
    opponent_id = fixture["away_team"] if fixture["home_team"] == _team_id(ctx) else fixture["home_team"]
    opponent_xi = fetch_players(opponent_id, _db(ctx))[:11]
    if len(opponent_xi) != 11:
        raise ValueError("Opponent squad is short of a full playing XI.")
    home_id, away_id = int(fixture["home_team"]), int(fixture["away_team"])
    home_team, away_team = get_team_summary(home_id, _db(ctx)), get_team_summary(away_id, _db(ctx))
    home_xi = user_xi if home_id == _team_id(ctx) else opponent_xi
    away_xi = opponent_xi if home_id == _team_id(ctx) else user_xi
    user_is_home = home_id == _team_id(ctx)
    pitch = get_pitch_selection(_team_id(ctx), _db(ctx)) if user_is_home else "Green"
    match = Match(home_team, away_team, home_xi, away_xi, fixture.get("format", "T20"), pitch=pitch)
    ctx["match"] = match
    ctx["_active_fixture"] = fixture
    ctx["_match_finalised"] = False
    ctx["_match_tactics"] = dict(DEFAULT_MATCH_TACTICS)
    return _match_state(match, ctx)


@method("get_match_state")
def _get_match_state(_params: dict, ctx: dict) -> dict:
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    return _match_state(match, ctx)


@method("simulate_balls")
def _simulate_balls(params: dict, ctx: dict) -> dict:
    """Steps the live match forward by up to `count` legal deliveries
    (illegal wides/no-balls don't count against it, matching how an
    "over" is defined) — powers NEXT BALL (count=1), OVER (count=6), and
    SKIP (a larger count) in the Godot Match screen, same as pygame's
    timer-driven simulate_ball() loop just called explicitly instead of
    on an accumulator."""
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    count = max(1, min(MAX_BALLS_PER_SIMULATE_CALL, int(params.get("count", 1))))
    events = []
    delivered = 0
    while delivered < count and not match.completed:
        innings = match.current_innings
        _apply_tactics_to_next_ball(ctx, match)
        batter = innings.striker_player
        bowler = (next((p for p in innings.bowling_squad if int(p["id"]) == innings.current_bowler_id), None)
                 if innings.current_bowler_id is not None else None)
        event = match.ball_outcome()
        payload = {key: event[key] for key in BALL_EVENT_KEYS}
        payload["batter"] = {"id": batter["id"], "name": batter["name"]}
        payload["bowler"] = {"id": bowler["id"], "name": bowler["name"]} if bowler else None
        events.append(payload)
        match.event_pool.release(event)
        if payload["legal"]:
            delivered += 1
    if match.completed and not ctx.get("_match_finalised"):
        _finalise_match(ctx, match)
        ctx["_match_finalised"] = True
    return {"events": events, "state": _match_state(match, ctx)}


@method("get_match_prediction")
def _get_match_prediction(_params: dict, ctx: dict) -> dict:
    """Mirrors ui/match_view.py's PREDICT button: the user's own team's
    win probability (the opponent's is always 100 minus this, so pygame
    never shows it separately either)."""
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    return {"probability": match.win_probability(_team_id(ctx))}


@method("set_match_field")
def _set_match_field(params: dict, ctx: dict) -> dict:
    """Mirrors ui/match_view.py's FIELD button: a genuine tactical choice,
    not cosmetic — Aggressive raises wicket chance and boundary risk,
    Defensive suppresses both (match_engine.py's ball-outcome weights)."""
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    preset = params.get("preset", "Neutral")
    if preset not in FIELD_PRESETS:
        raise ValueError(f"Unknown field preset: {preset}")
    _match_tactics(ctx)["field_preset"] = preset
    match.set_field(preset)
    return _match_state(match, ctx)


@method("set_match_aggression")
def _set_match_aggression(params: dict, ctx: dict) -> dict:
    """Mirrors ui/match_view.py's batting/bowling aggression sliders
    (1-10, same scale as Selection's per-player aggression) — applied to
    the striker/bowler on every subsequent delivery by
    _apply_tactics_to_next_ball, not persisted anywhere beyond this
    match."""
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    tactics = _match_tactics(ctx)
    if "batting" in params:
        tactics["batting_aggression"] = max(1, min(10, int(params["batting"])))
    if "bowling" in params:
        tactics["bowling_aggression"] = max(1, min(10, int(params["bowling"])))
    return _match_state(match, ctx)


@method("review_decision")
def _review_decision(_params: dict, ctx: dict) -> dict:
    """Mirrors ui/match_view.py's DRS button: reviews only cost the team a
    review when the original on-field decision is upheld (correct) —
    an overturned (wrong) decision is a free review, per
    Match.review_last_decision's own accounting."""
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    review = match.review_last_decision(_team_id(ctx))
    return {"review": review, "state": _match_state(match, ctx)}


@method("cycle_match_bowler")
def _cycle_match_bowler(_params: dict, ctx: dict) -> dict:
    """Mirrors ui/match_view.py's CHANGE button: steps to the next
    eligible bowler (excluding whoever bowled the previous over),
    wrapping around the list until a legal change is found."""
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    changed = False
    if not match.completed:
        eligible = match._eligible_bowlers()
        current_id = match.current_innings.current_bowler_id
        ids = [int(p["id"]) for p in eligible]
        start = ids.index(current_id) + 1 if current_id in ids else 0
        for offset in range(len(ids)):
            candidate = ids[(start + offset) % len(ids)]
            if match.set_bowler(candidate):
                changed = True
                break
    result = _match_state(match, ctx)
    result["bowler_changed"] = changed
    return result


@method("get_dashboard")
def _get_dashboard(_params: dict, ctx: dict) -> dict:
    db, team_id = _db(ctx), _team_id(ctx)
    fixture = fetch_next_fixture(team_id, db)
    # fetch_league_standings() doesn't return a "position" column (rows
    # already arrive ordered) — ui/dashboard.py enriches it the same way
    # before display, so mirror that here for IPC consumers.
    standings = [dict(position=i + 1, **row) for i, row in enumerate(fetch_league_standings(db))]
    return {"team": ctx["team"], "fixture": fixture,
           "standings": standings,
           "messages": fetch_inbox_messages(5, db),
           "unread_count": unread_inbox_count(db),
           "date": ctx["game_data"]["user"]["current_date"],
           "manager_name": ctx.get("new_game_setup", {}).get("manager", {}).get("name", "Manager")}


@method("get_inbox")
def _get_inbox(params: dict, ctx: dict) -> dict:
    limit = int(params.get("limit", 50))
    return {"messages": fetch_inbox_messages(limit, _db(ctx))}


@method("mark_message_read")
def _mark_message_read(params: dict, ctx: dict) -> dict:
    mark_inbox_read(int(params["message_id"]), _db(ctx))
    return {"ok": True}


@method("get_standings")
def _get_standings(_params: dict, ctx: dict) -> dict:
    return {"standings": fetch_league_standings(_db(ctx))}


@method("get_staff")
def _get_staff(params: dict, ctx: dict) -> dict:
    return {"staff": fetch_staff(_team_id(ctx), params.get("group"), _db(ctx))}


@method("release_staff")
def _release_staff(params: dict, ctx: dict) -> dict:
    """Sell one of the club's own staff back to the market — a fee is paid
    but the role is deliberately left vacant, mirroring ui/staff.py."""
    fee = sell_staff_member(int(params["staff_id"]), _db(ctx))
    ctx["team"] = get_team_summary(_team_id(ctx), _db(ctx))
    return {"fee": fee}


@method("get_transfer_market")
def _get_transfer_market(params: dict, ctx: dict) -> dict:
    db, team_id = _db(ctx), _team_id(ctx)
    players = scout_players(params.get("role", "All"), params.get("minimum_age", 16),
                            params.get("maximum_age", 45), params.get("minimum_overall", 0),
                            params.get("maximum_overall", 100), params.get("nationality", "All"),
                            team_id, None, db)
    # Money formatted here (mirrors ui/finances.py's format_money()) rather
    # than in the Godot client, so currency symbol/comma formatting stays
    # in one place and follows the player's active-currency setting. The
    # raw numeric field is kept alongside for submit_transfer_offer's fee.
    players = [{**p, "asking_price_display": format_money(p["asking_price"])} for p in players]
    offers = [{**o, "fee_display": format_money(o["fee"])} for o in fetch_transfer_offers(team_id, db)]
    return {"players": players, "offers": offers}


@method("submit_transfer_offer")
def _submit_transfer_offer(params: dict, ctx: dict) -> dict:
    offer_id = submit_transfer_offer(int(params["player_id"]), _team_id(ctx), int(params["fee"]),
                                     int(params["wage"]), ctx["game_data"]["user"]["current_date"], _db(ctx))
    return {"offer_id": offer_id}


@method("resolve_transfer_offer")
def _resolve_transfer_offer(params: dict, ctx: dict) -> dict:
    return {"success": resolve_transfer_offer(int(params["offer_id"]), bool(params["accept"]), _db(ctx))}


@method("get_scouting_assignments")
def _get_scouting_assignments(_params: dict, ctx: dict) -> dict:
    return {"assignments": fetch_scouting_assignments(_team_id(ctx), _db(ctx))}


@method("get_finances")
def _get_finances(_params: dict, ctx: dict) -> dict:
    transactions = [{**t, "amount_display": format_money(t["amount"])}
                    for t in fetch_financial_log(_team_id(ctx), _db(ctx))]
    return {"team": ctx["team"], "transactions": transactions}


FACILITY_LEVEL_KEYS = {
    "Stadium": "stadium_level", "Training Ground": "training_level",
    "Medical Centre": "medical_level", "Academy": "academy_level",
    "Commercial Office": "commercial_level", "Scouting Network": "scouting_level",
    "Grounds Department": "grounds_level",
}


@method("get_facilities")
def _get_facilities(_params: dict, ctx: dict) -> dict:
    team = ctx["team"]
    upgrades = fetch_facility_upgrades(_team_id(ctx), _db(ctx))
    building = {u["facility"] for u in upgrades if u["status"] == "BUILDING"}
    facilities = [{"facility": name, "level": team.get(key, 1),
                   "status": "Building" if name in building else "Ready"}
                  for name, key in FACILITY_LEVEL_KEYS.items()]
    return {"team": team, "upgrades": upgrades, "facilities": facilities}


@method("upgrade_facility")
def _upgrade_facility(params: dict, ctx: dict) -> dict:
    result = start_facility_upgrade(_team_id(ctx), params["facility"],
                                    ctx["game_data"]["user"]["current_date"], _db(ctx))
    ctx["team"] = get_team_summary(_team_id(ctx), _db(ctx))
    return result


@method("get_training")
def _get_training(_params: dict, ctx: dict) -> dict:
    assignments = fetch_training_assignments(_team_id(ctx), _db(ctx))
    # Flattens each player's assignment (if any) onto the player dict so
    # the Godot client can render this as a plain table like every other
    # list screen, instead of merging two separate structures itself.
    players = [{**p, "focus": assignments.get(p["id"], {}).get("focus") or "None",
               "intensity": assignments.get(p["id"], {}).get("intensity", "Normal"),
               "last_trained": assignments.get(p["id"], {}).get("last_trained") or "—"}
              for p in ctx["players"]]
    return {"players": players, "assignments": {str(k): v for k, v in assignments.items()}}


def _training_assignment(ctx: dict, player_id: int) -> dict:
    default = {"focus": "None", "intensity": "Normal", "days": [0, 2, 4]}
    return fetch_training_assignments(_team_id(ctx), _db(ctx)).get(player_id, default)


@method("cycle_training_focus")
def _cycle_training_focus(params: dict, ctx: dict) -> dict:
    """Mirrors ui/training.py's PROGRAMME cycle button/column: steps a
    player's training programme through TRAINING_FOCUSES (wrapping)."""
    player_id = int(params["player_id"])
    current = _training_assignment(ctx, player_id)["focus"]
    next_focus = TRAINING_FOCUSES[(TRAINING_FOCUSES.index(current) + 1) % len(TRAINING_FOCUSES)]
    set_training_focus(player_id, next_focus, _db(ctx))
    return _get_training({}, ctx)


@method("cycle_training_intensity")
def _cycle_training_intensity(params: dict, ctx: dict) -> dict:
    """Mirrors ui/training.py's INTENSITY cycle button/column: steps
    Light/Normal/Heavy (wrapping), keeping the current focus and days."""
    player_id = int(params["player_id"])
    assignment = _training_assignment(ctx, player_id)
    intensities = TRAINING_INTENSITIES
    next_intensity = intensities[(intensities.index(assignment.get("intensity", "Normal")) + 1) % len(intensities)]
    set_training_schedule(player_id, assignment["focus"], next_intensity, assignment.get("days", [0, 2, 4]), _db(ctx))
    return _get_training({}, ctx)


@method("cycle_training_days")
def _cycle_training_days(params: dict, ctx: dict) -> dict:
    """Mirrors ui/training.py's DAYS cycle button/column: steps through the
    same 3 weekly patterns (Mon/Wed/Fri, Tue/Thu, Mon/Tue/Thu/Fri)."""
    player_id = int(params["player_id"])
    assignment = _training_assignment(ctx, player_id)
    days = assignment.get("days", [0, 2, 4])
    index = TRAINING_DAY_PATTERNS.index(days) if days in TRAINING_DAY_PATTERNS else -1
    next_days = TRAINING_DAY_PATTERNS[(index + 1) % len(TRAINING_DAY_PATTERNS)]
    set_training_schedule(player_id, assignment["focus"], assignment.get("intensity", "Normal"), next_days, _db(ctx))
    return _get_training({}, ctx)


@method("apply_training_to_all")
def _apply_training_to_all(params: dict, ctx: dict) -> dict:
    """Mirrors ui/training.py's "APPLY PROGRAMME TO ALL" bulk action:
    copies one player's programme/intensity/days onto the whole squad."""
    source_id = int(params["player_id"])
    assignment = _training_assignment(ctx, source_id)
    for player in ctx["players"]:
        set_training_schedule(player["id"], assignment["focus"], assignment.get("intensity", "Normal"),
                              assignment.get("days", [0, 2, 4]), _db(ctx))
    return _get_training({}, ctx)


@method("simulate_training")
def _simulate_training(params: dict, ctx: dict) -> dict:
    """Mirrors ui/training.py's "ADVANCE TO NEXT SESSION"/"SIMULATE 30
    CALENDAR DAYS" actions: runs apply_daily_training() day-by-day from the
    current save date (training-only — does not advance fixtures/inbox/the
    rest of the calendar the way advance_day does) and reports points
    gained plus the refreshed player attributes."""
    days_count = max(1, int(params.get("days", 1)))
    start = date.fromisoformat(ctx["game_data"]["user"]["current_date"])
    points = sum(apply_daily_training(_team_id(ctx), (start + timedelta(days=offset)).isoformat(), _db(ctx))
                for offset in range(days_count))
    ctx["players"] = fetch_players(_team_id(ctx), _db(ctx))
    result = _get_training({}, ctx)
    result["points_gained"] = points
    return result


@method("get_staff_market")
def _get_staff_market(params: dict, ctx: dict) -> dict:
    staff = browse_staff_market(params.get("group", "All"), _team_id(ctx),
                                int(params.get("limit", 30)), _db(ctx))
    staff = [{**s, "fee_display": format_money(s["fee"]), "wage_display": format_money(s["wage"])}
            for s in staff]
    return {"staff": staff}


@method("sign_staff")
def _sign_staff(params: dict, ctx: dict) -> dict:
    """Bid-then-immediately-accept, mirroring ui/staff.py's _act_on_selected()."""
    offer_id = make_staff_offer(int(params["staff_id"]), int(params["from_team"]), _team_id(ctx),
                                int(params["fee"]), int(params["wage"]),
                                ctx["game_data"]["user"]["current_date"], _db(ctx))
    return {"success": resolve_staff_offer(offer_id, True, _db(ctx))}


@method("get_recruitment")
def _get_recruitment(_params: dict, ctx: dict) -> dict:
    players, db, team_id = ctx["players"], _db(ctx), _team_id(ctx)
    gaps = role_gaps(players)
    assignments = fetch_scouting_assignments(team_id, db)
    return {"team": ctx["team"], "gaps": [{"role": role, "have": have} for role, have in gaps],
           "weakest_group": weakest_attribute_group(players),
           "contract_watch": contract_watch(players),
           "active_assignments": [a for a in assignments if a["status"] == "ACTIVE"]}


def _academy_eligible(ctx: dict) -> list[dict]:
    """Mirrors ui/youth.py's roster filter: under-20s plus anyone flagged
    academy_squad, not just the flag alone."""
    return [p for p in ctx["players"] if p.get("age", 0) <= 20 or p.get("academy_squad")]


@method("get_youth_academy")
def _get_youth_academy(_params: dict, ctx: dict) -> dict:
    players = _academy_eligible(ctx)
    return {"team": ctx["team"], "recruitment_fee_display": format_money(ACADEMY_RECRUITMENT_FEE),
           "players": [{**p, "wage_display": format_money(p["wage"]),
                       "batting_avg": group_average(p, "batting"),
                       "bowling_avg": group_average(p, "bowling"),
                       "fielding_avg": group_average(p, "fielding")}
                      for p in players]}


@method("set_academy_focus")
def _set_academy_focus(params: dict, ctx: dict) -> dict:
    """Mirrors ui/youth.py's FOCUS button: applies one collective training
    programme to every academy-eligible player (Balanced/Batting/Bowling/
    Fielding, mapped onto the same programmes Training uses)."""
    focus = params.get("focus", "Balanced")
    if focus not in ACADEMY_FOCUSES:
        raise ValueError(f"Unknown academy focus: {focus}")
    programme = ACADEMY_FOCUS_PROGRAMMES[focus]
    for player in _academy_eligible(ctx):
        set_training_focus(player["id"], programme, _db(ctx))
    result = _get_youth_academy({}, ctx)
    result["focus"] = focus
    return result


@method("recruit_youth_prospects")
def _recruit_youth_prospects(params: dict, ctx: dict) -> dict:
    """Mirrors ui/youth.py's RECRUIT YOUTH action: runs a recruitment
    trial (3-5 new 16-year-olds, optionally skewed to a target role),
    charges the fixed trial fee, and posts the same inbox notification."""
    role_focus = params.get("role_focus", "Any")
    if role_focus not in ACADEMY_ROLE_FOCUSES:
        raise ValueError(f"Unknown academy scouting role focus: {role_focus}")
    current_date = ctx["game_data"]["user"]["current_date"]
    created = recruit_youth(_team_id(ctx), count=None, role_focus=role_focus, database_path=_db(ctx))
    add_financial_transaction(_team_id(ctx), current_date, "Youth Academy", "EXPENSE",
                              ACADEMY_RECRUITMENT_FEE, "Youth recruitment trials", _db(ctx))
    focus_note = "" if role_focus == "Any" else f" ({role_focus.lower()}s)"
    create_inbox_message("LOW", "Youth recruitment complete",
                         f"Academy trials have produced {len(created)} new 16-year-old prospects{focus_note}.",
                         timestamp=f"{current_date} 16:00", database_path=_db(ctx))
    ctx["team"] = get_team_summary(_team_id(ctx), _db(ctx))
    ctx["players"] = fetch_players(_team_id(ctx), _db(ctx))
    result = _get_youth_academy({}, ctx)
    result["created_count"] = len(created)
    return result


@method("get_medical")
def _get_medical(_params: dict, ctx: dict) -> dict:
    return {"injuries": fetch_active_injuries(_team_id(ctx), _db(ctx))}


@method("get_honours")
def _get_honours(_params: dict, ctx: dict) -> dict:
    return {"honours": fetch_honours(_team_id(ctx), _db(ctx))}


@method("get_cup_bracket")
def _get_cup_bracket(_params: dict, ctx: dict) -> dict:
    return get_cup_bracket(_db(ctx))


@method("get_trophy_room")
def _get_trophy_room(_params: dict, ctx: dict) -> dict:
    """Group the flat honours cabinet into a per-competition breakdown —
    the same rows as get_honours, plus counts/seasons-won per title."""
    honours = fetch_honours(_team_id(ctx), _db(ctx))
    by_competition: dict[str, dict[str, Any]] = {}
    for honour in honours:
        entry = by_competition.setdefault(honour["title"], {"title": honour["title"], "count": 0, "seasons": []})
        entry["count"] += 1
        entry["seasons"].append(honour["season"])
    breakdown = sorted(by_competition.values(), key=lambda entry: (-entry["count"], entry["title"]))
    for entry in breakdown:
        entry["seasons"].sort(reverse=True)
    return {"honours": honours, "breakdown": breakdown, "total": len(honours)}


@method("get_season_records")
def _get_season_records(params: dict, ctx: dict) -> dict:
    return {"seasons": fetch_season_records(_team_id(ctx), params.get("limit", 100), _db(ctx))}


@method("get_club_records")
def _get_club_records(_params: dict, ctx: dict) -> dict:
    return fetch_club_records(_team_id(ctx), _db(ctx))


@method("get_legends")
def _get_legends_ipc(params: dict, ctx: dict) -> dict:
    legends = fetch_legends(params.get("nationality"), params.get("limit", 200), _db(ctx))
    for legend in legends:
        if legend["became_staff"]:
            legend["status"] = "Now coaching"
        elif legend["reason"] == "retired":
            legend["status"] = "Retired"
        else:
            legend["status"] = "Released"
    return {"legends": legends}


@method("get_board_objectives")
def _get_board_objectives(_params: dict, ctx: dict) -> dict:
    objectives = get_board_objectives(_team_id(ctx), _db(ctx))
    evaluation = evaluate_board_objectives(_team_id(ctx), _db(ctx))
    return {"objectives": objectives, "progress": evaluation["progress"]}


@method("get_board_confidence_history")
def _get_board_confidence_history(_params: dict, ctx: dict) -> dict:
    return {"history": get_board_confidence_history(_team_id(ctx), _db(ctx))}


def _team_position(ctx: dict) -> int | None:
    standings = [dict(position=i + 1, **row) for i, row in enumerate(fetch_league_standings(_db(ctx)))]
    match = next((row for row in standings if row["team_id"] == _team_id(ctx)), None)
    return match["position"] if match else None


@method("get_team_talk_status")
def _get_team_talk_status(_params: dict, ctx: dict) -> dict:
    """Once-per-matchday gate: mirrors real pre-match team talks, not a
    free morale button spammable between advance_day calls."""
    state = load_game(_db(ctx))["state"]
    current_date = ctx["game_data"]["user"]["current_date"]
    last_date = state.get(f"team_talk_last_date_{_team_id(ctx)}")
    return {"available": last_date != current_date, "tones": list(TEAM_TALK_TONES.keys())}


@method("deliver_team_talk")
def _deliver_team_talk(params: dict, ctx: dict) -> dict:
    team_id, db = _team_id(ctx), _db(ctx)
    current_date = ctx["game_data"]["user"]["current_date"]
    state = load_game(db)["state"]
    if state.get(f"team_talk_last_date_{team_id}") == current_date:
        raise ValueError("A team talk has already been given today.")
    result = deliver_team_talk(str(params["tone"]))
    adjust_team_morale(team_id, result["delta"], db)
    save_game({f"team_talk_last_date_{team_id}": current_date}, db)
    return result


@method("get_press_conference")
def _get_press_conference(_params: dict, ctx: dict) -> dict:
    """Once-a-week gate — the first manager-driven lever on board
    confidence; previously it only ever moved via the passive season-end
    review (career.board_confidence, called once a season)."""
    db, team_id = _db(ctx), _team_id(ctx)
    current_date = ctx["game_data"]["user"]["current_date"]
    state = load_game(db)["state"]
    last_date = state.get(f"press_conference_last_date_{team_id}")
    available = True
    if last_date:
        available = (date.fromisoformat(current_date) - date.fromisoformat(last_date)).days >= 7
    return {"available": available, "question": press_conference_question(_team_position(ctx)),
           "tones": list(RESPONSE_TONES.keys())}


@method("answer_press_conference")
def _answer_press_conference(params: dict, ctx: dict) -> dict:
    db, team_id = _db(ctx), _team_id(ctx)
    current_date = ctx["game_data"]["user"]["current_date"]
    state = load_game(db)["state"]
    last_date = state.get(f"press_conference_last_date_{team_id}")
    if last_date and (date.fromisoformat(current_date) - date.fromisoformat(last_date)).days < 7:
        raise ValueError("No press conference scheduled yet — check back next week.")
    result = answer_press_conference(str(params["tone"]))
    adjust_team_morale(team_id, result["morale_delta"], db)
    history = get_board_confidence_history(team_id, db)
    base_score = history[-1]["score"] if history else 55
    score = max(5, min(98, base_score + result["confidence_delta"]))
    label = next(name for threshold, name in CONFIDENCE_LABELS if score >= threshold)
    record_board_confidence(team_id, score, label, f"{current_date} (press)", db)
    save_game({f"press_conference_last_date_{team_id}": current_date}, db)
    result["confidence_score"] = score
    result["confidence_label"] = label
    return result


@method("get_pitch_options")
def _get_pitch_options(_params: dict, ctx: dict) -> dict:
    current_pitch = get_pitch_selection(_team_id(ctx), _db(ctx))
    return {"types": PITCH_TYPES, "descriptions": PITCH_DESCRIPTIONS,
            "current": current_pitch}


@method("set_pitch_selection")
def _set_pitch_selection(params: dict, ctx: dict) -> dict:
    pitch = params.get("pitch", "Green")
    set_pitch_selection(_team_id(ctx), pitch, _db(ctx))
    return {"ok": True, "pitch": pitch}


@method("get_job_offers")
def _get_job_offers(_params: dict, ctx: dict) -> dict:
    return {"offers": get_job_offers(_db(ctx))}


@method("accept_job_offer")
def _accept_job_offer_ipc(params: dict, ctx: dict) -> dict:
    offer_id = params.get("offer_id", "")
    result = _accept_job_offer(offer_id, _db(ctx))
    ctx["team"] = get_team_summary(result["new_team_id"], _db(ctx))
    ctx["players"] = fetch_players(result["new_team_id"], _db(ctx))
    ctx["game_data"] = load_game(_db(ctx))
    return result


@method("decline_job_offer")
def _decline_job_offer_ipc(params: dict, ctx: dict) -> dict:
    offer_id = params.get("offer_id", "")
    _decline_job_offer(offer_id, _db(ctx))
    return {"ok": True}


@method("list_custom_tournaments")
def _list_custom_tournaments_ipc(_params: dict, ctx: dict) -> dict:
    return {"tournaments": get_custom_tournaments(_db(ctx))}


@method("get_custom_tournament")
def _get_custom_tournament_ipc(params: dict, ctx: dict) -> dict:
    tournament_id = params.get("tournament_id", 0)
    tournament = get_custom_tournament(tournament_id, _db(ctx))
    if not tournament:
        return {"error": "Tournament not found"}
    return tournament


@method("create_custom_tournament")
def _create_custom_tournament_ipc(params: dict, ctx: dict) -> dict:
    result = _create_custom_tournament(
        name=params.get("name", "Custom Tournament"),
        match_format=params.get("format", "T20"),
        team_ids=params.get("team_ids", []),
        advance_per_group=params.get("advance_per_group", 2),
        season=params.get("season", 2026),
        database_path=_db(ctx),
    )
    return result


@method("get_tournament_standings")
def _get_tournament_standings_ipc(params: dict, ctx: dict) -> dict:
    return get_tournament_standings(params.get("tournament_id", 0), _db(ctx))


@method("get_tournament_bracket")
def _get_tournament_bracket_ipc(params: dict, ctx: dict) -> dict:
    return get_tournament_bracket(params.get("tournament_id", 0), _db(ctx))


@method("advance_tournament_to_knockout")
def _advance_tournament_to_knockout_ipc(params: dict, ctx: dict) -> dict:
    from datetime import date as _date
    season = params.get("season", _date.today().year)
    result = _advance_tournament_to_knockout(
        params.get("tournament_id", 0), season, _db(ctx))
    if result is None:
        return {"error": "Group stage not yet complete"}
    return result


@method("get_onboarding_state")
def _get_onboarding_state_ipc(_params: dict, ctx: dict) -> dict:
    return get_onboarding_state(_db(ctx))


@method("get_onboarding_steps")
def _get_onboarding_steps_ipc(_params: dict, ctx: dict) -> dict:
    return {"steps": ONBOARDING_STEPS}


@method("advance_onboarding_step")
def _advance_onboarding_ipc(_params: dict, ctx: dict) -> dict:
    return _advance_onboarding(_db(ctx))


@method("dismiss_onboarding")
def _dismiss_onboarding_ipc(_params: dict, ctx: dict) -> dict:
    return _dismiss_onboarding(_db(ctx))


@method("advance_day")
def _advance_day(_params: dict, ctx: dict) -> dict:
    from competition import CompetitionEngine
    engine = CompetitionEngine(_db(ctx))
    events = engine.advance_day()
    ctx["game_data"] = load_game(_db(ctx))
    ctx["team"] = get_team_summary(_team_id(ctx), _db(ctx))
    ctx["players"] = fetch_players(_team_id(ctx), _db(ctx))
    return events


def build_context() -> dict[str, Any]:
    """Same boot sequence as main.py's bootstrap_game, minus pygame state.

    Real bug fixed here: this used to skip CompetitionEngine.ensure_season(),
    which main.py always calls on startup. A save that only ever went
    through the Godot client therefore had exactly one hardcoded demo
    fixture (seeded by database.py's _seed_phase_25_data) and then a
    permanently empty fixture list — no Domestic Division 1/2 league
    schedule or cup was ever generated. ensure_season() is idempotent
    (checks existing rows before inserting), so this is safe to call
    every time the backend starts, matching main.py exactly."""
    from competition import CompetitionEngine
    paths = get_launch_paths()
    state = prepare_environment(paths, interactive=False)
    initialise_database(state.paths.database)
    game_data = load_game(state.paths.database)
    CompetitionEngine(state.paths.database).ensure_season(date.fromisoformat(game_data["user"]["current_date"]).year)
    team = get_team_summary(game_data["user"]["current_team_id"], state.paths.database)
    players = fetch_players(team["id"], state.paths.database)
    context: dict[str, Any] = {"database_path": str(state.paths.database), "game_data": game_data,
                               "team": team, "players": players,
                               "new_game_setup": game_data["state"].get("new_game_setup", {})}
    # Mirrors main.py's self.game_controller = GameController(self.app_context,
    # self.set_active_screen, self.request_exit) — the navigate callback has
    # nothing to switch screens itself here, so it just records the intended
    # destination onto the shared ctx dict for the calling IPC method to
    # return to Godot, which does the actual navigation client-side.
    context["game_controller"] = GameController(
        context, navigate=lambda name: context.__setitem__("_pending_navigation", name),
        request_exit=lambda: None,
    )
    return context


def _respond(request_id: Any, *, result: Any = None, error: str | None = None) -> None:
    payload = {"id": request_id, "error": error} if error is not None else {"id": request_id, "result": result}
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def serve() -> None:
    context = build_context()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            _respond(None, error=f"invalid JSON: {exc}")
            continue
        request_id, method_name, params = request.get("id"), request.get("method"), request.get("params", {})
        if method_name == "quit":
            _respond(request_id, result={"bye": True})
            return
        handler = METHODS.get(method_name)
        if handler is None:
            _respond(request_id, error=f"unknown method: {method_name}")
            continue
        try:
            _respond(request_id, result=handler(params, context))
        except Exception as exc:  # noqa: BLE001 - report to the client instead of crashing the pipe
            _respond(request_id, error=f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    serve()
