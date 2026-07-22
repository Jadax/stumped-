# CURRENT — cross-agent handoff

- **Last updated:** 2026-07-22
- **Branch:** main
- **Version:** 0.59.0 (see `cricket_manager/config.json` and `CHANGELOG.md`)
  — pygame remains the shipped client this release; see below for the
  Godot migration now underway alongside it.
- **Company:** Owned by ASTRAIVA (Pty) Ltd (South Africa) — all copyright/credit
  text must say this, never "Stumped! development team".

## Graphics migration: pygame → Godot 4 (in progress, parallel track)

The user asked for an honest opinion on whether Python/pygame was holding
the game back visually; the answer given was: the simulation core isn't the
problem, the hand-rolled pixel-math UI layer is, and Godot 4 (free, MIT,
no royalties) is the right free/cheap target if a switch is ever made. The
user then asked to put a plan in place and start executing it. Full plan:
**`docs/GRAPHICS_MIGRATION_PLAN.md`**. Short version: **hybrid** — the
existing, tested Python `database.py`/`match_engine.py`/`competition.py`/
`src/models/*` stay exactly as they are and become the "backend"; a new
`godot_client/` becomes the presentation layer, talking to the backend over
a JSON-RPC-over-stdio pipe (`cricket_manager/ipc_server.py`, new). This
avoids re-deriving 146 tests' worth of validated simulation logic in
GDScript for zero player-facing benefit.

**Phase 0 (proof of concept) is done.** **Phase 1 (IPC method list, 25
methods) is done.** **Phase 2 (screen porting) is well underway: 15 of 16
registered screens now render real save data** — Dashboard, Squad,
Selection, Inbox, Staff, Staff Market, Transfers, Offers, Finances,
Facilities, Career/Honours, Training, Youth Academy, Medical Centre, and
Recruitment — through a working sidebar shell
(`godot_client/scenes/shell.tscn`) that mirrors `main.py`'s `NAV_GROUPS`.
Only **Match** (needs a live ball-by-ball feed — a much bigger, different
job) still shows the "Coming Soon" placeholder. Recruitment required a
real refactor first: its squad-gap/contract-watch logic used to live only
in the pygame UI layer, so it's now `src/models/recruitment.py` +
`src/models/squad_metrics.py`, called identically by both clients
(regression-tested). **Nine interactive (write) flows have shipped**:
Dashboard's "ADVANCE DAY" button; `table_screen.gd`'s generic `row_action`
(whole row clickable) powering Inbox mark-read-on-click, Transfers
submit-offer-on-click, Staff Market sign-on-click, and Selection's
add/remove-from-XI-on-click; and `table_screen.gd`'s generic `row_buttons`
(explicit per-row buttons) powering Offers' Accept/Reject, Facilities'
UPGRADE, Staff's RELEASE, and now Selection's CAPTAIN/KEEPER — the first
screen combining both mechanisms on the same table. Selection writes to
the exact same `selection.xi`/`selection.captain`/`selection.keeper`
save-state keys `ui/selection.py` already reads/writes, so picking an XI
(and captain/keeper) in either client is visible in the other. All verified
against real save-data changes — a message's `read` flag actually flips, a
real `PENDING` offer row is actually created, clicking Accept on an offer
genuinely ran the real affordability check (one test run flipped an
offer's status to `FAILED` when the buyer couldn't afford it, rather than
faking success), signing a staff member genuinely moves them into the
buying club's roster, clicking UPGRADE genuinely starts a real facility
build, releasing a staff member genuinely removes them from the roster and
credits the fee, and toggling a player genuinely persists to
`selection.xi` across a fresh backend process — not just "no error
returned". **One real bug was caught and fixed by this verification
discipline**: `table_screen.gd`'s row actions used to silently swallow IPC
errors (clicking UPGRADE on an already-building facility looked like it
succeeded); `_dispatch()` now surfaces failures on the title bar, same as
every read-path error already did. Everything else is still read-only
display; Selection now supports XI add/remove, captain/keeper, and batting
order reordering, but not per-player aggression yet. Full detail,
including the one real bug found along the way (a blocking Windows dialog
in `launcher.py`'s crash-recovery flow that hung a headless subprocess
forever, fixed with `prepare_environment(..., interactive=False)`), in the
plan doc's "Status" section. The pygame client is **still the shipped
product** — nothing about the current release changes.

## Active initiative

