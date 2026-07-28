extends Control
## Ports src/views/screens/career_team_selection.py: club shortlist (already
## filtered server-side by get_selectable_teams to the chosen country) plus
## the same expectation() heuristic, then confirms via confirm_career_team.

@onready var list_box: VBoxContainer = $Row/ListCard/Box/Scroll/List
@onready var team_name_label: Label = $Row/DetailCard/Box/TeamName
@onready var stats_box: VBoxContainer = $Row/DetailCard/Box/Stats
@onready var expectation_title: Label = $Row/DetailCard/Box/ExpectationTitle
@onready var expectation_detail: Label = $Row/DetailCard/Box/ExpectationDetail
@onready var back_button: Button = $Footer/BackButton
@onready var confirm_button: Button = $Footer/ConfirmButton
@onready var message_label: Label = $Footer/Message

var _teams: Array = []
var _selected_id: int = -1
var _row_buttons: Dictionary = {}


static func _initials(name: String) -> String:
	var initials := ""
	for word in name.split(" ", false):
		if not word.is_empty():
			initials += word[0]
	return initials.substr(0, 2).to_upper()


func _ready() -> void:
	back_button.pressed.connect(func(): _shell().show_screen("New Game Setup"))
	confirm_button.pressed.connect(_on_confirm_pressed)
	_load_teams()


func _shell() -> Node:
	return get_tree().get_first_node_in_group("shell")


func _load_teams() -> void:
	var response := IpcBridge.call_method("get_selectable_teams")
	if response.has("error"):
		message_label.text = response["error"]
		return
	_teams = response["result"].get("teams", [])
	for child in list_box.get_children():
		list_box.remove_child(child)
		child.queue_free()
	_row_buttons.clear()
	for team in _teams:
		var button := Button.new()
		button.toggle_mode = true
		button.custom_minimum_size = Vector2(0, 44)
		var row := HBoxContainer.new()
		row.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.add_theme_constant_override("separation", 10)
		row.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		row.offset_left = 10
		row.offset_right = -10
		# Club crest badge (v0.87.0) -- the reference screenshots show a
		# club identity next to every row; this was previously a plain
		# text-only line, indistinguishable from a spreadsheet. Reuses
		# the same initials-badge pattern already used in shell.gd's
		# header and the Dashboard's fixture card, not a new asset.
		var crest := PanelContainer.new()
		crest.custom_minimum_size = Vector2(28, 28)
		crest.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		crest.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var crest_box := StyleBoxFlat.new()
		crest_box.bg_color = AppTheme.GOLD
		crest_box.set_corner_radius_all(14)
		crest.add_theme_stylebox_override("panel", crest_box)
		var crest_label := Label.new()
		crest_label.text = _initials(str(team.get("name", "?")))
		crest_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		crest_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		crest_label.add_theme_font_size_override("font_size", 11)
		crest_label.add_theme_color_override("font_color", AppTheme.BACKGROUND)
		crest_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		crest.add_child(crest_label)
		row.add_child(crest)
		var text_label := Label.new()
		text_label.text = "%s   Div %s   •   OVR %.1f   •   %s" % [
			team.get("name", "?"), JsonFormat.value(team.get("division", "?")),
			float(team.get("average_rating", 50)), str(team.get("cash_display", team.get("cash", 0)))]
		text_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		text_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.add_child(text_label)
		button.add_child(row)
		var team_id := int(team.get("id", 0))
		button.pressed.connect(_on_team_pressed.bind(team_id))
		list_box.add_child(button)
		_row_buttons[team_id] = button
	if not _teams.is_empty():
		_on_team_pressed(int(_teams[0].get("id", 0)))


func _on_team_pressed(team_id: int) -> void:
	_selected_id = team_id
	for id in _row_buttons:
		_row_buttons[id].set_pressed_no_signal(id == team_id)
	_render_detail(_selected_team())


func _selected_team() -> Dictionary:
	for team in _teams:
		if int(team.get("id", -1)) == _selected_id:
			return team
	return _teams[0] if not _teams.is_empty() else {}


func _render_detail(team: Dictionary) -> void:
	if team.is_empty():
		return
	team_name_label.text = str(team.get("name", "?"))
	for child in stats_box.get_children():
		stats_box.remove_child(child)
		child.queue_free()
	var stats := [
		["Starting cash", str(team.get("cash_display", team.get("cash", 0)))],
		["Squad size", JsonFormat.value(team.get("squad_size", "?"))],
		["Average rating", "%.1f" % float(team.get("average_rating", 50))],
		["Stadium", "%s seats" % JsonFormat.value(team.get("stadium_capacity", "?"))],
		["Training level", "Level %s" % JsonFormat.value(team.get("training_level", "?"))],
	]
	for pair in stats:
		var row := HBoxContainer.new()
		var label := Label.new()
		label.text = pair[0]
		label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		label.size_flags_horizontal = SIZE_EXPAND_FILL
		row.add_child(label)
		var value := Label.new()
		value.text = pair[1]
		row.add_child(value)
		stats_box.add_child(row)
	var expectation := _expectation(team)
	expectation_title.text = expectation[0]
	expectation_title.add_theme_color_override("font_color", AppTheme.GOLD)
	expectation_detail.text = expectation[1]


## Mirrors CareerTeamSelectionScreen.expectation() exactly.
func _expectation(team: Dictionary) -> Array:
	var rating: float = float(team.get("average_rating", 50))
	var division: int = int(team.get("division", 1))
	if division == 1 and rating >= 68:
		return ["TITLE CHALLENGE", "Compete for the championship and reach the cup semi-final."]
	if division == 1:
		return ["MID-TABLE", "Build sustainably and finish clear of relegation."]
	if rating >= 56:
		return ["PROMOTION PUSH", "Challenge for a top-two promotion position."]
	return ["DEVELOP & SURVIVE", "Avoid the bottom two while developing younger players."]


func _on_confirm_pressed() -> void:
	if _selected_id == -1:
		return
	var response := IpcBridge.call_method("confirm_career_team", {"team_id": _selected_id})
	if response.has("error"):
		message_label.text = response["error"]
		return
	_shell().refresh_header()
	_shell().show_screen(str(response["result"].get("destination", "Dashboard")))
