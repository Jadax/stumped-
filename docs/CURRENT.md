# CURRENT — cross-agent handoff

Read `AGENTS.md` first; architecture in `docs/ARCHITECTURE.md`; open bugs and
debt in `docs/CODE_AUDIT.md`. This file is volatile state only — keep <200
lines, replace stale content, never append history.

## Snapshot

- **Version:** 5.2.0 in flight (`config.json` bumped; package rebuild +
  commit/push pending)
- **Tests:** pytest -k "friendly or fan or cohesion or ipc" = 242 passed;
  full suite ~942 (last full gate ran clean at v5.1.0)
- **Stack:** Python 3.12 + pygame-ce + pygame-gui backend; SQLite saves;
  Godot 4 client talks to `ipc_server.py` over stdio JSON

## Environment facts (hard-won)

- Python: `"C:\Users\Tushant\AppData\Local\Programs\Python\Python312\python.exe"`
- Godot: `C:\Users\Tushant\Downloads\Godot_v4.7.1-stable_win64.exe`
- Export: `--headless --path C:\Dev\Game\godot_client --export-release "Windows Desktop" C:\Dev\Game\godot_client_dist\StumpedGodot.exe`
- Full pytest runs hang on the PowerShell pipe: redirect to a file
  (`> "$env:TEMP\out.txt" 2>&1`) and read the tail.
- Start-Process needs -RedirectStandardOutput/-RedirectStandardError or the
  tool sandbox kills it (Godot GUI runs included).
- **PowerShell Get/Set-Content is UTF-8-hostile**: a previous session's
  PS regex rewrite double-encoded every smart punctuation char in the Godot
  client ("â€"" = em-dash). Parser: PowerShell console output lies about
  encodings — verify with Python `bytes.decode()` / `ord()` checks.
- Two agents share this repo — check `git status` before editing.

## Danger rule learned (v5.2.0)

NEVER edit text files via PowerShell Get-Content/Set-Content. The Python
FileIO (`Path.write_text(encoding="utf-8")`) repairs are already applied —
see CHANGELOG 5.2.0 for the full extent (18 files).

## v5.2.0 state (this session)

- **Club hub** (`club_screen.tscn/.gd`, shell "Club" route + CLUB nav
  group entry): landing screen after career team selection / load;
  career_team_selection_screen + load_game_screen remap
  destination "Dashboard" → "Club" (backend unchanged — pygame raises on
  unknown screen names, so GameController can't be retargeted).
- **Pastel light regrade**: AppTheme tokens are now the parchment
  palette (BACKGROUND #f6f4ee, TEXT_PRIMARY #2a2823, GOLD #9c6f14;
  see app_theme.gd); 39 scenes' hardcoded dark `Color(...)` literals
  remapped via Python; `default_clear_color` + min window 1024x640 set
  in project.godot.
- **Dashboard overflow fix**: Right column → ScrollContainer/RightInner in
  dashboard_screen.tscn (Bottom grow_vertical=1). gd paths updated.
- **Match Day pre-match**: fixture bar = card + green left accent,
  TEXT_PRIMARY; START MATCH = HEADER_GREEN + white text.
- **ipc_server**: missing `connect` import fixed; fan_sentiment /
  squad_cohesion / friendly fixtures handlers work again (broken since
  v5.1.0 — dashboard tiles silently blank).
- **Debug harness still installed**: `debug_snap.gd` autoload +
  `project.godot` DebugSnap entry + `_snapshots/` — drive
  show_screen(["Club","Dashboard","Match","Calendar"]), PNG + chrome
  metrics out. REMOVE BOTH before shipping (see Next actions 1).

## Next actions (suggested order)

1. Remove DebugSnap autoload from project.godot + delete debug_snap.gd and
   its .uid; re-import; Godot export rebuild.
2. Rebuild package: `python build_and_package.py` from `cricket_manager/`
   (own test gate ~25 min; phases may be run manually — see CHANGELOG).
3. Commit + push v5.2.0 (CHANGELOG + CURRENT.md + config.json already
   updated).
4. **Live strip overlap** (user report: momentum text over score strip) —
   needs an in-match snapshot via harness (drive `start_match` then snap
   Match; inspect LiveStripCard/Momentum rows in match_screen.tscn ~228+).
5. **LINKED/UNLINKED aggression end-to-end** (user asked): verify
   `natural_batting_aggression` caps vs the IPC set paths through the
   match screen striker/bowler aggro rows.
6. Remaining caller-less IPC (Steam cloud/achievements, custom-tournament
   CRUD, scouting, career timeline/press) — batch into v5.3.0.
7. Legal-names remediation (audit A) before Steam.

## Deferred / blocked

- Per-nation league structure replacing the global pyramid: ~20+ tests
  across 10+ files reference global competition names. Plan doc at
  `C:\Users\Tushant\.claude\plans\per-nation-domestic-leagues.md`.
- `advance_day()` decomposition (audit F) — only alongside related work.

## Validation (from `cricket_manager/`)

```
& "C:\Users\Tushant\AppData\Local\Programs\Python\Python312\python.exe" -m pytest tests -q > out.txt 2>&1
python main.py            # manual run (pygame legacy UI)
```

## Definition of done

Code change + tests pass + version bump + CHANGELOG entry +
`docs/CURRENT.md` updated + package rebuilt + commit pushed to origin main.
