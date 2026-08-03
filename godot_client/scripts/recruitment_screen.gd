extends Control
## Recruitment Hub — tiled front page over squad-gap/contract-watch/
## scouting data (docs/UX_ROADMAP.md), fed by get_recruitment which wraps
## the same src/models/recruitment.py logic the pygame RecruitmentHubScreen
## uses, so both clients apply identical rules.

@onready var title_label: Label = $Title
@onready var objectives_value: Label = $Row/ObjectivesCard/Box/Value
@onready var gaps_list: VBoxContainer = $Row/GapsCard/Box/List
@onready var contracts_list: VBoxContainer = $Row/ContractsCard/Box/List
@onready var scouting_list: VBoxContainer = $Row/ScoutingCard/Box/List


## Mirrors ui/recruitment.py's RecruitmentHubScreen shortcut buttons —
## a tiled front page over Transfers/Staff Market/Academy, so jumping to
## the relevant screen doesn't require the sidebar.
func _on_nav_button_pressed(screen_name: String) -> void:
	var shell := get_tree().get_first_node_in_group("shell")
	if shell:
		shell.show_screen(screen_name)


func _ready() -> void:
	$NavButtons/Transfers.pressed.connect(_on_nav_button_pressed.bind("Transfers"))
	$NavButtons/StaffMarket.pressed.connect(_on_nav_button_pressed.bind("Staff Market"))
	$NavButtons/Academy.pressed.connect(_on_nav_button_pressed.bind("Youth Academy"))
	refresh()


## Was previously only ever called once from _ready() — shell.gd's
## _on_advance_pressed() calls current_screen.refresh() on every other
## screen after Advance Day, so Recruitment was silently the one screen
## that kept showing stale squad gaps/contract watch/scouting data.
func refresh() -> void:
	var response := IpcBridge.call_method("get_recruitment")
	if response.has("error"):
		title_label.text = "RECRUITMENT — backend error: %s" % response["error"]
		push_error("RecruitmentScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	var team: Dictionary = result.get("team", {})
	title_label.text = "RECRUITMENT — %s" % team.get("name", "?")

	var gaps: Array = result.get("gaps", [])
	if gaps.is_empty():
		objectives_value.text = "Strengthen %s — every role is at target headcount." % result.get("weakest_group", "?")
	else:
		var first = gaps[0]
		objectives_value.text = "Fill %s — only %s in the squad." % [first.get("role", "?"), JsonFormat.value(first.get("have", 0))]

	# v4.24.0 fix: these were raw hardcoded Color() literals left over from
	# the pre-v0.84.0 dark theme (a near-white Color(1,1,1) for the
	# scouting list was nearly invisible against the warm light background
	# that replaced it) — the v0.84.0 hardcoded-colour sweep only covered
	# .tscn files, so this .gd file's inline colours were missed. Now uses
	# the same AppTheme palette every other screen reads from.
	for child in gaps_list.get_children():
		child.queue_free()
	if gaps.is_empty():
		_add_label(gaps_list, "Every role meets its target headcount.", AppTheme.HEADER_GREEN)
	for gap in gaps:
		_add_label(gaps_list, "%s — %s short" % [gap.get("role", "?"), JsonFormat.value(gap.get("have", 0))], AppTheme.DANGER)

	for child in contracts_list.get_children():
		child.queue_free()
	var expiring: Array = result.get("contract_watch", [])
	if expiring.is_empty():
		_add_label(contracts_list, "No contracts expiring within a year.", AppTheme.HEADER_GREEN)
	for player in expiring:
		_add_label(contracts_list, "%s — %s" % [player.get("name", "?"), player.get("status", "?")], AppTheme.GOLD)

	for child in scouting_list.get_children():
		child.queue_free()
	var assignments: Array = result.get("active_assignments", [])
	if assignments.is_empty():
		_add_label(scouting_list, "No scouts on assignment.", AppTheme.TEXT_MUTED)
	for assignment in assignments:
		_add_label(scouting_list, "%s → %s (%sd left)" % [assignment.get("scout_name", "?"),
			assignment.get("target_name", "?"), JsonFormat.value(assignment.get("days_remaining", 0))], AppTheme.TEXT_PRIMARY)


func _add_label(parent: VBoxContainer, value: String, colour: Color) -> void:
	var label := Label.new()
	label.text = value
	label.add_theme_color_override("font_color", colour)
	parent.add_child(label)
