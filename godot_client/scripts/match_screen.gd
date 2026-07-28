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

const OPPOSITION_REPORT_MODAL_SCENE := preload("res://scenes/opposition_report_modal.tscn")
const PITCH_TYPES := ["Green", "Dry", "Dusty", "Flat", "Worn"]

@onready var title_label: Label = $Title
@onready var pre_match_box: Control = $PreMatchBox
@onready var fixture_label: Label = $PreMatchBox/FixtureBar/FixtureLabel
@onready var start_button: Button = $PreMatchBox/StartButton
@onready var pitch_button: Button = $PreMatchBox/ControlsRow/PitchButton
@onready var opposition_button: Button = $PreMatchBox/ControlsRow/OppositionButton
@onready var xi_list: VBoxContainer = $PreMatchBox/Row/LineupCard/Box/List
@onready var xi_header: Label = $PreMatchBox/Row/LineupCard/Box/Header

var _opposition_report_modal: OppositionReportModal = null
var _is_home_fixture: bool = false
var _pitch: String = "Green"

@onready var live_match_box: Control = $LiveMatchBox
@onready var score_label: Label = $LiveMatchBox/ScoreBar/ScoreBox/ScoreLabel
@onready var status_label: Label = $LiveMatchBox/ScoreBar/ScoreBox/StatusLabel
@onready var prediction_label: Label = $LiveMatchBox/ScoreBar/ScoreBox/PredictionLabel
@onready var batting_card: PanelContainer = $LiveMatchBox/Row/BattingCard
@onready var bowling_card: PanelContainer = $LiveMatchBox/Row/BowlingCard
@onready var batting_list: VBoxContainer = $LiveMatchBox/Row/BattingCard/Box/Scroll/RowList
@onready var bowling_list: VBoxContainer = $LiveMatchBox/Row/BowlingCard/Box/Scroll/RowList
@onready var stamina_label: Label = $LiveMatchBox/Row/BowlingCard/Box/StaminaRow/StaminaLabel
@onready var stamina_bar: Control = $LiveMatchBox/Row/BowlingCard/Box/StaminaRow/StaminaBar
@onready var summary_card: PanelContainer = $LiveMatchBox/SummaryCard
@onready var summary_list: VBoxContainer = $LiveMatchBox/SummaryCard/Box/Scroll/RowList
@onready var commentary_list: VBoxContainer = $LiveMatchBox/CommentaryCard/Box/Scroll/RowList
@onready var commentary_scroll: ScrollContainer = $LiveMatchBox/CommentaryCard/Box/Scroll
@onready var predict_button: Button = $LiveMatchBox/TacticsRow/PredictButton
@onready var field_button: Button = $LiveMatchBox/TacticsRow/FieldButton
@onready var batting_aggro_button: Button = $LiveMatchBox/TacticsRow/BattingAggroButton
@onready var bowling_aggro_button: Button = $LiveMatchBox/TacticsRow/BowlingAggroButton
@onready var change_bowler_button: Button = $LiveMatchBox/TacticsRow/ChangeBowlerButton
@onready var drs_button: Button = $LiveMatchBox/TacticsRow/DrsButton
@onready var stats_tab_bar: HBoxContainer = $LiveMatchBox/StatsTabBar
@onready var scorecard_row: HBoxContainer = $LiveMatchBox/Row
@onready var stats_card: PanelContainer = $LiveMatchBox/StatsCard
@onready var stats_canvas: MatchStatsCanvas = $LiveMatchBox/StatsCard/StatsCanvas
@onready var partnerships_card: PanelContainer = $LiveMatchBox/PartnershipsCard
@onready var partnerships_list: VBoxContainer = $LiveMatchBox/PartnershipsCard/Box/Scroll/RowList
@onready var next_ball_button: Button = $LiveMatchBox/Controls/NextBallButton
@onready var over_button: Button = $LiveMatchBox/Controls/OverButton
@onready var auto_button: Button = $LiveMatchBox/Controls/AutoButton
@onready var speed_button: Button = $LiveMatchBox/Controls/SpeedButton
@onready var skip_button: Button = $LiveMatchBox/Controls/SkipButton
@onready var exit_button: Button = $LiveMatchBox/Controls/ExitButton
@onready var auto_timer: Timer = $LiveMatchBox/AutoTimer

