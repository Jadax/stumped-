extends Control
## Player comparison — two squad members side by side, every attribute
## group as bars, the stronger value of each pair highlighted.
##
## v5.3.0: the scene root shipped `visible = false` and was only ever shown
## by show_comparison(), which no navigation path called — the Compare tab
## rendered a completely blank page. It is now a self-contained screen with
## a player picker on each side.

const GROUPS := ["batting", "bowling", "fielding", "mental"]

@onready var title_label: Label = $Title
@onready var player1_panel: PanelContainer = $Players/Player1
@onready var player2_panel: PanelContainer = $Players/Player2
@onready var compare_button: Button = $Footer/CompareButton
@onready var back_button: Button = $Footer/BackButton

var _players: Array = []
var _player1: Dictionary = {}
var _player2: Dictionary = {}
var _pickers: Array = []


func _ready() -> void:
	visible = true
	compare_button.visible = false
	back_button.pressed.connect(_on_back)
	var response := IpcBridge.call_method("get_squad")
	if response.has("error"):
		title_label.text = "PLAYER COMPARISON — backend error: %s" % response["error"]
		return
	_players = response["result"].get("players", [])
	_players.sort_custom(func(a, b): return int(a.get("overall", 0)) > int(b.get("overall", 0)))
	if _players.size() < 2:
		title_label.text = "PLAYER COMPARISON — need at least two players"
		return
	for side in range(2):
		var picker := OptionButton.new()
		for player in _players:
			picker.add_item("%s  (%s, OVR %d)" % [player.get("name", "?"), player.get("role", "?"), int(player.get("overall", 0))])
		picker.select(side)
		picker.item_selected.connect(_on_pick.bind(side))
		_pickers.append(picker)
	_player1 = _players[0]
	_player2 = _players[1]
	_render_comparison()


func _on_pick(index: int, side: int) -> void:
	if side == 0:
		_player1 = _players[index]
	else:
		_player2 = _players[index]
	_render_comparison()


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
	_render_player_card(_player1, _player2, player1_panel, 0)
	_render_player_card(_player2, _player1, player2_panel, 1)


func _render_player_card(player: Dictionary, other: Dictionary, panel: PanelContainer, side: int) -> void:
	var box := panel.get_node_or_null("VBox")
	if not box:
		return
	for child in box.get_children():
		box.remove_child(child)
		if side < _pickers.size() and child == _pickers[side]:
			continue
		child.queue_free()
	if side < _pickers.size():
		box.add_child(_pickers[side])
	var name_label := Label.new()
	name_label.text = str(player.get("name", "?"))
	name_label.add_theme_font_size_override("font_size", 18)
	name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	box.add_child(name_label)
	var meta_label := Label.new()
	meta_label.text = "%s  •  %s yrs  •  %s  •  OVR %d  •  POT %d" % [
		str(player.get("role", "?")), str(int(player.get("age", 0))), str(player.get("nationality", "?")),
		int(player.get("overall", 0)), int(player.get("potential", 0))]
	meta_label.add_theme_font_size_override("font_size", 12)
	meta_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	box.add_child(meta_label)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(scroll)
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 3)
	scroll.add_child(list)
	for group in GROUPS:
		var attrs: Dictionary = player.get(group, {}) if player.get(group) is Dictionary else {}
		var rival: Dictionary = other.get(group, {}) if other.get(group) is Dictionary else {}
		if attrs.is_empty():
			continue
		var heading := Label.new()
		heading.text = group.to_upper()
		heading.add_theme_font_size_override("font_size", 11)
		heading.add_theme_color_override("font_color", AppTheme.ACCENT)
		list.add_child(heading)
		for attr in attrs:
			var value := float(attrs[attr])
			var row := HBoxContainer.new()
			row.add_theme_constant_override("separation", 8)
			var attr_label := Label.new()
			attr_label.text = str(attr).capitalize()
			attr_label.custom_minimum_size = Vector2(130, 0)
			attr_label.add_theme_font_size_override("font_size", 11)
			var better := rival.has(attr) and value > float(rival[attr])
			attr_label.add_theme_color_override("font_color", AppTheme.HEADER_GREEN if better else AppTheme.TEXT_SECONDARY)
			row.add_child(attr_label)
			row.add_child(AppTheme.make_bar_meter(150.0, value, 11))
			list.add_child(row)
	var status_row := HBoxContainer.new()
	status_row.add_theme_constant_override("separation", 8)
	status_row.add_child(AppTheme.make_status_chip("FORM", int(player.get("form", 50))))
	var mental: Dictionary = player.get("mental", {}) if player.get("mental") is Dictionary else {}
	status_row.add_child(AppTheme.make_status_chip("MORALE", int(mental.get("morale", 50))))
	box.add_child(status_row)
