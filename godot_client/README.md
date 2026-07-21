# godot_client — Godot 4 presentation layer

See [`docs/GRAPHICS_MIGRATION_PLAN.md`](../docs/GRAPHICS_MIGRATION_PLAN.md)
for the full plan and status. This is the Godot 4 side of the hybrid
architecture: Godot renders, the existing Python `cricket_manager` package
(unchanged) supplies data over a JSON-RPC-over-stdio pipe
(`cricket_manager/ipc_server.py`). 16 screens are registered, 15 render
real save data; Match view (live ball-by-ball feed) is still a "Coming
Soon" placeholder.

## Toolchain (pinned — this ships on Steam, so these matter)

- **Godot 4.7.1 stable** — not committed; `tools/godot/` is gitignored.
  Download the "Standard" Windows build from
  https://godotengine.org/download and point the commands below at it.
- **Python 3.14.6**, via the project-local venv at
  `cricket_manager/.venv` (see the main README's "Windows installation for
  development" section — `IpcBridge.gd` looks for this venv first and
  only falls back to whatever `python` resolves to on PATH if it's
  missing, e.g. on a fresh clone before the venv is set up).
- **pygame-ce 2.5.7**, **PyInstaller 6.21.0** — both ship official `cp314`
  wheels; confirmed clean (full test suite + a real packaged build) under
  3.14.6 before switching to it.

## Running it

```sh
# Interactive (opens a window):
godot --path godot_client

# Headless smoke test (cycles every registered screen and every
# interactive flow against real save data, exits 0/1):
godot --headless --path godot_client -- --smoke-test
```

If a fresh checkout shows `SCRIPT ERROR: Identifier "X" not declared in
the current scope` for a `class_name` script (e.g. `JsonFormat`), run a
one-time headless editor scan first so Godot registers global script
classes — needed after adding a new `class_name` file, not on every run:

```sh
godot --headless --path godot_client --editor --quit
```

## What's here

- `project.godot` — project config, `IpcBridge` autoload.
- `scripts/ipc_bridge.gd` — owns the Python backend subprocess and the
  JSON-RPC-over-stdio protocol. No simulation logic lives here.
- `scripts/shell.gd` + `scenes/shell.tscn` — the persistent chrome: a
  sidebar mirroring `main.py`'s `NAV_GROUPS`, a content area that swaps
  screens, and the `--smoke-test` harness.
- `scripts/table_screen.gd` + `scenes/table_screen.tscn` — the reusable
  generic list/table screen (mirrors how the pygame client reuses
  `ui/widgets/datatable.py`'s `DataTable`). Configure with a title, an IPC
  method, a column list, and optionally a `row_action` (whole row
  clickable, one action) or `row_buttons` (explicit per-row buttons, for
  when one action isn't enough, e.g. Accept/Reject). Powers most screens:
  Inbox, Staff, Staff Market, Transfers, Offers, Finances, Facilities,
  Career/Honours, Youth Academy, Medical Centre, Selection.
- `scripts/dashboard_screen.gd`, `squad_screen.gd`, `training_screen.gd`,
  `recruitment_screen.gd` — bespoke screens where the generic table didn't
  fit (cards, merged data sources, tiled layouts).
- `scripts/json_format.gd` — `JsonFormat.value()`. Godot's JSON parser
  returns every number as a float (no int/float distinction in the JSON
  spec), so anything from an `IpcBridge` response needs this before
  display or it renders/compares as `"25.0"` instead of `"25"`. Route any
  raw JSON value through it — this already caught one real display bug
  and one real dict-key-mismatch bug (see CHANGELOG v0.38.0).
- `scripts/placeholder_screen.gd` — the "Coming Soon" fallback for screens
  not yet ported (currently just Match), mirroring
  `ui/shared_components.py`'s `BaseScreen`.

## Known gotchas

- The backend calls `prepare_environment(..., interactive=False)` —
  `interactive=True` (the pygame client's default) can pop a native
  `MessageBoxW` "restore last session?" dialog after an unclean exit,
  which hangs a headless subprocess forever since nothing can click it.
  Any new headless/automated caller of
  `src.utilities.launcher.prepare_environment` must pass
  `interactive=False`.
- Any value read from an `IpcBridge.call_method()` response and displayed
  or used as a dictionary key must go through `JsonFormat.value()` first —
  see above.