const FIELD_PRESETS := ["Aggressive", "Neutral", "Defensive"]

var speed_index: int = 0
var auto_play: bool = false
var match_completed: bool = false
var field_index: int = 1
var batting_aggro: int = 5
var bowling_aggro: int = 5

# Stats Hub state — accumulated client-side from the ball-by-ball events
# this screen instance has actually seen. Ports pygame's ui/match_view.py
# Stats Hub tabs (Worm/Momentum/Manhattan have no per-over field on
# match_engine.Match, so both clients compute them from the ball stream).
# Known limitation: resuming a match already in progress (get_match_state
# after navigating away and back) starts these fresh, since only balls
# simulated through THIS screen instance are captured.
var stats_tab: String = "batting"
var _last_state: Dictionary = {}
var shot_events: Array = []
var bowling_events: Array = []
var innings_overs: Array = [[]]
var momentum_window: Array = []
var _current_innings_runs: int = 0
var _current_over_ball_count: int = 0


func _ready() -> void:
	_opposition_report_modal = OPPOSITION_REPORT_MODAL_SCENE.instantiate()
	add_child(_opposition_report_modal)
	pitch_button.pressed.connect(_on_pitch_pressed)
	opposition_button.pressed.connect(_on_opposition_report_pressed)
	start_button.pressed.connect(_on_start_pressed)
	next_ball_button.pressed.connect(func(): _simulate(1))
	over_button.pressed.connect(func(): _simulate(6))
	skip_button.pressed.connect(func(): _simulate(_skip_count()))
	auto_button.pressed.connect(_on_auto_pressed)
	speed_button.pressed.connect(_on_speed_pressed)
	exit_button.pressed.connect(_on_exit_pressed)
	auto_timer.timeout.connect(_on_auto_timeout)
	predict_button.pressed.connect(_on_predict_pressed)
	field_button.pressed.connect(_on_field_pressed)
	batting_aggro_button.pressed.connect(_on_batting_aggro_pressed)
	bowling_aggro_button.pressed.connect(_on_bowling_aggro_pressed)
	change_bowler_button.pressed.connect(_on_change_bowler_pressed)
	drs_button.pressed.connect(_on_drs_pressed)
	for tab_button in stats_tab_bar.get_children():
		tab_button.pressed.connect(_on_stats_tab_pressed.bind(tab_button))
	refresh()


func _on_stats_tab_pressed(button: Button) -> void:
	var tab_map := {"BattingTab": "batting", "BowlingTab": "bowling", "SummaryTab": "summary",
		"ShotMapTab": "shot_map", "BoundaryTab": "boundary_map",
		"PitchMapTab": "pitch_map", "WormTab": "worm", "ManhattanTab": "manhattan",
		"MomentumTab": "momentum", "PartnershipsTab": "partnerships"}
	stats_tab = tab_map.get(button.name, "batting")
	for tab_button in stats_tab_bar.get_children():
		tab_button.set_pressed_no_signal(tab_button == button)
	_show_stats_tab()


## Reference (Cricket Captain) layout: Batting/Bowling/Summary as separate
## tabs on one scorecard card, not two always-visible side-by-side lists.
func _show_stats_tab() -> void:
	scorecard_row.visible = stats_tab in ["batting", "bowling"]
	batting_card.visible = stats_tab == "batting"
	bowling_card.visible = stats_tab == "bowling"
	summary_card.visible = stats_tab == "summary"
	partnerships_card.visible = stats_tab == "partnerships"
	stats_card.visible = stats_tab in ["shot_map", "boundary_map", "pitch_map", "worm", "manhattan", "momentum"]
	if stats_card.visible:
		stats_canvas.shot_events = shot_events
		stats_canvas.bowling_events = bowling_events
		stats_canvas.innings_overs = innings_overs
		stats_canvas.momentum_window = momentum_window
		stats_canvas.set_mode(stats_tab)
	if summary_card.visible:
		_render_summary(_last_state.get("innings", []))


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
	_is_home_fixture = fixture != null and fixture.get("home_team") == result.get("team", {}).get("id")
	_refresh_pitch_button()

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


