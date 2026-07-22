extends Control
## Youth Academy's real interactivity — ports ui/youth.py's split-view UI
## (squad table + side panel with collective training focus, targeted
## scouting role, and a paid recruitment trial), a genuine gap found
## during the same "read-only port missed the interactive parts" audit
## that caught Training. Not a table_screen.gd fit for the same reason
## Training wasn't: a table + action side-panel layout.

const PROFILE_MODAL_SCENE := preload("res://scenes/player_profile_modal.tscn")
const FOCUSES := ["Balanced", "Batting", "Bowling", "Fielding"]
const ROLE_FOCUSES := ["Any", "Batsman", "Pace Bowler", "Spin Bowler", "All-Rounder", "Wicketkeeper"]

@onready var title_label: Label = $Title
@onready var row_list: VBoxContainer = $Row/SquadCard/SquadBox/Scroll/RowList
@onready var squad_header: Label = $Row/SquadCard/SquadBox/Header
@onready var focus_button: Button = $Row/SideCard/SideBox/FocusButton
@onready var scout_role_button: Button = $Row/SideCard/SideBox/ScoutRoleButton
@onready var recruit_button: Button = $Row/SideCard/SideBox/RecruitButton
@onready var pipeline_box: VBoxContainer = $Row/SideCard/SideBox/PipelineBox
@onready var toast_label: Label = $Row/SideCard/SideBox/Toast

var players: Array = []
var focus_index: int = 0
var scout_role_index: int = 0
var _profile_modal: PlayerProfileModal = null


