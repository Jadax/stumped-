extends Control
## National team management screen — accept jobs, view squad, resign.

@onready var title_label: Label = $Title
@onready var status_label: Label = $Status
@onready var teams_list: VBoxContainer = $Scroll/Teams
@onready var squad_list: VBoxContainer = $SquadPanel/Scroll/Content/SquadRow/Squad
@onready var xi_list: VBoxContainer = $SquadPanel/Scroll/Content/SquadRow/XI
@onready var fixtures_list: VBoxContainer = $SquadPanel/Scroll/Content/Fixtures
@onready var accept_button: Button = $Footer/AcceptButton
@onready var resign_button: Button = $Footer/ResignButton
@onready var back_button: Button = $Footer/BackButton

var _current_team: Dictionary = {}
var _selected_nationality: String = ""

## English/Australian/etc. -> "England"/"Australia"/etc., mirrors
## src.models.international.NATIONAL_TEAM_NAMES — duplicated here (small,
## static) rather than round-tripping an IPC call just for display labels.
const NATIONALITY_TEAM_NAMES := {"English": "England", "Australian": "Australia", "Indian": "India",
	"Pakistani": "Pakistan", "South African": "South Africa", "New Zealander": "New Zealand",
	"West Indian": "West Indies", "Sri Lankan": "Sri Lanka", "Bangladeshi": "Bangladesh",
	"Zimbabwean": "Zimbabwe"}


func _ready() -> void:
	accept_button.pressed.connect(_on_accept)
	resign_button.pressed.connect(_on_resign)
	back_button.pressed.connect(_on_back)
	refresh()


func _on_back() -> void:
	var shell := get_tree().get_first_node_in_group("shell")
	if shell:
		shell.show_screen("Dashboard")


func refresh() -> void:
	var response := IpcBridge.call_method("get_national_team")
	if response.has("error"):
		title_label.text = "NATIONAL TEAM — error: %s" % response["error"]
		return
	_current_team = response["result"]
	_render_ui()


func _render_ui() -> void:
	for child in teams_list.get_children():
		teams_list.remove_child(child)
		child.queue_free()
	for child in squad_list.get_children():
		squad_list.remove_child(child)
		child.queue_free()
	for child in xi_list.get_children():
		xi_list.remove_child(child)
		child.queue_free()
	for child in fixtures_list.get_children():
		fixtures_list.remove_child(child)
		child.queue_free()
	if _current_team.get("managing"):
		title_label.text = "NATIONAL TEAM — %s" % _current_team.get("team_name", "?")
		status_label.text = "You are managing %s" % _current_team.get("team_name", "?")
		accept_button.visible = false
		resign_button.visible = true
		_render_squad()
		_render_fixtures()
	else:
		title_label.text = "NATIONAL TEAM"
		status_label.text = "Select a national team to manage"
		accept_button.visible = false
		resign_button.visible = false
		_render_available_teams()


func _render_available_teams() -> void:
	for nat in NATIONALITY_TEAM_NAMES.keys():
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		var label := Label.new()
		label.text = NATIONALITY_TEAM_NAMES.get(nat, nat)
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(label)
		var button := Button.new()
		button.text = "APPLY"
		button.custom_minimum_size = Vector2(80, 28)
		button.pressed.connect(_on_team_selected.bind(nat))
		row.add_child(button)
		teams_list.add_child(row)


func _on_team_selected(nationality: String) -> void:
	_selected_nationality = nationality
	accept_button.visible = true
	accept_button.text = "ACCEPT %s JOB" % nationality.to_upper()
	status_label.text = "Selected: %s — click Accept to take the job" % nationality


func _render_squad() -> void:
	var xi_ids := {}
	for p in _current_team.get("xi", []):
		xi_ids[p["id"]] = true
	var squad: Array = _current_team.get("squad", [])
	for p in squad:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		var badge := Label.new()
		badge.text = "XI" if xi_ids.get(p["id"], false) else ""
		badge.custom_minimum_size = Vector2(24, 0)
		badge.add_theme_color_override("font_color", AppTheme.GOLD if xi_ids.get(p["id"], false) else AppTheme.TEXT_MUTED)
		row.add_child(badge)
		var name := Label.new()
		name.text = p.get("name", "?")
		name.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(name)
		var role := Label.new()
		role.text = p.get("role", "?")
		role.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		row.add_child(role)
		var ovr := Label.new()
		ovr.text = str(p.get("overall", 0))
		ovr.add_theme_color_override("font_color", AppTheme.GOLD)
		row.add_child(ovr)
		squad_list.add_child(row)
	var xi: Array = _current_team.get("xi", [])
	for p in xi:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		var name := Label.new()
		name.text = p.get("name", "?")
		name.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(name)
		var role := Label.new()
		role.text = p.get("role", "?")
		role.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		row.add_child(role)
		var ovr := Label.new()
		ovr.text = str(p.get("overall", 0))
		ovr.add_theme_color_override("font_color", AppTheme.GOLD)
		row.add_child(ovr)
		xi_list.add_child(row)


## Backed by database.py's get_national_fixtures (v4.12.0: broadened to
## include completed matches, not just upcoming ones, so a real results
## history can render here — previously this list would always be empty
## in practice since no international fixture was ever persisted before
## the v4.10.0-v4.12.0 tournament rebuild).
func _render_fixtures() -> void:
	var response := IpcBridge.call_method("get_international_fixtures")
	if response.has("error"):
		return
	var fixtures: Array = response.get("result", [])
	if fixtures.is_empty():
		var empty := Label.new()
		empty.text = "No international fixtures this season yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		fixtures_list.add_child(empty)
		return
	for fixture in fixtures:
		fixtures_list.add_child(_fixture_row(fixture))


func _fixture_row(fixture: Dictionary) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var date_label := Label.new()
	date_label.text = str(fixture.get("date", "?"))
	date_label.custom_minimum_size = Vector2(90, 0)
	date_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	row.add_child(date_label)
	var comp_label := Label.new()
	comp_label.text = str(fixture.get("round_name", fixture.get("competition_name", "")))
	comp_label.custom_minimum_size = Vector2(120, 0)
	comp_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	row.add_child(comp_label)
	var matchup := Label.new()
	matchup.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var completed: bool = bool(fixture.get("completed", false))
	if completed:
		matchup.text = "%s %s-%s vs %s %s-%s" % [
			str(fixture.get("home_name", "?")), JsonFormat.value(fixture.get("home_runs")), JsonFormat.value(fixture.get("home_wickets")),
			str(fixture.get("away_name", "?")), JsonFormat.value(fixture.get("away_runs")), JsonFormat.value(fixture.get("away_wickets"))]
	else:
		matchup.text = "%s vs %s (%s)" % [str(fixture.get("home_name", "?")), str(fixture.get("away_name", "?")),
			str(fixture.get("format", "?"))]
		matchup.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	row.add_child(matchup)
	return row


func _on_accept() -> void:
	if _selected_nationality.is_empty():
		return
	var response := IpcBridge.call_method("accept_national_job", {"nationality": _selected_nationality})
	if response.has("error"):
		status_label.text = "Error: %s" % response["error"]
		return
	_selected_nationality = ""
	refresh()


func _on_resign() -> void:
	var response := IpcBridge.call_method("resign_national_job")
	if response.has("error"):
		status_label.text = "Error: %s" % response["error"]
		return
	refresh()
