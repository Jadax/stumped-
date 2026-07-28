extends Control
## New in v0.88.0: a bracket-tree view for the Domestic Knockout Cup —
## previously no such visual existed anywhere in either client (pygame or
## Godot), and the only bracket-shaped backend endpoint
## (get_tournament_bracket) covered the separate, in-career "custom
## tournament" system, not the main season-long Cup every save has.
## Reference: Cricket Captain's "20 Over Trophy" bracket screenshot —
## columns of rounds (Round of 32 -> Final), each a vertical stack of
## match boxes, most recent/active round scrolled into view.

@onready var title_label: Label = $Title
@onready var scroll: ScrollContainer = $Scroll
@onready var columns: HBoxContainer = $Scroll/Columns

const CARD_WIDTH := 220.0


func _ready() -> void:
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_cup_bracket")
	if response.has("error"):
		title_label.text = "DOMESTIC KNOCKOUT CUP — backend error: %s" % response["error"]
		push_error("TournamentBracketScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	_render(result)
	var status: String = str(result.get("status", "not_started"))
	var season = result.get("season")
	if status == "not_started":
		title_label.text = "DOMESTIC KNOCKOUT CUP — not started yet"
	elif status == "complete":
		title_label.text = "DOMESTIC KNOCKOUT CUP — %s season, complete" % JsonFormat.value(season)
	else:
		title_label.text = "DOMESTIC KNOCKOUT CUP — %s season" % JsonFormat.value(season)


func _clear(container: Control) -> void:
	for child in container.get_children():
		container.remove_child(child)
		child.queue_free()


func _render(result: Dictionary) -> void:
	_clear(columns)
	var rounds: Array = result.get("rounds", [])
	var bracket: Dictionary = result.get("bracket", {})
	if rounds.is_empty():
		var empty := Label.new()
		empty.text = "The cup draw hasn't been made yet — check back once the season is under way."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		columns.add_child(empty)
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
			column.add_child(_match_card(match))
		columns.add_child(column)
	# Scroll to the rightmost (most advanced/active) round, matching how a
	# player's attention naturally moves as the cup progresses.
	await get_tree().process_frame
	scroll.scroll_horizontal = int(scroll.get_h_scroll_bar().max_value)


func _match_card(match: Dictionary) -> PanelContainer:
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
	var winner: Variant = match.get("winner")
	content.add_child(_team_row(str(match.get("home", "?")), match.get("home_runs"), winner))
	content.add_child(HSeparator.new())
	content.add_child(_team_row(str(match.get("away", "?")), match.get("away_runs"), winner))
	card.add_child(content)
	return card


func _team_row(team_name: String, runs: Variant, winner: Variant) -> HBoxContainer:
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
