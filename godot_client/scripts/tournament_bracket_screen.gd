extends Control
## New in v0.88.0: a bracket-tree view for the Domestic Knockout Cup —
## previously no such visual existed anywhere in either client (pygame or
## Godot), and the only bracket-shaped backend endpoint
## (get_tournament_bracket) covered the separate, in-career "custom
## tournament" system, not the main season-long Cup every save has.
## Reference: Cricket Captain's "20 Over Trophy" bracket screenshot —
## columns of rounds (Round of 32 -> Final), each a vertical stack of
## match boxes, most recent/active round scrolled into view.
## v4.52.0: rendering now goes through the shared BracketView.build()
## (bracket_view.gd) instead of a locally duplicated copy of the same
## match-card/team-row drawing international_screen.gd's knockout view
## also needed — both screens' knockout visuals were previously
## independent copies of the same code.

@onready var title_label: Label = $Title
@onready var scroll: ScrollContainer = $Scroll
@onready var columns: HBoxContainer = $Scroll/Columns


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


func _render(result: Dictionary) -> void:
	var rounds: Array = result.get("rounds", [])
	var bracket: Dictionary = result.get("bracket", {})
	if rounds.is_empty():
		for child in columns.get_children():
			columns.remove_child(child)
			child.queue_free()
		var empty := Label.new()
		empty.text = "The cup draw hasn't been made yet — check back once the season is under way."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		columns.add_child(empty)
		return
	BracketView.build(columns, bracket, rounds)
	# Scroll to the rightmost (most advanced/active) round, matching how a
	# player's attention naturally moves as the cup progresses.
	await get_tree().process_frame
	scroll.scroll_horizontal = int(scroll.get_h_scroll_bar().max_value)
