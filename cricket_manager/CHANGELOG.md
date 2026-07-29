# Changelog

All notable changes to **Stumped!** are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

## [3.2.0] - 2026-07-29

### Added

- **Improved commentary system.** Commentary cards now have:
  - Left border accent colour (red=wicket, gold=boundary, blue=milestone)
  - Result badge showing run value (0, 1, 2, 3, 4, 6)
  - Better visual hierarchy with header and commentary text
- **30 screens pass smoke test.**

## [3.1.0] - 2026-07-29

### Added

- **Player profile career statistics.** Added career records section to
  player profile modal showing matches played, runs scored, wickets taken,
  batting and bowling averages for each context (League, Cup, International).
- **Player records IPC methods.** Added `get_player_records` and
  `get_player_form` methods for fetching player career data.
- **30 screens pass smoke test.**

## [3.0.0] - 2026-07-29

### Added

- **Emblem editor.** New screen allowing users to customise team emblems/logos.
  - Select from 6 emblem shapes (shield, circle, diamond, hexagon, star, crest)
  - Select from 8 emblem icons (star, lion, eagle, bat, ball, stump, crown, flame)
  - Customise primary and secondary colours
  - Country-specific default emblem configurations
- **Emblem editor backend.** New `src/models/emblem_editor.py` with:
  - `get_team_emblem()`: Get team emblem configuration
  - `set_team_emblem()`: Save team emblem configuration
  - Country-specific default colour palettes
- **Emblem editor IPC methods.** Added `get_team_emblem`, `set_team_emblem`
  methods for Godot client integration.
- **30 screens pass smoke test.**

## [2.9.0] - 2026-07-29

### Added

- **Kit editor.** New screen allowing users to customise team kit colours
  (primary, secondary, accent). Click to cycle through preset colour
  palettes. Kit data stored in game_state table.
- **Kit editor backend.** New `src/models/kit_editor.py` with:
  - `get_team_kit()`: Get team kit configuration
  - `set_team_kit()`: Save team kit configuration
  - `get_all_kits()`: Get all team kits
  - Country-specific default colour palettes
- **Kit editor IPC methods.** Added `get_team_kit`, `set_team_kit`,
  `get_all_kits` methods for Godot client integration.
- **29 screens pass smoke test.**

## [2.8.0] - 2026-07-29

### Added

- **Steam integration methods.** Added IPC methods for Steam achievements
  and cloud saves:
  - `steam_unlock_achievement`: Unlock a specific achievement
  - `steam_get_achievements`: Get all achievements and their status
  - `steam_cloud_save`: Save game to Steam Cloud
  - `steam_cloud_load`: Load game from Steam Cloud
- **Achievement system integration.** The achievement system now works
  with the Steam stubs, allowing achievements to be tracked locally
  and synced with Steam Cloud when available.

## [2.7.0] - 2026-07-29

### Added

- **Attribute polygon (radar chart) in player profile.** New FM-style
  pentagon visualization showing Batting, Bowling, Fielding, Mental,
  and Physical attributes as a filled polygon.
- **Visual comparison.** Player's attribute polygon shows relative
  strengths across all five categories at a glance.
- **AttributePolygon class.** New reusable canvas class for drawing
  radar charts with customizable axes and data.

## [2.6.0] - 2026-07-29

### Added

- **Improved wagon wheel visualization.** Shot lines now have varying
  thickness based on runs scored (thicker for boundaries/sixes). Added
  legend showing run types (1 Run, 2-3 Runs, 4 Runs, 6 Runs, Wicket).
- **Improved pitch map visualization.** Added length zone labels
  (YORKER, FULL, GOOD, SHORT) with colour coding. Added off/leg
  channel labels. Added legend showing delivery types.
- **Fixed record_ground_honour import.** The function was used in
  ipc_server.py but not imported, causing match simulation failures.

## [2.5.0] - 2026-07-29

### Added

- **Field position view.** New canvas mode showing fielding positions
  on a circular field with player position labels (WK, SL, GL, PT, CO,
  MO, LO, LN, MI, MW, SL2, FL).
- **Fielding presets.** Basic fielding position presets for different
  match situations.
- **Stats Hub expansion.** Added "Field Positions" tab to the match
  stats hub for viewing fielding positions during play.

## [2.4.0] - 2026-07-29

### Added

- **Expanded name pools.** All 20+ countries now have 26-32 first names and
  last names for more realistic player generation.
