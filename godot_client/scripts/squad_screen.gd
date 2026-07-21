extends Control
## Phase 0 proof of concept (docs/GRAPHICS_MIGRATION_PLAN.md): the densest
## data-table screen in the pygame client, rebuilt with real anchored
## containers instead of hand-computed pixel rects, fed by the existing
## Python simulation/data layer over IpcBridge.

@onready var title_label: Label = $Title
@onready var row_list: VBoxContainer = $ScrollContainer/RowList

const COLUMN_WIDTH := 160


func _ready() -> void:
	var response := IpcBridge.call_method("get_squad")
	if response.has("error"):
		title_label.text = "SQUAD — backend error: %s" % response["error"]
		push_error("SquadScreen: %s" % response["error"])
		_exit_if_smoke_test()
		return
	var result: Dictionary = response["result"]
	var team: Dictionary = result["team"]
	var players: Array = result["players"]
	title_label.text = "%s — %d players" % [team.get("name", "?"), players.size()]
	for child in row_list.get_children():
		child.queue_free()
	_add_row(["NAME", "AGE", "ROLE", "OVR"], true)
	for player in players:
		_add_row([
			str(player.get("name", "?")),
			str(player.get("age", "?")),
			str(player.get("role", "?")),
			str(player.get("overall", "?")),
		], false)
	_exit_if_smoke_test()


func _add_row(values: Array, is_header: bool) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	for value in values:
		var label := Label.new()
		label.text = str(value)
		label.custom_minimum_size = Vector2(COLUMN_WIDTH, 0)
		if is_header:
			label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.75))
		row.add_child(label)
	row_list.add_child(row)


## `godot --headless --path . -- --smoke-test` renders once against real
## data and exits with a status code, for a scriptable CI-style check
## without needing a GUI or a person watching a window.
func _exit_if_smoke_test() -> void:
	if "--smoke-test" in OS.get_cmdline_user_args():
		print("SMOKE TEST: %s" % title_label.text)
		get_tree().quit(1 if title_label.text.begins_with("SQUAD — backend error") else 0)
