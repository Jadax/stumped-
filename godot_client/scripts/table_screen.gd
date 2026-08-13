extends Control
## Generic reusable list/table screen — most of the pygame client's simple
## data screens (Staff roster, Transfer market, Finances, Facilities,
## Honours, Inbox) are "fetch a list, show it in columns" exactly like
## ui/widgets/datatable.py's DataTable is reused across those pygame
## screens. Configure with `configure()` right after instancing, before
## adding to the tree, so _ready() has real settings to work with.

const HOVER_CARD_SCENE := preload("res://scenes/player_hover_card.tscn")
const PROFILE_MODAL_SCENE := preload("res://scenes/player_profile_modal.tscn")
const PLAYER_PORTRAIT_SCRIPT := preload("res://scripts/player_portrait.gd")

@onready var title_label: Label = $Title
@onready var row_list: VBoxContainer = $ScrollContainer/RowList
@onready var title_rule: ColorRect = $TitleRule

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

## v4.29.0: Football Manager-style squad lockdown — a response can set a
## top-level "locked" bool (Selection does, once a match is live) to
## disable row_action and row_buttons interactivity generically, without
## every screen needing its own bespoke lock handling.
var is_locked: bool = false

## v4.29.0: optional filter bar (Transfer/Staff Market asked for "type of
## coach, skill minimums" etc, FM-style) — a generic row of controls above
## the table that write straight into ipc_params and re-refresh, so any
## screen using this component gets real filtering for free instead of
## each screen hand-rolling its own. Each spec:
## {"key": "role", "label": "ROLE", "type": "option", "options": [...], "default": "All"}
## {"key": "minimum_overall", "label": "MIN OVR", "type": "number", "min": 0, "max": 100, "default": 0}
var filters: Array = []
var _filter_bar: HBoxContainer = null
var _selection_brief: PanelContainer = null
## v4.60.2: the four value labels below (STARTING_XI/LEADERSHIP/CONDITIONS/
## TACTICAL_CHECK) are nested one level deeper than the fragile
## get_node("HBoxContainer/<NAME>") lookups below them expected — each
## value label is a child of its own per-heading VBoxContainer card, which
## is itself the child of the HBoxContainer, so that path never resolved
## and the briefing card was permanently stuck on "Loading…". Storing
## direct references at build time instead of a brittle string path.
var _selection_brief_values: Dictionary = {}


func configure(p_title: String, p_method: String, p_columns: Array, p_rows_key: String = "rows",
			p_params: Dictionary = {}, p_row_action: Dictionary = {}, p_dim_when_key: String = "",
			p_row_buttons: Array = [], p_extra_tabs: Array = [], p_filters: Array = []) -> void:
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
	filters = p_filters


func _ready() -> void:
	title_rule.color = AppTheme.GOLD
	if not extra_tabs.is_empty():
		_build_tab_bar()
	if not filters.is_empty():
		_build_filter_bar()
	if screen_title == "SELECTION":
		_build_selection_brief()
	_hover_card = HOVER_CARD_SCENE.instantiate()
	add_child(_hover_card)
	_profile_modal = PROFILE_MODAL_SCENE.instantiate()
	add_child(_profile_modal)
	refresh()


## Builds the filter row and seeds ipc_params with each filter's default so
## the very first refresh() already reflects them (matching how a user
## would expect "MIN OVR: 0" to mean "no filter yet", not "show nothing").
func _build_filter_bar() -> void:
	# Stack below the tab bar when a screen uses both (none do today, but
	# this keeps the two additive rather than overlapping if one ever does).
	var top: float = 96.0 if not extra_tabs.is_empty() else 52.0
	_filter_bar = HBoxContainer.new()
	_filter_bar.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	_filter_bar.offset_left = 24
	_filter_bar.offset_top = top
	_filter_bar.offset_right = -24
	_filter_bar.add_theme_constant_override("separation", 16)
	add_child(_filter_bar)
	var scroll: Control = $ScrollContainer
	scroll.offset_top = top + 44

	for spec in filters:
		var box := VBoxContainer.new()
		box.add_theme_constant_override("separation", 2)
		var label := Label.new()
		label.text = str(spec.get("label", spec["key"]))
		label.add_theme_font_size_override("font_size", 11)
		label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		box.add_child(label)
		if spec.get("type", "option") == "number":
			var spin := SpinBox.new()
			spin.min_value = spec.get("min", 0)
			spin.max_value = spec.get("max", 100)
			spin.step = spec.get("step", 1)
			spin.value = spec.get("default", spec.get("min", 0))
			spin.custom_minimum_size = Vector2(spec.get("width", 90), 0)
			ipc_params[spec["key"]] = spin.value
			spin.value_changed.connect(func(v): ipc_params[spec["key"]] = v; refresh())
			box.add_child(spin)
		else:
			var option := OptionButton.new()
			var options: Array = spec.get("options", ["All"])
			for opt in options:
				option.add_item(str(opt))
			var default_value = spec.get("default", options[0] if not options.is_empty() else "All")
			var default_index: int = options.find(default_value)
			option.select(max(0, default_index))
			option.custom_minimum_size = Vector2(spec.get("width", 140), 0)
			ipc_params[spec["key"]] = default_value
			option.item_selected.connect(func(i): ipc_params[spec["key"]] = options[i]; refresh())
			box.add_child(option)
		_filter_bar.add_child(box)


