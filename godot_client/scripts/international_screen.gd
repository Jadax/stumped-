extends Control
## New in v4.12.0 (Part 3 of the international tournament rebuild,
## v4.10.0-v4.12.0): shows whichever international competition thread is
## most recent — a bilateral tour's flat match list, an ICC tournament's
## live group-stage standings, or its knockout bracket — backed by
## database.py's get_current_international_competition. Before this,
## World Cup/Champions Trophy/tour progression was only ever visible via
## one-off inbox messages, with no way to see the table or bracket in-app.
## The knockout rendering shares BracketView.build() (bracket_view.gd) with
## tournament_bracket_screen.gd's Domestic Cup — see that script's header.
##
## v4.53.0 structural pass (reference: the World Cup group-stage
## screenshot): previously stacked every group vertically with no way to
## focus one, no flags, and no sub-navigation — none of which matched the
## reference's one-group-at-a-time view with a Fixtures/Groups/Final Stages
## tab bar along the bottom. Rebuilt around a persistent sub-nav bar that
## re-renders from the last fetched result rather than a hardcoded
## dispatch on the backend "kind" field, so a group-stage tournament can
## still show "Final Stages" (as "not decided yet") and vice versa.

@onready var title_label: Label = $Title
@onready var content: VBoxContainer = $Scroll/Content
@onready var scroll: ScrollContainer = $Scroll
@onready var sub_nav: HBoxContainer = $SubNav

var _last_result: Dictionary = {}
var _sub_tab: String = "groups"
var _group_index: int = 0
var _group_labels: Array = []


func _ready() -> void:
	for tab in sub_nav.get_children():
		if tab is Button:
			tab.pressed.connect(_on_sub_tab_pressed.bind(tab))
	refresh()


func _on_sub_tab_pressed(tab: Button) -> void:
	_sub_tab = str(tab.name).to_lower().replace("tab", "")
	for other in sub_nav.get_children():
		if other is Button:
			other.set_pressed_no_signal(other == tab)
	_render(_last_result)


func refresh() -> void:
	var response := IpcBridge.call_method("get_current_international_competition")
	if response.has("error"):
		title_label.text = "WORLD CUP — backend error: %s" % response["error"]
		push_error("InternationalScreen: %s" % response["error"])
		return
	_last_result = response.get("result", {})
	_group_index = 0
	_render(_last_result)


func _clear(container: Control) -> void:
	for child in container.get_children():
		container.remove_child(child)
		child.queue_free()


func _render(result: Dictionary) -> void:
	_clear(content)
	var kind: String = str(result.get("kind", "none"))
	if kind == "none":
		title_label.text = "WORLD CUP"
		var empty := Label.new()
		empty.text = "No international tour or tournament has started yet this season."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		content.add_child(empty)
		return
	title_label.text = "%s — %s" % [str(result.get("name", "?")), JsonFormat.value(result.get("season"))]
	match _sub_tab:
		"groups":
			_render_groups_tab(result, kind)
		"fixtures":
			_render_fixtures_tab(result, kind)
		"finalstages":
			_render_final_stages_tab(result, kind)


## v4.53.0: flattens whichever shape the backend sent (a bilateral tour's
## flat "matches", or every group's own "matches") into one list — the
## reference's Fixtures tab is format-agnostic, not group-stage-only.
func _render_fixtures_tab(result: Dictionary, kind: String) -> void:
	var matches: Array = []
	if kind == "tour":
		matches = result.get("matches", [])
	elif kind == "tournament_group":
		for group in result.get("groups", {}).values():
			matches.append_array(group.get("matches", []))
	if matches.is_empty():
		var empty := Label.new()
		empty.text = "No fixtures to show yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		content.add_child(empty)
		return
	for match in matches:
		content.add_child(_match_row(match))


