extends Control
## v5.1.0: ports league_leaders (src/models/leaders.py) and the season
## award history (record_season_awards) to the Godot client — both
## backend systems existed for releases but had no caller. Live career
## race tables (runs, wickets) plus the recorded season awards, so award
## winners are visible somewhere a manager actually visits again.

@onready var title_label: Label = $Title
@onready var runs_list: VBoxContainer = $Row/RunsCard/Box/Scroll/List
@onready var wickets_list: VBoxContainer = $Row/WicketsCard/Box/Scroll/List
@onready var awards_list: VBoxContainer = $Row/AwardsCard/Box/Scroll/List


func _ready() -> void:
	refresh()


func refresh() -> void:
	var leaders_response := IpcBridge.call_method("get_league_leaders")
	if leaders_response.has("error"):
		title_label.text = "LEAGUE LEADERS — backend error: %s" % leaders_response["error"]
		push_error("LeadersScreen: %s" % leaders_response["error"])
		return
	var awards_response := IpcBridge.call_method("get_season_awards_history", {"limit": 10})
	_render(runs_list, leaders_response["result"].get("most_runs", []), "runs")
	_render(wickets_list, leaders_response["result"].get("most_wickets", []), "wickets")
	title_label.text = "LEAGUE LEADERS"
	if not awards_response.has("error"):
		_render_awards(awards_response["result"].get("awards", []))


func _clear(list: VBoxContainer) -> void:
	for child in list.get_children():
		list.remove_child(child)
		child.queue_free()


func _render(list: VBoxContainer, rows: Array, stat_key: String) -> void:
	_clear(list)
	if rows.is_empty():
		list.add_child(_label("Not enough matches played yet.", AppTheme.TEXT_MUTED, 11))
		return
	for index in rows.size():
		var row: Dictionary = rows[index]
		var entry := HBoxContainer.new()
		entry.add_theme_constant_override("separation", 8)
		entry.add_child(_label(str(index + 1), AppTheme.TEXT_MUTED, 12, 26))
		entry.add_child(_label(str(row.get("name", "?")), AppTheme.TEXT_PRIMARY, 13, 0, true))
		entry.add_child(_label(str(row.get("team_name", "")), AppTheme.TEXT_MUTED, 11, 0, true))
		entry.add_child(_label(JsonFormat.value(row.get(stat_key, 0)), AppTheme.ACCENT, 13, 52, false, true))
		list.add_child(entry)


func _render_awards(rows: Array) -> void:
	_clear(awards_list)
	if rows.is_empty():
		awards_list.add_child(_label("No season completed yet.", AppTheme.TEXT_MUTED, 11))
		return
	for row in rows:
		var entry := HBoxContainer.new()
		entry.add_theme_constant_override("separation", 8)
		entry.add_child(_label(str(row.get("season", "?")), AppTheme.GOLD, 12, 70))
		entry.add_child(_label(str(row.get("award_type", "?")), AppTheme.TEXT_MUTED, 12, 110, false))
		entry.add_child(_label(str(row.get("player_name", "?")), AppTheme.TEXT_PRIMARY, 13, 0, true))
		entry.add_child(_label(str(row.get("team_name", "")), AppTheme.TEXT_MUTED, 11, 0, true))
		awards_list.add_child(entry)


func _label(text: String, colour: Color, size: int, width: int = 0, expand: bool = false, right: bool = false) -> Label:
	var label := Label.new()
	label.text = text
	if width > 0:
		label.custom_minimum_size = Vector2(width, 0)
	if expand:
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		label.clip_text = true
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT if right else HORIZONTAL_ALIGNMENT_LEFT
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", colour)
	return label