func _build_selection_brief() -> void:
	## A compact pre-match brief inspired by the reference team-sheet layout.
	## It is deliberately built here (rather than a second scene) so existing
	## row actions, smoke-test hooks, and backend locking remain unchanged.
	_selection_brief = PanelContainer.new()
	_selection_brief.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	_selection_brief.offset_left = 24
	_selection_brief.offset_top = 62
	_selection_brief.offset_right = -24
	_selection_brief.custom_minimum_size = Vector2(0, 86)
	var style := StyleBoxFlat.new()
	style.bg_color = AppTheme.CARD
	style.border_color = AppTheme.BORDER
	style.set_border_width_all(1)
	style.set_corner_radius_all(10)
	style.content_margin_left = 14
	style.content_margin_right = 14
	style.content_margin_top = 10
	style.content_margin_bottom = 10
	_selection_brief.add_theme_stylebox_override("panel", style)
	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 26)
	_selection_brief.add_child(columns)
	for heading in ["STARTING XI", "LEADERSHIP", "CONDITIONS", "TACTICAL CHECK"]:
		var card := VBoxContainer.new()
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		card.add_theme_constant_override("separation", 3)
		var h := Label.new()
		h.text = heading
		h.add_theme_color_override("font_color", AppTheme.GOLD)
		h.add_theme_font_size_override("font_size", 11)
		card.add_child(h)
		var value := Label.new()
		value.name = heading.replace(" ", "_")
		value.text = "Loading…"
		value.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		value.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
		value.add_theme_font_size_override("font_size", 14)
		card.add_child(value)
		columns.add_child(card)
		_selection_brief_values[value.name] = value
	add_child(_selection_brief)
	var scroll: Control = $ScrollContainer
	scroll.offset_top = 164


func _update_selection_brief(result: Dictionary) -> void:
	if not _selection_brief:
		return
	var xi := int(result.get("xi_count", 0))
	var bowlers := int(result.get("bowlers_in_xi", 0))
	var captain := "Not set"
	var keeper := "Not set"
	var players: Array = result.get("players", [])
	for row in players:
		var status := str(row.get("xi_status", ""))
		if status.contains("C"): captain = str(row.get("name", "Captain"))
		if status.contains("WK"): keeper = str(row.get("name", "Keeper"))
	if _selection_brief_values.is_empty():
		return
	_selection_brief_values["STARTING_XI"].text = "%d / 11 selected  •  %d / 5 bowlers" % [xi, bowlers]
	_selection_brief_values["LEADERSHIP"].text = "C  %s\nWK  %s" % [captain, keeper]
	_selection_brief_values["CONDITIONS"].text = "Choose pitch and weather\nbefore confirming XI"
	var warning := "Ready to confirm"
	if xi != 11: warning = "Need %d more player%s" % [11 - xi, "s" if xi != 10 else ""]
	elif bowlers < 5: warning = "Only %d bowlers — need 5" % bowlers
	elif captain == "Not set" or keeper == "Not set": warning = "Set captain and wicketkeeper"
	_selection_brief_values["TACTICAL_CHECK"].text = warning


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
		button.custom_minimum_size = Vector2(0, 32)
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
	is_locked = bool(response["result"].get("locked", false))
	_update_selection_brief(response["result"])
	title_label.text = "%s — %d" % [screen_title, rows.size()]
	if is_locked:
		title_label.text += "  •  SQUAD LOCKED (match in progress)"
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
	var data_index := row_list.get_child_count() - 1
	var box := StyleBoxFlat.new()
	box.content_margin_left = 14
	box.content_margin_right = 14
	box.content_margin_top = 8
	box.content_margin_bottom = 8
	box.set_corner_radius_all(4)
	var base_colour: Color
	if is_header:
		base_colour = AppTheme.ACTIVE
		box.border_width_bottom = 2
		box.border_color = AppTheme.GOLD
		box.set_corner_radius_all(6)
	elif data_index % 2 == 0:
		base_colour = AppTheme.CARD
	else:
		base_colour = AppTheme.SURFACE
	box.bg_color = base_colour
	panel.add_theme_stylebox_override("panel", box)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	row.custom_minimum_size.y = 38 if not is_header else 42
	if not is_header:
		row.mouse_filter = Control.MOUSE_FILTER_STOP
		var hover_box := box.duplicate()
		hover_box.bg_color = AppTheme.HOVER
		hover_box.border_width_left = 3
		hover_box.border_color = AppTheme.GOLD
		row.mouse_entered.connect(func(): panel.add_theme_stylebox_override("panel", hover_box))
		row.mouse_exited.connect(func(): panel.add_theme_stylebox_override("panel", box))
	var dim := not is_header and not dim_when_key.is_empty() and bool(row_data.get(dim_when_key, false))
	for i in range(values.size()):
		var width: int = columns[i].get("width", 160) if i < columns.size() else 160
		var is_pill: bool = not is_header and i < columns.size() and bool(columns[i].get("pill", false)) and not str(values[i]).is_empty()
		var is_flag: bool = not is_header and i < columns.size() and bool(columns[i].get("flag", false))
		var is_bar: bool = not is_header and i < columns.size() and bool(columns[i].get("bar", false)) and str(values[i]).is_valid_float()
		var is_stars: bool = not is_header and i < columns.size() and bool(columns[i].get("stars", false)) and str(values[i]).is_valid_float()
		var is_portrait: bool = not is_header and i < columns.size() and bool(columns[i].get("portrait", false))
		if is_portrait:
			var cell := Control.new()
			cell.custom_minimum_size = Vector2(width, 0)
			var portrait := Control.new()
			portrait.set_script(PLAYER_PORTRAIT_SCRIPT)
			portrait.custom_minimum_size = Vector2(32, 32)
			cell.add_child(portrait)
			portrait.set_player(str(row_data.get("nationality", "England")), int(row_data.get("age", 25)), int(row_data.get("id", 0)))
			row.add_child(cell)
			continue
		if is_bar:
			var cell := Control.new()
			cell.custom_minimum_size = Vector2(width, 0)
			cell.add_child(_make_bar(width, float(values[i])))
			row.add_child(cell)
			continue
		if is_stars:
			var cell := Control.new()
			cell.custom_minimum_size = Vector2(width, 0)
			cell.add_child(_make_stars(float(values[i])))
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
			else:
				# AppTheme.flag_texture() returns null for nationalities
				# with no single ISO flag (West Indies — a multi-nation
				# cricket board, not a country) and documents that the
				# caller should draw a placeholder — this was the one spot
				# that never actually did, silently leaving the cell blank.
				cell.add_child(_flag_fallback_badge(str(values[i])))
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
		label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		label.clip_text = false
		label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
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
	if not is_header and not row_action.is_empty() and not is_locked:
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
			if spec.has("visible_if") and not bool(row_data.get(spec["visible_if"], false)):
				continue
			var button := Button.new()
			button.text = spec.get("label", "GO")
			button.custom_minimum_size = Vector2(spec.get("width", 90), 0)
			button.add_theme_font_size_override("font_size", 12)
			if is_locked:
				button.disabled = true
				button.tooltip_text = "Squad is locked — a match is already in progress."
			else:
				button.pressed.connect(_on_row_button_pressed.bind(spec, row_data))
			row.add_child(button)
	panel.add_child(row)
	row_list.add_child(panel)


