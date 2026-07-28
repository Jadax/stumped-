extends Control
## Ports database.py's fetch_honours into a real trophy room (v0.80.0):
## previously a bare flat list capped visually at the last 12 entries with
## no sense of which competitions had actually been won how often. Left
## card groups the same rows by competition title; right card is the full
## chronological cabinet, unclipped.

@onready var title_label: Label = $Title
@onready var breakdown_list: VBoxContainer = $Row/BreakdownCard/Box/Scroll/List
@onready var cabinet_list: VBoxContainer = $Row/CabinetCard/Box/Scroll/List


func _ready() -> void:
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_trophy_room")
	if response.has("error"):
		title_label.text = "TROPHY ROOM — backend error: %s" % response["error"]
		push_error("TrophyRoomScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	_render_breakdown(result.get("breakdown", []))
	_render_cabinet(result.get("honours", []))
	title_label.text = "TROPHY ROOM — %d HONOUR%s" % [result.get("total", 0), "" if result.get("total", 0) == 1 else "S"]


func _clear(list: VBoxContainer) -> void:
	for child in list.get_children():
		list.remove_child(child)
		child.queue_free()


func _render_breakdown(breakdown: Array) -> void:
	_clear(breakdown_list)
	if breakdown.is_empty():
		var empty := Label.new()
		empty.text = "The cabinet is waiting for its first trophy."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		breakdown_list.add_child(empty)
		return
	for entry in breakdown:
		var row := VBoxContainer.new()
		row.add_theme_constant_override("separation", 2)
		var head := HBoxContainer.new()
		var title := Label.new()
		title.text = str(entry.get("title", "—"))
		title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		head.add_child(title)
		var count := Label.new()
		var won: int = int(entry.get("count", 0))
		count.text = "x%d" % won
		count.add_theme_color_override("font_color", AppTheme.GOLD)
		head.add_child(count)
		row.add_child(head)
		var seasons: Array = entry.get("seasons", [])
		var seasons_label := Label.new()
		seasons_label.text = ", ".join(seasons.map(func(s): return str(s)))
		seasons_label.add_theme_font_size_override("font_size", 10)
		seasons_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		seasons_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		row.add_child(seasons_label)
		breakdown_list.add_child(row)
		breakdown_list.add_child(HSeparator.new())


func _render_cabinet(honours: Array) -> void:
	_clear(cabinet_list)
	if honours.is_empty():
		var empty := Label.new()
		empty.text = "No silverware yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		cabinet_list.add_child(empty)
		return
	for honour in honours:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 10)
		var season_label := Label.new()
		season_label.text = str(honour.get("season", "—"))
		season_label.custom_minimum_size = Vector2(70, 0)
		season_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		season_label.add_theme_font_size_override("font_size", 11)
		row.add_child(season_label)
		var title_text := Label.new()
		title_text.text = str(honour.get("title", "—"))
		title_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		title_text.add_theme_font_size_override("font_size", 12)
		row.add_child(title_text)
		cabinet_list.add_child(row)
