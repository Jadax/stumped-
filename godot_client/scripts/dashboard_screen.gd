extends Control
## Portal / Dashboard — the FM26-style "home screen" combining fixtures,
## standings, and inbox (docs/UX_ROADMAP.md Portal section), fed by
## get_dashboard over the IPC bridge.

@onready var title_label: Label = $Title
@onready var teams_row: HBoxContainer = $Row/FixtureCard/Box/TeamsRow
@onready var home_crest: PanelContainer = $Row/FixtureCard/Box/TeamsRow/HomeCrest
@onready var home_crest_label: Label = $Row/FixtureCard/Box/TeamsRow/HomeCrest/Label
@onready var home_name_label: Label = $Row/FixtureCard/Box/TeamsRow/HomeName
@onready var away_name_label: Label = $Row/FixtureCard/Box/TeamsRow/AwayName
@onready var away_crest: PanelContainer = $Row/FixtureCard/Box/TeamsRow/AwayCrest
@onready var away_crest_label: Label = $Row/FixtureCard/Box/TeamsRow/AwayCrest/Label
@onready var fixture_label: Label = $Row/FixtureCard/Box/Value
@onready var standings_list: VBoxContainer = $Row/StandingsCard/Box/List
@onready var messages_list: VBoxContainer = $Row/MessagesCard/Box/List
@onready var team_talk_tones: HBoxContainer = $Row/FixtureCard/Box/TeamTalk/Tones
@onready var team_talk_reaction: Label = $Row/FixtureCard/Box/TeamTalk/Reaction


func _ready() -> void:
	_style_crest(home_crest, home_crest_label)
	_style_crest(away_crest, away_crest_label)
	away_name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	home_name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	$Row/FixtureCard/Box/TeamsRow/Vs.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	for button in team_talk_tones.get_children():
		(button as Button).pressed.connect(_on_team_talk_pressed.bind(button.name))
	refresh()


func _style_crest(crest: PanelContainer, label: Label) -> void:
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.ACCENT
	box.set_corner_radius_all(18)
	crest.add_theme_stylebox_override("panel", box)
	label.add_theme_color_override("font_color", AppTheme.BACKGROUND)
	label.add_theme_font_size_override("font_size", 13)


static func _initials(name: String) -> String:
	var initials := ""
	for word in name.split(" ", false):
		if not word.is_empty():
			initials += word[0]
	return initials.substr(0, 2).to_upper()


func refresh() -> void:
	var response := IpcBridge.call_method("get_dashboard")
	if response.has("error"):
		title_label.text = "PORTAL — backend error: %s" % response["error"]
		push_error("DashboardScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	var team: Dictionary = result.get("team", {})
	title_label.text = "%s — Division %s" % [team.get("name", "?"), JsonFormat.value(team.get("division", "?"))]

	var fixture = result.get("fixture")
	teams_row.visible = fixture != null
	if fixture:
		var home_name: String = fixture.get("home_name", "?")
		var away_name: String = fixture.get("away_name", "?")
		home_name_label.text = home_name
		away_name_label.text = away_name
		home_crest_label.text = _initials(home_name)
		away_crest_label.text = _initials(away_name)
		fixture_label.text = "%s, %s" % [fixture.get("format", "?"), fixture.get("date", "?")]
		fixture_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	else:
		fixture_label.text = "No fixture scheduled"
		fixture_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT

	for child in standings_list.get_children():
		child.queue_free()
	for row in result.get("standings", []).slice(0, 6):
		var mine: bool = row.get("team_id") == team.get("id")
		var line := HBoxContainer.new()
		line.add_theme_constant_override("separation", 8)
		var badge := PanelContainer.new()
		badge.custom_minimum_size = Vector2(22, 22)
		var badge_box := StyleBoxFlat.new()
		badge_box.bg_color = AppTheme.GOLD if mine else AppTheme.BORDER
		badge_box.set_corner_radius_all(11)
		badge.add_theme_stylebox_override("panel", badge_box)
		var badge_label := Label.new()
		badge_label.text = JsonFormat.value(row.get("position", 0))
		badge_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		badge_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		badge_label.add_theme_font_size_override("font_size", 12)
		badge_label.add_theme_color_override("font_color", AppTheme.BACKGROUND if mine else AppTheme.TEXT_SECONDARY)
		badge.add_child(badge_label)
		line.add_child(badge)
		var label := Label.new()
		label.text = "%s — %d pts" % [row.get("name", "?"), row.get("points", 0)]
		if mine:
			label.add_theme_color_override("font_color", AppTheme.GOLD)
		line.add_child(label)
		standings_list.add_child(line)

	for child in messages_list.get_children():
		child.queue_free()
	_refresh_team_talk()

	for message in result.get("messages", []):
		var line := HBoxContainer.new()
		line.add_theme_constant_override("separation", 8)
		var dot := ColorRect.new()
		dot.custom_minimum_size = Vector2(8, 8)
		if message.get("priority", "") == "HIGH":
			dot.color = AppTheme.DANGER
		elif message.get("priority", "") == "MEDIUM":
			dot.color = AppTheme.GOLD
		else:
			dot.color = AppTheme.TEXT_MUTED
		var dot_wrap := Control.new()
		dot_wrap.custom_minimum_size = Vector2(8, 18)
		dot.position = Vector2(0, 5)
		dot_wrap.add_child(dot)
		line.add_child(dot_wrap)
		var label := Label.new()
		var unread := not bool(message.get("read", false))
		label.text = message.get("title", "?")
		if not unread:
			label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		line.add_child(label)
		messages_list.add_child(line)


## New in v0.81.0: the first manager-driven morale lever — previously
## squad morale only ever moved via passive events (match results,
## contracts, promotion/relegation). Ports src/models/team_talks.py's
## deliver_team_talk via the new IPC method of the same name.
func _refresh_team_talk() -> void:
	var response := IpcBridge.call_method("get_team_talk_status")
	if response.has("error"):
		team_talk_reaction.text = "Team talk unavailable: %s" % response["error"]
		for button in team_talk_tones.get_children():
			(button as Button).disabled = true
		return
	var available: bool = response["result"].get("available", false)
	for button in team_talk_tones.get_children():
		(button as Button).disabled = not available
	team_talk_reaction.text = "" if available else "Already spoken to the squad today."


func _on_team_talk_pressed(tone: String) -> void:
	var response := IpcBridge.call_method("deliver_team_talk", {"tone": tone})
	if response.has("error"):
		team_talk_reaction.text = "Team talk failed: %s" % response["error"]
		return
	var result: Dictionary = response["result"]
	var delta: int = result.get("delta", 0)
	team_talk_reaction.text = "%s (%s%d morale)" % [result.get("reaction", ""), "+" if delta >= 0 else "", delta]
	for button in team_talk_tones.get_children():
		(button as Button).disabled = true
