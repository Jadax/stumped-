extends Control
## New in v4.12.0 (Part 3 of the international tournament rebuild,
## v4.10.0-v4.12.0): shows whichever international competition thread is
## most recent — a bilateral tour's flat match list, an ICC tournament's
## live group-stage standings, or its knockout bracket — backed by
## database.py's get_current_international_competition. Before this,
## World Cup/Champions Trophy/tour progression was only ever visible via
## one-off inbox messages, with no way to see the table or bracket in-app.
## The knockout rendering (_match_card/_team_row) mirrors
## tournament_bracket_screen.gd's pattern (same response shape for that
## case: bracket/rounds/status/season) rather than inventing a second
## bracket visual style.

@onready var title_label: Label = $Title
@onready var content: VBoxContainer = $Scroll/Content
@onready var scroll: ScrollContainer = $Scroll

const CARD_WIDTH := 220.0


func _ready() -> void:
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_current_international_competition")
	if response.has("error"):
		title_label.text = "WORLD CUP — backend error: %s" % response["error"]
		push_error("InternationalScreen: %s" % response["error"])
		return
	_render(response.get("result", {}))


func _clear(container: Control) -> void:
	for child in container.get_children():
		container.remove_child(child)
		child.queue_free()


func _render(result: Dictionary) -> void:
	_clear(content)
	var kind: String = str(result.get("kind", "none"))
	match kind:
		"none":
			title_label.text = "WORLD CUP"
			var empty := Label.new()
			empty.text = "No international tour or tournament has started yet this season."
			empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
			content.add_child(empty)
		"tour":
			title_label.text = "%s — %s" % [str(result.get("name", "?")), JsonFormat.value(result.get("season"))]
			_render_match_list(result.get("matches", []))
		"tournament_group":
			title_label.text = "%s — %s, group stage" % [str(result.get("name", "?")), JsonFormat.value(result.get("season"))]
			_render_groups(result.get("groups", {}))
		"tournament_knockout":
			var status: String = str(result.get("status", "in_progress"))
			var suffix := " — complete" if status == "complete" else ""
			title_label.text = "%s — %s%s" % [str(result.get("name", "?")), JsonFormat.value(result.get("season")), suffix]
			_render_bracket(result.get("bracket", {}), result.get("rounds", []))


func _render_match_list(matches: Array) -> void:
	for match in matches:
		content.add_child(_match_row(match))


func _match_row(match: Dictionary) -> PanelContainer:
	var card := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.CARD
	box.set_corner_radius_all(8)
	box.content_margin_left = 12
	box.content_margin_right = 12
	box.content_margin_top = 8
	box.content_margin_bottom = 8
	card.add_theme_stylebox_override("panel", box)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	var round_label := Label.new()
	round_label.text = str(match.get("round_name", "?"))
	round_label.custom_minimum_size = Vector2(110, 0)
	round_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	row.add_child(round_label)
	var winner: Variant = match.get("winner")
	var summary := Label.new()
	summary.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	if bool(match.get("completed", false)):
		var home_win: bool = winner != null and str(winner) == str(match.get("home", "?"))
		var away_win: bool = winner != null and str(winner) == str(match.get("away", "?"))
		summary.text = "%s %s  vs  %s %s" % [str(match.get("home", "?")), JsonFormat.value(match.get("home_runs")),
			str(match.get("away", "?")), JsonFormat.value(match.get("away_runs"))]
		summary.add_theme_color_override("font_color", AppTheme.GOLD if (home_win or away_win) else AppTheme.TEXT_PRIMARY)
	else:
		summary.text = "%s vs %s" % [str(match.get("home", "?")), str(match.get("away", "?"))]
		summary.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	row.add_child(summary)
	card.add_child(row)
	return card


func _render_groups(groups: Dictionary) -> void:
	for label in groups.keys():
		var group: Dictionary = groups[label]
		var header := Label.new()
		header.text = str(label).to_upper()
		header.add_theme_color_override("font_color", AppTheme.GOLD)
		header.add_theme_font_size_override("font_size", 15)
		content.add_child(header)
		content.add_child(_standings_table(group.get("standings", [])))
		for match in group.get("matches", []):
			content.add_child(_match_row(match))


