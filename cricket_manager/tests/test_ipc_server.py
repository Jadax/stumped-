"""Godot-client IPC backend (docs/GRAPHICS_MIGRATION_PLAN.md Phase 0)."""
from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch


class IpcServerTests(unittest.TestCase):
    def test_ping_reports_version_without_touching_the_database(self) -> None:
        import ipc_server
        self.assertEqual(ipc_server._ping({}, {}), {"pong": True, "version": ipc_server.app_version()})

    def test_unknown_method_and_bad_json_are_reported_not_fatal(self) -> None:
        import ipc_server
        context = {"team": {"id": 1, "name": "Test"}, "players": []}
        fake_stdin = io.StringIO('not json\n{"id": 1, "method": "no_such_method"}\n{"id": 2, "method": "quit"}\n')
        fake_stdout = io.StringIO()
        with patch("ipc_server.build_context", return_value=context), \
             patch("sys.stdin", fake_stdin), patch("sys.stdout", fake_stdout):
            ipc_server.serve()
        lines = [json.loads(line) for line in fake_stdout.getvalue().splitlines()]
        self.assertIn("invalid JSON", lines[0]["error"])
        self.assertEqual(lines[1]["error"], "unknown method: no_such_method")
        self.assertEqual(lines[2]["result"], {"bye": True})

    def test_get_squad_returns_json_serialisable_team_and_players(self) -> None:
        import ipc_server
        from database import fetch_players, fetch_teams, get_team_summary, initialise_database
        import os, tempfile
        db = os.path.join(tempfile.mkdtemp(), "ipc.db")
        initialise_database(db)
        team = get_team_summary(fetch_teams(db)[0]["id"], db)
        context = {"team": team, "players": fetch_players(team["id"], db)}
        result = ipc_server._get_squad({}, context)
        encoded = json.dumps(result)  # raises if anything isn't JSON-safe
        decoded = json.loads(encoded)
        self.assertEqual(decoded["team"]["name"], team["name"])
        self.assertGreater(len(decoded["players"]), 0)


if __name__ == "__main__":
    unittest.main()
