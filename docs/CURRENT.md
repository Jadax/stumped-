# CURRENT — cross-agent handoff

Read `AGENTS.md` first; architecture in `docs/ARCHITECTURE.md`; open bugs and
debt in `docs/CODE_AUDIT.md`. This file is volatile state only — keep <200
lines, replace stale content, never append history.

## Snapshot

- **Version:** 5.3.2 (30-season world + Squad CONTRACTS view)
- **Tests:** full suite green (see Validation); Godot smoke all 40 screens
  OK; UI audit 0 issues at 1280x720 and 1920x1080
- **Stack:** Python 3.12 + pygame-ce + pygame-gui backend; SQLite saves;
  Godot 4 client talks to `ipc_server.py` over stdio JSON

## Environment facts (hard-won)

- Python: `"C:\Users\Tushant\AppData\Local\Programs\Python\Python312\python.exe"`
- Godot: `C:\Users\Tushant\Downloads\Godot_v4.7.1-stable_win64.exe`
- Export: `--headless --path C:\Dev\Game\godot_client --export-release "Windows Desktop" C:\Dev\Game\godot_client_dist\StumpedGodot.exe`
- Full pytest runs (~30 min) hang on the PowerShell pipe: redirect to a file.
- Start-Process needs -RedirectStandardOutput/-RedirectStandardError or the
  tool sandbox kills it (Godot GUI runs included).
- **PowerShell Get/Set-Content is UTF-8-hostile**: use Python
  `Path.write_text(encoding="utf-8")` or the edit tools.
- Two agents share this repo — check `git status` before editing.
- UI audit: `--path godot_client -- --ui-audit --res=WxH` (non-headless)
  writes screenshots + report to `screenshots/audit/<WxH>/`; it uses the
  active dev save (`cricket_manager/data/active_save.json`).
- Long-run verification: a day-by-day soak harness (session scratchpad, not
  in repo); a 30-season run takes ~2.5 h.

## v5.3.1 state — long-career ecosystem

- Late careers: `player_development.annual_decline` (role onset: quicks 31,
  batters/keepers 33, spinners 34), `retirement_probability` (age hazard +
  role/quality/club-level/major-injury modifiers), `post_career_role` ->
  staff pool in `game_state['staff_pool']` (`take_from_staff_pool` fills
  vacancies in `age_staff_at_rollover`).
- Squads: `database.manage_ai_squads` (AI_SQUAD_TARGET 26, AI_ACADEMY_MAX 6)
  + `_place_free_agents`; youth ceilings by tier (`YOUTH_TIER_CEILING`);
  market ambition rule + `_ai_make_room`; nationality demonyms
  (`COUNTRY_TO_DEMONYM`, `_normalise_nationalities`).
- AI injuries + best-fit-XI rating: `CompetitionEngine._available_xi`,
  `_ai_match_injuries` (AI_INJURY_CHANCE by format).
- Agents: `src/models/agents.py`, `agents` table, `players.agent_id`,
  `ensure_agents` (init + rollover). Talks: `open_contract_talks` /
  `submit_contract_offer` (state in `game_state['contract_talks_<id>']`,
  28-day lockout). Transfers: `respond_to_user_bids` (daily) +
  `personal_terms_agreed`; IPC refuses accepting your own bid.
- Sponsors: `ensure_sponsorship_deals` (AI), `generate_sponsor_offers` /
  `negotiate_sponsor_offer` / `accept_sponsor_offer` (manager), decision day
  15 Mar, bonuses at rollover. IPC `get_sponsorship`, `negotiate_sponsor`,
  `accept_sponsor`; Godot `scripts/sponsors_screen.gd` (Club > Sponsors).
- Economy (`src/models/club_economy.py`): sponsorship_monthly, facility
  upkeep, scouting cost, central funding net of sponsor/upkeep and capped
  at club costs, AI surplus reinvestment. Forecast mirrors all lines.
- Development: `club_development_factors` (training level + coaches).
- v5.3.2: Squad CONTRACTS view (`ipc_server._with_contract_status`: agent, agency, status incl. talks lockout).

## Next actions (suggested order)

1. Unmanaged-manager cash: an untouched user club still banks gate and
   sponsor profit because it never spends — consider board-driven spending
   or wage-budget pressure if it matters.
2. Visually check the player-profile contract-talks panel (audit does not open modals).
3. Legal-names remediation (audit A) before Steam.

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
