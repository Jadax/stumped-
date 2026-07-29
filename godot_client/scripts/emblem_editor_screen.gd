extends Control
## Emblem editor screen — allows users to customise team emblems/logos.

@onready var title_label: Label = $Title
@onready var team_label: Label = $TeamLabel
@onready var shape_option: OptionButton = $Options/ShapeOption
@onready var icon_option: OptionButton = $Options/IconOption
@onready var primary_color: ColorRect = $Colors/PrimaryColor
@onready var secondary_color: ColorRect = $Colors/SecondaryColor
@onready var primary_button: Button = $Colors/PrimaryButton
@onready var secondary_button: Button = $Colors/SecondaryButton
@onready var save_button: Button = $Footer/SaveButton
@onready var back_button: Button = $Footer/BackButton

var _team_id: int = 0
var _emblem: Dictionary = {}


func _ready() -> void:
	shape_option.add_item("Shield")
	shape_option.add_item("Circle")
	shape_option.add_item("Diamond")
	shape_option.add_item("Hexagon")
	shape_option.add_item("Star")
	shape_option.add_item("Crest")
	shape_option.item_selected.connect(_on_shape_selected)
	icon_option.add_item("Star")
	icon_option.add_item("Lion")
	icon_option.add_item("Eagle")
	icon_option.add_item("Bat")
	icon_option.add_item("Ball")
	icon_option.add_item("Stump")
	icon_option.add_item("Crown")
	icon_option.add_item("Flame")
	icon_option.item_selected.connect(_on_icon_selected)
	primary_button.pressed.connect(_on_primary_pressed)
	secondary_button.pressed.connect(_on_secondary_pressed)
	save_button.pressed.connect(_on_save)
	back_button.pressed.connect(_on_back)
	refresh()


func _on_back() -> void:
	var shell := get_tree().get_first_node_in_group("shell")
	if shell:
		shell.show_screen("Club")


func refresh() -> void:
	var response := IpcBridge.call_method("get_team_emblem")
	if response.has("error"):
		title_label.text = "EMBLEM EDITOR — error: %s" % response["error"]
		return
	_emblem = response["result"]
	_update_ui()
	title_label.text = "EMBLEM EDITOR"
	var team_response := IpcBridge.call_method("get_dashboard")
	if not team_response.has("error"):
		team_label.text = team_response["result"].get("team", {}).get("name", "?")


func _update_ui() -> void:
	primary_color.color = Color.html(_emblem.get("primary_color", "#1a5276"))
	secondary_color.color = Color.html(_emblem.get("secondary_color", "#f39c12"))
	var shapes := ["shield", "circle", "diamond", "hexagon", "star", "crest"]
	var shape_idx := shapes.find(_emblem.get("shape", "shield"))
	shape_option.selected = shape_idx if shape_idx >= 0 else 0
	var icons := ["star", "lion", "eagle", "bat", "ball", "stump", "crown", "flame"]
	var icon_idx := icons.find(_emblem.get("icon", "star"))
	icon_option.selected = icon_idx if icon_idx >= 0 else 0


func _on_shape_selected(index: int) -> void:
	var shapes := ["shield", "circle", "diamond", "hexagon", "star", "crest"]
	_emblem["shape"] = shapes[index]


func _on_icon_selected(index: int) -> void:
	var icons := ["star", "lion", "eagle", "bat", "ball", "stump", "crown", "flame"]
	_emblem["icon"] = icons[index]


func _on_primary_pressed() -> void:
	var presets := ["#1a5276", "#27ae60", "#7d3c98", "#c0392b", "#f39c12", "#1abc9c"]
	var current: String = _emblem.get("primary_color", "#1a5276")
	var idx: int = presets.find(current)
	_emblem["primary_color"] = presets[(idx + 1) % presets.size()]
	primary_color.color = Color.html(_emblem["primary_color"])


func _on_secondary_pressed() -> void:
	var presets := ["#f39c12", "#f4d03f", "#1a5276", "#27ae60", "#000000", "#e74c3c"]
	var current: String = _emblem.get("secondary_color", "#f39c12")
	var idx: int = presets.find(current)
	_emblem["secondary_color"] = presets[(idx + 1) % presets.size()]
	secondary_color.color = Color.html(_emblem["secondary_color"])


func _on_save() -> void:
	var response := IpcBridge.call_method("set_team_emblem", {"emblem": _emblem})
	if response.has("error"):
		title_label.text = "EMBLEM EDITOR — save failed: %s" % response["error"]
		return
	title_label.text = "EMBLEM EDITOR — saved!"
