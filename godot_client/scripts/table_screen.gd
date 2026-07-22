extends Control
## Generic reusable list/table screen — most of the pygame client's simple
## data screens (Staff roster, Transfer market, Finances, Facilities,
## Honours, Inbox) are "fetch a list, show it in columns" exactly like
## ui/widgets/datatable.py's DataTable is reused across those pygame
## screens. Configure with `configure()` right after instancing, before
## adding to the tree, so _ready() has real settings to work with.

const HOVER_CARD_SCENE := preload("res://scenes/player_hover_card.tscn")
const PROFILE_MODAL_SCENE := preload("res://scenes/player_profile_modal.tscn")

@onready var title_label: Label = $Title
@onready var row_list: VBoxContainer = $ScrollContainer/RowList

var _hover_card: PlayerHoverCard = null
var _profile_modal: PlayerProfileModal = null

var screen_title: String = "SCREEN"
var ipc_method: String = ""
var ipc_params: Dictionary = {}
var rows_key: String = "rows"
var columns: Array = []  # [{"key": "name", "header": "Name", "width": 160}]

## Optional: clicking anywhere on a data row calls another IPC method.
## Empty dict = rows aren't whole-row-clickable. Mutually exclusive in
## practice with row_buttons (Inbox/Transfers-browse use this; Offers uses
## row_buttons instead, since it needs two distinct actions per row).
## {"method": "mark_message_read", "params_from_row": {"message_id": "id"}, "params_fixed": {}}
var row_action: Dictionary = {}

## Optional: explicit action buttons appended to the end of each data row,
## for screens needing more than one action per row (e.g. Accept/Reject).
## [{"label": "ACCEPT", "method": "resolve_transfer_offer",
##   "params_from_row": {"offer_id": "id"}, "params_fixed": {"accept": true}}, ...]
var row_buttons: Array = []

## Optional: name of a boolean-ish field (e.g. "read") that dims a row when
## true — used by Inbox to fade already-read messages.
var dim_when_key: String = ""

## Optional: additional tabs beyond the default "GENERAL INFO" view
## (the columns passed to configure() are always tab 0) — same IPC method
## and rows_key for every tab, just a different column set, so switching
## tabs never needs a second network round trip. Mirrors the reference
## screenshots' "General Info / Stats / Injuries"-style sub-navigation.
## [{"label": "ATTRIBUTES", "columns": [...]}]
var extra_tabs: Array = []
var _base_columns: Array = []
var _base_row_buttons: Array = []
var _base_row_action: Dictionary = {}
var _tab_bar: HBoxContainer = null
var _tab_buttons: Array = []
var active_tab: int = 0


func configure(p_title: String, p_method: String, p_columns: Array, p_rows_key: String = "rows",
			p_params: Dictionary = {}, p_row_action: Dictionary = {}, p_dim_when_key: String = "",
			p_row_buttons: Array = [], p_extra_tabs: Array = []) -> void:
	screen_title = p_title
	ipc_method = p_method
	columns = p_columns
	_base_columns = p_columns
	rows_key = p_rows_key
	ipc_params = p_params
	row_action = p_row_action
	_base_row_action = p_row_action
	dim_when_key = p_dim_when_key
	row_buttons = p_row_buttons
	_base_row_buttons = p_row_buttons
	extra_tabs = p_extra_tabs


func _ready() -> void:
	if not extra_tabs.is_empty():
		_build_tab_bar()
	_hover_card = HOVER_CARD_SCENE.instantiate()
	add_child(_hover_card)
	_profile_modal = PROFILE_MODAL_SCENE.instantiate()
	add_child(_profile_modal)
	refresh()


## Ports ui/widgets/quick_card.py's row-hover behaviour: a compact summary
## card follows the cursor while hovering a player row, hidden again on
## mouse-exit or whenever the row list is rebuilt by refresh().
func _on_row_mouse_entered(row_data: Dictionary) -> void:
	_hover_card.show_for(row_data, get_global_mouse_position(), get_viewport_rect().size)


func _on_row_mouse_exited() -> void:
	_hover_card.hide_card()


## Ports ui/player_modals.py's PlayerDetailModal entry point: clicking a
## player row (on screens where the click isn't already claimed by a
## row_action) opens a single-view profile — scoped down from pygame's
## six-tab modal, see player_profile_modal.gd.
func _on_row_click_profile(event: InputEvent, row_data: Dictionary) -> void:
	if not (event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT):
		return
	_hover_card.hide_card()
	_profile_modal.show_for(row_data)


func _build_tab_bar() -> void:
	_tab_bar = HBoxContainer.new()
	_tab_bar.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	_tab_bar.offset_left = 24
	_tab_bar.offset_top = 52
	_tab_bar.offset_right = -24
	_tab_bar.add_theme_constant_override("separation", 24)
	add_child(_tab_bar)
	var scroll: Control = $ScrollContainer
	scroll.offset_top = 100

	var all_tabs := _all_tabs()
	for i in range(all_tabs.size()):
		var button := Button.new()
		button.text = all_tabs[i]["label"]
		button.focus_mode = Control.FOCUS_NONE
		button.custom_minimum_size = Vector2(0, 28)
		button.pressed.connect(_select_tab.bind(i))
		_tab_bar.add_child(button)
		_tab_buttons.append(button)
	_style_tabs()


