extends Control
## Ports ui/settings.py's field set to Godot at the data layer (see
## ipc_server.py's get_user_settings/update_user_settings docstring for why
## these don't yet drive live Godot audio/theme effects — no such systems
## exist in this client yet).

const SPEEDS := ["Normal", "Fast", "Instant"]
const RESOLUTIONS := ["1280x720", "1600x900", "1920x1080", "Fullscreen"]
const AUTOSAVES := ["Never", "Monthly", "Seasonal"]

@onready var rows_box: VBoxContainer = $Card/Scroll/Rows
@onready var back_button: Button = $Footer/BackButton
@onready var save_button: Button = $Footer/SaveButton
@onready var message_label: Label = $Footer/Message

var _settings: Dictionary = {}
var _currencies: Array = []
var _cycle_buttons: Dictionary = {}
var _volume_slider: HSlider


func _ready() -> void:
	back_button.pressed.connect(_on_back_pressed)
	save_button.pressed.connect(_on_save_pressed)
	_load_settings()


## Settings is reachable both pre-career (Main Menu) and in-career (sidebar
## footer, always chrome-less per shell.gd's STARTUP_SCREEN_NAMES) — Back
## should return wherever makes sense for each, not always Main Menu.
func _on_back_pressed() -> void:
	var response := IpcBridge.call_method("get_dashboard")
	if not response.has("error") and response.get("result", {}).get("team"):
		_shell().show_screen("Dashboard")
	else:
		_shell().show_screen("Main Menu")


func _shell() -> Node:
	return get_tree().get_first_node_in_group("shell")


func _load_settings() -> void:
	var response := IpcBridge.call_method("get_user_settings")
	if response.has("error"):
		message_label.text = response["error"]
		return
	_settings = response["result"].get("settings", {})
	_currencies = response["result"].get("currencies", ["GBP"])
	_build_rows()


func _build_rows() -> void:
	for child in rows_box.get_children():
		rows_box.remove_child(child)
		child.queue_free()
	_cycle_buttons.clear()
	_add_dropdown_row("game_speed", "Game Speed", SPEEDS, str(_settings.get("game_speed", "Normal")))
	_add_toggle_row("sound_on", "Crowd Sound", bool(int(_settings.get("sound_on", 1))))
	_add_volume_row()
	_add_dropdown_row("resolution", "Resolution", RESOLUTIONS, str(_settings.get("resolution", "1280x720")))
	_add_dropdown_row("currency", "Currency", _currencies, str(_settings.get("currency", "GBP")))
	_add_dropdown_row("auto_save_frequency", "Auto-save", AUTOSAVES, str(_settings.get("auto_save_frequency", "Monthly")))
	_add_toggle_row("reduced_motion", "Reduced Motion", bool(int(_settings.get("reduced_motion", 0))))
	_add_toggle_row("colour_blind_mode", "Colour-blind Glyphs", bool(int(_settings.get("colour_blind_mode", 1))))
	_add_cycle_row("ui_scale", "UI Scale", ["1.0", "1.1", "1.2"], "%.1f" % float(_settings.get("ui_scale", 1.0) or 1.0))


## Real dropdowns for fields with a fixed set of named options (speed,
## resolution, currency, auto-save frequency) — replaces the old
## click-to-cycle buttons the user flagged as reading like a debug form.
func _add_dropdown_row(key: String, label_text: String, options: Array, current: String) -> void:
	var row := HBoxContainer.new()
	var label := Label.new()
	label.text = label_text
	label.size_flags_horizontal = SIZE_EXPAND_FILL
	row.add_child(label)
	var dropdown := OptionButton.new()
	dropdown.custom_minimum_size = Vector2(220, 34)
	for option in options:
		dropdown.add_item(str(option))
	dropdown.selected = max(0, options.find(current))
	row.add_child(dropdown)
	rows_box.add_child(row)
	_cycle_buttons[key] = dropdown


func _add_cycle_row(key: String, label_text: String, options: Array, current: String) -> void:
	var row := HBoxContainer.new()
	var label := Label.new()
	label.text = label_text
	label.size_flags_horizontal = SIZE_EXPAND_FILL
	row.add_child(label)
	var button := Button.new()
	button.custom_minimum_size = Vector2(220, 34)
	var start_index: int = max(0, options.find(current))
	button.set_meta("options", options)
	button.set_meta("index", start_index)
	button.text = "%s: %s" % [label_text.to_upper(), options[start_index]]
	button.pressed.connect(_on_cycle_pressed.bind(button, label_text))
	row.add_child(button)
	rows_box.add_child(row)
	_cycle_buttons[key] = button


func _on_cycle_pressed(button: Button, label_text: String) -> void:
	var options: Array = button.get_meta("options")
	var index: int = (int(button.get_meta("index")) + 1) % options.size()
	button.set_meta("index", index)
	button.text = "%s: %s" % [label_text.to_upper(), options[index]]


func _add_toggle_row(key: String, label_text: String, current: bool) -> void:
	var row := HBoxContainer.new()
	var label := Label.new()
	label.text = label_text
	label.size_flags_horizontal = SIZE_EXPAND_FILL
	row.add_child(label)
	var button := Button.new()
	button.custom_minimum_size = Vector2(220, 34)
	button.toggle_mode = true
	button.button_pressed = current
	button.text = "%s: %s" % [label_text.to_upper(), "ON" if current else "OFF"]
	button.toggled.connect(func(pressed): button.text = "%s: %s" % [label_text.to_upper(), "ON" if pressed else "OFF"])
	row.add_child(button)
	rows_box.add_child(row)
	_cycle_buttons[key] = button


func _add_volume_row() -> void:
	var row := HBoxContainer.new()
	var label := Label.new()
	label.text = "Master Volume"
	label.size_flags_horizontal = SIZE_EXPAND_FILL
	row.add_child(label)
	_volume_slider = HSlider.new()
	_volume_slider.custom_minimum_size = Vector2(220, 34)
	_volume_slider.min_value = 0
	_volume_slider.max_value = 100
	_volume_slider.step = 5
	_volume_slider.value = float(_settings.get("master_volume", 70))
	row.add_child(_volume_slider)
	rows_box.add_child(row)


func _on_save_pressed() -> void:
	var params := {
		"game_speed": _cycle_value("game_speed"),
		"sound_on": 1 if _cycle_buttons["sound_on"].button_pressed else 0,
		"master_volume": int(_volume_slider.value),
		"resolution": _cycle_value("resolution"),
		"currency": _cycle_value("currency"),
		"auto_save_frequency": _cycle_value("auto_save_frequency"),
		"reduced_motion": 1 if _cycle_buttons["reduced_motion"].button_pressed else 0,
		"colour_blind_mode": 1 if _cycle_buttons["colour_blind_mode"].button_pressed else 0,
		"ui_scale": float(_cycle_value("ui_scale")),
	}
	var response := IpcBridge.call_method("update_user_settings", params)
	if response.has("error"):
		message_label.text = response["error"]
		return
	message_label.text = "Settings saved"


func _cycle_value(key: String) -> String:
	var control: Control = _cycle_buttons[key]
	if control is OptionButton:
		var dropdown := control as OptionButton
		return dropdown.get_item_text(dropdown.selected)
	var button := control as Button
	var options: Array = button.get_meta("options")
	return str(options[int(button.get_meta("index"))])
