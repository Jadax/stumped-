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
		var card := PanelContainer.new()
		card.add_theme_stylebox_override("panel", AppTheme.make_card(false))
		var card_box := VBoxContainer.new()
		card_box.add_theme_constant_override("separation", 8)
		var header := Label.new()
		header.text = "%s  •  GROUP STAGE" % str(label).to_upper()
		header.add_theme_color_override("font_color", AppTheme.GOLD)
		header.add_theme_font_size_override("font_size", 15)
		card_box.add_child(header)
		card_box.add_child(_standings_table(group.get("standings", [])))
		card.add_child(card_box)
		content.add_child(card)
		for match in group.get("matches", []):
			content.add_child(_match_row(match))


## Reference (World Cup group screenshot): a single gold qualification-line
## row after the last automatically-advancing team, not a per-row border —
## QUALIFY_COUNT mirrors CompetitionEngine._start_icc_tournament's default
## advance_per_group (2); the group response has no explicit count to read
## (see get_current_international_competition), so this is the same top-2
## assumption the previous top/bottom-border version made, just rendered
## as a real divider line matching the reference instead of row borders.
const QUALIFY_COUNT := 2


func _standings_table(standings: Array) -> VBoxContainer:
	var table := VBoxContainer.new()
	table.add_theme_constant_override("separation", 2)
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 12)
	for text in ["#", "TEAM", "P", "W", "L", "T", "PTS", "NRR"]:
		var h := Label.new()
		h.text = text
		h.custom_minimum_size = Vector2(28, 0) if text == "#" else (Vector2(150, 0) if text == "TEAM" else Vector2(48, 0))
		h.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT if text not in ["#", "TEAM"] else HORIZONTAL_ALIGNMENT_LEFT
		h.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		h.add_theme_font_size_override("font_size", 11)
		header.add_child(h)
	table.add_child(header)
	for index in range(standings.size()):
		var row_data: Dictionary = standings[index]
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
		row.add_child(_group_cell(str(index + 1), 28, AppTheme.TEXT_MUTED, HORIZONTAL_ALIGNMENT_LEFT))
		row.add_child(_group_cell(str(row_data.get("team", "?")), 150, AppTheme.TEXT_PRIMARY, HORIZONTAL_ALIGNMENT_LEFT, true))
		for key in ["played", "won", "lost", "tied", "points"]:
			var colour := AppTheme.GOLD if key == "points" else AppTheme.TEXT_SECONDARY
			row.add_child(_group_cell(str(row_data.get(key, 0)), 48, colour, HORIZONTAL_ALIGNMENT_RIGHT))
		row.add_child(_group_cell(str(row_data.get("net_run_rate", 0.0)), 48, AppTheme.TEXT_SECONDARY, HORIZONTAL_ALIGNMENT_RIGHT))
		panel.add_child(row)
		table.add_child(panel)
		if index == QUALIFY_COUNT - 1 and index < standings.size() - 1:
			var divider := ColorRect.new()
			divider.color = AppTheme.GOLD
			divider.custom_minimum_size = Vector2(0, 2)
			table.add_child(divider)
	return table


func _group_cell(text: String, width: int, colour: Color, alignment: HorizontalAlignment, expand: bool = false) -> Label:
	var label := Label.new()
	label.text = text
	label.custom_minimum_size = Vector2(width, 0)
	label.horizontal_alignment = alignment
	label.add_theme_color_override("font_color", colour)
	label.add_theme_font_size_override("font_size", 12 if expand else 11)
	if expand:
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		label.clip_text = true
	return label


## v4.52.0: goes through the shared BracketView.build() (bracket_view.gd) —
## this screen's knockout view was previously an independent copy of
## tournament_bracket_screen.gd's match-card/team-row drawing code; now both
## screens (Domestic Cup, World Cup knockout) share one implementation and
## both get the gold "CHAMPIONS" banner for free once the Final is decided.
func _render_bracket(bracket: Dictionary, rounds: Array) -> void:
	if rounds.is_empty():
		var empty := Label.new()
		empty.text = "The knockout draw hasn't been made yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		content.add_child(empty)
		return
	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 20)
	content.add_child(columns)
	BracketView.build(columns, bracket, rounds)
