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

from database import (add_bookmark as _add_bookmark, add_financial_transaction, adjust_players_morale, adjust_team_morale,
                      apply_daily_training, apply_match_player_updates,
                      browse_staff_market, check_sacking, create_inbox_message, evaluate_board_objectives,
                      fetch_active_injuries, fetch_club_records, fetch_facility_upgrades, fetch_financial_log, forecast_finances, summarise_finances,
                      fetch_honours, fetch_inbox_messages, fetch_last_result, fetch_league_standings, fetch_legends, fetch_next_fixture,
                      fetch_players, fetch_scouting_assignments, fetch_season_records, fetch_staff,
                      fetch_training_assignments, fetch_transfer_offers, get_board_confidence_history,
                       get_board_objectives, get_bookmarks as _get_bookmarks, get_cup_bracket,
                       get_current_international_competition,
                       get_custom_tournament, get_custom_tournaments,
                       get_data_hub as _get_data_hub,
                       get_ground_info, get_ground_stats, get_job_offers, get_match_ground_details,
                       get_ground_honours, get_player_honours,
                       fetch_calendar, facility_upgrade_cost,
                       get_onboarding_state, get_opposition_report, get_pitch_selection, get_pitch_status, get_player_form,
                       get_team_summary,
                       get_tournament_standings, advance_onboarding as _advance_onboarding,
                       dismiss_onboarding as _dismiss_onboarding,
                       initialise_database, load_game, make_staff_offer, mark_inbox_read,
                       ONBOARDING_STEPS, PITCH_DESCRIPTIONS, PITCH_TYPES,
                       PERSONALITIES, PERSONALITY_NAMES, PLAYER_TRAITS, TRAIT_NAMES,
                       record_board_confidence, record_ground_honour, record_player_chances, record_player_match_events, record_player_performance, recruit_youth,
                       remove_bookmark as _remove_bookmark,
                      resolve_staff_offer, resolve_transfer_offer, save_game,
                      scout_players, sell_staff_member, accept_job_offer as _accept_job_offer,
                      create_custom_tournament as _create_custom_tournament,
                      advance_tournament_to_knockout as _advance_tournament_to_knockout,
                      decline_job_offer as _decline_job_offer,
                      set_pitch_selection, set_training_focus,
                      set_training_schedule, start_facility_upgrade, submit_transfer_offer,
                      unread_inbox_count, update_user_settings)
from match_engine import FIELD_LAYOUT_PRESETS, FIELD_POSITIONS, Match
from src.controllers.game_controller import GameController
from src.models.career import CONFIDENCE_LABELS
from src.models.currency import currency_options, format_money
from src.models.manager import Manager, VALID_BACKGROUNDS
from src.models.morale import DROPPED_MORALE_PENALTY, dropped_from_xi, match_result_morale_deltas
from src.models.player import natural_batting_aggression
from src.models.press_conference import (RESPONSE_TONES, answer_press_conference, press_conference_question,
                                          press_conference_question_post_match)
from src.models.recruitment import contract_watch, role_gaps, weakest_attribute_group
from src.models.squad_metrics import group_average
from src.models.team_talks import TEAM_TALK_TONES, deliver_team_talk
from src.utilities.launcher import app_version, get_launch_paths, prepare_environment
import saves as saves_module

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
DEFAULT_MATCH_TACTICS = {"batting_aggression": 5, "bowling_aggression": 5, "field_preset": "Neutral",
                         # v4.13.0: True once set_field_layout has applied a
                         # custom drag-edited layout, so
                         # _apply_tactics_to_next_ball stops calling
                         # match.set_field(preset) every ball — that call
                         # reloads the preset's canonical layout wholesale
                         # and would otherwise silently stomp the custom
                         # edit back on the very next delivery.
                         "custom_field_layout": False,
                         # v4.21.0: the manager's chosen bowling target for
                         # the *next* delivery only — match_engine.py rolls a
                         # control-based chance to actually execute it (see
                         # Match._choose_delivery_line_length), so it is not
                         # re-applied automatically ball after ball the way
                         # aggression/field are; _apply_tactics_to_next_ball
                         # clears it once consumed.
                         "line_target": None, "length_target": None,
                         # v4.26.0: each not-out batter now carries their OWN
                         # aggression (previously one flat dial applied to
                         # whoever happened to be striking) — keyed by
                         # str(player_id). "linked" (default on, matching
                         # "build a partnership together") keeps both
                         # not-out batters' values equal whenever either is
                         # changed; turning it off lets them diverge.
                         "batting_aggression_by_id": {}, "batting_aggression_linked": True}
LINE_TARGETS = ["Leg Stump", "Middle", "Off Stump", "Wide"]
LENGTH_TARGETS = ["Short", "Good", "Full", "Yorker"]

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


def _game_mode(ctx: dict) -> str:
    return ctx["game_data"].get("state", {}).get("game_mode", "Career")


def _is_world_cup_mode(ctx: dict) -> bool:
    """v4.28.0: World Cup mode manages an already-assembled national squad
    for one tournament — no player development, following the same logic
    Football Manager's international-only saves use (you pick from who's
    already good enough, you don't train anyone up). Career mode is
    unaffected; this only gates the World Cup save flow."""
    return _game_mode(ctx) == "World Cup"


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
    # v4.28.0: Tournament mode removed — the custom-tournament flow it led
    # to never assigned the user a real club (team fell back to whatever
    # team_id happened to be current), a genuinely broken experience the
    # user hit directly. Career and World Cup are both complete.
    return {"countries": countries, "backgrounds": list(VALID_BACKGROUNDS),
           "modes": ["Career", "World Cup"], "difficulties": ["Easy", "Normal", "Hard"]}


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


## v0.90.0: real multi-save-slot system. Previously "Load Game" just
## re-entered whatever the single existing database held — there was no
## save-slot concept anywhere. Saves live under saves.save_database_path()
## (writable_root/saves/<id>.db); listing metadata (team/manager/date) is
## always read live from each save's own database rather than cached, so it
## can't drift from what the save actually contains.
@method("list_saves")
def _list_saves_ipc(_params: dict, ctx: dict) -> dict:
    return {"saves": saves_module.list_saves(Path(ctx["_writable_root"])),
           "active_save_id": ctx.get("_active_save_id")}


@method("create_save")
def _create_save_ipc(params: dict, ctx: dict) -> dict:
    writable_root = Path(ctx["_writable_root"])
    created = saves_module.create_save(writable_root, params.get("display_name", "New Save"))
    saves_module.write_active_save_id(writable_root, created["id"])
    saves_module.touch_last_played(writable_root, created["id"])
    ctx["_active_save_id"] = created["id"]
    _bind_database(ctx, created["database_path"])
    return {"id": created["id"], "destination": "New Game Setup"}


@method("load_save")
def _load_save_ipc(params: dict, ctx: dict) -> dict:
    writable_root = Path(ctx["_writable_root"])
    save_id = str(params["id"])
    database_path = saves_module.save_database_path(writable_root, save_id)
    if not database_path.exists():
        raise ValueError(f"Unknown save: {save_id}")
    saves_module.write_active_save_id(writable_root, save_id)
    saves_module.touch_last_played(writable_root, save_id)
    ctx["_active_save_id"] = save_id
    _bind_database(ctx, database_path)
    has_team = bool(ctx["game_data"]["user"].get("current_team_id"))
    return {"team": ctx["team"], "destination": "Dashboard" if has_team else "Career Team Selection"}


@method("delete_save")
def _delete_save_ipc(params: dict, ctx: dict) -> dict:
    writable_root = Path(ctx["_writable_root"])
    save_id = str(params["id"])
    if save_id == ctx.get("_active_save_id"):
        raise ValueError("Cannot delete the save currently in progress.")
    saves_module.delete_save(writable_root, save_id)
    return {"saves": saves_module.list_saves(writable_root)}


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


