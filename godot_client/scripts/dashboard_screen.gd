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


var _storylines_list: VBoxContainer


func _ready() -> void:
	_style_crest(home_crest, home_crest_label)
	_style_crest(away_crest, away_crest_label)
	away_name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	home_name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	$Bottom/Left/FixtureCard/Box/TeamsRow/Vs.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	for button in team_talk_tones.get_children():
		(button as Button).pressed.connect(_on_team_talk_pressed.bind(button.name))
	_style_cards()
	_build_storylines_card()
	refresh()


## v4.59.0: a "STORYLINES" card — the narrative layer's feed (rivalry
## results, player milestones; see src/database.py's narrative_events
## table) surfaced somewhere a manager already looks every session, rather
## than a whole new nav item. Built at runtime alongside the existing
## Standings/Messages cards in Bottom/Right, same pattern
## `_refresh_international_fixtures()` already uses for a conditional card.
func _build_storylines_card() -> void:
	var right: VBoxContainer = $Bottom/Right
	var card := PanelContainer.new()
	card.size_flags_vertical = SIZE_FILL
	card.add_theme_stylebox_override("panel", AppTheme.make_card(false))
	right.add_child(card)
	var box := VBoxContainer.new()
	card.add_child(box)
	var header := Label.new()
	header.text = "STORYLINES"
	header.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	header.add_theme_font_size_override("font_size", 10)
	box.add_child(header)
	_storylines_list = VBoxContainer.new()
	_storylines_list.add_theme_constant_override("separation", 6)
	box.add_child(_storylines_list)


func _refresh_storylines() -> void:
	var response := IpcBridge.call_method("get_narrative_events", {"scope": "team", "limit": 5})
	for child in _storylines_list.get_children():
		child.queue_free()
	if response.has("error"):
		return
	var events: Array = response["result"].get("events", [])
	if events.is_empty():
		var empty := Label.new()
		empty.text = "No storylines yet this season."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		empty.add_theme_font_size_override("font_size", 11)
		_storylines_list.add_child(empty)
		return
	for event in events:
		var line := VBoxContainer.new()
		var title := Label.new()
		title.text = str(event.get("title", "?"))
		title.add_theme_font_size_override("font_size", 12)
		title.add_theme_color_override("font_color", AppTheme.GOLD if event.get("category") == "RIVALRY" else AppTheme.TEXT_PRIMARY)
		line.add_child(title)
		var body := Label.new()
		body.text = str(event.get("body", ""))
		body.autowrap_mode = TextServer.AUTOWRAP_WORD
		body.add_theme_font_size_override("font_size", 10)
		body.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		line.add_child(body)
		_storylines_list.add_child(line)


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
	var season_label := "Season %s" % date_str.substr(0, 4) if date_str.length() >= 4 else "Season 1"
	title_label.text = "PORTAL — %s  •  %s  •  %s" % [team.get("name", "?"), season_label, date_str]

	var fixture = result.get("fixture")
	teams_row.visible = fixture != null
	if fixture:
		var home_name: String = fixture.get("home_name", "?")
		var away_name: String = fixture.get("away_name", "?")
		home_name_label.text = home_name
		away_name_label.text = away_name
		home_crest_label.text = _initials(home_name)
		away_crest_label.text = _initials(away_name)
		fixture_label.text = "%s  •  %s\n%s" % [fixture.get("format", "?"), fixture.get("date", "?"), fixture.get("venue", "Home venue")]
		fixture_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	else:
		fixture_label.text = "No fixture scheduled"
		fixture_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT

	_refresh_international_fixtures()
	_refresh_storylines()

	_render_standings(standings_list, result.get("standings", []), team)

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


## v4.28.0: was name + points only ("Auckland Aces — 0 pts") — the user
## compared it unfavourably to Football Manager's real table. Now a real
## P/W/L/PTS table, same data get_dashboard already returned
## (fetch_league_standings has played/won/lost/points/net_run_rate; only
## the rendering was flat).
func _render_standings(list: VBoxContainer, standings: Array, team: Dictionary) -> void:
	for child in list.get_children():
		list.remove_child(child)
		child.queue_free()
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 6)
	header.add_child(_standings_cell("#", 22, AppTheme.TEXT_MUTED, HORIZONTAL_ALIGNMENT_CENTER, 10))
	header.add_child(_standings_cell("TEAM", 0, AppTheme.TEXT_MUTED, HORIZONTAL_ALIGNMENT_LEFT, 10, true))
	for text in ["P", "W", "L", "PTS", "NRR"]:
		header.add_child(_standings_cell(text, 26, AppTheme.TEXT_MUTED, HORIZONTAL_ALIGNMENT_RIGHT, 10))
	list.add_child(header)
	list.add_child(HSeparator.new())
	for row in standings.slice(0, 6):
		var mine: bool = row.get("team_id") == team.get("id")
		var line := HBoxContainer.new()
		line.add_theme_constant_override("separation", 6)
		if mine:
			var highlight := StyleBoxFlat.new()
			highlight.bg_color = AppTheme.ACTIVE
			highlight.set_corner_radius_all(4)
			highlight.content_margin_left = 4
			highlight.content_margin_right = 4
			highlight.content_margin_top = 2
			highlight.content_margin_bottom = 2
			line.add_theme_stylebox_override("panel", highlight)
		var colour := AppTheme.GOLD if mine else AppTheme.TEXT_PRIMARY
		var position: int = int(row.get("position", 0))
		var zone_colour := AppTheme.HEADER_GREEN if position <= 2 else (AppTheme.DANGER if position >= standings.size() - 1 else colour)
		var font_size := 13 if mine else 12
		line.add_child(_standings_cell(JsonFormat.value(row.get("position", 0)), 22, colour, HORIZONTAL_ALIGNMENT_CENTER, font_size))
		line.add_child(_standings_cell(str(row.get("name", "?")), 0, colour, HORIZONTAL_ALIGNMENT_LEFT, font_size, true))
		line.add_child(_standings_cell(JsonFormat.value(row.get("played", 0)), 26, AppTheme.TEXT_SECONDARY, HORIZONTAL_ALIGNMENT_RIGHT, font_size))
		line.add_child(_standings_cell(JsonFormat.value(row.get("won", 0)), 26, AppTheme.TEXT_SECONDARY, HORIZONTAL_ALIGNMENT_RIGHT, font_size))
		line.add_child(_standings_cell(JsonFormat.value(row.get("lost", 0)), 26, AppTheme.TEXT_SECONDARY, HORIZONTAL_ALIGNMENT_RIGHT, font_size))
		line.add_child(_standings_cell(JsonFormat.value(row.get("points", 0)), 26, colour, HORIZONTAL_ALIGNMENT_RIGHT, font_size))
		line.add_child(_standings_cell(str(row.get("net_run_rate", 0.0)), 42, zone_colour if not mine else colour, HORIZONTAL_ALIGNMENT_RIGHT, font_size))
		list.add_child(line)


func _standings_cell(text: String, width: int, colour: Color, align: HorizontalAlignment, font_size: int, expand: bool = false) -> Label:
	var label := Label.new()
	label.text = text
	if width > 0:
		label.custom_minimum_size = Vector2(width, 0)
	if expand:
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		label.clip_text = true
	label.horizontal_alignment = align
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", colour)
	return label


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
