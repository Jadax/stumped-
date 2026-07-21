# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-20
- **Branch:** main
- **Version:** 0.17.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)

## Active initiative: approved UI redesign (docs/DESIGN.md)

The user approved the "Test at Dusk" redesign. Delivery order (doc §10):
theme ✅ (v0.16.0) → components (OverBeads ✅, Buttons ✅, TabBar ✅;
shared DataTable + player quick-card pending) → shell ✅ (grouped sidebar,
CONTINUE ▸ loop button, v0.17.0) → next: Dashboard bento polish → Squad →
Selection balance meter → Match three-zone → remaining screens → animation +
accessibility passes (UI scale, colour-blind glyphs, reduced motion). Every step ends: tests + version bump + exe rebuild
(`python build_and_package.py`) + push.

## Objective

Major UI/UX revamp and feature-depth expansion per `docs/UX_REVAMP.md`
(user-requested, research-backed five-phase plan). Phase 1 (Midnight Pitch
design system, v0.10.0) and Phase 2 (FM-style player profile: star ratings,
market value, form sparkline, v0.11.0) and Phase 3 (broadcast matchday:
score-bug header, condition chips, momentum chart, crowd ambience with wicket
ducking, v0.12.0), Phase 4 (Career screen v0.13.0; persisted honours,
season-award and board-review briefings, real fielding-chance tracking
v0.14.0), and a Phase 5 slice (T10 format, keeper byes, monthly P&L digest
v0.15.0) are **all shipped**. Remaining ambitions are the `planned` items in
`src/data/roadmap.json`.

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T10/T20/ODI/Test), competitions, transfers, training, youth, facilities,
  finances, honours, career hub, saves; packaged builds through v0.9.0.
- All 69 unit tests pass (verified 2026-07-21, ~7 s); match-engine
  statistical validation (`python validate_match_engine.py`) shows realistic
  rates (T20 7.0 RPO, ODI 5.0, Test 3.95).

## In progress / remaining (priority order)

1. Interactive job market — job offers/sackings driven by reputation and
   board confidence (`src/models/career.py` has the models; needs an offer
   flow, inbox actions, and club-switch plumbing).
2. The Hundred format — needs five-ball-over support in `match_engine.py`.
3. Roadmap `planned` items: live auctions, international management, academy
   expansion, financial forecasting, keeper batting roles, daily tournaments.
4. Career startup flow — `in_progress` in `src/data/roadmap.json`; verify gaps.
5. Real Steam integration (stubbed; app ID `null` in `config.json`).
6. Rebuild the packaged Windows edition (`python build_and_package.py`) —
   dist/ still contains v0.9.0.

## Known bugs / risks

- None known; no TODO/FIXME markers in source. `logs/error.log` is gitignored —
  check locally for runtime issues.

## Decisions made

- Proprietary license; no licensed real-world content (all generated).
- SQLite single-file saves with in-place migrations; GBP-base accounting.
- pygame-ce + pygame-gui only; PyInstaller for distribution.
- `dist/`, `build/`, save DBs, and logs are gitignored (recreatable/local).

## Validation actually run (2026-07-20)

- `python -m unittest discover -s tests` after v0.15.0 systems work →
  **Ran 69 tests, OK**; `python validate_match_engine.py` realistic.
- Test note: never call `pygame.quit()` in tearDownClass — it invalidates the
  lru-cached fonts for later test classes in the same run.
- Audio ducking still not verified on a real device — worth a manual listen.

## Next recommended action

Build the interactive job market (offers/sackings off `board_confidence()`
and `manager_reputation()`, inbox-driven, with club switching), or rebuild
and smoke-test the packaged Windows edition to refresh dist/ to v0.15.0.
Add tests, bump the version, update this file, commit and push.
