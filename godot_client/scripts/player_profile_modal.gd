class_name PlayerProfileModal
extends Control
## Single-view player profile, ported from pygame's ui/player_modals.py
## PlayerDetailModal — scoped down to one solid view (bio, contract, full
## attribute breakdown) rather than porting all six tabs (Records/Bat Form/
## Bowl Form/Personal/Match Stats/Comparison) in one pass. Those can follow
## as their own screens later.

const ATTRIBUTE_GROUPS := [
	["batting", "BATTING"], ["bowling", "BOWLING"], ["fielding", "FIELDING"],
	["mental", "MENTAL"], ["physical", "PHYSICAL"],
]

@onready var portrait: PlayerPortrait = $Center/Card/Margin/Box/Header/Portrait
@onready var flag_rect: TextureRect = $Center/Card/Margin/Box/Header/Flag
@onready var name_label: Label = $Center/Card/Margin/Box/Header/NameBox/Name
@onready var meta_label: Label = $Center/Card/Margin/Box/Header/NameBox/Meta
@onready var overall_label: Label = $Center/Card/Margin/Box/Header/Overall
@onready var potential_label: Label = $Center/Card/Margin/Box/Header/Potential
@onready var close_button: Button = $Center/Card/Margin/Box/Header/Close
@onready var bookmark_button: Button = $Center/Card/Margin/Box/Header/Bookmark
@onready var groups_box: VBoxContainer = $Center/Card/Margin/Box/ContentScroll/Content/Groups
@onready var wage_label: Label = $Center/Card/Margin/Box/ContentScroll/Content/Contract/Wage
@onready var contract_label: Label = $Center/Card/Margin/Box/ContentScroll/Content/Contract/ContractYears
@onready var status_box: HBoxContainer = $Center/Card/Margin/Box/ContentScroll/Content/Status
@onready var personality_box: VBoxContainer = $Center/Card/Margin/Box/ContentScroll/Content/Personality
@onready var attribute_polygon: Control = $Center/Card/Margin/Box/ContentScroll/Content/AttributePolygon
@onready var career_box: VBoxContainer = $Center/Card/Margin/Box/ContentScroll/Content/Career
@onready var form_box: VBoxContainer = $Center/Card/Margin/Box/ContentScroll/Content/Form
@onready var strengths_box: VBoxContainer = $Center/Card/Margin/Box/ContentScroll/Content/Strengths
@onready var dim: ColorRect = $Dim

var _player_id: int = 0
var _player_role: String = ""
var _player_overall: int = 0
var _bookmarked: bool = false


func _ready() -> void:
	close_button.pressed.connect(hide_modal)
	bookmark_button.pressed.connect(_toggle_bookmark)
	dim.gui_input.connect(_on_dim_input)
	var card_box := StyleBoxFlat.new()
	card_box.bg_color = AppTheme.CARD
	card_box.border_color = AppTheme.GOLD
	card_box.set_border_width_all(1)
	card_box.set_corner_radius_all(10)
	$Center/Card.add_theme_stylebox_override("panel", card_box)
	name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	meta_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	overall_label.add_theme_color_override("font_color", AppTheme.GOLD)
	potential_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	wage_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	contract_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	var bbox := StyleBoxFlat.new()
	bbox.bg_color = Color(0, 0, 0, 0)
	bookmark_button.add_theme_stylebox_override("normal", bbox)
	bookmark_button.add_theme_stylebox_override("hover", bbox)
	bookmark_button.add_theme_stylebox_override("pressed", bbox)
	bookmark_button.add_theme_font_size_override("font_size", 18)
	bookmark_button.focus_mode = Control.FOCUS_NONE


