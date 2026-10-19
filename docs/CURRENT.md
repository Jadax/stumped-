# CURRENT — cross-agent handoff

Read `AGENTS.md` first; architecture in `docs/ARCHITECTURE.md`; open bugs and
debt in `docs/CODE_AUDIT.md`. This file is volatile state only — keep <200
lines, replace stale content, never append history.

## Snapshot

- **Version:** 5.1.0 (shipped: packaged exe + release zip + Godot export)
- **Branch:** main — commit v5.1.0 pending push
- **Tests:** 941 passed + 3 new living-world regressions, 1 skipped
  (~18 min; slow DB reseeding per test — see audit item D)
- **Stack:** Python 3.12 + pygame-ce + pygame-gui backend; SQLite saves;
  Godot 4 client talks to `ipc_server.py` over stdio JSON

## Environment facts (hard-won)

- Python: `"C:\Users\Tushant\AppData\Local\Programs\Python\Python312\python.exe"`
- Godot: `C:\Users\Tushant\Downloads\Godot_v4.7.1-stable_win64.exe`
- Export: `--headless --path C:\Dev\Game\godot_client --export-release "Windows Desktop" C:\Dev\Game\godot_client_dist\StumpedGodot.exe`
- Full pytest runs can hang on the PowerShell pipe: redirect to a file
  (`> "$env:TEMP\out.txt" 2>&1`) and read the tail.
- Two agents share this repo — check `git status` before editing; expect
  parallel uncommitted work.

## Season calendar (v4.99.1)

- Careers start **1 March** (pre-season). Four friendly match days:
  1/5/9/13 March, global two-legged pairing schedule (no double-booking).
- Competitive season 1 April – 30 September. Transfer windows Apr–Jun and
  Jul–Aug; deadline drama on each window month's last two days.
- Board review 15 July; season rollover rewinds to 1 March next year.
- International window (v5.0.0): Frank Worrell Trophy (Mar), The Ashes
  (May), Eng–Ind T20I series (Jun), Border-Gavaskar Trophy (Jul); ICC
  windows Apr/Aug/Sep still pause bilaterals.

## Recently shipped (newest first)

- **5.1.0** Godot client wiring: dashboard Fans/Cohesion tiles, League
  Leaders + season-awards screen, Calendar friendlies scheduling,
  pre-match ground facts/stats. All previously caller-less IPC methods
  named in the v5.0.0 handoff now reachable from the Godot client.
- **5.0.0** Living-world wiring: gate revenue for every completed match
  (+ forecast), season prize money, fan reaction to
  trophies/promotion/relegation, stat-ranked season awards, seasonal
  ageing decline, shared training-age curve, free-hit enforcement, no-balls
  as balls faced, DRS energy rollback, exact per-format phase windows,
  persistent behaviour counters (see CHANGELOG). Schema
  stamped `user_version`=5.
- **4.99.1** Audit fixes: cup-final NameError corruption, tied-Cup bracket
  stall, SQL `current_date` quoting, division-CHECK migration gap,
  careers start March (fixes overdue-friendly calendar deadlock), debut-
  century gating, no-ball strike rotation, empty-squad COALESCE.
- **4.99.0** Deadline-day bids create real `transfer_offers` rows.
- **4.98.0** Pre-season friendlies + gate revenue + IPC methods.
- **4.97.0** AI pitch selection; `pitch_used` persisted per match.
- **4.96.0** Media headlines on both match completion paths.
- **4.95.0** Squad cohesion (0–100) with match-rating modifier.
- **4.94.0** League statistics leaders (6 tables).
- **4.93.0** Fan sentiment (0–100) feeding gate demand.

## Next actions (suggested order)

1. **Legal names remediation** (audit A) — generated pools for 100 clubs +
   venues + save migration. Highest risk item; do before Steam release.
3. Deferred v5.0.0: foreign-player limits enforcement, franchise-league
   activation (competition.py ~400), `ui/finances.py` demand formula
   (legacy UI, minor), cash-ledger consolidation.
4. Remaining caller-less IPC methods (verified 18 Oct 2026): mostly
   Steam cloud/achievements, custom-tournament CRUD, scouting
   assignments, career-timeline/press screens — each a small screen or
   modal; batch into v5.2.0.

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
`docs/CURRENT.md` updated + Godot export rebuilt + commit pushed to origin main.