func _ready() -> void:
	toast_label.add_theme_color_override("font_color", AppTheme.HEADER_GREEN)
	_profile_modal = PROFILE_MODAL_SCENE.instantiate()
	add_child(_profile_modal)
	focus_button.pressed.connect(_on_focus_pressed)
	scout_role_button.pressed.connect(_on_scout_role_pressed)
	recruit_button.pressed.connect(_on_recruit_pressed)
	_update_scout_role_label()
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_youth_academy")
	if response.has("error"):
		title_label.text = "YOUTH ACADEMY — backend error: %s" % response["error"]
		push_error("YouthAcademyScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	players = result.get("players", [])
	if result.has("focus"):
		focus_index = FOCUSES.find(str(result["focus"]))
		if focus_index == -1:
			focus_index = 0
	title_label.text = "YOUTH ACADEMY — %d" % players.size()
	squad_header.text = "UNDER-20 SQUAD — %d PROSPECTS" % players.size()
	focus_button.text = "FOCUS: %s" % FOCUSES[focus_index].to_upper()
	recruit_button.text = "RECRUIT YOUTH • %s" % str(result.get("recruitment_fee_display", ""))
	_build_rows()
	_build_pipeline()


func _build_rows() -> void:
	for child in row_list.get_children():
		row_list.remove_child(child)
		child.queue_free()
	_add_row(["PROSPECT", "AGE", "ROLE", "BAT", "BOWL", "FIELD", "OVR", "POT"], true, {})
	for i in range(players.size()):
		var player: Dictionary = players[i]
		var values := [player.get("name", "—"), JsonFormat.value(player.get("age", 0)), player.get("role", "—"),
			JsonFormat.value(player.get("batting_avg", 0)), JsonFormat.value(player.get("bowling_avg", 0)),
			JsonFormat.value(player.get("fielding_avg", 0)), JsonFormat.value(player.get("overall", 0)),
			JsonFormat.value(player.get("potential", player.get("overall", 0)))]
		_add_row(values, false, player, i % 2 == 0)


func _add_row(values: Array, is_header: bool, player: Dictionary, alt: bool = false) -> void:
	var panel := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.content_margin_left = 12
	box.content_margin_right = 12
	box.content_margin_top = 5
	box.content_margin_bottom = 5
	box.bg_color = AppTheme.ACTIVE if is_header else (AppTheme.CARD if alt else AppTheme.SURFACE)
	panel.add_theme_stylebox_override("panel", box)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	var widths := [200, 60, 150, 70, 70, 70, 60, 60]
	for i in range(values.size()):
		var label := Label.new()
		label.text = str(values[i])
		label.custom_minimum_size = Vector2(widths[i] if i < widths.size() else 100, 0)
		if is_header:
			label.add_theme_color_override("font_color", AppTheme.GOLD)
			label.add_theme_font_size_override("font_size", 12)
		else:
			label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
		row.add_child(label)
	if not is_header:
		row.mouse_filter = Control.MOUSE_FILTER_STOP
		row.gui_input.connect(_on_row_input.bind(player))
	panel.add_child(row)
	row_list.add_child(panel)


func _on_row_input(event: InputEvent, player: Dictionary) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_profile_modal.show_for(player)


## Mirrors ui/youth.py's DEVELOPMENT PIPELINE breakdown: elite/first-team/
## long-term prospect counts by potential band, purely informational.
func _build_pipeline() -> void:
	for child in pipeline_box.get_children():
		pipeline_box.remove_child(child)
		child.queue_free()
	var elite := 0
	var first_team := 0
	var long_term := 0
	for player in players:
		var potential := int(player.get("potential", player.get("overall", 50)))
		if potential >= 80:
			elite += 1
		elif potential >= 65:
			first_team += 1
		else:
			long_term += 1
	var bands := [["Elite potential (80+)", elite, AppTheme.GOLD], ["First-team potential (65+)", first_team, AppTheme.HEADER_GREEN],
		["Long-term projects", long_term, AppTheme.TEXT_PRIMARY]]
	for band in bands:
		var row := HBoxContainer.new()
		var label := Label.new()
		label.text = band[0]
		label.custom_minimum_size = Vector2(210, 0)
		label.add_theme_font_size_override("font_size", 11)
		label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
		row.add_child(label)
		var value_label := Label.new()
		value_label.text = str(band[1])
		value_label.add_theme_font_size_override("font_size", 12)
		value_label.add_theme_color_override("font_color", band[2])
		row.add_child(value_label)
		pipeline_box.add_child(row)


func _on_focus_pressed() -> void:
	focus_index = (focus_index + 1) % FOCUSES.size()
	var response := IpcBridge.call_method("set_academy_focus", {"focus": FOCUSES[focus_index]})
	if response.has("error"):
		toast_label.text = "Action failed: %s" % response["error"]
		push_error("YouthAcademyScreen set_academy_focus failed: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	players = result.get("players", [])
	focus_button.text = "FOCUS: %s" % FOCUSES[focus_index].to_upper()
	_build_rows()
	_build_pipeline()
	toast_label.text = "Academy focus changed to %s" % FOCUSES[focus_index]


func _on_scout_role_pressed() -> void:
	scout_role_index = (scout_role_index + 1) % ROLE_FOCUSES.size()
	_update_scout_role_label()


func _update_scout_role_label() -> void:
	scout_role_button.text = "SCOUT FOR: %s" % ROLE_FOCUSES[scout_role_index].to_upper()


func _on_recruit_pressed() -> void:
	var role_focus: String = ROLE_FOCUSES[scout_role_index]
	var response := IpcBridge.call_method("recruit_youth_prospects", {"role_focus": role_focus})
	if response.has("error"):
		toast_label.text = "Action failed: %s" % response["error"]
		push_error("YouthAcademyScreen recruit_youth_prospects failed: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	players = result.get("players", [])
	title_label.text = "YOUTH ACADEMY — %d" % players.size()
	squad_header.text = "UNDER-20 SQUAD — %d PROSPECTS" % players.size()
	_build_rows()
	_build_pipeline()
	var created: int = int(result.get("created_count", 0))
	var focus_note := "" if role_focus == "Any" else " (%ss)" % role_focus.to_lower()
	toast_label.text = "Recruited %d new prospects%s" % [created, focus_note]