## Adds "career_*"-prefixed lifetime batting/bowling figures (matches,
## innings, runs, batting average, strike rate, overs, wickets, bowling
## average, economy) to each player dict, combined across every format
## context via src.models.player_records.combined_record — feeds the Squad/
## Selection screens' STATS tab (a real county-squad-style combined column
## set, reference: M/Inns/Runs/SR%/Bat avg/Overs/Wkts/Econ per player).
def _with_career_stats(players: list[dict], database_path) -> list[dict]:
    from database import fetch_player_records
    from src.models.player_records import combined_record
    out = []
    for p in players:
        combined = combined_record(fetch_player_records(int(p["id"]), database_path))
        out.append({**p, "career_matches": combined["matches"], "career_innings": combined["innings"],
                   "career_runs": combined["runs"], "career_batting_average": combined["batting_average"],
                   "career_strike_rate": combined["strike_rate"], "career_overs": combined["overs"],
                   "career_wickets": combined["wickets"], "career_bowling_average": combined["bowling_average"],
                   "career_economy": combined["economy"]})
    return out


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
    players = _with_career_stats(players, _db(ctx))
    return {"team": ctx["team"], "players": players}


def _selection_locked(ctx: dict) -> bool:
    """v4.29.0: Football Manager-style squad lockdown — once a match is
    actually live (start_match called, not yet finalised), the XI/captain/
    keeper/batting-order/tactics you submitted are locked for that match,
    matching how FM won't let you re-pick your XI mid-game. Before kickoff
    (even on match day itself, right up until START MATCH) selection stays
    fully editable, same as FM."""
    match = ctx.get("match")
    return match is not None and not match.completed


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
        mental = p.get("mental", {})
        physical = p.get("physical", {})
        # Keep the selection payload presentation-ready.  These values are
        # derived from the same nested player documents used by the engine,
        # so the Godot client never has to duplicate attribute rules.
        players.append({**p, "selected": p["id"] in xi_set, "xi_status": "/".join(tags),
                       "batting_style": style, "batting_aggression": aggression,
                       "freshness": 100 - int(p.get("fatigue", 0)),
                       "fitness_value": int(mental.get("fitness", physical.get("fitness", 0))),
                       "morale_value": int(mental.get("morale", 0)),
                       "form_value": int(p.get("form", 0)),
                       "bowling_capable": p.get("role") in ("Bowler", "All-Rounder")})
    bowlers = sum(1 for p in players if p.get("selected") and p.get("bowling_capable"))
    players = _with_career_stats(players, _db(ctx))
    return {"players": players, "xi_count": len(xi_set), "captain_id": captain_id, "keeper_id": keeper_id,
           "bowlers_in_xi": bowlers, "required_bowlers": 5,
           "locked": _selection_locked(ctx)}


def _set_leadership_role(ctx: dict, role_key: str, player_id: int) -> dict:
    """Shared by set_captain/set_keeper: toggle a role, only within the XI —
    mirrors ui/selection.py's captain/keeper cycle buttons, which only
    cycle through self.xi."""
    if _selection_locked(ctx):
        raise ValueError("Squad is locked — a match is already in progress.")
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
    if _selection_locked(ctx):
        raise ValueError("Squad is locked — a match is already in progress.")
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
    if _selection_locked(ctx):
        raise ValueError("Squad is locked — a match is already in progress.")
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
    if _selection_locked(ctx):
        raise ValueError("Squad is locked — a match is already in progress.")
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
    if _selection_locked(ctx):
        raise ValueError("Squad is locked — a match is already in progress.")
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


@method("get_calendar")
def _get_calendar(_params: dict, ctx: dict) -> dict:
    """v4.27.0: a real Calendar screen — every fixture (played and
    upcoming) plus a weekday breakdown of the squad's training days.
    Repeatedly asked for; both reuse existing tables (matches,
    training_assignments), no new schema."""
    calendar = fetch_calendar(_team_id(ctx), _db(ctx))
    calendar["current_date"] = ctx["game_data"]["user"]["current_date"]
    return calendar


def _best_xi(players: list[dict]) -> list[dict]:
    """Mirrors ui/pre_match.py's fallback when the manager hasn't set a
    full XI on Selection: the best-rated keeper first, then the rest by
    overall, same as pygame does before a live match can start.

    The keeper is placed at batting position 7 (a realistic lower-middle-
    order spot), not at the top of the order — see classify_keeper_batting_role."""
    from database import classify_keeper_batting_role
    keepers = [p for p in players if p.get("role") == "Wicketkeeper"]
    keeper = keepers[0] if keepers else None
    rest = [p for p in players if p != keeper]
    rest = sorted(rest, key=lambda p: p.get("overall", 0), reverse=True)[:10]
    # Keeper bats at position 7 (after 6 others) — the classic lower-middle order
    xi = rest[:6] + ([keeper] if keeper else []) + rest[6:]
    return xi[:11]


## A simple, honest heuristic (runs + milestone bonus for batting, wickets*20
## minus economy penalty for bowling) across every innings a player appeared
## in — no existing "player of the match" concept anywhere in the engine to
## reuse, so this is new. Only meaningful once the match has actually
## finished (see _match_state's completed-only call site).
def _man_of_the_match(match: Match) -> dict | None:
    scores: dict[int, float] = {}
    names: dict[int, str] = {}
    for innings in match.innings:
        for pid, line in innings.batters.items():
            if line.balls or line.dismissal != "did not bat":
                bonus = 10.0 if line.runs >= 100 else 5.0 if line.runs >= 50 else 0.0
                scores[pid] = scores.get(pid, 0.0) + line.runs + bonus
                names[pid] = line.name
        for pid, line in innings.bowlers.items():
            if line.balls:
                scores[pid] = scores.get(pid, 0.0) + line.wickets * 20.0 - line.runs * 0.5
                names[pid] = line.name
    if not scores:
        return None
    best_id = max(scores, key=lambda k: scores[k])
    return {"player_id": best_id, "name": names.get(best_id, "?"), "score": round(scores[best_id], 1)}


