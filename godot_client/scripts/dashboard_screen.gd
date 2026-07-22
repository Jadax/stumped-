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


func _ready() -> void:
	_style_crest(home_crest, home_crest_label)
	_style_crest(away_crest, away_crest_label)
	away_name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	home_name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	$Row/FixtureCard/Box/TeamsRow/Vs.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
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
	var team: Dictionary = result["team"]
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