func _render_groups_tab(result: Dictionary, kind: String) -> void:
	if kind != "tournament_group":
		var empty := Label.new()
		empty.text = "No group stage for this competition." if kind == "tour" else "The group stage is complete — see Final Stages."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		content.add_child(empty)
		return
	var groups: Dictionary = result.get("groups", {})
	_group_labels = groups.keys()
	if _group_labels.is_empty():
		return
	_group_index = clampi(_group_index, 0, _group_labels.size() - 1)
	var label: String = _group_labels[_group_index]
	var group: Dictionary = groups[label]
	# Reference: one group visible at a time behind a "◄ label ►" cycle
	# control, not every group stacked vertically.
	if _group_labels.size() > 1:
		content.add_child(_group_cycle_row(label))
	else:
		content.add_child(_group_heading(label))
	content.add_child(_standings_table(group.get("standings", [])))


func _group_cycle_row(label: String) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 16)
	var prev_button := Button.new()
	prev_button.text = "◄"
	prev_button.custom_minimum_size = Vector2(36, 0)
	prev_button.pressed.connect(_on_group_cycle.bind(-1))
	row.add_child(prev_button)
	row.add_child(_group_heading(label))
	var next_button := Button.new()
	next_button.text = "►"
	next_button.custom_minimum_size = Vector2(36, 0)
	next_button.pressed.connect(_on_group_cycle.bind(1))
	row.add_child(next_button)
	return row


func _group_heading(label: String) -> Label:
	var heading := Label.new()
	heading.text = "%s  •  GROUP STAGE" % str(label).to_upper()
	heading.add_theme_color_override("font_color", AppTheme.GOLD)
	heading.add_theme_font_size_override("font_size", 15)
	heading.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return heading


func _on_group_cycle(delta: int) -> void:
	if _group_labels.is_empty():
		return
	_group_index = wrapi(_group_index + delta, 0, _group_labels.size())
	_render(_last_result)


func _render_final_stages_tab(result: Dictionary, kind: String) -> void:
	if kind != "tournament_knockout":
		var empty := Label.new()
		empty.text = "The knockout stage hasn't been decided yet — check back once the group stage finishes."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		content.add_child(empty)
		return
	_render_bracket(result.get("bracket", {}), result.get("rounds", []))


func _match_row(match: Dictionary) -> PanelContainer:
	var card := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.CARD
	box.set_corner_radius_all(8)
	box.content_margin_left = 12
	box.content_margin_right = 12
	box.content_margin_top = 8
	box.content_margin_bottom = 8
	card.add_theme_stylebox_override("panel", box)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	var round_label := Label.new()
	round_label.text = str(match.get("round_name", "?"))
	round_label.custom_minimum_size = Vector2(110, 0)
	round_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	row.add_child(round_label)
	var winner: Variant = match.get("winner")
	var summary := Label.new()
	summary.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	if bool(match.get("completed", false)):
		var home_win: bool = winner != null and str(winner) == str(match.get("home", "?"))
		var away_win: bool = winner != null and str(winner) == str(match.get("away", "?"))
		summary.text = "%s %s  vs  %s %s" % [str(match.get("home", "?")), JsonFormat.value(match.get("home_runs")),
			str(match.get("away", "?")), JsonFormat.value(match.get("away_runs"))]
		summary.add_theme_color_override("font_color", AppTheme.GOLD if (home_win or away_win) else AppTheme.TEXT_PRIMARY)
	else:
		summary.text = "%s vs %s" % [str(match.get("home", "?")), str(match.get("away", "?"))]
		summary.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	row.add_child(summary)
	card.add_child(row)
	return card


## Reference (World Cup group screenshot): a single gold qualification-line
## row after the last automatically-advancing team, not a per-row border —
## QUALIFY_COUNT mirrors CompetitionEngine._start_icc_tournament's default
## advance_per_group (2); the group response has no explicit count to read
## (see get_current_international_competition), so this is the same top-2
## assumption the previous top/bottom-border version made, just rendered
## as a real divider line matching the reference instead of row borders.
const QUALIFY_COUNT := 2