def _career_figures(player, match_format: str, database_path: str) -> dict:
    """v4.55.0: career batting/bowling figures for a live match player so the
    Godot matchday cards can show the reference's 'Format Batting Avg/SR' and
    'Format Bowling Avg' lines. Prefers the current match's format-context
    record (format_context labels, e.g. domestic T20 = '20 Over'), falling
    back to the combined-across-formats career total when that context has
    never been played yet."""
    from database import fetch_player_records
    from src.models.player_records import combined_record, format_context
    records = fetch_player_records(int(player["id"]), database_path)
    rec = None
    for international in (False, True):
        rec = records.get(format_context(match_format, international))
        if rec:
            break
    if rec is None:
        rec = combined_record(records)
    return {"career_batting_average": float(rec.get("batting_average", 0.0) or 0.0),
            "career_strike_rate": float(rec.get("strike_rate", 0.0) or 0.0),
            "career_bowling_average": float(rec.get("bowling_average", 0.0) or 0.0)}


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
    db_path = _db(ctx)
    striker_career = _career_figures(striker, match.format, db_path) if striker else {}
    non_striker_career = _career_figures(non_striker, match.format, db_path) if non_striker else {}
    bowler_career = _career_figures(bowler, match.format, db_path) if bowler else {}
    # v4.22.0: which side the manager's own team is on THIS innings — the
    # Godot client uses this to show only the Bowler Card while fielding or
    # only the Batsman Card while batting, never both at once (a manager is
    # never doing both jobs on the same delivery).
    user_is_bowling = bool(innings and innings.bowling_team == _team_id(ctx))
    tactics = _match_tactics(ctx)
    by_id = tactics["batting_aggression_by_id"]
    default_aggro = tactics["batting_aggression"]
    return {"format": match.format, "completed": match.completed, "result": match.result,
           "man_of_the_match": _man_of_the_match(match) if match.completed else None,
           "status": match.match_status(), "pitch": match.pitch, "weather": match.weather,
           "home_team": match.home_team_id, "away_team": match.away_team_id,
           "user_is_bowling": user_is_bowling,
           "current_innings_index": match.current_innings_index,
           "balls_per_set": match.balls_per_set, "overs_limit": match.overs_limit(),
           "innings": [match.scorecard(i) for i in range(len(match.innings))],
           "striker": {"id": striker["id"], "name": striker["name"],
                      "aggression": by_id.get(str(striker["id"]), default_aggro), **striker_career} if striker else None,
           "non_striker": {"id": non_striker["id"], "name": non_striker["name"],
                          "aggression": by_id.get(str(non_striker["id"]), default_aggro), **non_striker_career} if non_striker else None,
           "bowler": {"id": bowler["id"], "name": bowler["name"], "fatigue": int(bowler.get("fatigue", 0)), **bowler_career} if bowler else None,
           "last_six": list(match.last_six), "field_preset": match.field_setting,
           "field_layout": match.field_layout_by_team.get(innings.bowling_team, {}) if innings else {},
           "reviews_remaining": match.reviews.get(_team_id(ctx), 0),
           "eligible_bowlers": eligible_bowlers,
           "batting_aggression": default_aggro,
           "batting_aggression_linked": tactics.get("batting_aggression_linked", True),
           "bowling_aggression": tactics["bowling_aggression"],
           "line_target": tactics.get("line_target"),
           "length_target": tactics.get("length_target"),
           "line_targets": LINE_TARGETS, "length_targets": LENGTH_TARGETS}


def _match_tactics(ctx: dict) -> dict:
    if "_match_tactics" not in ctx:
        # Plain dict(DEFAULT_MATCH_TACTICS) is only a SHALLOW copy — the
        # nested batting_aggression_by_id dict would otherwise be the same
        # object shared (and mutated) across every match/context, silently
        # leaking one match's per-batter aggression into the next.
        tactics = dict(DEFAULT_MATCH_TACTICS)
        tactics["batting_aggression_by_id"] = {}
        ctx["_match_tactics"] = tactics
    return ctx["_match_tactics"]


def _apply_tactics_to_next_ball(ctx: dict, match: Match) -> None:
    """Mirrors ui/match_view.py's simulate_ball(): pushes the manager's
    live batting/bowling aggression sliders and field preset onto the
    engine right before each delivery — batting aggression is averaged
    with the striker's Selection-screen batting style (same STYLES
    weighting pygame uses), bowling aggression is applied directly."""
    tactics = _match_tactics(ctx)
    if not tactics.get("custom_field_layout"):
        match.set_field(tactics["field_preset"])
    innings = match.current_innings
    striker = innings.striker_player
    bowler = next((p for p in innings.bowling_squad if int(p["id"]) == innings.current_bowler_id), None)
    selection = ctx["game_data"].get("state", {}).get("selection", {})
    style = selection.get("batting_styles", {}).get(str(striker["id"]), "Build")
    style_value = BATTING_STYLE_VALUES.get(style, 5)
    # v4.26.0: each not-out batter carries their own aggression now — fall
    # back to the flat tactics["batting_aggression"] default only for a
    # batter who's never had a value set for them individually.
    striker_aggro = tactics["batting_aggression_by_id"].get(str(striker["id"]), tactics["batting_aggression"])
    striker["batting_aggression"] = round((striker_aggro + style_value) / 2)
    if bowler is not None:
        bowler["bowling_aggression"] = round(tactics["bowling_aggression"])
        bowler["_target_line"] = tactics.get("line_target")
        bowler["_target_length"] = tactics.get("length_target")
    # One-shot: the manager targets a specific delivery (mirrors an actual
    # bowler being told "yorker at leg stump" for THIS ball, not the rest of
    # the spell) — cleared here so the next delivery needs a fresh choice.
    tactics["line_target"] = None
    tactics["length_target"] = None


def _record_match_honours(ctx: dict, match: Match, fixture: dict,
                          career_lines: dict[int, dict[str, list[dict]]]) -> None:
    """Automatically record centuries and five-wicket hauls on the match's ground."""
    db_path = _db(ctx)
    ground_id = get_ground_info(int(fixture["home_team"]), db_path).get("id")
    if not ground_id:
        return
    by_id = {p["id"]: p for p in ctx["players"]}
    if int(fixture["home_team"]) == _team_id(ctx):
        opp = fixture.get("away_team_name", "")
    else:
        opp = fixture.get("home_team_name", "")
    match_format = fixture.get("format", "T20")
    match_date = ctx["game_data"]["user"]["current_date"]
    match_id = int(fixture["id"])

    for player_id, lines in career_lines.items():
        player = by_id.get(player_id)
        if not player:
            continue
        pname = player["name"]
        team_id = int(player.get("team_id", 0))

        for bl in lines["batting"]:
            runs = bl.get("runs", 0)
            if runs >= 100:
                record_ground_honour(player_id, pname, team_id, ground_id, "CENTURY",
                                     match_id, match_date, runs, 0, match_format, db_path)

        for bwl in lines["bowling"]:
            wkts = bwl.get("wickets", 0)
            if wkts >= 5:
                record_ground_honour(player_id, pname, team_id, ground_id, "FIVE_WICKETS",
                                     match_id, match_date, bwl.get("runs", 0), wkts, match_format, db_path)


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
             "winner": match.winner_id, "tied": match.winner_id is None and not match.drawn,
             "drawn": match.drawn,
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
    from src.models.player_records import format_context
    record_context = format_context(fixture.get("format", "T20"), international=False)
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
    _record_match_honours(ctx, match, fixture, career_lines)
    record_player_match_events(int(fixture["id"]), 1, match.shot_events, match.bowling_events, _db(ctx))
    record_player_chances(int(fixture["id"]), match.chance_log, _db(ctx))
    ctx["team"] = get_team_summary(_team_id(ctx), _db(ctx))
    ctx["players"] = fetch_players(_team_id(ctx), _db(ctx))
    # Check for achievements
    _check_match_achievements(ctx, match, home_id, away_id)




def _check_match_achievements(ctx, match, home_id, away_id):
    """Check for match-related achievements and unlock them."""
    steam = ctx.get("steam")
    if not steam:
        return
    user_team_id = _team_id(ctx)
    # Check for centuries
    for innings in match.innings:
        for player in innings.batting_order:
            line = innings.batters[int(player["id"])]
            if line.runs >= 100:
                steam.unlock_achievement("ACH_CENTURY_MAKER")
            if line.runs >= 200:
                steam.unlock_achievement("ACH_DOUBLE_CENTURY")
    # Check for five-wicket hauls
    for innings in match.innings:
        for player in innings.bowling_squad:
            line = innings.bowlers[int(player["id"])]
            if line.wickets >= 5:
                steam.unlock_achievement("ACH_FIVE_WICKET_HAUL")
    # Check for perfect game (win without losing any wickets)
    if match.winner_id == user_team_id:
        user_innings = [i for i in match.innings if i.batting_team == user_team_id]
        if user_innings and all(i.wickets == 0 for i in user_innings):
            steam.unlock_achievement("ACH_PERFECT_GAME")
    # Check for Test debut
    if match.overs_limit() >= 90:
        steam.unlock_achievement("ACH_TEST_DEBUT")

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
    match = Match(home_team, away_team, home_xi, away_xi, fixture.get("format", "T20"),
                   pitch=pitch, ground_info=get_ground_info(home_id, _db(ctx)))
    ctx["match"] = match
    ctx["_active_fixture"] = fixture
    ctx["_match_finalised"] = False
    # See _match_tactics()'s comment: dict(DEFAULT_MATCH_TACTICS) alone
    # would share the nested batting_aggression_by_id dict across matches.
    new_tactics = dict(DEFAULT_MATCH_TACTICS)
    new_tactics["batting_aggression_by_id"] = {}
    ctx["_match_tactics"] = new_tactics
    return _match_state(match, ctx)


