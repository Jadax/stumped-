extends Control

@onready var title_label: Label = $Title
@onready var teams_row: HBoxContainer = $Bottom/Left/FixtureCard/Box/TeamsRow
@onready var home_crest: PanelContainer = $Bottom/Left/FixtureCard/Box/TeamsRow/HomeCrest
@onready var home_crest_label: Label = $Bottom/Left/FixtureCard/Box/TeamsRow/HomeCrest/Label
@onready var home_name_label: Label = $Bottom/Left/FixtureCard/Box/TeamsRow/HomeName
@onready var away_name_label: Label = $Bottom/Left/FixtureCard/Box/TeamsRow/AwayName
@onready var away_crest: PanelContainer = $Bottom/Left/FixtureCard/Box/TeamsRow/AwayCrest
@onready var away_crest_label: Label = $Bottom/Left/FixtureCard/Box/TeamsRow/AwayCrest/Label
@onready var fixture_label: Label = $Bottom/Left/FixtureCard/Box/Value
@onready var standings_list: VBoxContainer = $Bottom/Right/StandingsCard/Box/List
@onready var messages_list: VBoxContainer = $Bottom/Right/MessagesCard/Box/List
@onready var team_talk_tones: HBoxContainer = $Bottom/Left/FixtureCard/Box/TeamTalk/Tones
@onready var team_talk_reaction: Label = $Bottom/Left/FixtureCard/Box/TeamTalk/Reaction

@onready var squad_tile: Label = $Tiles/SquadTile/Box/Value
@onready var league_tile: Label = $Tiles/LeagueTile/Box/Value
@onready var cash_tile: Label = $Tiles/CashTile/Box/Value
@onready var confidence_tile: Label = $Tiles/ConfidenceTile/Box/Value


func _ready() -> void:
	_style_crest(home_crest, home_crest_label)
	_style_crest(away_crest, away_crest_label)
	away_name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	home_name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	$Bottom/Left/FixtureCard/Box/TeamsRow/Vs.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	for button in team_talk_tones.get_children():
		(button as Button).pressed.connect(_on_team_talk_pressed.bind(button.name))
	_style_cards()
	refresh()


func _style_cards() -> void:
	for card_path in ["Tiles/SquadTile", "Tiles/LeagueTile", "Tiles/CashTile", "Tiles/ConfidenceTile",
		"Bottom/Left/FixtureCard", "Bottom/Right/StandingsCard", "Bottom/Right/MessagesCard"]:
		var card := get_node_or_null(card_path)
		if card and card is PanelContainer:
			card.add_theme_stylebox_override("panel", AppTheme.make_card(false))
	for label_path in ["Tiles/SquadTile/Box/Label", "Tiles/LeagueTile/Box/Label",
		"Tiles/CashTile/Box/Label", "Tiles/ConfidenceTile/Box/Label"]:
		var lbl := get_node_or_null(label_path)
		if lbl:
			lbl.add_theme_font_size_override("font_size", 10)
			lbl.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	for val_path in ["Tiles/SquadTile/Box/Value", "Tiles/LeagueTile/Box/Value",
		"Tiles/CashTile/Box/Value", "Tiles/ConfidenceTile/Box/Value"]:
		var val := get_node_or_null(val_path)
		if val:
			val.add_theme_font_size_override("font_size", 16)
			val.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)