func _standings_table(standings: Array) -> VBoxContainer:
	var table := VBoxContainer.new()
	table.add_theme_constant_override("separation", 2)
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 12)
	for text in ["#", "", "TEAM", "P", "W", "L", "T", "NR", "PTS", "NETRR"]:
		var h := Label.new()
		h.text = text
		h.custom_minimum_size = Vector2(28, 0) if text == "#" else (Vector2(24, 0) if text == "" else (Vector2(150, 0) if text == "TEAM" else Vector2(48, 0)))
		h.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT if text not in ["#", "", "TEAM"] else HORIZONTAL_ALIGNMENT_LEFT
		h.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		h.add_theme_font_size_override("font_size", 11)
		header.add_child(h)
	table.add_child(header)
	for index in range(standings.size()):
		var row_data: Dictionary = standings[index]
		var panel := PanelContainer.new()
		var style := StyleBoxFlat.new()
		style.bg_color = AppTheme.ROW_ALT if index % 2 else AppTheme.CARD
		style.set_corner_radius_all(4)
		style.content_margin_left = 6
		style.content_margin_right = 6
		style.content_margin_top = 5
		style.content_margin_bottom = 5
		panel.add_theme_stylebox_override("panel", style)
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 10)
		row.add_child(_group_cell(str(index + 1), 28, AppTheme.TEXT_MUTED, HORIZONTAL_ALIGNMENT_LEFT))
		row.add_child(_flag_cell(str(row_data.get("team", "?"))))
		row.add_child(_group_cell(str(row_data.get("team", "?")), 150, AppTheme.TEXT_PRIMARY, HORIZONTAL_ALIGNMENT_LEFT, true))
		for key in ["played", "won", "lost", "tied"]:
			row.add_child(_group_cell(str(row_data.get(key, 0)), 48, AppTheme.TEXT_SECONDARY, HORIZONTAL_ALIGNMENT_RIGHT))
		# "NR" (no result — an abandoned match with no winner or tie) is
		# always 0: the match engine has no abandoned/rain-off concept, so
		# every completed international always produces a winner or a tie.
		# Shown anyway (reference has the column) rather than omitted, so
		# the table's real column count matches the reference exactly.
		row.add_child(_group_cell("0", 40, AppTheme.TEXT_MUTED, HORIZONTAL_ALIGNMENT_RIGHT))
		row.add_child(_group_cell(str(row_data.get("points", 0)), 48, AppTheme.GOLD, HORIZONTAL_ALIGNMENT_RIGHT))
		row.add_child(_group_cell(str(row_data.get("net_run_rate", 0.0)), 56, AppTheme.TEXT_SECONDARY, HORIZONTAL_ALIGNMENT_RIGHT))
		panel.add_child(row)
		table.add_child(panel)
		if index == QUALIFY_COUNT - 1 and index < standings.size() - 1:
			var divider := ColorRect.new()
			divider.color = AppTheme.GOLD
			divider.custom_minimum_size = Vector2(0, 2)
			table.add_child(divider)
	return table


## Reference: a small national flag per row, matching the same
## AppTheme.flag_texture() lookup used everywhere else a nationality/team
## needs one (e.g. table_screen.gd's flag column).
func _flag_cell(team_name: String) -> Control:
	var cell := Control.new()
	cell.custom_minimum_size = Vector2(24, 0)
	var texture := AppTheme.flag_texture(team_name)
	if texture:
		var rect := TextureRect.new()
		rect.texture = texture
		rect.custom_minimum_size = Vector2(20, 14)
		rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		rect.stretch_mode = TextureRect.STRETCH_SCALE
		cell.add_child(rect)
	return cell


func _group_cell(text: String, width: int, colour: Color, alignment: HorizontalAlignment, expand: bool = false) -> Label:
	var label := Label.new()
	label.text = text
	label.custom_minimum_size = Vector2(width, 0)
	label.horizontal_alignment = alignment
	label.add_theme_color_override("font_color", colour)
	label.add_theme_font_size_override("font_size", 12 if expand else 11)
	if expand:
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		label.clip_text = true
	return label


## v4.52.0: goes through the shared BracketView.build() (bracket_view.gd) —
## this screen's knockout view was previously an independent copy of
## tournament_bracket_screen.gd's match-card/team-row drawing code; now both
## screens (Domestic Cup, World Cup knockout) share one implementation and
## both get the gold "CHAMPIONS" banner for free once the Final is decided.
func _render_bracket(bracket: Dictionary, rounds: Array) -> void:
	if rounds.is_empty():
		var empty := Label.new()
		empty.text = "The knockout draw hasn't been made yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		content.add_child(empty)
		return
	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 20)
	content.add_child(columns)
	BracketView.build(columns, bracket, rounds)