The docs/DESIGN.md redesign delivery list is **complete** (v0.16–0.19). A
user screenshot review (v0.20–0.21) fixed real rendering/legibility bugs
(match header overlap, fullscreen blur, portraits, flags). v0.22.0 added the
**staff department** (Coaching, Medical, Scouting). v0.23.0 added a **staff
transfer market**, staff retirement/regeneration, and **live commentary
modes**. The user then supplied a full Football Manager 26 feature
breakdown (six top-nav tabs, dozens of sub-features) as inspiration for
where to take the UI/UX next; v0.24.0 translated that into
**`docs/UX_ROADMAP.md`** (FM26 → Stumped! cricket equivalent, ranked by what
actually transfers to a cricket sim vs. what's out of scope) and shipped its
top two immediate items: a **navigation restructure** matching the FM26 IA
and a real **Squad Planner**. The user then supplied a second round of
context specifically on match-engine architecture (Cricket Captain/OOTP-
style ball-by-ball loop, attributes, aggression-as-a-format-personality-
trait) and said to keep going without stopping. Cross-checking that against
`match_engine.py` showed almost the entire described architecture already
exists (probability-weighted ball outcomes, pitch/weather, talent procs,
Monte Carlo win probability + score predictor) — the one genuine gap was
**player temperament**, shipped in v0.25.0. v0.26.0 shipped the
**Recruitment Hub**, and v0.27.0 shipped **active scouting assignments**
(send a named scout to a specific player for N days, get a report) — the
three highest-priority roadmap items are now all done. All under the
standing "make changes you would make as if this were your game" authority
— no approval sought per change.

## What works

- Full game runs (`python main.py` from `cricket_manager/`): match engine
  (T10/T20/ODI/Test), competitions, transfers, training, youth (targeted
  recruitment), facilities, finances, honours, career hub, contract
  negotiation, **staff (coaches/medical/scouts, transfer market, retirement)**,
  live commentary modes, saves.
- **181 unit tests pass** (verified 2026-07-21, ~31s, run under Python
  3.14.6 via the project venv); match-engine statistical validation
  (`python validate_match_engine.py`) realistic and unchanged (T20 7.0
  RPO, ODI 5.01, Test 3.95).
- `dist/Stumped.exe` rebuilt at v0.39.0 with passing diagnostics, built
  with the 3.14.6 venv's PyInstaller.
- Godot client runs on **4.7.1 stable**. Verified separately: `godot
  --headless --path godot_client -- --smoke-test` cycles all 16
  registered screens plus the Dashboard advance-day button, the
  Inbox/Transfers/Staff-Market/Selection row-click flows, and the
  Offers/Facilities/Staff/Selection row-button flows, all via real
  emitted Godot signals; multiple consecutive clean runs, zero script
  errors — see the migration section above.

## New in v0.59.0 — Youth Academy interactivity + Recruitment nav shortcuts

- Follow-up audit after Training (v0.58.0) turned out to be a
  "read-only port missed the interactive parts" case: checked the other
  data-heavy screens (Youth Academy, Medical Centre, Recruitment)
  against their pygame counterparts. Medical Centre is genuinely
  read-only in pygame too — no change needed there.
- New bespoke `youth_academy_screen.gd`/`.tscn` ports `ui/youth.py`'s
  split-view UI: squad table + side panel with collective training
  FOCUS cycling (Balanced/Batting/Bowling/Fielding, applied to every
  academy-eligible player), a SCOUT FOR role selector, a paid RECRUIT
  YOUTH trial (fixed fee, generates 3-5 new 16-year-old prospects,
  posts an inbox notification), and a development-pipeline breakdown
  by potential band. Row click opens the same player profile modal as
  Squad.
- New IPC methods `set_academy_focus` and `recruit_youth_prospects` in
  `ipc_server.py`, wrapping `database.py`'s existing
  `set_training_focus`/`recruit_youth`/`add_financial_transaction`/
  `create_inbox_message`.
- Fixed a real bug caught while porting this: `get_youth_academy`'s
  player filter checked the `academy_squad` flag only; pygame's actual
  rule is under-20 *or* flagged. The Godot roster was silently missing
  young prospects that hadn't been explicitly flagged. Corrected
  server-side; the pre-existing test that had baked in the old,
  narrower behavior was updated to assert the correct rule instead of
  being deleted.
- `recruitment_screen.gd`/`.tscn` gained the three header shortcut
  buttons pygame's `RecruitmentHubScreen` has (Browse Transfers, Staff
  Market, Academy). `shell.gd` now adds itself to a `"shell"` group in
  `_ready()` so any screen can call `get_tree().get_first_node_in_group
  ("shell").show_screen(...)` without needing a direct parent
  reference.
- New smoke-test exercises: Youth Academy's FOCUS button real `pressed`
  signal round-trips through the backend; RECRUIT YOUTH's real
  `pressed` signal actually grows the squad (checked via player count);
  Recruitment's ACADEMY button real `pressed` signal actually
  navigates the shell. Godot smoke test clean across 3 runs. 197/197
  Python tests pass (including the updated youth-academy-filter test).

## New in v0.58.0 — Training's real interactivity

- Third and last piece of the original "mousing over players... can't
  click on players, training doesn't show training groups" feedback.
  New bespoke `training_screen.gd`/`.tscn` replaces the read-only
  `table_screen.gd` config the Training screen used to have, porting
  `ui/training.py`'s split-view layout: squad table (left) + a
  programme detail card (right) with PROGRAMME/INTENSITY/DAYS cycle
  buttons, APPLY PROGRAMME TO ALL, and ADVANCE TO NEXT SESSION /
  SIMULATE 30 CALENDAR DAYS.
- New IPC methods in `ipc_server.py`: `cycle_training_focus`,
  `cycle_training_intensity`, `cycle_training_days`,
  `apply_training_to_all`, `simulate_training` — each wraps an
  already-existing `database.py` function the pygame client already
  used, so no simulation logic was duplicated.
- Fixed a real bug caught during verification: a copy-pasted `@onready`
  node path for the row list was missing the `Scroll` container level
  (`$Row/SquadCard/SquadBox/RowList` instead of
  `$Row/SquadCard/SquadBox/Scroll/RowList`), so every refresh silently
  crashed `_build_rows()` — silent because the crash happened after the
  title label was already set, so the screen still looked fine at a
  glance. Caught by the new smoke-test exercise, not by eyeballing.
- New smoke-test exercise emits the PROGRAMME button's real `pressed`
  signal and checks the change round-trips through the backend, then
  runs SIMULATE 30 CALENDAR DAYS and checks real points-gained is
  reported. Godot smoke test clean across 3 runs. 197/197 Python tests
  pass.

## New in v0.57.0 — click-to-open player profile

- Second piece of the "can't click on players" feedback: new
  `player_profile_modal.gd`/`.tscn` ports `ui/player_modals.py`'s
  `PlayerDetailModal`, scoped to a single view rather than pygame's
  full 6-tab modal — flag, name, role/age/nationality, overall +
  potential, weekly wage, contract years remaining, and a full
  Batting/Bowling/Fielding/Mental/Physical attribute bar breakdown
  (reads the same nested attribute dicts `table_screen.gd`'s hover card
  already relies on, no new IPC method needed for the attributes
  themselves).
- Wired into `table_screen.gd`: a player row's left-click opens the
  profile modal only when `row_action` is empty on that tab (Squad,
  Youth Academy) — screens where the click is already claimed for
  something else (Selection's toggle-XI, Inbox's mark-read) are
  unaffected.
- `ipc_server.py`'s `get_squad`/`get_youth_academy` now add a
  `wage_display` field (via `format_money()`), matching the `*_display`
  pattern already used for Transfers/Offers/Staff Market/Finances.
