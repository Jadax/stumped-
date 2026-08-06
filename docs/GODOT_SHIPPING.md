# Godot shipping contract

This is the short handover document for anyone continuing Stumped!. The
shipping game is **one Godot 4 client** in `godot_client/`. Do not build a
second UI in pygame. The Python package under `cricket_manager/` is retained
as the deterministic simulation and persistence backend used by Godot's IPC
bridge; its legacy `ui/` screens are compatibility code, not a second product.

## One source of truth

- Presentation: `godot_client/scenes/` and `godot_client/scripts/`.
- Design tokens: `godot_client/scripts/app_theme.gd` and `godot_client/ui/theme.json`.
- Game state and rules: `cricket_manager/match_engine.py`,
  `competition.py`, `database.py`, and `ipc_server.py`.
- Save format: SQLite under `cricket_manager/data/`; never duplicate state in
  Godot scene files.
- Windows release target: Godot 4.7.1's `Windows Desktop` export. The only
  user-facing release file is `godot_client_dist/StumpedGodot.exe`.
  Historical Python/PyInstaller executables and archives are deliberately not
  shipped; Python remains source/backend code only.

## Change protocol

1. Add or update an IPC method only when a screen needs data/action that does
   not already exist. Keep responses JSON-safe and deterministic.
2. Build reusable Godot controls before adding one-off screen code. Prefer
   `table_screen.gd`, `ground_view.gd`, `match_stats_canvas.gd`, and shared
   theme helpers.
3. Keep one screen per scene/script pair. Avoid parallel “v2” copies; replace
   the canonical screen and record the decision in `docs/CURRENT.md`.
4. Validate the smallest affected Python tests first, then the Godot smoke
   harness. Run the full release suite only for backend/schema/packaging
   changes.
5. Update `CHANGELOG.md` and this handoff document when a visual milestone is
   shipped. Commit to `main` and push after verification.

## Screen map for the supplied reference targets

| Reference | Canonical Godot destination |
|---|---|
| Match-day scorecard, batter/bowler views | `match_screen.tscn` |
| Player match analytics and career records | `player_profile_modal.tscn`, `season_records_screen.tscn` |
| Team hub and lineup | `dashboard_screen.tscn`, `training_screen.tscn`, `match_screen.tscn` pre-match |
| World Cup groups and final stages | `tournament_setup_screen.tscn`, `tournament_bracket_screen.tscn` |
| Domestic league table | `international_screen.tscn` / standings data view |
