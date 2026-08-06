class_name BracketView
extends RefCounted
## Shared knockout-bracket renderer — round columns of match-box cards plus
## a gold "CHAMPIONS" banner once the Final is decided. Previously
## tournament_bracket_screen.gd (Domestic Cup) and international_screen.gd
## (World Cup knockout) each carried an independent copy of this exact same
## visual (see docs/CURRENT.md's concept-screen-recreation plan) — one
## shared builder now, used by both.

const CARD_WIDTH := 220.0


## Fills an existing HBoxContainer with round columns from a
## {round_name: [match, ...]} bracket dict and an ordered round-name list —
## the same response shape get_cup_bracket/get_current_international_competition's
## knockout kind both already return. Appends a trailing "CHAMPIONS" column
## once the last round's last match is completed. Takes the container to
## fill (rather than returning a new one) so callers keep their existing
## @onready reference/scroll-to-end logic instead of re-parenting nodes.
static func build(columns: HBoxContainer, bracket: Dictionary, rounds: Array) -> void:
	for child in columns.get_children():
		columns.remove_child(child)
		child.queue_free()
	for round_name in rounds:
		var column := VBoxContainer.new()
		column.custom_minimum_size = Vector2(CARD_WIDTH, 0)
		column.add_theme_constant_override("separation", 14)
		var round_card := PanelContainer.new()
		var round_style := StyleBoxFlat.new()
		round_style.bg_color = AppTheme.ACTIVE
		round_style.set_corner_radius_all(6)
		round_style.content_margin_left = 10
		round_style.content_margin_right = 10
		round_style.content_margin_top = 6
		round_style.content_margin_bottom = 6
		round_card.add_theme_stylebox_override("panel", round_style)
		var header := Label.new()
		header.text = str(round_name).to_upper()
		header.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		header.add_theme_color_override("font_color", AppTheme.GOLD)
		header.add_theme_font_size_override("font_size", 13)
		round_card.add_child(header)
		column.add_child(round_card)
		var matches: Array = bracket.get(round_name, [])
		for match in matches:
			column.add_child(_match_card(match))
		columns.add_child(column)
	var champion := _champion_name(bracket, rounds)
	if champion != "":
		columns.add_child(_champion_column(champion))


static func _champion_name(bracket: Dictionary, rounds: Array) -> String:
	if rounds.is_empty():
		return ""
	var final_matches: Array = bracket.get(rounds[-1], [])
	if final_matches.is_empty():
		return ""
	var final_match: Dictionary = final_matches[-1]
	if not bool(final_match.get("completed", false)):
		return ""
	var winner: Variant = final_match.get("winner")
	return str(winner) if winner != null else ""


static func _champion_column(champion: String) -> VBoxContainer:
	var column := VBoxContainer.new()
	column.custom_minimum_size = Vector2(CARD_WIDTH, 0)
	column.alignment = BoxContainer.ALIGNMENT_CENTER
	var card := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.ACTIVE
	box.set_corner_radius_all(10)
	box.set_border_width_all(2)
	box.border_color = AppTheme.GOLD
	box.content_margin_left = 14
	box.content_margin_right = 14
	box.content_margin_top = 14
	box.content_margin_bottom = 14
	card.add_theme_stylebox_override("panel", box)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 6)
	var heading := Label.new()
	heading.text = "CHAMPIONS"
	heading.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	heading.add_theme_color_override("font_color", AppTheme.GOLD)
	heading.add_theme_font_size_override("font_size", 12)
	content.add_child(heading)
	var name_label := Label.new()
	name_label.text = champion
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	name_label.add_theme_font_size_override("font_size", 15)
	content.add_child(name_label)
	card.add_child(content)
	column.add_child(card)
	return column


static func _match_card(match: Dictionary) -> PanelContainer:
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
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 4)
	var status := Label.new()
	status.text = "COMPLETED" if bool(match.get("completed", false)) else "UPCOMING"
	status.add_theme_font_size_override("font_size", 9)
	status.add_theme_color_override("font_color", AppTheme.HEADER_GREEN if bool(match.get("completed", false)) else AppTheme.TEXT_MUTED)
	content.add_child(status)
	var winner: Variant = match.get("winner")
	content.add_child(_team_row(str(match.get("home", "?")), match.get("home_runs"), winner))
	content.add_child(HSeparator.new())
	content.add_child(_team_row(str(match.get("away", "?")), match.get("away_runs"), winner))
	card.add_child(content)
	return card


static func _team_row(team_name: String, runs: Variant, winner: Variant) -> HBoxContainer:
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
