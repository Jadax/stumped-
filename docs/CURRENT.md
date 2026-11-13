# CURRENT — cross-agent handoff

Read `AGENTS.md` first; architecture in `docs/ARCHITECTURE.md`; open bugs and
debt in `docs/CODE_AUDIT.md`. This file is volatile state only — keep <200
lines, replace stale content, never append history.

## Snapshot

- **Version:** 5.3.0 (living world — see "v5.3.0 state" below)
- **Tests:** full suite 957 (956 + new living-world tests); Godot smoke all
  39 screens OK; UI audit 0 issues at 1280x720 and 1920x1080
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
- **PowerShell Get/Set-Content is UTF-8-hostile**: use Python
  `Path.write_text(encoding="utf-8")` or the edit tools. PowerShell console
  output lies about encodings — verify with Python `ord()` checks before
  assuming data mojibake.
- Two agents share this repo — check `git status` before editing.
- **Snap-harness technique** (recreated as `debug_snap.gd` + DebugSnap
  autoload, REMOVED again before v5.2.2 packaging): wait for group "shell",
  loop `get_dashboard` until backend answers, `show_screen("Match")`, press
  `PreMatchBox/StartButton` by node path, 10x NextBallButton, PNG snapshots
  to `_snapshots/` + geometry dumps. Do NOT rely on `"x" in screen` property
  checks for onready vars — they mislead; use `get_node_or_null` paths.
  A live match started by the harness persists in the dev save; the harness
  must handle BOTH pre-match (StartButton present) and live-resume layouts.
- `_snapshots/` is gitignored — never commit its PNGs/logs.

## v5.3.0 state (this session) — living world

Verified by day-by-day soak runs (harness in session scratchpad, not in repo):
3 seasons with zero orphaned/overdue fixtures, zero same-day clashes, every
competition finished; 30-season run shows stable talent (Div 1 avg ~69-72,
~220-250 players rated 80+) and stable AI club cash.
- Scheduling: `_insert_scheduled_round_robin` + busy-date map keep every
  competition inside 1 Mar–26 Sep; `advance_day` catches up `date<=today`
  fixtures, purges stale ones, `_finish_season_fixtures` plays late rounds.
- Cups: `_cup_opening_round` + generic `_advance_cup_if_ready` (byes rejoin,
  one Final, format preserved). ICC cadence via `tournament_held_in`.
- People: `process_contract_expiries`, `run_ai_transfer_market`,
  `apply_annual_development` (after retire/release decisions), wider regen
  potential tail. Renewal IPC: `get_contract_offer`, `offer_contract`.
- Money: `_run_weekly_club_finances` (all clubs: wages, operating costs,
  self-balancing central funding — `src/models/club_economy.py`).
- Schema 6: `transfers.player_id` ON DELETE SET NULL (rollover crash fix).
- Known: an UNMANAGED manager's club (no renewals) dwindles and hoards
  central funding — fine for real play, but consider a minimum squad /
  emergency loan signings for neglected squads.
- UI: `--ui-audit --res=WxH` writes screenshots + report to
  `screenshots/audit/<WxH>/` (0 issues at 720p/1080p). Smoke test: all 39
  screens OK (stale v5.2.0 expectations updated).

## v5.2.2 state (this session)

"Live strip overlap" user report (momentum text over score strip) fixed and
verified with live in-match snapshots:

- **InfoBox overflow fixed**: match screen ScoreBar InfoBox stacked five
  rows (~91px min) inside the 90px broadcast bar — momentum + crowd +
  prediction spilled past the bottom of the green bar onto the live strip
  card. Momentum and crowd now share one centred HBox row
  (`_build_momentum_and_crowd_indicators`), and the prediction label is
  hidden until a prediction is requested (visible=true only in
  `_on_predict_pressed`, hidden in the reset path).
- **Score readability**: score + prediction tokens were the light-theme
  dark amber (AppTheme.GOLD) on HEADER_GREEN — unreadable. Now
  AppTheme.CARD (cream-on-green). Progress bar got a darkened-green track
  + cream fill via `AppTheme._panel_box` (note: reference AppTheme
  constants/functions through `AppTheme.` — bare names do not resolve in
  match_screen scope, caused a parse error that blanked the whole screen).
- **Momentum glyph**: ▲/▼/◆ prefix + plain white text replaces muddy
  mint/rose tints on green (`_update_momentum_and_crowd`).
- **Momentum chart** (`match_stats_canvas.gd _draw_momentum`): tinted
  batting/bowling halves, BATTING/BOWLING ON TOP side labels (drawn only
  when plot ≥40px), current-value marker coloured by sign. Stats card
  reserves min height 96px for chart tabs (`_show_stats_tab`); margins
  scale with card height (was fixed 24px squishing the chart to ~12px of
  drawing).
- Verified via harness: live spin of Lancashire match — score cream,
  one-row momentum/crowd, no spill over LiveStripCard (760×57), momentum
  chart with labels + red marker on negative momentum.

## Next actions (suggested order)

1. Rebuild package + export (see Definition of done), commit + push v5.2.2.
2. **LINKED/UNLINKED aggression end-to-end**: verify
   `natural_batting_aggression` caps vs the IPC set paths through the
   match screen striker/bowler aggro rows.
3. Systematic UI sweep of remaining screens (Data Hub, Inbox, Finances,
   Facilities, Youth Academy, Training, Tactics, Press Conference,
   Settings, Help) with the snap harness — same complaint classes
   (overlap, invisible chrome) will exist there.
4. Remaining caller-less IPC (Steam cloud/achievements, custom-tournament
   CRUD, scouting, career timeline/press) — batch into v5.3.0.
5. Legal-names remediation (audit A) before Steam.

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
