# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-30
- **Branch:** main
- **Version:** 4.12.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)
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
python -m unittest discover -s tests -v          # expect 424 pass, ~400-540s (100-team world)
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

**Still open, not yet investigated**: the two parallel "custom
tournament" systems from the pre-v1.0.0 backlog, never revisited since
(see the old "Known bugs / risks" section below — unverified whether
still accurate post-100-team-expansion). This needs a product decision
(keep both for different purposes, or merge) before more UI work goes
into either — not something to resolve unilaterally.
