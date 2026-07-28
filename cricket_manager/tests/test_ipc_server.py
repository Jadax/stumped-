"""Godot-client IPC backend (docs/GRAPHICS_MIGRATION_PLAN.md Phase 0/1)."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch


def _context(with_fixtures: bool = False) -> dict:
    from database import fetch_players, fetch_teams, get_team_summary, initialise_database, load_game
    db = os.path.join(tempfile.mkdtemp(), "ipc.db")
    initialise_database(db)
    team = get_team_summary(fetch_teams(db)[0]["id"], db)
    if with_fixtures:
        from competition import CompetitionEngine
        CompetitionEngine(db, seed=7).ensure_season(2026)
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

    def test_get_squad_freshness_is_the_inverse_of_fatigue(self) -> None:
        import ipc_server
        context = _context()
        context["players"][0]["fatigue"] = 30
        result = ipc_server._get_squad({}, context)
        player = next(p for p in result["players"] if p["id"] == context["players"][0]["id"])
        self.assertEqual(player["freshness"], 70)


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

    def test_get_youth_academy_filters_to_academy_squad_or_under_20_players(self) -> None:
        # Mirrors ui/youth.py's roster filter: under-20s plus anyone
        # flagged academy_squad, not just the flag alone (a flagged
        # veteran should still show up as a development case).
        flagged = self.context["players"][0]
        flagged["academy_squad"] = 1
        flagged["age"] = 28
        result = self._call("get_youth_academy")
        self.assertTrue(all(p.get("academy_squad") or p["age"] <= 20 for p in result["players"]))
        self.assertIn(flagged["id"], {p["id"] for p in result["players"]})

    def test_get_medical(self) -> None:
        self.assertEqual(self._call("get_medical")["injuries"], [])

    def test_get_honours(self) -> None:
        self.assertEqual(self._call("get_honours"), {"honours": []})

    def test_get_trophy_room_groups_honours_by_competition(self) -> None:
        from database import record_honour
        team_id = self.context["team"]["id"]
        record_honour(team_id, "Division 1 Champions", 2026, "2026-09-30", self.context["database_path"])
        record_honour(team_id, "Division 1 Champions", 2027, "2027-09-30", self.context["database_path"])
        record_honour(team_id, "Knockout Cup Winners", 2027, "2027-09-30", self.context["database_path"])
        result = self._call("get_trophy_room")
        self.assertEqual(result["total"], 3)
        champs = next(entry for entry in result["breakdown"] if entry["title"] == "Division 1 Champions")
        self.assertEqual(champs["count"], 2)
        self.assertEqual(champs["seasons"], [2027, 2026])

    def test_get_season_records_empty_by_default(self) -> None:
        self.assertEqual(self._call("get_season_records"), {"seasons": []})

    def test_get_club_records_with_no_matches(self) -> None:
        result = self._call("get_club_records")
        self.assertIsNone(result["highest_score"])
        self.assertEqual(result["matches_played"], 0)

    def test_get_board_objectives_returns_defaults_when_no_season_set(self) -> None:
        result = self._call("get_board_objectives")
        self.assertIn("objectives", result)
        self.assertIn("progress", result)
        self.assertIn("league_position", result["progress"])

    def test_get_board_objectives_returns_set_objectives(self) -> None:
        self.context = _context(with_fixtures=True)
        result = self._call("get_board_objectives")
        self.assertIn("objectives", result)
        self.assertIn("league_position", result["objectives"])
        self.assertIn("minimum_cash", result["objectives"])

    def test_get_board_confidence_history_starts_empty(self) -> None:
        result = self._call("get_board_confidence_history")
        self.assertEqual(result["history"], [])

    def test_get_pitch_options_returns_types_and_descriptions(self) -> None:
        result = self._call("get_pitch_options")
        self.assertIn("types", result)
        self.assertIn("descriptions", result)
        self.assertIn("current", result)
        self.assertEqual(result["current"], "Green")
        self.assertEqual(len(result["types"]), 5)

    def test_set_pitch_selection_persists(self) -> None:
        result = self._call("set_pitch_selection", {"pitch": "Dusty"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["pitch"], "Dusty")
        options = self._call("get_pitch_options")
        self.assertEqual(options["current"], "Dusty")

    def test_set_pitch_selection_rejects_invalid(self) -> None:
        with self.assertRaises(ValueError):
            self._call("set_pitch_selection", {"pitch": "InvalidPitch"})

    def test_get_job_offers_starts_empty(self) -> None:
        result = self._call("get_job_offers")
        self.assertEqual(result["offers"], [])

    def test_accept_job_offer_updates_context_team(self) -> None:
        from database import store_job_offers
        current_team_id = self.context["game_data"]["user"]["current_team_id"]
        store_job_offers(current_team_id,
                         [{"offer_id": "test_ipc_accept", "team_id": 3, "team_name": "IPC FC", "wage": 5000}],
                         self.context["database_path"])
        result = self._call("accept_job_offer", {"offer_id": "test_ipc_accept"})
        self.assertEqual(result["new_team_id"], 3)
        self.assertEqual(self.context["team"]["id"], 3)

    def test_decline_job_offer_removes_offer(self) -> None:
        from database import store_job_offers
        current_team_id = self.context["game_data"]["user"]["current_team_id"]
        store_job_offers(current_team_id,
                         [{"offer_id": "test_ipc_decline", "team_id": 4, "team_name": "Decline FC"}],
                         self.context["database_path"])
        result = self._call("decline_job_offer", {"offer_id": "test_ipc_decline"})
        self.assertTrue(result["ok"])

    def test_list_custom_tournaments_starts_empty(self) -> None:
        result = self._call("list_custom_tournaments")
        self.assertEqual(result["tournaments"], [])

    def test_create_and_list_custom_tournament(self) -> None:
        result = self._call("create_custom_tournament",
                            {"name": "IPC Cup", "format": "T20", "team_ids": [1, 2, 3, 4], "advance_per_group": 2, "season": 2026})
        self.assertIn("tournament_id", result)
        listing = self._call("list_custom_tournaments")
        self.assertGreaterEqual(len(listing["tournaments"]), 1)

    def test_get_custom_tournament_returns_details(self) -> None:
        created = self._call("create_custom_tournament",
                             {"name": "Detail Cup", "format": "T20", "team_ids": [1, 2, 3, 4], "advance_per_group": 2, "season": 2026})
        result = self._call("get_custom_tournament", {"tournament_id": created["tournament_id"]})
        self.assertEqual(result["name"], "Detail Cup")

    def test_get_tournament_standings(self) -> None:
        created = self._call("create_custom_tournament",
                             {"name": "Standings Cup", "format": "T20", "team_ids": [1, 2, 3, 4], "advance_per_group": 2, "season": 2026})
        result = self._call("get_tournament_standings", {"tournament_id": created["tournament_id"]})
        self.assertIn("groups", result)

    def test_get_onboarding_state_starts_at_welcome(self) -> None:
        result = self._call("get_onboarding_state")
        self.assertEqual(result["current_step"], "welcome")
        self.assertFalse(result["dismissed"])

    def test_get_onboarding_steps_returns_all(self) -> None:
        result = self._call("get_onboarding_steps")
        self.assertGreaterEqual(len(result["steps"]), 5)

    def test_advance_onboarding_step(self) -> None:
        result = self._call("advance_onboarding_step")
        self.assertEqual(result["current_step"], "squad")
        self.assertIn("welcome", result["completed_steps"])

    def test_dismiss_onboarding(self) -> None:
        result = self._call("dismiss_onboarding")
        self.assertTrue(result["dismissed"])

    def test_advance_day_updates_context_and_returns_events(self) -> None:
        before_date = self.context["game_data"]["user"]["current_date"]
        events = self._call("advance_day")
        self.assertIn("date", events)
        self.assertNotEqual(events["date"], before_date)
        self.assertEqual(self.context["game_data"]["user"]["current_date"], events["date"])

    def test_get_match_state_without_a_started_match_raises(self) -> None:
        with self.assertRaises(ValueError):
            self._call("get_match_state")

    def test_start_match_builds_a_live_match_from_the_next_fixture(self) -> None:
        self.context = _context(with_fixtures=True)
        result = self._call("start_match")
        self.assertIn("match", self.context)
        self.assertFalse(result["completed"])
        self.assertEqual(len(result["innings"]), 1)
        self.assertEqual(self._call("get_match_state"), result)

    def test_simulate_balls_advances_the_live_match_and_can_run_it_to_completion(self) -> None:
        self.context = _context(with_fixtures=True)
        self._call("start_match")
        first = self._call("simulate_balls", {"count": 1})
        self.assertEqual(len(first["events"]), 1)
        self.assertTrue(first["events"][0]["legal"])
        self.assertIn("batter", first["events"][0])
        self.assertIn("bowler", first["events"][0])
        for _ in range(80):
            result = self._call("simulate_balls", {"count": 90})
            if result["state"]["completed"]:
                break
        self.assertTrue(result["state"]["completed"])
        self.assertTrue(result["state"]["result"])
        # A second call after completion must be a safe no-op, not a
        # duplicate finalisation (double financial/form/records writes).
        again = self._call("simulate_balls", {"count": 1})
        self.assertEqual(again["events"], [])

    def test_simulate_balls_finalises_the_fixture_and_updates_standings_once(self) -> None:
        from database import fetch_league_standings
        import ipc_server
        self.context = _context(with_fixtures=True)
        self._call("start_match")
        fixture_id = self.context["_active_fixture"]["id"]
        for _ in range(80):
            result = self._call("simulate_balls", {"count": 90})
            if result["state"]["completed"]:
                break
        self.assertTrue(self.context["_match_finalised"])
        standings = fetch_league_standings(self.context["database_path"])
        played_total = sum(row["played"] for row in standings)
        self.assertGreater(played_total, 0)
        home_id = self.context["_active_fixture"]["home_team"]
        away_id = self.context["_active_fixture"]["away_team"]
        totals_before_replay = ipc_server.METHODS["get_standings"]({}, self.context)
        # Calling simulate_balls again post-completion must not re-run
        # _finalise_match and double-count the result.
        self._call("simulate_balls", {"count": 1})
        self.assertEqual(ipc_server.METHODS["get_standings"]({}, self.context), totals_before_replay)
        self.assertTrue(home_id and away_id)

    def test_finalising_a_match_moves_both_teams_morale_and_records_last_match_xi(self) -> None:
        from database import fetch_players
        self.context = _context(with_fixtures=True)
        start = self._call("start_match")
        home_id, away_id = start["home_team"], start["away_team"]
        before = {home_id: {p["id"]: p["mental"]["morale"] for p in fetch_players(home_id, self.context["database_path"])},
                 away_id: {p["id"]: p["mental"]["morale"] for p in fetch_players(away_id, self.context["database_path"])}}
        for _ in range(80):
            result = self._call("simulate_balls", {"count": 90})
            if result["state"]["completed"]:
                break
        self.assertTrue(result["state"]["completed"])
        after = {home_id: {p["id"]: p["mental"]["morale"] for p in fetch_players(home_id, self.context["database_path"])},
                away_id: {p["id"]: p["mental"]["morale"] for p in fetch_players(away_id, self.context["database_path"])}}
        # Every player on both squads moved (win, loss, or the small tie
        # bump) — a whole-squad event, not just the XI that played.
        self.assertTrue(any(after[home_id][pid] != before[home_id][pid] for pid in before[home_id]))
        self.assertTrue(any(after[away_id][pid] != before[away_id][pid] for pid in before[away_id]))
        self.assertIn("last_match_xi", self.context["game_data"]["state"])
        self.assertEqual(self.context["game_data"]["state"]["last_match_xi"]["team_id"], self.context["team"]["id"])
        self.assertEqual(len(self.context["game_data"]["state"]["last_match_xi"]["xi"]), 11)

    def test_starting_a_new_match_penalises_a_player_dropped_since_the_last_one(self) -> None:
        from database import fetch_players
        self.context = _context(with_fixtures=True)
        team_id = self.context["team"]["id"]
        squad = fetch_players(team_id, self.context["database_path"])
        # The worst-rated outfield player definitely won't make _best_xi()'s
        # fallback (top-10-by-overall + a guaranteed keeper slot) — excludes
        # keepers since a keeper is picked regardless of overall.
        outfield_by_overall = sorted((p for p in squad if p["role"] != "Wicketkeeper"),
                                     key=lambda p: p["overall"], reverse=True)
        dropped_player = outfield_by_overall[-1]
        fake_xi = [dropped_player["id"]]  # only membership in this list matters for dropped_from_xi()
        self.context["game_data"]["state"]["last_match_xi"] = {"team_id": team_id, "xi": fake_xi}
        before = dropped_player["mental"]["morale"]
        self._call("start_match")  # no Selection XI set -> falls back to _best_xi()
        after = next(p for p in fetch_players(team_id, self.context["database_path"]) if p["id"] == dropped_player["id"])
        self.assertLess(after["mental"]["morale"], before)

    def test_get_match_prediction_returns_a_probability_for_the_users_team(self) -> None:
        self.context = _context(with_fixtures=True)
        self._call("start_match")
        result = self._call("get_match_prediction")
        self.assertIn("probability", result)
        self.assertTrue(0 <= result["probability"] <= 100)

    def test_set_match_field_validates_the_preset_and_is_reflected_in_state(self) -> None:
        self.context = _context(with_fixtures=True)
        self._call("start_match")
        result = self._call("set_match_field", {"preset": "Aggressive"})
        self.assertEqual(result["field_preset"], "Aggressive")
        with self.assertRaises(ValueError):
            self._call("set_match_field", {"preset": "Not A Real Preset"})

    def test_set_match_aggression_clamps_to_the_1_to_10_scale(self) -> None:
        self.context = _context(with_fixtures=True)
        self._call("start_match")
        self._call("set_match_aggression", {"batting": 99, "bowling": -5})
        self.assertEqual(self.context["_match_tactics"]["batting_aggression"], 10)
        self.assertEqual(self.context["_match_tactics"]["bowling_aggression"], 1)

    def test_review_decision_without_a_pending_review_reports_unavailable(self) -> None:
        self.context = _context(with_fixtures=True)
        self._call("start_match")
        result = self._call("review_decision")
        self.assertFalse(result["review"]["available"])

    def test_review_decision_upheld_consumes_one_of_the_users_two_reviews(self) -> None:
        self.context = _context(with_fixtures=True)
        self._call("start_match")
        user_team_id = self.context["team"]["id"]
        for _ in range(300):
            result = self._call("simulate_balls", {"count": 1})
            if result["state"]["completed"]:
                self.skipTest("match finished before a reviewable wicket fell against the user's team")
            pending = self.context["match"].pending_review
            if pending and pending["team_id"] == user_team_id:
                review = self._call("review_decision")["review"]
                self.assertTrue(review["available"])
                if not review["overturned"]:
                    self.assertEqual(review["remaining"], 1)
                return
        self.fail("no reviewable wicket fell against the user's team in 300 balls")

    def test_get_opposition_report_returns_none_without_fixtures(self) -> None:
        result = self._call("get_opposition_report")
        self.assertIsNone(result["report"])

    def test_get_opposition_report_with_fixtures_returns_scouting_data(self) -> None:
        self.context = _context(with_fixtures=True)
        result = self._call("get_opposition_report")
        report = result.get("report")
        if report is None:
            self.skipTest("No fixture available for user team")
        self.assertIn("opponent_name", report)
        self.assertIn("key_players", report)
        self.assertIn("strengths", report)
        self.assertIn("weaknesses", report)
        self.assertIn("xi", report)
        self.assertLessEqual(len(report["xi"]), 11)

    def test_cycle_match_bowler_changes_to_a_different_eligible_bowler(self) -> None:
        self.context = _context(with_fixtures=True)
        self._call("start_match")
        before = self.context["match"].current_innings.current_bowler_id
        result = self._call("cycle_match_bowler")
        self.assertTrue(result["bowler_changed"])
        self.assertNotEqual(self.context["match"].current_innings.current_bowler_id, before)


if __name__ == "__main__":
    unittest.main()
