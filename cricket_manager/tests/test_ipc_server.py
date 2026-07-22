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

    def test_get_squad_includes_attribute_group_averages(self) -> None:
        import ipc_server
        from src.models.squad_metrics import group_average
        context = _context()
        result = ipc_server._get_squad({}, context)
        player = result["players"][0]
        expected = next(p for p in context["players"] if p["id"] == player["id"])
        self.assertEqual(player["batting_avg"], group_average(expected, "batting"))
        self.assertEqual(player["bowling_avg"], group_average(expected, "bowling"))


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

    def test_get_dashboard_includes_current_date(self) -> None:
        result = self._call("get_dashboard")
        self.assertEqual(result["date"], self.context["game_data"]["user"]["current_date"])

    def test_get_dashboard_standings_are_numbered_by_rank(self) -> None:
        standings = self._call("get_dashboard")["standings"]
        self.assertTrue(standings)
        self.assertEqual([row["position"] for row in standings], list(range(1, len(standings) + 1)))

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

    def test_get_transfer_market_formats_money_like_the_pygame_client(self) -> None:
        from src.models.currency import format_money
        market = self._call("get_transfer_market")
        target = market["players"][0]
        self.assertEqual(target["asking_price_display"], format_money(target["asking_price"]))

    def test_get_scouting_assignments(self) -> None:
        self.assertEqual(self._call("get_scouting_assignments"), {"assignments": []})

    def test_get_finances(self) -> None:
        from src.models.currency import format_money
        result = self._call("get_finances")
        self.assertIn("transactions", result)
        if result["transactions"]:
            row = result["transactions"][0]
            self.assertEqual(row["amount_display"], format_money(row["amount"]))

    def test_get_facilities(self) -> None:
        result = self._call("get_facilities")
        self.assertEqual(result["upgrades"], [])
        self.assertEqual(len(result["facilities"]), 7)
        self.assertTrue(all(f["status"] == "Ready" for f in result["facilities"]))

    def test_upgrade_facility_starts_a_build_and_marks_it_building(self) -> None:
        result = self._call("upgrade_facility", {"facility": "Grounds Department"})
        self.assertEqual(result["status"], "BUILDING")
        overview = self._call("get_facilities")
        entry = next(f for f in overview["facilities"] if f["facility"] == "Grounds Department")
        self.assertEqual(entry["status"], "Building")

    def test_upgrade_facility_rejects_a_second_upgrade_in_progress(self) -> None:
        self._call("upgrade_facility", {"facility": "Academy"})
        with self.assertRaises(ValueError):
            self._call("upgrade_facility", {"facility": "Academy"})

    def test_get_training_converts_int_keys_to_strings_for_json(self) -> None:
        result = self._call("get_training")
        self.assertIn("assignments", result)
        self.assertTrue(all(isinstance(key, str) for key in result["assignments"]))

    def test_get_training_flattens_assignment_onto_each_player(self) -> None:
        result = self._call("get_training")
        unassigned = result["players"][0]
        self.assertEqual(unassigned["focus"], "None")
        self.assertEqual(unassigned["intensity"], "Normal")
        self.assertEqual(unassigned["last_trained"], "—")

    def test_get_staff_market_excludes_own_team(self) -> None:
        result = self._call("get_staff_market")
        self.assertTrue(result["staff"])
        self.assertTrue(all(s["team_id"] != self.context["team"]["id"] for s in result["staff"]))

    def test_get_staff_market_formats_fee_and_wage_like_the_pygame_client(self) -> None:
        from src.models.currency import format_money
        target = self._call("get_staff_market")["staff"][0]
        self.assertEqual(target["fee_display"], format_money(target["fee"]))
        self.assertEqual(target["wage_display"], format_money(target["wage"]))

    def test_sign_staff_moves_the_member_and_charges_the_fee(self) -> None:
        market = self._call("get_staff_market")["staff"]
        target = market[0]
        buyer_id = self.context["team"]["id"]
        result = self._call("sign_staff", {"staff_id": target["id"], "from_team": target["team_id"],
                                           "fee": target["fee"], "wage": target["wage"]})
        self.assertTrue(result["success"])
        from database import fetch_staff
        roster = fetch_staff(buyer_id, database_path=self.context["database_path"])
        self.assertTrue(any(s["id"] == target["id"] for s in roster))

    def test_release_staff_removes_from_roster_and_pays_a_fee(self) -> None:
        from database import fetch_staff
        team_id = self.context["team"]["id"]
        roster_before = fetch_staff(team_id, database_path=self.context["database_path"])
        target = roster_before[0]
        result = self._call("release_staff", {"staff_id": target["id"]})
        self.assertGreater(result["fee"], 0)
        roster_after = fetch_staff(team_id, database_path=self.context["database_path"])
        self.assertFalse(any(s["id"] == target["id"] for s in roster_after))
        self.assertEqual(len(roster_after), len(roster_before) - 1)

    def test_get_recruitment_matches_pygame_recruitment_hub_logic(self) -> None:
        from src.models.recruitment import role_gaps, weakest_attribute_group
        result = self._call("get_recruitment")
        expected_gaps = role_gaps(self.context["players"])
        self.assertEqual([(g["role"], g["have"]) for g in result["gaps"]], expected_gaps)
        self.assertEqual(result["weakest_group"], weakest_attribute_group(self.context["players"]))
        self.assertIn("contract_watch", result)
        self.assertIn("active_assignments", result)

    def test_toggle_xi_adds_and_removes_a_player(self) -> None:
        player_id = self.context["players"][0]["id"]
        added = self._call("toggle_xi", {"player_id": player_id})
        self.assertEqual(added["xi_count"], 1)
        self.assertTrue(next(p for p in added["players"] if p["id"] == player_id)["selected"])
        removed = self._call("toggle_xi", {"player_id": player_id})
        self.assertEqual(removed["xi_count"], 0)

    def test_toggle_xi_persists_across_a_fresh_context(self) -> None:
        player_id = self.context["players"][0]["id"]
        self._call("toggle_xi", {"player_id": player_id})
        from database import load_game
        reloaded_game_data = load_game(self.context["database_path"])
        self.assertIn(player_id, reloaded_game_data["state"]["selection"]["xi"])

    def test_toggle_xi_rejects_a_twelfth_player(self) -> None:
        for player in self.context["players"][:11]:
            self._call("toggle_xi", {"player_id": player["id"]})
        with self.assertRaises(ValueError):
            self._call("toggle_xi", {"player_id": self.context["players"][11]["id"]})

    def test_set_captain_and_keeper_require_xi_membership(self) -> None:
        outsider = self.context["players"][0]["id"]
        with self.assertRaises(ValueError):
            self._call("set_captain", {"player_id": outsider})
        with self.assertRaises(ValueError):
            self._call("set_keeper", {"player_id": outsider})

    def test_set_captain_and_keeper_assign_and_toggle_off(self) -> None:
        player_id = self.context["players"][0]["id"]
        self._call("toggle_xi", {"player_id": player_id})
        assigned = self._call("set_captain", {"player_id": player_id})
        self.assertEqual(assigned["captain_id"], player_id)
        row = next(p for p in assigned["players"] if p["id"] == player_id)
        self.assertIn("C", row["xi_status"].split("/"))
        cleared = self._call("set_captain", {"player_id": player_id})
        self.assertIsNone(cleared["captain_id"])

    def test_set_keeper_is_independent_of_captain(self) -> None:
        captain_id = self.context["players"][0]["id"]
        keeper_id = self.context["players"][1]["id"]
        self._call("toggle_xi", {"player_id": captain_id})
        self._call("toggle_xi", {"player_id": keeper_id})
        self._call("set_captain", {"player_id": captain_id})
        result = self._call("set_keeper", {"player_id": keeper_id})
        self.assertEqual(result["captain_id"], captain_id)
        self.assertEqual(result["keeper_id"], keeper_id)

    def test_move_batting_up_and_down_swap_adjacent_xi_members(self) -> None:
        first, second, third = (p["id"] for p in self.context["players"][:3])
        for pid in (first, second, third):
            self._call("toggle_xi", {"player_id": pid})
        moved = self._call("move_batting_down", {"player_id": first})
        self.assertEqual([p["id"] for p in moved["players"] if p["selected"]][:3], [second, first, third])
        restored = self._call("move_batting_up", {"player_id": first})
        self.assertEqual([p["id"] for p in restored["players"] if p["selected"]][:3], [first, second, third])

    def test_move_batting_order_is_a_no_op_at_the_boundary(self) -> None:
        first, second = (p["id"] for p in self.context["players"][:2])
        self._call("toggle_xi", {"player_id": first})
        self._call("toggle_xi", {"player_id": second})
        unchanged = self._call("move_batting_up", {"player_id": first})
        self.assertEqual([p["id"] for p in unchanged["players"] if p["selected"]], [first, second])

    def test_move_batting_order_rejects_a_player_outside_the_xi(self) -> None:
        outsider = self.context["players"][0]["id"]
        with self.assertRaises(ValueError):
            self._call("move_batting_up", {"player_id": outsider})
        with self.assertRaises(ValueError):
            self._call("move_batting_down", {"player_id": outsider})

    def test_cycle_batting_style_steps_through_styles_and_sets_aggression(self) -> None:
        # Default style is "Build" (index 2); cycling wraps to "Rotate" (3)
        # first, then "Silly" (0) — matches BATTING_STYLES' declared order.
        player_id = self.context["players"][0]["id"]
        self._call("toggle_xi", {"player_id": player_id})
        first = self._call("cycle_batting_style", {"player_id": player_id})
        row = next(p for p in first["players"] if p["id"] == player_id)
        self.assertEqual(row["batting_style"], "Rotate")
        self.assertEqual(row["batting_aggression"], 3)
        second = self._call("cycle_batting_style", {"player_id": player_id})
        row = next(p for p in second["players"] if p["id"] == player_id)
        self.assertEqual(row["batting_style"], "Silly")
        self.assertEqual(row["batting_aggression"], 10)

    def test_cycle_batting_style_wraps_around(self) -> None:
        player_id = self.context["players"][0]["id"]
        self._call("toggle_xi", {"player_id": player_id})
        for _ in range(4):
            result = self._call("cycle_batting_style", {"player_id": player_id})
        row = next(p for p in result["players"] if p["id"] == player_id)
        self.assertEqual(row["batting_style"], "Build")

    def test_cycle_batting_style_rejects_a_player_outside_the_xi(self) -> None:
        outsider = self.context["players"][0]["id"]
        with self.assertRaises(ValueError):
            self._call("cycle_batting_style", {"player_id": outsider})

    def test_cycle_batting_aggression_wraps_1_to_10_independent_of_style(self) -> None:
        player_id = self.context["players"][0]["id"]
        self._call("toggle_xi", {"player_id": player_id})
        self._call("cycle_batting_style", {"player_id": player_id})  # style=Rotate, aggression=3
        result = self._call("cycle_batting_aggression", {"player_id": player_id})
        row = next(p for p in result["players"] if p["id"] == player_id)
        self.assertEqual(row["batting_aggression"], 4)
        self.assertEqual(row["batting_style"], "Rotate")

    def test_cycle_batting_aggression_rejects_a_player_outside_the_xi(self) -> None:
        outsider = self.context["players"][0]["id"]
        with self.assertRaises(ValueError):
            self._call("cycle_batting_aggression", {"player_id": outsider})

    def test_selection_xi_status_reflects_batting_position(self) -> None:
        first, second = (p["id"] for p in self.context["players"][:2])
        self._call("toggle_xi", {"player_id": first})
        result = self._call("toggle_xi", {"player_id": second})
        rows = {p["id"]: p["xi_status"] for p in result["players"]}
        self.assertEqual(rows[first], "1")
        self.assertEqual(rows[second], "2")

    def test_get_match_preview_returns_fixture_and_selected_xi(self) -> None:
        first_two = [p["id"] for p in self.context["players"][:2]]
        for pid in first_two:
            self._call("toggle_xi", {"player_id": pid})
        self._call("set_captain", {"player_id": first_two[0]})
        result = self._call("get_match_preview")
        self.assertEqual(result["xi_count"], 2)
        self.assertEqual({p["id"] for p in result["xi"]}, set(first_two))
        self.assertEqual(result["captain_id"], first_two[0])
        self.assertIn("fixture", result)

    def test_get_youth_academy_filters_to_academy_squad_players(self) -> None:
        self.context["players"][0]["academy_squad"] = 1
        result = self._call("get_youth_academy")
        self.assertTrue(all(p.get("academy_squad") for p in result["players"]))

    def test_get_medical(self) -> None:
        self.assertEqual(self._call("get_medical")["injuries"], [])

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
