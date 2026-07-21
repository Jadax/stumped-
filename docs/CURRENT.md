# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-20
- **Branch:** main
- **Version:** 0.13.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)

## Objective

Major UI/UX revamp and feature-depth expansion per `docs/UX_REVAMP.md`
(user-requested, research-backed five-phase plan). Phase 1 (Midnight Pitch
design system, v0.10.0) and Phase 2 (FM-style player profile: star ratings,
market value, form sparkline, v0.11.0) and Phase 3 (broadcast matchday:
score-bug header, condition chips, momentum chart, crowd ambience with wicket
ducking, v0.12.0) and Phase 4 first slice (Career screen: board confidence,
manager reputation, world ratings, season awards, trophy cabinet, v0.13.0)
are shipped. **Next: finish Phase 4** (persist honours at season end, wire
job offers/sackings off board confidence), then Phase 5 (systems depth).

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T20/ODI/Test), competitions, transfers, training, youth, facilities,
  finances, saves, packaged Windows builds through v0.9.0.
- All 50 unit tests pass (verified 2026-07-20, ~5.4 s).

## In progress / remaining (priority order)

1. **Phase 4 remainder** — persist honours into the save at season end (feed
   `context["honours"]` read by `ui/career.py`), award ceremony inbox message,
   job offers/sackings driven by `board_confidence()`; reputation currently
   uses league record only — persist a career-long match/trophy history.
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

- `python -m unittest discover -s tests` after v0.13.0 career work →
  **Ran 63 tests, OK** (includes `tests/test_career.py`).
- Test note: never call `pygame.quit()` in tearDownClass — it invalidates the
  lru-cached fonts for later test classes in the same run.
- Audio ducking still not verified on a real device — worth a manual listen.

## Next recommended action

Finish Phase 4: at season end append `{"title", "season"}` honours into the
save (surface via `context["honours"]`), send an awards inbox message using
`season_awards()`, and trigger job-offer/sacking events off
`board_confidence()`. Add tests, bump to 0.14.0, update this file, push.
