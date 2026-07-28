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

from database import get_team_summary, initialise_database, load_game

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


def list_saves(writable_root: Path) -> list[dict[str, Any]]:
    """Save metadata for the Load Game screen, newest-created first."""
    entries = _read_manifest(writable_root)
    results = []
    for entry in entries:
        db_path = save_database_path(writable_root, entry["id"])
        summary = dict(entry)
        if db_path.exists():
            try:
                game_data = load_game(db_path)
                team_id = game_data["user"].get("current_team_id")
                team = get_team_summary(team_id, db_path) if team_id else None
                summary["team_name"] = team["name"] if team else None
                summary["division"] = team.get("division") if team else None
                manager = game_data.get("state", {}).get("new_game_setup", {}).get("manager", {})
                summary["manager_name"] = manager.get("name")
                summary["current_date"] = game_data["user"].get("current_date")
            except (OSError, KeyError, ValueError):
                summary["team_name"] = None
        else:
            summary["team_name"] = None
        results.append(summary)
    results.sort(key=lambda e: e.get("created_at", ""), reverse=True)
    return results


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
