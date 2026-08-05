extends Control
## Training's real interactivity — ports ui/training.py's split-view UI
## (squad table + a detail card with programme/intensity/schedule
## controls and simulation actions) rather than table_screen.gd's generic
## list, since pygame's version needs a bespoke table+detail layout with
## per-column inline cycling, not a fit for the shared component.

const DAY_LETTERS := "MTWTFSS"
const DAY_NAMES := ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

@onready var title_label: Label = $Title
@onready var row_list: VBoxContainer = $Row/SquadCard/SquadBox/Scroll/RowList
@onready var name_label: Label = $Row/DetailCard/DetailBox/Name
@onready var meta_label: Label = $Row/DetailCard/DetailBox/Meta
@onready var focus_button: Button = $Row/DetailCard/DetailBox/FocusButton
@onready var intensity_button: Button = $Row/DetailCard/DetailBox/IntensityButton
@onready var days_button: Button = $Row/DetailCard/DetailBox/DaysButton
@onready var growth_box: VBoxContainer = $Row/DetailCard/DetailBox/GrowthBox
@onready var chips_row: HBoxContainer = $Row/DetailCard/DetailBox/ChipsRow
@onready var bulk_button: Button = $Row/DetailCard/DetailBox/BulkButton
@onready var day_button: Button = $Row/DetailCard/DetailBox/DayButton
@onready var month_button: Button = $Row/DetailCard/DetailBox/MonthButton
@onready var toast_label: Label = $Row/DetailCard/DetailBox/Toast

var players: Array = []
var assignments: Dictionary = {}
var selected_id: int = -1


func _ready() -> void:
	toast_label.add_theme_color_override("font_color", AppTheme.HEADER_GREEN)
	focus_button.pressed.connect(func(): _cycle(selected_id, "cycle_training_focus"))
	intensity_button.pressed.connect(func(): _cycle(selected_id, "cycle_training_intensity"))
	days_button.pressed.connect(func(): _cycle(selected_id, "cycle_training_days"))
	bulk_button.pressed.connect(_on_bulk_pressed)
	day_button.pressed.connect(_on_day_pressed)
	month_button.pressed.connect(_on_month_pressed)
	_style_buttons()
	refresh()


## v4.32.0: the three programme-cycle controls behave like mini dropdowns
## (they display a current value that a click steps on) — give them a card
## with a gold left edge instead of the default flat button, and style the
## two simulate actions as filled-accent primary buttons like every other
## screen's main action. All styleboxes are built here in code so the
## palette stays in AppTheme, not scattered across .tscn files.
func _style_buttons() -> void:
	for btn in [focus_button, intensity_button, days_button]:
		var box := StyleBoxFlat.new()
		box.bg_color = AppTheme.CARD
		box.set_corner_radius_all(8)
		box.set_border_width_all(1)
		box.border_color = AppTheme.GOLD
		box.border_width_left = 3
		box.content_margin_left = 12
		box.content_margin_right = 12
		box.content_margin_top = 6
		box.content_margin_bottom = 6
		btn.add_theme_stylebox_override("normal", box)
		var hover := box.duplicate()
		hover.bg_color = AppTheme.HOVER
		btn.add_theme_stylebox_override("hover", hover)
		var pressed := box.duplicate()
		pressed.bg_color = AppTheme.ACTIVE
		btn.add_theme_stylebox_override("pressed", pressed)
		btn.add_theme_font_size_override("font_size", 11)
		btn.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
		btn.add_theme_color_override("font_hover_color", AppTheme.TEXT_PRIMARY)
		btn.add_theme_color_override("font_pressed_color", AppTheme.GOLD)
	for btn in [bulk_button, day_button, month_button]:
		var box := StyleBoxFlat.new()
		box.bg_color = AppTheme.ACCENT
		box.set_corner_radius_all(8)
		box.content_margin_left = 12
		box.content_margin_right = 12
		box.content_margin_top = 6
		box.content_margin_bottom = 6
		btn.add_theme_stylebox_override("normal", box)
		var hover := box.duplicate()
		hover.bg_color = AppTheme.ACCENT.lightened(0.1)
		btn.add_theme_stylebox_override("hover", hover)
		btn.add_theme_color_override("font_color", AppTheme.CARD)
		btn.add_theme_color_override("font_hover_color", Color(1, 1, 1, 1))
		btn.add_theme_font_size_override("font_size", 11)


