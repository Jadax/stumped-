extends Control
## New in v0.81.0: the first manager-driven lever on board confidence —
## previously it only ever moved via the passive season-end review
## (src/models/career.py's board_confidence, called once a season). Ports
## src/models/press_conference.py's press_conference_question/
## answer_press_conference via the get_press_conference/answer_press_conference
## IPC methods. Gated to once a week (see ipc_server.py).

@onready var title_label: Label = $Title
@onready var question_label: Label = $Card/Box/Question
@onready var tones: HBoxContainer = $Card/Box/Tones
@onready var result_label: Label = $Card/Box/Result


func _ready() -> void:
	for button in tones.get_children():
		(button as Button).pressed.connect(_on_tone_pressed.bind(button.name))
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_press_conference")
	if response.has("error"):
		title_label.text = "PRESS CONFERENCE — backend error: %s" % response["error"]
		push_error("PressConferenceScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	var available: bool = result.get("available", false)
	question_label.text = str(result.get("question", "—"))
	for button in tones.get_children():
		(button as Button).disabled = not available
	result_label.text = "" if available else "No press conference scheduled — check back next week."
	title_label.text = "PRESS CONFERENCE"


func _on_tone_pressed(tone: String) -> void:
	var response := IpcBridge.call_method("answer_press_conference", {"tone": tone})
	if response.has("error"):
		result_label.text = "Couldn't answer: %s" % response["error"]
		return
	var result: Dictionary = response["result"]
	var confidence_delta: int = result.get("confidence_delta", 0)
	var morale_delta: int = result.get("morale_delta", 0)
	result_label.text = ("%s\nBoard confidence: %s (%s%d) — now %s (%d)\nSquad morale %s%d" % [
		result.get("quote", ""),
		result.get("confidence_label", "—"), "+" if confidence_delta >= 0 else "", confidence_delta,
		result.get("confidence_label", "—"), result.get("confidence_score", 0),
		"+" if morale_delta >= 0 else "", morale_delta,
	])
	for button in tones.get_children():
		(button as Button).disabled = true
