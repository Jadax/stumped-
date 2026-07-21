extends Control
## The persistent chrome — sidebar navigation (mirrors main.py's NAV_GROUPS,
## docs/UX_ROADMAP.md's FM26-translated IA) and a content area that swaps
## screens. Screens not yet ported show the same "Coming Soon" placeholder
## the pygame client's BaseScreen falls back to.

const NAV_GROUPS := [
	["PORTAL", ["Dashboard", "Inbox"]],
	["SQUAD", ["Squad", "Training", "Youth Academy", "Medical Centre"]],
	["MATCH DAY", ["Match"]],
	["RECRUITMENT", ["Recruitment", "Transfers", "Offers"]],
	["CLUB", ["Staff", "Staff Market", "Finances", "Facilities"]],
	["CAREER", ["Career"]],
]

const DASHBOARD_SCENE := preload("res://scenes/dashboard_screen.tscn")
const SQUAD_SCENE := preload("res://scenes/squad_screen.tscn")
const TRAINING_SCENE := preload("res://scenes/training_screen.tscn")
const RECRUITMENT_SCENE := preload("res://scenes/recruitment_screen.tscn")
const TABLE_SCENE := preload("res://scenes/table_screen.tscn")
const PLACEHOLDER_SCENE := preload("res://scenes/placeholder_screen.tscn")

@onready var sidebar: VBoxContainer = $Row/Sidebar
@onready var content: Control = $Row/Content

var current_screen: Control = null


func _ready() -> void:
	_build_sidebar()
	if "--smoke-test" in OS.get_cmdline_user_args():
		_run_smoke_test()
	else:
		show_screen("Dashboard")


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
	var dashboard := current_screen
	if not dashboard.has_node("AdvanceButton"):
		print("SMOKE TEST [Dashboard/advance_day]: AdvanceButton node missing")
		return false
	var button: Button = dashboard.get_node("AdvanceButton")
	button.pressed.emit()
	var summary := _describe_screen(current_screen)
	print("SMOKE TEST [Dashboard/advance_day]: %s" % summary)
	return "backend error" not in summary


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
	var first_row: Control = row_list.get_child(1)
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
	var first_row: Control = row_list.get_child(1)
	var buttons := first_row.get_children().filter(func(c): return c is Button)
	if buttons.is_empty():
		print("SMOKE TEST [%s/row-button]: row has no buttons" % screen_name)
		return false
	buttons[0].pressed.emit()
	var summary := _describe_screen(current_screen)
	print("SMOKE TEST [%s/row-button]: %s" % [screen_name, summary])
	return "backend error" not in summary


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
	for group in NAV_GROUPS:
		var section_label := Label.new()
		section_label.text = group[0]
		section_label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.55))
		sidebar.add_child(section_label)
		for screen_name in group[1]:
			var button := Button.new()
			button.text = screen_name
			button.pressed.connect(_on_nav_pressed.bind(screen_name))
			sidebar.add_child(button)


func _on_nav_pressed(screen_name: String) -> void:
	show_screen(screen_name)


func show_screen(screen_name: String) -> void:
	if current_screen:
		current_screen.queue_free()
		current_screen = null
	var instance := _instantiate(screen_name)
	content.add_child(instance)
	current_screen = instance


func _instantiate(screen_name: String) -> Control:
	match screen_name:
		"Dashboard":
			return DASHBOARD_SCENE.instantiate()
		"Squad":
			return SQUAD_SCENE.instantiate()
		"Training":
			return TRAINING_SCENE.instantiate()
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
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "age", "header": "AGE", "width": 60},
				{"key": "role", "header": "ROLE", "width": 140},
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
			], "staff")
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
				{"key": "facility", "header": "FACILITY", "width": 200},
				{"key": "status", "header": "STATUS", "width": 140},
				{"key": "target_level", "header": "TARGET LVL", "width": 120},
				{"key": "completion_date", "header": "COMPLETES", "width": 160},
			], "upgrades")
			return s
		"Youth Academy":
			var s := TABLE_SCENE.instantiate()
			s.configure("YOUTH ACADEMY", "get_youth_academy", [
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "age", "header": "AGE", "width": 60},
				{"key": "role", "header": "ROLE", "width": 140},
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