- **Realistic ground names.** Each team now has a realistic venue name
  (Lord's, The Oval, MCG, Eden Gardens, etc.) based on real cricket grounds.
- **Ground capacities.** Realistic stadium capacities for major venues
  (MCG: 100,000, Lord's: 31,000, Eden Gardens: 66,000, etc.).
- **Grounds module.** New `src/models/grounds.py` with realistic venue data
  for all teams.

## [2.3.0] - 2026-07-29

### Added

- **Realistic league structures.** Division 1 now uses County Championship
  names (Lancashire, Yorkshire, Surrey, etc.), Division 2 uses Sheffield
  Shield style (New South Wales, Victoria, Queensland, etc.).
- **Foreign player rules.** Added configuration for foreign player limits
  per division (0 for Division 1, 2 for Division 2, 4 for Division 3, etc.).
- **League format variety.** Each division now uses the correct match format:
  Division 1: Test, Division 2: ODI, Division 3-5: T20.
- **League configuration module.** New `src/models/league_config.py` with
  realistic competition names, formats, and foreign player rules.
- **Fixed round-robin scheduling bug.** The round-robin was generating
  exponentially more matches due to a loop indentation error. Now generates
  the correct number of matches.

## [2.2.0] - 2026-07-29

### Added

- **Expanded to 100 clubs.** 100 teams across 5 divisions with realistic
  league structures:
  - Division 1: 18 teams (elite clubs)
  - Division 2: 18 teams (mid-tier clubs)
  - Division 3: 21 teams (developing clubs)
  - Division 4: 20 teams (lower-tier clubs)
  - Division 5: 21 teams (development clubs)
- **More competitive matches.** With 100 teams and 2 cups, there are
  significantly more fixtures per season.
- **Realistic team distribution.** Teams from 10+ nations including
  Sri Lanka, Bangladesh, Zimbabwe, and more.

## [2.1.0] - 2026-07-29

### Added

- **Realistic player attribute distributions.** Updated `_target_rating`
  to have division-specific skill ranges:
  - Division 1: Elite players (70-95 overall)
  - Division 2: Good players (55-80 overall)
  - Division 3: Decent players (42-65 overall)
  - Division 4: Developing players (35-55 overall)
  - Division 5: Young/developing players (28-45 overall)
- **Role-specific attribute generation.** Batsmen have better batting stats,
  bowlers better bowling stats, all-rounders balanced, wicketkeepers
  have better keeping and reflexes.
- **Realistic age curves.** Players peak at 25-30, decline after 35,
  with realistic skill development and decline patterns.

## [2.0.0] - 2026-07-29

### Added

- **Match page Cricket Captain-style improvements.**
  - Score bug now shows match status with session info (Day 1 Session 2, etc.)
  - Control buttons (Next Ball, Over, Auto, Speed, Skip, Exit) now use
    blue/teal accent colour matching Cricket Captain's theme
  - Tactical buttons (Predict, Field, Aggro, Change, DRS) styled as
    card-based buttons with rounded corners
- **Match status display.** Status bar shows "Day X — Session Y" format
  matching Cricket Captain's match presentation.

## [1.9.0] - 2026-07-29

### Added

- **T20 Cup competition.** Added a second knockout competition (T20 format)
  running alongside the existing ODI Domestic Knockout Cup. Teams now
  compete in both league and two cup competitions per season.
- **More competitive matches.** With 90 teams across 5 divisions and 2 cups,
  there are significantly more fixtures per season.

## [1.8.0] - 2026-07-29

### Added

- **Realistic league structures.** Division names now match real cricket
  competitions: County Championship, One-Day Cup, T20 Blast, Second
  Division, Development League.
- **Match page score bar improvements.** Overs progress bar added to
  show match progress visually. Score format matches Cricket Captain style
  with team name, score, and overs clearly displayed.
- **Competitive roadmap v2.0.** Detailed plan for realistic league
  structures, domestic cups, match page improvements, and realistic
  player stats.

## [1.7.0] - 2026-07-29

### Added

- **Player comparison mode.** New screen to compare two players side-by-side
  with attribute bars, overall/potential ratings, and form/morale chips.
- **Visual comparison.** Each player shown in a card with:
  - Name, role, age, nationality header
  - Overall and potential ratings
  - Batting attribute bars with values
  - Form and morale status chips
- **Navigation.** Accessible from Squad section as "Compare" screen.

## [1.6.0] - 2026-07-29

### Added

- **Expanded to 54 clubs.** 18 teams per division (3 divisions), up from
  36 teams. New clubs include Surrey Sharks, Mumbai Indians, Lahore
  Qalandars, Melbourne Stars, Rajasthan Royals, and more.
- **Balanced league structure.** Each division now has exactly 18 teams
  for fair competition and promotion/relegation.
- **More international diversity.** Teams from 10+ nations including
  Sri Lanka, Bangladesh, Zimbabwe, and more.

## [1.5.0] - 2026-07-29

### Added

- **International fixture integration.** Dashboard now shows upcoming
  international fixtures when managing a national team. Card displays
  up to 3 upcoming matches with teams, format, and date.
- **National fixture database functions.** `get_national_fixtures()`
  returns upcoming international matches for the user's national team.
- **IPC method.** `get_international_fixtures` returns fixtures for the
  user's current national team (if managing one).

## [1.4.0] - 2026-07-29

### Added

- **Match Day score bar redesign.** Team name displayed prominently,
  score in larger font with clear "RUNS/WK (OVERS ov)" format.
- **Commentary cards.** Each delivery now shown in a styled card with:
  - Header: over number, bowler → batter
  - Commentary text with colour-coded border (red=wicket, gold=boundary,
    blue=milestone, grey=normal)
  - Card-based layout replacing flat text labels
- **Improved visual hierarchy.** Score bar shows team name, score, and
  overs more clearly than before.

## [1.3.0] - 2026-07-29

### Added

- **Dual management.** Manage both a club team and a national team
  simultaneously. Accept national team jobs, view squad, see best XI.
- **National team selection.** View full national squad (30 players),
  see auto-selected best XI, and resign from national team job.
- **10 national teams.** England, Australia, India, Pakistan, South Africa,
  New Zealand, West Indies, Sri Lanka, Bangladesh, Zimbabwe — all with
  real player pools from club squads.
- **National team screen.** New Godot screen showing available teams
  (if not managing), current squad and XI (if managing), accept/resign
  buttons.
- **IPC methods.** `get_national_team`, `accept_national_job`,
  `resign_national_job`, `get_international_fixtures`.
- **Database migration.** Added `national_team_id` column to `user_data`.

## [1.2.0] - 2026-07-29

### Added

- **Steam achievements system.** 47 achievements across 5 categories:
  - Career (8): First Victory, Season Survivor, Century Manager, etc.
  - Tactical (10): Hat Trick Hero, Double Century, Five-Wicket Haul, etc.
  - Management (12): Promotion Party, Division One Champion, Cup Glory, etc.
  - Collection (8): Player Collector, International Export, Scouting Network, etc.
  - International (5): International Debut, Ashes Legend, World Cup Hero, etc.
- **Achievements screen.** New Godot screen showing all achievements with
  unlock status, progress counter, and category filtering.
- **Achievement tracking.** `AchievementTracker` class monitors game state
  and unlocks achievements when conditions are met.
- **Cup bracket fix.** Cup seeding now handles any number of teams
  (not just 24) with dynamic bye count and round names.

## [1.1.0] - 2026-07-29

### Added

- **Bilateral tours.** Named international series with specific matchups:
  - The Ashes (ENG vs AUS, Nov, 5-match Test)
  - Border-Gavaskar Trophy (AUS vs IND, Dec, 4-match Test)
  - Freedom Trophy (SA vs IND, Jan, 3-match Test)
  - Frank Worrell Trophy (WI vs AUS, Feb, 3-match Test)
  - Chappell-Hadlee Trophy (NZ vs AUS, Feb, 3-match ODI)
  - Deodhar Trophy (IND vs BAN, Mar, 3-match ODI)
  - T20I Series (ENG vs IND, Jun, 3-match T20)
  - T20I Series (SA vs ENG, Oct, 3-match T20)
- **ICC tournaments.** World Cup (Mar), T20 World Cup (Jun), Champions
  Trophy (Sep) — run at their scheduled months with multiple nations.
- **Player call-ups.** When a user's player is selected for international
  duty, they receive an inbox notification with the player name, nation,
  opponent, and series result.
- **Season-long international calendar.** International cricket now runs
  throughout the season (not just one July window), with tours scheduled
  at their traditional months.

## [1.0.0] - 2026-07-29

### Added

- **Expanded league system.** 36 teams across 3 divisions (12 per division):
  - Division 1: 10 existing + Colombo Stars (Sri Lankan), Dhaka Dominators
    (Bangladeshi), Harare Heroes (Zimbabwean)
  - Division 2: 10 existing + Bristol Blasters (English), Adelaide Attendants
    (Australian), Lahore Lions (Pakistani), St Lucia Strikers (West Indian)
  - Division 3 (new): Hamilton Hurricanes (NZ), Centurion Crusaders (SA),
    Durham Dynamos (English), Chittagong Chargers (Bangladeshi), Bulawayo
    Blitz (Zimbabwean), Dambulla Dynamos (Sri Lankan)
- **3 new nationalities**: Sri Lankan, Bangladeshi, Zimbabwean — with name
  pools, international team IDs, and country aliases throughout.
- **Division 3 promotion/relegation**: 2-up/2-down between D2↔D3, same as
  D1↔D2. Schema migration (`_rebuild_teams_division_if_needed`) handles
  existing saves with `division IN (1, 2)` constraint.
- **Division 3 team generation**: lower cash ranges (1M-3M), lower stadium
  capacity (5K-12K), training level 1, lower target ratings (~42 base).
- **Competitive parity with Cricket Captain 2026**: now 36 teams vs their
  197 (still smaller but 50% more than before, with proper league pyramid).

## [0.99.0] - 2026-07-29

### Added

- **About/Version screen.** New screen showing game version, credits,
  copyright (ASTRAIVA (Pty) Ltd), changelog history, and build info.
  Accessible from Career nav section and Settings screen.
- **Settings page overhaul.** Sectioned layout (Gameplay, Display, Audio,
  Currency, Other) with gold accent headers and separator lines. Added
  "Reset Tutorial" and "About Stumped!" links at bottom.
- **Match Day button styling.** Tactical buttons (Predict/Field/Batting
  Aggro/Bowling Aggro/Change Bowler/DRS) now use card-style boxes with
  rounded corners and hover states. Control buttons (Next Ball/Over/Auto/
  Speed/Skip/Exit) have smaller font for better fit.
- **Competitive roadmap created.** `docs/COMPETITIVE_ROADMAP.md` outlines
  5-phase plan to make Stumped! the best cricket management game on
  Steam (matching Cricket Captain 2026 and Cricket Management 26).

## [0.98.0] - 2026-07-29

### Added

- **FM26-inspired UI overhaul for Godot client.** Full visual refresh
  across all 24 in-career screens:
  - Design system foundation: spacing tokens, card helpers, shadow/elevation,
    tab underline indicators, section header helper.
  - Navigation icons: all 17 nav glyphs increased from 18px to 22px with
    thicker lines; new icon types for Press, Cup, Legends, Offers.
  - Shell redesign: PanelContainer-based header/nav/subnav with proper
    styling; 16px content padding via MarginContainer; section buttons
    show icons inline with text.
  - Dashboard Portal: FM26-style stat tiles (Squad/League/Finances/
    Confidence), card-based layout with gold accent lines on crests,
    improved standings with player-team highlight row.
  - Table screens: gold left-border hover accent, rounded row corners,
    improved header with gold underline, better pill badges with CARD
    text colour.
  - Player Profile: bookmark star button (toggle add/remove), personality
    description display, trait chips via `get_personalities` and
    `get_player_traits` IPC methods.
  - Data Hub: backend query fixed (was querying non-existent columns
    `batting_avg` etc.; now reads JSON columns and computes averages).
  - SubNav buttons use `AppTheme.style_tab_button()` for consistent
    underline indicator active state.
  - Smoke test: all 24 screens pass clean.

### Fixed

- `get_data_hub` backend queried non-existent `batting_avg`, `bowling_avg`,
  `fielding_avg`, `mental_avg` columns. Now reads from `batting_json`,
  `bowling_json`, `fielding_json`, `mental_json` and computes group
  averages from the parsed JSON values.
- Bookmarks screen used `AUTOWRAP_WORD_SMART` without `TextServer.` prefix.
- SubNav button re-parenting: buttons now removed from parent before
  `add_child()` to prevent "already has a parent" errors.
- Dashboard team talk smoke test path updated for new layout tree.

## [0.97.0] - 2026-07-28

### Added

- **Player Personality system.** 10 archetypes (Professional, Maverick, Mercenary,
  Loyalist, Hot Head, Enigma, Leader, Artisan, Showman, Craftsman) each with
  unique morale_mult, form_volatility, pressure_resist, big_match_bonus,
  training_rate, and contract_mod values. Assigned at player generation.
  Personality affects match performance: big_match_bonus in knockout fixtures,
  pressure_resist during high-pressure run chases, and morale_mult on form swings.
  Exposed via IPC `get_personalities` method.

- **Player Traits system.** 10 traits (Powerplay Punisher, Death Specialist,
  Anchor, Nervous Starter, Swing Demon, Death Bowler, Economy Merchant,
  Wicket Taker, Slip Specialist, Gun Fielder) each with phase-specific
  attribute bonuses. 0-2 traits assigned per player at generation. Nervous
  Starter applies a penalty for the first 15 balls. Exposed via IPC
  `get_player_traits` method.

- **Honours Boards (centuries & five-wicket hauls per ground).** New
  `ground_honours` table records every CENTURY and FIVE_WICKETS achievement
  linked to the specific ground where it occurred. Automatic recording after
  live matches (both pygame and IPC flows). Database functions
  `record_ground_honour()`, `get_ground_honours()`, `get_player_honours()` with
  IPC methods. Dedup prevents duplicate entries for the same player/match/honour.

- 11 new tests (personality schema, trait validity, match engine integration,
  honour recording, dedup). 399 total tests pass.

### Changed

- `match_engine.Match._ratings()` now reads `personality` and `traits` from
  player dicts and applies bonuses/penalties by phase and context.
- `database.generate_player()` now assigns a random personality and 0-2 random
  traits to every newly generated player.
- `database.py` SCHEMA includes `personality` and `traits` columns on `players`
  table and `ground_honours` table with indexes.

## [0.96.0] - 2026-07-28

### Added

- **Grounds Department upgrades now physically affect ground characteristics.**
  Level 3+ repaves slow outfields to medium; level 5 upgrades to fast outfield
  and expands boundary to 80m. Stadium upgrades sync capacity to the `grounds`
  table automatically.
- **Home advantage from grounds facility.** Higher `grounds_level` gives the
  home team a subtle batting and bowling bonus in `_weights()`, reflecting
  better pitch preparation and familiarity.
- `_sync_ground_with_upgrades()` in `database.py` called automatically when a
  Grounds Department or Stadium upgrade completes.
- 8 new tests (6 facility upgrade + 2 home advantage). 388 total tests pass.

### Changed

- `Match._weights()` now applies up to +1.5 ones, +0.6 twos, +0.4 fours for
  home batters, and +1.0 wickets / +0.8 dots for home bowlers at max
  `grounds_level` (5).

## [0.95.0] - 2026-07-28

### Added

- **Session-by-session Test match analysis.** `InningsState.session_data` records
  runs, wickets, overs, and run rate at each Test day/session boundary. Exposed
  on `scorecard()` as `session_data` list.
- **Limited-overs phase tracking.** `InningsState.phase_data` records score/
  wickets at powerplay/middle/death phase transitions for T10/T20/Hundred/ODI.
  Exposed on `scorecard()` as `phase_data` list.
- **Key moments timeline.** `Match.key_moments()` extracts wickets, milestones
  (FIFTY/CENTURY/partnership), and boundaries (FOUR/SIX) from commentary.
  Added to `to_dict()` output for client-side timeline display.
- **Ground-specific statistics.** New database function `get_ground_stats(team_id)`
  returns average score, win percentage, and win% batting first from completed
  matches. New IPC method `get_ground_stats`.
- **Player form indicator.** New database function `get_player_form(player_id, last_n=5)`
  returns a 1-10 form rating averaged from recent `player_form_history` entries.
  New IPC method `get_player_form`.
- 8 new analytics tests. 380 total tests pass.

### Changed

- `Match._update_match_clock()` now records session snapshots for Tests and
  phase transitions for limited-overs matches.
- `Match.to_dict()` now includes `key_moments` alongside commentary.

### Added

- **Ground/stadium detail system.** New `grounds` table (team_id, stadium_name,
  city, capacity, boundary_size, outfield_speed, pitch_affinity) with seed data
  generated for every team. 2 new database functions: `get_ground_info()` and
  `get_match_ground_details()`, plus `get_ground_info` / `get_match_ground_details`
  IPC methods. Ground characteristics now mechanically affect match outcomes via
  `match_engine.py`'s `_weights()` — boundary size influences 4/6 probability,
  outfield speed influences 2/3 rotation, and pitch affinity (pace/spin/balanced)
  tilts the contest toward fast or spin bowlers. Ground info is passed from both
  `ipc_server.py` and `competition.py` when creating a `Match` instance.
  13 new ground-specific tests.
- **Commentary template expansion (2-3×).** Dot ball pool: 6→20 variants. Single
  pool: 5→18 variants. Two pool: 4→12 variants. Three pool: 3→8 variants. Four
  shots: 15→25 variants. Six shots: 10→17 variants. Wicket commentary: bowled
  4→10, caught 4→11, lbw 3→7, stumped 3→6, run out 3→6 lines.
- **Partnership landmarks.** `_maybe_partnership_landmark()` reports 50-run
  partnership milestones and century partnerships as they are reached (both
  during play and at wicket fall).
- **Test session wrap-up commentary.** `_session_wrapup()` and
  `_format_session_name()` produce "End of Day X, Morning/Afternoon/Evening
  Session" bulletins when Test match sessions change, with score and run rate.

### Changed

- `seed_database()` now calls `_ensure_grounds_for_all_teams()` to generate
  ground records for every club, and the migration path also generates any
  missing grounds on existing saves.
  paragraph content renders correctly — which is how the paragraph-break
  rendering was confirmed, not assumed.

Godot smoke test clean across 3 consecutive runs; new assertions confirm
a cross-topic search term returns results from more than one topic and
that switching topics clears an in-progress search. No backend changes;
359/359 Python tests unaffected.

This closes the "Post-launch UX fixes" initiative (v0.89.0-v0.93.0) —
all 5 issues the user reported after opening the post-revamp build are
now fixed: the Settings/Help chrome bug, the fake Load Game flow, low-
quality portraits/flags, Match Day's tab-gated scorecard, and thin Help
content.

## [0.92.0] - 2026-07-28

### Added

- **Match Day: always-visible batsmen/bowler strip + current/required run
  rate + bowler maidens.** The Cricket Captain reference shows the current
  batsmen and bowler figures at all times; Stumped's scorecard was
  tab-gated (only visible on the BATTING/BOWLING tab, hidden on shot map/
  worm/etc.) — a real structural gap flagged in the plan, not a palette
  issue.
  - New always-visible `LiveStripCard` (`match_screen.tscn`/`.gd`) sits
    below the score bar, outside the tab-gated scorecard row: striker,
    non-striker, and current bowler figures, visible across every stats
    tab. Reuses the batting/bowling scorecard rows already returned by
    `get_match_state` — no duplicate data fetch.
  - New `RatesLabel` on the score bar: current run rate always shown,
    required run rate added once a target is set (chases only, not Test
    matches). Computed client-side from raw ball counts.
  - **Backend**: `match_engine.py`'s `scorecard()` now includes
    `legal_balls`; `ipc_server.py`'s `_match_state()` now includes
    `balls_per_set`/`overs_limit` — needed because run rate can't be
    derived from the formatted "12.3 ov" display string alone (The
    Hundred uses 5-ball sets, not 6), and this was the one small backend
    addition the plan flagged as possibly necessary.
  - Bowler maidens needed no backend change — `BowlerLine.maidens` was
    already tracked and already flowed through `asdict(line)` into the
    scorecard's bowling rows; the strip's O-M-R-W figures just needed to
    read the field that was already there.
  - Layout note: the score bar's fixed height (56px) didn't actually fit
    a 4th line once RatesLabel was added — caught via screenshot review,
    not by the smoke test's boolean assertions, since the text still
    "existed" just visually overlapping/clipped. Bumped to 78px and
    shifted every fixed-offset node below it down to match.
  - 1 new backend test (`test_match_state_exposes_balls_per_set_overs_limit_and_legal_balls_for_run_rate`,
    359 tests total); new smoke-test assertion in `_exercise_stats_hub`
    confirms the strip stays visible and populated (not the placeholder
    "0.0-0-0-0") across every tab switch. `_run_screenshot_test()` now
    also captures a live in-progress match (`godot_match_live.png`), not
    just the pre-match view — the only way this version's overlap bug was
    actually caught.

No pitch/fielder-position graphic overlay on commentary — explicitly out
of scope per the plan (would need new backend fielding-position data the
match engine doesn't currently track).

Godot smoke test clean across 3 consecutive runs against a genuinely
fresh save. 359/359 Python tests pass.

## [0.91.0] - 2026-07-28

### Changed

- **Gradient-shaded player portraits.** The user flagged portraits and
  flags as low quality and asked for something closer to hand-painted
  layered art. There's no external art tool available and this project's
  no-real-photos policy stands, so this delivers the achievable version
  of that ask: `player_portrait.gd`'s every major shape (jaw/face, hair,
  bust/kit) now fills via a real per-vertex gradient (`draw_polygon()`
  with a computed colours array) instead of a single flat
  `draw_colored_polygon()` fill — a directional light model (soft
  highlight toward the upper-left, shadow toward the lower-right, same
  convention across every shape) replaces the old flat-fill-plus-a-few-
  translucent-overlay-ellipses approximation, so portraits read as shaded
  volumes instead of flat cartoon cutouts. Still fully procedural,
  original, stylized art — a real step up in rendering quality, not
  photorealism (said plainly, not oversold).
  - New shared helpers `_shaded_colours()`/`_draw_shaded_polygon()`/
    `_draw_shaded_ellipse()`; the old flat `_draw_ellipse_fill()` stays
    for tiny elements (skin pores, stubble) where a gradient would be
    imperceptible.
  - 2 new hairstyles (cropped/textured, long with a side part) alongside
    the original 5, using the same shaded-fill helpers — a modest variety
    bump since the layer split made it cheap, not the core focus of this
    version.
  - One real bug caught mid-implementation: the new asymmetric side-part
    hairstyle's hand-built concave polygon was self-intersecting and
    crashed Godot's triangulator (`canvas_item_add_polygon`) — replaced
    with two offset gradient-shaded ellipses (always simple/convex, so
    triangulation can't fail), same asymmetric silhouette.
- **Flags re-exported at higher fidelity.** The 19 flag PNGs
  (`assets/images/flags/*.png`) were 80×48 2-bit indexed images —
  genuinely low-res, visibly aliased next to any other UI element. New
  one-off dev tool `godot_client/tools/upscale_flags.gd`
  (`godot --headless --script godot_client/tools/upscale_flags.gd`, not
  part of any shipped build path) re-exports the same 19 source flags at
  160×96 (5:3 ratio) in full RGBA8 with Lanczos interpolation — same
  flags, no new designs, just a proper anti-aliased upscale.

Godot smoke test clean across 3 consecutive runs against a genuinely
fresh save. 358/358 Python tests pass (Godot-only visual change, no
backend surface touched). Verified primarily via `_run_screenshot_test()`
screenshot review (Squad list, hover card, profile modal) rather than
smoke-test assertions, since this is a rendering-quality change with no
functional state to assert against.

## [0.90.0] - 2026-07-28

### Added

- **Real multi-save-slot system.** Previously "Load Game" just called
  `show_screen("Dashboard")` — it re-entered whatever the single existing
  database held, because no save-slot concept existed anywhere: one
  `DEFAULT_DATABASE_PATH`, one file per install.
  - **New backend module `saves.py`**: each save is its own SQLite
    database under `<writable_root>/saves/<id>.db` (created via the
    existing `initialise_database()`, unchanged, so every save starts from
    the same seeded world), tracked in a small `saves/manifest.json`
    storing only what can't be read live (id, display name, creation
    time). Team/manager/date shown in a save listing are always read live
    from that save's own database — never duplicated into the manifest —
    so a listing can't drift from what the save actually contains.
  - **`ipc_server.py`**: new `list_saves`, `create_save`, `load_save`,
    `delete_save` IPC methods. The key architectural finding that made
    this tractable without a server restart: `build_context()`'s
    `database_path` was already read fresh on every call via `_db(ctx)`,
    and `ctx` is one shared dict for the life of the process — so
    switching saves is just mutating `ctx["database_path"]` in place plus
    reloading the database-derived state (`game_data`/`team`/`players`/
    `game_controller`), factored out into a new shared `_bind_database()`
    helper used by both `build_context()` and the new save-switching
    methods.
  - **Migration**: `saves.migrate_legacy_save()` copies (not moves —
    nothing destroyed) an existing install's pre-v0.90.0 single
    `data/cricket_manager.db` into `saves/save-1.db` as "Save 1" on first
    run post-update, so no one's in-progress career disappears.
  - **New Godot screen**: `load_game_screen.tscn`/`.gd` — a real card
    list of saves (team/division/manager/in-game date, read live) with
    CONTINUE and a two-click DELETE (arms to "CONFIRM DELETE?", second
    click actually deletes — no separate modal needed for a single-row
    destructive action). Main Menu's LOAD GAME button now navigates here
    instead of straight to Dashboard.
  - **`main_menu_screen.gd`**: NEW GAME now calls `create_save` first, so
    it always starts a genuinely new save slot instead of reconfiguring
    whatever save happened to be active (previously "New Game" really
    meant "overwrite the current career's manager identity", since there
    was only ever one database).
  - 14 new backend tests (`tests/test_saves.py`): manifest/slug/create/
    delete logic, live-read metadata, legacy-save migration (including
    the no-op-once-migrated case), active-save fallback when the marked
    save no longer exists, and the four new IPC methods including the
    "can't delete the save currently in progress" guard. 358 tests total.
  - New smoke-test exercise `_exercise_save_slots`: creates a throwaway
    save via the same IPC method the UI uses, confirms it appears in a
    real Load Game screen list, deletes it via two real DELETE button
    presses, confirms it's gone, and restores the save the startup-flow
    exercise had made active so every exercise after it still runs
    against a valid career.

### Fixed

- Caught during screenshot review: the new Load Game screen's division
  column showed "Division 1.0" (the same raw-JSON-float display bug this
  project already has a fix pattern for) — routed through the existing
  `JsonFormat.value()` helper.

Godot smoke test clean across 3 consecutive runs against a genuinely
fresh save (correct `saves/` reset path this time — the writable root
for an unpackaged run is `cricket_manager/` itself, not
`cricket_manager/data/`, since `launcher.py`'s `get_launch_paths()` sets
`base == resource_root` when not frozen; noted here since the dev-save
gotcha note above only covered the single legacy database file before
this version). 358/358 Python tests pass.

## [0.89.0] - 2026-07-28

### Fixed

- **Settings/Help showed full in-game chrome (header + sidebar with real
  team/fixture data) even when reached from Main Menu before any career
  was active.** Root cause: `shell.gd`'s `STARTUP_SCREEN_NAMES` (the list
  that suppresses header/sidebar) didn't include `"Settings"`/`"Help"`, so
  `show_screen()` left the game chrome visible for them regardless of
  entry point. Both are now always chrome-less.
- **No way to access Settings/Help, or quit/return to Main Menu, from
  inside an active career.** `shell.gd`'s sidebar gets a new footer block
  (below the existing nav groups, not part of them — the smoke test's
  per-group loop is unaffected) with Settings, Help, and "Quit to Main
  Menu" entries, each with a new hand-drawn `nav_icon.gd` glyph
  (gear/question-mark/door). Quit is a plain `show_screen("Main Menu")` —
  no explicit save step needed since every mutation already writes
  straight to SQLite.
- `settings_screen.gd`'s Back button is now context-aware: returns to
  Dashboard if a career is active (`get_dashboard` returns a team),
  Main Menu otherwise — previously always went to Main Menu even
  mid-career.

### Changed

- **Real dropdowns, not click-to-cycle buttons.** Game Speed, Resolution,
  Currency, and Auto-save on the Settings screen were custom "click to
  cycle through options" buttons reading like a debug form — replaced
  with real Godot `OptionButton` dropdowns (`_add_dropdown_row`), styled
  via `AppTheme`'s existing `field_box`/`field_focus` StyleBoxFlat
  (already wired for `OptionButton` in `build()` since Part 1, just never
  used by an actual `OptionButton` node until now). Binary toggles
  (Crowd Sound, Reduced Motion, Colour-blind Glyphs) and the volume
  slider/UI-scale cycle stay as-is — a dropdown adds nothing there.

### Added

- New smoke-test coverage: `_exercise_settings_back_context` (real
  Button.pressed emit, confirms Back lands on Dashboard when a career is
  active), `_exercise_quit_to_menu` (real Button.pressed emit on the new
  sidebar footer button, confirms it lands on Main Menu with chrome
  hidden). `_exercise_settings` updated for the dropdown's
  `OptionButton.selected`/`item_selected` interaction instead of a cycle
  button's `.text`/`.pressed`.

Godot smoke test clean across 3 consecutive runs against a genuinely
fresh save (one unrelated pre-existing flake on the
batting-order-swap step reproduced once under accumulated multi-run
save state, not on a clean run — matches this project's documented
stale-save flakiness pattern, not a regression). 344/344 Python tests
pass (Godot-only change, no backend surface touched).

## [0.88.0] - 2026-07-28

### Added

- **UI/UX revamp part 3, v3: Domestic Knockout Cup bracket tree.** No
  bracket-tree visual existed anywhere in either client before this —
  confirmed by research this session (grepped every pygame `ui/*.py`
  file, zero matches) — and the only bracket-shaped backend endpoint
  (`get_tournament_bracket`) covered the separate, in-career "custom
  tournament" system, not the main season-long Cup every save has
  automatically. That system is explicitly flagged elsewhere in
  `docs/CURRENT.md` as needing a product decision before more UI
  investment goes into it, so this deliberately targets the main Cup
  instead — unblocked, and the one every player actually sees.
  - **New backend**: `database.py`'s `get_cup_bracket()` groups the
    current season's `type='Cup'` competition's matches by `round_name`
    (`Round of 32` → `Round of 16` → `Quarter-final` → `Semi-final` →
    `Final`, mirroring `CompetitionEngine._advance_cup_if_ready`'s
    existing next-round mapping in `competition.py`), resolving team ids
    to names and a winner from each match's `result_json`. Wired up as
    the new `get_cup_bracket` IPC method.
  - **New Godot screen**: `tournament_bracket_screen.tscn`/`.gd` — a
    horizontally-scrolling row of round columns, each a vertical stack
    of match-box cards (home vs away, runs once completed, winner
    highlighted gold), auto-scrolling to the most advanced round.
    Reference: the Cricket Captain "20 Over Trophy" bracket screenshot.
    Added to the CAREER nav group as "Cup".
  - 4 new backend tests (`tests/test_cup_bracket.py`): empty-state
    reporting, Round of 32 population with resolved names, Round of 16
    auto-generation after simulating Round of 32, and IPC JSON-safety.
    344/344 tests passing (up from 340).
  - This closes UI/UX revamp Part 3 — all three gaps the user identified
    (Match Day, setup screens, tournament brackets) now have real,
    screenshot-verified work behind them instead of unchecked "reviewed,
    no changes needed" claims.

## [0.87.0] - 2026-07-28

### Added / Fixed

- **UI/UX revamp part 3, v2: setup screens, actually checked this time.**
  Part 1 claimed the pre-career setup screens (Main Menu, New Game Setup,
  Career Team Selection, Tournament Setup, World Cup Setup) only got a
  background/text colour swap — true, but static-source research alone
  couldn't say whether the shared `AppTheme.build()` Theme cascade
  already styled them well at runtime regardless. It does, mostly: these
  screens are not in `shell.gd`'s dev-only `_run_screenshot_test()`
  target list (only in-career screens were), so this version extends
  that list and actually looks at the PNGs before touching anything —
  and most of these screens turned out already well-styled (card
  chrome, gold-bordered selected-state toggle buttons) via the Theme
  cascade. Two real, confirmed-by-screenshot issues found and fixed:
  - **Career Team Selection club rows were plain text**
    (`career_team_selection_screen.gd`): `"Kingston Kings Div 1 • OVR
    75.2 • £14,750,000"` with no visual identity. Added the same
    initials-badge crest circle already used in `shell.gd`'s header and
    the Dashboard's fixture card — reused, not a new asset.
  - **A real formatting bug, not just cosmetic**: Division/Squad size/
    Stadium/Training level were displaying `"Div 1.0"`, `"25.0"`,
    `"30500.0 seats"`, `"Level 3.0"` — raw JSON floats never routed
    through the project's own `JsonFormat.value()` helper (which exists
    exactly for this — "JSON numbers arrive as float," per its own
    docstring — and is already used elsewhere). Fixed at all four
    call sites.
  - **`LineEdit`/`OptionButton` had never been styled at all** —
    `AppTheme.build()` only ever covered `Label`/`Button`/
    `PanelContainer`/`ScrollContainer`, so New Game Setup's manager-name
    text field rendered as the engine's unstyled grey default box, a
    visible sore thumb next to every other now-styled control. Both
    control types now match the established card/border language.
  - Tournament Setup / World Cup Setup reviewed and confirmed already
    correctly styled (gold-bordered selected state) — no changes needed,
    this time verified by screenshot rather than assumed.
  - 340/340 tests passing (no backend surface touched this version).