## Mirrors ui/pre_match.py's pitch cycle button — only the home team
## chooses (matches ipc_server.py's start_match rule); away always plays
## on the engine's default. Ports get_pitch_options/set_pitch_selection,
## both already exposed over IPC since v0.65.0 but never consumed by any
## Godot screen until now.
func _refresh_pitch_button() -> void:
	pitch_button.disabled = not _is_home_fixture
	if not _is_home_fixture:
		pitch_button.text = "PITCH: AWAY FIXTURE"
		return
	var response := IpcBridge.call_method("get_pitch_options")
	if response.has("error"):
		pitch_button.text = "PITCH: GREEN"
		return
	_pitch = str(response["result"].get("current", "Green"))
	pitch_button.text = "PITCH: %s" % _pitch.to_upper()


func _on_pitch_pressed() -> void:
	if not _is_home_fixture:
		return
	_pitch = PITCH_TYPES[(PITCH_TYPES.find(_pitch) + 1) % PITCH_TYPES.size()]
	var response := IpcBridge.call_method("set_pitch_selection", {"pitch": _pitch})
	if not response.has("error"):
		pitch_button.text = "PITCH: %s" % _pitch.to_upper()


## Ports get_opposition_report, exposed over IPC since v0.63.0 but never
## consumed by any UI in either client until now.
func _on_opposition_report_pressed() -> void:
	var response := IpcBridge.call_method("get_opposition_report")
	if response.has("error"):
		title_label.text = "MATCH — opposition report failed: %s" % response["error"]
		return
	var report = response["result"].get("report")
	if report == null:
		title_label.text = "MATCH — %s" % str(response["result"].get("message", "No report available."))
		return
	_opposition_report_modal.show_for(report)


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
	prediction_label.text = ""
	shot_events = []
	bowling_events = []
	innings_overs = [[]]
	momentum_window = []
	_current_innings_runs = 0
	_current_over_ball_count = 0
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
		_accumulate_stats(event)
	_render_state(result["state"])
	if stats_card.visible:
		stats_canvas.set_mode(stats_tab)


## Feeds the Stats Hub's client-side accumulators — see the "Stats Hub
## state" comment near the top of this file for why these are computed
## from the ball stream rather than a single backend field.
func _accumulate_stats(event: Dictionary) -> void:
	if event.get("shot") != null:
		shot_events.append(event["shot"])
		if shot_events.size() > 120:
			shot_events.pop_front()
	if event.get("delivery") != null:
		bowling_events.append(event["delivery"])
		if bowling_events.size() > 120:
			bowling_events.pop_front()
	if bool(event.get("legal", false)):
		var runs := int(event.get("runs", 0))
		_current_innings_runs += runs
		_current_over_ball_count += 1
		momentum_window.append({"runs": runs, "wicket": event.get("wicket") != null})
		if momentum_window.size() > 60:
			momentum_window.pop_front()
		if _current_over_ball_count >= 6:
			innings_overs[-1].append(_current_innings_runs)
			_current_over_ball_count = 0
	if bool(event.get("innings_complete", false)):
		if _current_over_ball_count > 0:
			innings_overs[-1].append(_current_innings_runs)
		innings_overs.append([])
		_current_innings_runs = 0
		_current_over_ball_count = 0
		momentum_window = []


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


## Mirrors ui/match_view.py's PREDICT button: shows only the user's own
## team's win probability (the opponent's is implicitly 100 minus this).
func _on_predict_pressed() -> void:
	var response := IpcBridge.call_method("get_match_prediction")
	if response.has("error"):
		prediction_label.text = "Prediction unavailable: %s" % response["error"]
		return
	prediction_label.text = "Win probability: %s%%" % JsonFormat.value(response["result"].get("probability", 0))


func _on_field_pressed() -> void:
	field_index = (field_index + 1) % FIELD_PRESETS.size()
	var response := IpcBridge.call_method("set_match_field", {"preset": FIELD_PRESETS[field_index]})
	if not response.has("error"):
		_sync_tactics(response["result"])


func _on_batting_aggro_pressed() -> void:
	batting_aggro = batting_aggro % 10 + 1
	var response := IpcBridge.call_method("set_match_aggression", {"batting": batting_aggro})
	if not response.has("error"):
		_sync_tactics(response["result"])


