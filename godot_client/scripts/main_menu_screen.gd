extends Control
## Ports src/views/screens/main_menu.py's field set: New Game / Load Game /
## Settings / Help / Credits / Exit. First screen shown on every launch,
## chrome-less (shell.gd hides sidebar/header for STARTUP_SCREEN_NAMES),
## matching main.py's CricketManagerApp always booting to "Main Menu".

@onready var new_game_button: Button = $Menu/NewGameButton
@onready var load_game_button: Button = $Menu/LoadGameButton
@onready var settings_button: Button = $Menu/SettingsButton
@onready var help_button: Button = $Menu/HelpButton
@onready var credits_button: Button = $Menu/CreditsButton
@onready var exit_button: Button = $Menu/ExitButton
@onready var version_label: Label = $VersionLabel
@onready var overlay: Control = $Overlay
@onready var overlay_title: Label = $Overlay/Card/Box/OverlayTitle
@onready var overlay_body: Label = $Overlay/Card/Box/OverlayBody
@onready var overlay_close_button: Button = $Overlay/Card/Box/CloseButton

const CREDITS_TEXT := "Design and development: ASTRAIVA (Pty) Ltd.\nBuilt with Godot Engine and Python/SQLite.\nAll visual motifs are original artwork. No real player photos or club logos are used."


func _ready() -> void:
	new_game_button.pressed.connect(_on_new_game_pressed)
	load_game_button.pressed.connect(_on_load_game_pressed)
	settings_button.pressed.connect(func(): _shell().show_screen("Settings"))
	help_button.pressed.connect(func(): _shell().show_screen("Help"))
	credits_button.pressed.connect(_on_credits_pressed)
	exit_button.pressed.connect(func(): get_tree().quit())
	overlay_close_button.pressed.connect(func(): overlay.visible = false)
	var response := IpcBridge.call_method("ping")
	if not response.has("error"):
		version_label.text = "v%s  •  F11 Fullscreen" % str(response["result"].get("version", "?"))


func _shell() -> Node:
	return get_tree().get_first_node_in_group("shell")


func _on_new_game_pressed() -> void:
	_shell().show_screen("New Game Setup")


## No multi-slot save system exists (single persistent database), so "Load
## Game" is simply continuing straight into the already-loaded save —
## mirrors GameController.load_existing_game()'s toast + Dashboard navigate.
func _on_load_game_pressed() -> void:
	_shell().show_screen("Dashboard")


func _on_credits_pressed() -> void:
	overlay_title.text = "CREDITS"
	overlay_body.text = CREDITS_TEXT
	overlay.visible = true
