extends Control
## The persistent chrome — sidebar navigation (mirrors main.py's NAV_GROUPS,
## docs/UX_ROADMAP.md's FM26-translated IA) and a content area that swaps
## screens. Screens not yet ported show the same "Coming Soon" placeholder
## the pygame client's BaseScreen falls back to.

const NAV_GROUPS := [
	["PORTAL", ["Dashboard", "Inbox"]],
	["SQUAD", ["Squad", "Selection", "Training", "Youth Academy", "Medical Centre"]],
	["MATCH DAY", ["Match"]],
	["RECRUITMENT", ["Recruitment", "Transfers", "Offers"]],
	["CLUB", ["Staff", "Staff Market", "Finances", "Facilities"]],
	["CAREER", ["Career"]],
]

## Hand-drawn nav_icon.gd glyph per screen — no icon asset pipeline exists,
## so related screens intentionally share a glyph (e.g. Staff/Staff Market
## both use "staff") rather than inventing sixteen distinct pictograms.
const NAV_ICONS := {
	"Dashboard": "dashboard", "Inbox": "inbox", "Squad": "squad", "Selection": "selection",
	"Training": "training", "Youth Academy": "academy", "Medical Centre": "medical", "Match": "match",
	"Recruitment": "recruitment", "Transfers": "transfers", "Offers": "transfers",
	"Staff": "staff", "Staff Market": "staff", "Finances": "finances", "Facilities": "facilities",
	"Career": "career",
}

const DASHBOARD_SCENE := preload("res://scenes/dashboard_screen.tscn")
const TRAINING_SCENE := preload("res://scenes/training_screen.tscn")
const RECRUITMENT_SCENE := preload("res://scenes/recruitment_screen.tscn")
const TABLE_SCENE := preload("res://scenes/table_screen.tscn")
const MATCH_SCENE := preload("res://scenes/match_screen.tscn")
const PLACEHOLDER_SCENE := preload("res://scenes/placeholder_screen.tscn")

@onready var sidebar: VBoxContainer = $Layout/Row/SidebarBg/Sidebar
@onready var content: Control = $Layout/Row/Content
@onready var crest_label: Label = $Layout/HeaderBg/Header/Crest/CrestLabel
@onready var team_name_label: Label = $Layout/HeaderBg/Header/TeamBox/TeamName
@onready var team_subtitle_label: Label = $Layout/HeaderBg/Header/TeamBox/TeamSubtitle
@onready var advance_button: Button = $Layout/HeaderBg/Header/AdvanceButton

var current_screen: Control = null
var current_screen_name: String = ""
var _nav_buttons: Dictionary = {}
var _nav_icons: Dictionary = {}
var _nav_labels: Dictionary = {}


func _ready() -> void:
	theme = AppTheme.build()
	_build_sidebar()
	_style_header()
	advance_button.pressed.connect(_on_advance_pressed)
	refresh_header()
	if "--smoke-test" in OS.get_cmdline_user_args():
		_run_smoke_test()
	elif "--screenshot-test" in OS.get_cmdline_user_args():
		_run_screenshot_test()
	else:
		show_screen("Dashboard")


func _style_header() -> void:
	var crest_box := StyleBoxFlat.new()
	crest_box.bg_color = AppTheme.GOLD
	crest_box.set_corner_radius_all(22)
	$Layout/HeaderBg/Header/Crest.add_theme_stylebox_override("panel", crest_box)
	crest_label.add_theme_color_override("font_color", AppTheme.BACKGROUND)
	crest_label.add_theme_font_size_override("font_size", 14)
	team_subtitle_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	var advance_box := StyleBoxFlat.new()
	advance_box.bg_color = AppTheme.DANGER
	advance_box.set_corner_radius_all(6)
	advance_button.add_theme_stylebox_override("normal", advance_box)
	var advance_hover := StyleBoxFlat.new()
	advance_hover.bg_color = AppTheme.DANGER.lightened(0.15)
	advance_hover.set_corner_radius_all(6)
	advance_button.add_theme_stylebox_override("hover", advance_hover)
	advance_button.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	advance_button.add_theme_color_override("font_hover_color", AppTheme.TEXT_PRIMARY)


