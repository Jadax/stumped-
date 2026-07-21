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


func configure(p_title: String, p_method: String, p_columns: Array, p_rows_key: String = "rows",
			p_params: Dictionary = {}) -> void:
	screen_title = p_title
	ipc_method = p_method
	columns = p_columns
	rows_key = p_rows_key
	ipc_params = p_params


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
	_add_row(_header_values(), true)
	for row in rows:
		var values := []
		for col in columns:
			values.append(str(row.get(col["key"], "")))
		_add_row(values, false)


func _header_values() -> Array:
	var values := []
	for col in columns:
		values.append(col["header"])
	return values


func _add_row(values: Array, is_header: bool) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	for i in range(values.size()):
		var label := Label.new()
		label.text = str(values[i])
		var width: int = columns[i].get("width", 160) if i < columns.size() else 160
		label.custom_minimum_size = Vector2(width, 0)
		if is_header:
			label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.75))
		row.add_child(label)
	row_list.add_child(row)