func show_for(player: Dictionary) -> void:
	portrait.set_player(str(player.get("nationality", "England")), int(player.get("age", 25)), int(player.get("id", 0)))
	_player_id = int(player.get("id", 0))
	name_label.text = str(player.get("name", "—"))
	var role: String = str(player.get("role", "—"))
	var overall := int(player.get("overall", 50))
	_player_role = role
	_player_overall = overall
	meta_label.text = "%s • %s yrs • %s" % [role, JsonFormat.value(player.get("age", "—")), player.get("nationality", "—")]
	overall_label.text = str(overall)
	potential_label.text = "POT %s" % str(int(player.get("potential", overall)))
	var texture := AppTheme.flag_texture(str(player.get("nationality", "")))
	flag_rect.texture = texture
	flag_rect.visible = texture != null
	wage_label.text = "Weekly wage: %s" % str(player.get("wage_display", player.get("wage", "—")))
	contract_label.text = "Contract remaining: %s years" % JsonFormat.value(player.get("contract_years_remaining", "—"))
	_build_status_chips(player)
	_build_groups(player)
	# Set attribute polygon
	var polygon: AttributePolygon = attribute_polygon as AttributePolygon
	if polygon:
		polygon.set_attributes(player, str(player.get("name", "")))
	_build_career_stats(player)
	_build_form_history(player)
	_build_strengths(player)
	_refresh_bookmark_state()
	visible = true


## FM-style status chip row (Happiness/Fitness/Form/Discipline in the
## reference screenshots) — previously this modal showed overall/potential
## but no form/fitness/morale at all, despite the hover card already
## surfacing all three; brings the full profile up to parity.
func _build_status_chips(player: Dictionary) -> void:
	for child in status_box.get_children():
		status_box.remove_child(child)
		child.queue_free()
	var mental: Dictionary = player.get("mental", {}) if player.get("mental") is Dictionary else {}
	status_box.add_child(AppTheme.make_status_chip("FORM", int(player.get("form", 50))))
	status_box.add_child(AppTheme.make_status_chip("FITNESS", int(mental.get("fitness", 50))))
	status_box.add_child(AppTheme.make_status_chip("MORALE", int(mental.get("morale", 50))))
	_build_personality_traits(player)


func hide_modal() -> void:
	visible = false


func _on_dim_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		hide_modal()


func _build_groups(player: Dictionary) -> void:
	for child in groups_box.get_children():
		groups_box.remove_child(child)
		child.queue_free()
	for pair in ATTRIBUTE_GROUPS:
		var key: String = pair[0]
		var heading: String = pair[1]
		var attrs: Dictionary = player.get(key, {}) if player.get(key) is Dictionary else {}
		if attrs.is_empty():
			continue
		var heading_label := Label.new()
		heading_label.text = heading
		heading_label.add_theme_color_override("font_color", AppTheme.GOLD)
		heading_label.add_theme_font_size_override("font_size", 13)
		groups_box.add_child(heading_label)
		for attr_key in attrs:
			groups_box.add_child(_attribute_row(str(attr_key).replace("_", " ").capitalize(), int(attrs[attr_key])))


func _attribute_row(label_text: String, value: int) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	var label := Label.new()
	label.text = label_text
	label.custom_minimum_size = Vector2(180, 0)
	label.add_theme_font_size_override("font_size", 12)
	label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	row.add_child(label)
	row.add_child(AppTheme.make_bar_meter(260.0, value, 12, AppTheme.TEXT_PRIMARY))
	return row


var _personality_descriptions: Dictionary = {}
var _trait_descriptions: Dictionary = {}


func _ensure_personality_cache() -> void:
	if _personality_descriptions.is_empty():
		var resp := IpcBridge.call_method("get_personalities")
		if not resp.has("error"):
			_personality_descriptions = resp["result"]
	if _trait_descriptions.is_empty():
		var resp := IpcBridge.call_method("get_player_traits")
		if not resp.has("error"):
			_trait_descriptions = resp["result"]


func _build_personality_traits(player: Dictionary) -> void:
	for child in personality_box.get_children():
		personality_box.remove_child(child)
		child.queue_free()
	_ensure_personality_cache()
	var p_name: String = str(player.get("personality", "Professional"))
	var p_desc: String = _personality_descriptions.get(p_name, {}).get("description", "")
	var p_line := Label.new()
	p_line.text = "%s — %s" % [p_name, p_desc]
	p_line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	p_line.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	p_line.add_theme_font_size_override("font_size", 11)
	personality_box.add_child(p_line)
	var raw_traits = player.get("traits", [])
	if raw_traits is String:
		var trait_json := JSON.new()
		if trait_json.parse(raw_traits) == OK and trait_json.data is Array:
			raw_traits = trait_json.data
		else:
			raw_traits = []
	if raw_traits.is_empty():
		return
	var trait_names := PackedStringArray()
	for tid in raw_traits:
		var tkey: String = str(tid)
		if _trait_descriptions.has(tkey):
			trait_names.append(_trait_descriptions[tkey]["description"])
	personality_box.add_child(AppTheme.make_status_chip("TRAITS", 100))
	for tname in trait_names:
		var t_label := Label.new()
		t_label.text = "• %s" % tname
		t_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		t_label.add_theme_font_size_override("font_size", 11)
		personality_box.add_child(t_label)
	_build_keeper_role(player)


