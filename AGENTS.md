# AGENTS.md — shared instructions for Codex and Claude

## Project overview

**Stumped!** (v0.9.0) — a cricket management sim for Windows. Python + pygame-ce
+ pygame-gui, SQLite persistence, PyInstaller packaging. All code is in
`cricket_manager/`. It is a working, near-release game: 50 automated tests pass
and packaged builds exist.

## Read first

1. `docs/CURRENT.md` — active task state and next action
2. `docs/ARCHITECTURE.md` — components and constraints
3. `cricket_manager/README.md` — features and player-facing docs
4. `cricket_manager/src/data/roadmap.json` — planned/in-progress features

## Architecture constraints

- Entry point: `cricket_manager/main.py` (startup via `src/utilities/launcher.py`).
- Match simulation lives in `cricket_manager/match_engine.py`; persistence in
  `cricket_manager/database.py`; competitions in `cricket_manager/competition.py`.
- UI screens are in `cricket_manager/ui/` and `cricket_manager/src/views/screens/`;
  reusable widgets in `cricket_manager/ui/widgets/`. Design tokens live in
  `src/views/theme.py` and `ui/theme.json` — do not hardcode colours/spacing in screens.
- Saves are SQLite (`data/cricket_manager.db`, gitignored). Schema migrations
  must keep existing saves loading (see 16→24-team migration precedent).
- No licensed real-world names, likenesses, or logos — everything is generated
  (see `LEGAL_COMPLIANCE.md`).

## Conventions

- Python, standard library + pygame-ce/pygame-gui only; no new deps without need.
- British-English naming in game text ("colours", cricket terminology).
- Tests use `unittest` with temporary databases; add tests alongside features
  in `cricket_manager/tests/`.

## Validation (run from `cricket_manager/`)

- Tests: `python -m unittest discover -s tests -v` (expect all pass, ~6 s)
- Manual run: `python main.py`
- Package: `python build_and_package.py` (only when releasing)

There is no lint/type-check configuration.

## Rules

- Do not make unrelated changes or broad refactors.
- Never commit secrets, `.env` files, `dist/`, `build/`, save databases, or logs.
- Update `docs/CURRENT.md` after any meaningful work (replace stale info; keep <200 lines).
- Update `CHANGELOG.md` and `config.json` version when shipping user-visible changes.
- Commit and push to `origin main` after completing work, with a descriptive message.

## Definition of done

Code change + tests pass + `docs/CURRENT.md` updated + committed and pushed.