@method("get_match_state")
def _get_match_state(_params: dict, ctx: dict) -> dict:
    """The Godot Match screen's refresh() probes this on every re-entry to
    decide whether to show the live view or the pre-match hub. A finished,
    finalised match must NOT still look "in progress" here — otherwise
    revisiting Match Day for the *next* fixture (e.g. after advance_day
    redirects there) shows the previous match's stale completed scorecard
    forever, with every control disabled and no way to start the new one
    (the actual bug reported: stuck, unable to play or advance). Once a
    match is both completed and finalised (_finalise_match already ran —
    see _simulate_balls below), treat it exactly like no match at all so
    the client falls back to the pre-match hub for whatever's next."""
    match = ctx.get("match")
    if match is None or (match.completed and ctx.get("_match_finalised")):
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
    tactics = _match_tactics(ctx)
    tactics["field_preset"] = preset
    # A quick-preset pick resets any custom drag-edited layout — matches
    # how the field editor is meant to work (presets + fine-tuning on top,
    # not two states fighting each other).
    tactics["custom_field_layout"] = False
    match.set_field(preset)
    return _match_state(match, ctx)


@method("set_match_aggression")
def _set_match_aggression(params: dict, ctx: dict) -> dict:
    """Mirrors ui/match_view.py's batting/bowling aggression sliders
    (1-10, same scale as Selection's per-player aggression) — applied to
    the striker/bowler on every subsequent delivery by
    _apply_tactics_to_next_ball, not persisted anywhere beyond this
    match.

    v4.26.0: batting aggression is now set per not-out batter
    (params["player_id"]), not one flat dial for whoever's striking. When
    "linked" (the default — mirrors trying to build a partnership by
    batting to a shared plan), setting either not-out batter's aggression
    sets BOTH to the same value; pass params["linked"] to change the mode
    for this match. Omitting player_id keeps the old flat-dial behaviour
    for any caller that doesn't care which batter (e.g. existing tests)."""
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    tactics = _match_tactics(ctx)
    if "linked" in params:
        tactics["batting_aggression_linked"] = bool(params["linked"])
    if "batting" in params:
        value = max(1, min(10, int(params["batting"])))
        player_id = params.get("player_id")
        if player_id is None:
            # Legacy flat-dial call (no particular batter named) — only
            # this path touches the shared default, so a player-specific
            # call below can never leak into an un-set partner's fallback.
            tactics["batting_aggression"] = value
        else:
            tactics["batting_aggression_by_id"][str(int(player_id))] = value
            if tactics.get("batting_aggression_linked", True):
                innings = match.current_innings if not match.completed else None
                if innings is not None:
                    for other in (innings.striker_player, innings.non_striker_player):
                        if other is not None:
                            tactics["batting_aggression_by_id"][str(int(other["id"]))] = value
    if "bowling" in params:
        tactics["bowling_aggression"] = max(1, min(10, int(params["bowling"])))
    return _match_state(match, ctx)


@method("set_delivery_target")
def _set_delivery_target(params: dict, ctx: dict) -> dict:
    """The manager picks where the bowler should aim the *next* ball —
    "yorker at leg stump" — mirroring the Cricket Captain pitch-strip
    targeting UI. One-shot: _apply_tactics_to_next_ball consumes and
    clears it after a single delivery, and Match._choose_delivery_line_length
    only honours it with a control-skill-based chance (a bowler doesn't
    execute every instruction perfectly), so this is a real tactical nudge,
    not a guarantee."""
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    line = params.get("line")
    length = params.get("length")
    if line is not None and line not in LINE_TARGETS:
        raise ValueError(f"Unknown line target: {line}")
    if length is not None and length not in LENGTH_TARGETS:
        raise ValueError(f"Unknown length target: {length}")
    tactics = _match_tactics(ctx)
    tactics["line_target"] = line
    tactics["length_target"] = length
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


@method("set_match_bowler")
def _set_match_bowler(params: dict, ctx: dict) -> dict:
    """A real bowler picker (v4.13.0), replacing blind cycle_match_bowler
    cycling — Match.set_bowler(player_id) already validates eligibility
    (must be in _eligible_bowlers(), can't repeat the previous over's
    bowler outside The Hundred), so this is a thin wrapper, not new engine
    logic."""
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    player_id = int(params.get("player_id", -1))
    changed = not match.completed and match.set_bowler(player_id)
    result = _match_state(match, ctx)
    result["bowler_changed"] = changed
    return result


@method("get_field_layout")
def _get_field_layout(_params: dict, ctx: dict) -> dict:
    """The field-editor's data source (v4.13.0, Part 2 of the Match Day
    rebuild): the full position catalog, the 3 canonical preset layouts
    (for the editor's quick-preset buttons), and the currently bowling
    team's real layout."""
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    bowling_team = match.current_innings.bowling_team if not match.completed else None
    layout = match.field_layout_by_team.get(bowling_team, {}) if bowling_team is not None else {}
    return {"positions": FIELD_POSITIONS,
           "presets": {name: dict(preset) for name, preset in FIELD_LAYOUT_PRESETS.items()},
           "layout": layout}


@method("set_field_layout")
def _set_field_layout(params: dict, ctx: dict) -> dict:
    """Applies a fully custom per-fielder layout to whichever team is
    currently bowling — the real drag-and-place field editor's target
    (v4.13.0, Part 2). Marks the layout as custom so
    _apply_tactics_to_next_ball stops reloading the preset every ball,
    which would otherwise silently overwrite the edit on the very next
    delivery."""
    match = ctx.get("match")
    if match is None:
        raise ValueError("No match in progress — call start_match first.")
    if match.completed:
        raise ValueError("Match has already completed.")
    positions = params.get("positions")
    if not isinstance(positions, dict):
        raise ValueError("positions must be a dict of {position_name: {angle, radius}}")
    layout = match.set_field_layout(match.current_innings.bowling_team, positions)
    _match_tactics(ctx)["custom_field_layout"] = True
    return {"layout": layout, "state": _match_state(match, ctx)}


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


## New in v4.53.0: backs the Godot League Standings screen — real
## P/W/L/D/T/Bat/Bwl/Pts/NRR for any division (Division 1/2 tab switch,
## reference: the County Championship table screenshot), not just
## fetch_league_standings()'s Division-1-only Dashboard crop.
@method("get_division_standings")
def _get_division_standings(params: dict, ctx: dict) -> dict:
    from database import fetch_division_match_count, fetch_division_standings
    from src.models.league_config import LEAGUE_NAMES
    division = int(params.get("division", 1))
    rows = fetch_division_standings(division, _db(ctx))
    standings = [dict(position=i + 1, **row) for i, row in enumerate(rows)]
    return {"division": division, "standings": standings,
           "league_name": LEAGUE_NAMES.get(division, "Division %d" % division),
           "matches_per_team": fetch_division_match_count(division, _db(ctx))}


## v4.57.0: per-nation domestic leagues (src/models/nations_config.py) were
## generated in v4.56.0 but never surfaced to either client — these back a
## nation picker on the League Standings screen alongside the existing
## global Division 1/2 tabs (additive, not a replacement — see docs/CURRENT.md).
@method("get_nation_leagues")
def _get_nation_leagues(_params: dict, ctx: dict) -> dict:
    from database import fetch_nation_leagues
    return {"leagues": fetch_nation_leagues(_db(ctx))}