## [0.86.0] - 2026-07-28

### Added

- **UI/UX revamp part 3, v1: Match Day tabbed scorecard + bowler stamina.**
  The user asked directly whether Match Day actually matches the Cricket
  Captain reference screenshots — honest answer at the time: no, it had
  only inherited the new palette, not any structural change. This closes
  that gap for the scorecard specifically.
  - **Batting/Bowling/Summary tabs** replace the old always-both-visible
    side-by-side scorecard (`match_screen.gd`'s `Row` used to show
    `BattingCard` and `BowlingCard` simultaneously). Reuses the existing
    `stats_tab_bar` tab mechanism and `_render_scorecard`'s row-building
    logic unchanged — just gates which card is visible per tab. New
    **Summary** tab shows each innings' score/wickets/overs and total
    extras, from data `match_engine.Match.scorecard()` already returns.
  - **Bowler stamina bar**: the reference's bowler card shows a Stamina
    meter this client had nothing equivalent to. `players.fatigue`
    (already tracked, already recovered via `recover_daily_fatigue()`)
    is now included on `_match_state()`'s `"bowler"` dict in
    `ipc_server.py` (previously id/name only) and rendered as a bar meter
    (via `AppTheme.make_bar_meter()`, added v0.85.0) in the Bowling tab.
  - Existing visualisation tabs (shot map, pitch map, worm, Manhattan,
    momentum, partnerships) are unchanged — kept as separate full-width
    tabs rather than rebuilt as embedded per-card widgets, a much larger
    restructure for proportionally little gain over what's already there.
  - Smoke-test coverage (`shell.gd`'s `_exercise_stats_hub`) extended
    with real button-signal-emit checks for all three new tabs (was
    exercising the now-renamed `ScorecardTab`, which would have broken
    silently otherwise). 1 new backend test (`test_ipc_server.py`) covering
    the new `fatigue` field. 340/340 tests passing (up from 339).

## [0.85.0] - 2026-07-28

### Added

- **UI/UX revamp part 2: reference-driven component polish**, building on
  v0.84.0's new light theme.
  - **Player profile modal** (`player_profile_modal.gd`/`.tscn`): a new
    status-chip row (FORM/FITNESS/MORALE, tier-coloured borders) sits
    between the header and the attribute groups — mirrors the Football
    Manager reference screenshot's Happiness/Fitness/Form/Discipline chip
    row. Previously the full profile modal showed overall/potential and a
    full attribute breakdown, but no form/fitness/morale at all, despite
    the smaller hover card already surfacing all three — a real parity
    gap, not just a visual one.
  - **Shared bar-meter helper**: `AppTheme.make_bar_meter()` and
    `AppTheme.make_status_chip()` are new. The horizontal progress-bar
    meter (track + tier-coloured fill + number) used for every 0-100 stat
    was independently duplicated three times (`table_screen.gd`'s
    `_make_bar`, `player_profile_modal.gd`'s `_attribute_row`, and
    `player_hover_card.gd`'s `_set_bar`) — the first two now call the one
    shared builder (`_make_bar` is a 1-line wrapper; `_attribute_row`'s
    20-line inline construction is gone). `player_hover_card.gd`'s
    `_set_bar` populates pre-declared scene nodes rather than building
    its own, a different enough shape that forcing it onto the shared
    helper wasn't worth the awkward fit — left as-is.
  - **Dashboard/Portal**: each of the three cards (Next Fixture, League
    Standings, Inbox) gained a gold underline beneath its header label —
    the same visual language as v0.84.0's new table-header treatment,
    giving the Portal's cards a crisper, more defined boundary between
    header and content.
  - **Match Day**: reviewed, no changes needed — `match_screen.gd`'s
    commentary colour-coding and `match_stats_canvas.gd`'s pitch-map
    already reference `AppTheme` tokens directly (or are deliberately
    theme-independent grass/pitch colours), so both inherited the new
    light palette automatically from v0.84.0's `app_theme.gd` change.

## [0.84.0] - 2026-07-28

### Fixed

- **Two real Godot layout bugs**, found by diagnosing a user-reported
  overlapping-text screenshot with `shell.gd`'s dev-only
  `_run_screenshot_test()` tool (headless mode can't capture real
  screenshots — the dummy renderer's `get_viewport().get_texture()`
  returns null — this needed a real windowed run):
  - **Onboarding tutorial card text was fully overlapping itself.**
    `onboarding_overlay.tscn` had `Title`/`StepLabel`/`Description`/
    `Buttons` as direct children of `Card` (a `PanelContainer`) instead of
    inside the `Box` `VBoxContainer` sibling that existed but was never
    populated — `PanelContainer` stacks all children filling the same
    rect rather than laying them out vertically, so every line of the
    tutorial card rendered on top of every other line. Fixed by moving
    them into `Box` and updating `onboarding_overlay.gd`'s `@onready`
    paths.
  - **The sidebar nav overlapped the header.** `shell.tscn`'s `Sidebar`
    (a `VBoxContainer`, `grow_vertical = 2`/GROW_BOTH, fully anchored to
    its parent) now holds 6 nav groups / ~21 items — its actual content
    height (952px) exceeds the available sidebar area (648px at 720p).
    With `grow_vertical` set to GROW_BOTH, Godot expands an over-full
    anchored `Control` symmetrically from its center, pushing the top
    edge up past y=0 into the 72px header — invisible in normal play
    because the opaque header simply painted over it, but exposed the
    instant anything (the onboarding veil) made either layer
    semi-transparent. Root-caused with a temporary debug print of live
    `get_global_rect()` values (`Sidebar: [P: (0.0, -80.0), ...]`), not
    guesswork. Fixed properly, not just symptomatically: wrapped the
    sidebar content in a real `ScrollContainer` (`shell.tscn`'s new
    `SidebarScroll` node) — bonus fix, this also means every nav group is
    now actually reachable by scrolling; before this, the ~300px of
    overflow meant several items (Legends, Club Records, Press
    Conference, ...) were silently unreachable off the bottom of the
    sidebar with no scrollbar at all.

### Added

- **UI/UX revamp part 1: warm light theme.** Replaces the prior "Test at
  Dusk" near-black dark theme outright (a straight swap, not a toggle —
  no runtime theme-switching mechanism exists in this client, and none
  was built for this). Every named constant in `app_theme.gd`
  (`BACKGROUND`/`SURFACE`/`CARD`/`TEXT_PRIMARY`/etc.) repainted to a
  warm, cream, cricket-ground-inspired palette; `attribute_colour()`'s
  mid tier now uses a new dedicated `NEUTRAL` constant instead of
  reusing `TEXT_PRIMARY` (a near-black-vs-near-white swap doesn't survive
  a light/dark repaint if a bar-fill colour and the text colour are
  secretly the same token). The 22 `.tscn` scene files that hand-copied
  the old dark palette's hex values (Godot scenes can't call GDScript, so
  they can't reference `AppTheme.X` directly) were swept and retinted to
  match. Modal/tutorial veils (`onboarding_overlay.tscn`,
  `opposition_report_modal.tscn`, `player_profile_modal.tscn`,
  `main_menu_screen.tscn`) were black at 60-68% opacity, tuned for a dark
  backdrop — against the new light theme this muddied everything
  underneath into illegible gray rather than just receding it, so they're
  now a warm dark-brown tint at 35-45% opacity instead. `table_screen.gd`
  (backs ~15 nav screens) gained a real hover-highlight on every row
  (previously only player rows got any hover feedback at all, via the
  floating hover card) and a gold underline separating the header row
  from data rows.
- Verified via `_run_screenshot_test()` visual review across all 19
  in-career screens plus the onboarding overlay, not just automated
  smoke-test title-text checks.

### Known issues

- `test_simulate_balls_advances_the_live_match_and_can_run_it_to_completion`
  is flaky (unseeded live-match RNG occasionally produces 2 ball-events in
  one `simulate_balls(count=1)` call) — confirmed unrelated to this
  release (Godot-only change) by re-running in isolation 3x, all green.
  Not investigated further this release; noted for whoever picks up
  Phase-9-adjacent stability work next.

## [0.83.0] - 2026-07-28

### Fixed

- **Long-save stability, Phase 8 of the "best-in-class Steam cricket
  manager" roadmap**: no multi-season stress test existed before this —
  season-boundary logic (`rollover_season`, `recruit_youth`, retirement)
  had only ever been tested one or two seasons at a time. A new 20-season
  headless stress test (`tests/test_long_save_stability.py`) immediately
  found a real bug:
  - **Unbounded squad growth**: `rollover_season()` called
    `recruit_youth(team_id, count=3)` unconditionally every season with
    no size check. A 20-season simulation took a 25-player squad to
    **59** — real clubs stop signing academy prospects once the squad is
    full, but this one never did. Fixed with a new
    `CompetitionEngine.SQUAD_SIZE_CAP = 30`: intake is now clamped to the
    room actually available (`min(3, cap - current_size)`), verified to
    genuinely *plateau* at the cap (not just grow more slowly) across 40
    simulated seasons in manual verification, with the existing
    retirement-at-45 conveyor keeping turnover healthy at the ceiling.
  - Everything else checked out: no DB corruption (`PRAGMA
    integrity_check` clean after 20 seasons), no orphaned `player_records`
    or dangling `team_id` references despite hundreds of retirements/
    releases, `legends`/`season_records` accumulate correctly (one row
    per season, no duplicates), and a full year of real day-by-day
    `advance_day()` calls (not just season-boundary jumps) stays bounded
    and healthy too.
  - 7 new tests. 339/339 passing (up from 332).

## [0.82.0] - 2026-07-28

### Added / Fixed

- **Realism tuning, Phase 7 of the "best-in-class Steam cricket manager"
  roadmap**: still entirely procedural/fictional (no real player names or
  data — see "Decisions made" in `docs/CURRENT.md`), but three
  distribution/content gaps found by research are tightened.
  - **Per-team squad-strength variance within a division**
    (`database.py`'s new `_team_quality_modifier`): previously every club
    in Division 1 (or 2) shared one identical target-rating distribution
    — Manchester Mavericks and Birmingham Bears, both D1, were
    statistically indistinguishable. Now a club's own randomised cash
    (already rolled per-team at seed time) becomes a small ±5-point
    offset on `_target_rating`'s baseline, so richer clubs within a
    division statistically field stronger squads — reusing the existing
    finance-depth theme rather than inventing a separate reputation stat.
  - **Realistic youth-intake curve** (`database.py`'s new
    `_youth_current_and_potential`, replacing flat `randint(20,50)`/
    `randint(40,85)` rolls in `recruit_youth`): potential is now mostly
    average with a deliberately tiny elite tail (≥1% chance of 88-97,
    ≥5% of 78-87, otherwise a bell curve around ~50-60 shifted by academy
    level) — mirroring `_target_rating`'s existing tail-probability
    pattern instead of a structurally different, much flatter curve
    living in the same file. Potential can never fall below current
    ability.
  - **Expanded name pools** (`src/data/names.json`): the 8 smallest
    associate-nation pools (Netherlands, Scotland, USA, UAE, Nepal, Oman,
    Namibia, Papua New Guinea) grew from 8/8 first/last names to 14/14;
    mid-tier nations (Sri Lanka, Bangladesh, Afghanistan, Zimbabwe,
    Ireland) from 10/10 to 14/14; the 7 "home" nations used for 76% of
    each club's roster (England, Australia, India, Pakistan, South
    Africa, New Zealand, West Indies) from 12/12 to 16/16 — reducing the
    numeric-suffix collision fallback (`"James Smith 2"`) that a large
    save was likely to hit.
  - **Removed dead code**: `src/data/countries.json`'s duplicate
    `first_names`/`last_names` arrays (used only for UI country metadata,
    never actually read by name generation — confirmed via a full-repo
    grep) and `src/models/player_generation.py`'s orphaned
    `realistic_rating()` (a near-duplicate, never-called twin of
    `database.py`'s `_target_rating` with a slightly different curve —
    a second source of truth nobody was maintaining).
  - 8 new tests (team-quality-modifier bounds and statistical spread,
    youth-potential tail shape, seeded-world integration) — 332/332
    passing (up from 324). Match-engine statistical validation
    re-verified stable after the world-generation changes (T20 ~6.9 RPO,
    ODI ~4.99, Test ~3.93).

## [0.81.0] - 2026-07-28

### Added

- **Team talks + press conferences, Phase 6 of the "best-in-class Steam
  cricket manager" roadmap**: zero code existed for either before this —
  board/squad confidence only ever moved via passive events (match
  results, contracts, promotion/relegation, the once-a-season board
  review). These are the first manager-driven interactions.
  - **Team talks** (`src/models/team_talks.py`, `deliver_team_talk`): a
    manager picks one of three pre-match tones — Calm (reliable, modest),
    Assertive (measured risk), Aggressive (higher risk, can genuinely
    backfire) — each rolling a whole-squad morale swing within a declared
    range. New `get_team_talk_status`/`deliver_team_talk` IPC methods,
    gated to once per matchday (`game_state` key
    `team_talk_last_date_<team_id>`). New tone-picker widget on the Godot
    Dashboard's fixture card.
  - **Press conferences** (`src/models/press_conference.py`,
    `press_conference_question`/`answer_press_conference`): a templated
    question flavoured by league position, four tone responses
    (Confident/Diplomatic/Critical/Humble) with fixed confidence/morale
    deltas. New `get_press_conference`/`answer_press_conference` IPC
    methods, gated to once a week. Feeds directly into the *existing*
    board-confidence history ring (`record_board_confidence`) rather than
    inventing a second confidence value — a press answer now shows up in
    the Board screen's confidence history alongside season reviews. New
    Godot **Press Conference** screen (CAREER nav group).
  - 10 new tests (pure-function tone/delta bounds, IPC gating, morale/
    confidence round-trips) — 324/324 passing (up from 314).

### Fixed

- **Corrected a mischaracterisation in v0.80.0's "Known issues" note**:
  the `_exercise_batting_order` smoke-test flakiness was blamed on a
  pre-existing product bug, "confirmed" by resetting the wrong dev-save
  path (`%LOCALAPPDATA%\Stumped`, which only the *packaged* .exe uses)
  before re-running against the base commit — the unpackaged dev run
  actually reads/writes `cricket_manager/data/cricket_manager.db`
  directly (see `launcher.py`'s `get_launch_paths`: `base == resource_root`
  when not frozen), so that "fresh save" was actually the same
  long-accumulated save the whole time. Resetting the *correct* path
  makes the batting-order step pass cleanly across 3 consecutive runs —
  there was no product bug, just a stale test save. No code changes
  needed; noted here so the next agent doesn't have to rediscover this.

## [0.80.0] - 2026-07-28

### Added

- **Trophy room + historical stats, Phase 5 of the "best-in-class Steam
  cricket manager" roadmap**: the trophy cabinet was a bare flat list
  (pygame's `ui/career.py` showed only the last 12 entries; Godot's
  version had no cap but no structure either), and there was no
  season-indexed stats archive at all — `player_records` is career-
  cumulative only, so "who was our top scorer this season" had never
  been answerable.
  - **`get_trophy_room` IPC method** groups the same `fetch_honours` rows
    by competition title into counts + seasons-won, alongside the full
    flat list. New Godot **Trophy Room** screen (`trophy_room_screen.gd`)
    replaces the old flat Honours table, showing both views side by side.
  - **New `season_records` table** (`database.py`): one row per club per
    season, written at rollover — league position, W/L, and that
    season's leading run-scorer/wicket-taker. Computed by
    `CompetitionEngine._record_season_stats`, which diffs each squad
    player's cumulative `player_records` totals against a baseline
    snapshot taken at the *previous* rollover (stored in `game_state`) —
    avoids touching every match-recording call site just to tag
    performances with a season number.
  - **`fetch_club_records`** (`database.py`) derives all-time club bests
    (highest team score, biggest win margin, heaviest defeat) live from
    `matches.result_json` — no dedicated table needed, club history is
    small enough to scan directly on each request.
  - New Godot **Club Records** screen (`season_records_screen.gd`) shows
    both: all-time bests on the left, season-by-season leaders on the
    right (via new `get_season_records`/`get_club_records` IPC methods).
  - 6 new Python tests (season-leader computation, baseline-diff
    correctness across two seasons, club-records computation, IPC
    grouping/JSON-safety) — 314/314 passing (up from 308).

### Known issues

- `shell.gd`'s `_exercise_batting_order` smoke-test step is flaky against
  a freshly generated dev save (confirmed pre-existing on v0.79.0 via
  `git stash`, not a Phase 5 regression) — tracked separately, does not
  block this release since the new Trophy Room/Club Records screens are
  unaffected and pass cleanly in every run.

## [0.79.0] - 2026-07-27

### Added / Fixed

- **Retirement realism + legends archive, Phase 4 of the "best-in-class
  Steam cricket manager" roadmap**: `competition.py`'s `rollover_season`
  used to hard-delete any player with `age>40 OR overall<20` — a blunt
  cutoff, no archive, no way to ever see a former player again, and no
  path to becoming staff. Replaced with:
  - **A real age-curve retirement probability**
    (`CompetitionEngine._retirement_probability`): negligible before 33,
    rising through the late 30s, effectively certain by 44, hard-forced
    at 45 (the `players.age` column's own CHECK constraint caps there,
    so this one case must never be left to chance). `overall<20` is now
    a distinct **release** path — a club letting a player go, not a
    personal retirement decision — tracked separately (`reason` column).
  - **A legends archive** (`database.py`'s new `legends` table,
    `record_legend`/`fetch_legends`): every retiring/released player is
    snapshotted — identity, final club/overall, retirement age/season,
    and a full career-record snapshot (taken *before* the `players` row
    delete, since `player_records` cascades on that same delete) — before
    removal. Visible but deliberately unsignable: no function reinserts
    a legend into `players`. New Godot **Legends** screen (`shell.gd`'s
    CAREER nav group) lists them via the generic `table_screen.gd`.
  - **Some retirees become staff.** ~15% of retiring players (not
    released ones) convert into a coaching role at their last club
    instead of leaving entirely — real cricket precedent for recently
    retired players moving straight into coaching. Role picked from
    their playing role (Batsman → Batting Coach, etc.), quality scaled
    from their final overall via the existing `generate_staff_member()`.
  - New `get_legends` IPC method.
- **Test coverage added**: `_retirement_probability`'s curve shape,
  retired players actually get archived (not just deleted),
  `overall<20` gets the `released` reason, and `_convert_retiree_to_staff`
  adds a real, correctly-roled `staff` row. The one existing test that
  relied on the old hard age>40 cutoff (`test_rollover_promotes_
  relegates_ages_and_retires`) now sets the veteran to 44 (→45 after the
  rollover's age+1 step), the only age retirement is still guaranteed.
- Verified with a 10-season rollover simulation: retiree counts stayed
  realistic per season, max player age never exceeded 41 across 10
  rollovers (comfortably under the 45 hard cap — confirms the CHECK
  constraint was never at risk), and legends/staff-conversion both
  produced real, correctly-shaped data throughout.
- 304 existing + 4 new tests pass (308 total). Godot smoke test clean
  across 3 runs (19 screens, up from 18 — Legends added).

## [0.78.0] - 2026-07-27

### Added / Fixed

- **Match commentary + line/length depth, Phase 3 of the "best-in-class
  Steam cricket manager" roadmap**: two related upgrades to
  `match_engine.py`.
  - **Commentary variety**: `_run_commentary`/`_wicket_commentary` went
    from exactly one fixed template per outcome (11 total across every
    run value and dismissal type) to weighted pools of 3-6 phrasings each,
    chosen via the match's own seeded RNG (so replays stay deterministic).
    Boundary commentary (fours/sixes) now names a real shot — drives,
    cuts, pulls, flicks, hooks — derived from the actual line/length that
    was bowled (see below), not a generic "drives through cover" no
    matter what happened. Added FIFTY!/CENTURY! milestone callouts,
    previously nonexistent.
  - **Line/length now has a real mechanical effect.** Discovered while
    building shot-aware commentary: `PlayerTactics.preferred_line`/
    `preferred_length` were read every ball (`match_engine.py`) but never
    set anywhere in either client's UI or backend — the "tactical"
    line/length was always the same hardcoded default, and only ever
    affected cosmetic pitch-map dot coordinates, never outcome
    probabilities. Replaced with `_choose_delivery_line_length()`: a real
    per-ball choice (bowlers vary delivery to delivery, not one fixed
    tactic per spell) that's phase-aware (death overs skew toward
    yorkers/full for containment), bowler-control-aware (a low-control
    bowler drifts short more often), and bowling-style-aware (spinners
    drift toward the stumps, seamers channel outside off) — then feeds
    modest, real-cricket-grounded deltas into `_weights()` (yorkers:
    harder to score off but higher wicket risk; short balls: boundary-
    prone via cut/pull/hook but also mistimed-shot risk; a "Good" length
    is the containment length; off-stump lines draw more edges, leg-stump
    concedes more through the leg side).
- Verified via `validate_match_engine.py`: run rates/wickets-per-innings
  stayed realistic and stable (T20 ~6.9 RPO, ODI ~4.98, Test ~3.95 —
  within normal run-to-run variance of the pre-change baseline).
- No existing test hardcoded exact commentary strings or pitch-map
  coordinates (checked before making this change), so nothing broke;
  304/304 tests pass unchanged. Godot smoke test clean across 3 runs
  (Match screen renders and plays through the new commentary/shot text
  without incident).

## [0.77.0] - 2026-07-27

### Added / Fixed

- **Godot player portraits, Phase 2 (visual identity) of the "best-in-class
  Steam cricket manager" roadmap**: the Godot client previously showed no
  player portraits at all (nationality flags only). New
  `godot_client/scripts/player_portrait.gd` — a `PlayerPortrait` custom-
  drawn `Control` (same pattern as `nav_icon.gd`) that ports the visual
  design of `src/utilities/player_portraits.py`'s `PlayerPortraitGenerator`
  (skin-tone table per nation, hair colour/style variety, age-based grey
  hair/wrinkles/beard chance, kit colour) to Godot's native vector drawing
  API instead of pygame's software-rasterized 128px canvas — renders crisp
  and anti-aliased at any size, the concrete fix for "player profile
  pictures... very pixely". Deterministic per player (same id/nationality/
  age always yields the same face, matching pygame's guarantee).
  - Wired into `player_hover_card.gd`/`.tscn` (row hover) and
    `player_profile_modal.gd`/`.tscn` (click-to-profile) — both scenes
    restructured to add a `Portrait` node alongside the existing text.
  - New `"portrait": true` column type in `table_screen.gd`'s generic
    row renderer; Squad and Selection's leftmost column (previously a
    bare nationality flag) now renders a portrait instead.