## v4.7.0: surfaces classify_keeper_batting_role's classification (backend
## since v4.6.0, no UI until now) — keeper-only, so this is a no-op for
## every other role rather than a wasted IPC round trip.
func _build_keeper_role(player: Dictionary) -> void:
	if str(player.get("role", "")) != "Wicketkeeper":
		return
	var player_id: int = int(player.get("id", 0))
	if player_id <= 0:
		return
	var resp := IpcBridge.call_method("get_keeper_batting_role", {"player_id": player_id})
	if resp.has("error"):
		return
	var label_text: String = str(resp["result"].get("label", ""))
	if label_text.is_empty():
		return
	var role_line := Label.new()
	role_line.text = "Keeper role: %s" % label_text
	role_line.add_theme_color_override("font_color", AppTheme.ACCENT)
	role_line.add_theme_font_size_override("font_size", 11)
	personality_box.add_child(role_line)


func _build_career_stats(player: Dictionary) -> void:
	for child in career_box.get_children():
		career_box.remove_child(child)
		child.queue_free()
	var player_id: int = int(player.get("id", 0))
	if player_id <= 0:
		return
	var resp := IpcBridge.call_method("get_player_records", {"player_id": player_id})
	if resp.has("error"):
		return
	var records: Dictionary = resp["result"]
	if records.is_empty():
		return
	var heading := Label.new()
	heading.text = "CAREER RECORDS"
	heading.add_theme_color_override("font_color", AppTheme.GOLD)
	heading.add_theme_font_size_override("font_size", 13)
	career_box.add_child(heading)
	for context in records:
		var record: Dictionary = records[context]
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 16)
		var ctx_label := Label.new()
		ctx_label.text = context
		ctx_label.custom_minimum_size = Vector2(80, 0)
		ctx_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
		ctx_label.add_theme_font_size_override("font_size", 12)
		row.add_child(ctx_label)
		var matches: int = int(record.get("matches", 0))
		var runs: int = int(record.get("runs", 0))
		var wickets: int = int(record.get("wickets", 0))
		var avg_bat: float = float(record.get("batting_average", 0))
		var avg_bowl: float = float(record.get("bowling_average", 0))
		var stats_text := "%d M  %d R  %.1f avg  %d W  %.1f avg" % [matches, runs, avg_bat, wickets, avg_bowl]
		var stats_label := Label.new()
		stats_label.text = stats_text
		stats_label.add_theme_font_size_override("font_size", 11)
		row.add_child(stats_label)
		career_box.add_child(row)


func _refresh_bookmark_state() -> void:
	if _player_id <= 0:
		bookmark_button.visible = false
		return
	var resp := IpcBridge.call_method("get_bookmarks", {"item_type": "player"})
	var items: Array = resp.get("result", []) if not resp.has("error") else []
	_bookmarked = false
	for item in items:
		if int(item.get("item_id", 0)) == _player_id:
			_bookmarked = true
			break
	bookmark_button.text = "★" if _bookmarked else "☆"
	bookmark_button.visible = true


func _toggle_bookmark() -> void:
	if _player_id <= 0:
		return
	if _bookmarked:
		var resp := IpcBridge.call_method("get_bookmarks", {"item_type": "player"})
		var items: Array = resp.get("result", []) if not resp.has("error") else []
		for item in items:
			if int(item.get("item_id", 0)) == _player_id:
				IpcBridge.call_method("remove_bookmark", {"bookmark_id": item["id"]})
				break
	else:
		IpcBridge.call_method("add_bookmark", {
			"item_type": "player",
			"item_id": _player_id,
			"label": name_label.text,
			"sublabel": "%s • OVR %d" % [_player_role, _player_overall],
		})
	_bookmarked = not _bookmarked
	bookmark_button.text = "★" if _bookmarked else "☆"