## The persistent header — team crest initials, name, next-fixture/date
## subtitle, and the Advance Day action — is fed by get_dashboard the same
## way DashboardScreen's own cards are, so both stay in sync without a
## second source of truth for team/fixture state.
func refresh_header() -> void:
	var response := IpcBridge.call_method("get_dashboard")
	if response.has("error"):
		team_name_label.text = "Stumped!"
		return
	var result: Dictionary = response["result"]
	var team: Dictionary = result.get("team", {})
	var name: String = team.get("name", "?")
	team_name_label.text = name
	var initials := ""
	for word in name.split(" ", false):
		if not word.is_empty():
			initials += word[0]
	crest_label.text = initials.substr(0, 2).to_upper()
	var fixture = result.get("fixture")
	var date_text: String = str(result.get("date", "?"))
	if fixture:
		var opponent: String = fixture.get("away_name", "?") if fixture.get("home_team") == team.get("id") else fixture.get("home_name", "?")
		team_subtitle_label.text = "%s — next: vs %s" % [date_text, opponent]
	else:
		team_subtitle_label.text = date_text


func _on_advance_pressed() -> void:
	advance_button.disabled = true
	var response := IpcBridge.call_method("advance_day")
	advance_button.disabled = false
	if response.has("error"):
		push_error("Shell: advance_day failed: %s" % response["error"])
		return
	refresh_header()
	if current_screen and current_screen.has_method("refresh"):
		current_screen.refresh()


## Dev-only: captures a handful of screens to PNG so a visual theme/layout
## pass can actually be reviewed as pixels, not just smoke-test title text.
## Not wired into any shipped build path.
func _run_screenshot_test() -> void:
	var targets := ["Dashboard", "Selection", "Match", "Squad", "Facilities"]
	for i in range(targets.size()):
		show_screen(targets[i])
		await get_tree().process_frame
		await get_tree().process_frame
		var image := get_viewport().get_texture().get_image()
		image.save_png("res://../screenshots/godot_%s.png" % targets[i].to_lower().replace(" ", "_"))
	get_tree().quit(0)


## Cycles through every registered screen, printing a pass/fail summary and
## exiting with a non-zero status if any screen's title shows a backend
## error — a scriptable, no-GUI way to catch regressions across the whole
## nav tree instead of just the one screen squad_screen.gd's own test covers.
func _run_smoke_test() -> void:
	var failures := []
	for group in NAV_GROUPS:
		for screen_name in group[1]:
			show_screen(screen_name)
			var summary := _describe_screen(current_screen)
			print("SMOKE TEST [%s]: %s" % [screen_name, summary])
			if "backend error" in summary:
				failures.append(screen_name)
	if not _exercise_advance_day():
		failures.append("Dashboard advance_day flow")
	if not _exercise_row_click("Inbox"):
		failures.append("Inbox mark-read row click")
	if not _exercise_row_click("Transfers"):
		failures.append("Transfers submit-offer row click")
	if not _exercise_row_button("Offers"):
		failures.append("Offers accept/reject row button")
	if not _exercise_row_click("Staff Market"):
		failures.append("Staff Market sign row click")
	if not _exercise_row_button("Facilities"):
		failures.append("Facilities upgrade row button")
	if not _exercise_row_button("Staff"):
		failures.append("Staff release row button")
	if not _exercise_row_click("Selection"):
		failures.append("Selection toggle-XI row click")
	if not _exercise_row_button("Selection"):
		failures.append("Selection captain/keeper row button")
	if not _exercise_batting_order():
		failures.append("Selection batting-order up/down row button")
	if not _exercise_squad_tabs():
		failures.append("Squad Attributes tab switch")
	if failures.is_empty():
		print("SMOKE TEST: all %d screens OK" % _screen_count())
		get_tree().quit(0)
	else:
		print("SMOKE TEST: FAILED — %s" % ", ".join(failures))
		get_tree().quit(1)


## Exercises the first real interactive (write) flow end-to-end by emitting
## the Dashboard's actual button signal — not just calling the IPC method
## directly — so a broken signal connection would fail this too.
func _exercise_advance_day() -> bool:
	show_screen("Dashboard")
	var before_date := team_subtitle_label.text
	advance_button.pressed.emit()
	var summary := _describe_screen(current_screen)
	print("SMOKE TEST [Dashboard/advance_day]: %s -> %s (%s)" % [before_date, team_subtitle_label.text, summary])
	return "backend error" not in summary and team_subtitle_label.text != before_date


