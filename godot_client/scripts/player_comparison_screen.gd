extends Control
## Player comparison screen — compare two players side-by-side
## with attribute bars and visual indicators.

@onready var title_label: Label = $Title
@onready var player1_panel: PanelContainer = $Players/Player1
@onready var player2_panel: PanelContainer = $Players/Player2
@onready var compare_button: Button = $Footer/CompareButton
@onready var back_button: Button = $Footer/BackButton

var _player1: Dictionary = {}
var _player2: Dictionary = {}


func _ready() -> void:
	compare_button.pressed.connect(_on_compare)
	back_button.pressed.connect(_on_back)


func _on_back() -> void:
	var shell := get_tree().get_first_node_in_group("shell")
	if shell:
		shell.show_screen("Squad")


func show_comparison(player1: Dictionary, player2: Dictionary) -> void:
	_player1 = player1
	_player2 = player2
	_render_comparison()
	visible = true


func _render_comparison() -> void:
	_render_player_card(_player1, player1_panel)
	_render_player_card(_player2, player2_panel)


func _render_player_card(player: Dictionary, panel: PanelContainer) -> void:
	var box := panel.get_node_or_null("VBox")
	if not box:
		return
	for child in box.get_children():
		child.queue_free()
	# Player header
	var header := VBoxContainer.new()
	header.add_theme_constant_override("separation", 4)
	var name_label := Label.new()
	name_label.text = str(player.get("name", "?"))
	name_label.add_theme_font_size_override("font_size", 18)
	name_label.add_theme_color_override("font_color", AppTheme.GOLD)
	header.add_child(name_label)
	var meta_label := Label.new()
	meta_label.text = "%s • %s yrs • %s" % [
		str(player.get("role", "?")),
		str(player.get("age", "?")),
		str(player.get("nationality", "?"))
	]
	meta_label.add_theme_font_size_override("font_size", 12)
	meta_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	header.add_child(meta_label)
	box.add_child(header)
	# Overall
	var ovr_row := HBoxContainer.new()
	ovr_row.add_theme_constant_override("separation", 8)
	var ovr_label := Label.new()
	ovr_label.text = "Overall: %d" % int(player.get("overall", 0))
	ovr_label.add_theme_font_size_override("font_size", 14)
	ovr_row.add_child(ovr_label)
	var pot_label := Label.new()
	pot_label.text = "Potential: %d" % int(player.get("potential", 0))
	pot_label.add_theme_font_size_override("font_size", 12)
	pot_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	ovr_row.add_child(pot_label)
	box.add_child(ovr_row)
	# Attributes
	var attrs: Dictionary = player.get("batting", {}) if player.get("batting") is Dictionary else {}
	for attr in attrs:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		var attr_label := Label.new()
		attr_label.text = str(attr).capitalize()
		attr_label.custom_minimum_size = Vector2(120, 0)
		attr_label.add_theme_font_size_override("font_size", 11)
		row.add_child(attr_label)
		row.add_child(AppTheme.make_bar_meter(150.0, float(attrs[attr]), 11))
		box.add_child(row)
	# Form/Morale
	var form: int = int(player.get("form", 50))
	var mental: Dictionary = player.get("mental", {}) if player.get("mental") is Dictionary else {}
	var morale: int = int(mental.get("morale", 50))
	var status_row := HBoxContainer.new()
	status_row.add_theme_constant_override("separation", 8)
	status_row.add_child(AppTheme.make_status_chip("FORM", form))
	status_row.add_child(AppTheme.make_status_chip("MORALE", morale))
	box.add_child(status_row)


func _on_compare() -> void:
	# Toggle comparison view
	visible = not visible