## A small horizontal bar meter (0-100 stats like form/morale) with a
## coloured fill tier and the raw number alongside it — mirrors the
## reference screenshots' form/confidence meters, instead of a bare number.
func _make_bar(width: int, value: float) -> Control:
	return AppTheme.make_bar_meter(max(10.0, width - 32), value)


## A 5-star fitness/condition rating (reference: the team-lineup screenshot's
## star column) — value is a 0-100 stat, rounded to the nearest whole star
## out of 5, tier-coloured the same way a bar meter would be.
func _make_stars(value: float) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 1)
	var filled: int = roundi(clampf(value / 100.0, 0.0, 1.0) * 5.0)
	var colour := AppTheme.attribute_colour(value)
	for i in range(5):
		var star := Label.new()
		var lit: bool = i < filled
		star.text = "★" if lit else "☆"
		star.add_theme_font_size_override("font_size", 13)
		star.add_theme_color_override("font_color", colour if lit else AppTheme.BORDER)
		row.add_child(star)
	return row


## The one nationality with no real ISO flag in this game's data (West
## Indies — a multi-nation cricket board, not a country) — see
## AppTheme.flag_texture()'s docstring for why it returns null here.
const NO_FLAG_CODES := {"West Indian": "WI", "West Indies": "WI"}


func _flag_fallback_badge(nationality: String) -> Control:
	var badge := PanelContainer.new()
	badge.custom_minimum_size = Vector2(24, 16)
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.BORDER
	box.set_corner_radius_all(3)
	badge.add_theme_stylebox_override("panel", box)
	var label := Label.new()
	label.text = NO_FLAG_CODES.get(nationality, "?")
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 9)
	label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	badge.add_child(label)
	return badge


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
	box.content_margin_top = 3
	box.content_margin_bottom = 3
	pill.add_theme_stylebox_override("panel", box)
	var label := Label.new()
	label.text = value
	label.add_theme_font_size_override("font_size", 11)
	label.add_theme_color_override("font_color", AppTheme.CARD)
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
	elif action.get("method", "") == "accept_job_offer":
		# The one row action that changes which club the user manages —
		# the persistent header (crest/team name/next fixture) needs a
		# refresh too, not just this screen's own row list.
		var shell := get_tree().get_first_node_in_group("shell")
		if shell:
			shell.refresh_header()
