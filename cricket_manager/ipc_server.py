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
from typing import Any, Callable

from database import (browse_staff_market, fetch_active_injuries, fetch_facility_upgrades,
                      fetch_financial_log, fetch_honours, fetch_inbox_messages,
                      fetch_league_standings, fetch_next_fixture, fetch_players,
                      fetch_scouting_assignments, fetch_staff, fetch_training_assignments,
                      fetch_transfer_offers, get_team_summary, initialise_database, load_game,
                      make_staff_offer, mark_inbox_read, resolve_staff_offer,
                      resolve_transfer_offer, save_game, scout_players, sell_staff_member,
                      start_facility_upgrade, submit_transfer_offer, unread_inbox_count)
from src.models.recruitment import contract_watch, role_gaps, weakest_attribute_group
from src.utilities.launcher import app_version, get_launch_paths, prepare_environment

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


@method("get_squad")
def _get_squad(_params: dict, ctx: dict) -> dict:
    return {"team": ctx["team"], "players": ctx["players"]}


def _selection_view(ctx: dict) -> dict:
    """Players are returned XI-first in batting order (mirroring
    ui/selection.py's self.xi array, whose order *is* the batting order),
    then the rest of the squad — so table_screen.gd's row list is directly
    reorderable by move_batting_up/down without any client-side sorting."""
    selection = ctx["game_data"].get("state", {}).get("selection", {})
    xi_ids = list(selection.get("xi", []))
    xi_set = set(xi_ids)
    captain_id, keeper_id = selection.get("captain"), selection.get("keeper")
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
        players.append({**p, "selected": p["id"] in xi_set, "xi_status": "/".join(tags)})
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


@method("get_dashboard")
def _get_dashboard(_params: dict, ctx: dict) -> dict:
    db, team_id = _db(ctx), _team_id(ctx)
    fixture = fetch_next_fixture(team_id, db)
    return {"team": ctx["team"], "fixture": fixture,
           "standings": fetch_league_standings(db),
           "messages": fetch_inbox_messages(5, db),
           "unread_count": unread_inbox_count(db)}


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
    return {"players": players, "offers": fetch_transfer_offers(team_id, db)}


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
    return {"team": ctx["team"], "transactions": fetch_financial_log(_team_id(ctx), _db(ctx))}


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
    return {"players": ctx["players"], "assignments": {str(k): v for k, v in assignments.items()}}


@method("get_staff_market")
def _get_staff_market(params: dict, ctx: dict) -> dict:
    return {"staff": browse_staff_market(params.get("group", "All"), _team_id(ctx),
                                         int(params.get("limit", 30)), _db(ctx))}


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


@method("get_youth_academy")
def _get_youth_academy(_params: dict, ctx: dict) -> dict:
    return {"players": [p for p in ctx["players"] if p.get("academy_squad")]}


@method("get_medical")
def _get_medical(_params: dict, ctx: dict) -> dict:
    return {"injuries": fetch_active_injuries(_team_id(ctx), _db(ctx))}


@method("get_honours")
def _get_honours(_params: dict, ctx: dict) -> dict:
    return {"honours": fetch_honours(_team_id(ctx), _db(ctx))}


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
    """Same boot sequence as main.py's bootstrap_game, minus pygame state."""
    paths = get_launch_paths()
    state = prepare_environment(paths, interactive=False)
    initialise_database(state.paths.database)
    game_data = load_game(state.paths.database)
    team = get_team_summary(game_data["user"]["current_team_id"], state.paths.database)
    players = fetch_players(team["id"], state.paths.database)
    return {"database_path": str(state.paths.database), "game_data": game_data,
           "team": team, "players": players}


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
