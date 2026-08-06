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
@onready var section_tabs: HBoxContainer = $Center/Card/Margin/Box/SectionTabs
@onready var content_scroll: ScrollContainer = $Center/Card/Margin/Box/ContentScroll
@onready var match_stats_card: PanelContainer = $Center/Card/Margin/Box/MatchStatsCard
@onready var match_stats_box: VBoxContainer = $Center/Card/Margin/Box/MatchStatsCard/MatchStats

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
	for tab in section_tabs.get_children():
		if tab is Button:
			tab.pressed.connect(_on_section_tab_pressed.bind(str(tab.name).to_lower()))


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
	_build_match_snapshot(player)
	_select_profile_tab("overview")
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
	# v4.28.0: this used to be AppTheme.make_status_chip("TRAITS", 100) — a
	# stat-meter chip with a hardcoded, meaningless "100" value, which read
	# as a real 0-100 rating and confused the user ("what does traits
	# mean?"). Traits aren't a scored attribute — they're a fixed set of
	# special behaviours (e.g. "Showman", listed below) a player either
	# has or doesn't, so this is now a plain section header with a
	# tooltip explaining that distinction on hover.
	var traits_heading := Label.new()
	traits_heading.text = "TRAITS"
	traits_heading.add_theme_color_override("font_color", AppTheme.GOLD)
	traits_heading.add_theme_font_size_override("font_size", 12)
	traits_heading.tooltip_text = "Special behaviours this player has, not a scored attribute — each one changes how they play in specific situations (e.g. big matches, under pressure)."
	personality_box.add_child(traits_heading)
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


## Real per-format record book, matching the reference screenshot's
## Batting/Bowling grids (one row per format — "First Class"/"One Day"/
## "20 Over"/"Test Match"/etc., see src/models/player_records.py's
## format_context()) instead of the old single flattened text line per
## context. Only formats the player actually has a record for are shown,
## in CONTEXTS order (domestic first, then the matching international tier).
const RECORD_CONTEXT_ORDER := ["First Class", "One Day", "20 Over", "10 Over", "The Hundred",
	"Test Match", "One Day International", "20 Over International",
	"10 Over International", "The Hundred International"]
const BATTING_COLUMNS := [["M", "matches"], ["Inns", "innings"], ["Runs", "runs"],
	["HS", "highest_score"], ["Avg", "batting_average"], ["100s", "hundreds"],
	["50s", "fifties"], ["SR%", "strike_rate"]]
const BOWLING_COLUMNS := [["Ovrs", "overs"], ["Runs", "runs_conceded"], ["Wkts", "wickets"],
	["Avg", "bowling_average"], ["SR", "bowling_strike_rate"], ["Best", "best"],
	["5i", "five_wickets"], ["10m", "ten_wickets"], ["Econ", "economy"],
	["Ct/St", "catches_stumpings"], ["CpM", "catches_per_match"]]


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
		var empty := Label.new()
		empty.text = "No matches played yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		career_box.add_child(empty)
		return
	var ordered_contexts: Array = []
	for context in RECORD_CONTEXT_ORDER:
		if records.has(context):
			ordered_contexts.append(context)
	for context in records:
		if not ordered_contexts.has(context):
			ordered_contexts.append(context)
	career_box.add_child(_career_stat_grid("BATTING", records, ordered_contexts, BATTING_COLUMNS))
	career_box.add_child(_career_stat_grid("BOWLING", records, ordered_contexts, BOWLING_COLUMNS))


func _career_stat_grid(heading_text: String, records: Dictionary, contexts: Array, columns: Array) -> VBoxContainer:
	var wrap := VBoxContainer.new()
	wrap.add_theme_constant_override("separation", 4)
	var heading := Label.new()
	heading.text = heading_text
	heading.add_theme_color_override("font_color", AppTheme.GOLD)
	heading.add_theme_font_size_override("font_size", 13)
	wrap.add_child(heading)
	var grid := GridContainer.new()
	grid.columns = columns.size() + 1
	grid.add_theme_constant_override("h_separation", 8)
	grid.add_theme_constant_override("v_separation", 4)
	var format_header := Label.new()
	format_header.text = "FORMAT"
	format_header.custom_minimum_size = Vector2(78, 0)
	format_header.add_theme_font_size_override("font_size", 9)
	format_header.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	grid.add_child(format_header)
	for pair in columns:
		var col_header := Label.new()
		col_header.text = str(pair[0])
		col_header.custom_minimum_size = Vector2(36, 0)
		col_header.add_theme_font_size_override("font_size", 9)
		col_header.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		grid.add_child(col_header)
	for context in contexts:
		var record: Dictionary = records[context]
		var ctx_label := Label.new()
		ctx_label.text = context
		ctx_label.custom_minimum_size = Vector2(78, 0)
		ctx_label.clip_text = true
		ctx_label.add_theme_font_size_override("font_size", 10)
		ctx_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
		grid.add_child(ctx_label)
		for pair in columns:
			var value_label := Label.new()
			value_label.text = _career_stat_value(record, str(pair[1]))
			value_label.custom_minimum_size = Vector2(36, 0)
			value_label.add_theme_font_size_override("font_size", 10)
			value_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
			grid.add_child(value_label)
	wrap.add_child(grid)
	return wrap


