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
var _branding_panel: PanelContainer
var _branding_name: LineEdit
var _branding_crest: OptionButton
var _branding_status: Label


func _ready() -> void:
	back_button.pressed.connect(_on_back)
	standings_panel.visible = false
	_build_branding_editor()
	refresh()


func _build_branding_editor() -> void:
	var content := $StandingsPanel/Scroll/Content as VBoxContainer
	_branding_panel = PanelContainer.new()
	_branding_panel.name = "CompetitionBranding"
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	_branding_panel.add_child(box)
	var heading := Label.new()
	heading.text = "COMPETITION BRANDING"
	heading.add_theme_color_override("font_color", AppTheme.ACCENT)
	box.add_child(heading)
	var hint := Label.new()
	hint.text = "Presentation only — customise the short label and crest used by your competition."
	hint.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	box.add_child(hint)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	_branding_name = LineEdit.new()
	_branding_name.placeholder_text = "Short name (optional)"
	_branding_name.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_branding_name.custom_minimum_size = Vector2(220, 36)
	row.add_child(_branding_name)
	_branding_crest = OptionButton.new()
	for crest in ["Shield", "Circle", "Diamond", "Star", "Crest"]:
		_branding_crest.add_item(crest)
	_branding_crest.custom_minimum_size = Vector2(120, 36)
	row.add_child(_branding_crest)
	for preset in [{"label":"GREEN", "value":"#3fb950"}, {"label":"GOLD", "value":"#d29922"}, {"label":"BLUE", "value":"#58a6ff"}, {"label":"PURPLE", "value":"#bc8cff"}]:
		var colour_button := Button.new()
		colour_button.text = preset.label
		colour_button.custom_minimum_size = Vector2(78, 36)
		colour_button.pressed.connect(_on_brand_colour.bind(preset.value))
		row.add_child(colour_button)
	var save := Button.new()
	save.text = "SAVE BRANDING"
	save.custom_minimum_size = Vector2(150, 36)
	save.pressed.connect(_on_save_branding)
	row.add_child(save)
	box.add_child(row)
	_branding_status = Label.new()
	_branding_status.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	box.add_child(_branding_status)
	content.add_child(_branding_panel)
	_branding_panel.visible = false


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
	_branding_panel.visible = true
	_load_branding()
	_render_standings()


func _load_branding() -> void:
	var response := IpcBridge.call_method("get_competition_branding", {"competition_id": int(_selected_competition.get("id", 0))})
	if response.has("error"):
		_branding_status.text = "Branding unavailable: %s" % response["error"]
		return
	var branding: Dictionary = response["result"]
	_branding_name.text = str(branding.get("short_name", ""))
	var crest := str(branding.get("crest", "shield")).capitalize()
	_branding_crest.selected = max(0, ["Shield", "Circle", "Diamond", "Star", "Crest"].find(crest))
	_branding_status.text = "Saved for %s" % str(_selected_competition.get("name", "competition"))


func _on_brand_colour(value: String) -> void:
	_branding_status.text = "Accent selected: %s — press SAVE BRANDING" % value
	_branding_status.set_meta("accent", value)


func _on_save_branding() -> void:
	var accents := str(_branding_status.get_meta("accent", "#3fb950"))
	var crests := ["shield", "circle", "diamond", "star", "crest"]
	var response := IpcBridge.call_method("set_competition_branding", {
		"competition_id": int(_selected_competition.get("id", 0)),
		"branding": {"short_name": _branding_name.text.strip_edges(), "accent": accents, "crest": crests[_branding_crest.selected]}
	})
	if response.has("error"):
		_branding_status.text = "Save failed: %s" % response["error"]
	else:
		_branding_status.text = "Branding saved"


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