func refresh() -> void:
	var response := IpcBridge.call_method("get_training")
	if response.has("error"):
		title_label.text = "TRAINING — backend error: %s" % response["error"]
		push_error("TrainingScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	players = result.get("players", [])
	assignments = result.get("assignments", {})
	# v4.28.0: World Cup mode manages an already-assembled national squad
	# for one tournament — no player development, same "pick from who's
	# already good enough" logic Football Manager uses for international-
	# only saves. get_training returns an empty roster with this flag set.
	if bool(result.get("world_cup_mode", false)):
		title_label.text = "TRAINING — not available in World Cup mode"
		selected_id = -1
		_build_rows()
		# _refresh_detail() would overwrite these with its own no-selection
		# text ("—" / "No players") — set the real explanation after it.
		_refresh_detail()
		name_label.text = "No training in World Cup mode"
		meta_label.text = "You're managing an already-assembled national squad for one tournament — focus on team selection and match tactics instead."
		return
	title_label.text = "TRAINING — %d" % players.size()
	if selected_id == -1 or not players.any(func(p): return int(p["id"]) == selected_id):
		selected_id = int(players[0]["id"]) if not players.is_empty() else -1
	_build_rows()
	_refresh_detail()


func _assignment_for(player_id: int) -> Dictionary:
	return assignments.get(str(player_id), {"focus": "None", "progress": {}, "intensity": "Normal", "days": [0, 2, 4]})


func _build_rows() -> void:
	for child in row_list.get_children():
		row_list.remove_child(child)
		child.queue_free()
	_add_row(["NAME", "ROLE", "OVR", "POT", "PROGRAMME", "DAYS", "LOAD", "30D"], true, {})
	for i in range(players.size()):
		var player: Dictionary = players[i]
		var assignment := _assignment_for(int(player["id"]))
		var growth := 0.0
		for value in assignment.get("progress", {}).values():
			growth += float(value)
		var labels := ""
		for day in assignment.get("days", [0, 2, 4]):
			labels += DAY_LETTERS[int(day)]
		var values := [player.get("name", "—"), player.get("role", "—"), JsonFormat.value(player.get("overall", 0)),
			JsonFormat.value(player.get("potential", player.get("overall", 0))), assignment.get("focus", "None"),
			labels, assignment.get("intensity", "Normal"), "+%.2f" % growth]
		_add_row(values, false, player, i % 2 == 0)


func _add_row(values: Array, is_header: bool, player: Dictionary, alt: bool = false) -> void:
	var panel := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.content_margin_left = 12
	box.content_margin_right = 12
	box.content_margin_top = 5
	box.content_margin_bottom = 5
	if is_header:
		box.bg_color = AppTheme.ACTIVE
	elif int(player.get("id", -1)) == selected_id:
		box.bg_color = AppTheme.HOVER
		# v4.32.0: a gold edge marks the row currently being edited in the
		# detail card — the selected player stays obvious even after
		# scrolling the list, not just via a tint that's easy to miss.
		box.set_border_width_all(1)
		box.border_color = AppTheme.GOLD
		box.border_width_left = 3
	elif alt:
		box.bg_color = AppTheme.CARD
	else:
		box.bg_color = AppTheme.SURFACE
	panel.add_theme_stylebox_override("panel", box)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	var widths := [180, 130, 60, 60, 150, 90, 90, 70]
	for i in range(values.size()):
		var label := Label.new()
		label.text = str(values[i])
		label.custom_minimum_size = Vector2(widths[i] if i < widths.size() else 100, 0)
		# v4.32.0: clip keeps every column at its fixed width no matter how
		# long a name gets, so the table columns always line up.
		label.clip_text = true
		if is_header:
			label.add_theme_color_override("font_color", AppTheme.GOLD)
			label.add_theme_font_size_override("font_size", 12)
		else:
			# v4.32.0: colour the ROLE column by role and the OVR/POT
			# columns by their tier so the table is scannable at a glance.
			if i == 1:
				label.add_theme_color_override("font_color", AppTheme.role_colour(str(values[i])))
			elif i == 2 or i == 3:
				label.add_theme_color_override("font_color", AppTheme.attribute_colour(float(values[i])))
			else:
				label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
		row.add_child(label)
	if not is_header:
		row.mouse_filter = Control.MOUSE_FILTER_STOP
		row.gui_input.connect(_on_row_input.bind(int(player["id"])))
	panel.add_child(row)
	row_list.add_child(panel)


func _on_row_input(event: InputEvent, player_id: int) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		selected_id = player_id
		_build_rows()
		_refresh_detail()


func _refresh_detail() -> void:
	var player := players.filter(func(p): return int(p["id"]) == selected_id)
	if player.is_empty():
		name_label.text = "—"
		meta_label.text = "No players"
		_clear_chips()
		return
	var selected: Dictionary = player[0]
	var assignment := _assignment_for(selected_id)
	name_label.text = str(selected.get("name", "—"))
	# v4.32.0: OVR/POT moved out of the meta line into colour-coded chips
	# beside a role pill (like the reference FM-style chips row), freeing
	# the meta line for the last-touched date.
	meta_label.text = "Last trained: %s" % str(selected.get("last_trained", "—"))
	_clear_chips()
	chips_row.add_child(_role_pill(str(selected.get("role", "?"))))
	var overall := int(selected.get("overall", 0))
	var potential := int(selected.get("potential", overall))
	if overall > 0:
		chips_row.add_child(AppTheme.make_status_chip("OVR", overall))
	if potential > 0:
		chips_row.add_child(AppTheme.make_status_chip("POT", potential))
	focus_button.text = "PROGRAMME: %s" % str(assignment.get("focus", "None")).to_upper()
	intensity_button.text = "INTENSITY: %s" % str(assignment.get("intensity", "Normal")).to_upper()
	var day_text := []
	for day in assignment.get("days", [0, 2, 4]):
		day_text.append(DAY_NAMES[int(day)])
	days_button.text = "DAYS: %s" % " / ".join(day_text)

	for child in growth_box.get_children():
		growth_box.remove_child(child)
		child.queue_free()
	var progress: Dictionary = assignment.get("progress", {})
	for group in ["batting", "bowling", "fielding", "mental"]:
		var total := 0.0
		for key in progress:
			if str(key).begins_with(group):
				total += float(progress[key])
		var value: int = clampi(int(total * 20.0), 0, 100)
		growth_box.add_child(_growth_row("%s growth" % group.capitalize(), value))


func _clear_chips() -> void:
	for child in chips_row.get_children():
		chips_row.remove_child(child)
		child.queue_free()


## A small filled pill showing the player's role (v4.32.0) — uses the same
## role palette as everywhere else so the detail card ties into the rest
## of the app's colour language.
func _role_pill(role: String) -> PanelContainer:
	var pill := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.role_colour(role)
	box.set_corner_radius_all(8)
	box.set_border_width_all(0)
	box.content_margin_left = 10
	box.content_margin_right = 10
	box.content_margin_top = 4
	box.content_margin_bottom = 4
	pill.add_theme_stylebox_override("panel", box)
	var label := Label.new()
	label.text = role
	label.add_theme_font_size_override("font_size", 10)
	label.add_theme_color_override("font_color", AppTheme.CARD)
	pill.add_child(label)
	return pill


func _growth_row(label_text: String, value: int) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var label := Label.new()
	label.text = label_text
	label.custom_minimum_size = Vector2(110, 0)
	label.add_theme_font_size_override("font_size", 11)
	label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	row.add_child(label)
	# v4.32.0: reuse the shared bar meter (track + tier-coloured fill +
	# numeric readout) instead of the hand-rolled track here — one source
	# of truth for bar visuals, and the number makes progress legible.
	row.add_child(AppTheme.make_bar_meter(120.0, float(value), 11, AppTheme.attribute_colour(float(value))))
	return row


func _cycle(player_id: int, method_name: String) -> void:
	if player_id == -1:
		return
	var response := IpcBridge.call_method(method_name, {"player_id": player_id})
	if response.has("error"):
		toast_label.text = "Action failed: %s" % response["error"]
		push_error("TrainingScreen %s failed: %s" % [method_name, response["error"]])
		return
	var result: Dictionary = response["result"]
	players = result.get("players", [])
	assignments = result.get("assignments", {})
	_build_rows()
	_refresh_detail()


func _on_bulk_pressed() -> void:
	if selected_id == -1:
		return
	var response := IpcBridge.call_method("apply_training_to_all", {"player_id": selected_id})
	if response.has("error"):
		toast_label.text = "Action failed: %s" % response["error"]
		return
	var result: Dictionary = response["result"]
	players = result.get("players", [])
	assignments = result.get("assignments", {})
	_build_rows()
	_refresh_detail()
	toast_label.text = "Programme and weekly schedule applied to the full squad"


## Mirrors ui/training.py's day_button: fast-forwards to (and including)
## the next default global training day (Mon/Wed/Fri), not just +1 day, so
## a single click reliably produces visible training progress.
func _on_day_pressed() -> void:
	var response := IpcBridge.call_method("get_dashboard")
	var current_date := "2026-04-01"
	if not response.has("error"):
		current_date = str(response["result"].get("date", current_date))
	var weekday: int = int(Time.get_datetime_dict_from_datetime_string(current_date + "T00:00:00", true).get("weekday", 1))
	# Godot's weekday: 0=Sunday..6=Saturday; pygame's date.weekday(): 0=Monday..6=Sunday.
	var py_weekday: int = (weekday + 6) % 7
	var offset := 1
	while (py_weekday + offset) % 7 not in [0, 2, 4]:
		offset += 1
	_simulate(offset + 1)


func _on_month_pressed() -> void:
	_simulate(30)


func _simulate(days: int) -> void:
	var response := IpcBridge.call_method("simulate_training", {"days": days})
	if response.has("error"):
		toast_label.text = "Action failed: %s" % response["error"]
		return
	var result: Dictionary = response["result"]
	players = result.get("players", [])
	assignments = result.get("assignments", {})
	_build_rows()
	_refresh_detail()
	toast_label.text = "Training complete • %s attribute points gained" % JsonFormat.value(result.get("points_gained", 0))
