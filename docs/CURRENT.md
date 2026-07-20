# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-20
- **Branch:** main
- **Version:** 0.10.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)

## Objective

Major UI/UX revamp and feature-depth expansion per `docs/UX_REVAMP.md`
(user-requested, research-backed five-phase plan). Phase 1 (Midnight Pitch
design system) shipped in v0.10.0; **Phase 2 (FM-style player profile hub)
is next**, then broadcast matchday presentation (Phase 3), career depth
(Phase 4), systems depth (Phase 5). The career startup flow roadmap item
also remains in progress.

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T20/ODI/Test), competitions, transfers, training, youth, facilities,
  finances, saves, packaged Windows builds through v0.9.0.
- All 50 unit tests pass (verified 2026-07-20, ~5.4 s).

## In progress / remaining (priority order)

1. **UX revamp Phase 2** — FM-style player profile hub (`ui/player_modals.py`,
   `src/views/screens/player_detail.py`): header strip, tiered attribute
   columns via `theme.attribute_colour()`, form sparkline, comparison overlay.
2. UX revamp Phase 3 — broadcast matchday presentation (`ui/match_view.py`):
   score bug, condition icon strip, beehive/pitch-map overlays, chances panel,
   momentum graph, wicket audio ducking.
3. UX revamp Phases 4–5 — career depth (reputation, job offers, trophy
   cabinet, world ratings) and systems depth (auctions, deeper finances,
   keeper specialisation, T10/Hundred). Details in `docs/UX_REVAMP.md`.
4. Career startup flow — `in_progress` in `src/data/roadmap.json`; verify gaps.
5. Real Steam integration (stubbed; app ID `null` in `config.json`).

## Known bugs / risks

- None known; no TODO/FIXME markers in source. `logs/error.log` is gitignored —
  check locally for runtime issues.

## Decisions made

- Proprietary license; no licensed real-world content (all generated).
- SQLite single-file saves with in-place migrations; GBP-base accounting.
- pygame-ce + pygame-gui only; PyInstaller for distribution.
- `dist/`, `build/`, save DBs, and logs are gitignored (recreatable/local).

## Validation actually run (2026-07-20)

- `python -m unittest discover -s tests` after the v0.10.0 skin change →
  **Ran 50 tests, OK**; headless smoke-render of Card and AttributeBar passed.
- No lint/type-check exists.

## Next recommended action

Implement UX revamp Phase 2 (player profile hub) per `docs/UX_REVAMP.md`,
using `theme.attribute_colour()` and `theme.vertical_gradient()`; add tests,
bump to 0.11.0, update this file, commit and push.