func _style_crest(crest: PanelContainer, label: Label) -> void:
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.ACCENT
	box.set_corner_radius_all(20)
	box.set_border_width_all(2)
	box.border_color = AppTheme.GOLD
	crest.add_theme_stylebox_override("panel", box)
	label.add_theme_color_override("font_color", AppTheme.CARD)
	label.add_theme_font_size_override("font_size", 14)


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
	var date_str: String = str(result.get("date", ""))
	title_label.text = "PORTAL — %s | %s" % [team.get("name", "?"), date_str]

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

	_refresh_international_fixtures()

	for child in standings_list.get_children():
		child.queue_free()
	for row in result.get("standings", []).slice(0, 6):
		var mine: bool = row.get("team_id") == team.get("id")
		var line := HBoxContainer.new()
		line.add_theme_constant_override("separation", 10)
		if mine:
			var highlight := StyleBoxFlat.new()
			highlight.bg_color = AppTheme.ACTIVE
			highlight.set_corner_radius_all(4)
			highlight.content_margin_left = 6
			highlight.content_margin_right = 6
			line.add_theme_stylebox_override("panel", highlight)
		var badge := PanelContainer.new()
		badge.custom_minimum_size = Vector2(24, 24)
		var badge_box := StyleBoxFlat.new()
		badge_box.bg_color = AppTheme.GOLD if mine else AppTheme.BORDER
		badge_box.set_corner_radius_all(12)
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
			label.add_theme_font_size_override("font_size", 13)
		else:
			label.add_theme_font_size_override("font_size", 12)
		line.add_child(label)
		standings_list.add_child(line)

	for child in messages_list.get_children():
		child.queue_free()
	_refresh_team_talk()

	for message in result.get("messages", []).slice(0, 5):
		var line := HBoxContainer.new()
		line.add_theme_constant_override("separation", 8)
		var dot := ColorRect.new()
		dot.custom_minimum_size = Vector2(6, 6)
		if message.get("priority", "") == "HIGH":
			dot.color = AppTheme.DANGER
		elif message.get("priority", "") == "MEDIUM":
			dot.color = AppTheme.GOLD
		else:
			dot.color = AppTheme.TEXT_MUTED
		var dot_wrap := Control.new()
		dot_wrap.custom_minimum_size = Vector2(6, 18)
		dot.position = Vector2(0, 6)
		dot_wrap.add_child(dot)
		line.add_child(dot_wrap)
		var label := Label.new()
		var unread := not bool(message.get("read", false))
		label.text = message.get("title", "?")
		if unread:
			label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
			label.add_theme_font_size_override("font_size", 13)
		else:
			label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
			label.add_theme_font_size_override("font_size", 12)
		line.add_child(label)
		messages_list.add_child(line)

	_refresh_tiles()


func _refresh_tiles() -> void:
	var resp := IpcBridge.call_method("get_data_hub")
	if resp.has("error"):
		return
	var d: Dictionary = resp["result"]
	squad_tile.text = "%d players · OVR %s" % [d.get("squad_size", 0), str(d.get("avg_overall", "—"))]
	var pos = d.get("league_position")
	league_tile.text = "League: #%d" % pos if pos else "League: —"
	cash_tile.text = JsonFormat.value(d.get("cash", 0))
	var conf = d.get("board_label", "—")
	var conf_score = d.get("board_confidence", 50)
	confidence_tile.text = "%s (%d)" % [conf, conf_score]


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


func _refresh_international_fixtures() -> void:
	var response := IpcBridge.call_method("get_national_team")
	if response.has("error") or not response.get("result", {}).get("managing"):
		return
	var national_team: Dictionary = response["result"]
	var fixtures_response := IpcBridge.call_method("get_international_fixtures")
	if fixtures_response.has("error"):
		return
	var fixtures: Array = fixtures_response.get("result", [])
	if fixtures.is_empty():
		return
	# Show international fixtures card
	var card := get_node_or_null("Bottom/Right/InternationalCard")
	if not card:
		return
	card.visible = true
	var list: VBoxContainer = card.get_node_or_null("Box/List")
	if not list:
		return
	for child in list.get_children():
		child.queue_free()
	for fixture in fixtures.slice(0, 3):
		var line := HBoxContainer.new()
		line.add_theme_constant_override("separation", 8)
		var label := Label.new()
		var home_name: String = str(fixture.get("home_name", "?"))
		var away_name: String = str(fixture.get("away_name", "?"))
		var comp_name: String = str(fixture.get("competition_name", "?"))
		var match_date: String = str(fixture.get("date", "?"))
		var format: String = str(fixture.get("format", "?"))
		label.text = "%s vs %s — %s, %s" % [home_name, away_name, format, match_date]
		label.add_theme_font_size_override("font_size", 11)
		line.add_child(label)
		list.add_child(line)

