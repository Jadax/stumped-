extends Control
## v5.2.0: the Club hub — the landing screen after choosing a team (user
## feedback: the old Portal landing buried club life under global stuff;
## "it should be club page from where I can click on other tabs"). Presents
## the club's identity and a card grid into every club-management screen.

const QUICK_LINKS := [
	["PLAYERS", "Full squad list, form and attributes", "Squad"],
	["SELECTION", "Pick the XI, captain and keeper", "Selection"],
	["TRAINING", "Assign weekly training focus", "Training"],
	["YOUTH ACADEMY", "The next generation coming through", "Youth Academy"],
	["TACTICS", "Batting intent and bowling plans", "Tactics"],
	["GROUND & FACILITIES", "Pitch, capacity and upgrades", "Facilities"],
	["FINANCES", "Cash, wages and forecast", "Finances"],
	["STAFF", "Coaches, scouts and medical team", "Staff"],
	["KIT EDITOR", "Playing colours and design", "Kit Editor"],
	["EMBLEM EDITOR", "Club crest identity", "Emblem Editor"],
]

@onready var title_label: Label = $Title
@onready var crest: PanelContainer = $MainCol/HeroCard/Box/HeroRow/Crest
@onready var crest_label: Label = $MainCol/HeroCard/Box/HeroRow/Crest/CrestLabel
@onready var club_name_label: Label = $MainCol/HeroCard/Box/HeroRow/ClubBox/ClubName
@onready var club_meta_label: Label = $MainCol/HeroCard/Box/HeroRow/ClubBox/ClubMeta
@onready var stat_chips: HBoxContainer = $MainCol/HeroCard/Box/StatChips
@onready var quick_grid: GridContainer = $MainCol/Scroll/QuickGrid


func _shell() -> Node:
	return get_tree().get_first_node_in_group("shell")


func _ready() -> void:
	_style_cards()
	_build_quick_links()
	refresh()


func _style_cards() -> void:
	$MainCol/HeroCard.add_theme_stylebox_override("panel", AppTheme.make_card(true))
	var crest_box := StyleBoxFlat.new()
	crest_box.bg_color = AppTheme.GOLD
	crest_box.set_corner_radius_all(12)
	crest.add_theme_stylebox_override("panel", crest_box)
	crest_label.add_theme_color_override("font_color", AppTheme.BACKGROUND)
	crest_label.add_theme_font_size_override("font_size", 22)
	club_name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	club_meta_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)


func _build_quick_links() -> void:
	for entry in QUICK_LINKS:
		var card := Button.new()
		card.custom_minimum_size = Vector2(292, 84)
		card.clip_text = false
		var box := VBoxContainer.new()
		box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		box.offset_left = 14
		box.offset_right = -14
		box.offset_top = 10
		box.offset_bottom = -10
		box.alignment = BoxContainer.ALIGNMENT_CENTER
		box.add_theme_constant_override("separation", 4)
		box.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var head := Label.new()
		head.text = entry[0]
		head.add_theme_font_size_override("font_size", 15)
		head.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
		head.mouse_filter = Control.MOUSE_FILTER_IGNORE
		box.add_child(head)
		var blurb := Label.new()
		blurb.text = entry[1]
		blurb.add_theme_font_size_override("font_size", 11)
		blurb.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		blurb.mouse_filter = Control.MOUSE_FILTER_IGNORE
		box.add_child(blurb)
		card.add_child(box)
		card.pressed.connect(_open.bind(entry[2]))
		quick_grid.add_child(card)


func _open(screen_name: String) -> void:
	var shell := _shell()
	if shell:
		shell.show_screen(screen_name)


func refresh() -> void:
	var response := IpcBridge.call_method("get_dashboard")
	if response.has("error"):
		title_label.text = "CLUB — backend error: %s" % response["error"]
		push_error("ClubScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	var team: Dictionary = result.get("team", {})
	var name_text := str(team.get("name", "?"))
	club_name_label.text = name_text
	crest_label.text = _initials(name_text)
	club_meta_label.text = "Managed by %s" % result.get("manager_name", "—")
	title_label.text = "CLUB"

	for child in stat_chips.get_children():
		child.queue_free()
	_add_chip("CASH", JsonFormat.value(team.get("cash", 0)), AppTheme.TEXT_PRIMARY)
	var hub_response := IpcBridge.call_method("get_data_hub")
	if not hub_response.has("error"):
		var d: Dictionary = hub_response["result"]
		var pos = d.get("league_position")
		_add_chip("LEAGUE", "#%d" % pos if pos else "—", AppTheme.TEXT_PRIMARY)
		_add_chip("BOARD", "%s (%d)" % [d.get("board_label", "Stable"), d.get("board_confidence", 50)],
			AppTheme.attribute_colour(float(d.get("board_confidence", 50))))
		_add_chip("TROPHIES", str(int(d.get("trophy_count", 0))), AppTheme.TEXT_PRIMARY)
	var fans_response := IpcBridge.call_method("get_fan_sentiment")
	if not fans_response.has("error"):
		var fans: Dictionary = fans_response["result"]
		_add_chip("FANS", "%d %s" % [int(fans.get("morale", fans.get("sentiment", 0))),
			str(fans.get("label", ""))], AppTheme.attribute_colour(float(fans.get("morale", fans.get("sentiment", 0)))))
	var cohesion_response := IpcBridge.call_method("get_squad_cohesion")
	if not cohesion_response.has("error"):
		var cohesion: Dictionary = cohesion_response["result"]
		_add_chip("COHESION", "%d %s" % [int(cohesion.get("cohesion", 0)),
			str(cohesion.get("label", ""))], AppTheme.attribute_colour(float(cohesion.get("cohesion", 0))))


func _add_chip(caption: String, value: String, colour: Color) -> void:
	var chip := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.ROW_ALT
	box.set_corner_radius_all(8)
	box.set_border_width_all(1)
	box.border_color = AppTheme.BORDER
	box.content_margin_left = 12
	box.content_margin_right = 12
	box.content_margin_top = 5
	box.content_margin_bottom = 5
	chip.add_theme_stylebox_override("panel", box)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	var caption_label := Label.new()
	caption_label.text = caption
	caption_label.add_theme_font_size_override("font_size", 10)
	caption_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	row.add_child(caption_label)
	var value_label := Label.new()
	value_label.text = value
	value_label.add_theme_font_size_override("font_size", 13)
	value_label.add_theme_color_override("font_color", colour)
	row.add_child(value_label)
	chip.add_child(row)
	stat_chips.add_child(chip)


static func _initials(name: String) -> String:
	var initials := ""
	for word in name.split(" ", false):
		if not word.is_empty():
			initials += word[0]
	return initials.substr(0, 2).to_upper()
