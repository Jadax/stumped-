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

Screens not yet ported show the same "Coming Soon" placeholder the pygame
`BaseScreen` falls back to (`placeholder_screen.gd`): **Training, Youth
Academy, Medical Centre, Match, Recruitment**. Match view in particular is
a substantially bigger job than the others — it needs a live ball-by-ball
feed, not just a data table — and is intentionally sequenced after the
simpler screens.

**Verification**: `shell.gd` has its own `--smoke-test` mode that cycles
every registered screen (not just one) and fails on any backend-error
title, run via
`godot --headless --path godot_client -- --smoke-test`. Two real bugs were
caught this way before they shipped (a GDScript type-inference issue in
Dashboard's standings render, and a `configure()`-before-`_ready()` timing
bug in the placeholder screen) — run 3x consecutively with zero errors.

**What's still not done, to be direct about it**: every screen shipped so
far is read-only display. None of the interactive flows are ported yet —
XI selection (drag/drop), training focus assignment, facility upgrade
requests, contract negotiation, staff hiring/firing, the match view itself.
"Complete everything" for a full engine migration remains realistically
multiple more sessions of work; this update is real, substantial progress
against that goal, not the finish line.

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
