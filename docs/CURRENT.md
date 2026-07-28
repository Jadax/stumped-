# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-28
- **Branch:** main
- **Version:** 0.82.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)
- **Dev-save gotcha**: the unpackaged Godot smoke test (run from source,
  not the built .exe) reads/writes `cricket_manager/data/cricket_manager.db`
  directly — `launcher.py`'s `get_launch_paths()` sets `base == resource_root`
  when not frozen. `%LOCALAPPDATA%\Stumped\data\cricket_manager.db` is
  only used by the *packaged* .exe. Reset the one matching how you're
  running it, or "fresh save" verification silently reuses old state
  (hit this in v0.80.0/v0.81.0 — see CHANGELOG v0.81.0's Fixed entry).
- **Company:** ASTRAIVA (Pty) Ltd (South Africa) — all copyright/credit text
  must say this, never "Stumped! development team".

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T10/T20/ODI/The Hundred/Test), competitions, transfers, training, youth (targeted
  recruitment), facilities, finances, honours, career hub, contract
  negotiation, staff (coaches/medical/scouts, transfer market, retirement),
  live commentary modes, saves.
- **332 unit tests pass** (324 + 8 new in v0.82.0; verified 2026-07-28,
  Python 3.14 via project venv); 1 pre-existing flaky academy test
  (probabilistic). Match-engine statistical validation realistic (T20
  ~6.91 RPO, ODI ~4.99, Test ~3.93 — normal run-to-run variance;
  re-verified after v0.82.0's world-generation changes).
- `dist/Stumped.exe` last rebuilt at v0.82.0; rebuild with
  `python build_and_package.py` from `cricket_manager/`.
- **Godot client** runs on **4.7.1 stable**. 21 in-career screens (added
  Press Conference, v0.81.0; Trophy Room + Club Records, v0.80.0,
  replacing the old flat Honours table) plus 7 pre-career/utility screens
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
  v0.82.0 (realism tuning is backend/data-only); smoke test re-verified
  clean across 3 consecutive runs against a genuinely fresh save (see the
  dev-save gotcha note above — the prior "1 pre-existing flaky step"
  claim in v0.80.0 was itself a stale-save artifact, corrected in
  v0.81.0's CHANGELOG). See `docs/GRAPHICS_MIGRATION_PLAN.md` for prior
  migration-phase status.

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
- **Phases 8-9** — not started (long-save stability, Steam packaging).
  See the plan file for the full phase list.

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
python -m unittest discover -s tests -v          # expect 332 pass, ~80-108s
python validate_match_engine.py                   # statistical validation
python main.py                                    # manual run
python build_and_package.py                       # packaged build
godot --headless --path godot_client -- --smoke-test  # Godot smoke test
```

## Next action

Phases 1-7 of the "best-in-class Steam cricket manager" roadmap are done
(v0.76.0-v0.82.0) — see "Godot migration status" above. **Next: Phase 8,
long-save stability** — a genuine multi-season headless stress test does
not exist yet (simulate N seasons via repeated `rollover_season()` calls,
assert no DB corruption/unbounded growth/orphaned rows — e.g. confirm
`legends`/`season_records`/`player_records` grow sanely and nothing like
`game_state`'s per-team baseline keys accumulates unboundedly), then fix
whatever it finds. Full phase list and rationale in the plan file:
`C:\Users\Tushant\.claude\plans\majestic-leaping-comet.md`. FM/Cricket
Captain reference screenshots still haven't been attached in this
conversation — worth asking for again before the next visual-focused
pass.

Also still open, not yet prioritised:

- The two parallel "custom tournament" systems (`src/views/screens/
  tournament_setup.py`'s pre-game standalone mode vs. `create_custom_
  tournament`/etc.'s in-career IPC system) still need a product decision
  before either gets more UI investment.
- **Fuller international cricket** — v0.72.0 is deliberately a scoped
  slice (once-a-season, auto-selected, no user control). A fuller
  version (more divisions, a proper international tournament/World Cup,
  user-influenced national squad selection) is still a large structural
  gap vs. Ashes Cricket, and overlaps with the roadmap's later phases.
- `docs/UX_ROADMAP.md`'s existing backlog (Squad Planner extensions,
  shortlists, board requests, manager persona/coaching badges).
