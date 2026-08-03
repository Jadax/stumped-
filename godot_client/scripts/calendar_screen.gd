extends Control
## v4.27.0: a real Calendar screen — repeatedly asked for across several
## rounds of feedback. Backend's get_calendar (database.fetch_calendar)
## reuses existing tables (matches, training_assignments), no new schema:
## every fixture (played and upcoming) for the user's team, plus which
## weekdays the squad currently trains on.

const WEEKDAY_NAMES := ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

@onready var title_label: Label = $Title
@onready var weekday_row: HBoxContainer = $MainCol/TrainingCard/Box/WeekdayRow
@onready var fixtures_list: VBoxContainer = $MainCol/FixturesCard/Box/Scroll/List


func _ready() -> void:
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_calendar")
	if response.has("error"):
		title_label.text = "CALENDAR — backend error: %s" % response["error"]
		push_error("CalendarScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	_render_training_days(result.get("training_weekday_counts", []))
	_render_fixtures(result.get("fixtures", []), str(result.get("current_date", "")))
	title_label.text = "CALENDAR"


func _render_training_days(counts: Array) -> void:
	for child in weekday_row.get_children():
		weekday_row.remove_child(child)
		child.queue_free()
	for i in range(WEEKDAY_NAMES.size()):
		var count: int = int(counts[i]) if i < counts.size() else 0
		var badge := PanelContainer.new()
		badge.custom_minimum_size = Vector2(70, 44)
		var box := StyleBoxFlat.new()
		box.set_corner_radius_all(8)
		box.bg_color = AppTheme.HEADER_GREEN if count > 0 else AppTheme.CARD
		box.set_border_width_all(1)
		box.border_color = AppTheme.BORDER
		badge.add_theme_stylebox_override("panel", box)
		var col := VBoxContainer.new()
		col.alignment = BoxContainer.ALIGNMENT_CENTER
		var day_label := Label.new()
		day_label.text = WEEKDAY_NAMES[i]
		day_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		day_label.add_theme_font_size_override("font_size", 11)
		day_label.add_theme_color_override("font_color", AppTheme.CARD if count > 0 else AppTheme.TEXT_MUTED)
		col.add_child(day_label)
		var count_label := Label.new()
		count_label.text = "%d training" % count if count > 0 else "—"
		count_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		count_label.add_theme_font_size_override("font_size", 9)
		count_label.add_theme_color_override("font_color", AppTheme.CARD if count > 0 else AppTheme.TEXT_MUTED)
		col.add_child(count_label)
		badge.add_child(col)
		weekday_row.add_child(badge)


func _render_fixtures(fixtures: Array, current_date: String) -> void:
	for child in fixtures_list.get_children():
		fixtures_list.remove_child(child)
		child.queue_free()
	if fixtures.is_empty():
		var empty := Label.new()
		empty.text = "No fixtures scheduled yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		fixtures_list.add_child(empty)
		return
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 10)
	for text in ["DATE", "OPPONENT", "H/A", "FORMAT", "RESULT"]:
		var head := Label.new()
		head.text = text
		head.add_theme_font_size_override("font_size", 10)
		head.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		head.custom_minimum_size = Vector2(280, 0) if text == "OPPONENT" else Vector2(90, 0)
		header.add_child(head)
	fixtures_list.add_child(header)
	fixtures_list.add_child(HSeparator.new())
	for entry in fixtures:
		var row := PanelContainer.new()
		var box := StyleBoxFlat.new()
		box.content_margin_left = 8
		box.content_margin_right = 8
		box.content_margin_top = 4
		box.content_margin_bottom = 4
		box.set_corner_radius_all(4)
		var is_today: bool = str(entry.get("date", "")) == current_date
		box.bg_color = AppTheme.HOVER if is_today else AppTheme.CARD
		if is_today:
			box.border_width_left = 3
			box.border_color = AppTheme.GOLD
		row.add_theme_stylebox_override("panel", box)
		var hbox := HBoxContainer.new()
		hbox.add_theme_constant_override("separation", 10)
		var date_label := Label.new()
		date_label.text = str(entry.get("date", "?"))
		date_label.custom_minimum_size = Vector2(90, 0)
		hbox.add_child(date_label)
		var opponent_label := Label.new()
		opponent_label.text = str(entry.get("opponent", "?"))
		opponent_label.custom_minimum_size = Vector2(280, 0)
		hbox.add_child(opponent_label)
		var home_label := Label.new()
		home_label.text = "HOME" if bool(entry.get("home", false)) else "AWAY"
		home_label.custom_minimum_size = Vector2(90, 0)
		home_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
		hbox.add_child(home_label)
		var format_label := Label.new()
		format_label.text = str(entry.get("format", "?"))
		format_label.custom_minimum_size = Vector2(90, 0)
		hbox.add_child(format_label)
		var result_label := Label.new()
		var completed: bool = bool(entry.get("completed", false))
		var summary = entry.get("result_summary")
		result_label.text = str(summary) if completed and summary != null else ("Played" if completed else "Upcoming")
		result_label.custom_minimum_size = Vector2(90, 0)
		result_label.add_theme_font_size_override("font_size", 11)
		result_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED if not completed else AppTheme.TEXT_PRIMARY)
		hbox.add_child(result_label)
		row.add_child(hbox)
		fixtures_list.add_child(row)