@method("get_nation_league_standings")
def _get_nation_league_standings(params: dict, ctx: dict) -> dict:
    from database import fetch_nation_league_match_count, fetch_nation_league_standings
    country_id = str(params.get("country_id", "england"))
    competition_name = str(params.get("competition_name", ""))
    division = params.get("division")
    division = int(division) if division not in (None, "") else None
    rows = fetch_nation_league_standings(country_id, competition_name, division, _db(ctx))
    standings = [dict(position=i + 1, **row) for i, row in enumerate(rows)]
    return {"country_id": country_id, "competition_name": competition_name, "division": division,
           "standings": standings,
           "matches_per_team": fetch_nation_league_match_count(competition_name, _db(ctx))}


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
    # v4.24.0 fix: this passed limit=None, so scout_players() scanned and
    # scored the ENTIRE player pool (~2500 players, minus the user's own
    # squad) with a per-player sale_assessment/apply_scouting_estimate call
    # every single time Transfers OR Offers opened (Offers reuses this same
    # method purely for its "offers" field) — a real multi-second freeze,
    # not a rendering issue. 150 comfortably covers a real scouted shortlist
    # and matches how these games actually present a transfer market (a
    # filtered/narrowed list, not the whole database at once).
    players = scout_players(params.get("role", "All"), params.get("minimum_age", 16),
                            params.get("maximum_age", 45), params.get("minimum_overall", 0),
                            params.get("maximum_overall", 100), params.get("nationality", "All"),
                            team_id, int(params.get("limit", 150)), db)
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
    """v4.29.0: was a single flat chronological transaction list with no
    totals — the user asked for income/expenses split with running
    totals and a recurring (monthly, matching this data's real posting
    cadence) figure. Kept the full transaction list too, split by kind,
    for the two-column detail view."""
    transactions = [{**t, "amount_display": format_money(t["amount"])}
                    for t in fetch_financial_log(_team_id(ctx), _db(ctx))]
    income = [t for t in transactions if t["kind"] == "INCOME"]
    expenses = [t for t in transactions if t["kind"] == "EXPENSE"]
    summary = summarise_finances(_team_id(ctx), _db(ctx))
    summary_display = {
        "total_income_display": format_money(summary["total_income"]),
        "total_expenses_display": format_money(summary["total_expenses"]),
        "net_display": format_money(summary["net"]),
        "cash_display": format_money(ctx["team"].get("cash", 0)),
        "month_income_display": format_money(summary["month_income"]),
        "month_expenses_display": format_money(summary["month_expenses"]),
        "month_net_display": format_money(summary["month_net"]),
        "latest_month": summary["latest_month"],
    }
    return {"team": ctx["team"], "transactions": transactions, "income": list(reversed(income)),
           "expenses": list(reversed(expenses)), "summary": {**summary, **summary_display}}


@method("get_financial_forecast")
def _get_financial_forecast(params: dict, ctx: dict) -> dict:
    """v4.31.0: long-term budget projection for the Finances screen. A
    forward view (default 12 months) of committed cash flow — player
    wages and sponsorship — plus estimated matchday income from home
    fixtures already on the calendar, flagging any month where the
    projected balance drops below the board's minimum-cash objective."""
    months = max(1, min(int(params.get("months", 12)), 36))
    forecast = forecast_finances(_team_id(ctx), _db(ctx), months=months)
    forecast["starting_cash_display"] = format_money(forecast["starting_cash"])
    forecast["ending_cash_display"] = format_money(forecast["ending_cash"])
    forecast["minimum_cash_display"] = format_money(forecast["minimum_cash"])
    forecast["months"] = [
        {**m,
         "income_display": format_money(m["income"]),
         "expenses_display": format_money(m["expenses"]),
         "net_display": format_money(m["net"]),
         "cash_display": format_money(m["cash"]),
         "lines": [{**ln, "amount_display": format_money(ln["amount"])} for ln in m["lines"]]}
        for m in forecast["months"]
    ]
    return forecast


FACILITY_LEVEL_KEYS = {
    "Stadium": "stadium_level", "Training Ground": "training_level",
    "Medical Centre": "medical_level", "Academy": "academy_level",
    "Commercial Office": "commercial_level", "Scouting Network": "scouting_level",
    "Grounds Department": "grounds_level",
}


@method("get_facilities")
def _get_facilities(_params: dict, ctx: dict) -> dict:
    """v4.28.0: the UPGRADE button used to be clickable regardless of
    state, so upgrading an already-building facility surfaced a raw
    backend ValueError, and there was no visible cost or ETA anywhere
    before committing — both existed server-side (start_facility_upgrade
    already charges cash and sets a 7-day completion_date) but were never
    returned to the client. Now: UPGRADE is only offered
    (facility_upgrade=True) when it's actually legal, and every row shows
    either the real upgrade cost or a "ready in Nd" ETA."""
    team = ctx["team"]
    upgrades = fetch_facility_upgrades(_team_id(ctx), _db(ctx))
    building_by_facility = {u["facility"]: u for u in upgrades if u["status"] == "BUILDING"}
    current_date = ctx["game_data"]["user"]["current_date"]
    facilities = []
    for name, key in FACILITY_LEVEL_KEYS.items():
        level = int(team.get(key, 1))
        pending = building_by_facility.get(name)
        if pending:
            days_left = max(0, (date.fromisoformat(pending["completion_date"]) - date.fromisoformat(current_date)).days)
            status = "Building — ready in %d day%s" % (days_left, "" if days_left == 1 else "s")
            upgradeable = False
        elif level >= 5:
            status = "Max level"
            upgradeable = False
        else:
            status = "Ready — %s to upgrade" % format_money(facility_upgrade_cost(name, level))
            upgradeable = True
        facilities.append({"facility": name, "level": level, "status": status,
                            "facility_upgrade": upgradeable})
    return {"team": team, "upgrades": upgrades, "facilities": facilities}


@method("upgrade_facility")
def _upgrade_facility(params: dict, ctx: dict) -> dict:
    result = start_facility_upgrade(_team_id(ctx), params["facility"],
                                    ctx["game_data"]["user"]["current_date"], _db(ctx))
    ctx["team"] = get_team_summary(_team_id(ctx), _db(ctx))
    return result


@method("get_training")
def _get_training(_params: dict, ctx: dict) -> dict:
    # v4.28.0: World Cup mode manages an already-assembled national squad
    # for one tournament — no player development, mirroring how Football
    # Manager's international-only saves work. world_cup_mode tells the
    # Godot Training screen to show that explanation instead of the table.
    if _is_world_cup_mode(ctx):
        return {"players": [], "assignments": {}, "world_cup_mode": True}
    assignments = fetch_training_assignments(_team_id(ctx), _db(ctx))
    # Flattens each player's assignment (if any) onto the player dict so
    # the Godot client can render this as a plain table like every other
    # list screen, instead of merging two separate structures itself.
    players = [{**p, "focus": assignments.get(p["id"], {}).get("focus") or "None",
               "intensity": assignments.get(p["id"], {}).get("intensity", "Normal"),
               "last_trained": assignments.get(p["id"], {}).get("last_trained") or "—"}
              for p in ctx["players"]]
    return {"players": players, "assignments": {str(k): v for k, v in assignments.items()}, "world_cup_mode": False}


def _training_assignment(ctx: dict, player_id: int) -> dict:
    default = {"focus": "None", "intensity": "Normal", "days": [0, 2, 4]}
    return fetch_training_assignments(_team_id(ctx), _db(ctx)).get(player_id, default)


