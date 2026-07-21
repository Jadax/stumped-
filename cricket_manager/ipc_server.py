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

from database import fetch_players, get_team_summary, initialise_database, load_game
from src.utilities.launcher import app_version, get_launch_paths, prepare_environment

Handler = Callable[[dict[str, Any], dict[str, Any]], Any]
METHODS: dict[str, Handler] = {}


def method(name: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        METHODS[name] = fn
        return fn
    return register


@method("ping")
def _ping(_params: dict, _ctx: dict) -> dict:
    return {"pong": True, "version": app_version()}


@method("get_squad")
def _get_squad(_params: dict, ctx: dict) -> dict:
    return {"team": ctx["team"], "players": ctx["players"]}


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
