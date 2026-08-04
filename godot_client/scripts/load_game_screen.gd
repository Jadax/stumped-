extends Control
## v0.90.0: real multi-save-slot system. Previously "Load Game" on Main Menu
## just called show_screen("Dashboard") — it re-entered whatever the single
## existing database held, because no save-slot concept existed anywhere.
## Chrome-less (shell.gd's STARTUP_SCREEN_NAMES), reached from Main Menu's
## LOAD GAME button.

@onready var list: VBoxContainer = $Card/Box/Scroll/List
@onready var back_button: Button = $Footer/BackButton

var _pending_delete_id: String = ""


func _ready() -> void:
	back_button.pressed.connect(func(): _shell().show_screen("Main Menu"))
	refresh()


func _shell() -> Node:
	return get_tree().get_first_node_in_group("shell")


func refresh() -> void:
	_pending_delete_id = ""
	var response := IpcBridge.call_method("list_saves")
	if response.has("error"):
		push_error("LoadGameScreen: %s" % response["error"])
		return
	_render(response["result"].get("saves", []))


func _clear() -> void:
	for child in list.get_children():
		list.remove_child(child)
		child.queue_free()


func _render(saves: Array) -> void:
	_clear()
	if saves.is_empty():
		var empty := Label.new()
		empty.text = "No saves yet — start a New Game from the Main Menu."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		list.add_child(empty)
		return
	for save in saves:
		list.add_child(_save_row(save))


func _save_row(save: Dictionary) -> Control:
	var card := PanelContainer.new()
	var box := HBoxContainer.new()
	box.add_theme_constant_override("separation", 14)
	card.add_child(box)

	var info := VBoxContainer.new()
	info.size_flags_horizontal = SIZE_EXPAND_FILL
	info.add_theme_constant_override("separation", 2)
	var name_label := Label.new()
	name_label.text = str(save.get("display_name", "Save"))
	name_label.add_theme_font_size_override("font_size", 16)
	info.add_child(name_label)
	var team_name = save.get("team_name")
	var division = save.get("division")
	var manager_name = save.get("manager_name")
	var current_date = save.get("current_date")
	var detail_parts: Array = []
	if team_name:
		detail_parts.append("%s%s" % [team_name, " — Division %s" % JsonFormat.value(division) if division else ""])
	if manager_name:
		detail_parts.append("Managed by %s" % manager_name)
	if current_date:
		detail_parts.append("In-game: %s" % str(current_date))
	var detail_label := Label.new()
	detail_label.text = " • ".join(detail_parts) if not detail_parts.is_empty() else "New save — no career started yet"
	detail_label.add_theme_font_size_override("font_size", 12)
	detail_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	info.add_child(detail_label)
	# v4.28.0: real wall-clock saved date/time — the "In-game" date above is
	# the career's own calendar date, not when this save was last opened,
	# and the list is now sorted by this same value (most recent first).
	var played_at = save.get("last_played_at")
	var saved_label := Label.new()
	saved_label.text = "Last played %s" % _format_timestamp(str(played_at)) if played_at \
		else "Created %s" % _format_timestamp(str(save.get("created_at", "")))
	saved_label.add_theme_font_size_override("font_size", 11)
	saved_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	info.add_child(saved_label)
	box.add_child(info)

	var continue_button := Button.new()
	continue_button.custom_minimum_size = Vector2(120, 36)
	continue_button.text = "CONTINUE"
	continue_button.pressed.connect(_on_continue_pressed.bind(str(save.get("id", ""))))
	box.add_child(continue_button)

	var delete_button := Button.new()
	delete_button.custom_minimum_size = Vector2(120, 36)
	var save_id: String = str(save.get("id", ""))
	delete_button.text = "CONFIRM DELETE?" if save_id == _pending_delete_id else "DELETE"
	delete_button.pressed.connect(_on_delete_pressed.bind(save_id))
	box.add_child(delete_button)

	return card


## Manifest timestamps are ISO 8601 ("2026-08-03T21:45:12") — a compact
## "Aug 3, 21:45" reads far better in a save-list row than the raw string.
func _format_timestamp(iso: String) -> String:
	if iso.is_empty():
		return "—"
	var parts := iso.split("T")
	if parts.size() != 2:
		return iso
	var date_parts := parts[0].split("-")
	if date_parts.size() != 3:
		return iso
	const MONTHS := ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	var month_index := int(date_parts[1])
	var month_name: String = MONTHS[month_index] if month_index >= 1 and month_index <= 12 else date_parts[1]
	var time_part := parts[1].substr(0, 5)
	return "%s %d, %s" % [month_name, int(date_parts[2]), time_part]


func _on_continue_pressed(save_id: String) -> void:
	var response := IpcBridge.call_method("load_save", {"id": save_id})
	if response.has("error"):
		push_error("LoadGameScreen: %s" % response["error"])
		return
	var shell := _shell()
	shell.refresh_header()
	shell.show_screen(str(response["result"].get("destination", "Dashboard")))


## First click on DELETE arms it (button relabels to CONFIRM DELETE?), a
## second click on the same row actually deletes — no separate modal dialog
## needed for a single-row destructive action.
func _on_delete_pressed(save_id: String) -> void:
	if _pending_delete_id != save_id:
		_pending_delete_id = save_id
		var response := IpcBridge.call_method("list_saves")
		if not response.has("error"):
			_render(response["result"].get("saves", []))
		return
	var response := IpcBridge.call_method("delete_save", {"id": save_id})
	if response.has("error"):
		push_error("LoadGameScreen: %s" % response["error"])
		return
	_pending_delete_id = ""
	_render(response["result"].get("saves", []))
