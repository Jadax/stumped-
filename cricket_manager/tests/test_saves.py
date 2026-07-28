"""Multi-save-slot system (v0.90.0) — previously "Load Game" just re-entered
whatever the single existing database held; there was no save-slot concept
anywhere. Covers saves.py's pure file/manifest logic plus the IPC methods
that (re)bind a live server context to a different save without restarting."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from database import get_team_summary, initialise_database, load_game
import saves


class TemporaryRootTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.directory.name)

    def tearDown(self) -> None:
        self.directory.cleanup()


class SavesModuleTests(TemporaryRootTest):
    def test_create_save_creates_a_playable_database_and_manifest_entry(self) -> None:
        created = saves.create_save(self.root, "My Career")
        self.assertTrue(Path(created["database_path"]).exists())
        entries = saves.list_saves(self.root)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], created["id"])
        self.assertEqual(entries[0]["display_name"], "My Career")

    def test_duplicate_display_names_get_distinct_slugged_ids(self) -> None:
        first = saves.create_save(self.root, "My Career")
        second = saves.create_save(self.root, "My Career")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(len(saves.list_saves(self.root)), 2)

    def test_list_saves_reads_team_and_date_live_from_each_database(self) -> None:
        created = saves.create_save(self.root, "My Career")
        db_path = Path(created["database_path"])
        from database import fetch_teams, set_current_team
        team_id = fetch_teams(db_path)[0]["id"]
        set_current_team(team_id, db_path)
        entries = saves.list_saves(self.root)
        self.assertIsNotNone(entries[0]["team_name"])
        self.assertIsNotNone(entries[0]["current_date"])

    def test_delete_save_removes_manifest_entry_and_database_file(self) -> None:
        created = saves.create_save(self.root, "Throwaway")
        db_path = Path(created["database_path"])
        saves.delete_save(self.root, created["id"])
        self.assertFalse(db_path.exists())
        self.assertEqual(saves.list_saves(self.root), [])

    def test_migrate_legacy_save_creates_save_1_from_existing_single_database(self) -> None:
        legacy = self.root / "cricket_manager.db"
        initialise_database(legacy)
        saves.migrate_legacy_save(self.root, legacy)
        entries = saves.list_saves(self.root)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], saves.LEGACY_SAVE_ID)
        self.assertEqual(entries[0]["display_name"], saves.LEGACY_SAVE_DISPLAY_NAME)
        self.assertTrue(legacy.exists())  # copied, not moved — nothing destroyed

    def test_migrate_legacy_save_is_a_no_op_once_a_manifest_already_exists(self) -> None:
        saves.create_save(self.root, "Already Real Save")
        legacy = self.root / "cricket_manager.db"
        initialise_database(legacy)
        saves.migrate_legacy_save(self.root, legacy)
        self.assertEqual(len(saves.list_saves(self.root)), 1)
        self.assertEqual(saves.list_saves(self.root)[0]["display_name"], "Already Real Save")

    def test_ensure_active_save_on_a_genuinely_fresh_install_creates_save_1(self) -> None:
        legacy = self.root / "cricket_manager.db"  # does not exist — fresh install
        active_id = saves.ensure_active_save(self.root, legacy)
        self.assertEqual(active_id, saves.LEGACY_SAVE_ID)
        self.assertEqual(saves.read_active_save_id(self.root), saves.LEGACY_SAVE_ID)

    def test_ensure_active_save_falls_back_to_first_save_if_marked_active_is_gone(self) -> None:
        first = saves.create_save(self.root, "First")
        second = saves.create_save(self.root, "Second")
        saves.write_active_save_id(self.root, "nonexistent-id")
        active_id = saves.ensure_active_save(self.root, self.root / "cricket_manager.db")
        self.assertEqual(active_id, first["id"])


class SavesIpcTests(TemporaryRootTest):
    def _build_ctx(self) -> dict:
        import ipc_server
        legacy = self.root / "cricket_manager.db"
        initialise_database(legacy)
        active_id = saves.ensure_active_save(self.root, legacy)
        database_path = saves.save_database_path(self.root, active_id)
        ctx: dict = {"_active_save_id": active_id, "_writable_root": str(self.root)}
        ipc_server._bind_database(ctx, database_path)
        return ctx

    def test_list_saves_ipc_reports_the_active_save(self) -> None:
        import ipc_server
        ctx = self._build_ctx()
        result = ipc_server.METHODS["list_saves"]({}, ctx)
        self.assertEqual(len(result["saves"]), 1)
        self.assertEqual(result["active_save_id"], ctx["_active_save_id"])

    def test_create_save_ipc_switches_the_live_context_to_a_fresh_save(self) -> None:
        import ipc_server
        ctx = self._build_ctx()
        original_save_id = ctx["_active_save_id"]
        original_database_path = ctx["database_path"]
        result = ipc_server.METHODS["create_save"]({"display_name": "New Career"}, ctx)
        self.assertNotEqual(ctx["_active_save_id"], original_save_id)
        self.assertNotEqual(ctx["database_path"], original_database_path)
        self.assertEqual(result["destination"], "New Game Setup")
        # A fresh save hasn't been through New Game Setup yet, so no manager
        # identity has been recorded — distinct from the seeded default team
        # every initialise_database() call assigns via its NOT NULL FK.
        self.assertEqual(ctx["new_game_setup"], {})
        self.assertEqual(len(ipc_server.METHODS["list_saves"]({}, ctx)["saves"]), 2)

    def test_load_save_ipc_switches_the_live_context_to_a_different_saves_team(self) -> None:
        import ipc_server
        ctx = self._build_ctx()
        first_team_name = ctx["team"]["name"]
        created = ipc_server.METHODS["create_save"]({"display_name": "Second Career"}, ctx)
        from database import fetch_teams
        team_id = fetch_teams(ctx["database_path"])[0]["id"]
        ipc_server.METHODS["confirm_career_team"]({"team_id": team_id}, ctx)
        second_team_name = ctx["team"]["name"]
        original_id = [s for s in saves.list_saves(self.root) if s["id"] != created["id"]][0]["id"]
        result = ipc_server.METHODS["load_save"]({"id": original_id}, ctx)
        self.assertEqual(result["team"]["name"], first_team_name)
        self.assertNotEqual(first_team_name, second_team_name)

    def test_load_save_ipc_rejects_an_unknown_save_id(self) -> None:
        import ipc_server
        ctx = self._build_ctx()
        with self.assertRaises(ValueError):
            ipc_server.METHODS["load_save"]({"id": "does-not-exist"}, ctx)

    def test_delete_save_ipc_refuses_to_delete_the_active_save(self) -> None:
        import ipc_server
        ctx = self._build_ctx()
        with self.assertRaises(ValueError):
            ipc_server.METHODS["delete_save"]({"id": ctx["_active_save_id"]}, ctx)

    def test_delete_save_ipc_removes_an_inactive_save(self) -> None:
        import ipc_server
        ctx = self._build_ctx()
        created = ipc_server.METHODS["create_save"]({"display_name": "Second Career"}, ctx)
        original_id = [s for s in saves.list_saves(self.root) if s["id"] != created["id"]][0]["id"]
        result = ipc_server.METHODS["delete_save"]({"id": original_id}, ctx)
        self.assertEqual(len(result["saves"]), 1)


if __name__ == "__main__":
    unittest.main()
