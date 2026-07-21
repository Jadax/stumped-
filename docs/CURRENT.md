# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-20
- **Branch:** main
- **Version:** 0.12.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)

## Objective

Major UI/UX revamp and feature-depth expansion per `docs/UX_REVAMP.md`
(user-requested, research-backed five-phase plan). Phase 1 (Midnight Pitch
design system, v0.10.0) and Phase 2 (FM-style player profile: star ratings,
market value, form sparkline, v0.11.0) and Phase 3 (broadcast matchday:
score-bug header, condition chips, momentum chart, crowd ambience with wicket
ducking, v0.12.0) are shipped; **Phase 4 (career depth) is next**, then
systems depth (Phase 5). The career startup flow roadmap item remains open.

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T20/ODI/Test), competitions, transfers, training, youth, facilities,
  finances, saves, packaged Windows builds through v0.9.0.
- All 50 unit tests pass (verified 2026-07-20, ~5.4 s).

## In progress / remaining (priority order)

1. **UX revamp Phase 4** — career depth: manager reputation, board
   confidence, job offers/sackings, season awards, trophy cabinet, world
   player ratings. Details in `docs/UX_REVAMP.md`.
2. UX revamp Phase 5 — systems depth (auctions, deeper finances, keeper
   specialisation, T10/Hundred formats).
3. Phase 3 leftover — a real chances panel (dropped catches, played & missed)
   needs `match_engine.py` to surface fielding-chance events on the delivery
   payload; the UI currently estimates these numbers.
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

- `python -m unittest discover -s tests` after v0.12.0 broadcast work →
  **Ran 57 tests, OK** (includes `tests/test_broadcast_presentation.py`).
- No lint/type-check exists. Audio ducking not verified on a real device
  (dev environment has a dummy audio driver) — worth a manual listen.

## Next recommended action

Implement UX revamp Phase 4 (career depth) per `docs/UX_REVAMP.md`: manager
reputation + board confidence model, season awards, trophy cabinet screen,
world player ratings table. Add tests, bump to 0.13.0, update this file,
commit and push.
