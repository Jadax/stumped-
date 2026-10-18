# Code Audit Register — 2026-08-24 (updated 2026-10-18)

Full-codebase review findings (three parallel audits: database.py,
competition.py+ipc_server.py, match_engine.py+src/models/). Fixed items are
kept for context; open items are the working backlog. Verify any finding
against current code before acting — line numbers drift.

## Fixed in v5.0.0

- **Auction cash snapshot** (B) — `advance_auctions` keeps the local cash
  snapshot in sync after every bid/sale, so one club can no longer win
  multiple auctions per tick against pre-tick cash.
- **`country_id` positional overwrite** (C) — only NULL/matching rows are
  touched, matched by name; non-native squad members keep their IDs.
- **Ground-stats double-count** (C) — the home-win branch no longer
  increments `home_games` twice.
- **Cohesion lineups missing via IPC** (C) — `_finalise_match` ships
  `lineups` payloads; cohesion failures log at debug instead of swallowing.
- **Powerplay/death windows inconsistent** (C) — one per-format table
  (`POWERPLAY_END_BALLS`/`DEATH_WINDOW_BALLS`) drives weights and phase stats.
- **Free hit never enforced** (C) — enforced: no wicket on the next ball,
  boundary boost; re-arms on another no-ball; no-balls also count as balls
  faced (Laws) with strike rotation already fixed in 4.99.1.
- **DRS overturn leaks side-effects** (C) — batter energy snapshot
  restored on overturn.
- **Gate-demand formula triplicated** (E) — single source
  `fan_sentiment.gate_demand`; forecast now mirrors the actual poster's
  share structure. `ui/finances.py` still legacy (deferred item).
- **`save_game` re-runs the schema migration** (D) — `user_version`
  stamp (5) gates a fast-path save.
- **Rollover date lies in `events["date"]`** (C) — same-day mail restamped
  to the 30 September endpoint after the calendar rewind.
- **Behaviour counters had no writer** — `update_behaviour_counters`/
  `load_behaviour_counters` persist XI-selection and low-morale streaks.

## Fixed in v4.99.1

- **ipc_server `_finalise_match` NameError** — `user_team_id` was used five
  lines before assignment on the cup-final branch; every interactive cup win
  crashed mid-finalisation and each `simulate_balls` poll then re-ran
  finalisation (compounding morale/records/honours).
- **Interactive cup ties stalled brackets** — `record_played_fixture`
  persisted tied Cup matches with no winner; `_advance_cup_if_ready` dropped
  a team. Now coin-flips ties like the AI path.
- **Unquoted SQL `current_date`** — resolved to SQLite's CURRENT_DATE keyword
  (wall clock) at four sites (`forecast_finances`, `add_bookmark`,
  `get_data_hub`, `generate_job_offers`). Quoted as `"current_date"`.
- **Division CHECK migration gap** — legacy saves carrying the old
  `(1,2,3)` constraint were never widened, crashing when world expansion
  inserted Division 4/5 clubs. Rebuild now targets `(1,2,3,4,5)`.
- **Overdue pre-season friendlies blocked the calendar** — careers started
  April 1 while friendlies were generated into March; `advance_day` blocks
  on overdue user matches, permanently stalling day advancement. Careers now
  start **2026-03-01** (config default, DB seed, season-progress bar aligned).
- **Debut-century headline fired for every debut** — now requires the debut
  innings to actually reach 100 runs.
- **No-ball strike rotation** — odd runs off a no-ball now swap striker, as
  ordinary runs and byes already did.
- **Empty squads crashed `simulate_fixture`** — AVG(overall) now COALESCEd.
- **`get_pitch_status` duplicated `get_pitch_options` byte-for-byte** — now
  delegates; both IPC names kept (different client screens).

## Open backlog (priority order)

### A. Legal/compliance — real-world names in seed data
`TEAM_DEFINITIONS` (database.py) contains real county/state/franchise club
names (Lancashire, Yorkshire, New South Wales, Mumbai, **Karachi Kings** — an
actual PSL mark) and `src/models/grounds.py` maps them to real venues (Lord's,
Old Trafford, WACA). This violates the project's own no-real-names rule
(AGENTS.md). Remediation: generated name pools for all 100 clubs + venues +
save migration renaming existing rows. Large, dedicated version required.

### B. Money-integrity bugs
- Cash adjustments bypass `financial_log` at 5 of 6 sites (transfer fees,
  auctions, staff sales, signing bonuses move cash invisibly on the Finances
  screen). Consolidate into one `adjust_team_cash(team_id, delta, ledger)`.

### C. Correctness
- `write_streak_event` and several game_state read-modify-writes span
  multiple transactions (duplicate events possible; pygame UI + Godot IPC hit
  the same DB from separate processes).

### D. Performance
- Test suite ~18 min: ~3 s/test spent reseeding a fresh DB per setUp
  (100 teams × squads + grounds). Shared per-module fixture would cut it hard.

### E. Duplication / dead code (consolidate opportunistically)
- Training-intensity injury multiplier has three conflicting definitions
  (src/models/training.py .55/.9×, database.py live path .72/1.32, dead
  training_schedule.py .65/1.75).
- Weekly-roundup assembly copy-pasted between advance_day and
  `_get_weekly_roundup`; career-stats enrichment triplicated;
  staff-overall calculation triplicated; competition-id lookup repeated ~8x.
- Dead modules never imported anywhere: `training_schedule.py`, `facilities.py`
  (formulas survive as hardcoded copies), `youth.py`. `match_context.py`,
  editors, `achievements.py` break the pure-models convention by hitting SQLite.
- ~32 registered IPC methods have no Godot caller yet — most are deliberate
  API surface ahead of the client (fan sentiment, cohesion, headlines,
  friendlies, custom tournaments…). Genuinely superseded:
  `cycle_match_bowler`, `get_standings`, `get_honours`.

### F. Structure
- `advance_day()` is a ~320-line monolith with 15 responsibilities (and two
  duplicate `day == 1` / two duplicate `weekday() == 0` blocks). Decompose
  into daily/weekly/monthly/transfer/fixture helpers when next touching it.
