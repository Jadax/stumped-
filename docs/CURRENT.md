# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-21
- **Branch:** main
- **Version:** 0.23.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)
- **Company:** Owned by ASTRAIVA (Pty) Ltd (South Africa) — all copyright/credit
  text must say this, never "Stumped! development team".

## Active initiative

The docs/DESIGN.md redesign delivery list is **complete** (v0.16–0.19). A
user screenshot review (v0.20–0.21) fixed real rendering/legibility bugs
(match header overlap, fullscreen blur, portraits, flags). v0.22.0 added the
**staff department** (Coaching, Medical, Scouting) as a genuinely new game
system, inspired by Football Manager/OOTP staff mechanics. v0.23.0 completed
it with a **staff transfer market**, staff retirement/regeneration, and
**live commentary modes** — all direct follow-up requests from the same
staff-system ask, given full creative authority ("make changes you would
make as if this were your game").

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T10/T20/ODI/Test), competitions, transfers, training, youth (targeted
  recruitment), facilities, finances, honours, career hub, contract
  negotiation, **staff (coaches/medical/scouts, transfer market, retirement)**,
  live commentary modes, saves.
- **131 unit tests pass** (verified 2026-07-21, ~18s); match-engine
  statistical validation (`python validate_match_engine.py`) realistic
  (T20 7.0 RPO, ODI 5.0, Test 3.95).
- `dist/Stumped.exe` rebuilt at v0.23.0 with passing diagnostics.

## New in v0.23.0 — staff market, retirement, commentary modes

- **Staff market** (`ui/staff.py` Market tab; `database.browse_staff_market`,
  `make_staff_offer`, `resolve_staff_offer`, `sell_staff_member`,
  `staff_transfer_value`): browse every other club's staff, sign for an
  immediate fee (cash moves both ways, blocked if the buyer can't afford
  it), or release your own staff back to the market. New
  `staff_transfer_offers` table records every deal.
- **Staff retirement/regeneration** (`database.age_staff_at_rollover`,
  `STAFF_RETIREMENT_AGE = 66`): rising retirement chance from 66+, each
  retiree immediately replaced so departments never go empty.
  `competition.rollover_season()`'s return dict now includes
  `staff_retired`.
- **Commentary modes** (`ui/match_view.py`): a COMM button toggles Full vs
  Key Moments (wickets/boundaries/milestones only) — useful once match
  speed is turned up. Fixing this also required widening the header's
  reserved control area (`speed_w` 246→360) to fit the new button without
  overflowing past the content edge — covered by a dedicated layout test.
- Scouting UI note: the user's request to put staff "in the transfer list"
  was interpreted as its own Market tab on the Staff screen rather than
  merging into `ui/transfers.py`'s player table — cleaner UX, kept clubs'
  player and staff dealings visually distinct. Worth revisiting if the user
  wants them unified.

## New in v0.22.0 — Staff department

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
2. **AI-initiated staff/player offers** — the user can buy/sell staff and
   players, but no AI club currently *initiates* a bid for your staff or
   players outside the handful of seeded incoming offers. Would need a
   periodic AI-evaluation pass (e.g. during `advance_day`).
3. Interactive job market — job offers/sackings driven by reputation and
   board confidence (`src/models/career.py` has the models; needs an offer
   flow, inbox actions, and club-switch plumbing).
4. The Hundred format — needs five-ball-over support in `match_engine.py`.
5. Roadmap `planned` items: live auctions, international management, academy
   expansion, financial forecasting, keeper batting roles, daily tournaments.
6. Career startup flow — `in_progress` in `src/data/roadmap.json`; verify gaps.
7. Real Steam integration (stubbed; app ID `null` in `config.json`).
8. Optional polish backlog: player quick-card on Selection/Transfers tables,
   crossfade screen transitions, skeleton loading rows for DB-heavy tabs.

## Known bugs / risks

- None known; no TODO/FIXME markers in source. `logs/error.log` is gitignored
  — check locally for runtime issues.
- Staff system (incl. market and retirement) is new and untested against a
  live multi-season save. Retirement always regenerates a same-role
  replacement so departments can't go empty *from ageing*, but selling a
  staff member on the Market deliberately leaves that role vacant until the
  user hires a replacement — watch for a club drifting for many seasons
  with an unfilled role if the user never revisits the Market.
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

- `python -m unittest discover -s tests` → **Ran 131 tests, OK** (~18s).
- `python validate_match_engine.py` → realistic scoring/wicket rates,
  unaffected by the physio-rating injury change.
- `python tests/render_final_polish.py` → visual spot-check, no regressions.
- Manually rendered Staff (Roster + Market modes), Medical Centre, and the
  Match screen's new header/commentary controls; verified a full staff
  signing end-to-end (cash both ways, roster updated) headlessly.
- `python build_and_package.py` → packaged build + diagnostics pass.
- Test note: never call `pygame.quit()` in tearDownClass — invalidates the
  lru-cached fonts for later test classes in the same run.

## Next recommended action

Build active scouting assignments (send a scout to a region or specific
player for N days; report quality/speed scales with judging ability), or
AI-initiated staff/player offers (see remaining item 2) so the market feels
two-directional rather than user-only. Add tests, bump the version, rebuild
the exe, update this file, commit and push.
