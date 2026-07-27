extends Control
## Ports src/views/screens/world_cup_setup.py: single-select grid of
## Full Member nations, confirmed via confirm_world_cup_team.

@onready var nation_grid: GridContainer = $Card/Box/Scroll/NationGrid
@onready var back_button: Button = $Footer/BackButton
@onready var confirm_button: Button = $Footer/ConfirmButton
@onready var message_label: Label = $Footer/Message

var _nations: Array = []
var _selected_id: String = ""
var _nation_buttons: Dictionary = {}


func _ready() -> void:
	back_button.pressed.connect(func(): _shell().show_screen("New Game Setup"))
	confirm_button.pressed.connect(_on_confirm_pressed)
	_load_nations()


func _shell() -> Node:
	return get_tree().get_first_node_in_group("shell")


func _load_nations() -> void:
	var response := IpcBridge.call_method("get_new_game_options")
	if response.has("error"):
		message_label.text = response["error"]
		return
	var all_countries: Array = response["result"].get("countries", [])
	_nations = all_countries.filter(func(c): return c.get("membership") == "Full Member")
	for child in nation_grid.get_children():
		nation_grid.remove_child(child)
		child.queue_free()
	_nation_buttons.clear()
	for i in range(_nations.size()):
		var nation: Dictionary = _nations[i]
		var country_id: String = nation.get("id", "")
		var button := Button.new()
		button.toggle_mode = true
		button.custom_minimum_size = Vector2(0, 60)
		button.text = "%s\n%s" % [nation.get("flag", ""), str(nation.get("name", "?")).to_upper()]
		button.button_pressed = i == 0
		button.pressed.connect(_on_nation_pressed.bind(country_id))
		nation_grid.add_child(button)
		_nation_buttons[country_id] = button
	if not _nations.is_empty():
		_selected_id = _nations[0].get("id", "")


func _on_nation_pressed(country_id: String) -> void:
	_selected_id = country_id
	for id in _nation_buttons:
		_nation_buttons[id].set_pressed_no_signal(id == country_id)


func _on_confirm_pressed() -> void:
	if _selected_id.is_empty():
		return
	var response := IpcBridge.call_method("confirm_world_cup_team", {"country_id": _selected_id})
	if response.has("error"):
		message_label.text = response["error"]
		return
	_shell().refresh_header()
	_shell().show_screen(str(response["result"].get("destination", "Dashboard")))
