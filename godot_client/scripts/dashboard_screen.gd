extends Control
## Portal / Dashboard — the FM26-style "home screen" combining fixtures,
## standings, and inbox (docs/UX_ROADMAP.md Portal section), fed by
## get_dashboard over the IPC bridge.

@onready var title_label: Label = $Title
@onready var advance_button: Button = $AdvanceButton
@onready var fixture_label: Label = $Row/FixtureCard/Box/Value
@onready var standings_list: VBoxContainer = $Row/StandingsCard/Box/List
@onready var messages_list: VBoxContainer = $Row/MessagesCard/Box/List


func _ready() -> void:
	advance_button.pressed.connect(_on_advance_pressed)
	refresh()


## The first interactive (not read-only) flow ported: this is what
## actually drives the game loop forward, exactly like main.py's
## "continue_button" wired to advance_campaign_day().
func _on_advance_pressed() -> void:
	advance_button.disabled = true
	var response := IpcBridge.call_method("advance_day")
	advance_button.disabled = false
	if response.has("error"):
		push_error("DashboardScreen: advance_day failed: %s" % response["error"])
		return
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_dashboard")
	if response.has("error"):
		title_label.text = "PORTAL — backend error: %s" % response["error"]
		push_error("DashboardScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	var team: Dictionary = result["team"]
	title_label.text = "%s — Division %s" % [team.get("name", "?"), JsonFormat.value(team.get("division", "?"))]

	var fixture = result.get("fixture")
	if fixture:
		fixture_label.text = "%s vs %s — %s, %s" % [fixture.get("home_name", "?"), fixture.get("away_name", "?"),
			fixture.get("format", "?"), fixture.get("date", "?")]
	else:
		fixture_label.text = "No fixture scheduled"

	for child in standings_list.get_children():
		child.queue_free()
	for row in result.get("standings", []).slice(0, 6):
		var label := Label.new()
		var mine: bool = row.get("team_id") == team.get("id")
		label.text = "%d. %s — %d pts" % [row.get("position", 0), row.get("name", "?"), row.get("points", 0)]
		if mine:
			label.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
		standings_list.add_child(label)

	for child in messages_list.get_children():
		child.queue_free()
	for message in result.get("messages", []):
		var label := Label.new()
		var unread := not bool(message.get("read", false))
		label.text = "%s%s" % ["● " if unread else "  ", message.get("title", "?")]
		messages_list.add_child(label)