@method("cycle_training_focus")
def _cycle_training_focus(params: dict, ctx: dict) -> dict:
    """Mirrors ui/training.py's PROGRAMME cycle button/column: steps a
    player's training programme through TRAINING_FOCUSES (wrapping)."""
    if _is_world_cup_mode(ctx):
        raise ValueError("Training is not available in World Cup mode.")
    player_id = int(params["player_id"])
    current = _training_assignment(ctx, player_id)["focus"]
    next_focus = TRAINING_FOCUSES[(TRAINING_FOCUSES.index(current) + 1) % len(TRAINING_FOCUSES)]
    set_training_focus(player_id, next_focus, _db(ctx))
    return _get_training({}, ctx)


@method("cycle_training_intensity")
def _cycle_training_intensity(params: dict, ctx: dict) -> dict:
    """Mirrors ui/training.py's INTENSITY cycle button/column: steps
    Light/Normal/Heavy (wrapping), keeping the current focus and days."""
    if _is_world_cup_mode(ctx):
        raise ValueError("Training is not available in World Cup mode.")
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
    if _is_world_cup_mode(ctx):
        raise ValueError("Training is not available in World Cup mode.")
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
    if _is_world_cup_mode(ctx):
        raise ValueError("Training is not available in World Cup mode.")
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
    if _is_world_cup_mode(ctx):
        raise ValueError("Training is not available in World Cup mode.")
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
    # v4.29.0: minimum_overall is applied here rather than in
    # browse_staff_market's SQL — overall is a derived per-role figure
    # computed from the attributes JSON after the query runs, not a stored
    # column, so it can only be filtered post-fetch.
    staff = browse_staff_market(params.get("group", "All"), _team_id(ctx),
                                int(params.get("limit", 30)), _db(ctx))
    minimum_overall = int(params.get("minimum_overall", 0))
    if minimum_overall:
        staff = [s for s in staff if s["overall"] >= minimum_overall]
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
    # v4.28.0: no youth development in World Cup mode either — same "pick
    # from who's already good enough" logic as Training.
    if _is_world_cup_mode(ctx):
        return {"team": ctx["team"], "recruitment_fee_display": format_money(ACADEMY_RECRUITMENT_FEE),
               "players": [], "world_cup_mode": True}
    players = _academy_eligible(ctx)
    return {"team": ctx["team"], "recruitment_fee_display": format_money(ACADEMY_RECRUITMENT_FEE),
           "players": [{**p, "wage_display": format_money(p["wage"]),
                       "batting_avg": group_average(p, "batting"),
                       "bowling_avg": group_average(p, "bowling"),
                       "fielding_avg": group_average(p, "fielding")}
                      for p in players], "world_cup_mode": False}


@method("set_academy_focus")
def _set_academy_focus(params: dict, ctx: dict) -> dict:
    """Mirrors ui/youth.py's FOCUS button: applies one collective training
    programme to every academy-eligible player (Balanced/Batting/Bowling/
    Fielding, mapped onto the same programmes Training uses)."""
    if _is_world_cup_mode(ctx):
        raise ValueError("The Youth Academy is not available in World Cup mode.")
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
    if _is_world_cup_mode(ctx):
        raise ValueError("The Youth Academy is not available in World Cup mode.")
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


def _press_conference_window(ctx: dict) -> dict:
    """v4.30.0: was a flat once-a-week timer, disconnected from match day
    entirely — the user asked for it to happen "before a match and after
    a match", mirroring how FM/Cricket Captain always tie pressers to the
    fixture just played or about to be played. A post-match presser for
    the most recently completed fixture takes priority (there's a result
    to talk about); otherwise a pre-match presser opens for the next
    fixture. Each is a once-per-fixture gate (state key keyed by match id,
    not by date), so it can't be spammed between advance_day calls."""
    db, team_id = _db(ctx), _team_id(ctx)
    state = load_game(db)["state"]
    last_result = fetch_last_result(team_id, db)
    if last_result and not state.get(f"press_conference_done_{team_id}_{last_result['id']}"):
        opponent = last_result["away_name"] if last_result["home_team"] == team_id else last_result["home_name"]
        result_json = json.loads(last_result["result_json"]) if last_result.get("result_json") else {}
        winner = result_json.get("winner")
        outcome = "tied" if winner is None else ("won" if winner == team_id else "lost")
        return {"context": "post-match", "fixture_id": last_result["id"], "opponent": opponent,
               "outcome": outcome, "question": press_conference_question_post_match(outcome, opponent)}
    next_fixture = fetch_next_fixture(team_id, db)
    if next_fixture and not state.get(f"press_conference_done_{team_id}_{next_fixture['id']}"):
        opponent = next_fixture["away_name"] if next_fixture["home_team"] == team_id else next_fixture["home_name"]
        return {"context": "pre-match", "fixture_id": next_fixture["id"], "opponent": opponent,
               "outcome": None, "question": press_conference_question(_team_position(ctx))}
    return {"context": None, "fixture_id": None, "opponent": None, "outcome": None, "question": None}


@method("get_press_conference")
def _get_press_conference(_params: dict, ctx: dict) -> dict:
    window = _press_conference_window(ctx)
    return {"available": window["context"] is not None, **window, "tones": list(RESPONSE_TONES.keys())}


@method("answer_press_conference")
def _answer_press_conference(params: dict, ctx: dict) -> dict:
    db, team_id = _db(ctx), _team_id(ctx)
    current_date = ctx["game_data"]["user"]["current_date"]
    window = _press_conference_window(ctx)
    if window["context"] is None:
        raise ValueError("No press conference scheduled right now — check back before or after your next match.")
    result = answer_press_conference(str(params["tone"]), window["outcome"])
    adjust_team_morale(team_id, result["morale_delta"], db)
    history = get_board_confidence_history(team_id, db)
    base_score = history[-1]["score"] if history else 55
    score = max(5, min(98, base_score + result["confidence_delta"]))
    label = next(name for threshold, name in CONFIDENCE_LABELS if score >= threshold)
    record_board_confidence(team_id, score, label, f"{current_date} ({window['context']} press)", db)
    save_game({f"press_conference_done_{team_id}_{window['fixture_id']}": True}, db)
    result["confidence_score"] = score
    result["confidence_label"] = label
    result["context"] = window["context"]
    return result


@method("get_pitch_options")
def _get_pitch_options(_params: dict, ctx: dict) -> dict:
    status = get_pitch_status(_team_id(ctx), _db(ctx))
    return {"types": PITCH_TYPES, "descriptions": PITCH_DESCRIPTIONS, **status}


@method("get_pitch_status")
def _get_pitch_status(_params: dict, ctx: dict) -> dict:
    """v4.26.0: pitch choice moved to the Facilities screen with a real
    groundskeeping delay — this is what that screen polls to show the
    current surface, any queued change, and days remaining."""
    status = get_pitch_status(_team_id(ctx), _db(ctx))
    return {"types": PITCH_TYPES, "descriptions": PITCH_DESCRIPTIONS, **status}


@method("set_pitch_selection")
def _set_pitch_selection(params: dict, ctx: dict) -> dict:
    """v4.26.0: no longer instant — queues a pitch change that takes
    PITCH_CHANGE_DELAY_DAYS in-game days to become active (see
    database.set_pitch_selection)."""
    pitch = params.get("pitch", "Green")
    status = set_pitch_selection(_team_id(ctx), pitch, _db(ctx))
    return {"ok": True, **status}


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