## Exercises a table_screen.gd row_action end-to-end by emitting a real
## mouse-click InputEvent on the first data row's gui_input signal — the
## same signal a genuine click delivers — not by calling the IPC method
## directly, so a broken wiring (wrong param names, unconnected signal)
## fails this too.
func _exercise_row_click(screen_name: String) -> bool:
	show_screen(screen_name)
	var screen := current_screen
	if not screen.has_node("ScrollContainer/RowList"):
		print("SMOKE TEST [%s/row-click]: not a table screen" % screen_name)
		return false
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	if row_list.get_child_count() < 2:
		print("SMOKE TEST [%s/row-click]: no data rows to click" % screen_name)
		return true
	var first_row := _row_hbox(row_list, 1)
	var event := InputEventMouseButton.new()
	event.pressed = true
	event.button_index = MOUSE_BUTTON_LEFT
	first_row.gui_input.emit(event)
	var summary := _describe_screen(current_screen)
	print("SMOKE TEST [%s/row-click]: %s" % [screen_name, summary])
	return "backend error" not in summary


## Exercises table_screen.gd's row_buttons (Accept/Reject-style multi-action
## rows) by pressing the first data row's first button — a real
## Button.pressed emit, same as _exercise_row_click does for whole-row
## actions.
func _exercise_row_button(screen_name: String) -> bool:
	show_screen(screen_name)
	var screen := current_screen
	if not screen.has_node("ScrollContainer/RowList"):
		print("SMOKE TEST [%s/row-button]: not a table screen" % screen_name)
		return false
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	if row_list.get_child_count() < 2:
		print("SMOKE TEST [%s/row-button]: no data rows with buttons" % screen_name)
		return true
	var first_row := _row_hbox(row_list, 1)
	var buttons := first_row.get_children().filter(func(c): return c is Button)
	if buttons.is_empty():
		print("SMOKE TEST [%s/row-button]: row has no buttons" % screen_name)
		return false
	buttons[0].pressed.emit()
	var summary := _describe_screen(current_screen)
	print("SMOKE TEST [%s/row-button]: %s" % [screen_name, summary])
	return "backend error" not in summary


## Exercises move_batting_up/down end-to-end: adds a second player to the XI
## (so there's someone to swap with — the first exercises already put one
## player in the XI as the topmost row), presses the first row's DOWN
## button, then checks the row order actually changed — not just that the
## call returned without error, same real-state-change standard as every
## other write-flow exercise in this file.
func _exercise_batting_order() -> bool:
	show_screen("Selection")
	var screen := current_screen
	if not screen.has_node("ScrollContainer/RowList"):
		print("SMOKE TEST [Selection/batting-order]: not a table screen")
		return false
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	if row_list.get_child_count() < 3:
		print("SMOKE TEST [Selection/batting-order]: fewer than 2 data rows to swap")
		return true
	# Don't assume anything about state left over from earlier exercises or
	# earlier smoke-test runs against the same persistent dev save (its XI
	# may already have players in it, or none) — explicitly guarantee the
	# first two rows are XI members before testing the reorder itself.
	_ensure_row_in_xi(screen, 1)
	_ensure_row_in_xi(screen, 2)
	row_list = screen.get_node("ScrollContainer/RowList")
	var first_row := _row_hbox(row_list, 1)
	var name_before: String = (first_row.get_child(1) as Label).text
	var buttons := first_row.get_children().filter(func(c): return c is Button)
	if buttons.is_empty():
		print("SMOKE TEST [Selection/batting-order]: no row buttons found")
		return false
	buttons[buttons.size() - 1].pressed.emit()  # DOWN is configured last
	row_list = screen.get_node("ScrollContainer/RowList")
	var name_after: String = (_row_hbox(row_list, 1).get_child(1) as Label).text
	var summary := _describe_screen(current_screen)
	print("SMOKE TEST [Selection/batting-order]: %s -> %s (%s)" % [name_before, name_after, summary])
	return "backend error" not in summary and name_before != name_after


