# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-20
- **Branch:** main
- **Version:** 0.11.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)

## Objective

Major UI/UX revamp and feature-depth expansion per `docs/UX_REVAMP.md`
(user-requested, research-backed five-phase plan). Phase 1 (Midnight Pitch
design system, v0.10.0) and Phase 2 (FM-style player profile: star ratings,
market value, form sparkline, v0.11.0) are shipped; **Phase 3 (broadcast
matchday presentation) is next**, then career depth (Phase 4) and systems
depth (Phase 5). The career startup flow roadmap item also remains open.

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T20/ODI/Test), competitions, transfers, training, youth, facilities,
  finances, saves, packaged Windows builds through v0.9.0.
- All 50 unit tests pass (verified 2026-07-20, ~5.4 s).

## In progress / remaining (priority order)

1. **UX revamp Phase 3** — broadcast matchday presentation (`ui/match_view.py`):
   score bug, condition icon strip, beehive/pitch-map overlays, chances panel,
   momentum graph, wicket audio ducking.
2. UX revamp Phases 4–5 — career depth (reputation, job offers, trophy
   cabinet, world ratings) and systems depth (auctions, deeper finances,
   keeper specialisation, T10/Hundred). Details in `docs/UX_REVAMP.md`.
3. Career startup flow — `in_progress` in `src/data/roadmap.json`; verify gaps.
4. Real Steam integration (stubbed; app ID `null` in `config.json`).

## Known bugs / risks

- None known; no TODO/FIXME markers in source. `logs/error.log` is gitignored —
  check locally for runtime issues.

## Decisions made

- Proprietary license; no licensed real-world content (all generated).
- SQLite single-file saves with in-place migrations; GBP-base accounting.
- pygame-ce + pygame-gui only; PyInstaller for distribution.
- `dist/`, `build/`, save DBs, and logs are gitignored (recreatable/local).

## Validation actually run (2026-07-20)

- `python -m unittest discover -s tests` after v0.11.0 profile work →
  **Ran 53 tests, OK** (includes new `tests/test_ui_profile.py` render checks).
- No lint/type-check exists.

## Next recommended action

Implement UX revamp Phase 3 (broadcast matchday presentation) per
`docs/UX_REVAMP.md`: score bug + condition strip in `ui/match_view.py`,
beehive/pitch-map overlays, chances panel fed by real match-engine events,
momentum graph, wicket audio ducking in `src/controllers/audio_controller.py`.
Add tests, bump to 0.12.0, update this file, commit and push.
