# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-20
- **Branch:** main
- **Version:** 0.9.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)

## Objective

Project handed off from Codex to alternating Codex/Claude development. The
game is feature-complete for a 0.9 release; next milestone (inferred from
`src/data/roadmap.json`) is finishing the **career startup flow** (manager
creation, game-mode selection, world configuration) and moving toward 1.0.

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T20/ODI/Test), competitions, transfers, training, youth, facilities,
  finances, saves, packaged Windows builds through v0.9.0.
- All 50 unit tests pass (verified 2026-07-20, ~5.4 s).

## In progress / remaining (priority order)

1. Career startup flow — listed as `in_progress` in `src/data/roadmap.json`;
   screens exist (`src/views/screens/new_game_setup.py`,
   `career_team_selection.py`, `tournament_setup.py`, `world_cup_setup.py`)
   and `test_startup_flow.py` passes, so verify what remains vs. roadmap.
2. Real Steam integration (currently stubbed in `src/steam_integration.py`;
   app ID is `null` in `config.json`).
3. Roadmap `planned` items (trophy cabinet, deeper finances, more formats, …).

## Known bugs / risks

- None known; no TODO/FIXME markers in source. `logs/error.log` is gitignored —
  check locally for runtime issues.

## Decisions made

- Proprietary license; no licensed real-world content (all generated).
- SQLite single-file saves with in-place migrations; GBP-base accounting.
- pygame-ce + pygame-gui only; PyInstaller for distribution.
- `dist/`, `build/`, save DBs, and logs are gitignored (recreatable/local).

## Validation actually run (2026-07-20)

- `python -m unittest discover -s tests -v` → **Ran 50 tests, OK**.
- No lint/type-check exists.

## Next recommended action

Compare the implemented startup screens against the roadmap's
`startup_flow` item; either finish the gaps or mark it `done` in
`src/data/roadmap.json`, then bump toward 1.0 planning.