- New smoke-test exercise emits a real row's `gui_input` left-click and
  checks the modal actually opens with the correct player name and
  non-empty attribute rows. Godot smoke test clean across 3 runs.
  Headless `--screenshot-test` capture fails in this environment (the
  dummy renderer used under `--headless` can't produce a viewport
  texture — pre-existing limitation, not new); verified instead by
  exporting and launching the real `.exe`, the higher-signal method
  already established this session. 196/197 Python tests pass (the
  1 failure is the known pre-existing flaky
  `test_academy_recruitment.py` assertion, unrelated).
- **Still open**: Training's real interactivity (see "Next recommended
  action" below).

## New in v0.56.0 — player hover cards

- Direct usability feedback: "mousing over players should give their
  details, can't click on players, training doesn't show training
  groups." First piece landed: `player_hover_card.gd` ports
  `ui/widgets/quick_card.py`'s `QuickCard` — name, role/age/nationality,
  overall, Form/Fitness/Morale bars — shown on row hover, wired into
  `table_screen.gd` so every player-list screen gets it automatically.
- Fixed a real bug caught during verification: overall/form both showed
  a hardcoded "50" fallback due to a broken `is_valid_int()` check on a
  raw JSON float string. Simplified to a direct `int()` cast.
- **Still open from this feedback** (see "Next recommended action"):
  click-row-to-open-full-profile, and Training's actual interactive
  focus/intensity/schedule assignment (pygame's `ui/training.py` has a
  much richer split-view UI than the Godot client currently ports —
  the Godot Training screen is still read-only).
- New smoke-test exercise emits real hover signals and checks the card
  shows/hides the correct player. Godot smoke test clean across 3 runs,
  visually verified. No Python-side changes; 197 tests unaffected.

## New in v0.55.0 — Training migrated to shared table component

- Training was the last screen using a bespoke plain-list layout
  predating the theme pass. `get_training` now flattens each player's
  assignment onto the player dict server-side; the Godot client just
  renders it as a normal table, same as every other list screen.
  `training_screen.gd`/`.tscn` deleted.
- 1 new test (197 total), Godot smoke test clean across 3 runs, visually
  verified via screenshot capture.

## New in v0.54.0 — full-screen visual audit fixes

- Expanded the screenshot-test dev tool to cover all 16 Godot screens
  (was 5), which surfaced two real bugs:
  - Training's "LAST TRAINED" column showed literal `<null>` text —
    `Dictionary.get(key, default)` only falls back when the key is
    absent, not when it's present with a JSON `null` value. Fixed with
    an explicit null check (also applied to focus/intensity).
  - Money fields across Transfers/Offers/Staff Market/Finances were bare
    integers instead of formatted currency. `ipc_server.py` now formats
    them with the pygame client's own `format_money()` helper
    (`src/models/currency.py`), adding a `*_display` field alongside the
    raw number rather than duplicating currency-formatting logic in
    GDScript.
- 2 new tests (196 total), Godot smoke test clean across 3 runs,
  visually verified across every screen via screenshot capture.

## New in v0.53.0 — fixed text ghosting + ground view fielder dots

- v0.52.0's MSDF font change caused a real regression: visible
  double-stroke text ghosting, caught when the user ran the exported
  `.exe` directly. MSDF doesn't play well with this project's
  `gl_compatibility` renderer. Reverted to non-MSDF with
  `oversampling=2.0` for smooth AA without the bug (hinting stays off).
