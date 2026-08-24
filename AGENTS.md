# AGENTS.md — shared instructions for Codex and Claude

## Project overview

**Stumped!** (v4.99.1) — a cricket management sim for Windows. Python 3.12 +
pygame-ce + pygame-gui backend, SQLite persistence, Godot 4 client UI
(`godot_client/`) talking to `cricket_manager/ipc_server.py` over stdio JSON.
Working, near-release: ~938 automated tests pass.

## Read first (stable → volatile; each file cached well between sessions)

1. This file + `docs/ARCHITECTURE.md` — stable architecture/constraints
2. `docs/CURRENT.md` — volatile state, next actions, environment facts
3. `docs/CODE_AUDIT.md` — open bugs/debt register; check before "fixing" things
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

- Tests: `python -m pytest tests -q` (~938 pass; ~18 min — slow DB reseed per
  test, see audit item D). If output stalls, the PowerShell pipe is backing
  up: redirect to a file (`> out.txt 2>&1`) and read the tail.
- Manual run: `python main.py`
- Package: `python build_and_package.py` (only when releasing)

There is no lint/type-check configuration.

## Rules

- Do not make unrelated changes or broad refactors.
- Never commit secrets, `.env` files, `dist/`, `build/`, save databases, or logs.
- Update `docs/CURRENT.md` after any meaningful work (replace stale info; keep <200 lines).
- Update `CHANGELOG.md` and `config.json` version when shipping user-visible changes.
- Commit and push to `origin main` after completing work, with a descriptive message.
- On every version bump, rebuild the packaged exe: `python build_and_package.py`
  from `cricket_manager/` (output in `dist/`, gitignored). The user tests from
  `dist/Stumped.exe` — a stale exe hides shipped work.

## Definition of done

Code change + tests pass + version bumped + `python build_and_package.py`
rebuilt + `docs/CURRENT.md` updated + committed and pushed.
