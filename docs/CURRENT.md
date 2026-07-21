# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-21
- **Branch:** main
- **Version:** 0.22.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)
- **Company:** Owned by ASTRAIVA (Pty) Ltd (South Africa) — all copyright/credit
  text must say this, never "Stumped! development team".

## Active initiative

The docs/DESIGN.md redesign delivery list is **complete** (v0.16–0.19). A
user screenshot review (v0.20–0.21) fixed real rendering/legibility bugs
(match header overlap, fullscreen blur, portraits, flags). This session
(v0.22.0) added a full **staff department** — Coaching, Medical, and
Scouting — a genuinely new game system, inspired by Football Manager/OOTP
staff mechanics per direct user request.

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T10/T20/ODI/Test), competitions, transfers, training, youth (targeted
  recruitment), facilities, finances, honours, career hub, contract
  negotiation, **staff (coaches/medical/scouts)**, saves.
- **119 unit tests pass** (verified 2026-07-21, ~17s); match-engine
  statistical validation (`python validate_match_engine.py`) realistic
  (T20 7.0 RPO, ODI 5.0, Test 3.95).
- `dist/Stumped.exe` rebuilt at v0.22.0 with passing diagnostics.

## New this session (v0.22.0) — Staff department

- **`src/models/staff.py`** + new `staff` DB table: every club has a real
  named roster — Head/Batting/Bowling/Fielding/Fitness Coaches, Doctor,
  Physio, Chief Scout, Scout — each with role attributes on a 1-20 scale.
  Existing saves auto-backfill via `_ensure_staff_for_all_teams`.
- **Coaches → training**: `database.team_coach_rating()` feeds
  `coach_training_multiplier()` into `apply_daily_training`'s per-discipline
  gain calculation (~0.72x-1.32x depending on coach quality).
- **Medical → injuries**: `database.team_physio_rating()` feeds
  `medical_injury_multiplier()` into `match_engine._maybe_injury` (both
  injury *chance* and *recovery duration*), stacking with the existing
  Medical Centre facility level. New **Medical Centre** screen
  (`ui/medical.py`) — the game previously tracked injuries in the DB with
  no screen to see them; this was a real gap, now closed.
- **Scouts → scouting accuracy**: `database.team_scout_rating()` feeds
  `scouting_noise()`/`apply_scouting_estimate()`; `scout_players()` now
  returns `estimated_overall`/`estimated_potential`/`confidence` alongside
  the true values. The Transfer Market table (`ui/transfers.py`) displays
  the *estimate*, not the omniscient true stat — a poor scouting network
  is visibly less reliable.
- **Staff ageing**: `age_staff_at_rollover()` runs every season rollover
  (young staff occasionally improve, veterans occasionally decline).
- New **Staff** screen (`ui/staff.py`): Coaching/Medical/Scouting tabs, a
  roster table, and a detail panel with attribute bars and contract terms.
- ASTRAIVA (Pty) Ltd publisher mark added to the splash screen (original
  vector recreation — the attached logo file itself could not be extracted
  from the chat into a repo asset, since there is no mechanism to save an
  inbound pasted image; if the user has the source file, drop it at
  `assets/images/astraiva_logo.png` and it can replace the procedural mark).

## Also fixed this session (v0.20.0–0.21.0) — see CHANGELOG.md for detail

- Squad quick-card crash, match header/action-row overlap, fullscreen blur
  on common monitors, text sharpness, real flag artwork, sharper portraits,
  "UI Foundation" placeholder removed, contract negotiation, targeted
  academy recruitment.

## In progress / remaining (priority order)

1. **Scouting assignments** — scouts are currently passive (their rating
   just affects estimate noise); FM-style active assignments (send a scout
   to a region/player for N days, then file a report) would deepen this
   further. Noted as a natural next step, not started.
2. Interactive job market — job offers/sackings driven by reputation and
   board confidence (`src/models/career.py` has the models; needs an offer
   flow, inbox actions, and club-switch plumbing).
3. The Hundred format — needs five-ball-over support in `match_engine.py`.
4. Roadmap `planned` items: live auctions, international management, academy
   expansion, financial forecasting, keeper batting roles, daily tournaments.
5. Career startup flow — `in_progress` in `src/data/roadmap.json`; verify gaps.
6. Real Steam integration (stubbed; app ID `null` in `config.json`).
7. Optional polish backlog: player quick-card on Selection/Transfers tables,
   crossfade screen transitions, skeleton loading rows for DB-heavy tabs.

## Known bugs / risks

- None known; no TODO/FIXME markers in source. `logs/error.log` is gitignored
  — check locally for runtime issues.
- Staff system is new and untested against a live multi-season save; watch
  for a club that ends up with zero staff in a group after many seasons of
  ageing/attrition (no re-hiring mechanic exists yet — staff never leave or
  get replaced, only age/drift in place).
- Audio ducking still not verified on a real device (dummy driver in dev).

## Decisions made

- Proprietary license; no licensed real-world content (all generated).
- SQLite single-file saves with in-place migrations; GBP-base accounting.
- pygame-ce + pygame-gui only; PyInstaller for distribution.
- `dist/`, `build/`, save DBs, and logs are gitignored (recreatable/local).
- Game owned by ASTRAIVA (Pty) Ltd — see branding note above.
- Text rendering: native-size SDL_ttf, not supersampled.
- Fullscreen: exact-integer SDL_SCALED only; never a fractional stretch.
- Scouting fog-of-war is scoped to the Transfer Market display only (not a
  global hidden-attributes system) — a deliberate, safely-bounded choice to
  avoid touching every screen that shows a player's own squad stats.

## Validation actually run (2026-07-21)

- `python -m unittest discover -s tests` → **Ran 119 tests, OK** (~17s).
- `python validate_match_engine.py` → realistic scoring/wicket rates,
  unaffected by the physio-rating injury change.
- `python tests/render_final_polish.py` → visual spot-check, no regressions.
- Manually rendered Staff and Medical Centre screens (all three staff
  groups, with and without active injuries) to confirm layout.
- `python build_and_package.py` → packaged build + diagnostics pass.
- Test note: never call `pygame.quit()` in tearDownClass — invalidates the
  lru-cached fonts for later test classes in the same run.

## Next recommended action

Build active scouting assignments (send a scout to a region or specific
player for N days; report quality/speed scales with judging ability) — the
natural completion of this session's staff system. Alternatively, pick up
the interactive job market. Add tests, bump the version, rebuild the exe,
update this file, commit and push.
