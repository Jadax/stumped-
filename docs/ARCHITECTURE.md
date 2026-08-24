# Architecture

All paths relative to `cricket_manager/` unless noted. Stable reference —
volatile state lives in `docs/CURRENT.md`, open bugs in `docs/CODE_AUDIT.md`.

## Components

- **Launcher/startup** — `main.py` + `src/utilities/launcher.py`: first-run
  directory/config creation, corrupt-DB quarantine, recovery backup, crash
  reporting, rotating logs (`src/utilities/logger.py`).
- **Game controller** — `src/controllers/game_controller.py`: top-level state
  machine, screen routing, game clock/date advancement, autosave.
  `src/controllers/audio_controller.py`: crowd effects, volume/mute.
- **Match engine** — `match_engine.py`: attribute-driven ball-by-ball sim for
  T10/T20/The Hundred/ODI/Test. Powerplays, wides/no-balls, DRS, DLS,
  follow-ons, declarations, Super Overs, energy/fatigue, fielding checks,
  Monte Carlo score predictor, sub-second fast sim. Validation harness:
  `validate_match_engine.py` against `src/data/match_validation.json`.
- **Competition layer** — `competition.py`: season calendar (March pre-season
  friendlies, April–September competitive season), per-nation leagues and
  domestic cups over a 100-team world, Academy Cup, weekly challenges,
  day-tick orchestration (`advance_day`: training, wages, transfers,
  auctions, narrative).
- **Persistence** — `database.py`: SQLite schema, saves, migrations (legacy
  saves migrate forward; see the `_rebuild_*` and `_ensure_column` helpers).
  DB path from `config.json`.
- **IPC server** — `ipc_server.py`: stdio JSON-RPC shim exposing database/
  competition functions to the Godot client. Handlers delegate; business
  logic does not live here.
- **Domain models** — `src/models/`: pure functions wherever possible
  (fixture/revenue maths, narratives, development, sentiment, cohesion,
  headlines, leaders, pitch AI…). Callers wire persistence. A few legacy
  modules still hit SQLite directly (tracked in `docs/CODE_AUDIT.md`).
- **UI** — two layers: management screens in `ui/` (pygame legacy) and
  startup/meta screens in `src/views/screens/`. Reusable widgets in
  `ui/widgets/`. Design tokens: `src/views/theme.py` + `ui/theme.json`.
- **Generated assets** — `src/utilities/player_portraits.py` (deterministic
  portraits), `logo_generator.py` (team crests), `graphics.py`. Static
  assets in `assets/`.
- **Steam integration** — `src/steam_integration.py` + `steam_stub.json`:
  stubbed Steam API (achievements, cloud) pending a real app ID.
- **Packaging** — the shipping presentation is the Godot 4 Windows export
  from `godot_client/` (repo root). `build_and_package.py` remains only for
  backend/legacy regression validation; do not add new pygame UI features.

## Data flow

Godot client → JSON-RPC → `ipc_server` → `database.py` / `competition.py` /
`match_engine.py` → SQLite → responses. The pygame app follows the same
layering inline via `game_controller`. Config from `config.json`; static game
data from `src/data/*.json`.

## Constraints

- 1280×720 minimum; scales to 4K with exact 2x logical canvas in fullscreen.
- No licensed real-world names, likenesses, or logos — everything generated
  (`../LEGAL_COMPLIANCE.md`; one known seed-data exception tracked in
  `CODE_AUDIT.md` item A).
- Save compatibility must be preserved across schema changes.
- GBP is the accounting base currency; display currencies are presentation only.
- British English in all game text.

## Known debt

See `docs/CODE_AUDIT.md` (single source of truth for bugs, duplication,
dead code, and structural debt). Notable: large single-file core modules;
no lint/type-check tooling configured.