- Also fixed, per direct feedback: Match's ground view fielder dots were
  nearly invisible (a same-radius "border" circle was fully overwriting
  each dot's colour with dark turf-green) and close-in labels
  (WK/slip/gully) overlapped into unreadable text. Rewrote with a proper
  ring+fill, shirt-number markers (1-11, gold keeper), radially-offset
  labels, stumps, and turf texture rings — closer to the Cricket Captain
  reference look.
- This is exactly the value of testing the real exported build instead
  of only screenshots — the ghosting bug was subtle enough to miss at
  screenshot scale. No Python-side changes; 194 tests unaffected, Godot
  smoke test clean across 3 runs.

## New in v0.52.0 — smoother text rendering + FM26-style tabs

- Direct feedback on the exported build: text "seems too sharp" and
  "tabs need work." Fixed both:
  - Inter now imports as an MSDF font with hinting disabled instead of
    Godot's default hinted rasterised glyphs — smoother anti-aliased
    edges at every size.
  - Tabs redesigned from a filled gold-bordered pill to a clean
    underline style (no background box either state), matching the
    reference screenshots' sub-navigation much more closely.
- Also exported and verified a real standalone `.exe` this session
  (`godot_client_dist/StumpedGodot.exe`) — see `godot_client/README.md`'s
  "Exporting a standalone .exe" section for how to reproduce it.
- No Python-side changes; 194 tests unaffected, Godot smoke test clean
  across 3 runs, visually verified via screenshot capture.

## New in v0.51.0 — Selection batting aggression/style

- Selection gained an "AGGRESSION" tab with STYLE/AGGRO buttons per
  player, closing the last gap in Selection's feature parity with
  `ui/selection.py`. `table_screen.gd`'s tabbed sub-navigation now
  supports per-tab `row_buttons`/`row_action` overrides, not just
  different columns, so a tab's actions can differ from the default view.
- New `cycle_batting_style`/`cycle_batting_aggression` IPC methods mirror
  `ui/selection.py`'s two independent click zones: style steps through
  Silly/Blitz/Build/Rotate and snaps aggression to that style's default;
  aggression separately wraps 1-10. `get_selection` now returns
  `batting_style`/`batting_aggression` per player.
- New smoke-test exercise switches tabs and presses the real STYLE/AGGRO
  buttons, asserting both values actually changed.
- 5 new tests (194 total), Godot smoke test clean across 3 runs, visually
  verified via screenshot capture.

## New in v0.50.0 — styled standings + inbox cards

- League standings rows show a numbered position badge (gold-filled for
  the user's own team) instead of a bare "N." prefix; inbox rows show a
  priority-coloured dot (red/gold/muted for HIGH/MEDIUM/LOW), unread in
  full contrast, read dimmed. This closes out the Dashboard-card item
  and the full reference-derived visual backlog from this session.
- Fixed a real bug: the position badge initially rendered "1.0"/"2.0" —
  missed applying `JsonFormat.value()` to a raw numeric IPC value (the
  same Godot JSON int/float quirk that bit this project before).
- No Python-side changes; 189 tests unaffected, Godot smoke test clean
  across 3 runs, visually verified via screenshot capture.

## New in v0.49.0 — styled Dashboard fixture card

- Dashboard's "NEXT FIXTURE" card now shows both teams as crest badges
  (coloured circle + initials, same treatment as the header's club
  crest) either side of a muted "vs", format/date centred underneath —
  replacing a plain text line. Also fixed a leftover pre-v0.41.0
  background colour on Dashboard that never picked up the shared palette.
- No Python-side changes; 189 tests unaffected, Godot smoke test clean
  across 3 runs, visually verified via screenshot capture.

## New in v0.48.0 — Selection column overflow fix

- Selection's row exceeded 1280px and scrolled horizontally, clipping the
  DOWN button. Tightened column widths, shortened CAPTAIN/KEEPER to
  CAPT/WK, and `table_screen.gd`'s `row_buttons` spec now accepts a
  per-button `"width"` override instead of a fixed 90px for every button.
- No Python-side changes; 189 tests unaffected, Godot smoke test clean
  across 3 runs, visually confirmed no horizontal scrollbar.

## New in v0.47.0 — secondary style tag

- `table_screen.gd` columns can render as a muted secondary label
  (`{"muted": true}`) — added a STYLE column (`bowling_style`) to Squad's
  GENERAL INFO tab, right after ROLE, mirroring the reference
  screenshots' muted secondary tag (e.g. "Stroke Maker").
- No Python-side changes; 189 tests still pass, Godot smoke test clean
  across 3 runs, visually verified via screenshot capture.

## New in v0.46.0 — tabbed sub-navigation

- `table_screen.gd` supports extra tabs beyond the default "GENERAL INFO"
  view — same IPC method/data, different columns per tab. Squad gained an
  "ATTRIBUTES" tab (batting/bowling/fielding/mental averages as bars),
  mirroring the reference's "General Info / Stats / Injuries" pattern.
  This was the biggest remaining structural gap on the visual redesign
  track; see `docs/GRAPHICS_MIGRATION_PLAN.md`.
- `get_squad` now returns `batting_avg`/`bowling_avg`/`fielding_avg`/
  `mental_avg` per player via `group_average()` (already used by pygame).
- New smoke-test exercise presses the real tab button and checks the
  header row's columns actually changed, not just "no error".
- 1 new test (189 total), Godot smoke test clean across 3 runs, visually
  verified via screenshot capture.

## New in v0.45.0 — form/morale bar meters

- `table_screen.gd` columns can render a 0-100 stat as a coloured
  horizontal bar (`{"bar": true}`) instead of a bare number, using the
  same FM-style attribute-tier colours as the pygame client's
  `attribute_colour()`. Added FORM and MORALE bars to Squad.
- Known minor gap: Squad now scrolls horizontally at 1280px width (same
  pre-existing behaviour Selection already had) — not addressed this pass.
- No Python-side changes; 188 tests still pass, Godot smoke test clean
  across 3 runs, visually verified via screenshot capture.

## New in v0.44.0 — sidebar nav icons

- New `nav_icon.gd` draws a small geometric glyph per nav section in code
  (no icon asset pipeline exists), recoloured gold when active — matches
  the reference sidebar's icon-per-item layout.
- Fixed a real layout bug this surfaced: nav buttons collapsed to
  near-zero height once their built-in `text` was replaced by a custom
  icon+label row, since an empty-text `Button` has almost no implicit
  minimum size. Fixed with an explicit `custom_minimum_size`.
- No Python-side changes; 188 tests still pass, Godot smoke test clean
  across 3 runs, visually verified via screenshot capture.

## New in v0.43.0 — nation flag icons

- `table_screen.gd` columns can render a flag icon (`{"flag": true}`) from
  a player's `nationality` field. Added to Squad, Selection, Transfers,
  and Youth Academy, ahead of the player name — matches the reference
  screenshots. `app_theme.gd`'s `flag_texture()` mirrors
  `ui/widgets/country_flag.py`'s alias/ISO mapping exactly and reuses the
  same bundled Flagpedia PNGs (now copied into
  `godot_client/assets/images/flags/`).
- Known minor gap: nationalities with no ISO flag (e.g. "West Indies")
  render nothing rather than pygame's drawn placeholder — acceptable for
  now rather than porting that drawing logic.
- No Python-side changes this pass; 188 tests still pass, Godot smoke
  test clean across 3 runs, visually verified via screenshot capture.

## New in v0.42.0 — persistent club header + coloured role pills

- New persistent header bar (crest initials, team name, date/next-fixture
  subtitle, ADVANCE DAY button) above the sidebar and content on every
  screen, fed by `get_dashboard` (now also returns `date`). Replaces
  Dashboard's own corner button — the club identity bar and the advance
  action are chrome now, not part of one screen, matching the FM26/Cricket
  Management reference layouts the user pointed to.
- `table_screen.gd` columns can render as coloured pill badges
  (`{"pill": true}`) — applied to ROLE on Squad, Selection, Transfers, and
  Youth Academy.
- `advance_day` is reachable from any screen now; the smoke test's
  advance-day exercise asserts the header's date text actually changed.
- User feedback this pass: the client "still looks terrible" even after
  v0.41.0's theme pass — this is being treated as a standing, multi-pass
  redesign effort against the FM26/Cricket Management reference
  screenshots the user supplied, not a single fix. See "Next recommended
  action" below for what's still outstanding.

## New in v0.41.0 — real Godot theme + Match Day screen

- The Godot client had no custom `Theme` at all — every screen rendered in
  the engine's unstyled default gray. New `AppTheme`
  (`godot_client/scripts/app_theme.gd`) ports the pygame client's actual
  "Test at Dusk" design tokens and Inter font into a Godot `Theme` applied
  at the shell root, cascading to every screen: styled buttons, a
  highlighted active nav item, zebra-striped `PanelContainer` table rows
  with a distinct header bar (was bare `Label`s in an `HBox`).
- Deleted `squad_screen.gd`/`.tscn` (duplicated `table_screen.gd`) and
  rebuilt Squad on the shared table component.
- New **Match Day** screen replaces the "Coming Soon" placeholder:
  next-fixture header, selected XI in batting order, and a drawn cricket
  ground (`ground_view.gd`) with default fielding positions — referencing
  the Cricket Captain wagon-wheel view. New `get_match_preview` IPC
  method. This is a pre-match hub, not a live simulation — no
  ball-by-ball feed exists yet.
- Fixed a real bug surfaced along the way: `get_dashboard`'s standings
  never had a `position` field (only the pygame client enriched it
  locally), so Godot's standings list showed "0." for every row. Fixed at
  the source in `ipc_server.py`.
- Verified visually, not just via title text: a temporary
  screenshot-capture smoke-test mode (`--screenshot-test`, not committed
  output) rendered Dashboard/Selection/Match/Squad/Facilities to PNG for
  actual pixel review before shipping.

## New in v0.40.0 — Selection batting order (UP/DOWN reorder)

- New `move_batting_up`/`move_batting_down` IPC methods, mirroring
  `ui/selection.py`'s arrow-click swap of adjacent `self.xi` entries — a
  no-op at either end of the order, rejected if the player isn't in the XI.
- `_selection_view()` now returns players XI-first *in batting order*, rest
  of the squad after, so the table's row order is the batting order with no
  client-side sorting; `xi_status` shows the batting position number (e.g.
  `"4/C"`) instead of a bare `"XI"` tag.
- Selection screen gained UP/DOWN row buttons alongside CAPTAIN/KEEPER.
- Verified against real data: adjacent swap, no-op at the boundary,
  rejection for a non-XI player, plus a dedicated Godot smoke-test exercise
  that checks the row order actually changed after pressing DOWN.

## New in v0.39.0 — Selection captain/keeper designation

- New `set_captain`/`set_keeper` IPC methods, mirroring `ui/selection.py`'s
  captain/keeper cycle buttons — must be an XI member, same rule, writing
  the same `selection.captain`/`selection.keeper` save-state keys.
- Selection screen now has CAPTAIN/KEEPER buttons per row, alongside the
  existing whole-row click for XI toggling — the first screen combining
  `table_screen.gd`'s `row_action` and `row_buttons` on the same table.
- Verified against real data, including the rejection path: assigning
  captain to a non-XI player correctly raises the same validation error
  the pygame client enforces.

## New in v0.38.0 — toolchain upgrade for Steam (Python 3.14.6, Godot 4.7.1)

- Prompted by the user asking to confirm the project is on current
  versions of both, since this is heading to a real Steam release — see
  `docs/GRAPHICS_MIGRATION_PLAN.md`'s "Toolchain" section for full detail,
  including exactly what was verified before switching (not assumed).
- **Python 3.12.10 → 3.14.6** via a new project-local venv at
  `cricket_manager/.venv`. `ipc_bridge.gd` now resolves this venv's
  `python.exe` directly instead of the fragile `where python` PATH lookup.
- **Godot 4.3.0 → 4.7.1 stable** — zero code changes required to load and
  run the existing project.
- **Two real, pre-existing bugs found by the version bump** (latent since
  Phase 0, not caused by the upgrade): every numeric table cell across
  every screen was silently rendering `"25.0"` instead of `"25"`
  (Godot's JSON parser has no int/float distinction), and — worse — the
  Training screen's assignment lookup could never match on that same
  float-vs-string mismatch, so it had been silently showing every
  player's focus as "None" regardless of what was actually assigned.
  Both fixed centrally via new `scripts/json_format.gd`.

## New in v0.37.0 — Selection screen (add/remove XI)

- New IPC methods `get_selection`/`toggle_xi`: click a squad row to
  add/remove them from the starting XI (max 11 enforced server-side).
- These write to the exact same `selection.xi` save-state key
  `ui/selection.py` already reads/writes — pick an XI in either client and
  the other sees it.
- New **Selection** screen (SQUAD nav group), built on the existing
  `table_screen.gd` — no new bespoke scene needed.
- Verified against real state: toggling a player persists to
  `selection.xi` across a fresh backend process, not just in memory.

## New in v0.36.0 — Staff release

- New `release_staff` IPC method wraps the existing `sell_staff_member`
  (already used identically by the pygame client — deliberately leaves the
  role vacant rather than auto-replacing, same rule both clients share).
- Staff screen now has a RELEASE button per row.
- Verified against real state: releasing a staff member genuinely removes
  them from the roster and credits the fee.

## New in v0.35.0 — Facilities upgrades, row-action error surfacing fix

- `get_facilities` now synthesizes a 7-row overview (current level +
  Ready/Building status per facility) alongside the upgrade-history list;
  new `upgrade_facility` IPC method wraps `start_facility_upgrade`.
- Facilities screen now shows this actionable overview with an UPGRADE
  button per row instead of a read-only history list.
- **Bug fixed**: `table_screen.gd`'s row actions silently swallowed IPC
  errors — caught via the smoke test's own repeated-run verification
  (clicking UPGRADE twice on the same dev save naturally hits "already
  building" the second time, which used to look like success).
  `_dispatch()` now surfaces failures on the title bar.

## New in v0.34.0 — Staff Market signing

- New IPC methods `get_staff_market` (wraps `browse_staff_market`) and
  `sign_staff` (bid-then-immediately-accept, mirroring `ui/staff.py`'s
  `_act_on_selected()`).
- New **Staff Market** screen (CLUB nav group, next to Staff): click a
  listed staff member to sign them at their listed fee/wage.
- Verified against real state: a signed staff member genuinely appears in
  the buying club's roster afterward, not just "the IPC call succeeded".

## New in v0.33.0 — Offers screen (Accept/Reject)

- `table_screen.gd` gained a generic optional `row_buttons`: explicit
  action buttons appended to each data row, for screens needing more than
  one action per row — `row_action` (previous release) only supports one
  whole-row click.
- New **Offers** screen (RECRUITMENT nav group): every pending transfer
  offer with **ACCEPT**/**REJECT** buttons calling `resolve_transfer_offer`
  — reuses `get_transfer_market`'s existing `offers` list, no new IPC
  method needed.
- Verified against real behaviour, not a stub: clicking Accept ran the
  actual affordability check `resolve_transfer_offer` always runs, and one
  verification run correctly flipped an offer to `FAILED` rather than
  faking an accept the buying club couldn't afford.

## New in v0.32.0 — two more interactive Godot flows

- `table_screen.gd` gained a generic optional `row_action`: click a data
  row to fire another IPC call built from that row's own fields
  (`params_from_row`) plus optional constants (`params_fixed`), then
  refresh — and an optional `dim_when_key` to visually fade rows matching
  a boolean field.
- **Inbox** rows mark themselves read on click and dim once read.
- **Transfers** rows submit an offer at the listed asking price on click.
- Verified against real save-data changes (a message's `read` flag
  actually flips; a real `PENDING` offer row is actually created in the
  database), not just "the IPC call didn't error".

## New in v0.31.0 — Recruitment ported, first interactive flow

- Extracted `ui/recruitment.py`'s squad-gap/contract-watch/objectives logic
  into pygame-free `src/models/recruitment.py` + `src/models/squad_metrics.py`
  (the latter also absorbed `group_average`/`estimated_value`, previously
  defined in `ui/shared_components.py`, which now just re-exports them —
  every existing `from .shared_components import group_average`-style
  caller across `ui/*.py` keeps working unchanged, regression-tested).
- New Godot **Recruitment** screen (bespoke, tiled like Dashboard) fed by a
  new `get_recruitment` IPC method that calls those same shared functions —
  both clients apply identical rules now, not parallel logic.
- Dashboard's **"ADVANCE DAY" button** — the first interactive/write flow
  in the Godot client, calling `advance_day` and refreshing.
- 12 of 13 registered screens are now real; only Match remains.

## New in v0.27.0 — active scouting assignments

- **`database.py`**: new `scouting_assignments` table + `create_scouting_
  assignment`/`fetch_scouting_assignments`/`advance_scouting_assignments`.
  Send one of your own, currently-free scouts to file a report on a named
  player over a chosen number of days; a longer assignment sharpens the
  read (effective judging ability rises with total days invested, capped at
  +4 above the scout's base rating). Wired into
  `CompetitionEngine.advance_day()`, which now files an inbox message the
  day a report completes.
- `ui/transfers.py`: "SEND SCOUT (10 DAYS)" button next to the selected
  scouted player — auto-picks your best available (not already busy) scout.
- `ui/recruitment.py`: new "Scouting Assignments" tile on the Recruitment
  Hub (bottom row, now 3 tiles instead of 2) shows active countdowns and
  completed estimates.

## New in v0.26.0 — Recruitment Hub

- **`ui/recruitment.py`** (new "Recruitment" screen, top of the
  RECRUITMENT nav group above Transfers): four tiles built entirely from
  data that already existed but had no single home —
  **Recruitment Objectives** (weakest attribute group across the squad +
  division context), **Squad Gaps** (role headcount vs. a fixed target —
  `ROLE_TARGETS`, e.g. flags too few frontline bowlers), **Contract Watch**
  (players with `contract_years_remaining <= 1`, reusing the same status
  logic as the Squad Planner), and **Requirements** (auto-derived scouting
  asks straight from the squad-gap list). Three quick-action buttons jump to
  Transfers, Staff Market, and the Academy.
- Closes item 1 of `docs/UX_ROADMAP.md`'s next-four list.

## New in v0.25.0 — player temperament

- **`src/models/player.py`**: `natural_batting_aggression()` and
  `natural_bowling_aggression()` derive a 1-10 inherent aggression from a
  player's real attributes (batting attack vs. concentration; bowling
  pace/variation vs. accuracy) — this is the "accumulator vs. boundary
  hitter" personality trait other cricket sims model explicitly, now
  grounded in Stumped!'s existing attribute data rather than a new stat.
- `ui/selection.py`: Auto-Select assigns batting styles from real
  temperament (previously only checked `attack >= 75`, ignoring
  accumulators entirely); manually adding a player to the XI now seeds a
  sensible aggression default instead of a flat neutral 5; the on-screen
  `A#`/`B#` indicators fall back to the natural value, not a hardcoded 5.
- Cross-referenced the user's supplied Cricket Captain/OOTP-style engine
  breakdown (ball-by-ball loop, weighted-probability outcomes, pitch/
  weather, win-probability predictor) against `match_engine.py` — nearly
  all of it already exists (talent procs, Monte Carlo win probability +
  score predictor, pitch wear, weather forecast evolution); temperament was
  the one real gap, now closed.

## New in v0.24.0 — UX roadmap, nav restructure, Squad Planner

- **`docs/UX_ROADMAP.md`**: full FM26-tab → Stumped!-cricket translation
  table (Portal/Squad/Recruitment/Match Day/Club/Career), each row marked
  Have/Partial/Planned, with a ranked next-four backlog. International
  management, 3D match visualisation, and manager-persona creation are
  explicitly called out as out of scope — they don't transfer to a
  text/2D cricket sim without a much larger redesign.
- **Navigation restructure** (`main.py` `NAV_GROUPS`): sidebar sections
  renamed/regrouped to PORTAL / SQUAD / MATCH DAY / RECRUITMENT / CLUB /
  CAREER / SYSTEM, mirroring the FM26 IA using entirely existing screens —
  no screen was added or removed, only regrouped (Staff moved from Squad to
  Club since it's roster+contract management, matching FM's Club>Staff).
- **Squad Planner** (`ui/squad.py`, new "Planner" tab on the existing Squad
  screen tab bar): projects each player's contract status across three
  seasons (`SquadScreen._season_label`) — Contracted / Expires this year /
  Free agent — computed straight from `contract_years_remaining`, no new
  schema needed. Colour-coded (green/gold/dim) via the existing
  `colour_func` hook on `DataTable`.

## New in v0.23.0 — staff market, retirement, commentary modes

- **Staff market** (`ui/staff.py` Market tab; `database.browse_staff_market`,
  `make_staff_offer`, `resolve_staff_offer`, `sell_staff_member`,
  `staff_transfer_value`): browse every other club's staff, sign for an
  immediate fee (cash moves both ways, blocked if the buyer can't afford
  it), or release your own staff back to the market. New
  `staff_transfer_offers` table records every deal.
- **Staff retirement/regeneration** (`database.age_staff_at_rollover`,
  `STAFF_RETIREMENT_AGE = 66`): rising retirement chance from 66+, each
  retiree immediately replaced so departments never go empty.
  `competition.rollover_season()`'s return dict now includes
  `staff_retired`.
- **Commentary modes** (`ui/match_view.py`): a COMM button toggles Full vs
  Key Moments (wickets/boundaries/milestones only) — useful once match
  speed is turned up. Fixing this also required widening the header's
  reserved control area (`speed_w` 246→360) to fit the new button without
  overflowing past the content edge — covered by a dedicated layout test.
- Scouting UI note: the user's request to put staff "in the transfer list"
  was interpreted as its own Market tab on the Staff screen rather than
  merging into `ui/transfers.py`'s player table — cleaner UX, kept clubs'
  player and staff dealings visually distinct. Worth revisiting if the user
  wants them unified.

## New in v0.22.0 — Staff department

- **`src/models/staff.py`** + new `staff` DB table: every club has a real
  named roster — Head/Batting/Bowling/Fielding/Fitness Coaches, Doctor,
  Physio, Chief Scout, Scout — each with role attributes on a 1-20 scale.
  Existing saves auto-backfill via `_ensure_staff_for_all_teams`.
- **Coaches → training**: `database.team_coach_rating()` feeds
  `coach_training_multiplier()` into `apply_daily_training`'s per-discipline
  gain calculation (~0.72x-1.32x depending on coach quality).
- **Medical → injuries**: `database.team_physio_rating()` feeds
  `medical_injury_multiplier()` into `match_engine._maybe_injury` (both
  injury *chance* and *recovery duration*), stacking with the existing
  Medical Centre facility level. New **Medical Centre** screen
  (`ui/medical.py`) — the game previously tracked injuries in the DB with
  no screen to see them; this was a real gap, now closed.
- **Scouts → scouting accuracy**: `database.team_scout_rating()` feeds
  `scouting_noise()`/`apply_scouting_estimate()`; `scout_players()` now
  returns `estimated_overall`/`estimated_potential`/`confidence` alongside
  the true values. The Transfer Market table (`ui/transfers.py`) displays
  the *estimate*, not the omniscient true stat — a poor scouting network
  is visibly less reliable.
- **Staff ageing**: `age_staff_at_rollover()` runs every season rollover
  (young staff occasionally improve, veterans occasionally decline).
- New **Staff** screen (`ui/staff.py`): Coaching/Medical/Scouting tabs, a
  roster table, and a detail panel with attribute bars and contract terms.
- ASTRAIVA (Pty) Ltd publisher mark added to the splash screen (original
  vector recreation — the attached logo file itself could not be extracted
  from the chat into a repo asset, since there is no mechanism to save an
  inbound pasted image; if the user has the source file, drop it at
  `assets/images/astraiva_logo.png` and it can replace the procedural mark).

## Also fixed this session (v0.20.0–0.21.0) — see CHANGELOG.md for detail

- Squad quick-card crash, match header/action-row overlap, fullscreen blur
  on common monitors, text sharpness, real flag artwork, sharper portraits,
  "UI Foundation" placeholder removed, contract negotiation, targeted
  academy recruitment.

## In progress / remaining (priority order)

See `docs/UX_ROADMAP.md` for the full FM26-derived backlog and status table.
Squad Planner (v0.24.0), Recruitment Hub (v0.26.0), and active scouting
assignments (v0.27.0) are all done. Top of what's left, folded in here:

1. **Opposition report** — pre-match scouting summary of the next opponent
   (formation/key players/strengths-weaknesses/recent form), reusing
   existing player attribute data; feeds Match Day. Next up.
2. **AI-initiated staff/player offers** — the user can buy/sell staff and
   players, but no AI club currently *initiates* a bid outside the handful
   of seeded incoming offers. Needs a periodic AI-evaluation pass (e.g.
   during `advance_day`).
3. Interactive job market — job offers/sackings driven by reputation and
   board confidence (`src/models/career.py` has the models; needs an offer
   flow, inbox actions, and club-switch plumbing).
4. The Hundred format — needs five-ball-over support in `match_engine.py`.
5. Roadmap `planned` items: live auctions, academy expansion, financial
   forecasting, keeper batting roles, daily tournaments.
6. Career startup flow — `in_progress` in `src/data/roadmap.json`; verify gaps.
7. Real Steam integration (stubbed; app ID `null` in `config.json`).
8. Optional polish backlog: player quick-card on Selection/Transfers tables,
   crossfade screen transitions, skeleton loading rows for DB-heavy tabs.

International management, 3D match visualisation, and manager-persona
creation from the FM26 breakdown are deliberately **not** on this list —
see `docs/UX_ROADMAP.md`'s closing note for why.

## Known bugs / risks

- None known; no TODO/FIXME markers in source. `logs/error.log` is gitignored
  — check locally for runtime issues.
- Staff system (incl. market and retirement) is new and untested against a
  live multi-season save. Retirement always regenerates a same-role
  replacement so departments can't go empty *from ageing*, but selling a
  staff member on the Market deliberately leaves that role vacant until the
  user hires a replacement — watch for a club drifting for many seasons
  with an unfilled role if the user never revisits the Market.
- Audio ducking still not verified on a real device (dummy driver in dev).

## Decisions made

- Proprietary license; no licensed real-world content (all generated).
- SQLite single-file saves with in-place migrations; GBP-base accounting.
- pygame-ce + pygame-gui only; PyInstaller for distribution.
- `dist/`, `build/`, save DBs, and logs are gitignored (recreatable/local).
- Game owned by ASTRAIVA (Pty) Ltd — see branding note above.
- Text rendering: native-size SDL_ttf, not supersampled.
- Fullscreen: exact-integer SDL_SCALED only; never a fractional stretch.
- Scouting fog-of-war is scoped to the Transfer Market display only (not a
  global hidden-attributes system) — a deliberate, safely-bounded choice to
  avoid touching every screen that shows a player's own squad stats.

## Validation actually run (2026-07-21)

- `python -m unittest discover -s tests` → **Ran 146 tests, OK** (~21s).
- `python validate_match_engine.py` → realistic scoring/wicket rates,
  unchanged (T20 7.0, ODI 5.01, Test 3.95).
- Manually verified: a full scouting-assignment lifecycle end-to-end
  (create → tick days via `advance_scouting_assignments` → report + inbox
  message via `CompetitionEngine.advance_day()`); a scout cannot hold two
  assignments; the Transfers screen's "SEND SCOUT" button picks the best
  free scout; the Recruitment Hub's new tile renders active countdowns and
  completed estimates.
- `python build_and_package.py` → packaged build + diagnostics pass.
- Test note: never call `pygame.quit()` in tearDownClass — invalidates the
  lru-cached fonts for later test classes in the same run.

## Next recommended action

The visual redesign backlog (v0.41.0–v0.55.0: theme, Match Day, header,
role pills, flags, icons, bars, tabs, style tags, column fixes, Dashboard
cards, batting aggression/style, ground view + text-rendering fixes,
Training migration) is done — see `docs/GRAPHICS_MIGRATION_PLAN.md` for
the full history. The user has since moved on to **usability depth**,
pointing out specific gaps found by actually using the exported build:
"mousing over players should give their details, can't click on players,
training doesn't show training groups." This is the live priority now:

- **Done (v0.56.0)**: player hover cards (`player_hover_card.gd`, ports
  `ui/widgets/quick_card.py`'s `QuickCard`) on every player-list screen.
- **Done (v0.57.0)**: click-row-to-open-profile. New
  `player_profile_modal.gd`/`.tscn` ports `ui/player_modals.py`'s
  `PlayerDetailModal`, scoped down to a single solid view (flag, name,
  role/age/nationality, overall + potential, weekly wage, contract years
  remaining, full Batting/Bowling/Fielding/Mental/Physical attribute
  bars) rather than the pygame version's full 6-tab modal (Records/Bat
  Form/Bowl Form/Personal/Match Stats/Comparison + comparison + contract
  negotiation) — that stays a later, separate piece of work if wanted.
  Wired into `table_screen.gd`: clicking a player row opens the profile
  only where nothing else already claims the click (Squad) — Selection's
  row click still toggles XI, Inbox's still marks read. Youth Academy
  moved off `table_screen.gd` in v0.59.0 (see below) and wires the same
  profile modal directly.
- **Done (v0.58.0)**: Training's real interactivity. All three items
  from the original feedback are now shipped. New bespoke
  `training_screen.gd`/`.tscn` (not a `table_screen.gd` fit — needs a
  table + detail-panel split layout) ports `ui/training.py`: squad table
  + detail card with PROGRAMME/INTENSITY/DAYS cycle buttons, APPLY
  PROGRAMME TO ALL bulk action, and ADVANCE TO NEXT SESSION / SIMULATE
  30 CALENDAR DAYS actions that call `apply_daily_training()` and show
  real Batting/Bowling/Fielding/Mental growth bars. Five new IPC methods
  (`cycle_training_focus`, `cycle_training_intensity`,
  `cycle_training_days`, `apply_training_to_all`, `simulate_training`)
  wrap `database.py`'s existing `set_training_focus`/
  `set_training_schedule`/`apply_daily_training`.
- **Done (v0.59.0)**: audited the remaining data-heavy screens (Youth
  Academy, Medical Centre, Recruitment) against their pygame
  counterparts, as suggested above. Medical Centre is genuinely
  read-only in pygame too (`process_event` is a no-op) — no gap, no
  change needed. Youth Academy and Recruitment both had real gaps, now
  fixed:
  - New bespoke `youth_academy_screen.gd`/`.tscn` ports `ui/youth.py`:
    squad table + side panel with collective FOCUS cycling (applied to
    every academy-eligible player), a SCOUT FOR role selector, a paid
    RECRUIT YOUTH trial (spends a fee, generates prospects, posts an
    inbox message), and a development-pipeline breakdown. Two new IPC
    methods: `set_academy_focus`, `recruit_youth_prospects`.
  - Fixed a real bug found while porting this: `get_youth_academy`'s
    player filter only checked the `academy_squad` flag; pygame's
    actual rule is under-20 *or* flagged. Corrected server-side, and
    the test that had baked in the old, narrower behavior was updated
    to assert the correct rule.
  - `recruitment_screen.gd`/`.tscn` gained the three header shortcut
    buttons (Browse Transfers, Staff Market, Academy) pygame's
    `RecruitmentHubScreen` has — `shell.gd` now self-registers in a
    `"shell"` group so any screen can call `show_screen()` without a
    tightly-coupled parent reference.

Sixteen interactive flows now exist (Dashboard advance-day, Inbox
mark-read, Transfers submit-offer, Offers accept/reject, Staff Market
signing, Facilities upgrades, Staff release, Selection add/remove-XI +
captain/keeper + batting order + aggression/style, Training programme/
intensity/days cycling + bulk-apply + simulate, Youth Academy focus
cycling + recruit trial). The ball-by-ball live feed for Match remains
the single biggest deferred item — the current Match screen is
deliberately just the pre-match view, not a simulation. With the
usability-depth feedback thread now fully closed (hover cards,
click-to-profile, Training interactivity, and this audit), the next
open question is what the user wants to prioritise next — likely either
the Match live feed, or a fresh pass through the exported build for any
new rough edges.

Either way: add tests, bump the version if pygame-client-facing code
changed, rebuild the exe, update this file, commit and push.