## v0.90.0: (re)binds ctx's database-derived state (game_data/team/players/
## new_game_setup/game_controller) to a given save's database file — the
## same body build_context() used to run inline against the single legacy
## path, now shared so load_save/create_save can re-point a live ctx at a
## different save without a server restart.
def _bind_database(ctx: dict[str, Any], database_path: str | Path) -> dict[str, Any]:
    from competition import CompetitionEngine
    ctx["database_path"] = str(database_path)
    game_data = load_game(database_path)
    CompetitionEngine(database_path).ensure_season(date.fromisoformat(game_data["user"]["current_date"]).year)
    team_id = game_data["user"].get("current_team_id")
    team = get_team_summary(team_id, database_path) if team_id else {}
    players = fetch_players(team_id, database_path) if team_id else []
    ctx["game_data"] = game_data
    ctx["team"] = team
    ctx["players"] = players
    ctx["new_game_setup"] = game_data["state"].get("new_game_setup", {})
    ctx["game_controller"] = GameController(
        ctx, navigate=lambda name: ctx.__setitem__("_pending_navigation", name),
        request_exit=lambda: None,
    )
    return ctx


def build_context() -> dict[str, Any]:
    """Same boot sequence as main.py's bootstrap_game, minus pygame state.

    Real bug fixed here: this used to skip CompetitionEngine.ensure_season(),
    which main.py always calls on startup. A save that only ever went
    through the Godot client therefore had exactly one hardcoded demo
    fixture (seeded by database.py's _seed_phase_25_data) and then a
    permanently empty fixture list — no Domestic Division 1/2 league
    schedule or cup was ever generated. ensure_season() is idempotent
    (checks existing rows before inserting), so this is safe to call
    every time the backend starts, matching main.py exactly.

    v0.90.0: the single legacy database path is no longer necessarily what
    gets played — saves.ensure_active_save() migrates a pre-v0.90.0 install's
    lone save into the new saves/ directory as "Save 1" (first run only) and
    resolves whichever save was last active, defaulting to the first save
    that exists. initialise_database() still runs against the legacy path
    too so prepare_environment()'s crash-recovery/corruption-quarantine
    logic (which still operates on that path) keeps working unchanged."""
    paths = get_launch_paths()
    state = prepare_environment(paths, interactive=False)
    initialise_database(state.paths.database)
    active_save_id = saves_module.ensure_active_save(paths.writable_root, state.paths.database)
    database_path = saves_module.save_database_path(paths.writable_root, active_save_id)
    context: dict[str, Any] = {"_active_save_id": active_save_id, "_writable_root": str(paths.writable_root)}
    _bind_database(context, database_path)
    return context


def _respond(request_id: Any, *, result: Any = None, error: str | None = None) -> None:
    payload = {"id": request_id, "error": error} if error is not None else {"id": request_id, "result": result}
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


@method("get_ground_info")
def _get_ground_info_ipc(params: dict, ctx: dict) -> dict:
    return get_ground_info(params["team_id"], _db(ctx)) or {}


@method("get_match_ground_details")
def _get_match_ground_details_ipc(params: dict, ctx: dict) -> dict:
    return get_match_ground_details(params["match_id"], _db(ctx)) or {}


@method("get_ground_stats")
def _get_ground_stats_ipc(params: dict, ctx: dict) -> dict:
    return get_ground_stats(params["team_id"], _db(ctx))


@method("get_player_form")
def _get_player_form_ipc(params: dict, ctx: dict) -> dict:
    return get_player_form(params["player_id"], _db(ctx), params.get("last_n", 5))


@method("get_personalities")
def _get_personalities_ipc(params: dict, ctx: dict) -> dict:
    return {k: {"description": v["description"]} for k, v in PERSONALITIES.items()}


@method("get_player_traits")
def _get_player_traits_ipc(params: dict, ctx: dict) -> dict:
    return {k: {"description": v["description"]} for k, v in PLAYER_TRAITS.items()}


@method("get_keeper_batting_role")
def _get_keeper_batting_role_ipc(params: dict, ctx: dict) -> dict:
    from database import classify_keeper_batting_role, fetch_players
    player_id = params["player_id"]
    team_id = _team_id(ctx)
    player = next((p for p in fetch_players(team_id, _db(ctx)) if p["id"] == player_id), None)
    if not player:
        return {"role": "specialist_keeper"}
    role = classify_keeper_batting_role(player)
    labels = {
        "keeper_batsman": "Keeper-Batsman",
        "allround_keeper": "All-round Keeper",
        "specialist_keeper": "Specialist Keeper",
    }
    return {"role": role, "label": labels.get(role, role)}


@method("get_ground_honours")
def _get_ground_honours_ipc(params: dict, ctx: dict) -> list[dict]:
    return get_ground_honours(params["ground_id"], _db(ctx))


@method("get_player_honours")
def _get_player_honours_ipc(params: dict, ctx: dict) -> list[dict]:
    return get_player_honours(params["player_id"], _db(ctx))


@method("add_bookmark")
def _add_bookmark_ipc(params: dict, ctx: dict) -> dict:
    return _add_bookmark(
        ctx["_active_save_id"],
        params["item_type"],
        params["item_id"],
        params["label"],
        params.get("sublabel", ""),
        _db(ctx),
    )


@method("remove_bookmark")
def _remove_bookmark_ipc(params: dict, ctx: dict) -> None:
    _remove_bookmark(params["bookmark_id"], _db(ctx))


@method("get_bookmarks")
def _get_bookmarks_ipc(params: dict, ctx: dict) -> list[dict]:
    return _get_bookmarks(ctx["_active_save_id"], params.get("item_type"), _db(ctx))


@method("get_achievements")
def _get_achievements_ipc(params: dict, ctx: dict) -> dict:
    from src.models.achievements import AchievementTracker
    tracker = AchievementTracker(_db(ctx))
    return {
        "progress": tracker.get_progress(),
        "unlocked_count": tracker.get_unlocked_count(),
        "total_count": tracker.get_total_count(),
    }


@method("check_achievements")
def _check_achievements_ipc(params: dict, ctx: dict) -> list[dict]:
    from src.models.achievements import AchievementTracker
    tracker = AchievementTracker(_db(ctx))
    game_state = params.get("game_state", {})
    return tracker.check_all(game_state)


@method("get_national_team")
def _get_national_team_ipc(params: dict, ctx: dict) -> dict:
    from database import get_national_team_id, get_national_squad, get_national_xi
    from src.models.international import NATIONAL_TEAM_NAMES
    national_id = get_national_team_id(_db(ctx))
    if national_id is None:
        return {"managing": False, "nationality": None, "team_name": None, "squad": [], "xi": []}
    # Find nationality from the negative ID
    from src.models.international import NATIONAL_TEAM_IDS
    nationality = None
    for nat, nid in NATIONAL_TEAM_IDS.items():
        if nid == national_id:
            nationality = nat
            break
    if not nationality:
        return {"managing": False, "nationality": None, "team_name": None, "squad": [], "xi": []}
    squad = get_national_squad(nationality, _db(ctx))
    xi = get_national_xi(nationality, _db(ctx))
    return {
        "managing": True,
        "nationality": nationality,
        "team_name": NATIONAL_TEAM_NAMES.get(nationality, nationality),
        "squad_size": len(squad),
        "squad": [{"id": p["id"], "name": p["name"], "role": p["role"], "overall": p["overall"],
                    "age": p["age"], "nationality": p["nationality"]} for p in squad[:30]],
        "xi": [{"id": p["id"], "name": p["name"], "role": p["role"], "overall": p["overall"]}
                for p in xi],
    }


@method("accept_national_job")
def _accept_national_job_ipc(params: dict, ctx: dict) -> dict:
    from database import set_national_team_id
    from src.models.international import NATIONAL_TEAM_IDS, NATIONAL_TEAM_NAMES
    nationality = params.get("nationality")
    if nationality not in NATIONAL_TEAM_IDS:
        return {"error": f"Unknown nationality: {nationality}"}
    set_national_team_id(NATIONAL_TEAM_IDS[nationality], _db(ctx))
    return {"success": True, "nationality": nationality, "team_name": NATIONAL_TEAM_NAMES[nationality]}


