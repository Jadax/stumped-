# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-24
- **Branch:** main
- **Version:** 0.64.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)
- **Company:** ASTRAIVA (Pty) Ltd (South Africa) — all copyright/credit text
  must say this, never "Stumped! development team".

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T10/T20/ODI/Test), competitions, transfers, training, youth (targeted
  recruitment), facilities, finances, honours, career hub, contract
  negotiation, staff (coaches/medical/scouts, transfer market, retirement),
  live commentary modes, saves.
- **226 unit tests pass** (verified 2026-07-24, ~53s, Python 3.12.10 via
  project venv); match-engine statistical validation realistic and unchanged
  (T20 7.0 RPO, ODI 5.01, Test 3.95).
- `dist/Stumped.exe` last rebuilt at v0.63.0; rebuild with
  `python build_and_package.py` from `cricket_manager/`.
- **Godot client** runs on **4.7.1 stable**. 16 screens registered, 22
  interactive flows. Full match live ball-by-ball with tactics (PREDICT,
  FIELD, aggression, DRS, CHANGE bowler) and Stats Hub (wagon wheel,
  pitch/bowling map, worm, momentum, Manhattan, partnerships). Smoke test
  clean across 3 runs. See `docs/GRAPHICS_MIGRATION_PLAN.md` for full
  migration status.

## Godot migration status

Phase 0 (PoC) done. Phase 1 (IPC, 28 methods) done. Phase 2 (screen
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
4. Pitch selection for home matches (From the Pavilion feature)
5. ~~Player talents visible in commentary~~ **DONE** (pre-existing)
6. Custom tournament creator
7. Onboarding tutorial for new players

## Active backlog (priority order)

1. **Pitch selection** — let user choose pitch type for home matches
   (tactical advantage for your bowling type).
2. **Interactive job market** — job offers/sackings driven by reputation
   and board confidence.
3. **The Hundred format** — five-ball-over support in `match_engine.py`.
4. **Roadmap planned items** — live auctions, academy expansion,
   financial forecasting, keeper batting roles, daily tournaments.
5. **Career startup flow** — manager creation, game-mode selection,
   world configuration.
6. **Real Steam integration** — stubbed; app ID `null` in `config.json`.

## Known bugs / risks

- None known; no TODO/FIXME markers in source.
- Staff system new and untested against live multi-season save.
- Audio ducking not verified on real device (dummy driver in dev).
- Godot Stats Hub accumulators reset if you navigate away from Match
  mid-game (only balls from current screen instance captured).
- AI transfer offers run weekly (Sundays); no throttle on offer count
  per day — may flood inbox if many AI clubs have gaps simultaneously.

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

## Validation commands (run from `cricket_manager/`)

```powershell
python -m unittest discover -s tests -v          # expect 226 pass, ~53s
python validate_match_engine.py                   # statistical validation
python main.py                                    # manual run
python build_and_package.py                       # packaged build
godot --headless --path godot_client -- --smoke-test  # Godot smoke test
```

## Next action

Implement pitch selection for home matches — let user choose pitch type
(tactical advantage for bowling type). Then the interactive job market.