func _on_bowling_aggro_pressed() -> void:
	bowling_aggro = bowling_aggro % 10 + 1
	var response := IpcBridge.call_method("set_match_aggression", {"bowling": bowling_aggro})
	if not response.has("error"):
		_sync_tactics(response["result"])


## Mirrors ui/match_view.py's CHANGE button: steps to the next eligible
## bowler server-side (see cycle_match_bowler in ipc_server.py).
func _on_change_bowler_pressed() -> void:
	var response := IpcBridge.call_method("cycle_match_bowler")
	if response.has("error"):
		status_label.text = "Bowler change failed: %s" % response["error"]
		return
	# _render_state() sets status_label from the match status, so it must
	# run BEFORE any one-off message this action wants to show — otherwise
	# the message is clobbered on the very next line and the player never
	# actually sees it (real pre-existing bug, caught only once a smoke
	# test asserted on status_label's text instead of just "no error").
	_render_state(response["result"])
	if not response["result"].get("bowler_changed", false):
		status_label.text = "No eligible bowler change available."


## Mirrors ui/match_view.py's DRS button: only meaningful immediately
## after a reviewable wicket (see review_decision in ipc_server.py) —
## otherwise reports "No reviewable decision" like pygame's disabled
## button would.
func _on_drs_pressed() -> void:
	var response := IpcBridge.call_method("review_decision")
	if response.has("error"):
		status_label.text = "DRS failed: %s" % response["error"]
		return
	var result: Dictionary = response.get("result", {})
	var review: Dictionary = result.get("review", {})
	if result.has("state"):
		_render_state(result["state"])
	status_label.text = "DRS: %s" % str(review.get("message", "No reviewable decision."))


func _sync_tactics(state: Dictionary) -> void:
	field_index = FIELD_PRESETS.find(str(state.get("field_preset", "Neutral")))
	if field_index == -1:
		field_index = 1
	batting_aggro = int(state.get("batting_aggression", 5))
	bowling_aggro = int(state.get("bowling_aggression", 5))
	field_button.text = "FIELD: %s" % FIELD_PRESETS[field_index].to_upper()
	batting_aggro_button.text = "BAT AGGRO: %d" % batting_aggro
	bowling_aggro_button.text = "BOWL AGGRO: %d" % bowling_aggro
	drs_button.text = "DRS: %d" % int(state.get("reviews_remaining", 0))


func _on_exit_pressed() -> void:
	var shell := get_tree().get_first_node_in_group("shell")
	if shell:
		shell.show_screen("Dashboard")


func _render_state(state: Dictionary) -> void:
	match_completed = bool(state.get("completed", false))
	var innings_list: Array = state.get("innings", [])
	if innings_list.is_empty():
		return
	_last_state = state
	var current_index: int = int(state.get("current_innings_index", innings_list.size() - 1))
	var live: Dictionary = innings_list[min(current_index, innings_list.size() - 1)]
	score_label.text = "%s %s/%s (%s ov)" % [live.get("team", "?"), JsonFormat.value(live.get("runs", 0)),
		JsonFormat.value(live.get("wickets", 0)), live.get("overs", "0.0")]
	status_label.text = str(state.get("status", "—"))
	_render_scorecard(batting_list, live.get("batting", []), true, state)
	_render_scorecard(bowling_list, live.get("bowling", []), false, state)
	_render_stamina(state.get("bowler"))
	if summary_card.visible:
		_render_summary(innings_list)
	_render_partnerships(live.get("partnerships", []))
	_sync_tactics(state)

	if match_completed:
		auto_play = false
		auto_timer.stop()
		auto_button.text = "AUTO: OFF"
		title_label.text = "MATCH DAY — %s" % state.get("result", "Match complete")
		next_ball_button.disabled = true
		over_button.disabled = true
		skip_button.disabled = true
		auto_button.disabled = true
		predict_button.disabled = true
		field_button.disabled = true
		batting_aggro_button.disabled = true
		bowling_aggro_button.disabled = true
		change_bowler_button.disabled = true
		drs_button.disabled = true
	else:
		title_label.text = "MATCH DAY — live"
		next_ball_button.disabled = false
		over_button.disabled = false
		skip_button.disabled = false
		auto_button.disabled = false
		predict_button.disabled = false
		field_button.disabled = false
		batting_aggro_button.disabled = false
		bowling_aggro_button.disabled = false
		change_bowler_button.disabled = false
		drs_button.disabled = false


