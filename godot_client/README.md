# godot_client — Phase 0 proof of concept

See [`docs/GRAPHICS_MIGRATION_PLAN.md`](../docs/GRAPHICS_MIGRATION_PLAN.md)
for the full plan. This directory is the Godot 4 side of the hybrid
architecture: Godot renders, the existing Python `cricket_manager` package
(unchanged) supplies data over a JSON-RPC-over-stdio pipe
(`cricket_manager/ipc_server.py`).

## Running it

Requires the Godot 4.3 editor (not committed — `tools/godot/` is
gitignored; download the "Standard" Windows build from
https://godotengine.org/download and point the commands below at it) and a
`python` on PATH able to import the `cricket_manager` package (i.e. the
same environment `cricket_manager/main.py` runs in).

```sh
# Interactive (opens a window):
godot --path godot_client

# Headless smoke test (renders once against real save data, exits 0/1):
godot --headless --path godot_client -- --smoke-test
```

## What's here

- `project.godot` — minimal project config, `IpcBridge` autoload.
- `scripts/ipc_bridge.gd` — owns the Python backend subprocess and the
  request/response protocol. No simulation logic lives here.
- `scripts/squad_screen.gd` + `scenes/squad_screen.tscn` — the proof of
  concept: a real anchored/container-based table (not hand-computed pixel
  rects) rendering live squad data fetched over the pipe.

## Known gotcha (fixed, keep in mind for future backend calls)

The backend calls `prepare_environment(..., interactive=False)` —
`interactive=True` (the pygame client's default) can pop a native
`MessageBoxW` "restore last session?" dialog after an unclean exit, which
hangs a headless subprocess forever since nothing can click it. Any new
headless/automated caller of `src.utilities.launcher.prepare_environment`
must pass `interactive=False`.