func _build_form_history(player: Dictionary) -> void:
	for child in form_box.get_children():
		form_box.remove_child(child)
		child.queue_free()
	var player_id: int = int(player.get("id", 0))
	if player_id <= 0:
		return
	var resp := IpcBridge.call_method("get_player_form", {"player_id": player_id})
	if resp.has("error"):
		return
	var form_data: Dictionary = resp["result"]
	if form_data.is_empty():
		return
	var heading := Label.new()
	heading.text = "FORM HISTORY"
	heading.add_theme_color_override("font_color", AppTheme.GOLD)
	heading.add_theme_font_size_override("font_size", 13)
	form_box.add_child(heading)
	# Show form trend
	var trend: String = str(form_data.get("trend", "stable"))
	var trend_label := Label.new()
	trend_label.text = "Trend: %s" % trend.capitalize()
	trend_label.add_theme_font_size_override("font_size", 11)
	trend_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	form_box.add_child(trend_label)
	# Show recent form values as a simple bar chart
	var values: Array = form_data.get("values", [])
	if values.size() > 0:
		var chart := HBoxContainer.new()
		chart.add_theme_constant_override("separation", 2)
		var max_val: float = 0.0
		for v in values:
			max_val = max(max_val, float(v))
		for i in range(min(values.size(), 10)):
			var val: float = float(values[values.size() - 1 - i])
			var bar_height: float = (val / max(max_val, 1.0)) * 40.0
			var bar := ColorRect.new()
			bar.color = AppTheme.attribute_colour(val)
			bar.custom_minimum_size = Vector2(8, bar_height)
			chart.add_child(bar)
		form_box.add_child(chart)


func _build_strengths(player: Dictionary) -> void:
	for child in strengths_box.get_children():
		strengths_box.remove_child(child)
		child.queue_free()
	var heading := Label.new()
	heading.text = "STRENGTHS & WEAKNESSES"
	heading.add_theme_color_override("font_color", AppTheme.GOLD)
	heading.add_theme_font_size_override("font_size", 13)
	strengths_box.add_child(heading)
	# Analyze attributes to find strengths and weaknesses
	var all_attrs: Dictionary = {}
	for group in ["batting", "bowling", "fielding", "mental"]:
		var attrs: Dictionary = player.get(group, {}) if player.get(group) is Dictionary else {}
		for key in attrs:
			all_attrs[key] = int(attrs[key])
	if all_attrs.is_empty():
		return
	# Sort by value
	var sorted_attrs := []
	for key in all_attrs:
		sorted_attrs.append({"name": str(key).replace("_", " ").capitalize(), "value": all_attrs[key]})
	sorted_attrs.sort_custom(func(a, b): return a["value"] > b["value"])
	# Show top 3 strengths
	var strengths_label := Label.new()
	strengths_label.text = "Top Strengths:"
	strengths_label.add_theme_font_size_override("font_size", 11)
	strengths_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	strengths_box.add_child(strengths_label)
	for i in range(min(3, sorted_attrs.size())):
		var attr: Dictionary = sorted_attrs[i]
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		var name_label := Label.new()
		name_label.text = attr["name"]
		name_label.custom_minimum_size = Vector2(150, 0)
		name_label.add_theme_font_size_override("font_size", 11)
		row.add_child(name_label)
		row.add_child(AppTheme.make_bar_meter(120.0, float(attr["value"]), 11))
		strengths_box.add_child(row)
	# Show bottom 3 weaknesses
	var weaknesses_label := Label.new()
	weaknesses_label.text = "Areas for Improvement:"
	weaknesses_label.add_theme_font_size_override("font_size", 11)
	weaknesses_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	strengths_box.add_child(weaknesses_label)
	for i in range(max(0, sorted_attrs.size() - 3), sorted_attrs.size()):
		var attr: Dictionary = sorted_attrs[i]
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		var name_label := Label.new()
		name_label.text = attr["name"]
		name_label.custom_minimum_size = Vector2(150, 0)
		name_label.add_theme_font_size_override("font_size", 11)
		row.add_child(name_label)
		row.add_child(AppTheme.make_bar_meter(120.0, float(attr["value"]), 11))
		strengths_box.add_child(row)
