extends Control
## Generic reusable list/table screen — most of the pygame client's simple
## data screens (Staff roster, Transfer market, Finances, Facilities,
## Honours, Inbox) are "fetch a list, show it in columns" exactly like
## ui/widgets/datatable.py's DataTable is reused across those pygame
## screens. Configure with `configure()` right after instancing, before
## adding to the tree, so _ready() has real settings to work with.

@onready var title_label: Label = $Title
@onready var row_list: VBoxContainer = $ScrollContainer/RowList

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


func configure(p_title: String, p_method: String, p_columns: Array, p_rows_key: String = "rows",
			p_params: Dictionary = {}, p_row_action: Dictionary = {}, p_dim_when_key: String = "",
			p_row_buttons: Array = []) -> void:
	screen_title = p_title
	ipc_method = p_method
	columns = p_columns
	rows_key = p_rows_key
	ipc_params = p_params
	row_action = p_row_action
	dim_when_key = p_dim_when_key
	row_buttons = p_row_buttons


func _ready() -> void:
	refresh()


func refresh() -> void:
	title_label.text = screen_title
	var response := IpcBridge.call_method(ipc_method, ipc_params)
	for child in row_list.get_children():
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
			values.append(str(row.get(col["key"], "")))
		_add_row(values, false, row)


func _header_values() -> Array:
	var values := []
	for col in columns:
		values.append(col["header"])
	return values


func _add_row(values: Array, is_header: bool, row_data: Dictionary) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	var dim := not is_header and not dim_when_key.is_empty() and bool(row_data.get(dim_when_key, false))
	for i in range(values.size()):
		var label := Label.new()
		label.text = str(values[i])
		var width: int = columns[i].get("width", 160) if i < columns.size() else 160
		label.custom_minimum_size = Vector2(width, 0)
		if is_header:
			label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.75))
		elif dim:
			label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.55))
		row.add_child(label)
	if not is_header and not row_action.is_empty():
		row.mouse_filter = Control.MOUSE_FILTER_STOP
		row.gui_input.connect(_on_row_gui_input.bind(row_data))
	if not is_header:
		for spec in row_buttons:
			var button := Button.new()
			button.text = spec.get("label", "GO")
			button.custom_minimum_size = Vector2(90, 0)
			button.pressed.connect(_on_row_button_pressed.bind(spec, row_data))
			row.add_child(button)
	row_list.add_child(row)


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
