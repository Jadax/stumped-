extends Control
## Board objectives + confidence history — ports evaluate_board_objectives()/
## get_board_confidence_history() (exposed over IPC since v0.64.0 but
## previously never consumed by any UI in either client: board reviews
## were only ever announced via inbox text, with no way to check current
## standing on demand). Mirrors pygame's ui/career.py Board tab.

@onready var title_label: Label = $Title
@onready var league_target: Label = $Row/ObjectivesCard/Box/LeagueRow/LeagueLabel/Target
@onready var league_current: Label = $Row/ObjectivesCard/Box/LeagueRow/LeagueStatus/Current
@onready var league_met: Label = $Row/ObjectivesCard/Box/LeagueRow/LeagueStatus/Met
@onready var cash_target: Label = $Row/ObjectivesCard/Box/CashRow/CashLabel/Target
@onready var cash_current: Label = $Row/ObjectivesCard/Box/CashRow/CashStatus/Current
@onready var cash_met: Label = $Row/ObjectivesCard/Box/CashRow/CashStatus/Met
@onready var history_list: VBoxContainer = $Row/HistoryCard/Box/Scroll/List


func _ready() -> void:
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_board_objectives")
	if response.has("error"):
		title_label.text = "BOARD — backend error: %s" % response["error"]
		push_error("BoardScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	var progress: Dictionary = result.get("progress", {})
	_render_objective(progress.get("league_position", {}), league_target, league_current, league_met, true)
	_render_objective(progress.get("cash_balance", {}), cash_target, cash_current, cash_met, false)

	var history_response := IpcBridge.call_method("get_board_confidence_history")
	var history: Array = [] if history_response.has("error") else history_response["result"].get("history", [])
	for child in history_list.get_children():
		history_list.remove_child(child)
		child.queue_free()
	if history.is_empty():
		var empty := Label.new()
		empty.text = "No confidence reviews recorded yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		history_list.add_child(empty)
	else:
		history.reverse()
		for entry in history.slice(0, 10):
			var row := HBoxContainer.new()
			row.add_theme_constant_override("separation", 10)
			var date_label := Label.new()
			date_label.text = str(entry.get("date", "—"))
			date_label.custom_minimum_size = Vector2(100, 0)
			date_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
			date_label.add_theme_font_size_override("font_size", 11)
			row.add_child(date_label)
			var label_text: String = str(entry.get("label", "—"))
			var status_label := Label.new()
			status_label.text = label_text
			status_label.add_theme_font_size_override("font_size", 12)
			status_label.add_theme_color_override("font_color", _label_colour(label_text))
			row.add_child(status_label)
			history_list.add_child(row)
	title_label.text = "BOARD"


func _render_objective(entry: Dictionary, target_label: Label, current_label: Label,
					   met_label: Label, is_league: bool) -> void:
	var met: bool = bool(entry.get("met", false))
	var colour: Color = AppTheme.HEADER_GREEN if met else AppTheme.DANGER
	if is_league:
		target_label.text = "Target: top %s" % JsonFormat.value(entry.get("target", "—"))
		var current = entry.get("current")
		current_label.text = str(JsonFormat.value(current)) if current != null else "—"
	else:
		target_label.text = "Target: %s+" % JsonFormat.value(entry.get("target", 0))
		current_label.text = JsonFormat.value(entry.get("current", 0))
	current_label.add_theme_color_override("font_color", colour)
	met_label.text = "MET" if met else "SHORT"
	met_label.add_theme_color_override("font_color", colour)


func _label_colour(label_text: String) -> Color:
	match label_text:
		"Delighted", "Content":
			return AppTheme.HEADER_GREEN
		"Under pressure":
			return AppTheme.GOLD
		"Ultimatum":
			return AppTheme.DANGER
		_:
			return AppTheme.TEXT_MUTED
