extends Control
## Kit editor screen — allows users to customise team kit colours.

@onready var title_label: Label = $Title
@onready var team_label: Label = $TeamLabel
@onready var primary_color: ColorRect = $Colors/PrimaryColor
@onready var secondary_color: ColorRect = $Colors/SecondaryColor
@onready var accent_color: ColorRect = $Colors/AccentColor
@onready var primary_button: Button = $Colors/PrimaryButton
@onready var secondary_button: Button = $Colors/SecondaryButton
@onready var accent_button: Button = $Colors/AccentButton
@onready var preview_panel: PanelContainer = $Preview
@onready var save_button: Button = $Footer/SaveButton
@onready var back_button: Button = $Footer/BackButton

var _team_id: int = 0
var _kit: Dictionary = {}


func _ready() -> void:
	primary_button.pressed.connect(_on_primary_pressed)
	secondary_button.pressed.connect(_on_secondary_pressed)
	accent_button.pressed.connect(_on_accent_pressed)
	save_button.pressed.connect(_on_save)
	back_button.pressed.connect(_on_back)
	refresh()


func _on_back() -> void:
	var shell := get_tree().get_first_node_in_group("shell")
	if shell:
		shell.show_screen("Club")


func refresh() -> void:
	var response := IpcBridge.call_method("get_team_kit")
	if response.has("error"):
		title_label.text = "KIT EDITOR — error: %s" % response["error"]
		return
	_kit = response["result"]
	_update_colors()
	title_label.text = "KIT EDITOR"
	var team_response := IpcBridge.call_method("get_dashboard")
	if not team_response.has("error"):
		team_label.text = team_response["result"].get("team", {}).get("name", "?")


func _update_colors() -> void:
	primary_color.color = Color.html(_kit.get("primary", "#1a5276"))
	secondary_color.color = Color.html(_kit.get("secondary", "#ffffff"))
	accent_color.color = Color.html(_kit.get("accent", "#f39c12"))


func _on_primary_pressed() -> void:
	var presets := ["#1a5276", "#27ae60", "#7d3c98", "#c0392b", "#f39c12", "#1abc9c"]
	var current: String = _kit.get("primary", "#1a5276")
	var idx: int = presets.find(current)
	_kit["primary"] = presets[(idx + 1) % presets.size()]
	_update_colors()


func _on_secondary_pressed() -> void:
	var presets := ["#ffffff", "#f4d03f", "#1a5276", "#27ae60", "#000000", "#f39c12"]
	var current: String = _kit.get("secondary", "#ffffff")
	var idx: int = presets.find(current)
	_kit["secondary"] = presets[(idx + 1) % presets.size()]
	_update_colors()


func _on_accent_pressed() -> void:
	var presets := ["#f39c12", "#27ae60", "#1a5276", "#e74c3c", "#f4d03f", "#9b59b6"]
	var current: String = _kit.get("accent", "#f39c12")
	var idx: int = presets.find(current)
	_kit["accent"] = presets[(idx + 1) % presets.size()]
	_update_colors()


func _on_save() -> void:
	var response := IpcBridge.call_method("set_team_kit", {"kit": _kit})
	if response.has("error"):
		title_label.text = "KIT EDITOR — save failed: %s" % response["error"]
		return
	title_label.text = "KIT EDITOR — saved!"
