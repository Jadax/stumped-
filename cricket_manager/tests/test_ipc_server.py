"""Godot-client IPC backend (docs/GRAPHICS_MIGRATION_PLAN.md Phase 0/1)."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch


def _context() -> dict:
    from database import fetch_players, fetch_teams, get_team_summary, initialise_database, load_game
    db = os.path.join(tempfile.mkdtemp(), "ipc.db")
    initialise_database(db)
    team = get_team_summary(fetch_teams(db)[0]["id"], db)
    return {"database_path": db, "team": team, "players": fetch_players(team["id"], db),
           "game_data": load_game(db)}


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
        context = _context()
        result = ipc_server._get_squad({}, context)
        encoded = json.dumps(result)  # raises if anything isn't JSON-safe
        decoded = json.loads(encoded)
        self.assertEqual(decoded["team"]["name"], context["team"]["name"])
        self.assertGreater(len(decoded["players"]), 0)


class IpcServerMethodCoverageTests(unittest.TestCase):
    """Every read-only method registered for the Godot client (Phase 1
    method list) must run against a real fresh save and return JSON-safe
    data — this is what tests/test_ipc_server.py's earlier direct-subprocess
    smoke test checked manually while building godot_client/shell.gd."""

    def setUp(self) -> None:
        self.context = _context()

    def _call(self, method_name: str, params: dict | None = None) -> dict:
        import ipc_server
        handler = ipc_server.METHODS[method_name]
        result = handler(params or {}, self.context)
        return json.loads(json.dumps(result))  # raises if not JSON-safe

    def test_get_dashboard(self) -> None:
        result = self._call("get_dashboard")
        self.assertIn("standings", result)
        self.assertIn("messages", result)

    def test_get_inbox_and_mark_message_read(self) -> None:
        inbox = self._call("get_inbox", {"limit": 1})
        self.assertEqual(len(inbox["messages"]), 1)
        message_id = inbox["messages"][0]["id"]
        self.assertEqual(self._call("mark_message_read", {"message_id": message_id}), {"ok": True})

    def test_get_standings(self) -> None:
        self.assertIn("standings", self._call("get_standings"))

    def test_get_staff(self) -> None:
        result = self._call("get_staff")
        self.assertGreater(len(result["staff"]), 0)

    def test_get_transfer_market_and_submit_offer(self) -> None:
        market = self._call("get_transfer_market")
        self.assertGreater(len(market["players"]), 0)
        target = market["players"][0]
        offer = self._call("submit_transfer_offer", {"player_id": target["id"], "fee": target["asking_price"],
                                                      "wage": 5000})
        self.assertIn("offer_id", offer)

    def test_get_scouting_assignments(self) -> None:
        self.assertEqual(self._call("get_scouting_assignments"), {"assignments": []})

    def test_get_finances(self) -> None:
        result = self._call("get_finances")
        self.assertIn("transactions", result)

    def test_get_facilities(self) -> None:
        self.assertEqual(self._call("get_facilities")["upgrades"], [])

    def test_get_training_converts_int_keys_to_strings_for_json(self) -> None:
        result = self._call("get_training")
        self.assertIn("assignments", result)
        self.assertTrue(all(isinstance(key, str) for key in result["assignments"]))

    def test_get_honours(self) -> None:
        self.assertEqual(self._call("get_honours"), {"honours": []})

    def test_advance_day_updates_context_and_returns_events(self) -> None:
        before_date = self.context["game_data"]["user"]["current_date"]
        events = self._call("advance_day")
        self.assertIn("date", events)
        self.assertNotEqual(events["date"], before_date)
        self.assertEqual(self.context["game_data"]["user"]["current_date"], events["date"])


if __name__ == "__main__":
    unittest.main()