## Reference (Cricket Captain) bowler card shows a Stamina bar — this
## client had nothing equivalent. `players.fatigue` (0-100, already
## tracked/recovered elsewhere) is the existing backend field; ipc_server.py's
## _match_state() now includes it on the "bowler" dict (v0.86.0).
func _render_stamina(bowler) -> void:
	for child in stamina_bar.get_children():
		child.queue_free()
	if bowler == null:
		stamina_label.text = ""
		return
	var fatigue := int(bowler.get("fatigue", 0))
	stamina_label.text = "%s stamina" % str(bowler.get("name", "?"))
	stamina_bar.add_child(AppTheme.make_bar_meter(120.0, 100.0 - fatigue, 11, AppTheme.TEXT_SECONDARY))


## New Summary tab (v0.86.0, reference: Cricket Captain's scorecard Summary
## tab) — total score/wickets/overs and extras per innings, using data
## already returned by match_engine.Match.scorecard() (no backend change).
func _render_summary(innings_list: Array) -> void:
	for child in summary_list.get_children():
		summary_list.remove_child(child)
		child.queue_free()
	if innings_list.is_empty():
		var empty := Label.new()
		empty.text = "No innings played yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		summary_list.add_child(empty)
		return
	for innings in innings_list:
		var row := VBoxContainer.new()
		row.add_theme_constant_override("separation", 2)
		var line := Label.new()
		line.text = "%s — %s/%s (%s ov)" % [innings.get("team", "?"), JsonFormat.value(innings.get("runs", 0)),
			JsonFormat.value(innings.get("wickets", 0)), innings.get("overs", "0.0")]
		line.add_theme_font_size_override("font_size", 15)
		row.add_child(line)
		var extras: Dictionary = innings.get("extras", {}) if innings.get("extras") is Dictionary else {}
		var extras_total := 0
		for value in extras.values():
			extras_total += int(value)
		var extras_label := Label.new()
		extras_label.text = "Extras: %d" % extras_total
		extras_label.add_theme_font_size_override("font_size", 11)
		extras_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		row.add_child(extras_label)
		summary_list.add_child(row)
		summary_list.add_child(HSeparator.new())


## Ports ui/match_view.py's Partnerships tab: a name-pair/runs(balls) row
## with a thin progress bar underneath (fill proportional to runs, capped
## visually at 100), most recent 6 partnerships plus the one in progress.
func _render_partnerships(partnerships: Array) -> void:
	for child in partnerships_list.get_children():
		partnerships_list.remove_child(child)
		child.queue_free()
	if partnerships.is_empty():
		var empty := Label.new()
		empty.text = "No completed partnerships yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		partnerships_list.add_child(empty)
		return
	var recent: Array = partnerships.slice(max(0, partnerships.size() - 6), partnerships.size())
	for entry in recent:
		var row := VBoxContainer.new()
		row.add_theme_constant_override("separation", 3)
		var label := Label.new()
		label.text = "%s / %s — %s (%s balls)" % [entry.get("a", "?"), entry.get("b", "?"),
			JsonFormat.value(entry.get("runs", 0)), JsonFormat.value(entry.get("balls", 0))]
		label.add_theme_font_size_override("font_size", 12)
		row.add_child(label)
		var bar_wrap := Control.new()
		bar_wrap.custom_minimum_size = Vector2(300, 6)
		var track := ColorRect.new()
		track.color = AppTheme.BORDER
		track.size = Vector2(300, 5)
		bar_wrap.add_child(track)
		var fill := ColorRect.new()
		fill.color = AppTheme.HEADER_GREEN
		fill.size = Vector2(clampf(float(entry.get("runs", 0)) / 100.0, 0.0, 1.0) * 300, 5)
		bar_wrap.add_child(fill)
		row.add_child(bar_wrap)
		partnerships_list.add_child(row)


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