func _standings_table(standings: Array) -> VBoxContainer:
	var table := VBoxContainer.new()
	table.add_theme_constant_override("separation", 2)
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 12)
	for text in ["TEAM", "PLD", "PTS", "NRR"]:
		var h := Label.new()
		h.text = text
		h.custom_minimum_size = Vector2(70, 0) if text != "TEAM" else Vector2(160, 0)
		h.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		h.add_theme_font_size_override("font_size", 11)
		header.add_child(h)
	table.add_child(header)
	for row_data in standings:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		var name := Label.new()
		name.text = str(row_data.get("team", "?"))
		name.custom_minimum_size = Vector2(160, 0)
		row.add_child(name)
		var played := Label.new()
		played.text = str(row_data.get("played", 0))
		played.custom_minimum_size = Vector2(70, 0)
		row.add_child(played)
		var points := Label.new()
		points.text = str(row_data.get("points", 0))
		points.custom_minimum_size = Vector2(70, 0)
		points.add_theme_color_override("font_color", AppTheme.GOLD)
		row.add_child(points)
		var nrr := Label.new()
		nrr.text = str(row_data.get("net_run_rate", 0.0))
		nrr.custom_minimum_size = Vector2(70, 0)
		row.add_child(nrr)
		table.add_child(row)
	return table


func _render_bracket(bracket: Dictionary, rounds: Array) -> void:
	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 20)
	if rounds.is_empty():
		var empty := Label.new()
		empty.text = "The knockout draw hasn't been made yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		content.add_child(empty)
		return
	for round_name in rounds:
		var column := VBoxContainer.new()
		column.custom_minimum_size = Vector2(CARD_WIDTH, 0)
		column.add_theme_constant_override("separation", 14)
		var header := Label.new()
		header.text = str(round_name).to_upper()
		header.add_theme_color_override("font_color", AppTheme.GOLD)
		header.add_theme_font_size_override("font_size", 13)
		column.add_child(header)
		for match in bracket.get(round_name, []):
			column.add_child(_bracket_match_card(match))
		columns.add_child(column)
	content.add_child(columns)


func _bracket_match_card(match: Dictionary) -> PanelContainer:
	var card := PanelContainer.new()
	card.custom_minimum_size = Vector2(CARD_WIDTH, 0)
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.CARD
	box.set_corner_radius_all(8)
	box.set_border_width_all(1)
	box.border_color = AppTheme.GOLD if bool(match.get("completed", false)) else AppTheme.BORDER
	box.content_margin_left = 10
	box.content_margin_right = 10
	box.content_margin_top = 8
	box.content_margin_bottom = 8
	card.add_theme_stylebox_override("panel", box)
	var box_content := VBoxContainer.new()
	box_content.add_theme_constant_override("separation", 4)
	var winner: Variant = match.get("winner")
	box_content.add_child(_bracket_team_row(str(match.get("home", "?")), match.get("home_runs"), winner))
	box_content.add_child(HSeparator.new())
	box_content.add_child(_bracket_team_row(str(match.get("away", "?")), match.get("away_runs"), winner))
	card.add_child(box_content)
	return card


func _bracket_team_row(team_name: String, runs: Variant, winner: Variant) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	var name_label := Label.new()
	name_label.text = team_name
	name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_label.add_theme_font_size_override("font_size", 12)
	var is_winner: bool = winner != null and str(winner) == team_name
	name_label.add_theme_color_override("font_color", AppTheme.GOLD if is_winner else AppTheme.TEXT_PRIMARY)
	row.add_child(name_label)
	if runs != null:
		var runs_label := Label.new()
		runs_label.text = JsonFormat.value(runs)
		runs_label.add_theme_font_size_override("font_size", 12)
		runs_label.add_theme_color_override("font_color", AppTheme.GOLD if is_winner else AppTheme.TEXT_SECONDARY)
		row.add_child(runs_label)
	return row
