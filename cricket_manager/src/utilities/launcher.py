"""First-run preparation, integrity checks, and crash recovery."""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "game_title": "Stumped!", "version": "0.9.0", "database_path": "data/cricket_manager.db",
    "resolution": {"width": 1280, "height": 720, "fullscreen": False},
    "minimum_resolution": {"width": 1280, "height": 720},
    "ui": {"sidebar_width": 200, "top_bar_height": 60, "target_fps": 60},
    "colours": {"background": "#0d1117", "sidebar": "#161b22", "top_bar": "#161b22",
                "panel": "#1c2333", "green": "#3fb950", "green_hover": "#2ea043",
                "accent": "#58a6ff", "white": "#f0f6fc", "muted": "#8b949e",
                "border": "#30363d"},
    "gameplay": {"starting_date": "2026-04-01", "season_end_date": "2026-09-30",
                 "starting_team_id": 1, "game_speed": "Normal", "sound_on": True,
                 "master_volume": 70, "auto_save": "Monthly"},
}


@dataclass(frozen=True)
class LaunchPaths:
    resource_root: Path
    writable_root: Path
    config: Path
    data: Path
    logs: Path
    database: Path
    recovery: Path
    session_marker: Path


@dataclass
class LaunchState:
    paths: LaunchPaths
    previous_crash: bool = False
    recovery_loaded: bool = False
    archived_corrupt_database: Path | None = None


def get_launch_paths() -> LaunchPaths:
    frozen = bool(getattr(sys, "frozen", False))
    resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    if frozen:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Stumped"
    else:
        base = resource_root
    return LaunchPaths(resource_root, base, base / "config.json", base / "data", base / "logs",
                       base / "data" / "cricket_manager.db", base / "data" / "recovery.db",
                       base / "data" / "session.lock")


def _write_default_config(path: Path) -> None:
    path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")


def ensure_config(paths: LaunchPaths) -> dict[str, Any]:
    """Copy/create a valid editable config without losing malformed input."""
    if not paths.config.exists():
        bundled = paths.resource_root / "config.json"
        if bundled.exists() and bundled.resolve() != paths.config.resolve(): shutil.copy2(bundled, paths.config)
        else: _write_default_config(paths.config)
    try:
        config = json.loads(paths.config.read_text(encoding="utf-8"))
        required = {"game_title", "database_path", "resolution", "minimum_resolution", "ui", "colours"}
        if not required.issubset(config): raise ValueError("required settings are missing")
        return config
    except (OSError, ValueError, json.JSONDecodeError):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        invalid = paths.config.with_name(f"config.invalid-{stamp}.json")
        if paths.config.exists(): shutil.move(paths.config, invalid)
        _write_default_config(paths.config)
        return dict(DEFAULT_CONFIG)


def database_integrity(path: str | Path) -> tuple[bool, str]:
    target = Path(path)
    if not target.exists() or target.stat().st_size == 0: return True, "new database"
    try:
        uri = target.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try: result = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        finally: connection.close()
        return result.lower() == "ok", result
    except sqlite3.Error as exc:
        return False, str(exc)


def _ask_restore_recovery() -> bool:
    message = ("Stumped! did not close normally last time.\n\n"
               "A recovery save is available. Load it now?\n\n"
               "Choose No to keep the current save.")
    try:
        if sys.platform == "win32": return ctypes.windll.user32.MessageBoxW(None, message, "Stumped! — Recovery", 0x24) == 6
        return False
    except Exception:
        return False


def create_recovery_save(database: str | Path, recovery: str | Path) -> bool:
    """Use SQLite's online backup API so WAL-backed saves remain consistent."""
    source_path, recovery_path = Path(database), Path(recovery)
    if not source_path.exists(): return False
    recovery_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        source = sqlite3.connect(source_path)
        target = sqlite3.connect(recovery_path)
        try: source.backup(target)
        finally: target.close(); source.close()
        return database_integrity(recovery_path)[0]
    except sqlite3.Error:
        return False


def prepare_environment(paths: LaunchPaths | None = None) -> LaunchState:
    """Create writable state, restore crashes, and quarantine corrupt saves."""
    paths = paths or get_launch_paths()
    paths.writable_root.mkdir(parents=True, exist_ok=True)
    paths.data.mkdir(parents=True, exist_ok=True)
    paths.logs.mkdir(parents=True, exist_ok=True)
    ensure_config(paths)
    previous_crash = paths.session_marker.exists()
    state = LaunchState(paths, previous_crash=previous_crash)

    if previous_crash and database_integrity(paths.recovery)[0] and paths.recovery.exists() and _ask_restore_recovery():
        if paths.database.exists():
            backup = paths.data / f"pre-recovery-{datetime.now():%Y%m%d-%H%M%S}.db"
            shutil.copy2(paths.database, backup)
        shutil.copy2(paths.recovery, paths.database)
        state.recovery_loaded = True

    healthy, _ = database_integrity(paths.database)
    if not healthy and paths.database.exists():
        corrupt = paths.data / f"cricket_manager.corrupt-{datetime.now():%Y%m%d-%H%M%S}.db"
        shutil.move(paths.database, corrupt); state.archived_corrupt_database = corrupt

    if not paths.database.exists():
        bundled = paths.resource_root / "data" / "cricket_manager.db"
        if bundled.exists() and bundled.resolve() != paths.database.resolve() and database_integrity(bundled)[0]:
            shutil.copy2(bundled, paths.database)
    paths.session_marker.write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
    return state


def end_session(state: LaunchState, clean: bool = True) -> None:
    if clean:
        create_recovery_save(state.paths.database, state.paths.recovery)
        try: state.paths.session_marker.unlink(missing_ok=True)
        except OSError: pass


def run_diagnostics(paths: LaunchPaths | None = None) -> bool:
    """Non-graphical packaged-build smoke check used by release automation."""
    state = prepare_environment(paths)
    try:
        # Imported lazily to keep this utility independent of the game schema.
        from database import initialise_database
        initialise_database(state.paths.database)
        healthy, _ = database_integrity(state.paths.database)
        return healthy and state.paths.config.exists() and state.paths.logs.is_dir()
    finally:
        end_session(state, clean=True)
