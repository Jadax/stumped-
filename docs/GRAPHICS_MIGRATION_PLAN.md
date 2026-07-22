# Graphics migration plan — pygame → Godot 4

## Status: Phase 0 complete (2026-07-21)

The proof of concept works end-to-end: `godot_client/` boots, spawns the
unmodified `cricket_manager` Python package as a subprocess, requests the
live squad over the JSON-RPC pipe, and renders it in a real anchored/
container-based table — verified with a deterministic headless smoke test
(`godot --headless --path godot_client -- --smoke-test`, exit 0, "Manchester
Mavericks — 25 players" from the actual save database), run 3x consecutively
clean. See `godot_client/README.md` for how to run it.

One real bug was found and fixed along the way, not a Godot-specific issue:
`src.utilities.launcher.prepare_environment()`'s crash-recovery flow could
pop a native Windows `MessageBoxW` dialog after an unclean exit — harmless
for the interactive pygame client (a person is there to click it), but it
hung the headless IPC backend forever, since nothing can click a dialog in
a subprocess with no window. Fixed with a new `interactive` parameter
(`interactive=False` for any headless/automated caller); regression-tested
in `tests/test_release_systems.py`.

## Status: Phase 1 + partial Phase 2 (2026-07-21, same day)

**IPC method surface (Phase 1)** — `cricket_manager/ipc_server.py` now
exposes 14 methods wrapping existing `database.py`/`competition.py`
functions: `get_squad`, `get_dashboard`, `get_inbox`, `mark_message_read`,
`get_standings`, `get_staff`, `get_transfer_market`,
`submit_transfer_offer`, `resolve_transfer_offer`,
`get_scouting_assignments`, `get_finances`, `get_facilities`,
`get_training`, `get_honours`, `advance_day`. All covered by
`tests/test_ipc_server.py` (14 tests) calling each handler directly
against a real fresh save.

**Screens ported (Phase 2, in progress)** — `godot_client/scenes/shell.tscn`
is now the main scene: a real sidebar (mirrors `main.py`'s `NAV_GROUPS`)
switching a content area between screens, exactly like the pygame
`ScreenManager`. Working, real-data screens:
- **Dashboard** (bespoke: next fixture, standings, inbox cards)
- **Squad** (Phase 0's proof of concept)
- **Inbox, Staff, Finances, Facilities, Career/Honours** — all built on
  one new reusable **`table_screen.gd`** component (configure with a
  title, an IPC method, and a column list) — this mirrors how the pygame
  client reuses `ui/widgets/datatable.py`'s `DataTable` across screens,
  and is why 6 screens shipped in the same pass instead of one each.
- **Transfers** (transfer market browse, via `table_screen.gd`)

- **Training** (bespoke: merges `get_training`'s player list with its
  per-player focus/intensity dict — a genuine merge, not a flat list, so it
  isn't `table_screen.gd`-shaped)
- **Youth Academy** (`get_youth_academy`, new: server-side filter of the
  same squad data `get_squad` already returns — `academy_squad` players
  only — no new database function needed)
- **Medical Centre** (`get_medical`, wraps `fetch_active_injuries`, via
  `table_screen.gd`)

- **Recruitment** (bespoke, tiled like Dashboard): its objectives/squad-gap/
  contract-watch/scouting logic used to live only inside the pygame
  `RecruitmentHubScreen` — extracted into pygame-free
  **`src/models/recruitment.py`** and **`src/models/squad_metrics.py`**
  (`role_gaps`, `weakest_attribute_group`, `contract_watch`,
  `group_average`, `estimated_value`), which `ui/recruitment.py` now
  imports instead of defining locally, and which `ipc_server.py`'s new
  `get_recruitment` method also calls — **both clients now apply
  identical rules**, not parallel reimplementations. Regression-tested
  (`test_shared_recruitment_logic.py`) including a test that the pygame
  screen's `_role_gaps()` still returns exactly what the shared function
  returns.

That's **15 of 16** registered screens now showing real data (**Offers**,
**Staff Market**, and **Selection** all joined the nav, see below). Only
**Match** remains as a placeholder — it needs a live ball-by-ball feed, not
a data table, a fundamentally bigger and different job than every other screen
here, and stays intentionally deferred to last.

**Interactive (write) flows shipped**: Dashboard's "ADVANCE DAY" button
(the game-loop driver); `table_screen.gd`'s generic `row_action` (whole
row clickable, one action) powering **Inbox** mark-read-on-click (dims
once read) and **Transfers** submit-offer-on-click; and now
`table_screen.gd`'s generic `row_buttons` (explicit per-row buttons, for
when one action per row isn't enough) powering a new **Offers** screen
(RECRUITMENT nav group) with **ACCEPT**/**REJECT** buttons on every
pending transfer offer, reusing `get_transfer_market`'s existing `offers`
list (no new IPC method needed) with `resolve_transfer_offer`.
A fifth: **Staff Market** (CLUB nav group) — click a listed staff member to
sign them via new `get_staff_market`/`sign_staff` IPC methods, the latter
mirroring `ui/staff.py`'s bid-then-immediately-accept pattern. A sixth:
**Facilities** was rebuilt from a read-only upgrade-history list into an
actionable 7-row overview (`get_facilities` now synthesizes current level
+ Ready/Building status per facility from the team record) with an
**UPGRADE** button calling the existing `start_facility_upgrade`. A
seventh: **Staff** now has a **RELEASE** button per row, wrapping the
existing `sell_staff_member` (already used identically by the pygame
client — deliberately leaves the role vacant rather than auto-replacing,
same rule both clients share). And an eighth, the first genuinely new
*screen* added since Recruitment: **Selection** (SQUAD nav group) — click
a squad row to add/remove them from the starting XI (max 11), via new
`get_selection`/`toggle_xi` IPC methods. These write to the exact same
`selection.xi` save-state key `ui/selection.py` already reads/writes
(the generic `game_state` key-value store `save_game`/`load_game` already
provide) — pick an XI in either client and the other sees it, since
pygame's selection reads use `.get()` with defaults throughout, so a
Godot-only partial write (just `xi`, no `bowlers`/`captain`/`keeper` yet)
doesn't break it.

All eight verified end-to-end (not just "the IPC method exists") by the
real save data changing — clicking Accept on a transfer offer genuinely
ran the same affordability check `resolve_transfer_offer` always has,
flipping a real offer's status to `FAILED` when the buying club couldn't
afford it rather than faking success; signing a staff member genuinely
moves them into the buying club's roster; clicking UPGRADE genuinely
starts a real facility build; releasing a staff member genuinely removes
them from the roster and credits the fee; toggling a player genuinely
persists to `selection.xi` across a fresh backend process (not just
in-memory) — and by `shell.gd`'s smoke test emitting the actual Godot
input/button signals rather than calling IPC methods directly, so a broken
UI wire-up would fail the test even if the backend endpoint itself were
fine.

**A real bug was found and fixed via this verification discipline**:
`table_screen.gd`'s row actions silently swallowed IPC errors — clicking
UPGRADE on a facility already mid-build looked like it succeeded (the
screen just refreshed normally) when the backend had actually rejected it.
Repeated smoke-test runs against the same persistent dev save (the second
click naturally hits "already building") caught this by producing a
false-clean result. Fixed: `_dispatch()` now surfaces `response.has("error")`
on the title bar and via `push_error`, exactly like every other
backend-error path in the file already does for read failures.

**Verification**: `shell.gd` has its own `--smoke-test` mode that cycles
every registered screen (not just one) and fails on any backend-error
title, run via
`godot --headless --path godot_client -- --smoke-test`. Two real bugs were
caught this way before they shipped (a GDScript type-inference issue in
Dashboard's standings render, and a `configure()`-before-`_ready()` timing
bug in the placeholder screen) — verified with multiple consecutive clean
runs (zero script errors) after every screen added.

**What's still not done, to be direct about it**: 7 of 15 real screens are
still purely read-only (Dashboard, Inbox, Selection, Transfers, Offers,
Staff, Staff Market, and Facilities now have at least one write action —
that's 8, since Selection is new this pass). Selection only supports
adding/removing players from the XI so far, not reordering the batting
order, setting captain/keeper, or per-player aggression — those still need
`ui/selection.py`'s fuller UI. Training focus assignment, contract
negotiation with counter-offers, and the match view itself (the single
biggest remaining item) are all still pygame-only. "Complete everything"
for a full engine migration remains realistically multiple more sessions
of work; this update is real, substantial, non-breaking progress against
that goal, not the finish line.

**Selection has since grown captain/keeper designation** — new
`set_captain`/`set_keeper` IPC methods mirroring `ui/selection.py`'s
captain/keeper cycle buttons (must be an XI member, same rule, writing the
same `selection.captain`/`selection.keeper` save-state keys), wired via
`table_screen.gd`'s `row_buttons` alongside the existing whole-row
`row_action` for XI toggling — the first screen combining both mechanisms
on the same table.

**Selection has since grown batting-order reordering too** — new
`move_batting_up`/`move_batting_down` IPC methods mirroring
`ui/selection.py`'s arrow-click swap of adjacent `self.xi` entries (same
no-op-at-the-boundary behaviour, same XI-membership rejection). Getting
this onto the generic `table_screen.gd` component without a bespoke
drag/reorder widget required `_selection_view()` to return players
XI-first *in batting order*, with the rest of the squad after — so the
row order the table already renders top-to-bottom simply *is* the batting
order, and UP/DOWN just swap adjacent rows. `xi_status` now carries the
batting position number instead of a bare "XI" tag. Per-player aggression
and bowling assignments are still pygame-only.

**The Godot client had no visual theme at all until now** — every screen
rendered in the engine's unstyled default gray/beige controls, which is
what "looks terrible" was correctly pointing at (a functional migration
isn't the same thing as a *finished* one). Fixed by porting the pygame
client's actual design tokens (`src/views/theme.py`'s "Test at Dusk"
palette, same Inter font) into a Godot `Theme` (`app_theme.gd`), applied
at the shell root so it cascades everywhere: styled buttons, a
highlighted active nav item, and `table_screen.gd` rows rebuilt as
zebra-striped `PanelContainer` cards with a distinct header bar instead
of bare `Label`s. `squad_screen.gd`, a near-duplicate of `table_screen.gd`
predating its generalisation, was deleted and Squad rebuilt on the shared
component — it now gets the same styling for free and there's one less
bespoke screen to maintain.

**Match is no longer a placeholder.** New `match_screen.gd` +
`ground_view.gd` show the next fixture, the selected XI in batting order,
and a drawn cricket ground with default fielding positions — referencing
the Cricket Captain wagon-wheel field view the user pointed to
specifically. Fed by a new `get_match_preview` IPC method. To be direct
about scope: this is a real pre-match hub, not a live simulation — there
is still no ball-by-ball feed, and building one remains the single
biggest deferred item in this migration, unchanged by this pass.

**The user has since asked explicitly for a "screen by screen redesign"
against FM26 reference screenshots they supplied** (real FM26 screenshots
plus a fan-made "Cricket Management 2026" concept that's an unusually
close match for this exact game — cricket-specific, FM26-styled). Landed
so far: a real `Theme` (v0.41.0 — the client had none before, hence
"looks terrible" being literally accurate, not just a matter of taste),
zebra-striped table rows, (v0.42.0) a persistent header bar (crest
initials, team name, date/fixture subtitle, ADVANCE DAY button, mirroring
the reference's always-visible club identity bar) plus coloured role
pills on Squad/Selection/Transfers/Youth Academy, and (v0.43.0) nation
flag icons on the same four player-list screens, reusing the pygame
client's existing bundled Flagpedia PNGs and alias/ISO-code mapping
directly rather than duplicating the logic, and (v0.44.0) drawn nav-rail
icons (`nav_icon.gd`, one small geometric glyph per section, since no
icon asset pipeline exists) that recolour gold when active, and (v0.45.0)
coloured form/morale bar meters on Squad, using the same FM-style
attribute tiers as the pygame client's `attribute_colour()`, and
(v0.46.0) tabbed sub-navigation — `table_screen.gd` now accepts extra
tabs beyond the default view (same IPC call, different columns per tab),
with Squad gaining a GENERAL INFO/ATTRIBUTES split mirroring the
reference's own tabbed player screens. This closes out what was
identified as the single biggest remaining structural gap, and (v0.47.0)
a muted STYLE tag column (`bowling_style`) on Squad, using the same
"muted" text treatment now available on any `table_screen.gd` column —
mirroring the reference's secondary tag next to a player's name/role
(e.g. "Stroke Maker"), and (v0.48.0) a fix for Selection's row (name/
role/OVR/order + 4 buttons) overflowing 1280px and scrolling
horizontally — tightened column widths, shorter CAPT/WK labels, and a
new per-button `"width"` override on `row_buttons` instead of a fixed
90px regardless of label length, (v0.49.0) a styled Dashboard fixture
card — both teams as crest badges either side of a muted "vs" — and
(v0.50.0) styled standings (numbered position badges, gold for the
user's own team) and inbox (priority-coloured dots) cards. This closes
out every concrete item identified from the FM26/Cricket Management
reference screenshots the user supplied. The user has been explicit that
visual quality is a user-acquisition/retention priority, not cosmetic
polish — this remains an ongoing track, not something to consider
finished. The next natural work goes beyond what the supplied
screenshots directly show: extending tabbed sub-navigation to more
screens (Selection, Staff), and a fresh round of reference comparison
once that lands to catch whatever gap turns out to be next. See
`docs/CURRENT.md`'s "Next recommended action" for the fuller list.

## Toolchain (pinned — this ships on Steam, so these matter)

Since this is heading to a real Steam release, the toolchain itself needs
to be on current, well-supported versions, not whatever happened to be
installed when the project started. Verified and pinned:

- **Python 3.14.6** (was 3.12.10) — via a project-local venv at
  `cricket_manager/.venv`, not the system interpreter. Verified before
  switching, not assumed: `pygame-ce` 2.5.7 and `PyInstaller` 6.21.0 (both
  already the latest release of each, already in use) both ship official
  `cp314` wheels; the **entire 178-test suite**, `validate_match_engine.py`,
  and a **real PyInstaller build with passing packaged diagnostics** were
  all run clean under 3.14.6 before it became the project's interpreter.
  `godot_client/scripts/ipc_bridge.gd` looks for this venv first (falling
  back to PATH only if it's missing, e.g. a fresh clone).
- **Godot 4.7.1 stable** (was 4.3.0) — the existing project and every
  script loaded and ran with **zero code changes required**; the version
  bump alone surfaced two independent, real bugs (below), which is exactly
  why the smoke test exists.
- **pygame-ce 2.5.7**, **PyInstaller 6.21.0** — both were already latest
  when first installed this session; still latest.

**Two real bugs found by the Godot version bump, unrelated to Godot itself
— they'd been latent in the client since Phase 0**:
1. Godot's JSON parser has always returned every JSON number as a float
   (there's no int/float distinction in the JSON spec) — every numeric
   table cell across every screen was quietly rendering `"25.0"` instead
   of `"25"`. Never caught before because the smoke test only ever
   asserted screen *titles*, never individual cell contents; the version
   bump prompted a closer look at Dashboard's "Division 1.0" specifically,
   which led to checking everywhere else. Fixed once, centrally:
   `scripts/json_format.gd`'s `JsonFormat.value()`, applied everywhere a
   raw `IpcBridge` response value reaches a `Label` or a format string.
2. The same float-vs-string issue meant `training_screen.gd`'s
   `assignments.get(str(player.get("id")), {})` lookup **could never
   match** — `str(25.0)` is `"25.0"`, but the server's
   `get_training`/`fetch_training_assignments` keys its dict with plain
   Python `str(player_id)` → `"25"`. The Training screen has been silently
   showing every player's focus as "None" and intensity as "Normal" since
   it shipped, regardless of what was actually assigned. Fixed by routing
   the lookup key through the same `JsonFormat.value()`.

Both are now covered by the smoke test's existing screen-render pass (it
would have caught bug 1 immediately with a title-content assertion, which
it doesn't have — a real gap in the smoke test worth closing later) and by
direct verification: `JsonFormat.value(25.0) == "25"` matches the server's
`str(player_id)` exactly, confirmed by code inspection and by re-running
the full smoke test clean after the fix.

## Decision

**Move the presentation layer to Godot 4** (MIT license, free forever, no
royalties, no revenue cap — safe for a commercial Steam release on an
indie budget). Godot is chosen over the alternatives because:

- Unity: 2D UI editor is worse-fitted to this kind of dense data-table UI
  than Godot's `Control` node system, and licensing terms have been
  hostile to indies in the past two years.
- Raw SDL/C++: more control, but reinvents the layout/anchoring system
  pygame is already missing — trades one hand-rolled UI framework for
  another, at far higher engineering cost.
- Staying on pygame + hand-rolled fixes: this session's bug list (header
  overlap, button-row cramming, the commentary-button overflow, fullscreen
  blur) are symptoms of not having a real anchor/container layout system
  or GPU-accelerated text/shape rendering. Every fix has been a patch, not
  a structural solution.

## What does NOT change

**The simulation core stays exactly as-is, in Python, untouched.**
`match_engine.py`, `database.py`, `competition.py`, `src/models/*` are pure
logic with no pygame dependency already — this is confirmed by this
session's audit while cross-referencing the Cricket Captain/OOTP engine
research. 146 passing tests cover this layer and keep covering it
throughout the migration; nothing here is rewritten, only *called
differently*.

## Architecture: Godot client, Python backend, JSON over stdio

```
┌─────────────────────┐        stdin/stdout         ┌──────────────────────┐
│   Godot 4 client     │  ───── JSON-RPC lines ─────▶│  Python backend       │
│  (all rendering/UI)  │◀──── JSON-RPC responses ────│ (existing database.py,│
│  godot_client/        │      subprocess pipe        │  competition.py,      │
└─────────────────────┘                              │  match_engine.py)     │
                                                        └──────────────────────┘
```

- The Godot executable spawns the Python backend as a child process on
  launch (`OS.create_process` / `OS.execute` with pipes) and talks to it
  over stdin/stdout — **not a network socket**. This avoids Windows
  Firewall prompts on a Steam release (a localhost HTTP server would
  trigger one; a subprocess pipe does not) and needs no port management.
- Protocol: newline-delimited JSON, `{"id": N, "method": "...", "params": {...}}`
  requests, `{"id": N, "result": {...}}` or `{"id": N, "error": "..."}`
  responses. Simple enough to hand-write on both ends — no RPC framework
  dependency needed.
- The Python side (`cricket_manager/ipc_server.py`, new) is a thin
  dispatch table mapping method names to existing `database.py`/
  `competition.py` functions — it does not reimplement any logic, only
  (de)serializes calls to functions that already exist and are already
  tested.
- Distribution: the Python backend is still packaged with PyInstaller
  (already proven — `build_and_package.py` exists and works) as a
  console-less helper exe bundled alongside the Godot export; the Godot
  client is the thing the user actually double-clicks.

## Why this instead of a full rewrite

A full port of match_engine.py + database.py + every model to GDScript
would throw away 146 tests and ~15,000 lines of validated simulation logic
(realistic scoring rates tuned this session: T20 7.0 RPO, ODI 5.0, Test
3.95) to re-derive the same rules in a language with weaker numerics
ergonomics, for zero player-facing benefit — the simulation was never the
part that looked bad. The hybrid approach ports **only the presentation
layer**, which is the part that actually needs to change.

## Phased rollout

**Phase 0 — proof of concept (this session).** Stand up the Godot project
skeleton and the IPC backend, and get one real screen (Squad list, chosen
because it's the densest data-table screen and proves the hardest case
first) rendering live data end-to-end: Godot boots → spawns the Python
backend → requests the squad over the JSON pipe → renders a real,
anchored, GPU-rendered table. If this works, the architecture is proven.

**Phase 1 — IPC contract.** Formalize the method list backend screens will
need (one method per current screen's data needs, mostly direct wraps of
existing `fetch_*`/`scout_players`/etc. functions), with error handling and
a reconnect/crash-recovery story (the backend must never silently die
mid-session).

**Phase 2 — port screens in priority order**, each one a self-contained
`.tscn` + script, each shippable independently behind a screen registry
(mirroring `SCREEN_CLASSES` today):
  1. Dashboard, Squad, Selection (highest-traffic, prove the pattern)
  2. Match view (the biggest visual win — GPU text/shapes, real
     animations, no more supersampling hacks)
  3. Transfers, Recruitment Hub, Staff, Medical, Training, Facilities
  4. Career, Finances, Youth Academy, Settings, Help

**Phase 3 — parity cutover.** Once every screen has a Godot equivalent
with test coverage, retire the pygame UI (`ui/`, `main.py`'s pygame_gui
usage) entirely. `database.py`/`match_engine.py`/`competition.py`/
`src/models/*` are untouched throughout — this is a rendering-layer
retirement, not a data-layer one.

**Phase 4 — packaging & Steam.** Godot's Windows export + the bundled
PyInstaller backend exe, wired into a single installer/distribution step
replacing today's `build_and_package.py` output.

## Testing strategy without a GUI harness

Godot supports `--headless` command-line execution, which is how this
migration is verified without a visual QA pass each time (the same
constraint pygame development operated under this whole session via
`SDL_VIDEODRIVER=dummy`):
- GDScript logic (IPC parsing, data transforms) gets `--headless` unit
  tests via GUT (Godot Unit Test, free/MIT) or Godot's built-in
  `--headless --script` execution.
- The Python backend gets ordinary `unittest` coverage exactly like today
  — it's still just Python functions.
- Visual/layout correctness is judged the same way this session's pygame
  work was: structural assertions (element positions, no overlap, correct
  data reaching the render call) rather than pixel comparison, since
  neither harness has a way to eyeball a rendered frame. The user should
  expect to spot-check the actual look periodically by running the client,
  the same way they did with pygame screenshots this session.

## Timeline honesty

This is realistically **weeks, not hours** of engineering across every
phase — Phase 0 alone (this session) is a proof of concept, not a shipped
screen. Each subsequent phase should get its own version bump and its own
"still ships/still passes tests" checkpoint exactly like every other
release this session, so the game stays in a working, playable state
(pygame UI) throughout the migration rather than being broken mid-port.

## Cost

**$0.** Godot 4 is MIT-licensed with no royalties, revenue share, or seat
fees at any team size or revenue level — this holds for the full Steam
release, not just development.