## Tab 0 is always the columns/row_action/row_buttons passed to configure()
## directly; extra tabs may override row_action/row_buttons independently
## of columns (e.g. Selection's AGGRESSION tab needs different buttons,
## not just different columns) — falling back to empty when a tab doesn't
## specify them, since most tabs (Squad's ATTRIBUTES) are read-only.
func _all_tabs() -> Array:
	return [{"label": "GENERAL INFO", "columns": _base_columns,
			"row_buttons": _base_row_buttons, "row_action": _base_row_action}] + extra_tabs


func _select_tab(index: int) -> void:
	if index == active_tab:
		return
	active_tab = index
	var tab: Dictionary = _all_tabs()[index]
	columns = tab["columns"]
	row_buttons = tab.get("row_buttons", [])
	row_action = tab.get("row_action", {})
	_style_tabs()
	refresh()


## FM26-style underline tabs — no filled box on either state (a bordered
## pill read as too heavy/"sharp" next to the rest of the flat UI); the
## active tab is just brighter text with a coloured underline, inactive
## tabs are muted with a faint hover fill, matching the reference
## screenshots' sub-navigation (e.g. player profile's Overview/Personal/
## Performance tabs).
func _style_tabs() -> void:
	for i in range(_tab_buttons.size()):
		var button: Button = _tab_buttons[i]
		var active := i == active_tab
		var box := StyleBoxFlat.new()
		box.bg_color = Color(0, 0, 0, 0)
		box.content_margin_left = 4
		box.content_margin_right = 4
		box.content_margin_top = 6
		box.content_margin_bottom = 8
		box.border_width_bottom = 2
		box.border_color = AppTheme.GOLD if active else Color(0, 0, 0, 0)
		var hover := box.duplicate()
		hover.bg_color = AppTheme.HOVER
		button.add_theme_stylebox_override("normal", box)
		button.add_theme_stylebox_override("hover", hover)
		button.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY if active else AppTheme.TEXT_MUTED)
		button.add_theme_color_override("font_hover_color", AppTheme.TEXT_PRIMARY)
		button.add_theme_font_size_override("font_size", 13)


func refresh() -> void:
	title_label.text = screen_title
	if _hover_card:
		_hover_card.hide_card()
	if _profile_modal:
		_profile_modal.hide_modal()
	var response := IpcBridge.call_method(ipc_method, ipc_params)
	# remove_child() (not just queue_free()) so the old rows are gone from
	# row_list's children *immediately* — queue_free() alone defers actual
	# removal to end-of-frame, so a caller reading row_list.get_child(N)
	# right after refresh() would still see the stale pre-refresh row
	# sitting ahead of the freshly-added ones.
	for child in row_list.get_children():
		row_list.remove_child(child)
		child.queue_free()
	if response.has("error"):
		title_label.text = "%s — backend error: %s" % [screen_title, response["error"]]
		push_error("TableScreen(%s): %s" % [screen_title, response["error"]])
		return
	var rows: Array = response["result"].get(rows_key, [])
	title_label.text = "%s — %d" % [screen_title, rows.size()]
	_add_row(_header_values(), true, {})
	for row in rows:
		var values := []
		for col in columns:
			values.append(JsonFormat.value(row.get(col["key"], "")))
		_add_row(values, false, row)


func _header_values() -> Array:
	var values := []
	for col in columns:
		values.append(col["header"])
	return values


