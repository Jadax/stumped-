extends Control
## v4.27.0: a real Calendar screen — repeatedly asked for across several
## rounds of feedback. Backend's get_calendar (database.fetch_calendar)
## reuses existing tables (matches, training_assignments), no new schema:
## every fixture (played and upcoming) for the user's team, plus which
## weekdays the squad currently trains on.

const WEEKDAY_NAMES := ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
const FRIENDLY_FORMATS := ["T20", "ODI", "Test"]

@onready var title_label: Label = $Title
@onready var weekday_row: HBoxContainer = $MainCol/TrainingCard/Box/WeekdayRow
@onready var fixtures_list: VBoxContainer = $MainCol/FixturesCard/Box/Scroll/List
@onready var friendlies_list: VBoxContainer = $MainCol/FriendliesCard/Box/List
@onready var opponent_option: OptionButton = $MainCol/FriendliesCard/Box/ScheduleRow/OpponentOption
@onready var date_input: LineEdit = $MainCol/FriendliesCard/Box/ScheduleRow/DateInput
@onready var format_option: OptionButton = $MainCol/FriendliesCard/Box/ScheduleRow/FormatOption
@onready var schedule_button: Button = $MainCol/FriendliesCard/Box/ScheduleRow/ScheduleButton


func _ready() -> void:
	for format_name in FRIENDLY_FORMATS:
		format_option.add_item(format_name)
	schedule_button.pressed.connect(_on_schedule_pressed)


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
	_refresh_friendlies()


## v5.1.0: get_friendly_fixtures + schedule_friendly had no client caller —
## the Calendar screen now lists this season's friendlies and lets you book
## new ones (opponent dropdown, date, format). schedule_friendly rejects
## double-booked dates server-side; its ValueError surfaces as an IPC error.
func _refresh_friendlies() -> void:
	var response := IpcBridge.call_method("get_friendly_fixtures")
	if response.has("error"):
		push_error("CalendarScreen friendlies: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	_fill_opponents(result.get("teams", []))
	for child in friendlies_list.get_children():
		child.queue_free()
	var fixtures: Array = result.get("fixtures", [])
	if fixtures.is_empty():
		var empty := Label.new()
		empty.text = "No friendlies scheduled this season — book one below."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		friendlies_list.add_child(empty)
		return
	var team_id: int = int(result.get("team", {}).get("id", 0))
	for entry in fixtures:
		var is_home: bool = int(entry.get("home_team", 0)) == team_id
		var opponent: String = str(entry.get("away_name", "?")) if is_home else str(entry.get("home_name", "?"))
		var status := "played" if bool(entry.get("completed", false)) else "upcoming"
		var row := Label.new()
		row.text = "%s  —  %s %s  (%s)" % [str(entry.get("date", "?")),
			"H" if is_home else "A", opponent, status]
		row.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
		friendlies_list.add_child(row)


func _fill_opponents(teams: Array) -> void:
	var selected_text := opponent_option.get_item_text(opponent_option.selected) \
		if opponent_option.selected >= 0 and opponent_option.item_count > 0 else ""
	opponent_option.clear()
	if teams.is_empty():
		return
	opponent_option.select(0)
	for team in teams:
		opponent_option.add_item(str(team.get("name", "?")), int(team.get("id", 0)))
	if selected_text != "":
		for i in range(opponent_option.item_count):
			if opponent_option.get_item_text(i) == selected_text:
				opponent_option.select(i)
				break


func _on_schedule_pressed() -> void:
	var date_text := date_input.text.strip_edges()
	if opponent_option.selected < 0:
		_show_schedule_feedback("Choose an opponent first.", AppTheme.GOLD)
		return
	if date_text.length() != 10:
		_show_schedule_feedback("Enter a date as YYYY-MM-DD.", AppTheme.GOLD)
		return
	var response := IpcBridge.call_method("schedule_friendly", {
		"away_team_id": opponent_option.get_selected_id(),
		"date": date_text,
		"format": FRIENDLY_FORMATS[format_option.selected],
	})
	if response.has("error"):
		_show_schedule_feedback(str(response["error"]), AppTheme.GOLD)
		return
	date_input.text = ""
	_show_schedule_feedback("Friendly booked.", AppTheme.HEADER_GREEN)
	_refresh_friendlies()


func _show_schedule_feedback(text: String, colour: Color) -> void:
	var feedback := Label.new()
	feedback.text = text
	feedback.add_theme_color_override("font_color", colour)
	friendlies_list.add_child(feedback)


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
