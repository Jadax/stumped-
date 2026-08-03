extends Control
## Player editor screen — allows editing player attributes, role, and contract.

const MAX_RENDERED_ROWS := 200

@onready var title_label: Label = $Title
@onready var search_edit: LineEdit = $SearchEdit
@onready var player_list: VBoxContainer = $Scroll/Players
@onready var editor_panel: PanelContainer = $Editor
@onready var name_edit: LineEdit = $Editor/Scroll/Fields/NameEdit
@onready var role_option: OptionButton = $Editor/Scroll/Fields/RoleOption
@onready var age_edit: LineEdit = $Editor/Scroll/Fields/AgeEdit
@onready var overall_edit: LineEdit = $Editor/Scroll/Fields/OverallEdit
@onready var potential_edit: LineEdit = $Editor/Scroll/Fields/PotentialEdit
@onready var save_button: Button = $Editor/Footer/SaveButton
@onready var cancel_button: Button = $Editor/Footer/CancelButton
@onready var back_button: Button = $Footer/BackButton

var _players: Array = []
var _selected_player: Dictionary = {}


func _ready() -> void:
	role_option.add_item("Batsman")
	role_option.add_item("Bowler")
	role_option.add_item("All-Rounder")
	role_option.add_item("Wicketkeeper")
	save_button.pressed.connect(_on_save)
	cancel_button.pressed.connect(_on_cancel)
	back_button.pressed.connect(_on_back)
	search_edit.text_changed.connect(func(_text): _render_player_list())
	editor_panel.visible = false
	refresh()


func _on_back() -> void:
	var shell := get_tree().get_first_node_in_group("shell")
	if shell:
		shell.show_screen("Squad")


func refresh() -> void:
	var response := IpcBridge.call_method("get_all_players_for_edit")
	if response.has("error"):
		title_label.text = "PLAYER EDITOR — error: %s" % response["error"]
		return
	_players = response["result"]
	title_label.text = "PLAYER EDITOR — %d players" % _players.size()
	_render_player_list()


## v4.24.0 fix: unconditionally building one row per player (~2500 in a
## full save) froze the UI for several seconds every time this screen
## opened — no pagination, no filtering, just raw node creation for the
## entire pool. Now only ever renders a search match (or the first
## MAX_RENDERED_ROWS as a starting point), so a normal open is instant and
## finding a specific player is actually faster than scrolling ever was.
func _render_player_list() -> void:
	for child in player_list.get_children():
		player_list.remove_child(child)
		child.queue_free()
	var query := search_edit.text.strip_edges().to_lower()
	var matches: Array = _players
	if not query.is_empty():
		matches = _players.filter(func(p): return query in str(p.get("name", "")).to_lower())
	var shown: Array = matches.slice(0, MAX_RENDERED_ROWS)
	if matches.size() > shown.size():
		var notice := Label.new()
		notice.text = "Showing %d of %d matches — refine your search to narrow further." % [shown.size(), matches.size()]
		notice.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		player_list.add_child(notice)
	for player in shown:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		var name_label := Label.new()
		name_label.text = str(player.get("name", "?"))
		name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(name_label)
		var role_label := Label.new()
		role_label.text = str(player.get("role", "?"))
		role_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		row.add_child(role_label)
		var ovr_label := Label.new()
		ovr_label.text = "OVR %d" % int(player.get("overall", 0))
		ovr_label.add_theme_color_override("font_color", AppTheme.GOLD)
		row.add_child(ovr_label)
		var edit_button := Button.new()
		edit_button.text = "EDIT"
		edit_button.custom_minimum_size = Vector2(60, 28)
		edit_button.pressed.connect(_on_edit_pressed.bind(player))
		row.add_child(edit_button)
		player_list.add_child(row)


func _on_edit_pressed(player: Dictionary) -> void:
	_selected_player = player
	name_edit.text = str(player.get("name", ""))
	var roles := ["Batsman", "Bowler", "All-Rounder", "Wicketkeeper"]
	role_option.selected = roles.find(str(player.get("role", "Batsman")))
	age_edit.text = str(player.get("age", 18))
	overall_edit.text = str(player.get("overall", 50))
	potential_edit.text = str(player.get("potential", 60))
	editor_panel.visible = true


func _on_save() -> void:
	var updates := {
		"name": name_edit.text,
		"role": role_option.get_item_text(role_option.selected),
		"age": int(age_edit.text),
		"overall": int(overall_edit.text),
		"potential": int(potential_edit.text),
	}
	var response := IpcBridge.call_method("update_player", {
		"player_id": _selected_player.get("id", 0),
		"updates": updates,
	})
	if response.has("error"):
		title_label.text = "PLAYER EDITOR — save failed: %s" % response["error"]
		return
	editor_panel.visible = false
	refresh()


func _on_cancel() -> void:
	editor_panel.visible = false
