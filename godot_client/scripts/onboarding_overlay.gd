extends Control
## First-run guided tutorial card — ports database.py's ONBOARDING_STEPS/
## get_onboarding_state/advance_onboarding/dismiss_onboarding (exposed over
## IPC since v0.68.0 but previously never consumed by any UI in either
## client, despite a prior docs claim that pygame had it). Mirrors pygame's
## OnboardingOverlay widget: shell.gd shows/hides this per matching screen.

signal advanced
signal skipped

@onready var title_label: Label = $Card/Box/Title
@onready var step_label: Label = $Card/Box/StepLabel
@onready var description_label: Label = $Card/Box/Description
@onready var next_button: Button = $Card/Box/Buttons/NextButton
@onready var skip_button: Button = $Card/Box/Buttons/SkipButton


func _ready() -> void:
	next_button.pressed.connect(func(): advanced.emit())
	skip_button.pressed.connect(func(): skipped.emit())
	modulate.a = 0.0
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.CARD
	box.set_corner_radius_all(12)
	box.set_border_width_all(1)
	box.border_color = AppTheme.BORDER
	box.content_margin_left = 24
	box.content_margin_right = 24
	box.content_margin_top = 20
	box.content_margin_bottom = 20
	$Card.add_theme_stylebox_override("panel", box)
	step_label.add_theme_color_override("font_color", AppTheme.GOLD)
	description_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)


func show_step(step: Dictionary, step_number: int, total_steps: int) -> void:
	title_label.text = str(step.get("title", "")).to_upper()
	step_label.text = "STEP %d OF %d" % [step_number, total_steps]
	description_label.text = str(step.get("description", ""))
	var hints := [
		"Next: meet the squad that will define your first season.",
		"Next: build a match-day XI from these players.",
		"Next: set the training plan that shapes development.",
		"Next: find the next player who can change your season.",
		"Next: your first strategic test is waiting on match day.",
		"Next: review the financial pressure behind each decision."
	]
	if step_number <= hints.size() and step_number < total_steps:
		description_label.text += "\n\n" + hints[step_number - 1]
	next_button.text = "FINISH" if step_number == total_steps else "NEXT"
	visible = true
	var tween := create_tween()
	tween.tween_property(self, "modulate:a", 1.0, 0.22)


func hide_overlay() -> void:
	var tween := create_tween()
	tween.tween_property(self, "modulate:a", 0.0, 0.18)
	tween.tween_callback(func(): visible = false)
