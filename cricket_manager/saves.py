"""Multi-save-slot management.

Before this, the whole project had exactly one save: a single SQLite file
at ``LaunchPaths.database``. "Load Game" in either client just meant
"continue whatever's already there" because there was nothing else to pick
from. This module adds real named save slots: each save is its own SQLite
database file under ``<writable_root>/saves/<id>.db`` (created via
``database.initialise_database``, so every save starts from the same
seeded world), tracked in a small ``saves/manifest.json`` that stores only
what can't be read live from the database (id, display name, creation
time). Team/manager/date shown in a save listing are always read live from
that save's own database — never duplicated into the manifest — so the
list can't go stale relative to the save it describes.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import json as _json
import sqlite3

from database import connect, initialise_database

SAVES_DIRNAME = "saves"
MANIFEST_FILENAME = "manifest.json"
LEGACY_SAVE_ID = "save-1"
LEGACY_SAVE_DISPLAY_NAME = "Save 1"


def _saves_dir(writable_root: Path) -> Path:
    directory = writable_root / SAVES_DIRNAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _manifest_path(writable_root: Path) -> Path:
    return _saves_dir(writable_root) / MANIFEST_FILENAME


def _read_manifest(writable_root: Path) -> list[dict[str, Any]]:
    path = _manifest_path(writable_root)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return []


def _write_manifest(writable_root: Path, entries: list[dict[str, Any]]) -> None:
    _manifest_path(writable_root).write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


def _slugify(display_name: str, existing_ids: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-") or "save"
    slug = base
    suffix = 2
    while slug in existing_ids:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def save_database_path(writable_root: Path, save_id: str) -> Path:
    return _saves_dir(writable_root) / f"{save_id}.db"


def _peek_save(db_path: Path) -> dict[str, Any]:
    """Lightweight metadata read for a save-list row: team name/division,
    manager name, and current in-game date — direct targeted SQL against
    the save's own (already-seeded) database.

    Deliberately does NOT go through database.load_game(), which calls
    initialise_database() unconditionally — that re-runs several
    "backfill any missing legacy data" passes (_ensure_staff_for_all_teams
    and friends) that each full-scan the players/staff/grounds tables, on
    every single call. Listing N saves used to mean N full world
    idempotency passes just to show a preview row, which is exactly what
    made Load Game (and the list refresh after a delete) feel slow."""
    with connect(db_path) as connection:
        row = connection.execute(
            """SELECT u."current_date" AS current_date, t.name AS team_name, t.division
               FROM user_data u LEFT JOIN teams t ON t.id = u.current_team_id
               WHERE u.id = 1"""
        ).fetchone()
        if row is None:
            return {"team_name": None, "division": None, "manager_name": None, "current_date": None}
        state_row = connection.execute(
            "SELECT value_json FROM game_state WHERE key='new_game_setup'"
        ).fetchone()
    manager_name = None
    if state_row is not None:
        try:
            manager_name = _json.loads(state_row[0]).get("manager", {}).get("name")
        except (ValueError, AttributeError):
            manager_name = None
    return {"team_name": row["team_name"], "division": row["division"],
            "manager_name": manager_name, "current_date": row["current_date"]}


def list_saves(writable_root: Path) -> list[dict[str, Any]]:
    """Save metadata for the Load Game screen, most recently played first
    (falling back to creation time for a save that's never been loaded)."""
    entries = _read_manifest(writable_root)
    results = []
    for entry in entries:
        db_path = save_database_path(writable_root, entry["id"])
        summary = dict(entry)
        if db_path.exists():
            try:
                summary.update(_peek_save(db_path))
            except (OSError, sqlite3.DatabaseError, KeyError):
                summary["team_name"] = None
        else:
            summary["team_name"] = None
        results.append(summary)
    results.sort(key=lambda e: e.get("last_played_at") or e.get("created_at", ""), reverse=True)
    return results


def touch_last_played(writable_root: Path, save_id: str, when: str | None = None) -> None:
    """Records when a save was last opened, so Load Game can list saves by
    recent playtime instead of just creation order. `when` is exposed for
    tests only — real callers always want "now"."""
    entries = _read_manifest(writable_root)
    now = when or datetime.now().isoformat(timespec="seconds")
    for entry in entries:
        if entry["id"] == save_id:
            entry["last_played_at"] = now
            break
    _write_manifest(writable_root, entries)


def create_save(writable_root: Path, display_name: str) -> dict[str, Any]:
    entries = _read_manifest(writable_root)
    existing_ids = {e["id"] for e in entries}
    save_id = _slugify(display_name or "save", existing_ids)
    db_path = save_database_path(writable_root, save_id)
    initialise_database(db_path)
    entry = {"id": save_id, "display_name": display_name or save_id,
              "created_at": datetime.now().isoformat(timespec="seconds")}
    entries.append(entry)
    _write_manifest(writable_root, entries)
    return {"id": save_id, "database_path": str(db_path)}


def delete_save(writable_root: Path, save_id: str) -> None:
    entries = [e for e in _read_manifest(writable_root) if e["id"] != save_id]
    _write_manifest(writable_root, entries)
    db_path = save_database_path(writable_root, save_id)
    if db_path.exists():
        db_path.unlink()


def _active_save_path(writable_root: Path) -> Path:
    return writable_root / "data" / "active_save.json"


def read_active_save_id(writable_root: Path) -> str | None:
    path = _active_save_path(writable_root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("active_save_id")
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def write_active_save_id(writable_root: Path, save_id: str) -> None:
    path = _active_save_path(writable_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"active_save_id": save_id}) + "\n", encoding="utf-8")


def migrate_legacy_save(writable_root: Path, legacy_database: Path) -> None:
    """First-run-after-update migration: an existing install's single
    pre-v0.90.0 ``data/cricket_manager.db`` becomes "Save 1" so no one's
    in-progress career disappears when multi-save ships. Copies rather than
    moves the legacy file — nothing is destroyed, the old path is just no
    longer the one the game reads from once a manifest exists."""
    if not legacy_database.exists():
        return
    if _read_manifest(writable_root):
        return
    dest = save_database_path(writable_root, LEGACY_SAVE_ID)
    if not dest.exists():
        shutil.copy2(legacy_database, dest)
    _write_manifest(writable_root, [{"id": LEGACY_SAVE_ID, "display_name": LEGACY_SAVE_DISPLAY_NAME,
                                     "created_at": datetime.now().isoformat(timespec="seconds")}])


def ensure_active_save(writable_root: Path, legacy_database: Path) -> str:
    """Resolve which save should be active on boot: migrate a legacy
    single-save install if needed, fall back to the first save if none is
    marked active (or the marked one no longer exists), and create a
    brand-new "Save 1" for a genuinely fresh install with no saves at all."""
    migrate_legacy_save(writable_root, legacy_database)
    entries = _read_manifest(writable_root)
    if not entries:
        created = create_save(writable_root, LEGACY_SAVE_DISPLAY_NAME)
        entries = _read_manifest(writable_root)
        active_id = created["id"]
    else:
        active_id = read_active_save_id(writable_root)
        known_ids = {e["id"] for e in entries}
        if active_id not in known_ids:
            active_id = entries[0]["id"]
    write_active_save_id(writable_root, active_id)
    return active_id
