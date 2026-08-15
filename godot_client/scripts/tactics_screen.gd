extends Control
## Dedicated manager's Tactics Hub. It separates preparation from live-match
## controls: managers can define a clear identity, then make small situational
## changes on Match Day without hunting through a crowded screen.

var _active_tab := "MATCH PLAN"
var _tabs: Dictionary = {}
var _body: VBoxContainer
var _status: Label

const TAB_DATA := {
	"MATCH PLAN": ["Set the default game plan", "Choose a safe baseline for unfamiliar conditions. The live engine can override it when wickets, weather or required rate demand it."],
	"BATTING": ["Manage the innings", "Protect wickets early, rotate strike through the middle phase and reserve your best power for the final overs."],
	"BOWLING": ["Build pressure", "Use control and movement when the ball is new; change pace and attack the stumps when batters settle."],
	"FIELDING": ["Turn pressure into wickets", "Aggressive rings create chances. Defensive fields protect boundaries when the target is under control."],
	"OPPOSITION": ["Prepare for the opponent", "Review their strongest batters, preferred scoring zones and vulnerable match-ups before confirming the XI."]
}

func _ready() -> void:
	_build()

func _build() -> void:
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_bottom", 10)
	add_child(margin)
	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 12)
	margin.add_child(root)
	var heading := Label.new()
	heading.text = "TACTICS HUB"
	heading.add_theme_font_size_override("font_size", 26)
	heading.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	root.add_child(heading)
	var sub := Label.new()
	sub.text = "Define how your team wants to win. Match Day decisions remain yours."
	sub.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	root.add_child(sub)
	var tabs_scroll := ScrollContainer.new()
	tabs_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	tabs_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	tabs_scroll.custom_minimum_size.y = 44
	root.add_child(tabs_scroll)
	var tabs := HBoxContainer.new()
	tabs.add_theme_constant_override("separation", 8)
	tabs_scroll.add_child(tabs)
	for tab_name in TAB_DATA.keys():
		var tab := Button.new()
		tab.text = tab_name
		tab.custom_minimum_size = Vector2(130, 36)
		tab.pressed.connect(_select_tab.bind(tab_name))
		tabs.add_child(tab)
		_tabs[tab_name] = tab
	var columns := HBoxContainer.new()
	columns.size_flags_vertical = Control.SIZE_EXPAND_FILL
	columns.add_theme_constant_override("separation", 12)
	root.add_child(columns)
	var main_card := _card("")
	main_card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	columns.add_child(main_card)
	var main_box := VBoxContainer.new()
	main_box.add_theme_constant_override("separation", 8)
	main_card.add_child(_padded(main_box))
	var main_title := Label.new()
	main_title.text = "PLAN BUILDER"
	main_title.add_theme_font_size_override("font_size", 12)
	main_title.add_theme_color_override("font_color", AppTheme.ACCENT)
	main_box.add_child(main_title)
	_body = VBoxContainer.new()
	_body.add_theme_constant_override("separation", 10)
	main_box.add_child(_body)
	var insight := _card("MANAGER NOTES")
	insight.custom_minimum_size.x = 290
	columns.add_child(insight)
	var insight_box := VBoxContainer.new()
	insight_box.add_theme_constant_override("separation", 10)
	insight.add_child(_padded(insight_box))
	var insight_title := Label.new()
	insight_title.text = "MANAGER NOTES"
	insight_title.add_theme_font_size_override("font_size", 12)
	insight_title.add_theme_color_override("font_color", AppTheme.ACCENT)
	insight_box.add_child(insight_title)
	for item in ["Conditions first", "Protect the partnership", "Attack the weakest match-up", "Keep one review in reserve"]:
		var note := Label.new()
		note.text = "•  " + item
		note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		note.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
		insight_box.add_child(note)
	_status = Label.new()
	_status.text = "Ready to set your plan."
	_status.add_theme_color_override("font_color", AppTheme.HEADER_GREEN)
	insight_box.add_child(_spacer())
	insight_box.add_child(_status)
	_select_tab(_active_tab)

func _select_tab(tab_name: String) -> void:
	_active_tab = tab_name
	for key in _tabs:
		AppTheme.style_tab_button(_tabs[key], key == tab_name)
	if _body == null:
		return
	for child in _body.get_children():
		child.queue_free()
	var details: Array = TAB_DATA[tab_name]
	var title := Label.new()
	title.text = str(details[0])
	title.add_theme_font_size_override("font_size", 20)
	title.add_theme_color_override("font_color", AppTheme.GOLD)
	_body.add_child(title)
	var description := Label.new()
	description.text = str(details[1])
	description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	description.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	_body.add_child(description)
	for row in _controls_for(tab_name):
		var card := _option_card(str(row[0]), str(row[1]), str(row[2]))
		_body.add_child(card)
	var apply := Button.new()
	apply.text = "APPLY AS DEFAULT"
	apply.custom_minimum_size.y = 40
	apply.pressed.connect(func(): _status.text = "%s plan applied for the next selection." % tab_name)
	_body.add_child(apply)
	AppTheme.polish_controls(_body)

func _controls_for(tab_name: String) -> Array:
	match tab_name:
		"BATTING": return [["Opening approach", "Protect the top order in the first six overs", "Balanced"], ["Middle overs", "Rotate strike and target the weaker bowler", "Build"], ["Closing overs", "Release hitters when wickets are available", "Blitz"]]
		"BOWLING": return [["New ball", "Attack the edge with movement and a catching ring", "Aggressive"], ["Middle phase", "Choke singles and change pace", "Control"], ["Death overs", "Yorkers first; protect the straight boundary", "Defensive"]]
		"FIELDING": return [["Default ring", "Keep saving positions inside the circle", "Neutral"], ["Wicket mode", "Bring catchers around the bat", "Aggressive"], ["Defence mode", "Protect the boundary and force mistakes", "Defensive"]]
		"OPPOSITION": return [["Primary threat", "Use the opposition report to pick a match-up", "Review"], ["Fallback plan", "Keep a second bowler ready for a momentum shift", "Prepared"]]
		_: return [["Tempo", "Start with a balanced plan and read the first over", "Balanced"], ["Risk budget", "Spend aggression only when the situation supports it", "Measured"], ["Captain's trigger", "Change plan after two quiet overs or a wicket", "Reactive"]]

func _option_card(label_text: String, help_text: String, value_text: String) -> PanelContainer:
	var card := _card("")
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	card.add_child(_padded(row))
	var box := VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(box)
	var label := Label.new()
	label.text = label_text
	label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	box.add_child(label)
	var help := Label.new()
	help.text = help_text
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	help.add_theme_font_size_override("font_size", 12)
	help.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	box.add_child(help)
	var value := OptionButton.new()
	value.add_item(value_text)
	value.add_item("Alternative")
	value.custom_minimum_size = Vector2(120, 34)
	row.add_child(value)
	return card

func _card(title_text: String) -> PanelContainer:
	var card := PanelContainer.new()
	card.add_theme_stylebox_override("panel", AppTheme.make_card(false))
	return card

func _padded(node: Control) -> MarginContainer:
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 14)
	margin.add_theme_constant_override("margin_right", 14)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	margin.add_child(node)
	return margin

func _spacer() -> Control:
	var spacer := Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	return spacer
