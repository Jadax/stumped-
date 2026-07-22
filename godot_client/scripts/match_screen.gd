extends Control
## Match Day — pre-match hub (fixture, XI, ground) plus, once started, the
## real live ball-by-ball feed: match_engine.Match run through ipc_server.py's
## start_match/simulate_balls/get_match_state, one real delivery at a time
## (not a bulk-simulate-then-replay), mirroring ui/match_view.py's
## simulate_ball() loop. Deliberately scoped down from pygame's full Stats
## Hub (wagon wheel, pitch map, worm/momentum/manhattan graphs, tactics,
## DRS, field presets) to what a live match genuinely needs to be playable:
## score bug, batting/bowling scorecards, commentary feed, and
## next-ball/over/auto/skip controls. The rest can follow later.

const SPEEDS := {"Normal": 0.9, "Fast": 0.22, "Instant": 0.03}
const SPEED_ORDER := ["Normal", "Fast", "Instant"]

@onready var title_label: Label = $Title
@onready var pre_match_box: Control = $PreMatchBox
@onready var fixture_label: Label = $PreMatchBox/FixtureBar/FixtureLabel
@onready var start_button: Button = $PreMatchBox/StartButton
@onready var xi_list: VBoxContainer = $PreMatchBox/Row/LineupCard/Box/List
@onready var xi_header: Label = $PreMatchBox/Row/LineupCard/Box/Header

@onready var live_match_box: Control = $LiveMatchBox
@onready var score_label: Label = $LiveMatchBox/ScoreBar/ScoreBox/ScoreLabel
@onready var status_label: Label = $LiveMatchBox/ScoreBar/ScoreBox/StatusLabel
@onready var batting_list: VBoxContainer = $LiveMatchBox/Row/BattingCard/Box/Scroll/RowList
@onready var bowling_list: VBoxContainer = $LiveMatchBox/Row/BowlingCard/Box/Scroll/RowList
@onready var commentary_list: VBoxContainer = $LiveMatchBox/CommentaryCard/Box/Scroll/RowList
@onready var commentary_scroll: ScrollContainer = $LiveMatchBox/CommentaryCard/Box/Scroll
@onready var next_ball_button: Button = $LiveMatchBox/Controls/NextBallButton
@onready var over_button: Button = $LiveMatchBox/Controls/OverButton
@onready var auto_button: Button = $LiveMatchBox/Controls/AutoButton
@onready var speed_button: Button = $LiveMatchBox/Controls/SpeedButton
@onready var skip_button: Button = $LiveMatchBox/Controls/SkipButton
@onready var exit_button: Button = $LiveMatchBox/Controls/ExitButton
@onready var auto_timer: Timer = $LiveMatchBox/AutoTimer

var speed_index: int = 0
var auto_play: bool = false
var match_completed: bool = false


func _ready() -> void:
	start_button.pressed.connect(_on_start_pressed)
	next_ball_button.pressed.connect(func(): _simulate(1))
	over_button.pressed.connect(func(): _simulate(6))
	skip_button.pressed.connect(func(): _simulate(_skip_count()))
	auto_button.pressed.connect(_on_auto_pressed)
	speed_button.pressed.connect(_on_speed_pressed)
	exit_button.pressed.connect(_on_exit_pressed)
	auto_timer.timeout.connect(_on_auto_timeout)
	refresh()


func refresh() -> void:
	title_label.text = "MATCH DAY"
	var state_response := IpcBridge.call_method("get_match_state")
	if not state_response.has("error"):
		_show_live(state_response["result"])
		return
	_show_pre_match()


