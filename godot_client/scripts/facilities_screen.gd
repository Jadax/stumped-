extends Control
## v4.28.0: pitch selection used to be five rows with a SELECT button each,
## squeezed into the same generic facility-upgrade table — user asked for
## a real dropdown instead. This screen now owns a dedicated pitch picker
## (OptionButton + CHANGE PITCH button) above the facility-upgrade table,
## which is still the generic TableScreen (res://scenes/table_screen.tscn)
## instantiated at runtime so the UPGRADE-row logic isn't duplicated.

const TABLE_SCENE := preload("res://scenes/table_screen.tscn")

@onready var pitch_option: OptionButton = $MainCol/PitchCard/Box/Row/PitchOption
@onready var change_button: Button = $MainCol/PitchCard/Box/Row/ChangeButton
@onready var status_label: Label = $MainCol/PitchCard/Box/Row/StatusLabel
@onready var description_label: Label = $MainCol/PitchCard/Box/DescriptionLabel
@onready var table_host: Control = $MainCol/TableHost

var _table: Control = null
var _pitch_types: Array = []


func _ready() -> void:
	change_button.pressed.connect(_on_change_pressed)
	pitch_option.item_selected.connect(_on_pitch_option_selected)
	_table = TABLE_SCENE.instantiate()
	_table.set_anchors_preset(Control.PRESET_FULL_RECT)
	# configure() must run before add_child() — TableScreen's own _ready()
	# calls refresh() immediately on entering the tree, and refresh() needs
	# ipc_method already set or it fires with an empty method name.
	_table.configure("FACILITY UPGRADES", "get_facilities", [
		{"key": "facility", "header": "FACILITY", "width": 200},
		{"key": "level", "header": "LEVEL", "width": 70},
		{"key": "status", "header": "STATUS", "width": 340},
	], "facilities", {}, {}, "", [
		{"label": "UPGRADE", "method": "upgrade_facility", "params_from_row": {"facility": "facility"}, "visible_if": "facility_upgrade"},
	])
	table_host.add_child(_table)
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_pitch_options")
	if response.has("error"):
		status_label.text = "Pitch status unavailable: %s" % response["error"]
		return
	var result: Dictionary = response["result"]
	_pitch_types = result.get("types", [])
	var descriptions: Dictionary = result.get("descriptions", {})
	var current := str(result.get("current", "Green"))
	pitch_option.clear()
	var selected_index := 0
	for i in range(_pitch_types.size()):
		var pitch_name := str(_pitch_types[i])
		pitch_option.add_item(pitch_name.to_upper())
		if pitch_name == current:
			selected_index = i
	pitch_option.select(selected_index)
	description_label.text = str(descriptions.get(current, ""))
	var pending = result.get("pending")
	if pending != null:
		var days := int(result.get("days_remaining", 0))
		status_label.text = "Active: %s  •  Changing to %s in %d day%s" % [
			current.to_upper(), str(pending).to_upper(), days, "" if days == 1 else "s"]
		change_button.disabled = true
	else:
		status_label.text = "Active: %s" % current.to_upper()
		change_button.disabled = false
	if _table:
		_table.refresh()


func _on_pitch_option_selected(index: int) -> void:
	if index < 0 or index >= _pitch_types.size():
		return
	description_label.text = str(IpcBridge.call_method("get_pitch_options").get("result", {}).get("descriptions", {}).get(_pitch_types[index], ""))


func _on_change_pressed() -> void:
	var index := pitch_option.selected
	if index < 0 or index >= _pitch_types.size():
		return
	var pitch_name: String = _pitch_types[index]
	var response := IpcBridge.call_method("set_pitch_selection", {"pitch": pitch_name})
	if response.has("error"):
		status_label.text = "Pitch change failed: %s" % response["error"]
		return
	refresh()
