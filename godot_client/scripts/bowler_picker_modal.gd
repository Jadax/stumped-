class_name BowlerPickerModal
extends Control
## Real bowler picker (v4.13.0-v4.15.0 Match Day rebuild, Part 4) — a list
## of eligible bowlers with live O-M-R-W figures and a SELECT action per
## row, replacing the old blind CHANGE cycle button. Backed by the new
## set_match_bowler IPC method (v4.14.0), which wraps the already-
## validated Match.set_bowler().

signal bowler_selected(player_id: int)

@onready var close_button: Button = $Center/Card/Margin/Box/Header/Close
@onready var bowler_list: VBoxContainer = $Center/Card/Margin/Box/Scroll/BowlerList
@onready var dim: ColorRect = $Dim


func _ready() -> void:
	close_button.pressed.connect(hide_modal)
	dim.gui_input.connect(_on_dim_input)
	bowler_selected.connect(func(_player_id): hide_modal())
	var card_box := StyleBoxFlat.new()
	card_box.bg_color = AppTheme.CARD
	card_box.border_color = AppTheme.GOLD
	card_box.set_border_width_all(1)
	card_box.set_corner_radius_all(10)
	$Center/Card.add_theme_stylebox_override("panel", card_box)


## eligible: [{id,name}] from get_match_state's eligible_bowlers.
## bowling_rows: the current innings' "bowling" scorecard rows, used to
## show real figures for whoever's already bowled this innings.
func show_for(eligible: Array, bowling_rows: Array, current_bowler_id: int) -> void:
	for child in bowler_list.get_children():
		bowler_list.remove_child(child)
		child.queue_free()
	if eligible.is_empty():
		var empty := Label.new()
		empty.text = "No eligible bowler change available right now."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		bowler_list.add_child(empty)
	for bowler in eligible:
		bowler_list.add_child(_bowler_row(bowler, bowling_rows, current_bowler_id))
	visible = true


func _bowler_row(bowler: Dictionary, bowling_rows: Array, current_bowler_id: int) -> PanelContainer:
	var player_id := int(bowler.get("id", -1))
	var figures := "0.0-0-0-0"
	for row in bowling_rows:
		if int(row.get("player_id", -1)) == player_id:
			figures = "%s-%d-%d-%d" % [JsonFormat.value(row.get("overs", "0.0")),
				int(row.get("maidens", 0)), int(row.get("runs", 0)), int(row.get("wickets", 0))]
			break
	var is_current: bool = player_id == current_bowler_id
	var card := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.SURFACE if is_current else AppTheme.CARD
	box.set_corner_radius_all(6)
	box.set_border_width_all(1)
	box.border_color = AppTheme.GOLD if is_current else AppTheme.BORDER
	box.content_margin_left = 10; box.content_margin_right = 10
	box.content_margin_top = 6; box.content_margin_bottom = 6
	card.add_theme_stylebox_override("panel", box)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	var name_label := Label.new()
	name_label.text = str(bowler.get("name", "?")) + (" (bowling)" if is_current else "")
	name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_label.add_theme_font_size_override("font_size", 13)
	if is_current:
		name_label.add_theme_color_override("font_color", AppTheme.GOLD)
	row.add_child(name_label)
	var figures_label := Label.new()
	figures_label.text = figures
	figures_label.custom_minimum_size = Vector2(90, 0)
	figures_label.add_theme_font_size_override("font_size", 12)
	figures_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	row.add_child(figures_label)
	var select_button := Button.new()
	select_button.text = "SELECT"
	select_button.disabled = is_current
	select_button.custom_minimum_size = Vector2(80, 28)
	select_button.pressed.connect(func(): bowler_selected.emit(player_id))
	row.add_child(select_button)
	card.add_child(row)
	return card


func hide_modal() -> void:
	visible = false


func _on_dim_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		hide_modal()
