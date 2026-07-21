# Changelog

All notable changes to **Stumped!** are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

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