## Derives fields CareerRecord.serialise() doesn't already provide directly
## (best bowling figures as "W-R", Ct/St combined, catches-per-match) from
## the raw serialised record, and formats the rest for display.
func _career_stat_value(record: Dictionary, key: String) -> String:
	match key:
		"best":
			var best_wickets := int(record.get("best_wickets", 0))
			var best_runs := int(record.get("best_runs", 999))
			if best_wickets == 0 and best_runs >= 999:
				return "—"
			return "%d-%d" % [best_wickets, best_runs]
		"catches_stumpings":
			return "%d/%d" % [int(record.get("catches", 0)), int(record.get("stumpings", 0))]
		"catches_per_match":
			var matches := int(record.get("matches", 0))
			if matches <= 0:
				return "0.00"
			return "%.2f" % (float(record.get("catches", 0)) / float(matches))
		"strike_rate", "bowling_strike_rate", "economy", "bowling_average", "batting_average":
			var value := float(record.get(key, 0.0))
			return "—" if value <= 0.0 else "%.2f" % value
		_:
			return JsonFormat.value(record.get(key, 0))


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
		var strength_attr: Dictionary = sorted_attrs[i]
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		var name_label := Label.new()
		name_label.text = strength_attr["name"]
		name_label.custom_minimum_size = Vector2(150, 0)
		name_label.add_theme_font_size_override("font_size", 11)
		row.add_child(name_label)
		row.add_child(AppTheme.make_bar_meter(120.0, float(strength_attr["value"]), 11))
		strengths_box.add_child(row)
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


const CHANCE_LABELS := [["Dropped catches", "dropped"], ["LBW appeals", "lbw_appeals"],
	["Played & missed", "played_and_missed"], ["Catchable shots", "catchable"]]


## Real per-ball data from this player's most recently completed match — no
## live in-progress innings here (that's Match Day's job, see docs/CURRENT.md);
## this is the wagon wheel / runs progression / chances panel the reference
## screenshot shows once a match is over. Shots/deliveries persist across every
## match a player's been in (fetch_player_match_events, LIMIT 500), so this
## filters down to just the most recent match_id for a genuinely "this match"
## view rather than a lifetime jumble of dots.
func _build_match_snapshot(player: Dictionary) -> void:
	for child in match_stats_box.get_children():
		match_stats_box.remove_child(child)
		child.queue_free()
	var player_id: int = int(player.get("id", 0))
	if player_id <= 0:
		return
	var resp := IpcBridge.call_method("get_player_match_events", {"player_id": player_id})
	if resp.has("error"):
		return
	var result: Dictionary = resp["result"]
	var all_shots: Array = result.get("shots", [])
	var chances: Dictionary = result.get("chances", {})
	if all_shots.is_empty():
		var empty := Label.new()
		empty.text = "No completed match data yet for this player. Play a match and this fills in with a real wagon wheel, runs progression and chances panel."
		empty.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		match_stats_box.add_child(empty)
		return
	var last_match_id = all_shots[0].get("match_id")
	var match_shots: Array = all_shots.filter(func(e): return e.get("match_id") == last_match_id)
	match_shots.reverse()  # rows come back most-recent-first; chronological order for the progression line
	match_stats_box.add_child(_match_figures_row(match_shots))
	var charts_row := HBoxContainer.new()
	charts_row.add_theme_constant_override("separation", 12)
	charts_row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	charts_row.add_child(_chances_box(chances))
	charts_row.add_child(_labelled_canvas("WAGON WHEEL", _shot_map_canvas(match_shots)))
	charts_row.add_child(_labelled_canvas("RUNS PROGRESSION", _progression_canvas(match_shots)))
	match_stats_box.add_child(charts_row)