func _show_pre_match() -> void:
	pre_match_box.visible = true
	live_match_box.visible = false
	auto_timer.stop()
	auto_play = false
	var response := IpcBridge.call_method("get_match_preview")
	if response.has("error"):
		title_label.text = "MATCH — backend error: %s" % response["error"]
		push_error("MatchScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	var fixture = result.get("fixture")
	if fixture:
		fixture_label.text = "%s vs %s — %s, %s" % [fixture.get("home_name", "?"), fixture.get("away_name", "?"),
			fixture.get("format", "?"), fixture.get("date", "?")]
		start_button.disabled = false
	else:
		fixture_label.text = "No fixture scheduled"
		start_button.disabled = true

	var xi: Array = result.get("xi", [])
	xi_header.text = "PLAYING XI — %d/11" % xi.size()
	for child in xi_list.get_children():
		child.queue_free()
	if xi.is_empty():
		var empty := Label.new()
		empty.text = "No XI selected yet — pick one on the Selection screen (or the best-XI fallback will be used)."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		xi_list.add_child(empty)
		return
	for i in range(xi.size()):
		var player: Dictionary = xi[i]
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		var order_label := Label.new()
		order_label.text = "%d." % (i + 1)
		order_label.custom_minimum_size = Vector2(24, 0)
		order_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		row.add_child(order_label)
		var tags := []
		if player.get("id") == result.get("captain_id"): tags.append("C")
		if player.get("id") == result.get("keeper_id"): tags.append("WK")
		var suffix := " (%s)" % "/".join(tags) if not tags.is_empty() else ""
		var name_label := Label.new()
		name_label.text = "%s%s" % [player.get("name", "?"), suffix]
		name_label.custom_minimum_size = Vector2(180, 0)
		if not tags.is_empty():
			name_label.add_theme_color_override("font_color", AppTheme.GOLD)
		row.add_child(name_label)
		var role_label := Label.new()
		role_label.text = player.get("role", "?")
		role_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
		row.add_child(role_label)
		xi_list.add_child(row)


func _on_start_pressed() -> void:
	start_button.disabled = true
	var response := IpcBridge.call_method("start_match")
	if response.has("error"):
		title_label.text = "MATCH — could not start: %s" % response["error"]
		push_error("MatchScreen start_match failed: %s" % response["error"])
		start_button.disabled = false
		return
	_show_live(response["result"])


func _show_live(state: Dictionary) -> void:
	pre_match_box.visible = false
	live_match_box.visible = true
	_render_state(state)


func _simulate(count: int) -> void:
	var response := IpcBridge.call_method("simulate_balls", {"count": count})
	if response.has("error"):
		status_label.text = "Action failed: %s" % response["error"]
		push_error("MatchScreen simulate_balls failed: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	for event in result.get("events", []):
		_append_commentary(event)
	_render_state(result["state"])


func _skip_count() -> int:
	# Mirrors ui/match_view.py's SKIP: fast-forward roughly 15 overs' worth
	# of legal deliveries in one call (capped server-side either way).
	return 90


func _on_auto_pressed() -> void:
	auto_play = not auto_play
	auto_button.text = "AUTO: %s" % ("ON" if auto_play else "OFF")
	if auto_play and not match_completed:
		auto_timer.wait_time = SPEEDS[SPEED_ORDER[speed_index]]
		auto_timer.start()
	else:
		auto_timer.stop()


func _on_speed_pressed() -> void:
	speed_index = (speed_index + 1) % SPEED_ORDER.size()
	speed_button.text = "SPEED: %s" % SPEED_ORDER[speed_index].to_upper()
	if auto_play:
		auto_timer.wait_time = SPEEDS[SPEED_ORDER[speed_index]]


func _on_auto_timeout() -> void:
	if match_completed:
		auto_timer.stop()
		return
	_simulate(1)


func _on_exit_pressed() -> void:
	var shell := get_tree().get_first_node_in_group("shell")
	if shell:
		shell.show_screen("Dashboard")


func _render_state(state: Dictionary) -> void:
	match_completed = bool(state.get("completed", false))
	var innings_list: Array = state.get("innings", [])
	if innings_list.is_empty():
		return
	var current_index: int = int(state.get("current_innings_index", innings_list.size() - 1))
	var live: Dictionary = innings_list[min(current_index, innings_list.size() - 1)]
	score_label.text = "%s %s/%s (%s ov)" % [live.get("team", "?"), JsonFormat.value(live.get("runs", 0)),
		JsonFormat.value(live.get("wickets", 0)), live.get("overs", "0.0")]
	status_label.text = str(state.get("status", "—"))
	_render_scorecard(batting_list, live.get("batting", []), true, state)
	_render_scorecard(bowling_list, live.get("bowling", []), false, state)

	if match_completed:
		auto_play = false
		auto_timer.stop()
		auto_button.text = "AUTO: OFF"
		title_label.text = "MATCH DAY — %s" % state.get("result", "Match complete")
		next_ball_button.disabled = true
		over_button.disabled = true
		skip_button.disabled = true
		auto_button.disabled = true
	else:
		title_label.text = "MATCH DAY — live"


func _render_scorecard(list: VBoxContainer, rows: Array, is_batting: bool, state: Dictionary) -> void:
	for child in list.get_children():
		list.remove_child(child)
		child.queue_free()
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 10)
	var headers: Array = ["NAME", "R", "B", "4s", "6s", "SR"] if is_batting else ["NAME", "O", "R", "W", "ECON"]
	var widths: Array = [140, 40, 40, 36, 36, 50] if is_batting else [140, 50, 50, 40, 50]
	for i in range(headers.size()):
		var label := Label.new()
		label.text = headers[i]
		label.custom_minimum_size = Vector2(widths[i], 0)
		label.add_theme_color_override("font_color", AppTheme.GOLD)
		label.add_theme_font_size_override("font_size", 11)
		header.add_child(label)
	list.add_child(header)

	var striker_id: int = int(state.get("striker", {}).get("id", -1)) if state.get("striker") else -1
	var non_striker_id: int = int(state.get("non_striker", {}).get("id", -1)) if state.get("non_striker") else -1
	var bowler_id: int = int(state.get("bowler", {}).get("id", -1)) if state.get("bowler") else -1
	for row_data in rows:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 10)
		var values: Array
		var highlight := false
		if is_batting:
			var runs := int(row_data.get("runs", 0))
			var balls := int(row_data.get("balls", 0))
			var sr: float = row_data.get("strike_rate", 0.0)
			values = [str(row_data.get("name", "?")) + _dismissal_suffix(row_data), runs, balls,
				int(row_data.get("fours", 0)), int(row_data.get("sixes", 0)), "%.1f" % float(sr)]
			highlight = int(row_data.get("player_id", -1)) in [striker_id, non_striker_id]
		else:
			values = [row_data.get("name", "?"), JsonFormat.value(row_data.get("overs", "0.0")),
				int(row_data.get("runs", 0)), int(row_data.get("wickets", 0)), "%.2f" % float(row_data.get("economy", 0.0))]
			highlight = int(row_data.get("player_id", -1)) == bowler_id
		for i in range(values.size()):
			var label := Label.new()
			label.text = str(values[i])
			label.custom_minimum_size = Vector2(widths[i] if i < widths.size() else 60, 0)
			label.add_theme_font_size_override("font_size", 12)
			label.add_theme_color_override("font_color", AppTheme.GOLD if highlight else AppTheme.TEXT_PRIMARY)
			row.add_child(label)
		list.add_child(row)


