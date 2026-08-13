# CURRENT — cross-agent handoff

- **Last updated:** 2026-08-13
- **Branch:** main
- **Version:** 4.70.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)
- **v4.70.0**: product-polish pass added shared hover-lift interactions for
  navigation/menu controls, an original vector ball-and-stumps title mark,
  and a brief colour-coded live-match impact cue for boundaries/wickets.
  The canonical Godot export was rebuilt to
  `godot_client_dist/StumpedGodot.exe`.
- **v4.69.0**: added a subtle procedural title-screen music bed and animated
  first-run onboarding transitions, completing the current atmosphere and
  onboarding pass without introducing external asset dependencies.
- **v4.68.0**: Steam-readiness presentation pass. Godot now has procedural
  fallback sound effects and a looping stadium ambience bed, plus an original
  vector stadium environment on the main menu; no external audio or licensed
  imagery is required.
- **v4.67.0 — the Academy Cup; academy_expansion COMPLETE**: closes
  roadmap.json's last open academy_expansion sub-item ("youth
  competitions") with a real knockout cup among academy-eligible talent,
  resolved by `CompetitionEngine.simulate_youth_fixture` (rates each side
  by youth talent only), always auto-resolved even for the user's own
  club. **Two real bugs found and fixed while building this**: (1)
  `rollover_season`'s cup-final lookup picked one "most recent Cup final"
  with no name filter — once the T20 Cup existed alongside the Domestic
  Knockout Cup, only whichever finished latest each season ever got a
  "Cup Winners" honour; the other was silently skipped every season since
  it was added. Now one honour per Cup competition. (2) Excluding the
  Academy Cup from `advance_day`'s "block on an unplayed user fixture"
  check via an `INNER JOIN competitions` silently dropped any fixture with
  a NULL `competition_id` (a real, nullable column) from the whole check —
  would have let real user fixtures sail past undetected, caught
  immediately by this project's own existing v4.23.0 regression test.
  Fixed with a `LEFT JOIN` + NULL-safe comparison. New
  `tests/test_academy_cup.py` (6)/`tests/test_cup_honours_bugfix.py` (2);
  `test_long_save_stability.py` re-verified clean given the `advance_day`
  changes. 619 backend tests pass. No new Godot screen — surfaces via the
  existing Calendar/Trophy Room, matching the T20 Cup's existing
  visibility level.
- **v4.66.0 — real national squad control** (roadmap.json's
  `international_management`, now `done`): researched the actual gap first
  — `dual_management`/`bilateral_tours` were already real, but every
  national-team decision was 100% automatic (`select_national_xi` always
  hardcoded the best-11, no setter existed). **Found a separate real bug
  along the way**: `database.get_national_xi` (which
  `ipc_server._get_national_team_ipc` calls for the National Team screen)
  imported `select_national_xi` from `src.models.international` — a module
  that has never defined that function, only `database.py` ever has. Every
  call raised `ImportError`; the screen's XI display has been broken for
  any manager who ever accepted a national job, zero test coverage
  catching it. New `toggle_national_xi`/`get_national_xi_override`
  (same interaction the club Selection screen already uses);
  `select_national_xi` prefers a complete, still-eligible manager
  selection, falling back to automatic otherwise — used everywhere
  national XIs are picked with no other call-site changes needed. New IPC
  `toggle_national_xi`; Godot's National Team screen gained a SELECT/DROP
  button per player. New `tests/test_national_xi_selection.py` (12 tests).
  611 backend tests pass (1 pre-existing conditional skip, unrelated).
- **v4.65.0 — the Weekly Challenge** (roadmap.json's `daily_tournaments`,
  now `done`): a fresh optional challenge offered every Monday against a
  random opponent, resolved immediately (not a scheduled live fixture —
  deliberately avoids re-risking v4.60.3's fixture-collision bug class),
  with a real cash reward that compounds with a win streak. New
  `database.ensure_weekly_challenge`/`play_weekly_challenge`, new IPC
  methods, a "WEEKLY CHALLENGE" card on Godot's Dashboard (screenshot-
  confirmed). New `tests/test_weekly_challenge.py` (9 tests). 599 backend
  tests pass.
