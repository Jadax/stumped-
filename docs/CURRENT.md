# CURRENT — cross-agent handoff

Read `AGENTS.md` first; architecture in `docs/ARCHITECTURE.md`; open bugs and
debt in `docs/CODE_AUDIT.md`. This file is volatile state only — keep <200
lines, replace stale content, never append history.

## Snapshot

- **Version:** 5.2.1 in flight (config.json + CHANGELOG updated; package
  rebuild + Godot export + commit/push pending for this round)
- **v5.2.0 shipped:** commit 7858671 pushed to origin main; deliverables
  `cricket_manager/dist/Stumped-Windows-x64-v5.2.0.zip` + `dist/Stumped.exe`;
  Godot export `godot_client_dist/StumpedGodot.exe` (111,778,800 bytes)
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
  client ("â€"" = em-dash). PowerShell console output also lies about
  encodings — verify with Python `bytes.decode()` / `ord()` checks.
- Two agents share this repo — check `git status` before editing.
- Snap-harness technique (recreate when needed): temp `debug_snap.gd`
  autoload driving `shell.show_screen([...])` + `get_viewport()` PNGs to
  `_snapshots/`, chrome metrics via prints; wait for IpcBridge backend
  (loop `get_dashboard` until no "backend not" error). Stylebox debugging:
  `btn.get_theme_stylebox(name)` per state; disable/hover journeys need
  `pixel scans` because visually identical greys come from many sources.

## v5.2.1 state (this session)

Six user screenshots → five root causes fixed and snap-verified:

- **Dark edge strips**: `ambient_background.gd` was still painting the
  night-sky palette behind the shell; screen backgrounds are 1248x538 in a
  1280x562 content band so dark strips showed right/bottom. Ambient
  repainted to parchment tones + `shell._ready` adds a parchment
  `ContentBacking` ColorRect under `$Layout/Content`.
- **Empty Calendar**: `calendar_screen.gd` fetched data only in
  `refresh()`, which the shell calls only after advance_day. `_ready()`
  now calls `refresh()`. (Backend `fetch_calendar` already returned
  `training_weekday_counts` — probe confirmed.)
- **Table text overlap**: `table_screen.gd` fixed offsets — context hint
  (60–88) vs tab bar (52) vs filter bar (52/96). Now a `_content_top`
  stacking cursor: hint → tab bar → filter bar → Selection brief; scroll
  area starts below whatever stacked.
- **0px-wide scrollbars**: VScrollBar size was (0, N) on every
  ScrollContainer — the track stylebox had zero content margins. Track:
  SURFACE + BORDER + 3px margins; grabber TEXT_MUTED; hover ACCENT. Codul
  grabber doubles as today's "scrollbar missing" report.
- **Grey active-tab fill**: effective styleboxes were transparent but the
  drawn box matched the theme's disabled composite; never fully root-
  caused. `style_tab_button(true)` now overrides all six button states
  (chrome = ACTIVE tint, radius 6, gold underline on focus) — deterministic
  result, verified across Studio/Club/Calendar/Transfers/Squad snaps.

## Next actions (suggested order)

1. Rebuild package + export (see Definition of done), commit + push v5.2.1.
2. **Live strip overlap** (user report: momentum text over score strip) —
   needs an in-match snapshot via harness (drive `start_match` then snap
   Match; inspect LiveStripCard/Momentum rows in match_screen.tscn ~228+).
3. **LINKED/UNLINKED aggression end-to-end**: verify
   `natural_batting_aggression` caps vs the IPC set paths through the
   match screen striker/bowler aggro rows.
4. Systematic UI sweep of remaining screens (Data Hub, Inbox, Finances,
   Facilities, Youth Academy, Training, Tactics, Press Conference,
   Settings, Help) with the snap harness — same complaint classes
   (overlap, invisible chrome) will exist there.
5. Remaining caller-less IPC (Steam cloud/achievements, custom-tournament
   CRUD, scouting, career timeline/press) — batch into v5.3.0.
6. Legal-names remediation (audit A) before Steam.

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
`docs/CURRENT.md` updated + package rebuilt (and Godot export rebuilt on
version bump) + commit pushed to origin main.