func _match_figures_row(match_shots: Array) -> HBoxContainer:
	var runs := 0
	var fours := 0
	var sixes := 0
	for shot in match_shots:
		var shot_runs := int(shot.get("runs", 0))
		runs += shot_runs
		fours += int(shot_runs == 4)
		sixes += int(shot_runs == 6)
	var balls := match_shots.size()
	var sr := (float(runs) * 100.0 / float(balls)) if balls > 0 else 0.0
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 18)
	var figures := [["RUNS", str(runs)], ["BALLS", str(balls)], ["4s", str(fours)],
		["6s", str(sixes)], ["SR%", "%.1f" % sr]]
	for pair in figures:
		var col := VBoxContainer.new()
		var header := Label.new()
		header.text = str(pair[0])
		header.add_theme_font_size_override("font_size", 9)
		header.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		col.add_child(header)
		var value := Label.new()
		value.text = str(pair[1])
		value.add_theme_font_size_override("font_size", 15)
		value.add_theme_color_override("font_color", AppTheme.GOLD if pair[0] == "RUNS" else AppTheme.TEXT_PRIMARY)
		col.add_child(value)
		row.add_child(col)
	return row


func _chances_box(chances: Dictionary) -> VBoxContainer:
	var box := VBoxContainer.new()
	box.custom_minimum_size = Vector2(160, 0)
	box.add_theme_constant_override("separation", 4)
	var heading := Label.new()
	heading.text = "CHANCES"
	heading.add_theme_color_override("font_color", AppTheme.GOLD)
	heading.add_theme_font_size_override("font_size", 11)
	box.add_child(heading)
	for pair in CHANCE_LABELS:
		var row := HBoxContainer.new()
		var label := Label.new()
		label.text = str(pair[0])
		label.custom_minimum_size = Vector2(112, 0)
		label.add_theme_font_size_override("font_size", 10)
		label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
		row.add_child(label)
		var value := Label.new()
		value.text = str(int(chances.get(pair[1], 0)))
		value.add_theme_font_size_override("font_size", 11)
		value.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
		row.add_child(value)
		box.add_child(row)
	return box


func _labelled_canvas(caption: String, canvas: Control) -> VBoxContainer:
	var wrap := VBoxContainer.new()
	wrap.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var caption_label := Label.new()
	caption_label.text = caption
	caption_label.add_theme_font_size_override("font_size", 10)
	caption_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	wrap.add_child(caption_label)
	wrap.add_child(canvas)
	return wrap


## Reuses match_screen.gd's Stats Hub shot-map drawing (MatchStatsCanvas) at a
## small size, fed by just this player's own shots — the per-batter wagon
## wheel the reference screenshots show inline with each player.
func _shot_map_canvas(match_shots: Array) -> MatchStatsCanvas:
	var canvas := MatchStatsCanvas.new()
	canvas.custom_minimum_size = Vector2(200, 200)
	canvas.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	canvas.shot_events = match_shots
	canvas.set_mode("shot_map")
	return canvas


## Bins this match's shots into 6-ball "overs" of cumulative runs and reuses
## MatchStatsCanvas's worm-graph line drawing — the same real progression
## data (this player's own runs vs. balls faced), not a generic team worm.
func _progression_canvas(match_shots: Array) -> MatchStatsCanvas:
	var canvas := MatchStatsCanvas.new()
	canvas.custom_minimum_size = Vector2(200, 200)
	canvas.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var overs: Array = []
	var cumulative := 0
	for i in range(match_shots.size()):
		cumulative += int(match_shots[i].get("runs", 0))
		if (i + 1) % 6 == 0 or i == match_shots.size() - 1:
			overs.append(cumulative)
	canvas.innings_overs = [overs]
	canvas.set_mode("worm")
	return canvas


func _on_section_tab_pressed(tab_name: String) -> void:
	_select_profile_tab(tab_name)


func _select_profile_tab(tab_name: String) -> void:
	var overview := tab_name == "overview"
	var records := tab_name == "records"
	var form := tab_name == "form"
	var match_stats := tab_name == "matchstats"
	var personal := tab_name == "personal"
	# Overview keeps the decision-relevant profile visible; specialised tabs
	# reduce density so the manager can read one evidence set at a time.
	# Match Stats gets the ContentScroll's reclaimed vertical space (its own
	# grid/canvases need real room, unlike the flat text career_box/form_box
	# were fine sharing scroll space with).
	content_scroll.visible = not match_stats
	status_box.visible = overview or personal
	personality_box.visible = overview or personal
	attribute_polygon.visible = overview or form
	strengths_box.visible = overview
	groups_box.visible = overview
	career_box.visible = records
	form_box.visible = form
	match_stats_card.visible = match_stats
	# Separators and contract sit in the scroll content; keep them with the
	# overview/personal tabs rather than leaving floating rules on every tab.
	$Center/Card/Margin/Box/ContentScroll/Content/Sep1.visible = overview
	$Center/Card/Margin/Box/ContentScroll/Content/Sep2.visible = overview or personal
	$Center/Card/Margin/Box/ContentScroll/Content/Contract.visible = overview or personal
	for tab in section_tabs.get_children():
		if tab is Button:
			tab.set_pressed_no_signal(str(tab.name).to_lower() == tab_name)