func _dismissal_suffix(row_data: Dictionary) -> String:
	var dismissal: String = str(row_data.get("dismissal", ""))
	if dismissal == "" or dismissal == "not out" or dismissal == "did not bat":
		return ""
	return " (%s)" % dismissal


## Mirrors ui/match_view.py's colour-coded commentary log: wickets in red,
## boundaries in gold, everything else muted, most recent entry at the
## bottom with the view auto-scrolled to follow it.
func _append_commentary(event: Dictionary) -> void:
	var label := Label.new()
	var over_text: String = str(event.get("over", "?"))
	var batter: String = str(event.get("batter", {}).get("name", "?")) if event.get("batter") else "?"
	var bowler: String = str(event.get("bowler", {}).get("name", "?")) if event.get("bowler") else "?"
	label.text = "Ov %s — %s to %s: %s" % [over_text, bowler, batter, event.get("commentary", "")]
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	var kind: String = str(event.get("kind", "normal"))
	if kind == "wicket":
		label.add_theme_color_override("font_color", AppTheme.DANGER)
	elif event.get("result", "") in ["4", "6"]:
		label.add_theme_color_override("font_color", AppTheme.GOLD)
	elif kind == "milestone":
		label.add_theme_color_override("font_color", AppTheme.ACCENT)
	else:
		label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	label.add_theme_font_size_override("font_size", 12)
	commentary_list.add_child(label)
	var children := commentary_list.get_children()
	if children.size() > 150:
		commentary_list.remove_child(children[0])
		children[0].queue_free()
	await get_tree().process_frame
	commentary_scroll.scroll_vertical = int(commentary_scroll.get_v_scroll_bar().max_value)
