"""Regression tests for competition branding persistence and IPC validation."""
from __future__ import annotations

import json
import os
import tempfile
import unittest


class CompetitionBrandingTests(unittest.TestCase):
    def setUp(self) -> None:
        from database import initialise_database

        self.database_path = os.path.join(tempfile.mkdtemp(), "branding.db")
        initialise_database(self.database_path)

    def test_branding_defaults_then_round_trips(self) -> None:
        from src.models.competition_editor import get_competition_branding, set_competition_branding

        default = get_competition_branding(42, self.database_path)
        self.assertEqual(default["crest"], "shield")
        saved = set_competition_branding(
            42,
            {"short_name": "  TEST CUP ", "accent": "#3fb950", "crest": "diamond", "ignored": "x"},
            self.database_path,
        )
        self.assertEqual(saved, {"short_name": "TEST CUP", "accent": "#3fb950", "crest": "diamond"})
        self.assertEqual(get_competition_branding(42, self.database_path), saved)

    def test_ipc_branding_is_json_safe_and_requires_competition(self) -> None:
        import ipc_server

        ctx = {"database_path": self.database_path, "team": {"id": 1}}
        self.assertEqual(ipc_server._get_competition_branding_ipc({}, ctx), {"error": "No competition_id provided"})
        result = ipc_server._set_competition_branding_ipc(
            {"competition_id": 7, "branding": {"short_name": "League", "accent": "#d29922", "crest": "circle"}},
            ctx,
        )
        json.dumps(result)
        self.assertEqual(result["short_name"], "League")

