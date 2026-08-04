extends Control
## Ports src/views/screens/new_game_setup.py's exact field set (name,
## nationality, background, mode, difficulty, starting league) to Godot,
## driven by the new save_new_game_setup/get_new_game_options IPC methods
## which reuse GameController's validation 1:1 (ipc_server.py).

@onready var message_label: Label = $Message
@onready var name_edit: LineEdit = $Row/ProfileCard/Box/NameEdit
@onready var nationality_dropdown: OptionButton = $Row/ProfileCard/Box/NationalityDropdown
@onready var background_buttons: VBoxContainer = $Row/ProfileCard/Box/BackgroundButtons
@onready var mode_buttons: VBoxContainer = $Row/GameCard/Box/ModeButtons
@onready var difficulty_buttons: HBoxContainer = $Row/GameCard/Box/DifficultyButtons
@onready var league_grid: GridContainer = $Row/LeagueCard/Box/Scroll/LeagueGrid
@onready var back_button: Button = $Footer/BackButton
@onready var continue_button: Button = $Footer/ContinueButton

const BACKGROUND_LABELS := {"EX-PLAYER": "Ex-Player", "COACH": "Coach", "SCOUT": "Scout"}
## v4.28.0: Tournament mode removed — the custom-tournament system it led
## to never assigned the user a real club (team fell back to whatever
## team_id happened to be current, e.g. Lancashire), a genuinely broken
## flow. Career and World Cup are both complete; Tournament wasn't.
const MODE_LABELS := {"CAREER": "Career", "WORLD CUP": "World Cup"}
const DIFFICULTY_LABELS := {"EASY": "Easy", "NORMAL": "Normal", "HARD": "Hard"}

var _countries: Array = []
var _country_buttons: Dictionary = {}
var _enabled_countries: Array = ["england", "australia", "india"]
var _primary_country: String = "england"


func _ready() -> void:
	back_button.pressed.connect(func(): _shell().show_screen("Main Menu"))
	continue_button.pressed.connect(_on_continue_pressed)
	for button in background_buttons.get_children():
		button.toggled.connect(func(pressed): if pressed: _select_single(background_buttons, button))
	for button in mode_buttons.get_children():
		button.toggled.connect(func(pressed): if pressed: _select_single(mode_buttons, button))
	for button in difficulty_buttons.get_children():
		button.toggled.connect(func(pressed): if pressed: _select_single(difficulty_buttons, button))
	_load_options()


func _shell() -> Node:
	return get_tree().get_first_node_in_group("shell")


func _select_single(group: Node, chosen: Button) -> void:
	for button in group.get_children():
		button.set_pressed_no_signal(button == chosen)


func _load_options() -> void:
	var response := IpcBridge.call_method("get_new_game_options")
	if response.has("error"):
		message_label.text = "Backend error: %s" % response["error"]
		return
	var result: Dictionary = response["result"]
	_countries = result.get("countries", [])
	nationality_dropdown.clear()
	var england_index := 0
	for i in range(_countries.size()):
		var country: Dictionary = _countries[i]
		nationality_dropdown.add_item(str(country.get("name", "?")))
		if country.get("id") == "england":
			england_index = i
	nationality_dropdown.select(england_index)
	_build_league_grid()


func _build_league_grid() -> void:
	for child in league_grid.get_children():
		league_grid.remove_child(child)
		child.queue_free()
	_country_buttons.clear()
	for country in _countries:
		var country_id: String = country.get("id", "")
		var button := Button.new()
		button.toggle_mode = true
		button.custom_minimum_size = Vector2(0, 36)
		button.text = "%s %s" % [country.get("flag", ""), country.get("name", "?")]
		button.button_pressed = country_id == _primary_country
		button.pressed.connect(_on_country_pressed.bind(country_id))
		league_grid.add_child(button)
		_country_buttons[country_id] = button


func _on_country_pressed(country_id: String) -> void:
	_primary_country = country_id
	if not _enabled_countries.has(country_id):
		_enabled_countries.append(country_id)
	for id in _country_buttons:
		_country_buttons[id].set_pressed_no_signal(id == country_id)


func _selected_label(group: Node, labels: Dictionary, fallback: String) -> String:
	for button in group.get_children():
		if button.button_pressed:
			return labels.get(button.text, fallback)
	return fallback


func _on_continue_pressed() -> void:
	var params := {
		"name": name_edit.text,
		"nationality": nationality_dropdown.get_item_text(nationality_dropdown.selected),
		"background": _selected_label(background_buttons, BACKGROUND_LABELS, "Coach"),
		"mode": _selected_label(mode_buttons, MODE_LABELS, "Career"),
		"difficulty": _selected_label(difficulty_buttons, DIFFICULTY_LABELS, "Normal"),
		"enabled_countries": _enabled_countries,
		"primary_country": _primary_country,
	}
	var response := IpcBridge.call_method("save_new_game_setup", params)
	if response.has("error"):
		message_label.text = response["error"]
		return
	var result: Dictionary = response["result"]
	message_label.text = ""
	_shell().show_screen(str(result.get("destination", "Career Team Selection")))