@method("resign_national_job")
def _resign_national_job_ipc(params: dict, ctx: dict) -> dict:
    from database import set_national_team_id
    set_national_team_id(None, _db(ctx))
    return {"success": True}


@method("get_international_fixtures")
def _get_international_fixtures_ipc(params: dict, ctx: dict) -> list[dict]:
    """Return international fixtures for the current season."""
    from database import get_national_fixtures, get_national_team_id
    from src.models.international import NATIONAL_TEAM_IDS
    national_id = get_national_team_id(_db(ctx))
    if national_id is None:
        return []
    nationality = None
    for nat, nid in NATIONAL_TEAM_IDS.items():
        if nid == national_id:
            nationality = nat
            break
    if not nationality:
        return []
    return get_national_fixtures(nationality, _db(ctx))


@method("get_current_international_competition")
def _get_current_international_competition_ipc(_params: dict, ctx: dict) -> dict:
    """Whichever international competition thread (bilateral tour, ICC
    tournament group stage, or knockout) was created most recently —
    powers the National Team screen's tournament standings/bracket view."""
    return get_current_international_competition(_db(ctx))


@method("steam_unlock_achievement")
def _steam_unlock_achievement_ipc(params: dict, ctx: dict) -> dict:
    """Unlock a Steam achievement."""
    steam = ctx.get("steam")
    if not steam:
        return {"error": "Steam not initialised"}
    achievement_id = params.get("achievement_id")
    if not achievement_id:
        return {"error": "No achievement_id provided"}
    result = steam.unlock_achievement(achievement_id)
    return {"success": result}


@method("steam_get_achievements")
def _steam_get_achievements_ipc(params: dict, ctx: dict) -> dict:
    """Get Steam achievement status."""
    steam = ctx.get("steam")
    if not steam:
        return {"unlocked": [], "total": 0}
    from src.steam_integration import ACHIEVEMENTS
    return {
        "unlocked": sorted(steam.unlocked),
        "total": len(ACHIEVEMENTS),
        "achievements": [{"id": a.id, "name": a.name, "description": a.description} for a in ACHIEVEMENTS],
    }


@method("steam_cloud_save")
def _steam_cloud_save_ipc(params: dict, ctx: dict) -> dict:
    """Save game to Steam Cloud."""
    steam = ctx.get("steam")
    if not steam:
        return {"error": "Steam not initialised"}
    database_path = params.get("database_path", ctx.get("database_path"))
    result = steam.cloud_save(database_path)
    return {"success": result}


@method("steam_cloud_load")
def _steam_cloud_load_ipc(params: dict, ctx: dict) -> dict:
    """Load game from Steam Cloud."""
    steam = ctx.get("steam")
    if not steam:
        return {"error": "Steam not initialised"}
    database_path = params.get("database_path", ctx.get("database_path"))
    result = steam.cloud_load(database_path)
    return {"success": result}


@method("get_team_kit")
def _get_team_kit_ipc(params: dict, ctx: dict) -> dict:
    """Get team kit configuration."""
    from src.models.kit_editor import get_team_kit
    team_id = params.get("team_id", _team_id(ctx))
    return get_team_kit(team_id, _db(ctx))


@method("set_team_kit")
def _set_team_kit_ipc(params: dict, ctx: dict) -> dict:
    """Set team kit configuration."""
    from src.models.kit_editor import set_team_kit
    team_id = params.get("team_id", _team_id(ctx))
    kit = params.get("kit", {})
    set_team_kit(team_id, kit, _db(ctx))
    return {"success": True}


@method("get_all_kits")
def _get_all_kits_ipc(params: dict, ctx: dict) -> dict:
    """Get all team kits."""
    from src.models.kit_editor import get_all_kits
    return get_all_kits(_db(ctx))


@method("get_player_for_edit")
def _get_player_for_edit_ipc(params: dict, ctx: dict) -> dict:
    """Get player data for editing."""
    from src.models.player_editor import get_player_for_edit
    player_id = params.get("player_id")
    if not player_id:
        return {"error": "No player_id provided"}
    return get_player_for_edit(player_id, _db(ctx))


@method("update_player")
def _update_player_ipc(params: dict, ctx: dict) -> dict:
    """Update player attributes."""
    from src.models.player_editor import update_player
    player_id = params.get("player_id")
    updates = params.get("updates", {})
    if not player_id:
        return {"error": "No player_id provided"}
    result = update_player(player_id, updates, _db(ctx))
    return {"success": result}


@method("get_all_players_for_edit")
def _get_all_players_for_edit_ipc(params: dict, ctx: dict) -> list[dict]:
    """Get all players for the editor."""
    from src.models.player_editor import get_all_players_for_edit
    return get_all_players_for_edit(_db(ctx))


@method("get_competitions")
def _get_competitions_ipc(params: dict, ctx: dict) -> list[dict]:
    """Get all competitions for the current season."""
    from src.models.competition_editor import get_competitions
    return get_competitions(_db(ctx))


@method("get_competition_standings")
def _get_competition_standings_ipc(params: dict, ctx: dict) -> list[dict]:
    """Get standings for a competition."""
    from src.models.competition_editor import get_competition_standings
    competition_id = params.get("competition_id")
    if not competition_id:
        return {"error": "No competition_id provided"}
    return get_competition_standings(competition_id, _db(ctx))


@method("get_competition_matches")
def _get_competition_matches_ipc(params: dict, ctx: dict) -> list[dict]:
    """Get matches for a competition."""
    from src.models.competition_editor import get_competition_matches
    competition_id = params.get("competition_id")
    if not competition_id:
        return {"error": "No competition_id provided"}
    return get_competition_matches(competition_id, _db(ctx))


@method("get_player_records")
def _get_player_records_ipc(params: dict, ctx: dict) -> dict:
    """Get player career records."""
    from database import fetch_player_records
    player_id = params.get("player_id")
    if not player_id:
        return {"error": "No player_id provided"}
    return fetch_player_records(player_id, _db(ctx))


@method("get_player_match_events")
def _get_player_match_events_ipc(params: dict, ctx: dict) -> dict:
    """Get a player's persisted shot map/pitch map/chances from their most
    recent matches — feeds the player profile Match Stats tab's wagon wheel
    and chances panel."""
    from database import fetch_player_match_events
    player_id = params.get("player_id")
    if not player_id:
        return {"error": "No player_id provided"}
    return fetch_player_match_events(player_id, _db(ctx))


@method("get_player_form")
def _get_player_form_ipc(params: dict, ctx: dict) -> dict:
    """Get player form history."""
    from database import fetch_player_form
    player_id = params.get("player_id")
    if not player_id:
        return {"error": "No player_id provided"}
    return fetch_player_form(player_id, _db(ctx))


@method("get_team_emblem")
def _get_team_emblem_ipc(params: dict, ctx: dict) -> dict:
    """Get team emblem configuration."""
    from src.models.emblem_editor import get_team_emblem
    team_id = params.get("team_id", _team_id(ctx))
    return get_team_emblem(team_id, _db(ctx))


@method("set_team_emblem")
def _set_team_emblem_ipc(params: dict, ctx: dict) -> dict:
    """Set team emblem configuration."""
    from src.models.emblem_editor import set_team_emblem
    team_id = params.get("team_id", _team_id(ctx))
    emblem = params.get("emblem", {})
    set_team_emblem(team_id, emblem, _db(ctx))
    return {"success": True}


@method("get_data_hub")
def _get_data_hub_ipc(params: dict, ctx: dict) -> dict:
    return _get_data_hub(_team_id(ctx), _db(ctx))


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