## Clicks a Selection row to add it to the XI, but only if it isn't already
## a member (empty ORDER/C/WK label) — so batting-order testing works the
## same whether the persistent dev save's XI is empty or already populated.
func _ensure_row_in_xi(screen: Control, index: int) -> void:
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	if row_list.get_child_count() <= index:
		return
	var row := _row_hbox(row_list, index)
	var status_label := row.get_child(4) as Label
	if status_label.text.is_empty():
		var click := InputEventMouseButton.new()
		click.pressed = true
		click.button_index = MOUSE_BUTTON_LEFT
		row.gui_input.emit(click)


## table_screen.gd wraps each data row in a PanelContainer (for the zebra
## background) whose only child is the HBoxContainer that actually carries
## the row's gui_input connection and Label/Button children — smoke-test
## helpers need that inner container, not the panel wrapper.
func _row_hbox(row_list: VBoxContainer, index: int) -> HBoxContainer:
	return row_list.get_child(index).get_child(0) as HBoxContainer


func _row_header_text(row_list: VBoxContainer) -> String:
	var parts := []
	for child in _row_hbox(row_list, 0).get_children():
		if child is Label:
			parts.append((child as Label).text)
	return "/".join(parts)


## Exercises table_screen.gd's tabbed sub-navigation (Squad's GENERAL
## INFO/ATTRIBUTES tabs) by pressing the second tab's real Button.pressed
## signal and checking the header row actually shows different columns
## afterwards — not just that no error was thrown.
func _exercise_squad_tabs() -> bool:
	show_screen("Squad")
	var screen := current_screen
	if not ("_tab_buttons" in screen) or screen._tab_buttons.size() < 2:
		print("SMOKE TEST [Squad/tabs]: expected at least 2 tabs")
		return false
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	var header_before := _row_header_text(row_list)
	screen._tab_buttons[1].pressed.emit()
	row_list = screen.get_node("ScrollContainer/RowList")
	var header_after := _row_header_text(row_list)
	print("SMOKE TEST [Squad/tabs]: %s -> %s" % [header_before, header_after])
	return header_before != header_after and "BATTING" in header_after


func _describe_screen(screen: Control) -> String:
	if screen.has_node("Title"):
		return (screen.get_node("Title") as Label).text
	return "(no title label — placeholder or unrecognised screen)"


func _screen_count() -> int:
	var total := 0
	for group in NAV_GROUPS:
		total += group[1].size()
	return total


func _build_sidebar() -> void:
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_left", 8)
	margin.add_theme_constant_override("margin_right", 8)
	margin.add_theme_constant_override("margin_bottom", 12)
	margin.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sidebar.add_child(margin)
	var list := VBoxContainer.new()
	list.add_theme_constant_override("separation", 2)
	margin.add_child(list)
	for group in NAV_GROUPS:
		var section_label := Label.new()
		section_label.text = group[0]
		section_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		section_label.add_theme_font_size_override("font_size", 11)
		var section_margin := MarginContainer.new()
		section_margin.add_theme_constant_override("margin_top", 16)
		section_margin.add_theme_constant_override("margin_bottom", 4)
		section_margin.add_theme_constant_override("margin_left", 12)
		section_margin.add_child(section_label)
		list.add_child(section_margin)
		for screen_name in group[1]:
			var button := Button.new()
			button.focus_mode = Control.FOCUS_NONE
			button.custom_minimum_size = Vector2(0, 32)
			button.pressed.connect(_on_nav_pressed.bind(screen_name))
			var row := HBoxContainer.new()
			row.mouse_filter = Control.MOUSE_FILTER_IGNORE
			row.add_theme_constant_override("separation", 10)
			row.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
			row.alignment = BoxContainer.ALIGNMENT_BEGIN
			var icon := NavIcon.new()
			icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
			icon.set_kind(NAV_ICONS.get(screen_name, "dot"))
			row.add_child(icon)
			var label := Label.new()
			label.mouse_filter = Control.MOUSE_FILTER_IGNORE
			label.text = screen_name
			label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
			row.add_child(label)
			button.add_child(row)
			AppTheme.style_nav_button(button, false)
			list.add_child(button)
			_nav_buttons[screen_name] = button
			_nav_icons[screen_name] = icon
			_nav_labels[screen_name] = label


func _on_nav_pressed(screen_name: String) -> void:
	show_screen(screen_name)


