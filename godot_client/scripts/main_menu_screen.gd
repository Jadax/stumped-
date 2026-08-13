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
	queue_redraw()
	resized.connect(queue_redraw)
	new_game_button.pressed.connect(_on_new_game_pressed)
	load_game_button.pressed.connect(_on_load_game_pressed)
	settings_button.pressed.connect(func(): _shell().show_screen("Settings"))
	help_button.pressed.connect(func(): _shell().show_screen("Help"))
	credits_button.pressed.connect(_on_credits_pressed)
	exit_button.pressed.connect(func(): get_tree().quit())
	for button in [new_game_button, load_game_button, settings_button, help_button, credits_button, exit_button]:
		AppTheme.enhance_button(button)
	overlay_close_button.pressed.connect(func(): overlay.visible = false)
	var response := IpcBridge.call_method("ping")
	if not response.has("error"):
		version_label.text = "v%s  •  F11 Fullscreen" % str(response["result"].get("version", "?"))


func _shell() -> Node:
	return get_tree().get_first_node_in_group("shell")


func _draw() -> void:
	# Original vector stadium environment: stands, floodlights, and a layered
	# outfield give the opening screen immediate cricket identity without
	# depending on licensed photography.
	var w := size.x
	var h := size.y
	draw_rect(Rect2(0, h * 0.68, w, h * 0.32), Color("#0f281c"))
	draw_rect(Rect2(0, h * 0.77, w, h * 0.23), Color("#123b26"))
	for i in range(12):
		var x := float(i) / 11.0 * w
		draw_line(Vector2(x, h * 0.68), Vector2(x + 120.0, h), Color(0.12, 0.38, 0.22, 0.32), 2.0, true)
	for i in range(9):
		var x := 80.0 + float(i) * (w - 160.0) / 8.0
		draw_rect(Rect2(x, h * 0.55, 56, 74), Color("#1d2c36"))
		draw_rect(Rect2(x + 8, h * 0.58, 40, 5), AppTheme.GOLD)
	for x in [w * 0.56, w * 0.82]:
		draw_line(Vector2(x, h * 0.18), Vector2(x - 18, h * 0.68), AppTheme.TEXT_MUTED, 3.0, true)
		draw_circle(Vector2(x, h * 0.16), 22.0, Color("#dfe8df"), true, -1.0, true)
		draw_circle(Vector2(x, h * 0.16), 12.0, Color("#fff8c7"), true, -1.0, true)
	# Original cricket identity mark: ball, seam and three stumps behind the
	# title.  It stays vector and scales cleanly on 720p through 4K.
	var mark := Vector2(690.0, 145.0)
	draw_circle(mark, 34.0, Color("#b63b3b"), true, -1.0, true)
	draw_arc(mark, 25.0, -1.1, 1.1, 24, Color("#f0f6fc"), 2.0, true)
	for i in range(3):
		var sx := mark.x + 64.0 + float(i) * 12.0
		draw_line(Vector2(sx, mark.y - 28.0), Vector2(sx, mark.y + 28.0), Color("#e3b341"), 4.0, true)
	draw_line(Vector2(mark.x + 59.0, mark.y - 27.0), Vector2(mark.x + 89.0, mark.y - 27.0), Color("#e3b341"), 3.0, true)
	draw_line(Vector2(mark.x + 59.0, mark.y - 18.0), Vector2(mark.x + 89.0, mark.y - 18.0), Color("#e3b341"), 3.0, true)


## v0.90.0: NEW GAME now always starts a genuinely new save slot (via
## create_save) instead of reconfiguring whatever save happened to be
## active — previously there was only ever one database, so "New Game"
## really meant "overwrite the current career's manager identity".
func _on_new_game_pressed() -> void:
	var response := IpcBridge.call_method("create_save", {"display_name": "New Career"})
	if response.has("error"):
		push_error("MainMenuScreen: %s" % response["error"])
		return
	_shell().show_screen(str(response["result"].get("destination", "New Game Setup")))


## v0.90.0: real multi-save-slot system — Load Game now shows an actual
## list of saves to pick from instead of just continuing whatever the
## single existing database held.
func _on_load_game_pressed() -> void:
	_shell().show_screen("Load Game")


func _on_credits_pressed() -> void:
	overlay_title.text = "CREDITS"
	overlay_body.text = CREDITS_TEXT
	overlay.visible = true