- **v4.64.0 — real academy graduation** (roadmap.json's `academy_expansion`
  "expanded development paths" sub-item): a real bug found while scoping
  it — nothing anywhere ever cleared `players.academy_squad` once set, so
  a player stayed listed as a Youth Academy "prospect" forever, even at
  30+ (`ipc_server._academy_eligible` includes anyone with the flag,
  not just genuine under-20s). `rollover_season` now clears it at 21, and
  posts a real graduation moment (inbox message + v4.59.0 narrative event,
  scoped to the user's own club). New `tests/test_academy_graduation.py`
  (5 tests). 590 backend tests pass. No Godot changes needed — the screen
  was always reading the flag correctly; the flag itself was wrong.
  "Youth competitions" remains the one open academy_expansion sub-item.
- **v4.63.0 — live player auctions** (roadmap.json's `live_auctions`, now
  `done`): closed a real pre-existing gap found while scoping this —
  `set_transfer_listed` existed but was never wired to any Godot IPC
  method, so a Godot manager had no way to list their own player for sale
  at all. New `auctions` table + `start_player_auction`/
  `place_auction_bid`/`advance_auctions` (daily tick from `advance_day`:
  AI clubs bid on real squad need capped by valuation, deadline resolution
  moves cash/player or leaves the player unsold). New IPC methods; Godot
  gained an "AUCTIONS" tab (RECRUITMENT group) and an "AUCTION" button on
  every Squad row, both screenshot-confirmed. New
  `tests/test_player_auctions.py` (14 tests). 585 backend tests pass.
- **v4.62.0 — regional academy scouting** (roadmap.json's `academy_expansion`,
  now `in_progress` not `planned`): `recruit_youth` was silently forcing
  every prospect's nationality to the club's own `country_id` no matter
  what was passed in — a real, confirmed gap, no "regional scouting" lever
  existed anywhere. New `database.get_academy_focus_nation`/
  `set_academy_focus_nation` (persisted standing preference, defaults to
  the club's own nation), new `ACADEMY_NATION_NAMES` constant (also fixed
  a real drift — the old inline dict had "Afghanistan" instead of
  "Zimbabwe", not matching `nations_config.py`'s canonical ten). New IPC
  `get_academy_scouting_region`/`set_academy_scouting_region` (named
  distinctly from the pre-existing, unrelated `set_academy_focus`
  training-programme lever). Godot's Youth Academy screen gained a
  "SCOUTING REGION" cycle button, screenshot-confirmed working. New
  `tests/test_academy_regional_scouting.py` (9 tests). 571 backend tests
  pass. "Youth competitions"/"expanded development paths" (the other two
  academy_expansion sub-items) remain open, not attempted in this pass.
- **v4.61.0 — reconciled the two "momentum" concepts**: v4.60.0's real
  backend `Innings.momentum` (used by the live ScoreBar) and the Stats
  Hub's pre-existing client-side "Momentum" chart (a different,
  independently-invented trailing-24-ball formula) were two different
  things both called momentum — flagged as a follow-up in v4.60.0's own
  changelog. New `InningsState.momentum_history` (the per-ball trail of
  the real value) is now what `match_stats_canvas.gd`'s Momentum chart
  plots directly; `match_screen.gd`'s separate client-side
  `momentum_window` accumulator is gone entirely. One value, one source of
  truth. 562 backend tests pass; screenshot-verified Match Day still works
  end to end.
- **v4.60.3 — fixture date-collision fixed; "fully retire the division
  system" descoped to its own future pass**: researched every consumer of
  `teams.division`/`LEAGUE_NAMES` before attempting task (6) below and
  found the real scope is much bigger than scheduling — `division` is also
  the world-generation *quality tier* (`_team_quality_modifier`/
  `_target_rating`/`wage_for_player`/staff generation, division 1 = best
  ~20 teams globally, unrelated to nation), a job-market eligibility gate
  (`generate_job_offers`), and a scouting valuation heuristic — none of
  which map cleanly onto a team's `nation_division` (1 or 2 within its OWN
  country). Collapsing them means redesigning world-gen's quality model,
  not just fixture scheduling; doing that safely needs its own properly-
  scoped pass, not a rush inside this one. **Fixed the concrete bug
  instead**: `ensure_per_nation_season`'s cursor now starts strictly after
  every one of a nation's teams' own global-division fixtures conclude
  (queried via real `MAX(date)`, not assumed), so the two schedules can
  never collide on a date for the same team — this is what actually
  produced the Lancashire-vs-Glamorgan-twice symptom the v4.60.2 QA sweep
  observed. New regression test reproduces that exact scenario. 561
  backend tests pass (1 known-flaky, confirmed unrelated). Foreign-player
  limits (`get_foreign_player_limit` etc.) confirmed dead code — defined,
  never called anywhere — left untouched.
  **Queued as its own future pass, not abandoned**: retiring
  `teams.division` as the domestic-structure driver in favour of
  per-nation leagues, which requires first designing a nation-aware
  replacement for the global quality-tier concept (task 6 in this
  session's list is otherwise done in its narrowed scope).
- **Post-revamp QA sweep** (user request 2026-08-09: "ensure no
  issues, the workflow and phases are the best, everything works
  properly"). Ran the full 38-screen `--screenshot-test` list and reviewed
  every screenshot — found and fixed a real pre-existing bug (below);
  next up: (7)
  reconcile the two "momentum" concepts, (8) a new roadmap feature (youth
  academy expansion). Task list is in-session; no separate plan file for
  this pass.
- **v4.60.2 — Selection screen's briefing card fixed (pre-existing bug,
  unrelated to v4.57.0-v4.60.0)**: `table_screen.gd`'s
  `_build_selection_brief()` nested each value Label one level deeper than
  `_update_selection_brief()`'s `get_node("HBoxContainer/<NAME>")` lookups
  expected — the STARTING XI/LEADERSHIP/CONDITIONS/TACTICAL CHECK card had
  been stuck on "Loading…" forever, found only by actually screenshotting
  the Selection screen. Fixed with a `_selection_brief_values` dictionary
  of direct label references instead of a brittle path. Full 38-screen
  sweep otherwise clean (zero script/node errors). **Observed but not
  fixed**: the Calendar screen shows a real symptom of v4.57.0's additive
  scope decision — a team can be scheduled against the same opponent on
  the same date via both the legacy global division and the new
  per-nation league (two independent random round-robins over overlapping
  team pools). Not a crash, but a visible gap — this is exactly what
  closing the Phase 1 descope (queued next) fixes properly.
- **v4.60.1 — Godot verification pass**: v4.60.0 honestly flagged its own
  Godot UI as unverified; ran the real `--editor --quit`/export/
  `--screenshot-test` cycle and found two real bugs. (1)
  `league_standings_screen.gd` (v4.57.0) **failed to parse entirely** —
  `x in ("A","B")` isn't valid GDScript (no tuple literal; use `["A","B"]`)
  — the League Standings screen had been silently broken since v4.57.0
  shipped. (2) v4.60.0's momentum/crowd labels used dark-card text colours
  on the ScoreBar's solid green background, reading as clipped/invisible;
  restyled to match `status_label`/`rates_label`'s existing white-on-green
  pattern. Screenshot-confirmed working after both fixes: League
  Standings' Nations tab, Dashboard's Storylines card, Match Day's
  Momentum/Crowd/Key-Moments. **Lesson for future GDScript work in this
  project**: there is no static type-check/parse-check in the Python test
  suite for `.gd` files — a syntax error here is invisible until someone
  actually runs `godot --headless --editor --path godot_client --quit` (or
  the full app). Any session shipping a new/edited `.gd` file should run
  that scan before calling the work done, not just read the diff.
- **Design-lead revamp — COMPLETE** (user request 2026-08-09: "make it the
  most fun, most realistic, most complete cricket management game out
  there... you're the lead game designer, full approval to revamp whatever
  systems need it"). Plan file:
  `C:\Users\Tushant\.claude\plans\ticklish-finding-dawn.md`. All four
  phases shipped: (1) per-nation league wiring — v4.57.0; (2) manager
  progression (XP/perks) — v4.58.0; (3) narrative layer (rivalries/event
  feed/milestones) — v4.59.0; (4) match-day momentum/key-moments/crowd
  feel — **v4.60.0 (this entry)**. Research behind this initiative:
  `docs/COMPETITIVE_RESEARCH.md`.
- **v4.60.0 — match-day momentum, key moments, crowd/atmosphere feel**:
  `InningsState.momentum`/`key_moments` (purely additive display state
  built from signals `ball_outcome()` already computes — no outcome-weight
  formula touched) via new `Match._update_momentum`, exposed through
  `scorecard()`. `Match.crowd_boost` (default 1.0, no behaviour change
  unless set) multiplies the *existing* home-grounds advantage term in
  `_weights` — the one permitted small engine effect, explicitly scoped to
  extending an existing mechanic. `ipc_server._start_match` sets it to 1.15
  for a real derby fixture (v4.59.0's `rivalries` table) plus a cosmetic
  attendance/label reading, surfaced as `crowd` on `get_match_state`.
  Godot's Match Day screen gained a momentum indicator + crowd label on the
  score bar and a "KEY MOMENTS" card next to the Ball-tracker, built at
  runtime like every other recent addition — **not screenshot-verified
  this session**, flagged honestly rather than claimed; verify before the
  next visual pass touches this screen. A separate, pre-existing
  client-side "Momentum" Stats Hub tab (rolling-window chart, unrelated to
  this new backend value) is unchanged — reconciling the two is a
  follow-up. New `tests/test_match_feel.py` (14 tests). 560 backend tests
  total, all pass; existing calibration/statistical test suites
  (`test_match_engine.py`/`test_realism_tuning.py`/`test_field_positions.py`)
  pass unchanged, confirming no outcome-weight drift. **This completes the
  design-lead revamp (v4.57.0-v4.60.0).**
- **v4.59.0 — narrative layer (rivalries, milestones, a real story feed)**:
  before this, no rivalry/derby concept existed anywhere, and the inbox
  (transient, no `category` column) was the closest thing to a story feed.
  New `narrative_events` table (permanent, queryable, category-tagged) +
  `rivalries` table (one derby pairing per nation, the two highest-cash
  clubs, seeded idempotently from `ensure_per_nation_season`'s existing
  per-country loop). `CompetitionEngine._record_rivalry_result` bumps
  intensity and writes a RIVALRY event on a completed derby fixture, wired
  into both match-completion paths (`simulate_fixture` AI-only,
  `record_played_fixture` live engine). `ipc_server._record_match_honours`
  (already writing centuries/five-fors to `ground_honours`) now also writes
  a MILESTONE event for the same two thresholds. New IPC
  `get_narrative_events`; Godot's Dashboard gained a runtime-built
  "STORYLINES" card. New `tests/test_narrative_layer.py` (8 tests). 546
  backend tests total, all pass (up from 538 — the previous version's one
  flaky test did not recur). **Real perf bug found while packaging this
  release**: several new v4.58.0/v4.59.0 `database.py` functions called
  `create_tables()` (a full schema-migration pass) on every single call
  instead of once at bootstrap — invisible in normal play, but
  `_record_rivalry_result`→`fetch_rivalry_for_team` firing on every League
  match completion hung `test_long_save_stability`'s 365-day AI-only
  simulation past the packaged build's 1800s test timeout, twice. Fixed by
  removing the redundant calls (the established, correct pattern every
  other `database.py` function already follows); the same test now
  completes in ~83s. `build_and_package.py`'s test timeout bumped 900s→1000s
  for headroom. **Any future `database.py` addition should NOT call
  `create_tables(connection)` inside its own `with connect(...)` block** —
  schema setup happens once via `initialise_database`/`load_game` at
  session start; only those two (plus `save_game`, by established
  precedent) should ever call it.
- **v4.58.0 — manager progression (XP, levels, perk tree)**: nothing about
  the manager themselves ever persisted between sessions before this —
  `manager_reputation()` is stateless. New `manager_xp` game_state scalar +
  `manager_perks` table (additive), `src/models/manager_progression.py`
  (6 perks, flat 100-XP/level curve). XP awarded at real hooks: user match
  win (+15)/draw (+5) in `ipc_server._finalise_match`, season trophy (+100)
  in `_award_season_honours`, mid-season objectives all on track (+20),
  team talk/press conference engagement (+2 each). Each perk modifies one
  existing formula at its exact source — team talk morale range
  (`team_talks.py`), press conference confidence swings
  (`press_conference.py`), youth intake (+1 slot, user's club only,
  `rollover_season`), pitch-change delay (`set_pitch_selection`). New IPC
  `get_manager_progress`/`unlock_manager_perk`; Godot's Board screen
  (`board_screen.gd`) gained a runtime-built "MANAGER PROGRESS" card
  alongside the existing objectives/confidence cards. New
  `tests/test_manager_progression.py` (14 tests). 538 backend tests total;
  one confirmed pre-existing flaky test unrelated to this change
  (`test_simulate_balls_advances_the_live_match_and_can_run_it_to_completion`,
  5/5 pass in isolation).
- **v4.57.0 — per-nation domestic leagues actually wired in**: v4.56.0 built
  `ensure_per_nation_season`/the `leagues` table but never called it from
  anywhere (calling it naively alongside the existing global 5-division
  pyramid would double-book every team). `ensure_season` now calls it every
  season for real. Two real bugs found and fixed while wiring it in: (a) a
  nation's own multiple "league"-kind competitions (e.g. England's Test
  County Championship *and* T20 Blast) all started on the same date —
  `_insert_round_robin` gained an optional `start` param so
  `ensure_per_nation_season` staggers them; (b) divisions were re-derived
  every season by blind team-id order, so promotion/relegation had nothing
  real to move — new `teams.nation_division` column (additive) persists
  each team's tier, updated by a new nation-league promotion/relegation
  pass in `rollover_season`, deliberately scoped to each nation's primary
  Test-format league only (a second bug: letting a nation's *other*
  divisioned competition, e.g. T20 Blast, also drive the same shared column
  in the same pass caused its mostly-tied standings to immediately undo the
  Test league's real result — found by this version's own tests). New read
  surfaces (`fetch_nation_leagues`/`fetch_nation_league_standings`/
  `fetch_nation_league_match_count`, IPC `get_nation_leagues`/
  `get_nation_league_standings`), and a "Nations" tab on Godot's League
  Standings screen alongside the existing Division 1/2 tabs. **Deliberately
  additive, not yet a full replacement** of the global division system —
  `teams.division`/`fetch_division_standings`/foreign-player limits/the
  Dashboard's Division-1 crop are all untouched this pass; making nation
  leagues the *sole* domestic structure (as the plan file's Phase 1
  originally scoped) would also require reworking those consumers plus the
  pygame client, which this pass deliberately did not risk in one sitting —
  flagged as a real follow-up, not silently dropped. New
  `tests/test_per_nation_leagues.py` (8 tests). All 524 backend tests pass.
- **v4.56.0 — per-nation domestic league structure (foundation)**: first step
  toward Cricket Captain's full world — each of the ten league-playing nations
  now has its own defined domestic structure. New registry
  `src/models/nations_config.py` (`NATION_COMPETITIONS` — County Championship,
  Sheffield Shield, Ranji Trophy, Quaid-e-Azam, CSA 4-Day, Plunket Shield,
  National Super League, National Cricket League, WI Championship, Logan Cup +
  their ODI/T20 counterparts; `FRANCHISE_LEAGUES` records IPL/BBL/PSL/CPL/
  BPL/SA20/LPL for the shared-squad follow-up). New additive `leagues` table
  (existing saves keep loading — purely `CREATE TABLE IF NOT EXISTS`).
  `CompetitionEngine.ensure_per_nation_season(season)` generates each nation's
  competitions + double round-robins from its own teams (grouped by
  `country_id`); names stored as "Nation Name" (e.g. "England County
  Championship") so they never collide with the existing global leagues that
  reuse the same bare names. **Deliberately NOT yet wired into
  `ensure_season`/`rollover_season`**: the additive model would double-schedule
  teams (fixture clashes); the planned v4.57.x wiring re-points the engine at
  per-nation competitions + adds 50-over knockout cups + franchise shared-squad
  drafting + per-nation promotion/relegation, then the League Standings/
  Calendar UI becomes nation-aware. **Test-suite reality check**: the suite is
  508 tests and takes **~11 minutes** (AGENTS.md's "~6s" is badly stale) — run
  it via the background-donefile method, not in-foreground (a 90s foreground
  call is killed by the shell). plan:
  `C:\Users\Tushant\.claude\plans\per-nation-domestic-leagues.md`.
- **12-concept-screen recreation, v4.49.0-v4.54.0, plus v4.55.0 matchday
  card parity**: the user supplied 12 Cricket Captain reference screenshots
  to recreate in the Godot client. Plan at
  `C:\Users\Tushant\.claude\plans\ethereal-waddling-blum.md`. v4.49-v4.53
  added the right data/columns; v4.54.0 fixed the confirmed structural
  deltas (Match Day columns, League Standings, World Cup groups); **v4.55.0
  closes the batter/bowler card internals**: each not-out batter is now a
  fully independent bordered card with name+figures header, a "Format
  Batting Avg/SR" subtitle (real career figures via ipc_server's new
  `_career_figures()`, format-context preferred, combined fallback), their
  mini wagon wheel, a pitch-with-batter-silhouette icon, and the reference's
  VERTICAL aggression bar (`AggroSlider` HSlider→VSlider, mechanic
  unchanged). Bowler card gained a "Format Bowling Avg" line. Pure runtime
  node surgery in `match_screen.gd`'s   `_restructure_batter_cards()`, so all
  @onready paths + the smoke test's aggro-slider exercise keep working.
  Cards sized compactly (VSliders 60px, tight paddings) so the taller
  right column still fits the 720p viewport without overflow. Dev save
  was found in a polluted state (empty starting XI -> Selection action
  errors + screenshot-test hang); it has been reset to a fresh career
  (old one backed up to
  `C:\Users\Tushant\AppData\Local\Temp\opencode\*_20260808_110430.*`).
  New `docs/COMPETITIVE_RESEARCH.md` records the deep-research pass (CC
  feature set, competitor comparison, Steam success factors). 125 IPC
  backend tests pass; Godot smoke test: all match-day checks pass (aggro
  slider, live feed to completion) — **one pre-existing smoke failure
  remains** ("Selection batting-order up/down row button", `Jake Foster ->
  Jake Foster`), confirmed to also fail on the clean v4.54.0 baseline, i.e.
  unrelated to v4.55.0.
- **A real Godot 4.7.1 binary is now available in this dev environment**
  (`C:\Users\Tushant\Downloads\Godot_v4.7.1-stable_win64.exe`, found via
  PowerShell search — was previously assumed unavailable). Future sessions
  should use it directly rather than assuming screenshot verification is
  impossible. **The reliable way to verify a Godot UI change**: rebuild the
  export (`godot --headless --path godot_client --export-release "Windows
  Desktop" godot_client_dist/StumpedGodot.exe`), then run
  `StumpedGodot.exe -- --screenshot-test` (via `Start-Process
  -ArgumentList "--","--screenshot-test"`, wait for the process to exit on
  its own — it finishes in ~7s) and read the PNGs it writes to
  `screenshots/godot_*.png` (repo root, gitignored) directly. **Do NOT**
  try to OS-level screenshot the running window (`CopyFromScreen` +
  `SetForegroundWindow`) — tried first this session and proved unreliable,
  silently grabbing unrelated desktop windows (Dota 2, a YouTube tab)
  instead of the game, because `SetForegroundWindow` from a background
  process is frequently blocked by Windows without any visible error.
- **Godot workflow reminder**: v4.52.0 added a brand-new `class_name`
  script (`bracket_view.gd`'s `BracketView`). Per the existing "Godot
  workflow note" below, run
  `godot --headless --editor --path godot_client --quit` once before
  relying on it — a plain `--headless` run alone does NOT rebuild
  `.godot/global_script_class_cache.cfg`, so `tournament_bracket_screen.gd`/
  `international_screen.gd` referencing `BracketView` will fail to resolve
  until that one-time scan happens. Same applies to any new `class_name`
  script from this whole concept-screen-recreation pass. Two backend
  decisions were confirmed with the user up front (see the plan file):
  switch player records to format-keyed contexts (not just relabel the
  UI), and add real bonus-point scoring (not skip those columns) for the
  League Standings screen.
- **v4.54.0**: structural realignment pass — Match Day's live layout
  swapped columns (scorecard+Ball-tracker LEFT, bowler/batsman tactics
  RIGHT, matching the reference; the old shared "live pitch" broadcast-
  camera column retired), bowler card gained a Stamina+O/M/R/W/Econ row,
  each batter row is now its own bordered sub-card, and match completion
  no longer force-switches to a Summary tab (Next Ball's slot becomes
  CONTINUE instead, staying on whatever the manager was viewing) — all via
  `match_screen.gd`'s new `_restructure_live_layout()`, pure runtime node
  reordering/reparenting, no `.tscn` rewrite. League Standings trimmed to
  the reference's exact `#/TEAM/P/W/L/D/BAT/BWL/PTS` columns (dropped T/
  NRR from display) and gained a real rules caption (`fetch_division_match_count`)
  — also fixed a real "1.0" position-column bug. World Cup groups rebuilt
  around a persistent Fixtures/Groups/Final Stages sub-nav bar, one group
  at a time with a cycle control, real team flags, and an always-0 NR
  column. See CHANGELOG v4.54.0 for full detail. Verified via the app's
  own `--screenshot-test` harness — see the Godot-binary note above.
- **v4.53.0**: Real County Championship-style bonus-point scoring for
  First Class (Test-format) league matches — batting bonus points at
  200/250/300/350 run thresholds, bowling bonus points at 3/5/7/9/10
  wicket thresholds (`competition.py`'s new `_batting_bonus_points`/
  `_bowling_bonus_points`, folded into `_update_table`'s points calc).
  New `league_standings` columns `bat_bonus`/`bowl_bonus`/`drawn`. A
  genuine "drawn" outcome (`match_engine.py`'s new `Match.drawn`, set
  only on a real time-expired Test draw) is now tracked separately from a
  scores-level tie — both previously collapsed into the same "tied"
  counter across every result-recording path
  (`ipc_server.py`/`ui/match_view.py`/`competition.py`'s lightweight AI
  `simulate_fixture`). The AI-only simulator also now gives Test-format
  fixtures a real (simplified, ~35%) chance of drawing — it had zero
  time/session concept before, so a draw was practically impossible
  there. New dedicated Godot **League Standings** screen
  (`league_standings_screen.gd`/`.tscn`, DATA HUB nav group) — full
  P/W/L/D/T/Bat/Bwl/Pts/NRR table, Division 1/2 tab switch, promotion/
  relegation divider line — backed by new
  `database.fetch_division_standings()`/`ipc_server.py`'s
  `get_division_standings`. New tests:
  `test_final_refinement.py::LeagueBonusPointsTests`. All 505 backend
  tests pass. **This completes the 12-concept-screen recreation plan** —
  see the entry above.
- **v4.52.0**: Real Man of the Match (`ipc_server.py`'s new
  `_man_of_the_match()`, a runs/wickets scoring heuristic across the whole
  match — no prior concept of this existed anywhere in the engine) on
  `get_match_state`'s completed payload; Match Day's Summary tab shows the
  final result banner + MOTM and auto-switches to it once on completion.
  New shared `bracket_view.gd`/`BracketView.build()` replacing two
  independent copies of the same knockout-bracket rendering
  (`tournament_bracket_screen.gd`, `international_screen.gd`), plus a new
  gold "CHAMPIONS" banner neither screen had before. Fixed a real bug:
  the World Cup group table's W/L/T columns always read 0 because
  `database.py`'s `_international_standings_rows()` never computed them
  (only points/NRR) — now tracked properly; also replaced the qualification
  zone's per-row top/bottom borders with a single gold divider line
  matching the reference. New tests in `test_ipc_server.py` (MOTM) and
  `test_international_tournaments.py` (won/lost/tied). All 501+ backend
  tests pass. **Godot workflow note**: this version added a new
  `class_name` script (`BracketView`) — see the reminder above, an editor
  scan is needed once before it resolves.
- **v4.51.0**: Match Day polish — a real per-batter mini wagon wheel next
  to each not-out batter's name in the Batsman Card (`match_stats_canvas.gd`
  gained a `compact` mode so its existing `_draw_shot_map` can be reused at
  ~52px instead of duplicating the drawing code, `match_screen.gd`'s new
  `_striker_wagon`/`_non_striker_wagon`/`_update_mini_wagon`), and a new
  Ball-tracker panel (`BallTrackerCard` in `match_screen.tscn`, left
  column) showing the last 6 legal deliveries as coloured-dot rows
  ("AW: No run.") — `_initials`/`_ball_description`/`_update_ball_tracker`.
  No backend changes; all 499 Python tests still pass (unaffected).
- **v4.50.0**: Squad and Selection screens gain a real "CAREER STATS" tab —
  combined batting+bowling record per player (M/Inns/Runs/Bat avg/SR%/
  Overs/Wkts/Bowl avg/Econ), summed across every format context a player's
  played (`src/models/player_records.py`'s new `combined_record()`,
  `ipc_server.py`'s new `_with_career_stats()`, wired into both
  `get_squad`/`get_selection`). Selection's FIT column is now a real
  5-star condition rating (`table_screen.gd`'s new `"stars"` column flag/
  `_make_stars()`, a generic addition any screen can reuse) instead of a
  bar meter. New test:
  `test_final_refinement.py::RecordsAndTrainingTests::test_combined_record_sums_every_format_context`.
  All 499 backend tests pass.
- **v4.49.0**: player records switched from competition-type contexts
  (League/Cup/Friendly/International) to match-format contexts (First
  Class/One Day/20 Over/10 Over/The Hundred, and the matching
  international tier) — `src/models/player_records.py`'s new
  `format_context()`, used by every `record_player_performance` call site.
  Old rows are untouched (no migration/delete); only new performances
  write under the new keys. Added real per-match fielding-chance tracking
  (`Match.chance_log` gained `catchable`/`lbw_appeals`/`played_and_missed`
  alongside the pre-existing `dropped`/`missed_stumping`/`missed_runout`),
  persisted via new `database.record_player_chances()` and a new
  `get_player_match_events` IPC method — this replaces a real placeholder:
  pygame's `ui/player_modals.py` Chances panel was fabricating these four
  numbers with `rng.randint`, never wired to real engine data. Godot's
  player profile modal: Records tab is now a real per-format Batting/
  Bowling grid (`player_profile_modal.gd`'s `_build_career_stats`/
  `_career_stat_grid`, was one flattened text line per context); Match
  Stats tab now shows a real wagon wheel, runs-progression line, match
  figures, and the new Chances panel from the player's most recently
  completed match (`_build_match_snapshot` and helpers), reusing
  `match_screen.gd`'s `MatchStatsCanvas` drawing code instead of a static
  "no active innings" placeholder. New Python tests in
  `tests/test_final_refinement.py`'s `RecordsAndTrainingTests`
  (`test_format_context_maps_domestic_and_international_labels`,
  `test_player_chances_round_trip_through_database`,
  `test_match_chance_log_only_uses_known_categories`); all 123 tests in
  `test_management_systems`/`test_final_refinement` pass.
- **v4.48.0**: upgraded the match ground renderer with crisp vector
  cricketer silhouettes, bat, limbs, head, shadow, and role-colour accents.
- **v4.47.0**: applied the canonical warm-dark surface, row, text, and accent
  palette directly to every Godot scene so no screen falls back to the old
  cream prototype background or brown text overrides.
- **v4.46.0**: completed the shared Godot concept shell pass: dark control
  styling for sliders/tabs/tables, richer manager header context, and a clean
  Windows export from the canonical client.
- **v4.45.0**: began the full concept-faithful Godot visual pass. The shared
  application theme is now the warm dark broadcast palette across every
  screen, replacing the inconsistent cream prototype styling. The Godot
  export was rebuilt after correcting the player-profile script parse error.
- **v4.44.0**: rebuilt the canonical Godot 4.7.1 Windows export and
  simplified release output to one executable: `godot_client_dist/StumpedGodot.exe`.
  Historical Python/PyInstaller executables and archives were removed from
  the workspace release surface; Python remains source/backend code only.
- **v4.43.0**: refined the Godot domestic cup bracket with stronger round
  hierarchy and explicit completed/upcoming tie status markers.
- **v4.42.0**: fixed the Godot player-profile strengths/weaknesses panel,
  preventing tab-switch duplication and removing an invalid local-variable
  reference in the Overview renderer.
- **v4.41.0**: restyled the Godot Data Hub as the Club Hub with consistent
  cards, accent headings, and tier-coloured squad attribute summaries.
- **v4.40.0**: improved Godot career club selection with active/hover card
  styling and a clearer league/cup briefing before a manager confirms their
  club.
- **v4.39.0**: strengthened the canonical Godot club hub with season/date
  context, fixture venue, NRR standings, and promotion/relegation colour cues.
- **v4.38.0**: upgraded the canonical Godot World Cup/international group
  presentation with card-framed standings, full P/W/L/T/PTS/NRR columns,
  alternating rows, and clear qualification/elimination zone markers.
- **v4.37.0**: upgraded the canonical Godot Selection screen with a pre-match
  team-sheet brief (XI/bowler coverage, captain, wicketkeeper, readiness
  warnings) and form/fitness/morale meters. Existing row actions and selection
  locking remain unchanged.
- **v4.36.0**: upgraded the canonical Godot player profile modal with
  Overview, Records, Form, Match Stats, and Personal tabs. Career records are
  aggregated from existing IPC data; live Match Day values remain owned by the
  match screen and are labelled honestly when no innings is active.
- **v4.35.0**: Match Day now uses a three-column broadcast layout inspired by
  the supplied bowler and batter concepts. The centre column keeps a live,
  read-only pitch/shot-map camera visible alongside dynamic perspective
  guidance and a last-delivery readout; existing scorecards and manager
  controls remain wired to the same engine state.
- **Godot-only workflow (2026-08-06):** added `docs/GODOT_SHIPPING.md` and
  `docs/VISUAL_TARGETS.md`. Godot is the single presentation/client source of
  truth for Steam; Python remains the rules/persistence backend. Future UI
  work should replace canonical Godot scenes, not create parallel pygame
  screens.
- **v4.34.0**: Alpha validation pass. Godot smoke test completes all 34
  screens/flows; Python release suite passes 495 tests. Added a regression
  guard for hidden fractional training progress and corrected stale format/
  Match Day documentation. Headless screenshot testing remains unsupported by
  Godot's dummy renderer; use the normal windowed renderer for pixel review.
- **v4.33.0**: Match Day SKIP cut from ~15 overs to 1 over per press
  (6 legal deliveries) in both clients after user feedback that 15 was
  far too much — button relabelled "SKIP OVER", same cadence as OVER so
  every over is seen before the next decision point.
  (`match_screen.gd::_skip_count`, `match_screen.tscn`,
  `ui/match_view.py::_skip`.)
- **v4.32.0**: Match Day + Training screen visual polish (a design-led pass,
  no roadmap item). Match Day's pre-match hub now reads like a scoreboard
  page: broadcast-style green fixture banner, a filled-green START MATCH
  primary button, card-styled OPPOSITION REPORT, colour-coded pitch status
  (green settled / gold pending change), and the PLAYING XI rendered as a
  real team sheet — column header, alternating card rows, gold edge + gold
  name for captain/keeper, role-coloured roles, OVR tinted by attribute
  tier. The always-on live strip gained STRIKER / NON-STRIKER / BOWLER
  captions, a gold-accented card frame and a blue bowler name. Training:
  squad rows colour ROLE/OVR/POT by value with clipped fixed-width columns
  and a gold-edged highlight for the edited row; the detail card shows a
  role pill plus colour-coded OVR/POT chips (meta line repurposed for the
  last-trained date), the programme/intensity/days controls are gold-edged
  mini-dropdown cards, bulk/simulate actions are filled-accent primary
  buttons, and growth bars reuse the shared `make_bar_meter` under a
  "RECENT PROGRESS" header. All styling via AppTheme tokens (no
  hardcoded colours). 495 tests pass; Godot smoke test 34/34 screens OK;
  dev screenshots regenerated in `screenshots/` (godot_training.png,
  godot_match.png, godot_match_live.png).
- **v4.31.0**: Financial forecasting (roadmap: `finance_forecasting`).
  The Finances screen gains a "12-month projection" card: per-month
  income/expenses/net with a running cash balance and a risk warning for
  any month where the projected balance falls below the board's
  minimum-cash objective. The model only projects what the ledger actually
  posts (weekly player wages, monthly sponsorship), derives estimated
  matchday income from home fixtures already on the calendar (same gate
  formula as the pygame commercial controls), and assumes sponsorship
  renewal at the club's commercial level after the current deal ends.
  Transfers/prize money/youth recruitment/facility upgrades are excluded
  and disclosed in `assumptions`. New `database.forecast_finances()`
  (anchored by an explicit `current_date` param for deterministic tests),
  IPC method `get_financial_forecast`, rendered in `finances_screen.gd`
  (new `ForecastCard` in `finances_screen.tscn`). 495 tests pass; Godot
  smoke test 34/34 screens OK.
- **v4.30.0**: final item from the v4.28.0 feedback round — Press
  Conference relocation. Moved from the CAREER nav group to MATCH DAY.
  Was a flat once-a-week timer with no relationship to matches at all;
  now a post-match presser opens for the fixture just played (question
  flavoured by won/lost/tied, taking priority since there's a real result
  to discuss) and a pre-match presser opens for the next fixture — each a
  once-per-fixture gate (`ipc_server._press_conference_window`, new
  `database.fetch_last_result()`), not a calendar timer. Answers now also
  depend on the match result, not just the tone: a post-match answer's
  confidence effect gets a small win bonus / loss penalty on top of the
  tone's fixed delta (`src/models/press_conference.py`). All items from
  the original v4.28.0 feedback round are now shipped.
- **v4.29.0**: continuation of the v4.28.0 feedback round — the 3 items
  carried forward as "not yet started" are now done (Press Conference
  relocation is the one remaining item). Finances screen redesigned:
  4 summary tiles (Total Income/Expenses/Net/Cash), a "this month"
  income/expenses/net line, and a real two-column Income/Expenses split
  with per-transaction cards — new `database.summarise_finances()`,
  bespoke `finances_screen.gd`/`.tscn` (was a flat single-column
  TableScreen). Squad selection now locks Football-Manager-style once a
  match is live (XI/captain/keeper/batting-order/tactics all rejected
  server-side and disabled client-side until the match finalises) —
  implemented generically via a `locked` response flag in
  `table_screen.gd`, not a Selection-only special case, so any future
  screen gets the same gating for free. Transfer Market and Staff Market
  gained real filter bars (role/age-range/min-overall for Transfers,
  department/min-overall for Staff Market) — `table_screen.gd`'s generic
  table component now supports an optional filter bar
  (`_build_filter_bar`), so any screen using it gets real filtering
  without a bespoke rebuild. Remaining: moving Press Conference under
  Match Day with visible tone effects (task #160) is not yet started.
  See CHANGELOG v4.29.0.
- **v4.28.0**: large feedback batch. Fixed the real Load Game/delete-save
  slowness (`saves.list_saves()` was calling `database.load_game()` per
  save, which unconditionally re-runs `initialise_database()`'s full
  legacy-backfill table scans — ~140x speedup with a lightweight targeted
  peek in `saves.py`, `_peek_save`); Load Game now sorts by most recently
  played and shows real saved timestamps. Removed Tournament mode (its
  custom-tournament flow never assigned a real managed team — dumped the
  user onto a default dashboard); New Game Setup now only offers Career
  and World Cup. World Cup mode no longer offers Training/Youth Academy
  (`ipc_server._is_world_cup_mode` gates both, FM-style — an
  already-assembled national squad for one tournament, no development).
  Fixed three real layout bugs: Help screen's oversized BACK TO GAME
  button (leftover full-width anchor preset), Portal's four summary
  tiles overlapping (missing `anchor_right`), and the player profile
  modal's large dead gap (`AttributePolygon` had no script attached in
  the scene, so it rendered nothing while reserving full height). League
  Standings on the Dashboard is now a real P/W/L/Pts table. Facilities:
  UPGRADE is only offered when actually legal (was a raw backend error
  on a second click), every row shows its real cost/ETA, and pitch
  selection is now a dropdown instead of five button-rows (new
  `facilities_screen.gd`/`.tscn`, nesting the generic upgrade table).
  "Traits" no longer shows a meaningless stat-meter "100" — a plain
  header with an explanatory tooltip + new Help glossary entry. Calendar
  promoted to a top-level nav item. Remaining feedback from this round
  (squad-selection lockdown, a Finances screen redesign, Staff/Transfer
  Market filters, moving Press Conference under Match Day with visible
  tone effects) is carried forward, not yet started. See CHANGELOG v4.28.0.
- **v4.27.0**: fixed a real game-breaking bug — after a match finished,
  revisiting Match Day for the next fixture got permanently stuck showing
  the OLD completed match (every control disabled, no way to play or
  advance) because `get_match_state` never stopped reporting a finalised
  match as still in progress; now falls back to the pre-match hub
  correctly (see `ipc_server._get_match_state`). Commentary overs are now
  clickable (a "JUMP TO OVER" chip strip scrolls to any over's first
  ball). PITCH status box on the pre-match hub now matches OPPOSITION
  REPORT's styling instead of looking like unstyled leftover text. Added
  a real Calendar screen (MATCH DAY nav group) — every fixture plus
  weekly training days, reusing existing `matches`/`training_assignments`
  data — after being repeatedly requested across several feedback rounds.
  See CHANGELOG v4.27.0.
- **v4.26.0**: concrete Match Day feedback round. Both not-out batters
  now shown with real per-batter aggression (LINKED toggle keeps them
  equal, mirroring a partnership; unlink for independent control) —
  backend tracks `batting_aggression_by_id` per match in `ipc_server.py`.
  Pitch selection moved from an instant pre-match cycle button to
  Facilities, with a real `PITCH_CHANGE_DELAY_DAYS` (4-day) groundskeeping
  delay (`database.py`'s `set_pitch_selection`/`get_pitch_status`).
  Opposition Report gained a real GAME PLAN section (bowling matchups,
  pitch advice, batting-order advice from real technique_vs_pace/spin
  gaps, cross-referenced against your own bowlers — see
  `database._opposition_recommendations`). Commentary card gained an
  always-visible "THIS OVER" ball-pill strip, claims more of its
  previously-wasted layout space, scrollback is effectively unlimited
  (was capped at 50), and auto-scroll no longer fights a manual scroll-up.
  PREDICT renamed "WIN CHANCE?" with the result now shown directly on the
  button label, not just a hover tooltip. Also fixed a real SQLite bug:
  unquoted `current_date` collides with the `CURRENT_DATE` keyword and
  silently reads today's real wall-clock date instead of the game's
  actual in-game date — quoted in the new pitch-delay code; the same
  latent bug in `evaluate_board_objectives` is tracked as a follow-up.
  See CHANGELOG v4.26.0.
- **v4.25.0**: Data Hub enriched with Recent Form, Next Fixture, and
  Availability (injuries) cards — reuses existing `matches`/`injuries`
  tables, no new schema. Also fixed jagged rendering across player
  portraits, nav icons, the attribute radar chart, and the pitch strip —
  every custom `draw_circle`/`draw_arc`/`draw_line`/`draw_polyline` call
  outside `ground_view.gd`/`match_stats_canvas.gd` (fixed earlier) was
  still defaulting to `antialiased=false`; also enabled project-wide 2D
  MSAA for the polygon fills (portrait jaw/hair/bust) that have no
  per-call AA option at all. See CHANGELOG v4.25.0.
- **v4.24.0**: large real-bug-fix batch. One copy-pasted layout bug
  (negative offsets with no `anchors_preset`, so bottom-anchored content
  rendered above the top of the screen) hit 8 screens' Back
  buttons/footers — `about_screen`, `achievements_screen`,
  `competition_editor_screen`, `emblem_editor_screen`,
  `kit_editor_screen`, `national_team_screen`, `player_comparison_screen`,
  `player_editor_screen`. The player profile modal was effectively
  non-functional (its content was ~1000px tall inside a 600px card,
  pushing the header off-screen above y=0) — restructured with a pinned
  header and a properly bounded scroll region. Transfers/Offers/Player
  Editor froze for seconds (`get_transfer_market` scanned/scored the
  entire ~2500-player pool with no limit; Player Editor built one
  unpaginated row per player) — both now capped/filtered. Cup screen's
  `vertical_scroll_mode` was disabled, making a multi-round bracket
  unreachable below the first screen. About page's changelog rendered as
  overlapping text (`ScrollContainer` had 4 direct children instead of
  1). See CHANGELOG v4.24.0 for full detail — a genuinely large batch,
  found by the user actually clicking through the game.
- **v4.23.0**: real, serious bug fix — `advance_day()` used to move the
  calendar forward unconditionally even when the user's own fixture sat
  unplayed, permanently orphaning it (query only ever checked
  `date=<today>`, never revisited an older unresolved date). Now blocks
  on any already-due unresolved user fixture before touching the date at
  all; `shell.gd` now redirects to Match Day instead of silently ignoring
  the `user_fixture` response field. Also fixed: scorecard column
  misalignment (long dismissal text widened the NAME column past its
  fixed size — `Label.clip_text` was off), and the SKIP button was
  mislabeled "1 OVER" while actually skipping ~15. Fixing the advance_day
  bug's regression test also surfaced and fixed a latent team-identity
  mismatch in `test_ipc_server.py`'s `_context()` helper. See CHANGELOG
  v4.23.0.
- **v4.22.0**: real cricket fielding-legality rules on `set_field_layout`
  (Law 41.5 leg-side limit always; powerplay circle cap, calibrated to
  this app's own preset radii so Neutral/Aggressive/Defensive stay legal
  starting points — see `match_engine.py`'s `_field_legality_error`).
  `_match_state` now reports `user_is_bowling`; Match Day shows only the
  Bowler Card OR the Batsman Card, never both. Top nav chrome now hides
  automatically while a match is live (`shell.gd`'s `set_chrome_visible`)
  and the ScoreBar was shrunk. Pitch strip length bands got distinct
  colour tints. PREDICT has a tooltip explaining it's a real 240-run
  Monte Carlo win-probability simulation. See CHANGELOG v4.22.0.
- **v4.21.0**: Match Day's left column now has real bowling-target
  interactivity — a new `pitch_strip_view.gd` widget (close top-down
  Line×Length grid) replaced the full circular ground there; clicking a
  zone calls `ipc_server.py`'s new `set_delivery_target`, which
  `match_engine.py`'s `_choose_delivery_line_length` honours with a
  control-skill-based execution chance (one-shot, consumed after a single
  delivery). The left column is now a Bowler Card (name/CHANGE/pitch
  strip/vertical BOWL AGGRO gauge) + a compact Batsman Card (name-figures/
  BAT AGGRO gauge), matching the two Cricket Captain reference screenshots
  the user compared against. See CHANGELOG v4.21.0 for full detail.
- **v4.20.0**: Match Day's `LiveMatchBox` was rebuilt from a single
  fixed-pixel-offset stack (three separate overlap bugs across v4.17.0-
  v4.19.0) into a real two-column `VBoxContainer`/`HBoxContainer` layout
  — left column is always the live batsmen/bowler strip + a large
  always-visible pitch/field view (was a tab, now the permanent
  centerpiece, matching the user's explicit "cricket captain look, ball
  by ball overhaul" ask) + tactics/controls; right column is the
  scrollable stats-tab bar + scorecard/chart tabs + commentary.
  `ground_view.gd` gained a real ball-flight tween (`_flight_t`) so
  boundaries/wickets animate the ball travelling to its landing spot
  instead of popping in instantly. `match_screen.gd`'s ~50 onready paths
  and `shell.gd`'s smoke test were updated for the new tree; see
  CHANGELOG v4.20.0 for full detail.
- **Staleness notice**: this file's narrative below stops around the
  v0.99.0 Nav/Portal redesign — over 100 commits (v1.0.0 through v4.6.0)
  shipped since then are **not** described here: a major world expansion
  (36 → 100 teams, realistic 5-division league structure), international
  tours (bilateral series, ICC tournaments, dual club+national management),
  Steam achievements (47 across 5 categories) and cloud-save stubs, a kit
  editor, an emblem editor, a player editor, a competition editor, an
  audio system, ball-tracker/field-position/radar-chart visualizations,
  player comparison mode, form history, and more. **`CHANGELOG.md` has
  full per-version detail for all of it** — read that, not this file's
  narrative, for anything after v0.99.0. This file's header stats
  (version, test count, known bugs, validation commands) are kept current
  as of the date above; only the prose walkthrough below is stale.
- **Dev-save gotcha**: the unpackaged Godot smoke test (run from source,
  not the built .exe) reads/writes `cricket_manager/data/cricket_manager.db`
  directly — `launcher.py`'s `get_launch_paths()` sets `base == resource_root`
  when not frozen. `%LOCALAPPDATA%\Stumped\data\cricket_manager.db` is
  only used by the *packaged* .exe. Reset the one matching how you're
  running it, or "fresh save" verification silently reuses old state
  (hit this in v0.80.0/v0.81.0 — see CHANGELOG v0.81.0's Fixed entry).
  **v0.90.0 update**: multi-save data lives at `cricket_manager/saves/`
  (writable_root/saves, i.e. sibling to `cricket_manager/data/`, NOT
  inside it) for an unpackaged run — `%LOCALAPPDATA%\Stumped\saves\` for
  the packaged .exe. Reset `saves/`, `data/active_save.json`, and
  `data/cricket_manager.db`/`data/session.lock` together for a genuinely
  fresh multi-save state (hit the same "wrong path" mistake once this
  session before catching it — see CHANGELOG v0.90.0).
- **Company:** ASTRAIVA (Pty) Ltd (South Africa) — all copyright/credit text
  must say this, never "Stumped! development team".

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T10/T20/ODI/The Hundred/Test), competitions, transfers, training, youth (targeted
  recruitment), facilities, finances, honours, career hub, contract
  negotiation, staff (coaches/medical/scouts, transfer market, retirement),
  live commentary modes, saves.
- **407 unit tests pass** (verified 2026-07-30, Python 3.12 via project
  venv, full suite now takes ~9 minutes after the 100-team world
  expansion — see the packaging gotcha below); 2 pre-existing flaky tests
  (one academy probabilistic, one DRS review-decision probabilistic —
  both pass clean on rerun, different one fails each time depending on
  luck). Match-engine statistical validation realistic (T20 ~6.91 RPO,
  ODI ~4.99, Test ~3.93 — normal run-to-run variance).
- `dist/Stumped.exe` last rebuilt at v4.6.0; rebuild with
  `python build_and_package.py` from `cricket_manager/`.
- **Packaging gotcha (found/fixed v4.6.0)**: `build_and_package.py` had
  two hardcoded timeouts (test suite: 180s, packaged `--diagnostics`:
  60s) left over from before the 100-team world expansion made both
  slower — bumped the test-suite one to 900s (actual: ~540s). The
  `--diagnostics` 60s timeout turned out to be fine on its own (~4s
  against a clean install) — what actually broke it was a **stale
  `%LOCALAPPDATA%\Stumped\data\cricket_manager.db` left over from an
  older schema version** (from earlier ad-hoc `--diagnostics` runs in
  this same dev environment) crashing `_expand_world_to_twenty_four` with
  `UNIQUE constraint failed: teams.name` when `initialise_database` tried
  to reseed a DB that already had some-but-not-all of the expected teams.
  **This is a real, unaddressed robustness gap**: `initialise_database`/
  world-seeding isn't verified idempotent-safe against a DB from an older
  world-size schema — a real user upgrading a packaged install across the
  100-team expansion could hit the same crash. Not fixed here (needs a
  real migration path or a version-gated reseed guard, out of scope for
  this pass) — flagged for whoever picks up world-schema migrations next.
- **Long-save stability verified** (v0.83.0): a 20-season headless
  simulation stays DB-integrity-clean with no orphaned rows; squads no
  longer grow unbounded (`CompetitionEngine.SQUAD_SIZE_CAP = 30` fixed a
  real bug — see CHANGELOG). `tests/test_long_save_stability.py` is the
  permanent regression guard.
- **Godot client** runs on **4.7.1 stable**. 22 in-career screens (added
  Cup bracket, v0.88.0; Press Conference, v0.81.0; Trophy Room + Club
  Records, v0.80.0, replacing the old flat Honours table) plus 7
  pre-career/utility screens
  (Main Menu, New Game Setup, Career Team Selection, World Cup Setup,
  Tournament Setup, Settings, Help — v0.76.0), 30 interactive flows. The
  Godot client can now start a brand-new career end to end (manager
  identity → club selection → Dashboard) — previously impossible, see
  "Godot migration status" below. Full match live ball-by-ball with
  tactics (PREDICT, FIELD, aggression, DRS, CHANGE bowler), Stats Hub
  (wagon wheel, pitch/bowling map, worm, momentum, Manhattan,
  partnerships), pre-match pitch selection and opposition report, board
  objectives/confidence, first-run tutorial, shared fade+slide
  screen-transition Tween (v0.76.0), procedural player portraits
  (v0.77.0, replacing pygame's pixelated 128px-canvas portraits with
  crisp native vector drawing), varied ball-by-ball commentary with real
  line/length mechanics (v0.78.0), a Legends hall-of-fame for retired/
  released players (v0.79.0), a grouped Trophy Room + season-by-season
  Club Records archive (v0.80.0), and pre-match Team Talks (Dashboard
  widget) + weekly Press Conferences — the first manager-driven levers on
  squad morale/board confidence (v0.81.0). No Godot-side change in
  v0.82.0/v0.83.0 (realism tuning and long-save stability are both
  backend-only). **v0.84.0**: a genuinely new warm light theme (replacing
  the old near-black dark theme outright — see "Decisions made"), two
  real layout bugs found and fixed (onboarding tutorial card text was
  fully overlapping itself; the sidebar was overlapping the header and
  ~300px of nav items were silently unreachable with no scrollbar), and
  real per-row hover highlighting on every table screen. **v0.85.0**:
  status chips (Form/Fitness/Morale) added to the player profile modal —
  a real feature-parity gap closed, not just visual polish, since the
  smaller hover card already showed all three but the full modal didn't;
  a shared `AppTheme.make_bar_meter()`/`make_status_chip()` helper
  replacing 2 of 3 independently-duplicated bar-meter implementations;
  gold header underlines on the Dashboard/Portal's three cards; Match Day
  reviewed and needed no changes (already fully `AppTheme`-driven — this
  claim was later corrected in v0.86.0, see below). **v0.86.0**: Match
  Day's scorecard actually restructured into real Batting/Bowling/Summary
  tabs (previously always-both-visible side by side, unlike the Cricket
  Captain reference) plus a bowler stamina bar surfacing `players.fatigue`
  for the first time in a live match. Prompted by the user directly
  asking whether Match Day/setup screens/tournament brackets had actually
  been compared against the reference screenshots — the honest answer at
  the time was no, only the palette had propagated; see the plan file's
  "UI/UX revamp part 3" section. **v0.87.0**: extended
  `_run_screenshot_test()` to actually capture the pre-career setup
  screens for the first time (they weren't in the target list before) —
  most were already well-styled via the Theme cascade, contrary to
  static-source assumptions, but found two real issues: Career Team
  Selection's club rows were plain text with no crest identity (now have
  the same initials-badge pattern as the header), and Division/Squad
  size/Stadium/Training level were displaying raw floats (`"Div 1.0"`,
  `"30500.0 seats"`) instead of going through the project's own
  `JsonFormat.value()` helper. Also: `LineEdit`/`OptionButton` had never
  been styled by `AppTheme.build()` at all — New Game Setup's manager-name
  field was an unstyled grey box next to every other now-styled control.
  **v0.88.0**: a new Domestic Knockout Cup bracket-tree screen — no
  bracket visual existed anywhere before this, Godot or pygame (confirmed
  by grepping every pygame `ui/*.py` file). New backend `get_cup_bracket()`
  groups the season's Cup matches by round; new Godot screen shows
  round columns of match-box cards, auto-scrolling to the most advanced
  round. This closes UI/UX revamp Part 3 — all three gaps the user
  identified (Match Day, setup screens, tournament brackets) now have
  real, screenshot-verified work behind them. Smoke test clean across 3
  consecutive runs against a genuinely fresh save (see the dev-save
  gotcha note above — the prior "1 pre-existing flaky step" claim in
  v0.80.0 was itself a stale-save artifact, corrected in v0.81.0's
  CHANGELOG). See `docs/GRAPHICS_MIGRATION_PLAN.md` for prior
  migration-phase status. **v0.89.0** (first of the "Post-launch UX
  fixes" initiative, see "Next action" below): Settings/Help now always
  chrome-less regardless of entry point (previously showed full in-game
  header/sidebar even from Main Menu pre-career); new sidebar footer
  (Settings/Help/Quit to Main Menu) makes both reachable in-career too,
  which they weren't before at all; Settings' Game Speed/Resolution/
  Currency/Auto-save are now real `OptionButton` dropdowns instead of
  click-to-cycle buttons. **v0.90.0**: a real multi-save-slot system —
  previously "Load Game" just re-entered the single existing database.
  New `saves.py` backend module (saves under `saves/<id>.db`, listing
  metadata always read live so it can't go stale), new `list_saves`/
  `create_save`/`load_save`/`delete_save` IPC methods (switching saves
  mutates the live server context in place, no restart), a real Load
  Game screen (card list, CONTINUE/two-click DELETE), and NEW GAME now
  always starts a genuinely new save instead of overwriting whatever was
  active. A pre-v0.90.0 install's single save auto-migrates to "Save 1"
  so no one's career disappears. 358 tests total (14 new). **v0.91.0**:
  `player_portrait.gd`'s shapes now fill with real per-vertex gradients
  (`draw_polygon()`) instead of flat colour — a directional light model
  replaces the old flat-fill-plus-overlay-ellipses look, plus 2 new
  hairstyles. Flags re-exported at 160x96 full RGBA8 (were 80x48 2-bit
  indexed) via a one-off `godot_client/tools/upscale_flags.gd` dev tool.
  Still fully procedural/stylized (no external art tools, no-photos
  policy stands) — a real quality step, not photorealism. **v0.92.0**:
  Match Day's batsmen/bowler scorecard was tab-gated (hidden on shot map/
  worm/etc. tabs) — now a new always-visible `LiveStripCard` shows
  striker/non-striker/bowler figures across every tab, plus a current/
  required run-rate label on the score bar and bowler maidens (the latter
  needed no backend change, the field was already tracked and unused).
  Small backend addition: `legal_balls`/`balls_per_set`/`overs_limit`
  exposed on `get_match_state` so run rate can be computed accurately
  (format-aware — The Hundred uses 5-ball sets). 359 tests total.
  **v0.93.0**: all 36 Help & Guide articles rewritten from single 25-50
  word paragraphs into structured 2-paragraph entries (also fixed two
  FAQ entries left stale by v0.90.0's save-slot system); search now spans
  every topic at once instead of just the active one, with results
  labelled by their owning topic. This closes the "Post-launch UX fixes"
  initiative (v0.89.0-v0.93.0) — all 5 issues the user reported after the
  UI/UX revamp are now fixed.   **v0.98.0**: FM26-inspired UI overhaul —
  design system foundation (spacing tokens, card helpers, shadow/elevation,
  tab underline indicators), navigation icons (22px, thicker lines, 4 new
  glyph types), shell redesign (PanelContainer backgrounds, 16px content
  padding, section icons inline), Dashboard Portal (stat tiles, gold
  accent crests, improved standings), table screens (gold hover accent,
  rounded rows, better pills), player profile (bookmark star button,
  personality/traits display via `get_personalities` IPC). Backend fixes:
  `get_data_hub` column mismatch, SubNav re-parenting, bookmarks
  autowrap enum. All 24 Godot screens pass, 399 Python tests pass.
  **v0.99.0**: About/Version screen, Settings page overhaul (sectioned
  layout with gold accents, Reset Tutorial and About links), Match Day
  button styling (card-style tactical buttons, smaller control button
  font). Competitive roadmap created (5-phase plan). All 25 Godot screens
  pass, 399 Python tests pass.

## Godot migration status — strategic decision (2026-07-27)

**Godot is now the client that ships on Steam.** pygame's feature depth
is being ported into Godot (not the other way around); pygame stops being
the long-term shipped product once parity is reached. This reverses the
prior "pygame remains the shipped product" framing below one section, which
is now superseded — kept only as history until the old phase-numbering is
fully retired.

Prior migration numbering (superseded): Phase 0 (PoC) done. Phase 1 (IPC,
30+ methods) done. Phase 2 (screen porting): all in-career screens render
real data + interactive flows.

**New roadmap** (see the "best-in-class Steam cricket manager" plan,
`C:\Users\Tushant\.claude\plans\majestic-leaping-comet.md`, for full
detail): a 9-phase plan to make Stumped! best-in-class — deep progression/
history systems, richer match commentary and tactical depth, realistic
retirement + legends archive, team talks/press conferences, realistic-but-
fictional player/league tuning, long-save stability stress testing, and
finally full Steam packaging as the single Godot client.

- **Phase 1 (Godot pre-career startup flow)** — **DONE** (v0.76.0). See
  CHANGELOG for full detail: Main Menu/New Game Setup/Career Team
  Selection/World Cup Setup/Tournament Setup/Settings/Help all ported;
  manager identity now created and surfaced in the persistent header;
  shared screen-transition Tween added.
- **Phase 2 (visual identity)** — **DONE, partially** (v0.77.0). Ported
  the procedural portrait generator to Godot as `player_portrait.gd`
  (wired into hover card/profile modal/Squad+Selection rows). **Still
  open**: folding in FM/Cricket Captain reference screenshots (none have
  been attached in the requesting conversation yet — ask again before
  doing a further visual pass) and a richer visual-hierarchy pass beyond
  portraits.
- **Phase 3 (commentary + tactical depth)** — **DONE** (v0.78.0).
  Commentary expanded from 11 fixed templates to weighted pools (3-6
  variants per outcome) with real shot names derived from line/length;
  FIFTY!/CENTURY! milestones added. Bigger find: `preferred_line`/
  `preferred_length` were dead code (never set anywhere, always the
  class default, only ever affected cosmetic pitch-map dots) — replaced
  with a real per-ball situational choice (`_choose_delivery_line_length()`
  in `match_engine.py`: phase-aware, bowler-control-aware,
  bowling-style-aware) that now feeds real deltas into outcome weights.
  Statistical calibration re-verified stable.
- **Phase 4 (retirement realism + legends)** — **DONE** (v0.79.0). The
  hard `age>40 OR overall<20` delete rule is gone — replaced with a real
  age-curve retirement probability (negligible before 33, ~certain by
  44, hard-forced at 45 to respect the `players.age` CHECK constraint),
  a distinct `released` reason for the quality-floor case, a `legends`
  archive table so nobody just vanishes (full career-record snapshot
  taken before the cascading delete), and a ~15% chance a retiree
  becomes club staff instead of leaving. New Godot Legends screen.
- **Phase 5 (trophy room + historical stats)** — **DONE** (v0.80.0). The
  flat honours list is now also grouped by competition (`get_trophy_room`);
  new `season_records` table captures each club's season-by-season
  leaders (top scorer/wicket-taker, computed by diffing cumulative
  `player_records` against a `game_state` baseline snapshot at rollover,
  see "Decisions made"); `fetch_club_records` derives all-time bests
  (highest score, biggest win, heaviest defeat) live from
  `matches.result_json`. New Godot Trophy Room + Club Records screens.
- **Phase 6 (team talks + press conferences)** — **DONE** (v0.81.0). The
  first manager-driven levers on squad morale/board confidence — both
  only ever moved via passive events before this. Team talks: 3 tones
  (Calm/Assertive/Aggressive), whole-squad morale roll, once per
  matchday. Press conferences: a position-flavoured templated question,
  4 tone responses with fixed confidence/morale deltas, once a week —
  feeds into the *existing* board-confidence history ring rather than a
  new parallel value. New Godot Dashboard team-talk widget + Press
  Conference screen.
- **Phase 7 (realism tuning)** — **DONE** (v0.82.0). Squad quality is no
  longer identical across every club in a division — a club's own
  randomised cash now nudges its target rating (`_team_quality_modifier`,
  ±5 points at each division's cash extremes). Youth-intake potential
  moved from a flat `randint` roll to a bell-curve-plus-tail distribution
  (`_youth_current_and_potential`) mirroring `_target_rating`'s existing
  pattern — genuine wonderkids are rare again. Name pools expanded
  (8-12 → 14-16 per nationality) to cut collision risk in large saves.
  Two dead-code duplicates removed (`realistic_rating()`,
  `countries.json`'s unused name arrays).
- **Phase 8 (long-save stability)** — **DONE** (v0.83.0). First-ever
  multi-season stress test found a real bug: unconditional
  `recruit_youth(count=3)` every rollover, with no squad-size check,
  took a 25-player squad to 59 over 20 seasons. Fixed with
  `CompetitionEngine.SQUAD_SIZE_CAP = 30` (intake now clamped to
  available room); manually verified the squad size genuinely plateaus
  at the cap through 40 seasons, not just grows more slowly. DB
  integrity, `player_records`/`team_id` FK cleanliness,
  `legends`/`season_records` accumulation, and a full year of real
  `advance_day()` calls (not just season jumps) all checked out clean.
  `tests/test_long_save_stability.py` is the permanent regression guard.
- **Phase 9** — not started (Steam packaging: retire pygame as the
  shipped product, final cross-resolution/fullscreen QA, Steam store/
  achievement wiring). See the plan file for the full phase list. Put on
  hold at the user's request (2026-07-28) — needs a real Steam App ID/
  Steamworks SDK access this agent doesn't have, plus a decision on
  actually retiring pygame; revisit when ready.

**UI/UX revamp** (2026-07-28, not one of the original 9 phases — a new
initiative the user requested after reviewing Cricket Captain/Football
Manager reference screenshots and reporting a real overlap bug): see the
plan file's "UI/UX revamp" section for full detail and reasoning.
- **Part 1 (v0.84.0)** — **DONE**: warm light theme (outright replace,
  no toggle), the two layout bugs above, per-row table hover states.
- **Part 2 (v0.85.0)** — **DONE**: player profile modal gained a
  Form/Fitness/Morale status-chip row (closes a real feature gap — the
  hover card already had these, the full modal didn't); a shared
  `AppTheme.make_bar_meter()`/`make_status_chip()` helper factored out of
  2 of the 3 independently-duplicated bar-meter implementations; gold
  header underlines on the Dashboard/Portal's three cards. Match Day
  reviewed and needed no changes — already fully `AppTheme`-driven from
  Part 1.
- **Part 3 (v0.86.0-v0.88.0) — DONE.** The user pushed back on Parts
  1-2's "reviewed, no changes needed" claims, asking directly whether
  Match Day/setup screens/tournament brackets actually matched the
  reference screenshots. Honest answer: no, only the palette had
  propagated to them. Part 3 did the real comparison + work, scoped via
  a second plan-mode pass with two AskUserQuestion decisions (scorecard
  tabs: yes; bracket scope: the main Domestic Cup, not the flagged
  custom-tournament system). v0.86.0: Match Day's Batting/Bowling/Summary
  tabs + bowler stamina bar. v0.87.0: setup screens actually
  screenshotted for the first time, club crest badges + a real
  float-formatting bug fixed on Career Team Selection,
  LineEdit/OptionButton styled for the first time. v0.88.0: a new
  Domestic Knockout Cup bracket-tree screen (see above for all three).
  The whole UI/UX revamp (Parts 1-3) is now shipped; no further UI work
  is queued unless new reference material or feedback comes in.

Hybrid architecture unchanged for now: Python backend
(`database.py`/`match_engine.py`/`competition.py`/`src/models/*`) shared
by both clients; Godot talks to it via JSON-RPC-over-stdio
(`ipc_server.py`).

## Competitive analysis (2026-07-24)

Researched: Cricket Captain 2024/2025, From the Pavilion, Hattrick,
Football Manager, OOTP Baseball, Cricket Management 26, Cricket Director,
Cricket Chairman, Cricket Club Manager, Wicket Cricket Manager.

**Stumped! strengths vs competitors:**
- Deep attribute-driven match engine with DRS, DLS, talents, temperament
- Full staff system (coaches/medical/scouts) — Cricket Captain has none
- Contract negotiation with multi-round AI — Cricket Captain has none
- Scout fog-of-war on transfers — no competitor has this
- Procedurally generated world (no licensing issues)
- Both pygame + Godot clients sharing same backend

**Gaps identified (prioritised):**
1. ~~AI-initiated transfer offers~~ **DONE** (v0.63.0)
2. ~~Opposition reports~~ **DONE** (v0.63.0)
3. ~~Board expectations/club vision~~ **DONE** (v0.64.0)
4. ~~Pitch selection~~ **DONE** (v0.65.0)
5. ~~Player talents visible in commentary~~ **DONE** (pre-existing)
6. ~~Interactive job market~~ **DONE** (v0.66.0)
7. ~~Custom tournament creator~~ **DONE** (v0.67.0)
8. ~~Onboarding tutorial~~ **DONE** (v0.68.0)

## Active backlog (priority order)

User-directed priority (2026-07-27), building one at a time:

1. ~~Persistent player fatigue & rotation~~ **DONE** (v0.70.0)
2. ~~Dynamic player morale~~ **DONE** (v0.71.0)
3. ~~Deeper league/international structure~~ **DONE, scoped** (v0.72.0)
   — a once-a-season 3-match T20I international window, not a full
   separate international career mode (no manager creation, no parallel
   calendar, no user-controlled national squad selection). See "Decisions
   made" below and the v0.72.0 CHANGELOG entry for exactly what shipped
   vs. what a fuller international layer would still need. All three
   user-directed roadmap priorities from the 2026-07-27 stability audit
   are now done.
4. ~~Godot/pygame feature-parity catch-up, part 1 of 3~~ **DONE**
   (v0.73.0) — pitch selection (a real bug: the selected pitch was
   silently discarded and never reached the live match), opposition
   report, and job offers accept/decline (pygame's Career screen never
   showed them despite the inbox message telling players to check
   there).
5. ~~Godot/pygame feature-parity catch-up, part 2 of 3~~ **DONE**
   (v0.74.0) — dedicated Board objectives/confidence screen in both
   clients; found and fixed a real bug along the way
   (`evaluate_board_objectives()` compared against the team's own id
   instead of its actual league position).
6. ~~Godot/pygame feature-parity catch-up, part 3 of 3~~ **DONE**
   (v0.75.0) — a real onboarding tutorial overlay, built from scratch
   in both clients (correcting a prior docs claim that pygame already
   had one — it did not; v0.68.0 only ever shipped the backend). This
   closes the full 3-part catch-up pass. Still deferred: reconciling
   the two parallel "custom tournament" systems — see "Known bugs /
   risks" below.
7. ~~Career startup flow (Godot)~~ **DONE** (v0.76.0) — manager creation,
   game-mode selection, club selection now all work in Godot; see
   "Godot migration status" above for the full best-in-class roadmap
   this kicks off (Phase 1 of 9).
8. **Roadmap planned items** — live auctions, academy expansion,
   financial forecasting, keeper batting roles, daily tournaments.
9. **Real Steam integration** — stubbed; app ID `null` in `config.json`.

## Known bugs / risks

- Audio ducking not verified on real device (dummy driver in dev).
- Godot Stats Hub accumulators reset if you navigate away from Match
  mid-game (only balls from current screen instance captured).
- AI transfer offers run weekly (Sundays); no throttle on offer count
  per day — may flood inbox if many AI clubs have gaps simultaneously.
- Pitch selection only applies when user is home team; away matches
  always use "Green" default (AI opponent pitch selection not implemented).
  (Fixed in v0.73.0: previously the selection wasn't even passed to the
  live match at all — this is the remaining, lesser limitation.)
- Job offers only generated at season end; no mid-season vacancy fills.
  (Now actually visible/actionable in both clients as of v0.73.0.)
- **Two parallel, disconnected "custom tournament" systems exist**:
  `src/views/screens/tournament_setup.py` (a pre-game, standalone
  tournament-only game mode selecting countries, wired to
  `game_controller.confirm_custom_tournament`) and
  `create_custom_tournament`/`list_custom_tournaments`/etc. in
  `database.py`/`ipc_server.py` (an in-career system using real club
  team ids, persisted as `competitions`/`matches` rows, fully exposed
  over IPC — and completely unused by any UI in either client). These
  need a product decision (keep both for different purposes, or merge)
  before more UI work goes into either.
- League structure is still 2 fictional divisions + 1 knockout cup.
  International cricket exists now (v0.72.0) but only as a once-a-season
  3-match T20I window with auto-selected teams — not a full
  international career mode (no manager creation, no parallel calendar,
  no user-controlled national squad selection, no international
  tournament like a World Cup). `docs/UX_ROADMAP.md`'s original
  deprioritisation reasoning (a much larger redesign than a single pass)
  still holds for that fuller version.

## Fixed 2026-07-27 (audit pass — see git history for full detail)

- **`ipc_server.py`'s `build_context()` never called
  `CompetitionEngine.ensure_season()`** — a save that only ever went
  through the Godot client had exactly one hardcoded demo fixture
  (`_seed_phase_25_data`) and then a permanently empty fixture list; no
  Domestic Division 1/2 league or cup was ever generated. This was the
  most significant bug found — the whole league loop was broken for a
  Godot-only game. Fixed by calling `ensure_season()` on every backend
  startup, matching `main.py`'s pygame bootstrap exactly (idempotent, so
  safe to call every time).
- **Two independent, diverging player valuation formulas** —
  `squad_metrics.estimated_value()` and `transfer.transfer_value()` gave
  different numbers (~30-40% apart) for the same player depending on
  which screen you were on. Consolidated: `estimated_value()` now
  delegates to `transfer_value()` at a neutral reputation.
- **Scouting used hardcoded team finances** (`team_cash=8_000_000,
  team_reputation=60`) for every scouted player regardless of which club
  actually owned them — availability/asking-price signals now reflect
  the player's own club's real cash and division.
- **Season-end promotion/relegation/retirement was computed but never
  shown to the user** — `rollover_season()`'s return value was silently
  dropped by every caller. Now posts inbox messages for promotion,
  relegation, and any of the user's own players retiring.
- **League standings had no tiebreaker beyond points** — added `won` as
  a secondary sort key (points → wins → net run rate) everywhere
  standings are read; also added a minimum-teams guard against a
  too-small division corrupting promotion/relegation.
- Godot: `match_screen.gd`'s DRS/CHANGE BOWLER status messages were
  immediately clobbered by `_render_state()` on the very next line — the
  player never actually saw them. Reordered. `recruitment_screen.gd` had
  no `refresh()` method at all, so it silently went stale after Advance
  Day (every other screen refreshes). Added defensive `.get()` in place
  of unguarded `result["team"]` bracket access in two screens.
- Smoke-test coverage added for DRS, AUTO/SPEED, Training's intensity/
  days/bulk-apply buttons, and Recruitment's remaining nav buttons —
  all previously unexercised.

## Decisions made

- **Light theme replaces dark outright** (v0.84.0, user decision via
  AskUserQuestion) — no light/dark toggle. `app_theme.gd` is still the
  single palette source; every named constant kept its old semantic role
  (`BACKGROUND` is still the deepest layer, `GOLD` still the accent/active
  colour) so every screen referencing `AppTheme.<TOKEN>` repainted for
  free — only the 22 `.tscn` files that hand-copied hex values needed a
  manual sweep. New `NEUTRAL` constant added for `attribute_colour()`'s
  mid tier — the old dark theme reused `TEXT_PRIMARY` for this (near-white
  text doubling as a bar-fill tone), which doesn't survive a light/dark
  repaint since text colour and "steady tier" colour are different
  concerns. Modal veils (onboarding, opposition report, player profile,
  main menu) are a warm dark-brown tint at 35-45% opacity now, not black
  at 60-68% — black at that opacity muddies a light theme's underlying UI
  into near-illegibility instead of just receding it.
- **Godot's `_run_screenshot_test()` needs a real window, not
  `--headless`** — headless mode uses the dummy rendering driver, whose
  `get_viewport().get_texture()` returns null, so `save_png()` crashes.
  Run it as `godot --path godot_client -- --screenshot-test` (no
  `--headless`) on a machine with a real display; screenshots land in
  `screenshots/` (repo root, gitignored). This is the tool that found
  both v0.84.0 layout bugs — static `.tscn` analysis alone didn't reveal
  either one.
- Squad-size cap (v0.83.0): `CompetitionEngine.SQUAD_SIZE_CAP = 30`.
  `recruit_youth` intake at rollover is clamped to
  `min(3, cap - current_squad_size)` rather than always recruiting 3 —
  a real club stops signing academy prospects once full. No forced
  release/trim mechanic was added for squads that might already be
  over the cap in an existing pre-v0.83.0 save; the cap only prevents
  *further* growth. Not a concern for shipping since no player saves
  exist yet outside this dev environment.
- Squad-strength variance (v0.82.0) is deliberately tied to a club's own
  already-randomised cash rather than a new standalone reputation field
  — `_team_quality_modifier(cash, division)` linearly maps a team's cash
  within its division's seed-time range to a ±5 target-rating offset.
  This only applies at world-seed time (`generate_player`'s optional
  `team_modifier` parameter, default 0.0 for any other caller); it does
  not retroactively re-roll existing saves.
- Youth potential (v0.82.0) uses the same tail-probability shape as
  `_target_rating` (rare 88-97, uncommon 78-87, otherwise a bell curve)
  instead of a structurally different flat `randint` — see
  `_youth_current_and_potential` in `database.py`. Potential is always
  clamped to be `>= current`.
- Team talks (v0.81.0) are gated once per matchday
  (`game_state["team_talk_last_date_<team_id>"]`), press conferences
  once a week (date-diff ≥7 days against
  `game_state["press_conference_last_date_<team_id>"]`) —
  `src/models/team_talks.py`/`src/models/press_conference.py` are pure
  functions (tone → morale/confidence delta), gating and persistence
  live in `ipc_server.py`. Press conference responses write into the
  *existing* `record_board_confidence` history ring (base score = most
  recent history entry, or 55 if none) rather than adding a second,
  parallel confidence value — a press answer shows up in the Board
  screen's confidence history right alongside season-end reviews.
- **Godot is the client that ships on Steam** (2026-07-27); pygame's
  feature depth is being ported into Godot, not developed further as the
  long-term shipped product.
- **Players stay realistic-but-fictional** (2026-07-27) — procedural
  generation only, no real player names/data/likenesses, to avoid
  licensing/legal exposure for a commercial Steam release. Realism work
  (Phase 7 of the roadmap) means tuning generation harder — name pools,
  squad-strength distributions, youth-intake realism — not switching to
  real-world data.
- Proprietary license; no licensed real-world content (all generated).
- SQLite single-file saves with in-place migrations; GBP-base accounting.
- pygame-ce + pygame-gui only; PyInstaller for distribution.
- `dist/`, `build/`, save DBs, and logs are gitignored.
- Game owned by ASTRAIVA (Pty) Ltd — see branding note above.
- Text rendering: native-size SDL_ttf, not supersampled.
- Fullscreen: exact-integer SDL_SCALED only; never a fractional stretch.
- Scouting fog-of-war scoped to Transfer Market display only.
- AI transfer offers use deterministic seed (date-based) for reproducibility.
- Board objectives stored in game_state keyed by team ID; 20-entry
  confidence history ring buffer; mid-season review fires on July 15.
- Pitch selection stored in game_state keyed by team ID; defaults to
  "Green"; only home team can choose; away uses engine default.
- Job offers generated at season end in `_award_season_honours()` based on
  `manager_reputation()` score; clubs must have avg overall ≥ 55, be in
  user's division or lower, and be below 6th place. Sacking triggers after
  3 consecutive "Ultimatum" board-confidence reviews.
- Custom tournaments create one League competition per group (so
  CompetitionEngine auto-updates standings); knockout is a single Cup
  competition. T10 format added to matches CHECK constraint via table
  rebuild migration.
- Retirement (v0.79.0): age-curve probability
  (`CompetitionEngine._retirement_probability`, 0% below 33, ~certain by
  44, hard 45 cap) replaces the old blunt `age>40` cutoff; `overall<20`
  is a separate `released` reason, not retirement. Every departing
  player is archived into `legends` (`record_legend`/`fetch_legends` in
  `database.py`) — snapshot taken before the `players` row delete since
  `player_records` cascades on it — with no function that ever
  reinserts a legend into `players`. ~15% of retirees (not releases)
  convert to a staff role at their last club via
  `CompetitionEngine._convert_retiree_to_staff`, role picked from
  playing role, quality scaled from final `overall`.
- Season stats (v0.80.0): `CompetitionEngine._record_season_stats` runs
  inside `_award_season_honours`, called before retirees are deleted so
  `player_records` is still intact for the whole departing squad too.
  It diffs each current-squad player's cumulative runs/wickets (summed
  across all `player_records` contexts) against a baseline snapshot
  keyed `season_baseline_<team_id>` in `game_state`, takes the max as
  that season's top scorer/wicket-taker, writes one row to the new
  `season_records` table via `record_season_stats`, then overwrites the
  baseline with the new cumulative totals for next season's diff. Scoped
  to the user's team only (mirrors the Legends/Trophy Room precedent of
  not tracking this for every AI club). Known edge case: a player
  transferred in mid-season has no prior baseline entry, so their whole
  career-to-date total (not just this season's contribution) counts —
  acceptable for v1, not worth a bigger redesign yet.
- Club records (v0.80.0) are deliberately *not* a stored table —
  `fetch_club_records` scans `matches.result_json` for a team live on
  each request. Club match history is small enough that this is cheap,
  and it avoids a second write path to keep in sync with match results.
- Delivery line/length (v0.78.0) is chosen fresh every ball by
  `Match._choose_delivery_line_length()`, NOT read from
  `PlayerTactics.preferred_line`/`preferred_length` (those fields still
  exist on the dataclass/default-parsing path but are effectively legacy
  now — nothing sets them, and the per-ball chooser is what actually
  drives both the pitch-map coordinates and outcome weights). If a future
  phase adds manager-controlled bowling line/length, treat the chooser's
  distribution as the AI baseline to bias, not something to remove.
- **Godot workflow note**: a new script declaring `class_name X` is not
  resolvable by other scripts typing an `@onready var` against it until
  the global script-class cache (`.godot/global_script_class_cache.cfg`)
  is rebuilt — a plain `--headless` run does NOT do this, only an editor
  scan does. After adding a new `class_name` script, run
  `godot --headless --editor --path godot_client --quit` once (harmless,
  ~1s) before relying on it elsewhere, or expect a "Could not find type"
  parse error (hit once building `player_portrait.gd`, v0.77.0).
- New-game/startup IPC methods (v0.76.0) reuse one shared `GameController`
  instance stashed on `ctx["game_controller"]` by `build_context()` (mirrors
  `main.py`'s own `self.game_controller = GameController(...)` pattern) —
  new IPC handlers call the controller's existing validated methods
  directly rather than reimplementing validation logic, and read the
  navigation destination it records via a `navigate` callback that just
  writes to `ctx["_pending_navigation"]` (no real screen to switch,
  headless). `src/controllers/__init__.py`'s dead `audio_controller`
  re-export was removed as part of this — it was the only thing that made
  importing `GameController` transitively import pygame, which corrupted
  `ipc_server.py`'s stdout JSON-RPC stream (see CHANGELOG v0.76.0).
- Onboarding tutorial stored in game_state as `"onboarding_state"` with
  `completed_steps`, `current_step`, `dismissed` fields. 7 steps covering
  Dashboard, Squad, Selection, Training, Transfers, Match Day, Finances.
  UI (v0.75.0): a dismissible card shown only when the current step's
  target screen matches the screen the user is actually on; NEXT calls
  `advance_onboarding`/`advance_onboarding_step`, SKIP TUTORIAL calls
  `dismiss_onboarding` and skips all remaining steps at once (no
  per-step re-prompt). State re-synced on every navigation, not
  every frame.
- The Hundred uses 100 legal deliveries in 20 five-ball sets; each bowler is
  capped at 20 balls. Scorecards, ball trackers and rates display sets rather
  than mislabelling them as six-ball overs.
- Fatigue (`players.fatigue`, 0-100) recovers 12 points/rest day via
  `recover_daily_fatigue()`; persisted from `Match.performance_updates()`
  as an absolute post-match reading, not a delta. Morale
  (`mental.morale`, nested JSON) moves on match results (whole-squad,
  cup fixtures 1.6x stakes), being dropped from the XI since last time
  (tracked via game-state key `last_match_xi`), signed contract
  renewals, and promotion/relegation (whole-squad, all clubs) — see
  `src/models/morale.py` for the event-delta formulas, shared by both
  clients identically.
- International cricket: a fixed July-1-each-season 3-match T20I window
  (`CompetitionEngine._run_international_window()`), auto-selecting the
  best 11 eligible players per nation from every club in the world
  (`select_national_xi()`). Uses stable negative synthetic team ids
  (`src/models/international.py`'s `NATIONAL_TEAM_IDS`) since these
  aren't real club rows. No `matches` table rows are created for these
  fixtures (run and resolved synchronously within one `advance_day()`
  call) — only a guard `competitions` row, `player_records` entries
  (context `"International"`), morale, and an inbox message persist.

## Validation commands (run from `cricket_manager/`)

```powershell
python -m unittest discover -s tests -v          # expect 442 pass, ~400-540s (100-team world)
python validate_match_engine.py                   # statistical validation
python main.py                                    # manual run
python build_and_package.py                       # packaged build (~9-10 min total)
godot --headless --path godot_client -- --smoke-test  # Godot smoke test
```

## Nav & Portal redesign (2026-07-28)

Full FM26-inspired Tile & Card UI upgrade — **all 3 structural items done:**

1. **Top nav bar replaces sidebar** (v0.97.0+): `shell.gd`/`shell.tscn` rewritten —
   sidebar removed, horizontal NavBar (section buttons) + SubNav (sub-screen tabs)
   added. Settings/Help/Quit moved to right side of NavBar. All 22 in-career
   screens navigate correctly via two-tier (section → sub-screen) pattern.

2. **Bookmarks + Data Hub screens created**: `bookmarks_screen.gd/.tscn` (list +
   remove), `data_hub_screen.gd/.tscn` (2x2 grid). Backend methods registered in
   `database.py` + `ipc_server.py`. NAV_GROUPS extended with BOOKMARKS / DATA HUB.
   `nav_icon.gd` gained bookmarks (star) + data_hub (bar chart) glyphs.

3. **Dashboard Portal tile home redesigned**: 4 stat tiles (Squad, League,
   Finances, Confidence) in an HBoxContainer row at top, fed by
   `get_data_hub` IPC call. Content area restructured: left column (NEXT
   FIXTURE card + Team Talk widget), right column (LEAGUE STANDINGS + INBOX).
   Title shows `"PORTAL — Team Name | Date"`.

Sub-nav button styling unified via `AppTheme.style_nav_button()` (active: gold
bg, inactive: transparent) — both section buttons and sub-screen tab buttons
use the same consistent theme path.

## Next action

**v4.6.0 + v4.7.0 (keeper batting roles, backend + UI) are shipped.**
`database.py`'s `classify_keeper_batting_role`, the best-XI fallback no
longer batting the keeper at the top of the order, a new
`get_keeper_batting_role` IPC method, and — as of v4.7.0 — a "Keeper
role: <label>" line on the player profile modal for wicketkeepers.

**v4.7.0 also found and fixed a real, user-facing crash**: `shell.gd`'s
`_rebuild_subnav()` (top-nav-bar rewrite, v0.97.0+) was calling
`queue_free()` on the outgoing section's sub-nav buttons even though
`_nav_buttons` (built once, meant to be reused forever) still held
references to them — revisiting any section you'd already navigated away
from once crashed `show_screen()`'s `style_tab_button()` call with
"previously freed". This affected completely ordinary navigation (Squad
→ Finances → back to Squad) and had apparently been live since the
nav-bar rewrite — nobody had run `--screenshot-test` (which is what
caught it) since then. Fixed with `remove_child()` instead of
`queue_free()`. **v4.8.0** adds a permanent regression guard for this
exact bug (`_exercise_section_revisit` in `shell.gd`) — manually verified
both directions (fails on the bug reintroduced, passes with the fix), so
this class of bug can't silently ship again the same way.

Also found and fixed at v4.6.0 (not part of keeper batting, found while
verifying that release):
- `test_higher_grounds_level_boosts_home_batting`/
  `..._home_bowling` were failing **deterministically**, not flaky — but
  the underlying grounds-level mechanic itself is correct (verified
  directly via `Match._weights()`'s raw output). The tests compared noisy
  full-match run/wicket totals over only 20 simulated seeds against a
  true effect size of only a few runs/wickets per match — far too little
  signal relative to T20's natural ~20-30 run per-innings variance,
  especially since two seeded simulations' RNG streams decorrelate
  completely after their first differing ball. Rewrote both tests to
  assert on `_weights()`'s deterministic output directly instead —
  passes reliably now, and actually tests the mechanism more precisely.
- `build_and_package.py`'s two stale timeouts (see the packaging gotcha
  above) and the version-file drift (`launcher.py`'s
  `DEFAULT_CONFIG["version"]`/`version_info.txt` stuck at `0.93.0` since
  that version, ~40 releases out of sync with `config.json`).

**v4.9.0 fixed the packaging/world-seeding robustness gap flagged above.**
`_expand_world_to_twenty_four()` only guarded against team-ID collisions
when migrating an older save's roster, not NAME collisions — a save
predating one of the several "expand the world" roster reshuffles could
crash `initialise_database` on every single launch. Fixed (skip the
colliding definition instead of crashing, plus an `INSERT OR IGNORE`
safety net) and covered by 3 new tests in `tests/test_world_migration.py`,
verified against the pre-fix code to actually catch the crash.

**In progress: real international tournament structure** (user request,
2026-07-30) — "replicate the real world tournament types and breakdown
and progression": domestic leagues (already real), ODI/T20 World Cups,
bilateral tours. Full plan:
`C:\Users\Tushant\.claude\plans\majestic-leaping-comet.md` (top section).
- **v4.10.0 (done, Part 1)**: the ODI World Cup, T20 World Cup, and
  Champions Trophy are now real tournaments — full group stage (all real
  nations, not 2), real dated fixtures simulated day by day, automatic
  knockout bracket generation, a champion-crowned inbox message. Also
  fixed a real pre-existing bug in `_generate_round_robin` (odd team
  counts produced an incomplete/unfair schedule) and dropped
  `matches.home_team`/`away_team`'s FK to `teams(id)` via schema
  migration, since international fixtures use negative synthetic
  national ids that were never meant to be real `teams` rows.
- **v4.11.0 (done, Part 2)**: bilateral tours (the Ashes, etc.) also get
  real persisted dated fixtures (one `matches` row per game in the
  series, gap days per format), instead of resolving in one synchronous
  in-memory call with nothing left to look back at. Call-up morale bonus
  now applies once per match a player features in rather than once per
  series (arguably more realistic — kept as-is, not suppressed).
- **v4.12.0 (done, Part 3 — this rebuild is complete)**: Godot UI now
  shows the real progression this whole rebuild was for. National Team
  screen gets a real Fixtures & Results list (also fixed a real
  pre-existing layout bug there — Squad/XI columns were silently
  overlapping). New World Cup nav screen (CAREER group) shows whichever
  tour/tournament is most current: a flat match list, live group
  standings, or a knockout bracket — backed by a new
  `get_current_international_competition` IPC method, reusing
  `tournament_bracket_screen.gd`'s bracket-card pattern for the knockout
  case.

**In progress: Cricket Captain-style Match Day rebuild** (user request,
2026-07-31) — "make the match day screen better, more detailed and
interactive like cricket captain series." Full plan:
`C:\Users\Tushant\.claude\plans\majestic-leaping-comet.md` (top section).
User explicitly chose the bigger/riskier option: a real drag-and-place
field editor where fielder positions actually affect outcomes, not just a
cosmetic overlay on the 3 presets.
- **v4.13.0 (done, Part 1)**: real per-fielder field positions in
  `match_engine.py` — `FIELD_POSITIONS`/`FIELD_LAYOUT_PRESETS`,
  `field_layout_by_team`, `set_field_layout()`, `_covering_fielder()`. A
  shot's wagon-wheel angle is now rolled before wicket/run resolution
  (previously after, purely for display) so catches and boundary-saves
  (fours only — a six has already cleared the rope by definition) can
  check real field coverage instead of a flat aggregate nudge. Uses two
  previously-unread player attributes (`ground_fielding`, `agility`) for
  the boundary-save roll. Verified against `validate_match_engine.py`'s
  per-format baselines (small ~1-3% downward drift, expected/accepted —
  genuine gaps in the field now matter).
- **v4.14.0 (done, Part 2)**: `get_field_layout`/`set_field_layout` +
  `set_match_bowler` IPC methods (backend-only — no Godot UI drives them
  yet). Fixed a real bug while wiring this up:
  `_apply_tactics_to_next_ball` unconditionally reloaded the field preset
  every ball, which would have silently stomped a custom layout back to
  the preset on the very next delivery — a `custom_field_layout` flag
  fixes it.
- **v4.15.0 (done, Part 3)**: `ground_view.gd` is now a real drag-and-
  place field editor (interactive mode, `layout_changed` signal wired to
  `set_field_layout`), reused on a new FIELD tab in the live Match Day
  screen with 3 quick-preset buttons above it. Fixed a real layout bug
  caught by screenshot review: the ground view's minimum size overflowed
  into the always-visible Commentary panel below it.
- **v4.16.0 (done, Part 4 — this rebuild is complete for now)**: real
  bowler picker (`BowlerPickerModal`, backed by `set_match_bowler`), real
  `HSlider` aggression controls, and a new PITCH VIEW tab showing live
  striker/non-striker/bowler names plus a colour-coded flash at the last
  ball's actual landing spot. **Explicitly deferred**: a full broadcast-
  style scoreboard redesign and consolidating the now-12-tab
  `StatsTabBar` into fewer groups.
- **v4.17.0 (done)**: found and fixed a real, pre-existing overlap bug
  while investigating whether the deferred relayout above was feasible —
  `TacticsRow`/`Controls` were bottom-anchored assuming a total
  `LiveMatchBox` height that didn't match reality (measured ~488px via
  screenshot, not the naive 720px window height), so they silently drew
  on top of `CommentaryCard`. Fixed by switching both to top-anchored,
  explicit-offset positioning right after Commentary. The measured
  ~488px real budget is tight (Cards 204px + Commentary + 2 button rows
  barely fits today) — genuinely growing the FIELD/PITCH VIEW tabs'
  cramped card region and/or consolidating the 12-tab bar would need
  either shrinking the always-visible ScoreBar/LiveStripCard or merging
  TacticsRow+Controls into one row, not just moving boxes around. Worth
  its own scoped pass, not a natural continuation.

**v4.18.0 (done) — real bugs from actually playing the packaged build**:
reported by the user after playing the exported/packaged clients (not
the dev/smoke-test environment). All four were genuine, previously-
unnoticed problems, not user error:
- The whole top nav bar's text was garbled/overlapping and mostly
  unclickable in both clients — a `Button`-doesn't-auto-size-to-child-
  Controls bug in `shell.gd`'s `_build_navbar()`, present (visible in
  screenshots, unflagged) for a long time. Fixed by explicitly sizing
  each section button from its icon+label content.
- Settings/Help/About's Back button always hardcoded Dashboard/Main
  Menu, dropping the player's actual place. New
  `shell.return_from_utility()` tracks and returns to whatever screen
  was open before.
- Every `PanelContainer` without its own margin wrapper had zero content
  padding — headers/fields sat flush against card borders across many
  screens. Fixed centrally in `app_theme.gd`'s default panel stylebox.
- West Indies showed a palm tree emoji instead of a flag in nation
  pickers (`countries.json` — no real ISO flag exists for a multi-nation
  cricket board) — changed to the text code "WI". Also fixed a related
  blank-flag-cell gap in `table_screen.gd`'s Legends-style flag column.

**v4.19.0 (done) — same feedback round, part 2**: the v4.18.0 card-
padding fix only reached the Theme's default `PanelContainer` stylebox;
turned out most real cards in the app go through an explicit per-
instance stylebox override instead (`AppTheme._panel_box()`/
`make_card()`), a separate code path the Theme default never touches —
"still not fixed" was a fair complaint. Also addressed in the same pass:
- `_panel_box()` gained an optional `content_margin` param (default 0,
  every existing call site unaffected unless it opts in); `make_card()`
  now passes one. Dashboard stat tiles, the onboarding card, and Match
  Day's highlight cards audited and fixed directly.
- Nav bar icons were all the same pale grey ("looks very bland") — new
  `NAV_SECTION_COLOURS` gives each of the 8 sections a distinct accent
  from the existing palette.
- `ground_view.gd`/`match_stats_canvas.gd`'s ~20 draw calls all default
  to `antialiased=false` in Godot — every one now passes `true`, fixing
  the reported "too pixely" field diagram.
- Match Day's `ScoreBar` could overflow into `LiveStripCard` and cut off
  text once PREDICT populated a 4th text row in a fixed 80px box.
  Restructured into a two-column split (score+progress left, status/
  rates/prediction stacked right) and given a real broadcast-style green/
  gold treatment while fixing it — a real step toward "look more like
  Cricket Captain," not just a bug fix. **Honest scope note**: the full
  ask (a genuinely Cricket-Captain-grade Match Day + ball-by-ball
  presentation) is bigger than this pass and remains open.

**Still open, not yet investigated**: the two parallel "custom
tournament" systems from the pre-v1.0.0 backlog, never revisited since
(see the old "Known bugs / risks" section below — unverified whether
still accurate post-100-team-expansion). This needs a product decision
(keep both for different purposes, or merge) before more UI work goes
into either — not something to resolve unilaterally.
