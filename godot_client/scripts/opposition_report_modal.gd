class_name OppositionReportModal
extends Control
## Pre-match scouting summary of the next opponent — ports the backend's
## get_opposition_report (ipc_server.py/database.py, shipped since
## v0.63.0 but never consumed by any UI in either client until now):
## key players, strengths/weaknesses, squad composition, recent form.

@onready var title_label: Label = $Center/Card/Margin/Box/Header/Title
@onready var close_button: Button = $Center/Card/Margin/Box/Header/Close
@onready var meta_label: Label = $Center/Card/Margin/Box/Meta
@onready var game_plan_list: VBoxContainer = $Center/Card/Margin/Box/GamePlanList
@onready var strengths_list: VBoxContainer = $Center/Card/Margin/Box/StrengthsList
@onready var weaknesses_list: VBoxContainer = $Center/Card/Margin/Box/WeaknessesList
@onready var key_players_list: VBoxContainer = $Center/Card/Margin/Box/Scroll/KeyPlayersList
@onready var dim: ColorRect = $Dim


func _ready() -> void:
	close_button.pressed.connect(hide_modal)
	dim.gui_input.connect(_on_dim_input)
	var card_box := StyleBoxFlat.new()
	card_box.bg_color = AppTheme.CARD
	card_box.border_color = AppTheme.GOLD
	card_box.set_border_width_all(1)
	card_box.set_corner_radius_all(10)
	$Center/Card.add_theme_stylebox_override("panel", card_box)
	meta_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)


func show_for(report: Dictionary) -> void:
	title_label.text = "OPPOSITION REPORT — %s" % str(report.get("opponent_name", "?")).to_upper()
	meta_label.text = "%s • %s • %s • Squad avg OVR %s (%d players)" % [
		report.get("fixture_date", "?"), report.get("venue", "?"), report.get("format", "?"),
		JsonFormat.value(report.get("average_overall", 0)), int(report.get("squad_size", 0))]
	_fill_game_plan(report.get("recommendations", {}))
	_fill_list(strengths_list, report.get("strengths", []), AppTheme.GOLD)
	_fill_list(weaknesses_list, report.get("weaknesses", []), AppTheme.DANGER)
	for child in key_players_list.get_children():
		key_players_list.remove_child(child)
		child.queue_free()
	for player in report.get("key_players", []):
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 10)
		var name_label := Label.new()
		name_label.text = "%s (%s)" % [player.get("name", "?"), player.get("role", "?")]
		name_label.custom_minimum_size = Vector2(280, 0)
		name_label.add_theme_font_size_override("font_size", 12)
		row.add_child(name_label)
		var ovr_label := Label.new()
		ovr_label.text = "OVR %s" % JsonFormat.value(player.get("overall", 0))
		ovr_label.add_theme_font_size_override("font_size", 12)
		ovr_label.add_theme_color_override("font_color", AppTheme.attribute_colour(float(player.get("overall", 50))))
		row.add_child(ovr_label)
		key_players_list.add_child(row)
	visible = true


## v4.26.0: the report used to be pure flavour text (strengths/weaknesses
## with no actionable follow-through) — this turns it into real pre-match
## calls: which of the user's own bowlers to target which opponent
## batter with, which pitch to request, and how to lean the batting order.
## Grounded in database._opposition_recommendations' real per-player
## technique_vs_pace/technique_vs_spin comparison, not flavour text.
func _fill_game_plan(recommendations: Dictionary) -> void:
	var items: Array = []
	items.append_array(recommendations.get("bowling_plan", []))
	var pitch_advice = recommendations.get("pitch_advice")
	if pitch_advice != null:
		items.append(str(pitch_advice))
	var batting_advice = recommendations.get("batting_order_advice")
	if batting_advice != null:
		items.append(str(batting_advice))
	_fill_list(game_plan_list, items, AppTheme.HEADER_GREEN)


func _fill_list(list: VBoxContainer, items: Array, colour: Color) -> void:
	for child in list.get_children():
		list.remove_child(child)
		child.queue_free()
	if items.is_empty():
		var empty := Label.new()
		empty.text = "None noted."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		empty.add_theme_font_size_override("font_size", 12)
		list.add_child(empty)
		return
	for item in items:
		var label := Label.new()
		label.text = "• %s" % str(item)
		label.add_theme_color_override("font_color", colour)
		label.add_theme_font_size_override("font_size", 12)
		list.add_child(label)


func hide_modal() -> void:
	visible = false


func _on_dim_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		hide_modal()
