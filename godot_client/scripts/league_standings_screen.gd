extends Control
## New in v4.53.0 (concept-screen recreation, part 7/7): a real dedicated
## League Standings screen — reference: the County Championship table
## screenshot's full P/W/L/D/Bat/Bwl/Pts columns with a promotion/
## relegation divider line, Division 1/2 tab switch. Previously the only
## standings view anywhere was dashboard_screen.gd's top-6 Division-1-only
## crop. Backed by ipc_server.py's new get_division_standings (division 1
## and 2 use the same 2-up/2-down promotion rule as
## CompetitionEngine.rollover_season).

@onready var title_label: Label = $Title
@onready var content: VBoxContainer = $Scroll/Content
@onready var division_tabs: HBoxContainer = $DivisionTabs

const PROMOTE_RELEGATE_COUNT := 2

var _division: int = 1


func _ready() -> void:
	for tab in division_tabs.get_children():
		if tab is Button:
			tab.pressed.connect(_on_division_tab_pressed.bind(tab))
	refresh()


func _on_division_tab_pressed(tab: Button) -> void:
	_division = 1 if tab.name == "Division1" else 2
	for other in division_tabs.get_children():
		if other is Button:
			other.set_pressed_no_signal(other == tab)
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_division_standings", {"division": _division})
	if response.has("error"):
		title_label.text = "LEAGUE STANDINGS — backend error: %s" % response["error"]
		push_error("LeagueStandingsScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	title_label.text = str(result.get("league_name", "LEAGUE STANDINGS")).to_upper()
	_render(result.get("standings", []))


func _render(standings: Array) -> void:
	for child in content.get_children():
		content.remove_child(child)
		child.queue_free()
	if standings.is_empty():
		var empty := Label.new()
		empty.text = "No matches played yet this season."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		content.add_child(empty)
		return
	content.add_child(_header_row())
	# Division 1 is the top of the pyramid (no promotion above it);
	# Division 2 can both promote (up) and relegate (down) — matches
	# CompetitionEngine.rollover_season's 2-up/2-down rule.
	var can_promote: bool = _division > 1
	var can_relegate: bool = true
	for index in range(standings.size()):
		content.add_child(_standings_row(standings[index], index))
		if can_promote and index == PROMOTE_RELEGATE_COUNT - 1 and index < standings.size() - 1:
			content.add_child(_divider(AppTheme.HEADER_GREEN))
		if can_relegate and index == standings.size() - PROMOTE_RELEGATE_COUNT - 1 and index >= PROMOTE_RELEGATE_COUNT:
			content.add_child(_divider(AppTheme.DANGER))


func _divider(colour: Color) -> ColorRect:
	var line := ColorRect.new()
	line.color = colour
	line.custom_minimum_size = Vector2(0, 2)
	return line


const COLUMNS := [["#", 28, HORIZONTAL_ALIGNMENT_LEFT], ["TEAM", 190, HORIZONTAL_ALIGNMENT_LEFT],
	["P", 36, HORIZONTAL_ALIGNMENT_RIGHT], ["W", 36, HORIZONTAL_ALIGNMENT_RIGHT],
	["L", 36, HORIZONTAL_ALIGNMENT_RIGHT], ["D", 36, HORIZONTAL_ALIGNMENT_RIGHT],
	["T", 36, HORIZONTAL_ALIGNMENT_RIGHT], ["BAT", 44, HORIZONTAL_ALIGNMENT_RIGHT],
	["BWL", 44, HORIZONTAL_ALIGNMENT_RIGHT], ["PTS", 48, HORIZONTAL_ALIGNMENT_RIGHT],
	["NRR", 56, HORIZONTAL_ALIGNMENT_RIGHT]]


func _header_row() -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	for column in COLUMNS:
		var label := Label.new()
		label.text = str(column[0])
		label.custom_minimum_size = Vector2(column[1], 0)
		label.horizontal_alignment = column[2]
		label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		label.add_theme_font_size_override("font_size", 11)
		row.add_child(label)
	return row


func _standings_row(row_data: Dictionary, index: int) -> PanelContainer:
	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = AppTheme.ROW_ALT if index % 2 else AppTheme.CARD
	style.set_corner_radius_all(4)
	style.content_margin_left = 6
	style.content_margin_right = 6
	style.content_margin_top = 5
	style.content_margin_bottom = 5
	panel.add_theme_stylebox_override("panel", style)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	var values := [str(row_data.get("position", index + 1)), str(row_data.get("name", "?")),
		JsonFormat.value(row_data.get("played", 0)), JsonFormat.value(row_data.get("won", 0)),
		JsonFormat.value(row_data.get("lost", 0)), JsonFormat.value(row_data.get("drawn", 0)),
		JsonFormat.value(row_data.get("tied", 0)), JsonFormat.value(row_data.get("bat_bonus", 0)),
		JsonFormat.value(row_data.get("bowl_bonus", 0)), JsonFormat.value(row_data.get("points", 0)),
		JsonFormat.value(row_data.get("net_run_rate", 0.0))]
	for i in range(COLUMNS.size()):
		var label := Label.new()
		label.text = values[i]
		label.custom_minimum_size = Vector2(COLUMNS[i][1], 0)
		label.horizontal_alignment = COLUMNS[i][2]
		label.clip_text = true
		var is_points: bool = str(COLUMNS[i][0]) == "PTS"
		label.add_theme_color_override("font_color", AppTheme.GOLD if is_points else AppTheme.TEXT_PRIMARY)
		label.add_theme_font_size_override("font_size", 12)
		row.add_child(label)
	panel.add_child(row)
	return panel
