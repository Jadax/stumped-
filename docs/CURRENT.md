# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-27
- **Branch:** main
- **Version:** 0.69.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)
- **Company:** ASTRAIVA (Pty) Ltd (South Africa) — all copyright/credit text
  must say this, never "Stumped! development team".

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T10/T20/ODI/The Hundred/Test), competitions, transfers, training, youth (targeted
  recruitment), facilities, finances, honours, career hub, contract
  negotiation, staff (coaches/medical/scouts, transfer market, retirement),
  live commentary modes, saves.
- **277 unit tests pass** (verified 2026-07-26, ~88s, Python 3.14 via
  project venv); 1 pre-existing flaky academy test (probabilistic). Match-engine
  statistical validation realistic and unchanged (T20 7.0 RPO, ODI 5.01,
  Test 3.95).
- `dist/Stumped.exe` last rebuilt at v0.69.0; rebuild with
  `python build_and_package.py` from `cricket_manager/`.
- **Godot client** runs on **4.7.1 stable**. 16 screens registered, 22
  interactive flows. Full match live ball-by-ball with tactics (PREDICT,
  FIELD, aggression, DRS, CHANGE bowler) and Stats Hub (wagon wheel,
  pitch/bowling map, worm, momentum, Manhattan, partnerships). Smoke test
  clean across 3 runs. See `docs/GRAPHICS_MIGRATION_PLAN.md` for full
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

1. **Persistent player fatigue & rotation** — add a real `fatigue`
   column, persist match energy cost across games, feed it into team
   selection risk/injury likelihood, give squad rotation an actual reason
   to exist.
2. **Dynamic player morale** — wire real events (win/loss, being
   dropped, contract situations, relegation/promotion) into morale
   changes instead of a fixed random constant.
3. **Deeper league/international structure** — the largest, most
   disruptive item; sequenced last. More divisions and/or an
   international layer, closing the biggest structural gap vs. Ashes
   Cricket.
4. **Roadmap planned items** — live auctions, academy expansion,
   financial forecasting, keeper batting roles, daily tournaments.
5. **Career startup flow** — manager creation, game-mode selection,
   world configuration.
6. **Real Steam integration** — stubbed; app ID `null` in `config.json`.

## Known bugs / risks

- Audio ducking not verified on real device (dummy driver in dev).
- Godot Stats Hub accumulators reset if you navigate away from Match
  mid-game (only balls from current screen instance captured).
- AI transfer offers run weekly (Sundays); no throttle on offer count
  per day — may flood inbox if many AI clubs have gaps simultaneously.
- Pitch selection only applies when user is home team; away matches
  always use "Green" default (AI opponent pitch selection not implemented).
- Job offers only generated at season end; no mid-season vacancy fills.
- **Player fatigue does not persist across matches** — `player["fatigue"]`
  is read in `match_engine.py`'s energy setup but no `fatigue` column
  exists anywhere in the DB schema, so it always evaluates to 0. Every
  player starts every match at full energy regardless of recent workload;
  squad rotation is currently cosmetic. Next up on the backlog.
- **Player morale never updates in-game** — it genuinely affects match
  performance (`match_engine.py` batting/bowling modifiers) and AI
  selection/negotiation logic, but nothing (win/loss, being dropped,
  contract events) ever mutates it after initial generation. A fixed
  random constant dressed up as a live mood stat. Next up on the backlog.
- League structure is 2 fictional divisions + 1 knockout cup; no
  international cricket / national-team layer. Deliberately deprioritised
  per `docs/UX_ROADMAP.md`, but the single biggest structural gap vs.
  Ashes Cricket specifically. Third item on the backlog below.

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
- The Hundred uses 100 legal deliveries in 20 five-ball sets; each bowler is
  capped at 20 balls. Scorecards, ball trackers and rates display sets rather
  than mislabelling them as six-ball overs.

## Validation commands (run from `cricket_manager/`)

```powershell
python -m unittest discover -s tests -v          # expect 277 pass, ~88s
python validate_match_engine.py                   # statistical validation
python main.py                                    # manual run
python build_and_package.py                       # packaged build
godot --headless --path godot_client -- --smoke-test  # Godot smoke test
```

## Next action

Implement persistent player fatigue & rotation (backlog item 1 above) —
add a `fatigue` column to the players table, persist match energy cost
via `apply_match_player_updates`, recover it gradually on rest days
(`apply_daily_training`/`advance_day`), and surface it on Squad/Selection
so rotation decisions actually matter.
