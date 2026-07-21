# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-21
- **Branch:** main
- **Version:** 0.21.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)
- **Company:** Owned by ASTRAIVA (Pty) Ltd (South Africa) — all copyright/credit
  text must say this, never "Stumped! development team".

## Active initiative: approved UI redesign (docs/DESIGN.md)

The user approved the "Test at Dusk" redesign; the docs/DESIGN.md delivery
list is **complete** (theme, components, shell, accessibility settings all
shipped through v0.19.0). Since then, a user screenshot review (v0.20–0.21)
surfaced real rendering/legibility bugs that the redesign had introduced or
left unaddressed — all fixed this session, see below.

## Objective

Continue polishing based on direct user feedback on screenshots. This
session (v0.20.0 → v0.21.0) fixed a real crash and a batch of visual/UX
bugs, and added two user-requested gameplay features (contract negotiation,
targeted academy recruitment). Prior phases (UX_REVAMP.md 5-phase plan,
DESIGN.md redesign) are complete — see CHANGELOG.md for full history.

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T10/T20/ODI/Test), competitions, transfers, training, youth (incl.
  targeted recruitment), facilities, finances, honours, career hub, contract
  negotiation, saves.
- **104 unit tests pass** (verified 2026-07-21, ~13 s); match-engine
  statistical validation (`python validate_match_engine.py`) shows realistic
  rates (T20 7.0 RPO, ODI 5.0, Test 3.95).
- Packaged Windows build is current: `dist/Stumped.exe` rebuilt at v0.21.0
  (never let this drift — see `docs/UX_REVAMP.md`/AGENTS.md: every version
  bump must rebuild the exe via `python build_and_package.py`).

## Fixed this session (v0.20.0–0.21.0) — see CHANGELOG.md for full detail

- Squad quick-card crash (mental dict overwritten by an int average).
- Match screen score-bug: six fields crammed into one row with hardcoded
  offsets, overlapping/merging text at 1280x720 — rewritten as a six-column
  grid (`MatchScreen.HEADER_COLUMNS`) with vertical dividers, impossible to
  overlap by construction.
- Match screen action row: ten buttons crammed into one row, label text
  bleeding into neighbours — now two clearly-spaced rows (index order 0–9
  preserved for `process_event`, only on-screen position changed).
- Fullscreen text blur on common monitors: `_fullscreen_logical_size` always
  targeted ~1920x1080 regardless of desktop size, giving a *non-integer*
  SDL_SCALED stretch (2560x1440 → 1.33x = blur). Now picks the largest exact
  integer divisor (1440p/4K/ultrawide/5K all get a clean 2x).
  Non-clean-divisor desktops fall back to the old proportional approach.
- Text rendering: removed the 2x-supersample-then-downscale pass (it read
  soft on larger monitors) in favour of native-size SDL_ttf rendering; all
  remaining aliased circles/lines (radar chart, gauges) are now anti-aliased.
- Real flag artwork (bundled Flagpedia PNGs) replaces hand-drawn flags.
- Player portraits: 4x supersampling (was 3x), kit collar, edge vignette.
- Removed "UI FOUNDATION 2.14+" placeholder; sidebar footer + all
  credits/legal text now read "ASTRAIVA (Pty) Ltd".
- Spatial analytics (wagon wheel/bowling map) on the player profile: much
  larger area + a This Match/Season filter so it won't get cramped as
  season data accumulates.

## Added this session — new gameplay features

- **Contract negotiation** (`src/models/contracts.py`,
  `ui/widgets/contract_modal.py`): propose wage/years/bonus; the player
  accepts/counters/rejects based on true valuation, morale, age, and
  contract security. Reachable via NEGOTIATE on any player profile.
  `database.renew_player_contract()` persists agreed terms.
- **Targeted academy recruitment** (`database.recruit_youth(role_focus=...)`,
  `database.ACADEMY_ROLE_FOCUSES`): Youth Academy screen has a "Scout For"
  role cycle button (Any/Batsman/Pace Bowler/Spin Bowler/All-Rounder/
  Wicketkeeper). Generation stays realistic — a requested bowler never
  quietly out-bats a requested batsman; pace vs spin focus biases each
  recruit's actual pace/swing_or_spin skill split, verified per-recruit
  in tests, not just on average.

## In progress / remaining (priority order)

1. Interactive job market — job offers/sackings driven by reputation and
   board confidence (`src/models/career.py` has the models; needs an offer
   flow, inbox actions, and club-switch plumbing).
2. The Hundred format — needs five-ball-over support in `match_engine.py`.
3. Roadmap `planned` items: live auctions, international management, academy
   expansion, financial forecasting, keeper batting roles, daily tournaments.
4. Career startup flow — `in_progress` in `src/data/roadmap.json`; verify gaps.
5. Real Steam integration (stubbed; app ID `null` in `config.json`).
6. Optional polish backlog: player quick-card on Selection/Transfers tables
   (currently only on Squad), crossfade screen transitions, skeleton loading
   rows for DB-heavy tabs.

## Known bugs / risks

- None known; no TODO/FIXME markers in source. `logs/error.log` is gitignored
  — check locally for runtime issues.
- Contract negotiation and academy role-focus are new — untested against a
  live multi-season save; watch for edge cases (e.g. negotiating with a
  player who has 0 years contract remaining, or an academy with a very high
  level producing implausibly strong 16-year-olds).
- Audio ducking still not verified on a real device (dummy driver in dev).

## Decisions made

- Proprietary license; no licensed real-world content (all generated).
- SQLite single-file saves with in-place migrations; GBP-base accounting.
- pygame-ce + pygame-gui only; PyInstaller for distribution.
- `dist/`, `build/`, save DBs, and logs are gitignored (recreatable/local).
- Game owned by ASTRAIVA (Pty) Ltd — see branding note above.
- Text rendering: native-size SDL_ttf, not supersampled (see "Fixed" above).
- Fullscreen: exact-integer SDL_SCALED only; never a fractional stretch.

## Validation actually run (2026-07-21)

- `python -m unittest discover -s tests` → **Ran 104 tests, OK** (~13s).
- `python tests/render_final_polish.py` → visual spot-check of Dashboard,
  Selection, Transfer Market, Training, Facilities screens — clean, no
  regressions.
- Manually rendered the Match screen headlessly (T20 and Test formats) to
  confirm the header/action-row rewrite has zero overlapping elements.
- `python build_and_package.py` → packaged build + diagnostics pass.
- Test note: never call `pygame.quit()` in tearDownClass — it invalidates
  the lru-cached fonts for later test classes in the same run.

## Next recommended action

Build the interactive job market (offers/sackings off `board_confidence()`
and `manager_reputation()`, inbox-driven, with club switching) — the next
substantial feature gap. Alternatively, pick up the optional polish backlog
item 6 above. Add tests, bump the version, rebuild the exe, update this
file, commit and push.
