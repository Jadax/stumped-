extends Control

@onready var title_label: Label = $Title

@onready var squad_size_label: Label = $Grid/SquadCard/Box/Value
@onready var avg_overall_label: Label = $Grid/SquadCard/Box/Overall
@onready var avg_age_label: Label = $Grid/SquadCard/Box/Age
@onready var batting_avg_label: Label = $Grid/AttrsCard/Box/Batting/Value
@onready var bowling_avg_label: Label = $Grid/AttrsCard/Box/Bowling/Value
@onready var fielding_avg_label: Label = $Grid/AttrsCard/Box/Fielding/Value

@onready var cash_label: Label = $Grid/FinanceCard/Box/CashValue
@onready var wage_label: Label = $Grid/FinanceCard/Box/WageValue
@onready var position_label: Label = $Grid/PositionCard/Box/PositionValue
@onready var confidence_label: Label = $Grid/PositionCard/Box/ConfidenceValue
@onready var trophy_label: Label = $Grid/PositionCard/Box/TrophyValue

@onready var form_row: HBoxContainer = $Grid/FormCard/Box/FormRow
@onready var next_opponent_label: Label = $Grid/NextFixtureCard/Box/OpponentValue
@onready var next_detail_label: Label = $Grid/NextFixtureCard/Box/DetailValue
@onready var injuries_list: VBoxContainer = $Grid/InjuriesCard/Box/List


func _ready() -> void:
	_style_cards()
	refresh()


func _style_cards() -> void:
	for card in $Grid.get_children():
		if card is PanelContainer:
			card.add_theme_stylebox_override("panel", AppTheme.make_card(false))
	for label_path in ["Grid/SquadCard/Box/Header", "Grid/AttrsCard/Box/Header", "Grid/FinanceCard/Box/Header",
		"Grid/PositionCard/Box/Header", "Grid/FormCard/Box/Header", "Grid/NextFixtureCard/Box/Header",
		"Grid/InjuriesCard/Box/Header"]:
		var header := get_node_or_null(label_path)
		if header:
			header.add_theme_font_size_override("font_size", 11)
			header.add_theme_color_override("font_color", AppTheme.GOLD)
	for value_path in ["Grid/SquadCard/Box/Value", "Grid/FinanceCard/Box/CashValue", "Grid/PositionCard/Box/PositionValue"]:
		var value := get_node_or_null(value_path)
		if value:
			value.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)


func refresh() -> void:
	var response := IpcBridge.call_method("get_data_hub")
	if response.has("error"):
		title_label.text = "DATA HUB — backend error: %s" % response["error"]
		push_error("DataHubScreen: %s" % response["error"])
		return
	var d: Dictionary = response["result"]

	squad_size_label.text = str(d.get("squad_size", "—"))
	avg_overall_label.text = "AVG OVR %s" % str(d.get("avg_overall", "—"))
	avg_age_label.text = "AVG AGE %s" % str(d.get("avg_age", "—"))
	batting_avg_label.text = str(d.get("batting_avg", "—"))
	bowling_avg_label.text = str(d.get("bowling_avg", "—"))
	fielding_avg_label.text = str(d.get("fielding_avg", "—"))
	for pair in [[batting_avg_label, d.get("batting_avg", 0)], [bowling_avg_label, d.get("bowling_avg", 0)],
		[fielding_avg_label, d.get("fielding_avg", 0)]]:
		pair[0].add_theme_color_override("font_color", AppTheme.attribute_colour(float(pair[1])))

	cash_label.text = JsonFormat.value(d.get("cash", 0))
	wage_label.text = "WAGE BILL: %s/wk" % JsonFormat.value(d.get("wage_bill", 0))

	var pos = d.get("league_position")
	position_label.text = "League: %s" % (("#%d" % pos) if pos else "—")
	var conf = d.get("board_confidence", 50)
	var conf_str = d.get("board_label", "Stable")
	confidence_label.text = "Board: %s (%d)" % [conf_str, conf]
	trophy_label.text = "Trophies: %d" % d.get("trophy_count", 0)

	_render_form(d.get("recent_form", []))
	_render_next_fixture(d.get("next_fixture"))
	_render_injuries(d.get("injuries", []))

	title_label.text = "CLUB HUB"


## v4.25.0: Data Hub enrichment — recent results, next fixture, and
## current injuries were previously nowhere on this screen despite being
## exactly the "at a glance" info a real management sim overview shows.
func _render_form(recent_form: Array) -> void:
	for child in form_row.get_children():
		child.queue_free()
	if recent_form.is_empty():
		var empty := Label.new()
		empty.text = "No results yet this season."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		form_row.add_child(empty)
		return
	for result in recent_form:
		var chip := PanelContainer.new()
		var box := StyleBoxFlat.new()
		box.bg_color = AppTheme.HEADER_GREEN if result == "W" else AppTheme.DANGER if result == "L" else AppTheme.TEXT_MUTED
		box.set_corner_radius_all(6)
		box.content_margin_left = 10
		box.content_margin_right = 10
		box.content_margin_top = 4
		box.content_margin_bottom = 4
		chip.add_theme_stylebox_override("panel", box)
		var label := Label.new()
		label.text = str(result)
		label.add_theme_color_override("font_color", AppTheme.CARD)
		label.add_theme_font_size_override("font_size", 13)
		chip.add_child(label)
		form_row.add_child(chip)


func _render_next_fixture(fixture) -> void:
	if fixture == null:
		next_opponent_label.text = "No fixture scheduled"
		next_detail_label.text = ""
		return
	var venue: String = "Home" if fixture.get("home", false) else "Away"
	next_opponent_label.text = "vs %s" % str(fixture.get("opponent", "?"))
	next_detail_label.text = "%s — %s — %s" % [str(fixture.get("date", "?")), str(fixture.get("format", "?")), venue]


func _render_injuries(injuries: Array) -> void:
	for child in injuries_list.get_children():
		child.queue_free()
	if injuries.is_empty():
		var empty := Label.new()
		empty.text = "Full squad available."
		empty.add_theme_color_override("font_color", AppTheme.HEADER_GREEN)
		injuries_list.add_child(empty)
		return
	for injury in injuries:
		var label := Label.new()
		label.text = "%s — %s, back %s" % [str(injury.get("player_name", "?")),
			str(injury.get("severity", "?")), str(injury.get("return_date", "?"))]
		label.add_theme_font_size_override("font_size", 12)
		label.add_theme_color_override("font_color", AppTheme.DANGER)
		injuries_list.add_child(label)
