extends Control
## Ports src/views/screens/tournament_setup.py: multi-select nation grid
## (4-12 teams, first 8 pre-selected) + a cycling format button, confirmed
## via confirm_custom_tournament.

const FORMATS := ["T10", "T20", "Hundred", "ODI", "Test"]

@onready var nation_grid: GridContainer = $Card/Box/Scroll/NationGrid
@onready var selected_count_label: Label = $Card/Box/HeaderRow/SelectedCount
@onready var back_button: Button = $Footer/BackButton
@onready var format_button: Button = $Footer/FormatButton
@onready var confirm_button: Button = $Footer/ConfirmButton
@onready var message_label: Label = $Footer/Message

var _nations: Array = []
var _selected_ids: Array = []
var _format: String = "T20"
var _nation_buttons: Dictionary = {}


func _ready() -> void:
	back_button.pressed.connect(func(): _shell().show_screen("New Game Setup"))
	format_button.pressed.connect(_on_format_pressed)
	confirm_button.pressed.connect(_on_confirm_pressed)
	_load_nations()


func _shell() -> Node:
	return get_tree().get_first_node_in_group("shell")


func _load_nations() -> void:
	var response := IpcBridge.call_method("get_new_game_options")
	if response.has("error"):
		message_label.text = response["error"]
		return
	_nations = response["result"].get("countries", [])
	for child in nation_grid.get_children():
		nation_grid.remove_child(child)
		child.queue_free()
	_nation_buttons.clear()
	_selected_ids.clear()
	for i in range(_nations.size()):
		var nation: Dictionary = _nations[i]
		var country_id: String = nation.get("id", "")
		var button := Button.new()
		button.toggle_mode = true
		button.custom_minimum_size = Vector2(0, 40)
		button.text = "%s %s" % [nation.get("flag", ""), nation.get("name", "?")]
		var pre_selected := i < 8
		button.button_pressed = pre_selected
		if pre_selected:
			_selected_ids.append(country_id)
		button.pressed.connect(_on_nation_pressed.bind(country_id, button))
		nation_grid.add_child(button)
		_nation_buttons[country_id] = button
	_update_selected_count()


func _on_nation_pressed(country_id: String, button: Button) -> void:
	if _selected_ids.has(country_id):
		_selected_ids.erase(country_id)
	elif _selected_ids.size() < 12:
		_selected_ids.append(country_id)
	else:
		button.set_pressed_no_signal(false)
	button.set_pressed_no_signal(_selected_ids.has(country_id))
	_update_selected_count()


func _update_selected_count() -> void:
	selected_count_label.text = "%d TEAMS SELECTED" % _selected_ids.size()


func _on_format_pressed() -> void:
	_format = FORMATS[(FORMATS.find(_format) + 1) % FORMATS.size()]
	format_button.text = "FORMAT: %s" % _format.to_upper()


func _on_confirm_pressed() -> void:
	var response := IpcBridge.call_method("confirm_custom_tournament",
		{"country_ids": _selected_ids, "format": _format})
	if response.has("error"):
		message_label.text = response["error"]
		return
	message_label.text = ""
	_shell().refresh_header()
	_shell().show_screen(str(response["result"].get("destination", "Dashboard")))
