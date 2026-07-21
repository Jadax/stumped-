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


func _ready() -> void:
	var response := IpcBridge.call_method("get_recruitment")
	if response.has("error"):
		title_label.text = "RECRUITMENT — backend error: %s" % response["error"]
		push_error("RecruitmentScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	var team: Dictionary = result["team"]
	title_label.text = "RECRUITMENT — %s" % team.get("name", "?")

	var gaps: Array = result.get("gaps", [])
	if gaps.is_empty():
		objectives_value.text = "Strengthen %s — every role is at target headcount." % result.get("weakest_group", "?")
	else:
		var first = gaps[0]
		objectives_value.text = "Fill %s — only %s in the squad." % [first.get("role", "?"), JsonFormat.value(first.get("have", 0))]

	for child in gaps_list.get_children():
		child.queue_free()
	if gaps.is_empty():
		_add_label(gaps_list, "Every role meets its target headcount.", Color(0.4, 0.85, 0.5))
	for gap in gaps:
		_add_label(gaps_list, "%s — %s short" % [gap.get("role", "?"), JsonFormat.value(gap.get("have", 0))], Color(0.9, 0.4, 0.4))

	for child in contracts_list.get_children():
		child.queue_free()
	var expiring: Array = result.get("contract_watch", [])
	if expiring.is_empty():
		_add_label(contracts_list, "No contracts expiring within a year.", Color(0.4, 0.85, 0.5))
	for player in expiring:
		_add_label(contracts_list, "%s — %s" % [player.get("name", "?"), player.get("status", "?")], Color(1.0, 0.85, 0.3))

	for child in scouting_list.get_children():
		child.queue_free()
	var assignments: Array = result.get("active_assignments", [])
	if assignments.is_empty():
		_add_label(scouting_list, "No scouts on assignment.", Color(0.6, 0.6, 0.65))
	for assignment in assignments:
		_add_label(scouting_list, "%s → %s (%sd left)" % [assignment.get("scout_name", "?"),
			assignment.get("target_name", "?"), JsonFormat.value(assignment.get("days_remaining", 0))], Color(1, 1, 1))


func _add_label(parent: VBoxContainer, value: String, colour: Color) -> void:
	var label := Label.new()
	label.text = value
	label.add_theme_color_override("font_color", colour)
	parent.add_child(label)
