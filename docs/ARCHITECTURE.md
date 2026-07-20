# Architecture

All paths relative to `cricket_manager/`.

## Components

- **Launcher/startup** — `main.py` → `src/utilities/launcher.py`: first-run
  directory/config creation, corrupt-DB quarantine, recovery backup, crash
  reporting, rotating logs (`src/utilities/logger.py`).
- **Game controller** — `src/controllers/game_controller.py`: top-level state
  machine, screen routing, game clock/date advancement, autosave.
  `src/controllers/audio_controller.py`: crowd effects, volume/mute.
- **Match engine** — `match_engine.py`: attribute-driven ball-by-ball sim for
  T20/ODI/Test. Powerplays, wides/no-balls, DRS, DLS, follow-ons, declarations,
  Super Overs, energy/fatigue, fielding checks, Monte Carlo score predictor,
  sub-second fast sim. Validation harness: `validate_match_engine.py` against
  `src/data/match_validation.json`.
- **Competition layer** — `competition.py`: two 12-club divisions,
  promotion/relegation, knockout cup, friendlies, fixtures, standings, NRR.
- **Persistence** — `database.py`: SQLite schema, saves, migrations (older
  16-team saves migrate to 24-team model). DB path from `config.json`.
- **Domain models** — `src/models/`: player, generation, form, records,
  training (+schedule), transfers, youth, facilities, finances/currency
  (GBP-base, 10 display currencies), difficulty, manager.
- **UI** — two layers: management screens in `ui/` (dashboard, selection,
  match_view, squad, transfers, training, youth, facilities, finances, inbox,
  settings, pre_match, player_modals) and startup/meta screens in
  `src/views/screens/` (main menu, new game setup, career team selection,
  tournament/world-cup setup, player detail, help). Reusable widgets in
  `ui/widgets/`. Design tokens: `src/views/theme.py` + `ui/theme.json`.
- **Generated assets** — `src/utilities/player_portraits.py` (deterministic
  portraits), `logo_generator.py` (team crests), `graphics.py`. Static assets
  in `assets/` (Inter font, procedural audio, images).
- **Steam integration** — `src/steam_integration.py` + `steam_stub.json`:
  stubbed Steam API (achievements, cloud) pending a real app ID.
- **Packaging** — `build_and_package.py`, `build.spec`, `build_windows.bat`,
  `hooks/pyi_rth_stumped.py`; output to `dist/` (gitignored).

## Data flow

Input → active screen → `game_controller` → models/`match_engine` →
`database.py` (SQLite) → screens re-render from model state. Config from
`config.json`; static game data (countries, names, leagues, help, FAQ,
roadmap) from `src/data/*.json`.

## Constraints

- 1280×720 minimum; scales to 4K with exact 2x logical canvas in fullscreen.
- All players/teams/portraits/crests are procedurally generated — no licensed
  content (`LEGAL_COMPLIANCE.md`).
- Save compatibility must be preserved across schema changes.
- GBP is the accounting base currency; display currencies are presentation only.

## Known debt / notes

- Steam integration is a stub; real Steamworks wiring pending app ID.
- `database.py` and `match_engine.py` are large single-file modules.
- No lint or type-check tooling configured.