func show_screen(screen_name: String) -> void:
	if current_screen:
		content.remove_child(current_screen)
		current_screen.queue_free()
		current_screen = null
	var instance := _instantiate(screen_name)
	content.add_child(instance)
	current_screen = instance
	if current_screen_name in _nav_buttons:
		AppTheme.style_nav_button(_nav_buttons[current_screen_name], false)
		_nav_icons[current_screen_name].set_colour(AppTheme.TEXT_SECONDARY)
		_nav_labels[current_screen_name].add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	current_screen_name = screen_name
	if screen_name in _nav_buttons:
		AppTheme.style_nav_button(_nav_buttons[screen_name], true)
		_nav_icons[screen_name].set_colour(AppTheme.GOLD)
		_nav_labels[screen_name].add_theme_color_override("font_color", AppTheme.GOLD)


func _instantiate(screen_name: String) -> Control:
	match screen_name:
		"Dashboard":
			return DASHBOARD_SCENE.instantiate()
		"Squad":
			var s := TABLE_SCENE.instantiate()
			s.configure("SQUAD", "get_squad", [
				{"key": "nationality", "header": "", "width": 32, "flag": true},
				{"key": "name", "header": "NAME", "width": 200},
				{"key": "age", "header": "AGE", "width": 80},
				{"key": "role", "header": "ROLE", "width": 160, "pill": true},
				{"key": "overall", "header": "OVR", "width": 80},
				{"key": "form", "header": "FORM", "width": 90, "bar": true},
				{"key": "morale", "header": "MORALE", "width": 90, "bar": true},
			], "players", {}, {}, "", [], [
				{"label": "ATTRIBUTES", "columns": [
					{"key": "nationality", "header": "", "width": 32, "flag": true},
					{"key": "name", "header": "NAME", "width": 200},
					{"key": "batting_avg", "header": "BATTING", "width": 100, "bar": true},
					{"key": "bowling_avg", "header": "BOWLING", "width": 100, "bar": true},
					{"key": "fielding_avg", "header": "FIELDING", "width": 100, "bar": true},
					{"key": "mental_avg", "header": "MENTAL", "width": 100, "bar": true},
				]},
			])
			return s
		"Training":
			return TRAINING_SCENE.instantiate()
		"Match":
			return MATCH_SCENE.instantiate()
		"Selection":
			var s := TABLE_SCENE.instantiate()
			s.configure("SELECTION", "get_selection", [
				{"key": "nationality", "header": "", "width": 32, "flag": true},
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "role", "header": "ROLE", "width": 140, "pill": true},
				{"key": "overall", "header": "OVR", "width": 70},
				{"key": "xi_status", "header": "ORDER/C/WK", "width": 100},
			], "players", {}, {"method": "toggle_xi", "params_from_row": {"player_id": "id"}}, "",
			[
				{"label": "CAPTAIN", "method": "set_captain", "params_from_row": {"player_id": "id"}},
				{"label": "KEEPER", "method": "set_keeper", "params_from_row": {"player_id": "id"}},
				{"label": "UP", "method": "move_batting_up", "params_from_row": {"player_id": "id"}},
				{"label": "DOWN", "method": "move_batting_down", "params_from_row": {"player_id": "id"}},
			])
			return s
		"Inbox":
			var s := TABLE_SCENE.instantiate()
			s.configure("INBOX", "get_inbox", [
				{"key": "priority", "header": "PRI", "width": 60},
				{"key": "title", "header": "TITLE", "width": 420},
				{"key": "timestamp", "header": "WHEN", "width": 160},
			], "messages", {}, {"method": "mark_message_read", "params_from_row": {"message_id": "id"}}, "read")
			return s
		"Recruitment":
			return RECRUITMENT_SCENE.instantiate()
		"Transfers":
			var s := TABLE_SCENE.instantiate()
			s.configure("TRANSFER MARKET", "get_transfer_market", [
				{"key": "nationality", "header": "", "width": 32, "flag": true},
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "age", "header": "AGE", "width": 60},
				{"key": "role", "header": "ROLE", "width": 140, "pill": true},
				{"key": "estimated_overall", "header": "OVR~", "width": 80},
				{"key": "asking_price", "header": "PRICE", "width": 120},
			], "players", {}, {"method": "submit_transfer_offer",
				"params_from_row": {"player_id": "id", "fee": "asking_price"},
				"params_fixed": {"wage": 5000}})
			return s
		"Offers":
			var s := TABLE_SCENE.instantiate()
			s.configure("TRANSFER OFFERS", "get_transfer_market", [
				{"key": "player_name", "header": "PLAYER", "width": 180},
				{"key": "from_name", "header": "FROM", "width": 160},
				{"key": "to_name", "header": "TO", "width": 160},
				{"key": "fee", "header": "FEE", "width": 120},
				{"key": "status", "header": "STATUS", "width": 100},
			], "offers", {}, {}, "", [
				{"label": "ACCEPT", "method": "resolve_transfer_offer",
					"params_from_row": {"offer_id": "id"}, "params_fixed": {"accept": true}},
				{"label": "REJECT", "method": "resolve_transfer_offer",
					"params_from_row": {"offer_id": "id"}, "params_fixed": {"accept": false}},
			])
			return s
		"Staff":
			var s := TABLE_SCENE.instantiate()
			s.configure("STAFF", "get_staff", [
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "role", "header": "ROLE", "width": 160},
				{"key": "group_name", "header": "DEPT", "width": 120},
				{"key": "age", "header": "AGE", "width": 60},
				{"key": "overall", "header": "OVR", "width": 80},
			], "staff", {}, {}, "", [
				{"label": "RELEASE", "method": "release_staff", "params_from_row": {"staff_id": "id"}},
			])
			return s
		"Staff Market":
			var s := TABLE_SCENE.instantiate()
			s.configure("STAFF MARKET", "get_staff_market", [
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "role", "header": "ROLE", "width": 160},
				{"key": "club_name", "header": "CLUB", "width": 160},
				{"key": "overall", "header": "OVR", "width": 70},
				{"key": "fee", "header": "FEE", "width": 110},
				{"key": "wage", "header": "WAGE", "width": 100},
			], "staff", {}, {"method": "sign_staff",
				"params_from_row": {"staff_id": "id", "from_team": "team_id", "fee": "fee", "wage": "wage"}})
			return s
		"Finances":
			var s := TABLE_SCENE.instantiate()
			s.configure("FINANCES", "get_finances", [
				{"key": "date", "header": "DATE", "width": 120},
				{"key": "category", "header": "CATEGORY", "width": 180},
				{"key": "kind", "header": "TYPE", "width": 100},
				{"key": "amount", "header": "AMOUNT", "width": 140},
				{"key": "description", "header": "NOTE", "width": 300},
			], "transactions")
			return s
		"Facilities":
			var s := TABLE_SCENE.instantiate()
			s.configure("FACILITIES", "get_facilities", [
				{"key": "facility", "header": "FACILITY", "width": 220},
				{"key": "level", "header": "LEVEL", "width": 100},
				{"key": "status", "header": "STATUS", "width": 140},
			], "facilities", {}, {}, "", [
				{"label": "UPGRADE", "method": "upgrade_facility", "params_from_row": {"facility": "facility"}},
			])
			return s
		"Youth Academy":
			var s := TABLE_SCENE.instantiate()
			s.configure("YOUTH ACADEMY", "get_youth_academy", [
				{"key": "nationality", "header": "", "width": 32, "flag": true},
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "age", "header": "AGE", "width": 60},
				{"key": "role", "header": "ROLE", "width": 140, "pill": true},
				{"key": "overall", "header": "OVR", "width": 80},
				{"key": "potential", "header": "POT", "width": 80},
			], "players")
			return s
		"Medical Centre":
			var s := TABLE_SCENE.instantiate()
			s.configure("MEDICAL CENTRE", "get_medical", [
				{"key": "player_name", "header": "PLAYER", "width": 180},
				{"key": "player_role", "header": "ROLE", "width": 140},
				{"key": "severity", "header": "SEVERITY", "width": 120},
				{"key": "start_date", "header": "SINCE", "width": 130},
				{"key": "return_date", "header": "RETURNS", "width": 130},
			], "injuries")
			return s
		"Career":
			var s := TABLE_SCENE.instantiate()
			s.configure("HONOURS", "get_honours", [
				{"key": "season", "header": "SEASON", "width": 100},
				{"key": "title", "header": "HONOUR", "width": 300},
				{"key": "awarded_on", "header": "DATE", "width": 160},
			], "honours")
			return s
		_:
			var placeholder := PLACEHOLDER_SCENE.instantiate()
			placeholder.set_screen_name(screen_name)
			return placeholder
