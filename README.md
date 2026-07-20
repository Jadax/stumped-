# Stumped! (repository root)

Cricket management simulation for Windows. All source lives in
[`cricket_manager/`](cricket_manager/) — see
[`cricket_manager/README.md`](cricket_manager/README.md) for full docs
(features, installation, how to play, packaging).

## Quick reference

- Stack: Python 3.10+ (64-bit), pygame-ce, pygame-gui, SQLite, PyInstaller
- Run: `cd cricket_manager && python main.py`
- Tests: `cd cricket_manager && python -m unittest discover -s tests -v`
- Package: `cd cricket_manager && python build_and_package.py` (output in `dist/`, gitignored)
- No environment variables or secrets are required.

Agent/AI-assistant guidance: [`AGENTS.md`](AGENTS.md) and
[`docs/CURRENT.md`](docs/CURRENT.md).