- Real gotcha found while building this: a brand-new script declaring
  `class_name PlayerPortrait` isn't visible to other scripts typing an
  `@onready var` against it until Godot's global script-class cache
  (`.godot/global_script_class_cache.cfg`) is rebuilt — which only happens
  via an editor scan, not a normal `--headless` run. Documented for future
  new `class_name` scripts: run
  `godot --headless --editor --path godot_client --quit` once after adding
  one, or the class fails to resolve with a "Could not find type" parse
  error.
- Godot smoke test: existing hover-card/click-to-profile exercises and the
  Squad/Selection screen checks already exercise portrait rendering (any
  `_draw()` failure would surface as a script error breaking those
  checks) — no bespoke new exercise needed. 18 screens clean across 3 runs.
- 304/304 Python tests pass, unchanged (this phase is Godot-only).

## [0.76.0] - 2026-07-27

### Added / Fixed

- **Godot pre-career startup flow, Phase 1 of the "best-in-class Steam
  cricket manager" roadmap**: the Godot client could not start a new
  career at all — Main Menu, New Game Setup, Career Team Selection, World
  Cup Setup, Tournament Setup, Settings, and Help all fell through to a
  placeholder. All seven are now real screens, ported field-for-field
  from their pygame counterparts (`src/views/screens/*.py`, `ui/settings.py`)
  rather than redesigned:
  - **Manager identity**: New Game Setup collects name/nationality/
    background/mode/difficulty/starting league — the same fields as
    pygame's screen — and now surfaces in Godot's persistent header
    ("Managed by {name}"), reusing `get_dashboard`'s existing response
    shape (`manager_name` field added).
  - New backend IPC methods (`ipc_server.py`) reuse `GameController`'s
    existing validated logic 1:1 by instantiating one shared instance on
    `ctx` (mirroring `main.py`'s own pattern) rather than reimplementing
    validation: `get_new_game_options`, `save_new_game_setup`,
    `get_selectable_teams` (now filters by chosen country, matching
    `CareerTeamSelectionScreen.build()`), `confirm_career_team`,
    `confirm_world_cup_team`, `confirm_custom_tournament`,
    `get_user_settings`/`update_user_settings`, `get_help_content`.
  - **Screen-transition system**: `shell.gd`'s `show_screen()` was an
    instant swap with zero animation anywhere in the Godot client. Added
    a shared fade+slide-up `Tween`, so every screen (ported or future)
    gets a modern/snappy feel for free.
  - Chrome-less presentation for the five pre-career screens (mirrors
    `main.py`'s `STARTUP_SCREEN_NAMES`) — sidebar/header hide automatically
    while no career is active yet.
- **Real bug found and fixed while building this**: adding
  `from src.controllers.game_controller import GameController` to
  `ipc_server.py` (a module explicitly documented "never touches pygame")
  transitively imported pygame anyway — `src/controllers/__init__.py`
  eagerly re-exported `AudioManager` from `audio_controller.py`, which
  imports pygame at module scope. pygame's own startup banner print then
  corrupted the JSON-RPC stdout stream the Godot client parses, breaking
  every IPC call on boot. Fixed by removing the dead re-export (confirmed
  nothing in the codebase actually used it — every real consumer already
  imports directly from the submodule).
- Godot smoke test extended: a new `_exercise_startup_flow()` drives the
  entire pre-career flow via real `Button.pressed` emits (Main Menu → New
  Game Setup → Career Team Selection → Dashboard) and asserts the manager
  name actually reaches the header; `_exercise_settings()` and
  `_exercise_help()` cover the two new utility screens. 18 screens still
  render; 3 new state-changing flows added — 3 clean runs.
- 304/304 Python tests pass, unchanged (this phase is almost entirely
  Godot-side; the small `ipc_server.py` additions were function-tested
  directly rather than needing new unittest coverage, matching how prior
  `ipc_server.py` IPC-only additions were verified in this session).

## [0.75.0] - 2026-07-27

### Added / Fixed

- **Godot/pygame feature-parity catch-up, part 3 of 3**: a real onboarding
  tutorial overlay, built from scratch in **both** clients. Correcting a
  prior docs claim: v0.68.0 only ever shipped the backend
  (`ONBOARDING_STEPS`, `get_onboarding_state`/`advance_onboarding`/
  `dismiss_onboarding` in `database.py`, matching IPC methods) plus 10
  backend-level tests — no screen in pygame or Godot ever called them.
  - pygame: `ui/widgets/onboarding_overlay.py`'s `OnboardingOverlay`
    (subclasses the existing `Modal` widget), driven from `main.py` —
    shown only when the current step's target screen matches
    `self.active_screen`, refreshed on every navigation via a new
    `_sync_onboarding_overlay()` hook in `set_active_screen()`/
    `build_interface()`. NEXT/SKIP TUTORIAL call `advance_onboarding()`/
    `dismiss_onboarding()` directly (single-player, no IPC round trip).
  - Godot: new `onboarding_overlay.gd`/`.tscn`, instantiated once by
    `shell.gd` and shown/hidden from `_sync_onboarding_overlay()` on every
    `show_screen()` call, driven by `get_onboarding_steps`/
    `get_onboarding_state`/`advance_onboarding_step`/`dismiss_onboarding`
    over IPC.
  - Smoke-test coverage added: a new `_exercise_onboarding()` drives real
    NEXT/SKIP TUTORIAL `Button.pressed` emits and checks the card only
    shows on its matching screen — idempotent against a persistent dev
    save where a prior run already dismissed the tutorial.
- **Real bug fixed in test infrastructure**: `test_youth_intake_uses_club_country`
  (`tests/test_final_refinement.py`) called `recruit_youth(3, "English", 4,
  database)` positionally — the 4th argument landed in `role_focus`
  (`recruit_youth`'s actual signature has `database_path` as the 5th
  parameter), so the test silently exercised the shared default database
  path instead of its own temp db, only failing when that default database
  happened to lack a `teams` table (e.g. right after a dev-save reset).
  Fixed to pass `database_path=database` as a keyword.

## [0.74.0] - 2026-07-27

### Added / Fixed

- **Godot/pygame feature-parity catch-up, part 2 of 3**: a dedicated Board
  screen in both clients, surfacing `evaluate_board_objectives()`/
  `get_board_confidence_history()` — previously exposed over IPC since
  v0.64.0 but never consumed by any UI; board reviews were only ever
  announced via one-off inbox messages with no way to check current
  standing on demand. pygame's `ui/career.py` gained a "Board" tab
  (season objectives with target/current/met, and confidence history);
  Godot gained a new `board_screen.gd`/`.tscn` under a new "Board" nav
  entry in the CAREER group.
- **Real bug found and fixed while building it**: `evaluate_board_objectives()`
  in `database.py` read the standings row as `row[0]` (always `team_id`,
  from `SELECT team_id, position FROM (...) WHERE team_id=?`) instead of
  `row["position"]` — so the league-position objective was silently
  comparing against the team's own database id, never the actual table
  position. Fixed to use named `sqlite3.Row` access. Regression test added
  (`test_evaluate_board_objectives_reports_the_real_standings_position_not_team_id`).

## [0.73.0] - 2026-07-27

### Added / Fixed

- **Godot/pygame feature-parity catch-up, part 1 of 3**: an audit found
  six backend features shipped in v0.63.0-v0.68.0/v0.72.0
  (opposition reports, pitch selection, job offers, board objectives,
  custom tournaments, onboarding tutorial) had real IPC/database
  support but **zero UI consumer in either client** — not just a Godot
  gap, a pygame one too. This pass closes three of the six:
  - **Pitch selection — real bug, not just missing UI.** pygame's
    `ui/pre_match.py` hardcoded `"Green"` to `PitchDisplay` regardless
    of what `set_pitch_selection()` actually stored, and never passed a
    pitch to `match_setup` at all — so the chosen pitch was silently
    discarded and the live match always used the engine's own default.
    Fixed: reads the real selection via `get_pitch_selection()`, adds a
    cycle button (home team only, matching the existing rule), and
    actually threads it through to the match. Godot's backend
    (`ipc_server.py`'s `start_match`) already read this correctly — it
    just had no UI button, now added to the pre-match screen.
  - **Opposition report** — pre-match scouting summary of the next
    opponent (key players, strengths/weaknesses, squad composition).
    Was `docs/UX_ROADMAP.md`'s explicit "next up" item since v0.63.0,
    with a working backend (`get_opposition_report`) nothing ever
    called. New Godot `opposition_report_modal.gd`/`.tscn`, opened from
    a new pre-match button.
  - **Job offers** — pygame's inbox literally tells the player "Review
    them in the Career screen," but no screen anywhere ever showed
    them; a broken promise in the shipped product. Fixed in both
    clients: pygame's `ui/career.py` gained a Job Offers tab
    (Accept/Decline, mirroring `ui/transfers.py`'s existing incoming-
    offer pattern); Godot gained a new "Job Offers" nav entry under
    CAREER, reusing `table_screen.gd`'s existing `row_buttons`
    mechanism. Accepting switches the managed club — `table_screen.gd`
    now refreshes the shell header after any `accept_job_offer` row
    action, since that's the one action that changes which club's data
    the rest of the UI should show.
  - **Still deferred** (see `docs/CURRENT.md`): a dedicated board-
    objectives/confidence screen, reconciling the two parallel "custom
    tournament" systems (a pre-game standalone tournament-only mode vs.
    the in-career `create_custom_tournament`/`list_custom_tournaments`
    IPC methods — a product decision, not a quick UI add), and the
    onboarding tutorial overlay.
  - 303/303 Python tests pass; Godot smoke test clean across 3 runs
    (17 screens registered, up from 16); packaged pygame diagnostics
    pass (confirms the new Job Offers tab doesn't crash startup).

## [0.72.0] - 2026-07-27

### Added

- **International cricket** — the third and last of the user-directed
  roadmap priorities from the stability audit, and the largest/most
  disruptive by design, so deliberately scoped down from a full
  separate international career mode (no manager creation, no parallel
  calendar, no user-controlled squad selection). Once a season (a
  fixed July 1 window), the best 11 eligible players of two
  randomly-chosen represented nations — drawn from every club in the
  game world, not just the user's — contest a 3-match T20I series using
  the full ball-by-ball `match_engine.Match` (affordable here since it
  runs only once a season, unlike `simulate_fixture()`'s lightweight
  statistical simulator used for the many AI-vs-AI club fixtures).
  - New shared `src/models/international.py` (mirrors `morale.py`'s and
    `squad_metrics.py`'s role as a single source of truth): the seven
    nationalities actually represented in the generated world, stable
    negative synthetic team ids for the ad-hoc national "teams",
    facilities defaults for match-engine calculations, and the series
    length/morale-bonus constants.
  - New `database.py` helper `select_national_xi()`: the best 11
    eligible players of a nationality (keeper guaranteed a slot, then
    filled by overall), mirroring `ipc_server.py`'s existing
    `_best_xi()` club-selection fallback rule.
  - New `CompetitionEngine._run_international_window()`, called from
    `advance_day()` — shared by both clients automatically (no separate
    Godot/pygame wiring needed, unlike morale's match-completion hooks,
    since both clients already funnel through the same
    `CompetitionEngine.advance_day()`). Idempotent per season.
  - A user's own player being selected is a real, consequential event:
    an `"International"` `player_records` entry (a context the schema
    already anticipated but never used), a morale boost for every
    called-up player, and a named HIGH-priority inbox message. Already
    visible today in pygame's existing `PlayerDetailModal` Records tab,
    which iterates all four record contexts including `"International"`
    without any UI changes needed.
  - New `tests/test_international.py`: national-team helper correctness,
    `select_national_xi`'s keeper-priority rule, the once-per-season
    guard, the exact July-1-only `advance_day()` trigger, call-up
    morale/record effects, and the inbox message. 303/303 Python tests
    pass; Godot smoke test clean across 3 runs (no Godot script changes
    needed — this is backend-shared).

This closes out all three user-directed roadmap priorities from the
2026-07-27 stability audit: persistent fatigue (v0.70.0), dynamic
morale (v0.71.0), and this. See `docs/CURRENT.md` for what's next.

## [0.71.0] - 2026-07-27

### Added

- **Dynamic player morale** — the second of three user-directed roadmap
  priorities. Morale already genuinely affected match performance,
  AI team selection, and contract negotiation, but nothing in the game
  ever changed it after initial generation; it behaved as a fixed random
  constant dressed up as a live mood stat. Four real events now move it:
  - **Match results** — a whole-squad morale shift for both teams on
    every completed match (win/loss/tie), not just the XI that played;
    cup fixtures carry higher stakes (1.6x) than league games.
  - **Being dropped from the XI** — a player who was in the previous
    match's confirmed XI but is left out of the next one takes a small
    morale hit, the real-world "unhappy to be benched" case. Tracked via
    a new `last_match_xi` game-state key, written on match completion
    and read at the next match start.
  - **A signed contract renewal** — accepting negotiated terms lifts
    morale; this is the acceptance-persistence point
    (`renew_player_contract`), so it only fires once `negotiate()` has
    already returned "accept".
  - **Promotion/relegation** — a whole-squad bonus/penalty applied to
    every promoted or relegated club at season rollover, not just the
    user's — an AI club going up or down should feel it too.
  - New shared `src/models/morale.py` (mirrors `squad_metrics.py`'s
    role as a single source of truth) with the pure event-delta
    functions, and two new `database.py` helpers
    (`adjust_players_morale`, `adjust_team_morale`) using SQLite's
    `json_set`/`json_extract` to mutate the nested `mental.morale`
    field directly, bounded 0-100.
  - Wired into both clients identically: `ipc_server.py`'s
    `_finalise_match`/`_start_match` for Godot, `ui/match_view.py`'s
    `_record_result`/`ui/pre_match.py`'s XI-confirmation for pygame —
    same formulas, same game-state key, so a career played in one
    client and continued in the other stays consistent.
  - New tests: the pure delta formulas (win/loss/tie, cup stakes
    multiplier, dropped-player detection), bounded persistence for both
    the per-player and whole-squad helpers, contract-signing and
    rollover-season morale effects, and end-to-end IPC coverage that a
    completed match actually moves both squads' morale and that
    starting a new match actually penalises a genuinely-dropped player.
    294/294 Python tests pass; Godot smoke test clean across 3 runs (no
    Godot UI changes needed — Squad's MORALE column already existed).

## [0.70.0] - 2026-07-27

### Added

- **Persistent player fatigue & rotation** — the first of the three
  roadmap items flagged by the stability audit (fatigue was previously
  session-only: every player started every match at full energy
  regardless of recent workload). Squad rotation now has an actual
  reason to exist.
  - New `fatigue` column on `players` (0-100, higher = more tired).
  - `Match.performance_updates()` now includes an absolute post-match
    fatigue reading for every player who took the field (the complement
    of the engine's existing end-of-match `energy` value), persisted by
    `apply_match_player_updates()`.
  - New `recover_daily_fatigue()`, called once per `advance_day()`:
    every player recovers `FATIGUE_DAILY_RECOVERY` (12) points per rest
    day, roughly a week to fully recover from a demanding match.
  - Incoming fatigue already fed into `Match._initialise_energy()`'s
    starting-energy calculation before this change — it just always
    read 0. That wiring now does something real: a fatigued player
    starts their next match with less energy in the tank.
  - Fatigue now also contributes to injury risk in `_maybe_injury()` — a
    player carrying fatigue from insufficient rest is more injury-prone
    than endurance alone accounted for, matching the real-world case for
    rotating a squad.
  - Surfaced in both clients: pygame's Squad and Selection screens gained
    a Fatigue/Fat column; Godot's Squad and Selection screens gained a
    FRESH (freshness = 100 − fatigue) bar column — inverted from raw
    fatigue so the existing high-is-good bar colour scheme reads
    correctly.
  - New tests: fatigue persists across `apply_match_player_updates` calls
    and is left untouched when a caller omits it (not silently reset to
    0), `recover_daily_fatigue` decays correctly and never goes negative,
    `performance_updates()` reports a bounded fatigue value for every
    player on the field, and incoming fatigue measurably lowers starting
    match energy.

### Fixed

- A Godot smoke-test regression caught by this session's own added
  coverage: inserting the new FRESH column into Selection's row layout
  shifted a hardcoded child-index lookup in `shell.gd`'s smoke test
  (`_ensure_row_in_xi`), crashing batting-order/aggression exercises.
  Fixed the index; a reminder that column insertions in `table_screen.gd`
  configs need matching updates wherever a smoke test reads row children
  by position rather than by column key.

## [0.69.0] - 2026-07-26

### Added

- **The Hundred** — a complete 100-ball format with 20 five-ball sets,
  a 20-ball cap for each bowler, five-ball score notation and trackers,
  set-based powerplay, drinks break, rate calculations and scorecards.
- The Hundred is selectable in custom tournaments and migrates safely into
  existing save databases without discarding tournament records.

### Tests

- Added coverage for the 100-ball innings limit, five-ball notation,
  individual bowling cap and custom-tournament persistence.

### Fixed (project-wide stability audit, 2026-07-27)

- **`ipc_server.py`'s `build_context()` never called
  `CompetitionEngine.ensure_season()`** — a save created purely through
  the Godot client had exactly one hardcoded demo fixture and then a
  permanently empty fixture list; no Domestic Division 1/2 league or cup
  was ever generated. The most significant bug found in this pass — it
  broke the entire season/league loop for a Godot-only game. Fixed by
  calling `ensure_season()` on every backend startup, matching
  `main.py`'s pygame bootstrap (idempotent, safe to call every time).
- Consolidated two independently-diverging player valuation formulas
  (`squad_metrics.estimated_value()` vs `transfer.transfer_value()`,
  ~30-40% apart for the same player) into one source of truth.
- Fixed scouting using hardcoded team finances (`team_cash=8_000_000,
  team_reputation=60`) for every scouted player regardless of which club
  actually owned them — availability/asking-price now reflect the
  player's own club's real cash and division.
- Season-end promotion/relegation/retirement was computed but never
  actually shown to the user (`rollover_season()`'s return value was
  silently dropped by every caller) — now posts inbox messages.
- Added a `won` tiebreaker (points → wins → net run rate) everywhere
  league standings are sorted, plus a minimum-teams guard against a
  too-small division corrupting promotion/relegation.
- Godot: fixed `match_screen.gd`'s DRS/CHANGE BOWLER status messages
  being immediately overwritten by `_render_state()` on the next line;
  added a missing `refresh()` to `recruitment_screen.gd` (silently went
  stale after Advance Day, unlike every other screen); replaced
  unguarded `result["team"]` bracket access with defensive `.get()` in
  two screens. New smoke-test coverage for DRS, AUTO/SPEED, Training's
  intensity/days/bulk-apply, and Recruitment's remaining nav buttons.

## [0.68.0] - 2026-07-24

### Added

- **Onboarding tutorial** — guided first-run experience for new managers.
  A 7-step walkthrough highlights every core screen with contextual
  descriptions, persisted via `game_state` so it survives saves.
  - `database.py`: new `ONBOARDING_STEPS` constant (7 steps: welcome,
    squad, selection, training, transfers, match day, finances),
    `get_onboarding_state()`, `advance_onboarding()`, `dismiss_onboarding()`.
  - State stored in `game_state` as `"onboarding_state"` with fields:
    `completed_steps`, `current_step`, `dismissed`.
  - `ipc_server.py`: new `get_onboarding_state`, `get_onboarding_steps`,
    `advance_onboarding_step`, `dismiss_onboarding` IPC methods.

### Tests

- **10 new tests** (274 total; 1 pre-existing flaky academy test):
  - `test_management_systems.py`: 6 new `OnboardingTests` — initial state
    has welcome step, advance moves to next step, advance through all
    steps completes, dismiss skips all, steps have required fields, state
    persists across calls.
  - `test_ipc_server.py`: 4 new tests — `get_onboarding_state` starts at
    welcome, `get_onboarding_steps` returns all steps, advance moves
    forward, dismiss marks all completed.

## [0.67.0] - 2026-07-24

### Added

- **Custom tournament creator** — build database-backed cup competitions
  with group-stage round-robin and single-elimination knockout rounds.
  Fully integrated with the existing match engine, CompetitionEngine
  and standings pipeline.
  - `database.py`: new tables `custom_tournaments` and
    `tournament_id` column on `competitions`.
  - New functions: `create_custom_tournament()`, `get_custom_tournaments()`,
    `get_custom_tournament()`, `get_tournament_standings()`,
    `advance_tournament_to_knockout()`, `get_tournament_bracket()`.
  - Circle-method round-robin generator (`_generate_round_robin()`).
  - Group stage creates one `'League'` competition per group so
    `CompetitionEngine.simulate_fixture` updates standings automatically.
  - Knockout phase creates a `'Cup'` competition with seeded bracket.
  - T10 format now accepted in `matches.format` CHECK constraint
    (table rebuild migration for existing saves).
  - `ipc_server.py`: new `list_custom_tournaments`, `get_custom_tournament`,
    `create_custom_tournament`, `get_tournament_standings`,
    `get_tournament_bracket`, `advance_tournament_to_knockout` IPC methods.

### Tests

- **16 new tests** (264 total; 1 pre-existing flaky academy test):
  - `test_management_systems.py`: 12 new `CustomTournamentTests` —
    creation generates groups, min-4-teams validation, invalid format
    rejection, round-robin structure, standings populated, list endpoint,
    advance requires groups complete, advance after groups complete,
    bracket empty before knockout, T10 format accepted, round-robin
    balanced pair count, 3-group layout for large pools.
  - `test_ipc_server.py`: 4 new tests — `list_custom_tournaments` starts
    empty, create+list round-trip, `get_custom_tournament` returns details,
    `get_tournament_standings` returns group data.

## [0.66.0] - 2026-07-24

### Added

- **Interactive job market** — at season end, the manager may receive job
  offers from underperforming clubs based on reputation. Also includes a
  sacking mechanism for persistent board-confidence failure.
  - `database.py`: new `generate_job_offers()`, `get_job_offers()`,
    `store_job_offers()`, `accept_job_offer()`, `decline_job_offer()`,
    `check_sacking()` functions.
  - Offers generated at season end in `_award_season_honours()` based on
    `manager_reputation()` score. Clubs must have average overall ≥ 55,
    be in the user's division or lower, and be below 6th place.
  - Accepting an offer switches `user_data.current_team_id` and refreshes
    the IPC context (team, players, game_data).
  - Sacking triggers after 3 consecutive "Ultimatum" board-confidence
    reviews (mid-season + season-end).
  - `ipc_server.py`: new `get_job_offers`, `accept_job_offer`,
    `decline_job_offer` IPC methods registered in `METHODS`.

### Tests

- **14 new tests** (248 total; 1 pre-existing flaky academy test):
  - `test_management_systems.py`: 10 new `JobMarketTests` — offer
    generation returns list, excludes own team, has required fields,
    store/retrieve round-trip, accept switches team and clears from list,
    accept invalid raises, decline removes, sacking returns None with
    few reviews, None without streak, returns sacking with 3 ultimatums.
  - `test_ipc_server.py`: 4 new tests — `get_job_offers` starts empty,
    `accept_job_offer` updates context team, `decline_job_offer` removes
    offer.

## [0.65.0] - 2026-07-24

### Added

- **Pitch selection for home matches** — the home team manager can now
  choose the pitch surface before a match, giving a tactical advantage
  tailored to their bowling attack. Five pitch types, each with distinct
  gameplay effects already built into the match engine:
  - **Green** — favours seam and swing; pace and bounce amplified.
  - **Dry** — moderate spin assistance; low bounce.
  - **Dusty** — big turn from day one; spinners dominate.
  - **Flat** — true bounce; batters dominate; high-scoring.
  - **Worn** — variable bounce, reverse swing; spin and pace both viable.
  - `database.py`: new `set_pitch_selection()`, `get_pitch_selection()`
    functions; `PITCH_TYPES` and `PITCH_DESCRIPTIONS` constants.
  - `ipc_server.py`: new `get_pitch_options` and `set_pitch_selection`
    IPC methods; `start_match` now passes the user's chosen pitch to the
    Match constructor when the user is the home team.

### Tests

- **8 new tests** (234 total, all pass):
  - `test_management_systems.py`: 5 new `PitchSelectionTests` —
    round-trip set/get, default is Green, rejects invalid types,
    overwrites previous, all valid pitches round-trip.
  - `test_ipc_server.py`: 3 new tests — `get_pitch_options` returns
    types/descriptions/current, `set_pitch_selection` persists, rejects
    invalid pitch type.

## [0.64.0] - 2026-07-24

### Added

- **Board expectations / club vision** — the board sets visible season
  objectives at campaign start and tracks progress throughout the season.
  Objectives are stored in `game_state` and include a league-position
  target and minimum cash balance.
  - At season start (`ensure_season`), the board generates objectives
    (random league target 4–8, random cash minimum £75k–£200k) and sends
    a HIGH-priority inbox message outlining the targets.
  - Mid-season review on July 15 (`advance_day`) evaluates progress
    against each objective, sends a status report (on track / behind
    target), and records a confidence snapshot.
  - Season-end review (`_award_season_honours`) now uses stored
    objectives instead of a hardcoded target, showing per-objective
    progress (met/missed) with tick/cross indicators.
  - `database.py`: new `set_board_objectives()`, `get_board_objectives()`,
    `record_board_confidence()`, `get_board_confidence_history()`,
    `evaluate_board_objectives()` functions.
  - `ipc_server.py`: new `get_board_objectives` and
    `get_board_confidence_history` IPC methods registered in `METHODS`.

### Tests

- **10 new tests** (226 total, all pass):
  - `test_management_systems.py`: 6 new `BoardExpectationsTests` —
    objectives set on season start, inbox message sent, defaults returned
    for unknown teams, confidence history round-trip, history capped at
    20 entries, evaluation returns progress dict.
  - `test_ipc_server.py`: 4 new tests — `get_board_objectives` returns
    defaults and real objectives, `get_board_confidence_history` starts
    empty, objectives with fixtures return real data.

## [0.63.0] - 2026-07-24

### Added

- **AI-initiated transfer offers** — AI clubs now proactively evaluate their
  squads weekly during `advance_day()`. When a club has fewer than 2 players
  in a key role (Batsman, Bowler, All-Rounder, Wicketkeeper) and sufficient
  cash, they identify the best available target (transfer-listed or
  short-contracted) and submit a bid. Offers surface as HIGH-priority inbox
  messages. User can accept or reject via the existing Offers screen.
  - `database.py`: new `generate_ai_transfer_offers()` function with squad-gap
    detection, budget-aware fee calculation, and pending-offer deduplication.
  - `competition.py`: wired into `advance_day()` on Sundays; creates inbox
    notifications for each received offer.
  - `ipc_server.py`: imports updated to include `generate_ai_transfer_offers`.

- **Opposition reports** — pre-match scouting summary of the next opponent
  accessible via the Godot IPC `get_opposition_report` method. Includes
  predicted XI, key players (top 5 by overall), role distribution, squad
  size, average overall rating, and generated strengths/weaknesses (deep
  bowling, key performers, all-rounder depth, ageing squad, weak overall).
  - `database.py`: new `get_opposition_report()` function.
  - `ipc_server.py`: new `get_opposition_report` IPC method registered in
    `METHODS` dict; imports updated.

### Tests

- **9 new tests** (216 total, all pass):
  - `test_management_systems.py`: 6 new tests — `AiTransferOfferTests`
    (returns list, targets transfer-listed/short-contract, deduplication,
    excludes user-team buyers) and `OppositionReportTests` (returns None
    without fixtures, returns scouting summary, includes predicted XI).
  - `test_ipc_server.py`: 3 new tests — `get_opposition_report` returns
    None without fixtures, returns scouting data with fixtures (checks
    opponent_name, key_players, strengths, weaknesses, xi fields).

## [0.62.0] - 2026-07-22

### Added

- **Godot client: Match Stats Hub visual layer** — wagon wheel, pitch/
  bowling map, worm, momentum, Manhattan, and partnerships. The last
  remaining piece of pygame's fuller Match experience; everything else
  (live feed, tactics) shipped in v0.60.0/v0.61.0.
  - `ipc_server.py`'s `BALL_EVENT_KEYS` now forwards each ball's `shot`
    and `delivery` sub-dicts (already produced by
    `Match.ball_outcome()`, previously dropped from the IPC payload) —
    the only backend change needed; everything else is pure Godot-side
    aggregation from the ball stream the client already receives.
  - New `match_stats_canvas.gd` (a `Control` with a custom `_draw()`)
    ports `ui/widgets/shot_map.py`'s `ShotMap` (wagon wheel/boundary
    map — line+dot per shot at `(angle, distance)` from centre, red/
    wicket, gold/4+6, green/other runs, muted/dot ball) and
    `ui/widgets/bowling_map.py`'s `BowlingMap` (pitch map — dots at
    each delivery's normalised `(x, y)` against SHORT/GOOD/FULL/YORKER
    length guides and off/leg channel guides).
  - Worm, Momentum, and Manhattan have no dedicated pygame widget or
    backend field — `match_engine.py` doesn't track per-over data, so
    both clients compute them from the ball-by-ball stream. Godot
    tracks real cumulative-runs-per-over for **every innings played so
    far**, which is a genuine improvement over pygame's Worm tab: pygame
    fakes the non-user-team's line with a hardcoded 3-point placeholder
    curve, since its client-side `ball_history` only covers the
    currently batting side. Momentum is a rolling 24-ball
    `sum(runs) - 8*sum(wickets)` window, matching pygame's formula
    exactly.
  - Partnerships needed no new tracking — `scorecard()`'s existing
    `partnerships` field (already round-tripped through
    `get_match_state`/`simulate_balls`) was enough; rendered as pygame
    does, a name-pair/runs(balls) row with a proportional bar underneath.
  - Known, documented limitation: resuming a match already in progress
    (navigating away from Match and back) starts these accumulators
    fresh, since only balls simulated through the current screen
    instance are captured — full history reconstruction would need
    backend-side per-over tracking, out of scope for this pass.
  - New smoke-test exercise switches real Stats Hub tabs via actual
    button presses and asserts the shot/bowling event accumulators
    actually captured data and the right panel (`scorecard_row` /
    `stats_card` / `partnerships_card`) actually became visible for
    each tab — not just that no error fired. Godot smoke test clean
    across 3 runs. 207/207 Python tests pass.

## [0.61.0] - 2026-07-22

### Added

- **Godot client: Match tactics — PREDICT, FIELD, aggression, DRS,
  bowler change**, the next slice of pygame's Stats Hub/action-button
  row (deliberately deferred from v0.60.0's core live feed). Still not
  ported: wagon wheel, pitch/bowling maps, worm/momentum/manhattan
  graphs, and a dedicated tactics hub UI — this pass covers the
  mechanically simple, high-value controls only.
  - Five new IPC methods in `ipc_server.py`: `get_match_prediction`
    (the user's own team's win% via `Match.win_probability`, matching
    pygame's `PredictorModal` — the opponent's is always 100 minus
    this, never shown separately), `set_match_field` (a genuine
    tactical choice, not cosmetic: Aggressive raises wicket chance and
    boundary risk, Defensive suppresses both), `set_match_aggression`
    (1-10 batting/bowling sliders, applied to the striker/bowler on
    every subsequent delivery — batting is averaged with the striker's
    Selection-screen batting style exactly as pygame's
    `simulate_ball()` does), `review_decision` (DRS — a review is free
    when it overturns a wrong decision, and only costs one of the
    team's two reviews when the original call is upheld, per
    `Match.review_last_decision`'s actual accounting, confirmed by
    reading the code rather than assumed), and `cycle_match_bowler`
    (steps to the next eligible bowler, excluding whoever bowled the
    previous over, matching pygame's CHANGE button).
  - `match_screen.gd`/`.tscn` gained a second control row: PREDICT,
    FIELD (cycling Aggressive/Neutral/Defensive), BAT AGGRO / BOWL
    AGGRO (cycling 1-10 — a simplification of pygame's continuous
    slider widgets, which Godot's UI toolkit doesn't have a ready
    equivalent for; a real slider control can follow later), CHANGE,
    and DRS, all disabled once the match completes.
  - New smoke-test coverage: real PREDICT and FIELD button presses,
    asserting the prediction label and field state actually changed
    (not just "no error"). New Python tests for all five methods,
    including a real Monte Carlo probability bounds check, field-preset
    validation, aggression clamping, a DRS review that actually finds
    a reviewable wicket against the user's team and consumes exactly
    one of two reviews when upheld, and a real bowler change. Godot
    smoke test clean across 3 runs. 207/207 Python tests pass.

## [0.60.0] - 2026-07-22

### Added

- **Godot client: live ball-by-ball Match feed**, the single largest
  deferred piece of the whole Godot migration. The Match screen no
  longer stops at the static pre-match preview — START MATCH now runs
  a real `match_engine.Match` through `ipc_server.py`, one genuine
  delivery at a time (`Match.ball_outcome()`, not a bulk-simulate-then-
  replay), mirroring `ui/match_view.py`'s timer-driven `simulate_ball()`
  loop.
  - Three new IPC methods: `start_match` (builds the match from the
    manager's selected XI — or pygame's same best-XI fallback — and the
    opponent's squad, keeps the live `Match` object in the backend
    process between calls), `simulate_balls` (steps forward up to N
    *legal* deliveries, extras don't count against the requested
    count — matches how an over is actually defined), and
    `get_match_state` (a lightweight live snapshot for
    reconnect/resume, deliberately not `match.to_dict()`, which also
    computes `performance_updates()` — a once-per-match cost, not a
    once-per-ball one).
  - On completion, the backend runs the same finalisation pygame's
    `_record_result()` does: records the fixture result into the real
    standings/cup pipeline (`CompetitionEngine.record_played_fixture`),
    applies bounded player form/overall progression and injuries,
    records career batting/bowling lines, and persists shot/delivery
    events — guarded against double-finalisation if the client calls
    `simulate_balls` again after the match has already ended.
  - New Godot Match screen (rewired `match_screen.gd`/`.tscn`): a live
    score bug, batting/bowling scorecards with the striker/non-striker/
    bowler highlighted, a colour-coded scrolling commentary feed, and
    NEXT BALL / OVER / AUTO (with a Normal/Fast/Instant speed cycle,
    same as pygame) / SKIP / EXIT controls. Deliberately scoped down
    from pygame's full Stats Hub (wagon wheel, pitch map, worm/
    momentum/manhattan graphs, tactics hub, DRS, field presets,
    win-probability) to what a live match needs to be genuinely
    playable — the rest can follow in a later pass.
  - New smoke-test exercise runs a real match end-to-end through real
    button-press signals (START MATCH, NEXT BALL, then bounded SKIP
    presses) and asserts the match actually reaches `completed`, not
    just that no error fired. Godot smoke test clean across 3 runs.
  - New Python tests directly exercise `start_match`/`simulate_balls`/
    `get_match_state`, including a full run-to-completion check and an
    explicit assertion that a second post-completion `simulate_balls`
    call does not re-run finalisation (standings/form/injuries would
    otherwise double-count). 201/201 Python tests pass.

## [0.59.0] - 2026-07-22

### Added

- **Godot client: Youth Academy interactivity + Recruitment nav
  shortcuts**, found by auditing the remaining data-heavy screens
  (Youth Academy, Medical Centre, Recruitment) against their pygame
  counterparts for the same "read-only port missed the interactive
  parts" gap that Training turned out to have. Medical Centre checked
  out clean — pygame's version is genuinely read-only too
  (`process_event` is a no-op there), so no work needed. Youth Academy
  and Recruitment both had real gaps.
  - New bespoke `youth_academy_screen.gd`/`.tscn` ports `ui/youth.py`'s
    split-view UI: squad table + side panel with a collective training
    FOCUS cycle (Balanced/Batting/Bowling/Fielding, applied to every
    academy-eligible player), a targeted SCOUT FOR role selector, and a
    paid RECRUIT YOUTH trial (spends a fixed fee, generates 3-5 new
    16-year-old prospects, posts an inbox notification) plus a
    development-pipeline breakdown by potential band. Row click opens
    the same player profile modal as Squad/Youth Academy elsewhere.
  - `ipc_server.py` gained `set_academy_focus` and
    `recruit_youth_prospects`, wrapping `database.py`'s existing
    `set_training_focus`/`recruit_youth`/`add_financial_transaction`/
    `create_inbox_message`. `get_youth_academy`'s player filter was
    also corrected to match `ui/youth.py`'s actual roster rule
    (under-20s *or* anyone flagged `academy_squad`, not the flag
    alone) — a real behavioural bug fix, not just new functionality;
    the existing test asserting the old, narrower filter was updated
    to assert the correct pygame-parity rule instead.
  - `recruitment_screen.gd`/`.tscn` gained the three header shortcut
    buttons pygame's `RecruitmentHubScreen` has (Browse Transfers,
    Staff Market, Academy) — `shell.gd` now registers itself in a
    `"shell"` group so any screen can call `show_screen()` without a
    tightly-coupled parent reference.
  - New smoke-test exercises: Youth Academy's FOCUS button real
    `pressed` signal round-trips through the backend, and RECRUIT
    YOUTH's real `pressed` signal actually grows the squad (checked via
    player count, not just "no error"); Recruitment's ACADEMY button
    real `pressed` signal actually navigates the shell. Godot smoke
    test clean across 3 runs. 197/197 Python tests pass (including the
    updated youth-academy-filter test).

## [0.58.0] - 2026-07-22

### Added

- **Godot client: Training's real interactivity**, the third and last of
  the usability gaps the user flagged ("mousing over players should give
  their details, can't click on players, training doesn't show training
  groups"). The Godot Training screen was previously read-only display;
  it now ports `ui/training.py`'s full split-view UI as a bespoke
  `training_screen.gd`/`.tscn` (a `table_screen.gd` generic list wasn't a
  fit — this needs a table + detail-panel layout with per-column inline
  cycling, closer to Match's custom layout).
  - Squad table (left) + programme detail card (right): click a row to
    select a player, PROGRAMME/INTENSITY/DAYS buttons cycle that
    player's training assignment, APPLY PROGRAMME TO ALL copies it to
    the whole squad, ADVANCE TO NEXT SESSION / SIMULATE 30 CALENDAR DAYS
    actually run training and show real attribute growth bars
    (Batting/Bowling/Fielding/Mental) plus a toast reporting points
    gained.
  - `ipc_server.py` gained five new IPC methods wrapping
    `database.py`'s already-existing `set_training_focus`/
    `set_training_schedule`/`apply_daily_training` (previously only used
    by the pygame client): `cycle_training_focus`,
    `cycle_training_intensity`, `cycle_training_days`,
    `apply_training_to_all`, `simulate_training` — each mirrors the
    corresponding pygame cycle/bulk/simulate action and returns the
    refreshed `get_training` view.
  - New smoke-test exercise emits the real PROGRAMME button's `pressed`
    signal and checks the selected player's programme actually changed
    on the backend round trip, then presses SIMULATE 30 CALENDAR DAYS
    and checks it reports real points gained. Godot smoke test clean
    across 3 runs (caught and fixed one real bug during that
    verification: a copy-pasted node path missing the `Scroll` level
    left `row_list` null, crashing `_build_rows()` on every refresh).
    197/197 Python tests pass.

## [0.57.0] - 2026-07-22

### Added

- **Godot client: click-to-open player profile**, the second of the
  usability gaps the user flagged ("mousing over players should give
  their details, can't click on players, training doesn't show training
  groups"). New `player_profile_modal.gd`/`.tscn` ports
  `ui/player_modals.py`'s `PlayerDetailModal`, scoped down to a single
  solid view (flag, name, role/age/nationality, overall + potential,
  weekly wage, contract years remaining, and a full Batting/Bowling/
  Fielding/Mental/Physical attribute bar breakdown) rather than the
  pygame version's full six-tab modal (Records/Bat Form/Bowl Form/
  Personal/Match Stats/Comparison) — those can follow as their own
  screens later.
  - Wired into `table_screen.gd`: clicking any player row opens the
    profile, but only on screens where nothing else already claims the
    click (Squad, Youth Academy) — Selection's row click still toggles
    XI membership and Inbox's still marks messages read, both unchanged.
  - `ipc_server.py`'s `get_squad`/`get_youth_academy` now add a
    `wage_display` field (via `format_money()`) alongside the raw
    `wage`, matching the existing `*_display` pattern used elsewhere for
    the profile's contract line.
  - New smoke-test exercise emits a real row's `gui_input` left-click
    signal and asserts the modal actually opens with the correct player
    name and non-empty attribute rows, not just that no error fired.

## [0.56.0] - 2026-07-21

### Added

- **Godot client: player hover cards**, the first of several usability
  gaps the user flagged directly ("mousing over players should give
  their details, can't click on players, training doesn't show training
  groups"). New `player_hover_card.gd` ports
  `ui/widgets/quick_card.py`'s `QuickCard` exactly — name, role/age/
  nationality, overall (attribute-tier coloured), and Form/Fitness/
  Morale bars, shown near the cursor while hovering a data row. Wired
  into `table_screen.gd` so it applies to every player-list screen (any
  row with `overall` + `role` keys) with no per-screen wiring.
  - Fixed a real bug caught while verifying visually: overall/form both
    showed a hardcoded fallback "50" instead of the real value — a
    `str(value).is_valid_int()` check on a raw JSON float (e.g. `92.0`,
    which stringifies with a decimal point) always failed, silently
    falling through to the default. Simplified to a direct `int()` cast
    on the Variant, no string round-trip needed.
  - New smoke-test exercise emits a real row's `mouse_entered`/
    `mouse_exited` signals and asserts the card actually shows the right
    player's name, then actually hides — not just "no error".
- Click-to-profile and Training's interactive focus/intensity/schedule
  assignment (both flagged in the same feedback) are next — Training
  currently only *shows* assignments, matching `get_training`'s
  read-only IPC method; setting them needs new IPC methods wrapping
  `set_training_focus`/`set_training_schedule`/`apply_daily_training`,
  which pygame's `ui/training.py` already calls.
- Godot smoke test clean across 3 consecutive runs, visually verified
  via screenshot capture. No Python-side changes; 197 tests unaffected.

## [0.55.0] - 2026-07-21

### Changed

- **Training migrated to the shared `table_screen.gd` component**, the
  last screen still using a bespoke plain-list layout predating the
  theme pass (same reasoning as Squad's earlier migration this session).
  `get_training` now flattens each player's assignment (focus/intensity/
  last_trained) onto the player dict server-side, instead of the client
  merging two separate structures — Training gets flags, role pills, and
  zebra-striped rows for free, and `training_screen.gd`/`.tscn` are
  deleted (one less bespoke screen to maintain).
- 1 new test (197 total), Godot smoke test clean across 3 consecutive
  runs, visually verified via screenshot capture, pygame client
  unaffected. (One unrelated pre-existing flaky test —
  `test_academy_recruitment.py`'s pace/spin assertion, already tracked
  separately — surfaced once during this pass; confirmed unrelated by
  rerunning clean.)

## [0.54.0] - 2026-07-21

### Fixed

- **Comprehensive visual audit of all 16 Godot screens** (screenshot-test
  now covers every screen, not just 5) surfaced two real bugs:
  - Training's "LAST TRAINED" column showed the literal text `<null>`
    instead of a blank placeholder — `Dictionary.get(key, default)` only
    falls back when the key is *absent*; a JSON `null` value (Python's
    `None`, round-tripped through the IPC layer) still returns `null`
    itself, and `str(null)` prints `"<null>"`. Same root cause applies to
    `focus`/`intensity`; fixed with an explicit null check.
  - Money fields (Transfers price, Offers fee, Staff Market fee/wage,
    Finances amount) displayed as bare integers instead of formatted
    currency. `ipc_server.py` now formats these using
    `src/models/currency.py`'s existing `format_money()` — the same
    helper `ui/finances.py` already uses — returning a new `*_display`
    field alongside the raw number (kept for methods like
    `submit_transfer_offer` that still need the real integer).
- 2 new tests (196 total), Godot smoke test clean across 3 consecutive
  runs, visually verified via screenshot capture across every screen.

## [0.53.0] - 2026-07-21

### Fixed

- **Text ghosting regression from v0.52.0's MSDF font change** — the
  user ran the exported build and every heading showed a visible
  double-stroke/ghost artifact (most obvious on "Manchester Mavericks").
  MSDF font rendering doesn't play well with this project's
  `gl_compatibility` renderer. Reverted `multichannel_signed_distance_field`
  to `false` and used `oversampling=2.0` instead to get smoother
  anti-aliased text without MSDF's rendering bug — hinting stays
  disabled from v0.52.0.
- **Match ground view fielder dots invisible + label overlap** — also
  flagged directly: `ground_view.gd` drew a same-radius "border" circle
  fully on top of each fielder dot, completely overwriting its intended
  colour with dark turf-green (nearly invisible against the pitch), and
  close-in fielders (WK/slip/gully) had labels stacked directly beneath
  each dot regardless of how close together the dots themselves were,
  overlapping into unreadable text. Rewrote as: a proper ring (larger
  circle behind, smaller fill on top), shirt-number markers (1-11, gold
  for the keeper) for a clearer Cricket Captain-style look, labels offset
  radially outward from the ground's centre (so nearby dots' labels fan
  out instead of stacking), plus stumps at both ends and subtle turf
  rings for texture.
- Godot smoke test clean across 3 consecutive runs, visually verified
  via screenshot capture *and* the exported standalone `.exe` directly
  (this is exactly the workflow that caught both bugs — screenshots
  alone had missed the ghosting since it's subtle at small scale). No
  Python-side changes; 194 tests unaffected.

## [0.52.0] - 2026-07-21

### Changed

- **Graphics migration: smoother text rendering + FM26-style tabs**,
  following direct feedback on the exported build (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`). The Inter font now imports as an
  MSDF (multichannel signed-distance-field) font with hinting disabled,
  instead of Godot's default hinted rasterised glyphs — smoother
  anti-aliased edges at every size instead of the harder, pixel-snapped
  look the user flagged as "too sharp".
  - Tabs (`table_screen.gd`'s `_style_tabs()`) redesigned from a filled,
    gold-bordered pill to a clean underline style with no background box
    on either state — matches the reference screenshots' sub-navigation
    (e.g. the player profile's Overview/Personal/Performance tabs) much
    more closely than the boxed look.
  - Also exported and verified a real standalone `.exe`
    (`godot_client_dist/StumpedGodot.exe`) this session, since the user
    correctly pointed out that screenshots weren't enough to judge the
    actual result — see `godot_client/README.md`'s new "Exporting a
    standalone .exe" section.
- No Python-side changes; 194 tests unaffected, Godot smoke test clean
  across 3 runs, visually verified via screenshot capture.

## [0.51.0] - 2026-07-21

### Added

- **Graphics migration: Selection batting aggression/style** — the last
  gap in Selection's feature parity with `ui/selection.py` (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`). Selection gained a second
  "AGGRESSION" tab (using `table_screen.gd`'s tabbed sub-navigation,
  extended to support per-tab `row_buttons`/`row_action` overrides, not
  just different columns) with STYLE and AGGRO buttons per player.
  - New `cycle_batting_style`/`cycle_batting_aggression` IPC methods
    mirror `ui/selection.py`'s two independent click zones exactly:
    style steps through Silly/Blitz/Build/Rotate and snaps aggression to
    that style's default; aggression separately wraps 1-10, both gated
    on XI membership. `get_selection` now also returns each player's
    `batting_style`/`batting_aggression`.
  - New smoke-test exercise switches to the AGGRESSION tab and presses
    the real STYLE/AGGRO buttons, asserting both values actually changed.
- 5 new tests (194 total), Godot smoke test clean across 3 consecutive
  runs, visually verified via screenshot capture, pygame client
  unaffected.

## [0.50.0] - 2026-07-21

### Added

- **Graphics migration: styled standings + inbox cards**, closing out the
  reference-derived visual backlog for this pass (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`). League standings rows now show a
  numbered position badge (gold-filled for the user's own team) instead
  of a bare "N." prefix; inbox rows show a priority-coloured dot
  (red/gold/muted for HIGH/MEDIUM/LOW) with unread messages in full
  contrast and read ones dimmed.
  - Fixed a real bug this surfaced: the position badge initially showed
    "1.0", "2.0" — Godot's JSON parser has no int/float distinction, so
    raw numeric values need `JsonFormat.value()` before display; missed
    it in the first pass of this change.
- Godot smoke test clean across 3 consecutive runs, visually verified via
  the temporary screenshot-capture mode (not committed), pygame client
  and its 189 tests unaffected (no Python-side changes this pass).

## [0.49.0] - 2026-07-21

### Added

- **Graphics migration: styled Dashboard fixture card**, continuing the
  FM26-referenced redesign (see `docs/GRAPHICS_MIGRATION_PLAN.md`). The
  Dashboard's "NEXT FIXTURE" card now shows both teams as crest badges
  (coloured circle + initials, same treatment as the persistent header's
  club crest) either side of a muted "vs", with the format/date centred
  underneath — replacing a single plain text line. Also fixed the
  Dashboard's background colour, a leftover from before the v0.41.0
  theme pass that never got updated to the shared palette.
- No Python-side changes; 189 tests unaffected, Godot smoke test clean
  across 3 runs, visually verified via screenshot capture.

## [0.48.0] - 2026-07-21

### Fixed

- **Graphics migration: Selection column overflow**, continuing the
  FM26-referenced redesign (see `docs/GRAPHICS_MIGRATION_PLAN.md`).
  Selection's row (name/role/OVR/order + 4 row buttons) exceeded 1280px
  and scrolled horizontally, clipping the DOWN button. Tightened column
  widths and shortened CAPTAIN/KEEPER to CAPT/WK, and `table_screen.gd`'s
  `row_buttons` spec now accepts a per-button `"width"` override (used
  here for narrower CAPT/WK/UP/DOWN buttons) instead of every row button
  being a fixed 90px regardless of label length.
- Godot smoke test clean across 3 consecutive runs, visually verified via
  the temporary screenshot-capture mode (not committed) — Selection now
  fits without a horizontal scrollbar. No Python-side changes; 189 tests
  unaffected.

## [0.47.0] - 2026-07-21

### Added

- **Graphics migration: secondary style tag**, continuing the
  FM26-referenced redesign (see `docs/GRAPHICS_MIGRATION_PLAN.md`).
  `table_screen.gd` columns can now render as a muted secondary label
  (`{"muted": true}`) instead of full-contrast text — added a STYLE
  column (`bowling_style`, e.g. "Medium", "Off-Spin") to Squad's GENERAL
  INFO tab, right after ROLE, mirroring the reference screenshots' muted
  secondary tag next to a player's name/role (e.g. "Stroke Maker").
- Godot smoke test clean across 3 consecutive runs, visually verified via
  the temporary screenshot-capture mode (not committed), pygame client
  and its 189 tests unaffected (no Python-side changes this pass).

## [0.46.0] - 2026-07-21

### Added

- **Graphics migration: tabbed sub-navigation**, closing out the biggest
  remaining structural gap identified in the FM26-referenced redesign
  (see `docs/GRAPHICS_MIGRATION_PLAN.md`). `table_screen.gd` now supports
  an optional list of extra tabs beyond the default "GENERAL INFO" view —
  same IPC method and data, just a different column set per tab, so
  switching tabs never needs a second round trip. Squad gained an
  "ATTRIBUTES" tab (batting/bowling/fielding/mental group-average bars),
  mirroring the reference's "General Info / Stats / Injuries" pattern.
  - `get_squad` now also returns each player's `batting_avg`/`bowling_avg`/
    `fielding_avg`/`mental_avg`, reusing `src/models/squad_metrics.py`'s
    `group_average()` — the same pure helper the pygame client already
    uses, not a duplicated calculation.
- New smoke-test exercise presses the real tab button and asserts the
  header row's columns actually changed (`NAME/AGE/ROLE/OVR/FORM/MORALE`
  → `NAME/BATTING/BOWLING/FIELDING/MENTAL`), not just that no error fired.
- 1 new test (189 total), Godot smoke test clean across 3 consecutive
  runs, visually verified via screenshot capture, pygame client unaffected.

## [0.45.0] - 2026-07-21

### Added

- **Graphics migration: form/morale bar meters**, continuing the
  FM26-referenced redesign (see `docs/GRAPHICS_MIGRATION_PLAN.md`).
  `table_screen.gd` columns can now render a 0-100 stat as a coloured
  horizontal bar (`{"bar": true}`) instead of a bare number — the fill
  colour follows the same FM-style attribute tiers as the pygame client's
  `attribute_colour()` (red/amber/white/green/gold). Added FORM and
  MORALE bars to Squad.
- Known minor layout gap: Squad's row now has enough columns that it
  scrolls horizontally at 1280px width (same pre-existing behaviour
  Selection already had with its 4 row buttons) — not addressed this pass.
- No Python-side changes; 188 tests still pass, Godot smoke test clean
  across 3 runs, visually verified via screenshot capture.

## [0.44.0] - 2026-07-21

### Added

- **Graphics migration: sidebar nav icons**, continuing the FM26-referenced
  redesign (see `docs/GRAPHICS_MIGRATION_PLAN.md`). New `nav_icon.gd`
  draws a small geometric glyph per nav section in code (no icon asset
  pipeline exists) — distinct shapes for Dashboard/Inbox/Squad/Selection/
  Training/Youth Academy/Medical/Match/Recruitment/Transfers-Offers/Staff/
  Finances/Facilities/Career, recoloured gold when that screen is active,
  matching the reference sidebar's icon-per-item layout.
  - Fixed a real layout bug this surfaced: nav buttons collapsed to
    near-zero height once their built-in `text` was replaced with a
    custom icon+label child row, since a `Button` with no text has almost
    no implicit minimum size — rows overlapped until an explicit
    `custom_minimum_size` was set.
- Godot smoke test clean across 3 consecutive runs, visually verified via
  the temporary screenshot-capture mode (not committed), pygame client
  and its 188 tests unaffected (no Python-side changes this pass).

## [0.43.0] - 2026-07-21

### Added

- **Graphics migration: nation flag icons**, continuing the FM26-referenced
  redesign (see `docs/GRAPHICS_MIGRATION_PLAN.md`). `table_screen.gd`
  columns can now render a flag icon (`{"flag": true}`) from a player's
  `nationality` field — added to Squad, Selection, Transfers, and Youth
  Academy, ahead of the player name, matching the reference screenshots.
  `app_theme.gd`'s `flag_texture()` mirrors
  `ui/widgets/country_flag.py`'s alias/ISO-code mapping exactly, reusing
  the same bundled Flagpedia PNGs (now also copied into
  `godot_client/assets/images/flags/`) rather than maintaining a second
  set. Entities with no ISO flag (e.g. "West Indies") render no icon
  rather than a placeholder — a smaller gap than pygame's drawn fallback,
  left as a known minor cosmetic difference rather than duplicating that
  drawing logic for now.
- Godot smoke test clean across 3 consecutive runs, visually verified via
  the temporary screenshot-capture mode (not committed), pygame client
  and its 188 tests unaffected (no Python-side changes this pass).

## [0.42.0] - 2026-07-21

### Added

- **Graphics migration: persistent club header + coloured role pills** (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`), continuing the redesign against the
  FM26/Cricket Management reference screenshots.
  - New persistent header bar (crest initials, team name, date/next-fixture
    subtitle, and an ADVANCE DAY button) always visible above the sidebar
    and content, replacing Dashboard's own corner button — matches the
    reference layout where the club identity bar and the advance action
    are chrome, not part of any one screen. Fed by `get_dashboard`, now
    also returning the current in-game `date`.
  - `table_screen.gd` columns can now render as coloured capsule "pill"
    badges (`{"pill": true}`) instead of plain text — applied to the ROLE
    column on Squad, Selection, Transfers, and Youth Academy
    (Batsman/Bowler/Wicketkeeper/All-Rounder each get a distinct colour),
    mirroring the reference screenshots' coloured role tags.
  - `advance_day` is now reachable from any screen (not just Dashboard);
    the smoke test's advance-day exercise now asserts the header's date
    text actually changed, not just that the call returned without error.
- 1 new test (188 total), Godot smoke test clean across 3 consecutive
  runs, visually verified via the temporary screenshot-capture mode
  (not committed), pygame client unaffected.

## [0.41.0] - 2026-07-21

### Added

- **Graphics migration: real visual theme + Match Day screen** (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`). The Godot client had no custom
  `Theme` at all until now — every screen rendered in the engine's
  unstyled default gray, which is what "the UI still looks terrible" was
  pointing at.
  - New `AppTheme` (`godot_client/scripts/app_theme.gd`) ports the pygame
    client's "Test at Dusk" design tokens (`src/views/theme.py`) — same
    palette, same Inter font — into a Godot `Theme` applied at the shell
    root so it cascades to every screen. Styled buttons, panels, and a
    highlighted active nav item replace the plain default controls.
  - `table_screen.gd`'s rows are now zebra-striped `PanelContainer` cards
    with a distinct header bar, instead of bare `Label`s in an `HBox`.
  - Deleted `squad_screen.gd`/`.tscn` (a near-duplicate of
    `table_screen.gd` predating its generalisation) and rebuilt Squad on
    the shared table component — one less bespoke screen to maintain, and
    Squad now gets the same zebra/header styling for free.
  - New **Match Day** screen (`match_screen.gd`, `ground_view.gd`)
    replaces the old "Coming Soon" placeholder: next-fixture header, the
    selected XI in batting order, and a drawn cricket ground with default
    fielding positions (wicketkeeper, slips, gully, point, cover,
    mid-off/on, midwicket, square leg, fine leg, third man) — referencing
    Cricket Captain's wagon-wheel field view. New `get_match_preview` IPC
    method combines the next fixture with the current selection. This is
    honestly a pre-match hub, not a live ball-by-ball simulation — that
    remains the single biggest deferred item.
  - Fixed a real, pre-existing bug surfaced while building the Dashboard
    card styling: `get_dashboard`'s `standings` never had a `position`
    field (`fetch_league_standings()` doesn't return one — the pygame
    client enriches it locally in `ui/dashboard.py` but the IPC path
    never did), so every Godot standings row showed "0." instead of its
    rank. Fixed at the source in `ipc_server.py`.
- 2 new tests (187 total), Godot smoke test clean across 3 consecutive
  runs (including a real visual check via a temporary screenshot-capture
  mode, not committed), pygame client unaffected.

## [0.40.0] - 2026-07-21

### Added

- **Graphics migration: Selection batting order (UP/DOWN reorder)** (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`):
  - New `move_batting_up`/`move_batting_down` IPC methods, mirroring
    `ui/selection.py`'s arrow-click swap of adjacent entries in `self.xi` —
    same no-op-at-the-boundary behaviour, same rejection when the player
    isn't in the XI.
  - `get_selection`/`toggle_xi`/`set_captain`/`set_keeper` now return
    players XI-first in batting order (rest of the squad follows), so the
    Godot table's row order *is* the batting order — no client-side
    sorting needed. `xi_status` now shows the batting position number
    (e.g. `"4/C"`) instead of a bare `"XI"` tag.
  - Selection screen gained UP/DOWN row buttons alongside CAPTAIN/KEEPER.
  - Verified against real data: swap of adjacent players, no-op at the
    top/bottom of the order, and rejection for a non-XI player.
- 4 new tests (185 total), Godot smoke test extended with a dedicated
  batting-order exercise that checks the row order actually changed (not
  just that the call returned without error), pygame client unaffected.

## [0.39.0] - 2026-07-21

### Added

- **Graphics migration: Selection captain/keeper designation** (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`):
  - New `set_captain`/`set_keeper` IPC methods, mirroring
    `ui/selection.py`'s captain/keeper cycle buttons — must be an XI
    member, same rule, writing the same `selection.captain`/
    `selection.keeper` save-state keys.
  - Selection screen now has CAPTAIN/KEEPER buttons per row, alongside the
    existing whole-row click for XI toggling — the first screen combining
    `table_screen.gd`'s `row_action` and `row_buttons` on the same table.
  - Verified against real data, including the rejection path: assigning
    captain to a non-XI player correctly raises the same validation error
    the pygame client enforces.
- 3 new tests (181 total), match-engine statistics unaffected, Godot smoke
  test clean across multiple runs, pygame client rebuilt and unaffected.

## [0.38.0] - 2026-07-21

### Changed

- **Toolchain upgraded for the Steam release** (see
  `docs/GRAPHICS_MIGRATION_PLAN.md` "Toolchain" section for full detail):
  - **Python 3.12.10 → 3.14.6**, via a new project-local venv at
    `cricket_manager/.venv` (previously the system interpreter was used
    directly). Verified before switching: the full 178-test suite,
    `validate_match_engine.py`, and a real PyInstaller build with passing
    packaged diagnostics all run clean under 3.14.6. `pygame-ce` 2.5.7 and
    `PyInstaller` 6.21.0 (both already latest) both ship official `cp314`
    wheels.
  - **Godot 4.3.0 → 4.7.1 stable**. The existing project loaded and ran
    with zero code changes required.
  - `godot_client/scripts/ipc_bridge.gd` now resolves the project venv's
    `python.exe` directly instead of relying on `where python` PATH
    resolution, which was fragile — it could silently pick up an
    unrelated interpreter.

### Fixed

- **Two real, pre-existing bugs surfaced by the Godot version bump** (not
  caused by it — they'd been latent in the client since Phase 0):
  1. Godot's JSON parser returns every number as a float; every numeric
     table cell across every screen was rendering `"25.0"` instead of
     `"25"`. Fixed centrally via new `scripts/json_format.gd`
     (`JsonFormat.value()`), applied everywhere a raw IPC response value
     reaches a `Label`.
  2. The same float-vs-string mismatch meant `training_screen.gd`'s
     assignment lookup could never match its keys (`str(25.0)` != the
     server's `str(25)`) — the Training screen had been silently showing
     every player's focus as "None" regardless of what was actually
     assigned. Fixed via the same `JsonFormat.value()`.
- `godot_client/README.md` rewritten to reflect current status (16
  screens, not just the Phase 0 proof of concept) and the pinned toolchain.
- Main `README.md`'s Python version guidance updated from "3.10 or newer"
  to the specific tested version (3.14).

178 tests pass (unchanged — Python-side logic untouched, only the
interpreter/engine versions and Godot-side display formatting changed).
Godot smoke test clean across multiple consecutive runs on 4.7.1.

## [0.37.0] - 2026-07-21

### Added

- **Graphics migration: Selection screen, first new interactive screen
  since Recruitment** (see `docs/GRAPHICS_MIGRATION_PLAN.md`):
  - New IPC methods `get_selection`/`toggle_xi`: click a squad row to
    add/remove them from the starting XI (max 11 enforced server-side).
  - These write to the exact same `selection.xi` save-state key
    `ui/selection.py` already reads/writes via the generic `game_state`
    key-value store — pick an XI in either client and the other sees it.
    Pygame's selection reads use `.get()` with defaults throughout, so a
    Godot-only partial write (just `xi`, no `bowlers`/`captain`/`keeper`
    yet) doesn't break it.
  - New **Selection** screen (SQUAD nav group), built on the existing
    `table_screen.gd` — no new bespoke scene needed.
  - Verified against real state: toggling a player persists to
    `selection.xi` across a fresh backend process, not just in memory.
- 16 of 16 registered screens render, 15 with real data (only Match is a
  placeholder); 8 interactive write flows now exist. 3 new tests (178
  total), match-engine statistics unaffected, pygame client rebuilt and
  unaffected.

## [0.36.0] - 2026-07-21

### Added

- **Graphics migration: Staff release, seventh interactive flow** (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`):
  - New `release_staff` IPC method wraps the existing `sell_staff_member`
    (already used identically by the pygame client — deliberately leaves
    the role vacant rather than auto-replacing, same rule both clients
    share).
  - Staff screen now has a RELEASE button per row.
  - Verified against real state: releasing a staff member genuinely
    removes them from the roster and credits the fee.
- 7 of 14 real screens now have at least one write action. 1 new test (175
  total), match-engine statistics unaffected, pygame client rebuilt and
  unaffected.

## [0.35.0] - 2026-07-21

### Added

- **Graphics migration: Facilities upgrades, sixth interactive flow** (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`):
  - `get_facilities` now synthesizes a 7-row overview (current level +
    Ready/Building status per facility, from the team record + any active
    upgrade) alongside the existing upgrade-history list.
  - New `upgrade_facility` IPC method wraps `start_facility_upgrade`.
  - The Facilities screen now shows this actionable overview with an
    UPGRADE button per row instead of a read-only history list.
  - Verified against real state: clicking UPGRADE genuinely creates a
    `BUILDING` facility_upgrades row and charges the cost.

### Fixed

- `table_screen.gd`'s row actions (`row_action`/`row_buttons`) silently
  swallowed IPC errors — clicking UPGRADE on a facility already mid-build
  looked like it succeeded (the screen just refreshed normally) when the
  backend had actually rejected it. Found via the smoke test's own
  verification discipline: repeated runs against the same persistent dev
  save naturally hit "already building" on the second click, producing a
  false-clean result. `_dispatch()` now surfaces `response.has("error")` on
  the title bar and via `push_error`, matching every other backend-error
  path in the file.
- 15 of 15 registered screens render, 14 with real data; 6 interactive
  write flows now exist. 4 new tests (174 total), match-engine statistics
  unaffected, pygame client rebuilt and unaffected.

## [0.34.0] - 2026-07-21

### Added

- **Graphics migration: Staff Market signing** (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`):
  - New IPC methods `get_staff_market` (wraps `browse_staff_market`) and
    `sign_staff` (bid-then-immediately-accept, mirroring
    `ui/staff.py`'s `_act_on_selected()` — `make_staff_offer` followed by
    `resolve_staff_offer(..., True)` in one call).
  - New **Staff Market** screen (CLUB nav group, next to Staff): click a
    listed staff member to sign them at their listed fee/wage, via
    `table_screen.gd`'s existing `row_action`.
  - Verified against real state: a signed staff member genuinely appears
    in the buying club's roster afterward (`fetch_staff` confirms it), not
    just "the IPC call succeeded".
- 15 of 15 registered screens render, 14 with real data (only Match is a
  placeholder); 5 interactive write flows now exist across the Godot
  client. 2 new tests (172 total), match-engine statistics unaffected,
  pygame client rebuilt and unaffected.

## [0.33.0] - 2026-07-21

### Added

- **Graphics migration: Offers screen (Accept/Reject)** (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`):
  - `table_screen.gd` gained a generic optional `row_buttons` — explicit
    action buttons appended to each data row, for screens needing more
    than one action per row (`row_action` only supports one whole-row
    click).
  - New **Offers** screen (RECRUITMENT nav group): every pending transfer
    offer with ACCEPT/REJECT buttons calling `resolve_transfer_offer` —
    reuses `get_transfer_market`'s existing `offers` list, no new IPC
    method needed.
  - Verified against real behaviour: clicking Accept ran the actual
    affordability check, correctly flipping an offer to `FAILED` in one
    verification run when the buying club couldn't afford it, rather than
    faking success.
- 14 of 14 registered screens now render, 13 with real data (only Match is
  a placeholder); 4 interactive write flows now exist across the Godot
  client. 170 tests still pass, match-engine statistics unaffected, pygame
  client rebuilt and unaffected.

## [0.32.0] - 2026-07-21

### Added

- **Graphics migration: two more interactive flows** (see
  `docs/GRAPHICS_MIGRATION_PLAN.md`):
  - `table_screen.gd` gained a generic optional `row_action` — click a data
    row to fire another IPC call built from that row's own fields
    (`params_from_row`) plus optional constants (`params_fixed`), then
    refresh. Also gained `dim_when_key` to visually fade rows matching a
    boolean field.
  - **Inbox** rows now mark themselves read on click and dim once read
    (`mark_message_read`).
  - **Transfers** rows now submit a transfer offer at the listed asking
    price on click (`submit_transfer_offer`).
  - Verified against the real save, not just "no error returned": clicking
    an inbox row flips its `read` flag in the database; clicking a
    transfer row creates a real `PENDING` offer row. `shell.gd`'s smoke
    test emits real Godot input/button signals (not direct IPC calls) so a
    broken UI wire-up fails the test even if the backend endpoint is fine.
- 170 tests still pass, match-engine statistics unaffected, pygame client
  rebuilt and unaffected.

## [0.31.0] - 2026-07-21

### Added

- **Graphics migration: Recruitment ported + first interactive flow** (12
  of 13 screens now real; see `docs/GRAPHICS_MIGRATION_PLAN.md`):
  - Extracted the pygame Recruitment Hub's squad-gap/contract-watch/
    objectives logic out of `ui/recruitment.py` into pygame-free
    **`src/models/recruitment.py`** (`role_gaps`, `weakest_attribute_group`,
    `contract_watch`) and **`src/models/squad_metrics.py`**
    (`group_average`, `estimated_value`, moved from
    `ui/shared_components.py`, which now re-exports them so every existing
    caller keeps working unchanged). Both the pygame client and the new
    `get_recruitment` IPC method now call the same functions.
  - New bespoke **Recruitment** screen in Godot (tiled like Dashboard).
  - **First interactive (write) flow**: Dashboard's "ADVANCE DAY" button
    calls `advance_day` and refreshes — the actual game-loop driver.
    `shell.gd`'s smoke test now emits the button's real signal to verify
    the whole click→backend→refresh path.
- Only **Match** remains a placeholder — deliberately deferred, needs a
  live ball-by-ball feed rather than a data table.
- 8 new tests (`test_shared_recruitment_logic.py`, `get_recruitment`
  coverage in `test_ipc_server.py`); 170 total, all pass; match-engine
  statistics unaffected.

## [0.30.0] - 2026-07-21

### Added

- **Graphics migration: 3 more real screens** (11 of 13 now real, up from
  8 — see `docs/GRAPHICS_MIGRATION_PLAN.md`):
  - **Training** — bespoke Godot screen merging `get_training`'s player
    list with its per-player focus/intensity assignments.
  - **Youth Academy** — new `get_youth_academy` IPC method (server-side
    filter of the existing squad data to `academy_squad` players; no new
    database function needed).
  - **Medical Centre** — new `get_medical` IPC method wrapping
    `fetch_active_injuries`, via the reusable `table_screen.gd`.
- Only **Match** (needs a live ball-by-ball feed, a fundamentally bigger
  job) and **Recruitment** (blocked on extracting `ui/recruitment.py`'s
  squad-gap logic out of the pygame-dependent UI layer first) remain as
  placeholders. 2 new IPC tests (16 total in `test_ipc_server.py`).

## [0.29.0] - 2026-07-21

### Added

- **Graphics migration Phase 1 + partial Phase 2** (see
  `docs/GRAPHICS_MIGRATION_PLAN.md` "Status" section for full detail):
  - `cricket_manager/ipc_server.py`: 14 JSON-RPC methods now wrap existing
    `database.py`/`competition.py` functions (dashboard, inbox, standings,
    staff, transfer market + offer submission, scouting assignments,
    finances, facilities, training, honours, day advancement). Covered by
    14 new tests in `tests/test_ipc_server.py`.
  - `godot_client/`: a real sidebar shell (`scenes/shell.tscn`, mirrors
    `main.py`'s `NAV_GROUPS`) now switches between 8 working, real-data
    screens (Dashboard, Squad, Inbox, Staff, Transfers, Finances,
    Facilities, Career/Honours) — 6 of them built on one new reusable
    `table_screen.gd` component, mirroring how the pygame client reuses
    `ui/widgets/datatable.py`'s `DataTable`. Screens not yet ported
    (Training, Youth Academy, Medical Centre, Match, Recruitment) show the
    same "Coming Soon" placeholder the pygame `BaseScreen` falls back to.
  - `shell.gd`'s own `--smoke-test` mode cycles every registered screen and
    fails on any backend-error title; caught two real GDScript bugs before
    they shipped (a type-inference issue and a `configure()`-timing bug).
- The pygame client is unaffected and remains the shipped product — every
  screen ported to Godot so far is read-only display; no interactive flows
  (selection, contracts, hiring, the match view) are ported yet.

## [0.28.0] - 2026-07-21

### Added

- **Graphics migration groundwork** (see `docs/GRAPHICS_MIGRATION_PLAN.md`):
  a hybrid Godot 4 (free, MIT) presentation layer talking to the existing,
  unchanged Python simulation/data layer over a new JSON-RPC-over-stdio
  backend (`cricket_manager/ipc_server.py`). Phase 0 proof of concept
  (`godot_client/`) is done and verified: a real anchored/container-based
  Squad table rendering live save data, headless-smoke-testable via
  `godot --headless --path godot_client -- --smoke-test`.
- The pygame client is unaffected and remains the shipped product this
  release — nothing here changes what ships in `Stumped.exe`.

### Fixed

- `src.utilities.launcher.prepare_environment()` could pop a native Windows
  "restore last session?" dialog after an unclean exit; harmless for the
  interactive pygame client but hangs any headless caller forever (found
  while building the Godot IPC backend). New `interactive` parameter
  (default `True`, unchanged pygame behaviour); headless callers must pass
  `interactive=False`.

## [0.27.0] - 2026-07-21

### Added

- **Active scouting assignments**: send a named scout to file a report on a
  specific player over a fixed number of days (`database.py`
  `create_scouting_assignment`/`fetch_scouting_assignments`/
  `advance_scouting_assignments`, new `scouting_assignments` table). A
  scout can only hold one assignment at a time; longer assignments sharpen
  the read (effective judging ability rises with total days invested,
  capped at +4). Wired into `CompetitionEngine.advance_day()` — a
  completed assignment files an inbox report automatically.
- `ui/transfers.py`: a "SEND SCOUT (10 DAYS)" button on the selected
  scouted player sends your best available (not already busy) scout.
- `ui/recruitment.py`: new "Scouting Assignments" tile on the Recruitment
  Hub shows active assignments' countdown and completed ones' estimate —
  the "Requirements" tile's static suggestions now have somewhere to go.
- Closes docs/UX_ROADMAP.md item 3 (scouting assignments).

## [0.26.0] - 2026-07-21

### Added

- **Recruitment Hub** (`ui/recruitment.py`, new "Recruitment" screen at the
  top of the RECRUITMENT nav group): a tiled front page over data that
  already existed but had no single home — Recruitment Objectives (weakest
  attribute group + division context), Squad Gaps (role headcount vs.
  target, e.g. too few frontline bowlers), Contract Watch (players expiring
  within a year), and Requirements (auto-derived scouting asks from the
  squad gaps). Quick-action buttons jump straight to Transfers, Staff
  Market, and the Academy. Closes docs/UX_ROADMAP.md's #1 priority.

## [0.25.0] - 2026-07-21

### Added

- **Player temperament** (`src/models/player.py` `natural_batting_aggression`,
  `natural_bowling_aggression`): every player now has an inherent scoring/
  attacking style derived from their real attributes (attack vs.
  concentration for batting, pace/variation vs. accuracy for bowling) —
  the accumulator-vs-boundary-hitter distinction other cricket management
  sims model as a player trait, not just a manager-chosen dial. Wired into
  `ui/selection.py`: Auto-Select now assigns batting styles from real
  temperament instead of a single crude "attack >= 75" check, and any
  player manually added to the XI is seeded with a sensible aggression
  default instead of a flat neutral 5.

## [0.24.0] - 2026-07-21

### Added

- **Squad Planner** (`ui/squad.py` Planner tab): projects each player's
  contract status across the current season and the following two seasons
  (Contracted / Expires this year / Free agent), derived directly from
  `contract_years_remaining`. Closes the biggest single gap flagged in the
  new UX roadmap.
- **Navigation restructure**: sidebar groups renamed and regrouped to match
  a Portal / Squad / Match Day / Recruitment / Club / Career information
  architecture (`main.py` `NAV_GROUPS`), translated from a full Football
  Manager 26 feature breakdown the user supplied.
- **`docs/UX_ROADMAP.md`** (new): maps every FM26 tab/feature to its Stumped!
  cricket equivalent — Have / Partial / Planned — and sequences the next
  four priorities (Squad Planner done this release; Recruitment Hub, active
  scouting assignments, and opposition reports next).

## [0.23.0] - 2026-07-21

### Added

- **Staff transfer market**: a new Market tab on the Staff screen lets you
  browse every other club's coaches, medics, and scouts, priced by ability
  and age, and sign them for an immediate fee (cash moves both ways).
  Release your own staff back to the market for a fee at any time — exactly
  like listing a player, the vacated role must then be filled from the
  Market rather than auto-replacing.
- **Staff retirement and regeneration**: staff now retire at a rising
  chance from age 66 onward at each season rollover, and are immediately
  replaced with a fresh, realistically-attributed staff member so no
  department is ever left empty.
- **Live commentary modes**: a COMM: FULL/KEY MOMENTS toggle on the match
  screen. Key Moments strips routine dot-balls and singles from the
  ball-by-ball log, keeping it readable at Fast/Instant speeds — the
  score, beads, and scorecards are unaffected either way.

## [0.22.0] - 2026-07-21

### Added

- **Coaching, Medical, and Scouting staff**: every club now fields a real
  named roster (Head/Batting/Bowling/Fielding/Fitness Coaches, Doctor,
  Physio, Chief Scout, Scout), each with role-appropriate 1-20 attributes
  (`src/models/staff.py`, new `staff` DB table). Existing saves are
  backfilled automatically.
  - **Coaches** now genuinely accelerate training: the assigned discipline's
    coach quality scales daily training gains (a poor coach can more than
    halve progress; an elite one boosts it by up to ~30%).
  - **Medical staff** reduce match injury likelihood and shorten recovery
    time on top of the Medical Centre facility level. A new **Medical
    Centre** screen shows active injuries, return dates, a physiotherapy
    risk-assessment rating, and players at elevated risk.
  - **Scouts** now genuinely matter: the Transfer Market shows an estimated
    OVR/POT with a scout confidence percentage instead of the exact true
    value — a poor scouting department's estimates carry real error; a
    world-class one is nearly exact.
  - Staff age and slowly improve or decline at each season rollover.
  - New **Staff** screen (Coaching/Medical/Scouting tabs with a detail panel).
- **ASTRAIVA (Pty) Ltd** publisher mark on the splash screen.

## [0.21.0] - 2026-07-21

### Added

- **Contract negotiation**: a full offer/counter/accept flow reachable from
  any player profile's NEGOTIATE button. Propose weekly wage, contract
  length, and a signing bonus; the player accepts, counters with a figure
  based on their true valuation, or rejects outright, weighing morale, age,
  and existing contract security (`src/models/contracts.py`). Agreed terms
  are written straight to the save.
- **Targeted academy recruitment**: the Youth Academy screen gained a
  "Scout For" role selector (Any / Batsman / Pace Bowler / Spin Bowler /
  All-Rounder / Wicketkeeper). Recruits generate with realistic role-true
  skills — a requested bowler will never quietly out-bat a requested
  batsman, and pace/spin focus genuinely biases each prospect's skill split.
- Real country flag artwork (public-domain Flagpedia PNGs) replaces the
  hand-drawn flag approximations throughout the game.
- Spatial analytics on the player Match Stats tab now has a **This
  Match / Season** filter and a much larger wagon-wheel/bowling-map area,
  so it stays legible as career data accumulates.
- A club crest now anchors the top bar, and the sidebar footer reads
  "© ASTRAIVA (Pty) Ltd" (all legal/credits text updated to match).

### Fixed

- **Match screen score-bug and action row overhaul**: the live header was
  cramming six unrelated fields into one 58px row with hardcoded pixel
  offsets, causing format/DRS/status text to visibly overlap and merge at
  1280x720. It's rebuilt as a six-column grid with fixed proportional
  widths and vertical dividers, so no two fields can ever collide. The
  ten-button action row (PREDICT/AUTO/NEXT BALL/…/EXIT) — badly cramped
  into one row — now spans two clearly-spaced rows.
- **Fullscreen text blur on common monitors**: the fullscreen logical
  canvas always targeted ~1920x1080, which is a *non-integer* stretch on
  a 2560x1440 desktop (1.33x) and blurs every glyph. Common resolutions
  (1440p, 4K, ultrawide, 5K) now resolve to an exact integer-scale logical
  canvas (2560x1440 → clean 2x from 1280x720; unchanged clean 2x for 4K).
- **Blocky text and jagged curves**: text now renders at native pixel size
  (the previous supersample-then-downscale pass had gone soft on larger
  monitors) and every remaining aliased circle/polygon outline (radar
  chart, portraits, gauges) now draws anti-aliased.
- Higher-detail procedural player portraits: 4x supersampling (was 3x), a
  simple kit collar, and a soft edge vignette.
- Removed the leftover "UI FOUNDATION 2.14+" placeholder label.

## [0.19.1] - 2026-07-21

### Fixed

- Crash when hovering a Squad row: the Skills-tab mental average had
  overwritten each row's mental attribute dictionary, breaking the player
  quick-card (and profile modal). The average now lives under its own key,
  the quick-card is defensive against malformed rows, and a regression test
  hovers real table rows.

## [0.19.0] - 2026-07-21

### Added

- **Player quick-card**: hovering any row on the Squad table shows a compact
  popover — portrait, role, age, nationality, tier-coloured overall,
  potential stars, and form/fitness/morale bars — clamped to the window.
- **Squad view tabs**: Overview / Skills / Contracts swap the shared table's
  column sets (per-discipline averages and potential on Skills; value, wage,
  and years remaining on Contracts).
- **Accessibility settings** (persisted to the save, applied live):
  - Reduced Motion — disables the wicket flash and hover growth.
  - Colour-blind Glyphs — forces result glyphs on the Over Beads.
  - UI Scale — 100% / 110% / 120% interface text.
- **Matchday polish**: DRS review pips in the score bug and a fading red
  band flash on wickets (suppressed by Reduced Motion).

## [0.18.0] - 2026-07-21

### Changed

- **Sharper, modern rendering pass**: all UI text is now supersampled (drawn
  at 2× and smooth-downscaled, with a render cache) for crisper glyph edges,
  and every circle in the interface — beads, portraits, gauges, menu motifs —
  is anti-aliased.
- Card accent rails and hover borders follow the signature red / sky accent
  instead of the legacy green.

### Added

- **XI Balance meter** on the Selection screen: live batting depth, bowling
  options, pace/spin mix, and wicketkeeper checks, tier-coloured, updating as
  the XI changes — cricket's answer to FM's tactic familiarity bar.

## [0.17.0] - 2026-07-21

### Added

- **Grouped sidebar navigation** — CLUB / SQUAD / MATCH / BUSINESS / WORLD /
  SYSTEM section headers per the approved redesign.
- **CONTINUE ▸** — the context-aware loop button in the header band: advances
  one day and stops on the Pre-Match screen when a fixture is due; SAVE
  becomes a quiet secondary control.
- **TabBar** component — text tabs with the sliding signature-red underline,
  adopted on the Career screen.

### Fixed

- Card headers and gradients now render in fully headless contexts (render
  audits before a display exists).

## [0.16.0] - 2026-07-21

### Changed

- New **"Test at Dusk"** skin per the approved redesign (docs/DESIGN.md):
  warm near-black canvas, warm charcoal surfaces, cricket-ball red as the
  signature action colour, gold ratings, pitch green positives, and a cool
  sky accent reserved for links and info.
- Button hierarchy redesigned: primary actions are now signature red,
  confirm/positive actions green, and destructive actions render as red
  outline buttons; sidebar selection and the top action button follow the
  signature red.
- The live match header band is tinted signature red — management screens
  stay calm, match screens carry broadcast energy.

### Added

- **Over Beads** — Stumped!'s signature six-ball strip widget (hollow dot,
  green runs, gold boundary, red wicket, sky extras), now rendering the
  current over on the live match footer.
- Automated WCAG contrast tests: primary text AAA on canvas, secondary text
  AA on cards, bold text AA on the signature red.

## [0.15.0] - 2026-07-21

### Added

- **T10 format**: a fully playable 10-over format (60 balls, 12-ball bowler
  limit, 3-over powerplay, over-5 drinks break, tuned scoring baselines),
  selectable in custom tournament setup.
- **Wicketkeeping depth**: weak glovework now leaks byes on missed takes —
  byes are credited to extras, rotate the strike correctly, and produce their
  own commentary; totals reconcile exactly.
- **Deeper finances**: a monthly profit-and-loss inbox digest on the 1st of
  each month with per-category income/expense lines and the closing balance.

### Changed

- The engine's overs limits are now derived from a single `overs_limit()`
  helper instead of scattered T20/ODI conditionals, so new formats inherit
  projections, DLS reductions, and declaration logic automatically.

## [0.14.0] - 2026-07-21

### Added

- Permanent honours: league champions of both divisions and the Knockout Cup
  winners are written to a new `honours` table at season end (older saves
  migrate automatically), and the Career screen's Trophy Cabinet now shows the
  club's real silverware.
- Season-end inbox briefings: a silverware celebration when the user's club
  wins a title, the full individual Season Awards list, and a board season
  review whose tone follows the board-confidence model.
- The match engine now logs real fielding chances per batter (dropped
  catches, missed stumpings, missed run-outs) and surfaces them on each
  delivery event; the player Match Stats chances panel now shows genuine
  dropped-catch and let-off counts instead of estimates.

## [0.13.0] - 2026-07-21

### Added

- New **Career** screen in the sidebar with four tabs:
  - **Overview** — board confidence and manager reputation gauges with a
    written board verdict, plus season position, record, points, and NRR.
  - **World Ratings** — ICC-style 0–1000 ranking points for the top 20
    batters, bowlers, and all-rounders across every club in the world.
  - **Awards** — live season-award leaders (Batter, Bowler, Young Player, and
    Player of the Season).
  - **Trophies** — the club's trophy cabinet, ready to collect honours.
- `src/models/career.py`: pure, tested models for board confidence, manager
  reputation, world rating points, and season awards, shared with future
  season-end processing.

## [0.12.0] - 2026-07-21

### Added

- Momentum chart in the match Stats Hub: a rolling four-over swing line
  (runs scored minus wicket damage) coloured green/red around the axis.
- Continuous low crowd ambience during live matches, started on the first
  delivery and faded out when leaving the match screen.
- Broadcast-style audio ducking: the crowd bed dips under the wicket roar and
  swells back in over a few seconds.

### Changed

- Live match header restyled as a broadcast score bug: accent gradient,
  underline rail, a coloured weather pip, and a pitch-wear meter that shifts
  green → amber → red as the surface deteriorates.

## [0.11.0] - 2026-07-20

### Added

- FM-style five-star ability and potential ratings (half-star precision) on
  the player profile, via a new reusable `StarRating` widget.
- Market value on the player profile's contract card, computed from the live
  transfer valuation model.
- A 30-match form sparkline on the player profile's contract and traits card.
- Headless render tests covering the star widget, attribute colour tiers, and
  every player-profile tab.

## [0.10.0] - 2026-07-20

### Changed

- New "Midnight Pitch" interface skin: deeper blue-black canvas, electric
  sky-blue action accent, refreshed surfaces, borders, and text colours across
  every screen, the pygame-gui theme, and the packaged defaults.
- Football-Manager-style five-tier attribute colouring (red/amber/white/green
  and gold for elite 90+ ratings) applied through a single shared
  `attribute_colour()` token used by all attribute meters.
- Card headers now render with a subtle accent gradient and retained accent rail.

### Added

- `docs/UX_REVAMP.md`: competitor research (Cricket Captain 25/26, Cricket
  Management 26, From the Pavilion, Big Ant titles) and a five-phase UI/UX and
  feature-depth roadmap covering the player profile hub, broadcast-style
  matchday presentation, career depth, and systems depth.

## [0.9.0] - 2026-07-20

### Added

- Expanded player attributes, individual match tactics, bowling styles, energy,
  form, career records, spatial shot data, and delivery maps.
- Country-correct youth recruitment and country-specific generated identities.
- Scheduled, facility-aware training with intensity and injury-risk modelling.
- Dynamic weather, pitch wear, rain interruptions, and condition-aware AI.
- Twelve-team divisions, promotion and relegation, and an expanded domestic cup.
- Full transfer-market search, willingness-to-sell logic, and calculated prices.
- Seven upgradeable club facilities with interconnected sporting and financial effects.
- Detailed player, selection, match-perspective, weather, pitch, and analytics views.

### Changed

- Refined the warm dark interface for 1280x720 through 4K displays.
- Improved fictional procedural portraits, generated team identities, tables,
  widgets, help content, and accessibility of match analytics.
- Existing 16-team saves now migrate safely into the 24-team competition model.

### Verified

- 50 automated tests pass.
- Packaged startup diagnostics pass.
- Fifty-over fast simulation completes in under one second on the build machine.
