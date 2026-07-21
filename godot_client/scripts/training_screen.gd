extends Control
## Squad training focus — merges get_training's player list and its
## per-player assignment dict (mirrors ui/training.py combining
## database.fetch_training_assignments with the squad).

@onready var title_label: Label = $Title
@onready var row_list: VBoxContainer = $ScrollContainer/RowList

const COLUMN_WIDTH := 150


func _ready() -> void:
	var response := IpcBridge.call_method("get_training")
	if response.has("error"):
		title_label.text = "TRAINING — backend error: %s" % response["error"]
		push_error("TrainingScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	var players: Array = result["players"]
	var assignments: Dictionary = result["assignments"]
	title_label.text = "TRAINING — %d players" % players.size()
	for child in row_list.get_children():
		child.queue_free()
	_add_row(["NAME", "ROLE", "FOCUS", "INTENSITY", "LAST TRAINED"], true)
	for player in players:
		var assignment: Dictionary = assignments.get(str(player.get("id")), {})
		_add_row([
			str(player.get("name", "?")),
			str(player.get("role", "?")),
			str(assignment.get("focus", "None")),
			str(assignment.get("intensity", "Normal")),
			str(assignment.get("last_trained", "—")),
		], false)


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
