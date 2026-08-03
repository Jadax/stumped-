extends Control
## Competition editor screen — view competitions, standings, and matches.

@onready var title_label: Label = $Title
@onready var competition_list: VBoxContainer = $Scroll/Competitions
@onready var standings_list: VBoxContainer = $StandingsPanel/Scroll/Content/Standings
@onready var matches_list: VBoxContainer = $StandingsPanel/Scroll/Content/Matches
@onready var standings_panel: PanelContainer = $StandingsPanel
@onready var back_button: Button = $Footer/BackButton

var _competitions: Array = []
var _selected_competition: Dictionary = {}


func _ready() -> void:
	back_button.pressed.connect(_on_back)
	standings_panel.visible = false
	refresh()


func _on_back() -> void:
	if standings_panel.visible:
		standings_panel.visible = false
		return
	var shell := get_tree().get_first_node_in_group("shell")
	if shell:
		shell.show_screen("Club")


func refresh() -> void:
	var response := IpcBridge.call_method("get_competitions")
	if response.has("error"):
		title_label.text = "COMPETITIONS — error: %s" % response["error"]
		return
	_competitions = response["result"]
	title_label.text = "COMPETITIONS — %d" % _competitions.size()
	_render_competition_list()


func _render_competition_list() -> void:
	for child in competition_list.get_children():
		competition_list.remove_child(child)
		child.queue_free()
	for comp in _competitions:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		var name_label := Label.new()
		name_label.text = str(comp.get("name", "?"))
		name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(name_label)
		var type_label := Label.new()
		type_label.text = str(comp.get("type", "?"))
		type_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		row.add_child(type_label)
		var view_button := Button.new()
		view_button.text = "VIEW"
		view_button.custom_minimum_size = Vector2(60, 28)
		view_button.pressed.connect(_on_view_pressed.bind(comp))
		row.add_child(view_button)
		competition_list.add_child(row)


func _on_view_pressed(comp: Dictionary) -> void:
	_selected_competition = comp
	standings_panel.visible = true
	_render_standings()


func _render_standings() -> void:
	for child in standings_list.get_children():
		standings_list.remove_child(child)
		child.queue_free()
	for child in matches_list.get_children():
		matches_list.remove_child(child)
		child.queue_free()
	var comp_id: int = int(_selected_competition.get("id", 0))
	# Get standings
	var standings_response := IpcBridge.call_method("get_competition_standings", {"competition_id": comp_id})
	if not standings_response.has("error"):
		var standings: Array = standings_response["result"]
		for i in range(min(standings.size(), 10)):
			var row: Dictionary = standings[i]
			var line := HBoxContainer.new()
			line.add_theme_constant_override("separation", 8)
			var pos_label := Label.new()
			pos_label.text = "#%d" % (i + 1)
			pos_label.custom_minimum_size = Vector2(30, 0)
			pos_label.add_theme_color_override("font_color", AppTheme.GOLD)
			line.add_child(pos_label)
			var name_label := Label.new()
			name_label.text = str(row.get("team_name", "?"))
			name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			line.add_child(name_label)
			var pts_label := Label.new()
			pts_label.text = "%d pts" % int(row.get("points", 0))
			line.add_child(pts_label)
			standings_list.add_child(line)
	# Get matches
	var matches_response := IpcBridge.call_method("get_competition_matches", {"competition_id": comp_id})
	if not matches_response.has("error"):
		var matches: Array = matches_response["result"]
		for match in matches.slice(0, 5):
			var line := HBoxContainer.new()
			line.add_theme_constant_override("separation", 8)
			var date_label := Label.new()
			var date_str: String = str(match.get("date", "?"))
			date_label.text = date_str.substr(0, 10) if date_str.length() > 10 else date_str
			date_label.custom_minimum_size = Vector2(80, 0)
			line.add_child(date_label)
			var teams_label := Label.new()
			teams_label.text = "%s vs %s" % [str(match.get("home_name", "?")), str(match.get("away_name", "?"))]
			teams_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			line.add_child(teams_label)
			var result_label := Label.new()
			var result_str: String = str(match.get("result", ""))
			result_label.text = result_str.substr(0, 20) if result_str.length() > 20 else result_str
			result_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
			line.add_child(result_label)
			matches_list.add_child(line)
