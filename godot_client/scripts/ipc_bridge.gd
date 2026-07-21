extends Node
## Autoload singleton: owns the Python backend subprocess and the
## JSON-RPC-over-stdio protocol described in docs/GRAPHICS_MIGRATION_PLAN.md.
## No simulation logic lives here — every call forwards to a function that
## already exists (and is already tested) in the Python cricket_manager package.

var _process_info: Dictionary
var _stdio: FileAccess
var _stderr: FileAccess
var _next_id: int = 1


func _ready() -> void:
	var python_path := _resolve_python()
	if python_path.is_empty():
		push_error("IpcBridge: could not find a python executable (checked the project .venv and PATH)")
		return
	var script_path := ProjectSettings.globalize_path("res://../cricket_manager/ipc_server.py")
	_process_info = OS.execute_with_pipe(python_path, [script_path])
	if _process_info.is_empty():
		push_error("IpcBridge: failed to start the Python backend at %s" % script_path)
		return
	_stdio = _process_info["stdio"]
	_stderr = _process_info["stderr"]


## Prefers the project-local venv (pinned Python version, isolated
## dependencies — see cricket_manager/README.md "Getting started" and
## docs/GRAPHICS_MIGRATION_PLAN.md "Toolchain") over whatever "python"
## happens to resolve to on PATH, which is fragile: it can silently pick up
## an unrelated interpreter with the wrong packages. Falls back to PATH so
## a fresh clone without the venv set up yet still runs.
func _resolve_python() -> String:
	var venv_python := ProjectSettings.globalize_path("res://../cricket_manager/.venv/Scripts/python.exe")
	if FileAccess.file_exists(venv_python):
		return venv_python
	var output: Array = []
	OS.execute("cmd", ["/c", "where python"], output)
	if output.is_empty():
		return ""
	return String(output[0]).split("\n")[0].strip_edges()


## Blocking request/response — fine for turn-based management-sim data
## fetches; long-running work (e.g. simulating a match) should get an
## async/polling method once the protocol needs one (not required in Phase 0).
##
## Reads on the pipe FileAccess return immediately with "" rather than
## blocking when no data is ready yet, and the backend's first response can
## take a moment (it runs the full database bootstrap before reading
## stdin) — so this polls for a real line instead of trusting the first read.
func call_method(method_name: String, params: Dictionary = {}, timeout_msec: int = 15000) -> Dictionary:
	if _stdio == null:
		return {"error": "backend not running"}
	var id := _next_id
	_next_id += 1
	var request := {"id": id, "method": method_name, "params": params}
	_stdio.store_string(JSON.stringify(request) + "\n")
	_stdio.flush()
	var waited := 0
	var line := ""
	while waited < timeout_msec:
		line = _stdio.get_line()
		if not line.is_empty():
			break
		OS.delay_msec(20)
		waited += 20
	if line.is_empty():
		return {"error": "backend did not respond within %dms" % timeout_msec, "stderr": _drain_stderr()}
	var parsed = JSON.parse_string(line)
	if typeof(parsed) != TYPE_DICTIONARY:
		return {"error": "malformed response: %s" % line}
	return parsed


func _drain_stderr() -> String:
	var text := ""
	while _stderr != null and not _stderr.eof_reached():
		var chunk := _stderr.get_line()
		if chunk.is_empty():
			break
		text += chunk + "\n"
	return text


func shutdown() -> void:
	if _stdio:
		call_method("quit")
		_stdio.close()
	if _process_info.has("pid"):
		OS.kill(_process_info["pid"])


func _exit_tree() -> void:
	shutdown()
