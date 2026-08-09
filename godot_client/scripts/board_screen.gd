extends Control
## Board objectives + confidence history — ports evaluate_board_objectives()/
## get_board_confidence_history() (exposed over IPC since v0.64.0 but
## previously never consumed by any UI in either client: board reviews
## were only ever announced via inbox text, with no way to check current
## standing on demand). Mirrors pygame's ui/career.py Board tab.
##
## v4.58.0: a third "MANAGER PROGRESS" card, built at runtime (not in the
## .tscn — same pattern match_screen.gd's `_restructure_*` helpers use for
## additive node surgery) showing the new manager XP/level/perk ladder
## (src/models/manager_progression.py) alongside the pre-existing board
## objectives/confidence cards — this is where a manager's own standing
## already lives, so the new progression system joins it rather than
## getting a whole new nav item.

@onready var title_label: Label = $Title
@onready var league_target: Label = $Row/ObjectivesCard/Box/LeagueRow/LeagueLabel/Target
@onready var league_current: Label = $Row/ObjectivesCard/Box/LeagueRow/LeagueStatus/Current
@onready var league_met: Label = $Row/ObjectivesCard/Box/LeagueRow/LeagueStatus/Met
@onready var cash_target: Label = $Row/ObjectivesCard/Box/CashRow/CashLabel/Target
@onready var cash_current: Label = $Row/ObjectivesCard/Box/CashRow/CashStatus/Current
@onready var cash_met: Label = $Row/ObjectivesCard/Box/CashRow/CashStatus/Met
@onready var history_list: VBoxContainer = $Row/HistoryCard/Box/Scroll/List

var _manager_level_label: Label
var _manager_xp_bar_holder: Control
var _manager_perks_list: VBoxContainer


func _ready() -> void:
	_build_manager_card()
	refresh()


func _build_manager_card() -> void:
	var row: HBoxContainer = $Row
	var card := PanelContainer.new()
	card.size_flags_horizontal = SIZE_EXPAND_FILL
	row.add_child(card)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	card.add_child(box)
	var header := Label.new()
	header.text = "MANAGER PROGRESS"
	header.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	box.add_child(header)
	_manager_level_label = Label.new()
	_manager_level_label.add_theme_font_size_override("font_size", 16)
	box.add_child(_manager_level_label)
	_manager_xp_bar_holder = Control.new()
	box.add_child(_manager_xp_bar_holder)
	var perks_header := Label.new()
	perks_header.text = "PERKS"
	perks_header.add_theme_font_size_override("font_size", 11)
	perks_header.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	box.add_child(perks_header)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = SIZE_EXPAND_FILL
	box.add_child(scroll)
	_manager_perks_list = VBoxContainer.new()
	_manager_perks_list.add_theme_constant_override("separation", 4)
	_manager_perks_list.size_flags_horizontal = SIZE_EXPAND_FILL
	scroll.add_child(_manager_perks_list)


func _refresh_manager_progress() -> void:
	var response := IpcBridge.call_method("get_manager_progress")
	if response.has("error"):
		push_error("BoardScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	var xp: int = int(result.get("xp", 0))
	var level: int = int(result.get("level", 1))
	var points: int = int(result.get("points_available", 0))
	_manager_level_label.text = "Level %d  •  %d perk point%s" % [level, points, "" if points == 1 else "s"]
	for child in _manager_xp_bar_holder.get_children():
		_manager_xp_bar_holder.remove_child(child)
		child.queue_free()
	_manager_xp_bar_holder.add_child(AppTheme.make_bar_meter(160.0, float(xp % 100)))
	for child in _manager_perks_list.get_children():
		_manager_perks_list.remove_child(child)
		child.queue_free()
	for perk in result.get("perks", []):
		_manager_perks_list.add_child(_perk_row(perk, level, points))


func _perk_row(perk: Dictionary, level: int, points: int) -> Control:
	var row := PanelContainer.new()
	var unlocked: bool = bool(perk.get("unlocked", false))
	var min_level: int = int(perk.get("min_level", 1))
	var eligible: bool = not unlocked and level >= min_level and points > 0
	var box := HBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	row.add_child(box)
	var text := VBoxContainer.new()
	text.size_flags_horizontal = SIZE_EXPAND_FILL
	box.add_child(text)
	var name_label := Label.new()
	name_label.text = str(perk.get("name", "?"))
	name_label.add_theme_font_size_override("font_size", 12)
	name_label.add_theme_color_override("font_color", AppTheme.GOLD if unlocked else AppTheme.TEXT_PRIMARY)
	text.add_child(name_label)
	var desc_label := Label.new()
	desc_label.text = str(perk.get("description", ""))
	desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	desc_label.add_theme_font_size_override("font_size", 10)
	desc_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	text.add_child(desc_label)
	if unlocked:
		var status := Label.new()
		status.text = "UNLOCKED"
		status.add_theme_font_size_override("font_size", 10)
		status.add_theme_color_override("font_color", AppTheme.HEADER_GREEN)
		box.add_child(status)
	else:
		var unlock_button := Button.new()
		unlock_button.text = "Unlock" if eligible else ("Lvl %d" % min_level)
		unlock_button.disabled = not eligible
		unlock_button.pressed.connect(_on_unlock_perk_pressed.bind(str(perk.get("id", ""))))
		box.add_child(unlock_button)
	return row


func _on_unlock_perk_pressed(perk_id: String) -> void:
	var response := IpcBridge.call_method("unlock_manager_perk", {"perk_id": perk_id})
	if response.has("error"):
		push_error("BoardScreen: %s" % response["error"])
		return
	_refresh_manager_progress()


func refresh() -> void:
	_refresh_manager_progress()
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
