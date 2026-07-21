extends Control
## The persistent chrome — sidebar navigation (mirrors main.py's NAV_GROUPS,
## docs/UX_ROADMAP.md's FM26-translated IA) and a content area that swaps
## screens. Screens not yet ported show the same "Coming Soon" placeholder
## the pygame client's BaseScreen falls back to.

const NAV_GROUPS := [
	["PORTAL", ["Dashboard", "Inbox"]],
	["SQUAD", ["Squad", "Training", "Youth Academy", "Medical Centre"]],
	["MATCH DAY", ["Match"]],
	["RECRUITMENT", ["Recruitment", "Transfers"]],
	["CLUB", ["Staff", "Finances", "Facilities"]],
	["CAREER", ["Career"]],
]

const DASHBOARD_SCENE := preload("res://scenes/dashboard_screen.tscn")
const SQUAD_SCENE := preload("res://scenes/squad_screen.tscn")
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
	if failures.is_empty():
		print("SMOKE TEST: all %d screens OK" % _screen_count())
		get_tree().quit(0)
	else:
		print("SMOKE TEST: FAILED — %s" % ", ".join(failures))
		get_tree().quit(1)


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
		"Inbox":
			var s := TABLE_SCENE.instantiate()
			s.configure("INBOX", "get_inbox", [
				{"key": "priority", "header": "PRI", "width": 60},
				{"key": "title", "header": "TITLE", "width": 420},
				{"key": "timestamp", "header": "WHEN", "width": 160},
			], "messages")
			return s
		"Transfers":
			var s := TABLE_SCENE.instantiate()
			s.configure("TRANSFER MARKET", "get_transfer_market", [
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "age", "header": "AGE", "width": 60},
				{"key": "role", "header": "ROLE", "width": 140},
				{"key": "estimated_overall", "header": "OVR~", "width": 80},
				{"key": "asking_price", "header": "PRICE", "width": 120},
			], "players")
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