func _add_row(values: Array, is_header: bool, row_data: Dictionary) -> void:
	var panel := PanelContainer.new()
	# row_list.get_child_count() at call time is the row's own index (header
	# is index 0), so odd/even data rows zebra-stripe automatically.
	var data_index := row_list.get_child_count() - 1
	var box := StyleBoxFlat.new()
	box.content_margin_left = 12
	box.content_margin_right = 12
	box.content_margin_top = 6
	box.content_margin_bottom = 6
	if is_header:
		box.bg_color = AppTheme.ACTIVE
	elif data_index % 2 == 0:
		box.bg_color = AppTheme.CARD
	else:
		box.bg_color = AppTheme.SURFACE
	panel.add_theme_stylebox_override("panel", box)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	var dim := not is_header and not dim_when_key.is_empty() and bool(row_data.get(dim_when_key, false))
	for i in range(values.size()):
		var width: int = columns[i].get("width", 160) if i < columns.size() else 160
		var is_pill: bool = not is_header and i < columns.size() and bool(columns[i].get("pill", false)) and not str(values[i]).is_empty()
		var is_flag: bool = not is_header and i < columns.size() and bool(columns[i].get("flag", false))
		var is_bar: bool = not is_header and i < columns.size() and bool(columns[i].get("bar", false)) and str(values[i]).is_valid_float()
		if is_bar:
			var cell := Control.new()
			cell.custom_minimum_size = Vector2(width, 0)
			cell.add_child(_make_bar(width, float(values[i])))
			row.add_child(cell)
			continue
		if is_flag:
			var cell := Control.new()
			cell.custom_minimum_size = Vector2(width, 0)
			var texture := AppTheme.flag_texture(str(values[i]))
			if texture:
				var rect := TextureRect.new()
				rect.texture = texture
				rect.custom_minimum_size = Vector2(24, 16)
				rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
				rect.stretch_mode = TextureRect.STRETCH_SCALE
				cell.add_child(rect)
			row.add_child(cell)
			continue
		if is_pill:
			var cell := Control.new()
			cell.custom_minimum_size = Vector2(width, 0)
			cell.add_child(_make_pill(str(values[i])))
			row.add_child(cell)
			continue
		var label := Label.new()
		label.text = str(values[i])
		label.custom_minimum_size = Vector2(width, 0)
		var is_muted: bool = not is_header and i < columns.size() and bool(columns[i].get("muted", false))
		if is_header:
			label.add_theme_color_override("font_color", AppTheme.GOLD)
			label.add_theme_font_size_override("font_size", 12)
		elif dim or is_muted:
			label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
			if is_muted:
				label.add_theme_font_size_override("font_size", 12)
		else:
			label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
		row.add_child(label)
	if not is_header and not row_action.is_empty():
		row.mouse_filter = Control.MOUSE_FILTER_STOP
		row.gui_input.connect(_on_row_gui_input.bind(row_data))
	if not is_header and PlayerHoverCard.is_player_row(row_data):
		row.mouse_filter = Control.MOUSE_FILTER_STOP
		row.mouse_entered.connect(_on_row_mouse_entered.bind(row_data))
		row.mouse_exited.connect(_on_row_mouse_exited)
		# row_action (e.g. Inbox's mark-read, Selection's toggle-XI) already
		# claims left-click on its screens, so click-to-profile only applies
		# where nothing else owns the click (Squad, Youth Academy).
		if row_action.is_empty():
			row.gui_input.connect(_on_row_click_profile.bind(row_data))
	if not is_header:
		for spec in row_buttons:
			var button := Button.new()
			button.text = spec.get("label", "GO")
			button.custom_minimum_size = Vector2(spec.get("width", 90), 0)
			button.add_theme_font_size_override("font_size", 12)
			button.pressed.connect(_on_row_button_pressed.bind(spec, row_data))
			row.add_child(button)
	panel.add_child(row)
	row_list.add_child(panel)


## A small horizontal bar meter (0-100 stats like form/morale) with a
## coloured fill tier and the raw number alongside it — mirrors the
## reference screenshots' form/confidence meters, instead of a bare number.
func _make_bar(width: int, value: float) -> Control:
	var container := Control.new()
	container.custom_minimum_size = Vector2(width, 18)
	var track_width: float = max(10.0, width - 32)
	var track := ColorRect.new()
	track.color = AppTheme.BORDER
	track.position = Vector2(0, 8)
	track.size = Vector2(track_width, 4)
	container.add_child(track)
	var fill := ColorRect.new()
	fill.color = AppTheme.attribute_colour(value)
	fill.position = Vector2(0, 8)
	fill.size = Vector2(clampf(value / 100.0, 0.0, 1.0) * track_width, 4)
	container.add_child(fill)
	var label := Label.new()
	label.text = str(int(value))
	label.add_theme_font_size_override("font_size", 11)
	label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	label.position = Vector2(track_width + 6, -2)
	container.add_child(label)
	return container


## A small coloured capsule badge for role/status-style columns — mirrors
## the coloured role tags (BAT/BOWL/WK/AR) in the reference cricket-manager
## screenshots, instead of showing role names as plain text like every
## other column.
func _make_pill(value: String) -> PanelContainer:
	var pill := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.role_colour(value)
	box.set_corner_radius_all(10)
	box.content_margin_left = 10
	box.content_margin_right = 10
	box.content_margin_top = 2
	box.content_margin_bottom = 2
	pill.add_theme_stylebox_override("panel", box)
	var label := Label.new()
	label.text = value
	label.add_theme_font_size_override("font_size", 11)
	label.add_theme_color_override("font_color", AppTheme.BACKGROUND)
	pill.add_child(label)
	return pill


func _on_row_gui_input(event: InputEvent, row_data: Dictionary) -> void:
	if not (event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT):
		return
	_dispatch(row_action, row_data)


func _on_row_button_pressed(spec: Dictionary, row_data: Dictionary) -> void:
	_dispatch(spec, row_data)


func _dispatch(action: Dictionary, row_data: Dictionary) -> void:
	var params: Dictionary = action.get("params_fixed", {}).duplicate()
	for param_name in action.get("params_from_row", {}):
		params[param_name] = row_data.get(action["params_from_row"][param_name])
	var response := IpcBridge.call_method(action["method"], params)
	refresh()
	# A failed action (e.g. "an upgrade is already in progress") must not
	# look like it silently succeeded just because the screen still
	# rendered fine on refresh — surface it on the title like every other
	# backend-error path in this file does.
	if response.has("error"):
		title_label.text = "%s — action failed: %s" % [screen_title, response["error"]]
		push_error("TableScreen(%s) action %s failed: %s" % [screen_title, action.get("method", "?"), response["error"]])
