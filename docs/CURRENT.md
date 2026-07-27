# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-27
- **Branch:** main
- **Version:** 0.75.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)
- **Company:** ASTRAIVA (Pty) Ltd (South Africa) — all copyright/credit text
  must say this, never "Stumped! development team".

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T10/T20/ODI/The Hundred/Test), competitions, transfers, training, youth (targeted
  recruitment), facilities, finances, honours, career hub, contract
  negotiation, staff (coaches/medical/scouts, transfer market, retirement),
  live commentary modes, saves.
- **304 unit tests pass** (verified 2026-07-27, ~79s, Python 3.14 via
  project venv); 1 pre-existing flaky academy test (probabilistic). Match-engine
  statistical validation realistic and unchanged (T20 7.0 RPO, ODI 5.01,
  Test 3.95).
- `dist/Stumped.exe` last rebuilt at v0.75.0; rebuild with
  `python build_and_package.py` from `cricket_manager/`.
- **Godot client** runs on **4.7.1 stable**. 18 screens registered, 25
  interactive flows (added the onboarding tutorial overlay, v0.75.0 —
  not a nav screen, so the screen count is unchanged). Full match live
  ball-by-ball with tactics (PREDICT, FIELD, aggression, DRS, CHANGE
  bowler), Stats Hub (wagon wheel, pitch/bowling map, worm, momentum,
  Manhattan, partnerships), pre-match pitch selection and opposition
  report, board objectives/confidence, first-run tutorial. Smoke test
  clean across 3 runs (both a fresh-save and an already-dismissed-
  tutorial run). See `docs/GRAPHICS_MIGRATION_PLAN.md` for full
  migration status.

## Godot migration status

Phase 0 (PoC) done. Phase 1 (IPC, 30 methods) done. Phase 2 (screen
porting): **all 16 screens render real data + interactive flows**. The
pygame client remains the shipped product. Hybrid architecture: Python
backend (`database.py`/`match_engine.py`/`competition.py`/`src/models/*`)
unchanged; Godot client talks to it via JSON-RPC-over-stdio
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
7. **Roadmap planned items** — live auctions, academy expansion,
   financial forecasting, keeper batting roles, daily tournaments.
8. **Career startup flow** — manager creation, game-mode selection,
   world configuration.
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
python -m unittest discover -s tests -v          # expect 304 pass, ~80s
python validate_match_engine.py                   # statistical validation
python main.py                                    # manual run
python build_and_package.py                       # packaged build
godot --headless --path godot_client -- --smoke-test  # Godot smoke test
```

## Next action

The full 3-part "flesh out everything" Godot/pygame feature-parity
catch-up is now done (v0.73.0–v0.75.0: pitch selection, opposition
report, job offers, board objectives/confidence, onboarding tutorial).
No fresh user-directed roadmap item is currently open. The two parallel
"custom tournament" systems need a product decision before either gets
more UI investment — see "Known bugs / risks" above. Otherwise, pick
from "Roadmap planned items" in Active backlog or the still-open items
below.

Also still open, not yet prioritised:

- **Fuller international cricket** — v0.72.0 is deliberately a scoped
  slice (once-a-season, auto-selected, no user control). A fuller
  version (more divisions, a proper international tournament/World Cup,
  user-influenced national squad selection) is still the largest
  remaining structural gap vs. Ashes Cricket if wanted.
- `docs/UX_ROADMAP.md`'s existing backlog (Squad Planner extensions,
  shortlists, board requests, manager persona/coaching badges).
- A fresh visual/UX pass through the exported build for rough edges.
