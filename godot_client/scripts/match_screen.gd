extends Control
## Match Day — pre-match hub (fixture, XI, ground) plus, once started, the
## real live ball-by-ball feed: match_engine.Match run through ipc_server.py's
## start_match/simulate_balls/get_match_state, one real delivery at a time
## (not a bulk-simulate-then-replay), mirroring ui/match_view.py's
## simulate_ball() loop. Wagon wheel, pitch map, worm/momentum/manhattan
## graphs, tactics, and DRS are all here; the FIELD tab (v4.13.0/v4.14.0
## Match Day rebuild, Part 3) is a real drag-and-place field editor
## (ground_view.gd, reused from the pre-match hub) — field positions
## genuinely affect catch/boundary-save outcomes server-side, not a
## cosmetic overlay on the 3 presets.

const SPEEDS := {"Normal": 0.9, "Fast": 0.22, "Instant": 0.03}
const SPEED_ORDER := ["Normal", "Fast", "Instant"]

const OPPOSITION_REPORT_MODAL_SCENE := preload("res://scenes/opposition_report_modal.tscn")
const BOWLER_PICKER_MODAL_SCENE := preload("res://scenes/bowler_picker_modal.tscn")

var _audio: AudioManager = null
var _bowler_picker_modal: BowlerPickerModal = null

@onready var title_label: Label = $Title
@onready var pre_match_box: Control = $PreMatchBox
@onready var fixture_label: Label = $PreMatchBox/FixtureBar/FixtureLabel
@onready var start_button: Button = $PreMatchBox/StartButton
@onready var pitch_status_box: PanelContainer = $PreMatchBox/ControlsRow/PitchStatusBox
@onready var pitch_status_label: Label = $PreMatchBox/ControlsRow/PitchStatusBox/PitchStatusLabel
@onready var opposition_button: Button = $PreMatchBox/ControlsRow/OppositionButton
@onready var xi_list: VBoxContainer = $PreMatchBox/Row/LineupCard/Box/List
@onready var xi_header: Label = $PreMatchBox/Row/LineupCard/Box/Header

var _opposition_report_modal: OppositionReportModal = null
var _is_home_fixture: bool = false

@onready var live_match_box: Control = $LiveMatchBox
const LMB := "LiveMatchBox/Margin/MainCol/"
const LEFT := LMB + "BodySplit/LeftCol/"
const CENTER := LMB + "BodySplit/CenterCol/"
const RIGHT := LMB + "BodySplit/RightCol/"
const TABS := RIGHT + "TabContentArea/"
@onready var score_label: Label = $LiveMatchBox/Margin/MainCol/ScoreBar/Split/ScoreBox/ScoreLabel
@onready var status_label: Label = $LiveMatchBox/Margin/MainCol/ScoreBar/Split/InfoBox/StatusLabel
@onready var prediction_label: Label = $LiveMatchBox/Margin/MainCol/ScoreBar/Split/InfoBox/PredictionLabel
@onready var rates_label: Label = $LiveMatchBox/Margin/MainCol/ScoreBar/Split/InfoBox/RatesLabel
@onready var live_strip_card: PanelContainer = get_node(LEFT + "LiveStripCard")
@onready var live_pitch_view: Control = get_node(CENTER + "LivePitchCard/Box/LivePitchView")
@onready var perspective_label: Label = get_node(CENTER + "LivePitchCard/Box/PerspectiveLabel")
@onready var delivery_readout: Label = get_node(CENTER + "ReadoutCard/Box/Readout")
@onready var striker_name_label: Label = get_node(LEFT + "LiveStripCard/Box/StrikerBox/StrikerName")
@onready var striker_figures_label: Label = get_node(LEFT + "LiveStripCard/Box/StrikerBox/StrikerFigures")
@onready var non_striker_name_label: Label = get_node(LEFT + "LiveStripCard/Box/NonStrikerBox/NonStrikerName")
@onready var non_striker_figures_label: Label = get_node(LEFT + "LiveStripCard/Box/NonStrikerBox/NonStrikerFigures")
@onready var strip_bowler_name_label: Label = get_node(LEFT + "LiveStripCard/Box/BowlerBox/BowlerName")
@onready var strip_bowler_figures_label: Label = get_node(LEFT + "LiveStripCard/Box/BowlerBox/BowlerFigures")
@onready var batting_card: PanelContainer = get_node(TABS + "Row/BattingCard")
@onready var bowling_card: PanelContainer = get_node(TABS + "Row/BowlingCard")
@onready var batting_list: VBoxContainer = get_node(TABS + "Row/BattingCard/Box/Scroll/RowList")
@onready var bowling_list: VBoxContainer = get_node(TABS + "Row/BowlingCard/Box/Scroll/RowList")
@onready var stamina_label: Label = get_node(TABS + "Row/BowlingCard/Box/StaminaRow/StaminaLabel")
@onready var stamina_bar: Control = get_node(TABS + "Row/BowlingCard/Box/StaminaRow/StaminaBar")
@onready var summary_card: PanelContainer = get_node(TABS + "SummaryCard")
@onready var summary_list: VBoxContainer = get_node(TABS + "SummaryCard/Box/Scroll/RowList")
@onready var commentary_list: VBoxContainer = get_node(RIGHT + "CommentaryCard/Box/Scroll/RowList")
@onready var commentary_scroll: ScrollContainer = get_node(RIGHT + "CommentaryCard/Box/Scroll")
@onready var current_over_header: Label = get_node(RIGHT + "CommentaryCard/Box/CurrentOverHeader")
@onready var current_over_strip: HBoxContainer = get_node(RIGHT + "CommentaryCard/Box/CurrentOverScroll/CurrentOverStrip")
@onready var overs_list: HBoxContainer = get_node(RIGHT + "CommentaryCard/Box/OversScroll/OversList")
@onready var predict_button: Button = get_node(LEFT + "TacticsRow/PredictButton")
@onready var drs_button: Button = get_node(LEFT + "TacticsRow/DrsButton")
@onready var bowler_card: PanelContainer = get_node(LEFT + "BowlerCard")
@onready var batsman_card: PanelContainer = get_node(LEFT + "BatsmanCard")
@onready var bowler_card_name_label: Label = get_node(LEFT + "BowlerCard/Box/Header/BowlerCardNameLabel")
@onready var change_bowler_button: Button = get_node(LEFT + "BowlerCard/Box/Header/ChangeBowlerButton")
@onready var pitch_strip_view: Control = get_node(LEFT + "BowlerCard/Box/Body/PitchStripView")
@onready var bowling_aggro_label: Label = get_node(LEFT + "BowlerCard/Box/Body/AggroCol/BowlingAggroLabel")
@onready var bowling_aggro_slider: VSlider = get_node(LEFT + "BowlerCard/Box/Body/AggroCol/BowlingAggroSlider")
@onready var link_button: Button = get_node(LEFT + "BatsmanCard/Box/Header/LinkButton")
@onready var striker_row_marker: Label = get_node(LEFT + "BatsmanCard/Box/StrikerRow/StrikerMarker")
@onready var striker_row_name: Label = get_node(LEFT + "BatsmanCard/Box/StrikerRow/NameLabel")
@onready var striker_row_figures: Label = get_node(LEFT + "BatsmanCard/Box/StrikerRow/FiguresLabel")
@onready var striker_row_aggro_slider: VSlider = get_node(LEFT + "BatsmanCard/Box/StrikerRow/AggroSlider")
@onready var striker_row_aggro_value: Label = get_node(LEFT + "BatsmanCard/Box/StrikerRow/AggroValueLabel")
@onready var non_striker_row_name: Label = get_node(LEFT + "BatsmanCard/Box/NonStrikerRow/NameLabel")
@onready var non_striker_row_figures: Label = get_node(LEFT + "BatsmanCard/Box/NonStrikerRow/FiguresLabel")
@onready var non_striker_row_aggro_slider: VSlider = get_node(LEFT + "BatsmanCard/Box/NonStrikerRow/AggroSlider")
@onready var non_striker_row_aggro_value: Label = get_node(LEFT + "BatsmanCard/Box/NonStrikerRow/AggroValueLabel")
@onready var stats_tab_bar: HBoxContainer = get_node(RIGHT + "TabBarScroll/StatsTabBar")
@onready var scorecard_row: HBoxContainer = get_node(TABS + "Row")
@onready var stats_card: PanelContainer = get_node(TABS + "StatsCard")
@onready var stats_canvas: MatchStatsCanvas = get_node(TABS + "StatsCard/StatsCanvas")
@onready var partnerships_card: PanelContainer = get_node(TABS + "PartnershipsCard")
@onready var partnerships_list: VBoxContainer = get_node(TABS + "PartnershipsCard/Box/Scroll/RowList")
@onready var field_card: PanelContainer = get_node(TABS + "FieldCard")
@onready var field_ground_view: Control = get_node(TABS + "FieldCard/Box/GroundView")
@onready var field_aggressive_button: Button = get_node(TABS + "FieldCard/Box/PresetRow/AggressiveButton")
@onready var field_neutral_button: Button = get_node(TABS + "FieldCard/Box/PresetRow/NeutralButton")
@onready var field_defensive_button: Button = get_node(TABS + "FieldCard/Box/PresetRow/DefensiveButton")
@onready var ball_tracker_list: VBoxContainer = get_node(LEFT + "BallTrackerCard/Box/RowList")
@onready var next_ball_button: Button = get_node(LEFT + "Controls/NextBallButton")
@onready var over_button: Button = get_node(LEFT + "Controls/OverButton")
@onready var highlights_button: Button = get_node(LEFT + "Controls/HighlightsButton")
@onready var auto_button: Button = get_node(LEFT + "Controls/AutoButton")
@onready var speed_button: Button = get_node(LEFT + "Controls/SpeedButton")
@onready var skip_button: Button = get_node(LEFT + "Controls/SkipButton")
@onready var exit_button: Button = get_node(LEFT + "Controls/ExitButton")
@onready var highlights_card: PanelContainer = get_node(TABS + "HighlightsCard")
@onready var highlights_list: VBoxContainer = get_node(TABS + "HighlightsCard/Box/Scroll/RowList")
@onready var auto_timer: Timer = $LiveMatchBox/AutoTimer

## Per-batter mini wagon wheels next to their name in the Batsman Card
## (reference: the bowler/batter concept screenshots show a small wagon
## wheel inline with each not-out batter) — created once in _ready() and
## just re-fed/redrawn each render rather than rebuilt every ball.
var _striker_wagon: MatchStatsCanvas = null
var _non_striker_wagon: MatchStatsCanvas = null
## v4.55.0: reference-matchday subtitles — each batter card carries its own
## 'Format Batting Avg/SR' line and the bowler card a 'Format Bowling Avg'
## line, both fed from the career figures ipc_server now attaches to the
## live striker/non-striker/bowler snapshots.
var _striker_subtitle: Label = null
var _non_striker_subtitle: Label = null
var _bowler_card_avg_label: Label = null

var speed_index: int = 0
var auto_play: bool = false
var match_completed: bool = false
var bowling_aggro: int = 5
var batting_aggression_linked: bool = true

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
var commentary_events: Array = []
var current_over_pills: Array = []
var current_over_index: int = -1
var over_first_panel: Dictionary = {}
var over_chip_buttons: Dictionary = {}


func _ready() -> void:
	_audio = AudioManager.new()
	add_child(_audio)
	_opposition_report_modal = OPPOSITION_REPORT_MODAL_SCENE.instantiate()
	add_child(_opposition_report_modal)
	_bowler_picker_modal = BOWLER_PICKER_MODAL_SCENE.instantiate()
	add_child(_bowler_picker_modal)
	_bowler_picker_modal.bowler_selected.connect(_on_bowler_selected)
	opposition_button.pressed.connect(_on_opposition_report_pressed)
	start_button.pressed.connect(_on_start_pressed)
	next_ball_button.pressed.connect(func(): _simulate(1))
	over_button.pressed.connect(func(): _simulate(6))
	highlights_button.pressed.connect(_on_highlights_pressed)
	skip_button.pressed.connect(func(): _simulate(_skip_count()))
	auto_button.pressed.connect(_on_auto_pressed)
	speed_button.pressed.connect(_on_speed_pressed)
	exit_button.pressed.connect(_on_exit_pressed)
	auto_timer.timeout.connect(_on_auto_timeout)
	predict_button.pressed.connect(_on_predict_pressed)
	# v4.22.0: user asked what PREDICT actually does — it's a real live
	# call into the match engine's win-probability model (get_match_prediction),
	# not a cosmetic label; make that explicit rather than relying on the
	# result text alone to explain itself.
	predict_button.tooltip_text = "Runs 240 Monte Carlo simulations of the rest of this match from the current score, wickets, and overs, and shows YOUR team's share of the wins."
	field_aggressive_button.pressed.connect(_on_field_preset_pressed.bind("Aggressive"))
	field_neutral_button.pressed.connect(_on_field_preset_pressed.bind("Neutral"))
	field_defensive_button.pressed.connect(_on_field_preset_pressed.bind("Defensive"))
	field_ground_view.layout_changed.connect(_on_field_layout_changed)
	# drag_ended (not value_changed) so a slider fires one IPC call per
	# drag gesture, not one per pixel of mouse movement.
	striker_row_aggro_slider.drag_ended.connect(_on_striker_aggro_changed)
	non_striker_row_aggro_slider.drag_ended.connect(_on_non_striker_aggro_changed)
	link_button.toggled.connect(_on_batting_aggro_link_toggled)
	bowling_aggro_slider.drag_ended.connect(_on_bowling_aggro_changed)
	pitch_strip_view.target_chosen.connect(_on_delivery_target_chosen)
	change_bowler_button.pressed.connect(_on_change_bowler_pressed)
	drs_button.pressed.connect(_on_drs_pressed)
	for tab_button in stats_tab_bar.get_children():
		tab_button.pressed.connect(_on_stats_tab_pressed.bind(tab_button))
	_style_match_buttons()
	_restructure_live_layout()
	refresh()


func _make_mini_wagon() -> MatchStatsCanvas:
	var canvas := MatchStatsCanvas.new()
	canvas.custom_minimum_size = Vector2(52, 52)
	canvas.compact = true
	canvas.set_mode("shot_map")
	return canvas


## v4.53.0 structural pass: pure node-tree surgery, no new .tscn editing —
## every @onready `get_node(LEFT/CENTER/RIGHT + ...)` above has already
## resolved to a live node reference by the time _ready()'s body runs, so
## reordering/reparenting those same node objects here doesn't invalidate
## any of them. Reference (bowler/batter concept screenshots): scorecard +
## Ball-tracker on the LEFT, bowler/batsman tactics cards on the RIGHT —
## the opposite of this scene's original v4.20.0 column order, which was
## never actually compared against the reference until now. The old
## CenterCol "live pitch" broadcast camera is retired — each batsman
## card's own mini wagon wheel (v4.51.0) already covers that role, and the
## reference has no equivalent third column at all.
func _restructure_live_layout() -> void:
	var body_split := get_node(LMB + "BodySplit")
	var left_col := get_node(LMB + "BodySplit/LeftCol")
	var center_col := get_node(LMB + "BodySplit/CenterCol")
	var right_col := get_node(LMB + "BodySplit/RightCol")
	body_split.move_child(right_col, 0)
	center_col.visible = false
	# Ball-tracker sits directly under the scorecard in the reference, not
	# grouped in with the bowler/batsman tactics controls.
	var ball_tracker_card: Control = left_col.get_node("BallTrackerCard")
	left_col.remove_child(ball_tracker_card)
	right_col.add_child(ball_tracker_card)
	_build_bowler_figures_row()
	_restructure_batter_cards()


## Reference: the bowler card shows a Stamina bar plus O/M/R/W/Econ
## figures directly under the name — this scene had a stamina bar in the
## Stats Hub's Bowling tab (stamina_bar/_render_stamina) but nothing on
## the live tactics card itself. Reuses the same bar-meter helper and the
## same figures-string shape as _set_bowler_strip, just placed here too.
var _bowler_card_stamina_bar: Control = null
var _bowler_card_figures_label: Label = null


func _build_bowler_figures_row() -> void:
	var bowler_box := get_node(LEFT + "BowlerCard/Box")
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	var stamina_wrap := VBoxContainer.new()
	var stamina_caption := Label.new()
	stamina_caption.text = "STAMINA"
	stamina_caption.add_theme_font_size_override("font_size", 9)
	stamina_caption.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	stamina_wrap.add_child(stamina_caption)
	_bowler_card_stamina_bar = Control.new()
	stamina_wrap.add_child(_bowler_card_stamina_bar)
	row.add_child(stamina_wrap)
	_bowler_card_figures_label = Label.new()
	_bowler_card_figures_label.add_theme_font_size_override("font_size", 12)
	_bowler_card_figures_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	row.add_child(_bowler_card_figures_label)
	bowler_box.add_child(row)
	bowler_box.move_child(row, 1)
	_bowler_card_avg_label = Label.new()
	_bowler_card_avg_label.add_theme_font_size_override("font_size", 10)
	_bowler_card_avg_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	_bowler_card_avg_label.text = "BOWL AVG —"
	bowler_box.add_child(_bowler_card_avg_label)
	bowler_box.move_child(_bowler_card_avg_label, 2)


func _update_bowler_card_figures(bowler, bowling_rows: Array) -> void:
	if _bowler_card_stamina_bar == null:
		return
	for child in _bowler_card_stamina_bar.get_children():
		child.queue_free()
	if bowler == null:
		_bowler_card_figures_label.text = ""
		if _bowler_card_avg_label:
			_bowler_card_avg_label.text = "BOWL AVG —"
		return
	var fatigue := int(bowler.get("fatigue", 0))
	_bowler_card_stamina_bar.add_child(AppTheme.make_bar_meter(90.0, 100.0 - fatigue, 10, AppTheme.TEXT_SECONDARY))
	if _bowler_card_avg_label:
		var bow_avg := float(bowler.get("career_bowling_average", 0.0))
		_bowler_card_avg_label.text = "BOWL AVG %s" % ("%.2f" % bow_avg if bow_avg > 0.0 else "—")
	var player_id := int(bowler.get("id", -1))
	for row in bowling_rows:
		if int(row.get("player_id", -1)) == player_id:
			_bowler_card_figures_label.text = "%s-%d-%d-%d  Econ %.2f" % [
				JsonFormat.value(row.get("overs", "0.0")), int(row.get("maidens", 0)),
				int(row.get("runs", 0)), int(row.get("wickets", 0)), float(row.get("economy", 0.0))]
			return
	_bowler_card_figures_label.text = "0.0-0-0-0  Econ 0.00"


## Reference: each not-out batter is their own bordered card (name/figures,
## avg/SR subtitle, wagon wheel, pitch-with-batter icon, VERTICAL aggression
## bar). v4.54.0 only got the grouping right (per-batter border inside one
## card); this pass rebuilds each row into a fully independent card and swaps
## the aggression control to the reference's vertical slider. The slider and
## label objects keep their identities, so the drag_ended wiring and every
## @onready reference above stay valid through the reparenting.
func _restructure_batter_cards() -> void:
	_striker_wagon = _make_mini_wagon()
	_non_striker_wagon = _make_mini_wagon()
	var box := get_node(LEFT + "BatsmanCard/Box")
	_rebuild_batter_card(box, box.get_node("StrikerRow"), _striker_wagon, true)
	_rebuild_batter_card(box, box.get_node("NonStrikerRow"), _non_striker_wagon, false)


func _rebuild_batter_card(box: VBoxContainer, row: HBoxContainer, wagon: MatchStatsCanvas, is_striker: bool) -> void:
	var index := row.get_index()
	var marker: Label = row.get_node("StrikerMarker")
	var name_lbl: Label = row.get_node("NameLabel")
	var fig_lbl: Label = row.get_node("FiguresLabel")
	var slider: VSlider = row.get_node("AggroSlider")
	var value_lbl: Label = row.get_node("AggroValueLabel")
	for child in row.get_children():
		row.remove_child(child)
	box.remove_child(row)
	row.free()
	var card := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = AppTheme.SURFACE
	style.set_corner_radius_all(8)
	style.set_border_width_all(1)
	style.border_color = AppTheme.BORDER
	style.content_margin_left = 8
	style.content_margin_right = 8
	style.content_margin_top = 6
	style.content_margin_bottom = 6
	card.add_theme_stylebox_override("panel", style)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 4)
	card.add_child(vbox)
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 6)
	header.add_child(marker)
	header.add_child(name_lbl)
	header.add_child(fig_lbl)
	vbox.add_child(header)
	var subtitle := Label.new()
	subtitle.add_theme_font_size_override("font_size", 10)
	subtitle.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	subtitle.text = "AVG —  SR —"
	vbox.add_child(subtitle)
	if is_striker:
		_striker_subtitle = subtitle
	else:
		_non_striker_subtitle = subtitle
	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation", 8)
	body.add_child(wagon)
	body.add_child(_make_pitch_batter_icon())
	var aggro_col := VBoxContainer.new()
	aggro_col.add_theme_constant_override("separation", 2)
	value_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	aggro_col.add_child(value_lbl)
	aggro_col.add_child(slider)
	body.add_child(aggro_col)
	vbox.add_child(body)
	box.add_child(card)
	box.move_child(card, index)


## Reference: a small pitch-strip-with-batter-silhouette icon beside each
## batsman's aggression column. Drawn once via the CanvasItem.draw signal —
## a plain Control keeps it lighter than a full custom scene.
func _make_pitch_batter_icon() -> Control:
	var icon := Control.new()
	icon.custom_minimum_size = Vector2(34, 52)
	icon.draw.connect(func():
		var w := icon.size.x
		var h := icon.size.y
		var strip_x := w * 0.36
		var strip_w := w * 0.28
		icon.draw_rect(Rect2(strip_x - 1, 0, strip_w + 2, h), AppTheme.BORDER)
		icon.draw_rect(Rect2(strip_x, 0, strip_w, h), Color(0.86, 0.80, 0.62))
		var cx := w * 0.5
		icon.draw_circle(Vector2(cx, 16.0), 3.5, Color(0.94, 0.86, 0.78))
		icon.draw_line(Vector2(cx, 20.0), Vector2(cx, 33.0), AppTheme.TEXT_PRIMARY, 3.0)
		icon.draw_line(Vector2(cx, 24.0), Vector2(cx - 5.0, 33.0), AppTheme.TEXT_PRIMARY, 2.5)
		icon.draw_line(Vector2(cx, 24.0), Vector2(cx + 5.0, 33.0), AppTheme.TEXT_PRIMARY, 2.5)
		icon.draw_line(Vector2(cx - 5.0, 33.0), Vector2(cx - 2.0, 35.0), AppTheme.TEXT_PRIMARY, 2.0)
		icon.draw_line(Vector2(cx + 5.0, 33.0), Vector2(cx + 2.0, 35.0), AppTheme.TEXT_PRIMARY, 2.0)
	)
	return icon


func _style_match_buttons() -> void:
	# v4.32.0: pre-match hub polish. The fixture line used to be the bare
	# default panel with default-sized text — give it the same broadcast
	# treatment as the live scorebar (deep green band, gold text) so the
	# screen reads like a real scoreboard page from the first second.
	var fixture_box := StyleBoxFlat.new()
	fixture_box.bg_color = AppTheme.HEADER_GREEN
	fixture_box.set_corner_radius_all(8)
	fixture_box.content_margin_left = 16
	fixture_box.content_margin_right = 16
	fixture_box.content_margin_top = 7
	fixture_box.content_margin_bottom = 7
	$PreMatchBox/FixtureBar.add_theme_stylebox_override("panel", fixture_box)
	fixture_label.add_theme_font_size_override("font_size", 15)
	fixture_label.add_theme_color_override("font_color", AppTheme.GOLD)
	# START MATCH is the hub's single primary action — make it the one
	# filled-green button on the screen (like the control row in live play),
	# not just another default grey button stretched full width.
	var start_box := StyleBoxFlat.new()
	start_box.bg_color = AppTheme.HEADER_GREEN
	start_box.set_corner_radius_all(8)
	start_box.set_border_width_all(1)
	start_box.border_color = AppTheme.HEADER_GREEN
	start_button.add_theme_stylebox_override("normal", start_box)
	var start_hover := start_box.duplicate()
	start_hover.bg_color = AppTheme.HEADER_GREEN.lightened(0.08)
	start_button.add_theme_stylebox_override("hover", start_hover)
	var start_pressed := start_box.duplicate()
	start_pressed.bg_color = AppTheme.HEADER_GREEN.darkened(0.1)
	start_button.add_theme_stylebox_override("pressed", start_pressed)
	var start_disabled := start_box.duplicate()
	start_disabled.bg_color = AppTheme.SURFACE
	start_disabled.border_color = AppTheme.BORDER
	start_button.add_theme_stylebox_override("disabled", start_disabled)
	start_button.add_theme_color_override("font_color", AppTheme.CARD)
	start_button.add_theme_color_override("font_hover_color", Color(1, 1, 1, 1))
	start_button.add_theme_color_override("font_pressed_color", Color(1, 1, 1, 1))
	start_button.add_theme_color_override("font_disabled_color", AppTheme.TEXT_MUTED)
	start_button.add_theme_font_size_override("font_size", 14)
	# v4.27.0: PITCH status used to be a bare, unstyled Label sitting next
	# to the properly-boxed OPPOSITION REPORT button — the user flagged it
	# as looking broken/misaligned. Give it the identical card-box look
	# every other pre-match/tactical control already has.
	var pitch_box := StyleBoxFlat.new()
	pitch_box.bg_color = AppTheme.CARD
	pitch_box.set_corner_radius_all(8)
	pitch_box.set_border_width_all(1)
	pitch_box.border_color = AppTheme.BORDER
	pitch_box.content_margin_left = 12
	pitch_box.content_margin_right = 12
	pitch_box.content_margin_top = 6
	pitch_box.content_margin_bottom = 6
	pitch_status_box.add_theme_stylebox_override("panel", pitch_box)
	pitch_status_label.add_theme_font_size_override("font_size", 11)
	pitch_status_label.add_theme_color_override("font_color", AppTheme.HEADER_GREEN)
	var tactical_buttons := [predict_button, field_aggressive_button, field_neutral_button,
		field_defensive_button, change_bowler_button, drs_button, opposition_button]
	striker_row_aggro_value.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	non_striker_row_aggro_value.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	bowling_aggro_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	for btn in tactical_buttons:
		if btn:
			var box := StyleBoxFlat.new()
			box.bg_color = AppTheme.CARD
			box.set_corner_radius_all(8)
			box.set_border_width_all(1)
			box.border_color = AppTheme.BORDER
			box.content_margin_left = 12
			box.content_margin_right = 12
			box.content_margin_top = 8
			box.content_margin_bottom = 8
			btn.add_theme_stylebox_override("normal", box)
			var hover := box.duplicate()
			hover.bg_color = AppTheme.HOVER
			btn.add_theme_stylebox_override("hover", hover)
			btn.add_theme_font_size_override("font_size", 11)
	var control_buttons := [next_ball_button, over_button, highlights_button, skip_button, auto_button, speed_button, exit_button]
	for btn in control_buttons:
		if btn:
			var box := StyleBoxFlat.new()
			box.bg_color = AppTheme.ACCENT
			box.set_corner_radius_all(8)
			box.content_margin_left = 12
			box.content_margin_right = 12
			box.content_margin_top = 8
			box.content_margin_bottom = 8
			btn.add_theme_stylebox_override("normal", box)
			var hover := box.duplicate()
			hover.bg_color = AppTheme.ACCENT.lightened(0.1)
			btn.add_theme_stylebox_override("hover", hover)
			btn.add_theme_color_override("font_color", AppTheme.CARD)
			btn.add_theme_font_size_override("font_size", 12)
	# v4.32.0: the always-on batter/bowler figures strip gets a clean card
	# with a thin gold top accent and role captions so the three columns
	# (striker / non-striker / bowler) are recognisable at a glance.
	var strip_box := StyleBoxFlat.new()
	strip_box.bg_color = AppTheme.CARD
	strip_box.set_corner_radius_all(8)
	strip_box.set_border_width_all(1)
	strip_box.border_color = AppTheme.GOLD
	strip_box.border_width_top = 2
	strip_box.content_margin_left = 12
	strip_box.content_margin_right = 12
	strip_box.content_margin_top = 6
	strip_box.content_margin_bottom = 6
	live_strip_card.add_theme_stylebox_override("panel", strip_box)
	for caption in [get_node(LEFT + "LiveStripCard/Box/StrikerBox/Caption"),
			get_node(LEFT + "LiveStripCard/Box/NonStrikerBox/Caption"),
			get_node(LEFT + "LiveStripCard/Box/BowlerBox/Caption")]:
		caption.add_theme_font_size_override("font_size", 9)
		caption.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	striker_name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	non_striker_name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	# The bowler's column is the only one showing bowling figures — tint its
	# name blue so the eye picks the fielding side out of the strip.
	strip_bowler_name_label.add_theme_color_override("font_color", AppTheme.ACCENT)
	striker_figures_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	non_striker_figures_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	strip_bowler_figures_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	# Broadcast-style score bar: a deep green header (real scoreboards
	# never sit on the same flat card colour as everything else on the
	# page) with gold score text, instead of the plain default panel.
	# v4.22.0: trimmed down (was 76px/28pt) — user feedback called the
	# green bar oversized; this keeps the broadcast treatment but gives
	# the pitch strip/cards below more of the tight vertical budget.
	var score_bar: PanelContainer = $LiveMatchBox/Margin/MainCol/ScoreBar
	var score_box := StyleBoxFlat.new()
	score_box.bg_color = AppTheme.HEADER_GREEN
	score_box.set_corner_radius_all(8)
	score_box.content_margin_left = 16
	score_box.content_margin_right = 16
	score_box.content_margin_top = 5
	score_box.content_margin_bottom = 5
	score_bar.add_theme_stylebox_override("panel", score_box)
	if score_label:
		score_label.add_theme_font_size_override("font_size", 20)
		score_label.add_theme_color_override("font_color", AppTheme.GOLD)
	if status_label:
		status_label.add_theme_font_size_override("font_size", 12)
		status_label.add_theme_color_override("font_color", Color(1, 1, 1, 0.92))
	if prediction_label:
		prediction_label.add_theme_font_size_override("font_size", 12)
		prediction_label.add_theme_color_override("font_color", AppTheme.GOLD)
	if rates_label:
		rates_label.add_theme_font_size_override("font_size", 12)
		rates_label.add_theme_color_override("font_color", Color(1, 1, 1, 0.75))
	# Style stats tabs
	for tab_button in stats_tab_bar.get_children():
		tab_button.add_theme_font_size_override("font_size", 11)
	var tracker_box := StyleBoxFlat.new()
	tracker_box.bg_color = AppTheme.CARD
	tracker_box.set_corner_radius_all(8)
	tracker_box.set_border_width_all(1)
	tracker_box.border_color = AppTheme.BORDER
	tracker_box.content_margin_left = 10
	tracker_box.content_margin_right = 10
	tracker_box.content_margin_top = 6
	tracker_box.content_margin_bottom = 6
	get_node(LEFT + "BallTrackerCard").add_theme_stylebox_override("panel", tracker_box)
	get_node(LEFT + "BallTrackerCard/Box/Header").add_theme_color_override("font_color", AppTheme.TEXT_MUTED)


const STATS_TAB_MAP := {"BattingTab": "batting", "BowlingTab": "bowling", "SummaryTab": "summary",
	"ShotMapTab": "shot_map", "BoundaryTab": "boundary_map",
	"PitchMapTab": "pitch_map", "WormTab": "worm", "ManhattanTab": "manhattan",
	"MomentumTab": "momentum", "PartnershipsTab": "partnerships",
	"FieldPositionsTab": "field_positions", "FieldTab": "field"}


func _on_stats_tab_pressed(button: Button) -> void:
	stats_tab = STATS_TAB_MAP.get(button.name, "batting")
	for tab_button in stats_tab_bar.get_children():
		tab_button.set_pressed_no_signal(tab_button == button)
	_show_stats_tab()


func _show_stats_tab() -> void:
	scorecard_row.visible = stats_tab in ["batting", "bowling"]
	batting_card.visible = stats_tab == "batting"
	bowling_card.visible = stats_tab == "bowling"
	summary_card.visible = stats_tab == "summary"
	partnerships_card.visible = stats_tab == "partnerships"
	field_card.visible = stats_tab == "field"
	stats_card.visible = stats_tab in ["shot_map", "boundary_map", "pitch_map", "worm", "manhattan", "momentum", "field_positions"]
	if stats_card.visible:
		stats_canvas.shot_events = shot_events
		stats_canvas.bowling_events = bowling_events
		stats_canvas.innings_overs = innings_overs
		stats_canvas.momentum_window = momentum_window
		stats_canvas.set_mode(stats_tab)
	if summary_card.visible:
		_render_summary(_last_state)
	# Update tab styling
	for tab_button in stats_tab_bar.get_children():
		AppTheme.style_tab_button(tab_button, STATS_TAB_MAP.get(tab_button.name, "") == stats_tab)


func refresh() -> void:
	title_label.text = "MATCH DAY"
	var state_response := IpcBridge.call_method("get_match_state")
	if not state_response.has("error"):
		_show_live(state_response["result"])
		return
	_show_pre_match()


func _shell() -> Node:
	return get_tree().get_first_node_in_group("shell")


func _show_pre_match() -> void:
	pre_match_box.visible = true
	live_match_box.visible = false
	auto_timer.stop()
	auto_play = false
	var shell := _shell()
	if shell:
		shell.set_chrome_visible(true)
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
	_refresh_pitch_status()

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
	# v4.32.0: a column header row so the XI reads like a real team sheet
	# instead of a flat name list.
	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 12)
	var head_cols := [["#", 24], ["NAME", 178], ["ROLE", 92], ["OVR", 40]]
	for pair in head_cols:
		var head_label := Label.new()
		head_label.text = str(pair[0])
		head_label.custom_minimum_size = Vector2(int(pair[1]), 0)
		head_label.add_theme_font_size_override("font_size", 10)
		head_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		head.add_child(head_label)
	xi_list.add_child(head)
	for i in range(xi.size()):
		var player: Dictionary = xi[i]
		var tags := []
		if player.get("id") == result.get("captain_id"): tags.append("C")
		if player.get("id") == result.get("keeper_id"): tags.append("WK")
		# Card per row: alternating fill plus a gold left edge for the
		# captain/keeper so the leadership spine stands out at a glance.
		var panel := PanelContainer.new()
		var box := StyleBoxFlat.new()
		box.bg_color = AppTheme.CARD if i % 2 == 0 else AppTheme.SURFACE
		box.set_corner_radius_all(6)
		box.set_border_width_all(1)
		box.border_color = AppTheme.BORDER
		if not tags.is_empty():
			box.border_color = AppTheme.GOLD
			box.border_width_left = 3
		box.content_margin_left = 10
		box.content_margin_right = 10
		box.content_margin_top = 4
		box.content_margin_bottom = 4
		panel.add_theme_stylebox_override("panel", box)
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		var order_label := Label.new()
		order_label.text = "%d" % (i + 1)
		order_label.custom_minimum_size = Vector2(24, 0)
		order_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		row.add_child(order_label)
		var suffix := " (%s)" % "/".join(tags) if not tags.is_empty() else ""
		var name_label := Label.new()
		name_label.text = "%s%s" % [player.get("name", "?"), suffix]
		name_label.custom_minimum_size = Vector2(178, 0)
		name_label.clip_text = true
		if not tags.is_empty():
			name_label.add_theme_color_override("font_color", AppTheme.GOLD)
		row.add_child(name_label)
		var role_label := Label.new()
		role_label.text = player.get("role", "?")
		role_label.custom_minimum_size = Vector2(92, 0)
		role_label.clip_text = true
		role_label.add_theme_color_override("font_color", AppTheme.role_colour(str(player.get("role", "?"))))
		row.add_child(role_label)
		var overall := int(player.get("overall", 0))
		var overall_label := Label.new()
		overall_label.text = JsonFormat.value(overall) if overall > 0 else "—"
		overall_label.custom_minimum_size = Vector2(40, 0)
		overall_label.add_theme_color_override("font_color", AppTheme.attribute_colour(float(overall)))
		overall_label.add_theme_font_size_override("font_size", 12)
		row.add_child(overall_label)
		panel.add_child(row)
		xi_list.add_child(panel)


## v4.26.0: pitch choice moved to the Facilities screen with a real
## groundskeeping delay (database.set_pitch_selection) — this is now a
## read-only status line, not a clickable cycle button, since pitch is no
## longer a free instant tactical toggle. Only the home team's pitch
## matters (matches ipc_server.py's start_match rule); away always plays
## on the engine's default.
func _refresh_pitch_status() -> void:
	if not _is_home_fixture:
		pitch_status_label.text = "PITCH: away fixture (opponent's ground)"
		return
	var response := IpcBridge.call_method("get_pitch_status")
	if response.has("error"):
		pitch_status_label.text = "PITCH: GREEN"
		return
	var result: Dictionary = response["result"]
	var current := str(result.get("current", "Green"))
	var pending = result.get("pending")
	if pending != null:
		var days := int(result.get("days_remaining", 0))
		pitch_status_label.text = "PITCH: %s → %s (%d day%s)" % [current.to_upper(), str(pending).to_upper(), days, "" if days == 1 else "s"]
		# A queued groundskeeping change is "coming soon", not a fact — gold
		# makes that transient state visible next to the steady green of a
		# settled pitch.
		pitch_status_label.add_theme_color_override("font_color", AppTheme.GOLD)
	else:
		pitch_status_label.text = "PITCH: %s" % current.to_upper()
		pitch_status_label.add_theme_color_override("font_color", AppTheme.HEADER_GREEN)


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
	var shell := _shell()
	if shell:
		shell.set_chrome_visible(false)
	# v4.26.0 fix: _show_stats_tab() was only ever called from a tab-button
	# press — never on initial load — so BattingCard and BowlingCard (both
	# default to visible=true in the scene) showed simultaneously, squeezed
	# side by side, until the user manually clicked a tab. That's also what
	# broke the bowling stamina bar's layout (it renders assuming the full
	# card width, not half of it).
	_show_stats_tab()
	prediction_label.text = ""
	predict_button.text = "WIN CHANCE?"
	shot_events = []
	bowling_events = []
	innings_overs = [[]]
	momentum_window = []
	_current_innings_runs = 0
	_current_over_ball_count = 0
	current_over_pills = []
	current_over_index = -1
	over_first_panel = {}
	over_chip_buttons = {}
	for child in overs_list.get_children():
		overs_list.remove_child(child)
		child.queue_free()
	for child in ball_tracker_list.get_children():
		ball_tracker_list.remove_child(child)
		child.queue_free()
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
	# v4.33.0: user feedback — 15 overs per SKIP press was far too much.
	# Skip one over (6 legal deliveries) at a time, matching the OVER
	# button so the manager always sees what happened before the next
	# decision point.
	return 6


func _on_highlights_pressed() -> void:
	highlights_card.visible = not highlights_card.visible
	if highlights_card.visible:
		_render_highlights()


func _render_highlights() -> void:
	for child in highlights_list.get_children():
		child.queue_free()
	var key_events := []
	for event in commentary_events:
		var kind: String = str(event.get("kind", "normal"))
		var result: String = str(event.get("result", ""))
		if kind == "wicket" or result in ["4", "6"] or kind == "milestone":
			key_events.append(event)
	if key_events.is_empty():
		var empty := Label.new()
		empty.text = "No highlights yet"
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		highlights_list.add_child(empty)
		return
	for event in key_events:
		var panel := PanelContainer.new()
		var box := StyleBoxFlat.new()
		box.bg_color = AppTheme.CARD
		box.set_corner_radius_all(4)
		box.set_border_width_all(1)
		box.content_margin_left = 8
		box.content_margin_right = 8
		box.content_margin_top = 5
		box.content_margin_bottom = 5
		var kind: String = str(event.get("kind", "normal"))
		var result: String = str(event.get("result", ""))
		if kind == "wicket":
			box.border_color = AppTheme.DANGER
		elif result in ["4", "6"]:
			box.border_color = AppTheme.GOLD
		else:
			box.border_color = AppTheme.ACCENT
		panel.add_theme_stylebox_override("panel", box)
		var label := Label.new()
		label.text = "Over %s: %s" % [str(event.get("over", "?")), str(event.get("commentary", ""))]
		label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		label.add_theme_font_size_override("font_size", 11)
		panel.add_child(label)
		highlights_list.add_child(panel)


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
## v4.26.0: the user was still confused about what this does even with a
## hover tooltip explaining it — a tooltip only reaches someone who
## hovers. The result now also lands directly on the button's own label
## (impossible to miss) in addition to the ScoreBar's prediction_label,
## and the button starts with a self-explanatory question rather than a
## bare "PREDICT" that gives no hint of what's being predicted.
func _on_predict_pressed() -> void:
	var response := IpcBridge.call_method("get_match_prediction")
	if response.has("error"):
		prediction_label.text = "Prediction unavailable: %s" % response["error"]
		predict_button.text = "WIN CHANCE?"
		return
	var probability := JsonFormat.value(response["result"].get("probability", 0))
	prediction_label.text = "Win probability: %s%%" % probability
	predict_button.text = "YOUR WIN %%: %s%%" % probability


## v4.13.0/v4.14.0 Match Day rebuild (Part 3): a quick-preset pick clears
## any custom drag-edited layout server-side (ipc_server.py's
## set_match_field) and reloads the preset's canonical positions, which
## _sync_tactics() then pushes into the ground view via field_layout.
func _on_field_preset_pressed(preset: String) -> void:
	var response := IpcBridge.call_method("set_match_field", {"preset": preset})
	if not response.has("error"):
		_sync_tactics(response["result"])


## The real field editor's write path — fires once per drag-release
## (ground_view.gd debounces to that, not per-frame), applying the new
## per-fielder layout via set_field_layout.
func _on_field_layout_changed(positions: Dictionary) -> void:
	var response := IpcBridge.call_method("set_field_layout", {"positions": positions})
	if response.has("error"):
		status_label.text = "Field layout failed: %s" % response["error"]


func _on_striker_aggro_changed(_value_changed: bool) -> void:
	var striker: Variant = _last_state.get("striker")
	if striker == null:
		return
	var value := int(striker_row_aggro_slider.value)
	var response := IpcBridge.call_method("set_match_aggression", {"batting": value, "player_id": int(striker.get("id", -1))})
	if not response.has("error"):
		_sync_tactics(response["result"])


func _on_non_striker_aggro_changed(_value_changed: bool) -> void:
	var non_striker: Variant = _last_state.get("non_striker")
	if non_striker == null:
		return
	var value := int(non_striker_row_aggro_slider.value)
	var response := IpcBridge.call_method("set_match_aggression", {"batting": value, "player_id": int(non_striker.get("id", -1))})
	if not response.has("error"):
		_sync_tactics(response["result"])


## "LINKED" toggle: when ON, both not-out batters' aggression are kept
## equal by the backend (modeling a partnership trying to bat at the same
## tempo). Toggling doesn't push a slider value itself — it just changes
## how future slider drags propagate server-side.
func _on_batting_aggro_link_toggled(pressed: bool) -> void:
	batting_aggression_linked = pressed
	link_button.text = "LINKED" if pressed else "UNLINKED"
	var response := IpcBridge.call_method("set_match_aggression", {"linked": pressed})
	if not response.has("error"):
		_sync_tactics(response["result"])


func _on_bowling_aggro_changed(_value_changed: bool) -> void:
	bowling_aggro = int(bowling_aggro_slider.value)
	var response := IpcBridge.call_method("set_match_aggression", {"bowling": bowling_aggro})
	if not response.has("error"):
		_sync_tactics(response["result"])


## v4.15.0 Match Day rebuild (Part 4): a real picker instead of blind
## cycling — opens BowlerPickerModal with the current eligible list and
## live figures, backed by _last_state (already refreshed after every
## ball, no extra IPC round-trip needed just to open the picker).
func _on_change_bowler_pressed() -> void:
	var innings_list: Array = _last_state.get("innings", [])
	var current_index: int = int(_last_state.get("current_innings_index", innings_list.size() - 1))
	var live: Dictionary = innings_list[current_index] if current_index < innings_list.size() else {}
	var current_bowler_id: int = int(_last_state.get("bowler", {}).get("id", -1)) if _last_state.get("bowler") else -1
	_bowler_picker_modal.show_for(_last_state.get("eligible_bowlers", []), live.get("bowling", []), current_bowler_id)


func _on_bowler_selected(player_id: int) -> void:
	var response := IpcBridge.call_method("set_match_bowler", {"player_id": player_id})
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
		status_label.text = "That bowler change wasn't legal — picker list may be stale."


## v4.21.0: the pitch-strip's click-to-aim target — "make my bowler bowl to
## the three stumps" — fires set_delivery_target immediately on click so the
## strip's own highlight is the confirmation; the target is one-shot server-
## side (consumed by the very next delivery), so no local re-arming needed.
func _on_delivery_target_chosen(line: String, length: String) -> void:
	var response := IpcBridge.call_method("set_delivery_target", {"line": line, "length": length})
	if response.has("error"):
		status_label.text = "Delivery target failed: %s" % response["error"]


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
	bowling_aggro = int(state.get("bowling_aggression", 5))
	bowling_aggro_label.text = "BOWL AGGRO: %d" % bowling_aggro
	# set_value_no_signal so pushing a server-confirmed value never
	# re-triggers drag_ended and loops back into another IPC call.
	bowling_aggro_slider.set_value_no_signal(bowling_aggro)
	batting_aggression_linked = bool(state.get("batting_aggression_linked", true))
	link_button.set_pressed_no_signal(batting_aggression_linked)
	link_button.text = "LINKED" if batting_aggression_linked else "UNLINKED"
	var striker: Variant = state.get("striker")
	var striker_aggro := int(striker.get("aggression", 5)) if striker != null else 5
	striker_row_aggro_slider.set_value_no_signal(striker_aggro)
	striker_row_aggro_value.text = str(striker_aggro)
	var non_striker: Variant = state.get("non_striker")
	var non_striker_aggro := int(non_striker.get("aggression", 5)) if non_striker != null else 5
	non_striker_row_aggro_slider.set_value_no_signal(non_striker_aggro)
	non_striker_row_aggro_value.text = str(non_striker_aggro)
	drs_button.text = "DRS: %d" % int(state.get("reviews_remaining", 0))
	# Keeps the field editor's dots in sync with the engine's actual layout
	# (an AI-controlled bowling team, or the user's own preset picks) —
	# harmless to update while the tab is hidden, and means it's always
	# current the moment the player switches to it.
	var layout: Dictionary = state.get("field_layout", {})
	if not layout.is_empty():
		field_ground_view.set_layout(layout)
	# v4.21.0: the pitch-strip targeting widget — cleared back to "no
	# target" once the engine consumes it (one-shot per delivery, see
	# ipc_server.py's set_delivery_target), and always shown the real
	# pitch-mark trail from this innings' actual deliveries.
	pitch_strip_view.bowling_events = bowling_events
	var line_target = state.get("line_target")
	var length_target = state.get("length_target")
	pitch_strip_view.set_target(str(line_target) if line_target != null else "", str(length_target) if length_target != null else "")
	var bowler_name: String = str(state.get("bowler", {}).get("name", "")) if state.get("bowler") else "—"
	bowler_card_name_label.text = bowler_name


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
	# Cricket Captain-style score bug with match status
	var team_name: String = str(live.get("team", "?"))
	var runs: int = int(live.get("runs", 0))
	var wickets: int = int(live.get("wickets", 0))
	var overs: String = str(live.get("overs", "0.0"))
	var total_overs: float = float(state.get("overs_limit", 50))
	var current_overs: float = float(overs)
	var progress: float = min(current_overs / total_overs, 1.0) if total_overs > 0 else 0.0
	# Match status with session info
	var match_status: String = str(state.get("status", ""))
	var session_info: String = str(state.get("session", ""))
	if session_info.is_empty():
		session_info = "Day %d" % (int(state.get("innings_index", 0)) / 2 + 1)
	score_label.text = "%s  %d/%d  (%s ov)" % [team_name, runs, wickets, overs]
	status_label.text = "%s — %s" % [match_status, session_info]
	rates_label.text = _rates_text(state, live)
	# Update overs progress bar if it exists
	var progress_bar: ProgressBar = $LiveMatchBox/Margin/MainCol/ScoreBar/Split/ScoreBox/ProgressBar
	if progress_bar:
		progress_bar.value = progress * 100
	_render_scorecard(batting_list, live.get("batting", []), true, state)
	_render_scorecard(bowling_list, live.get("bowling", []), false, state)
	# v4.22.0: a manager is only ever doing one job on a given delivery —
	# show the Bowler Card (target/aggro/CHANGE) while fielding, or the
	# Batsman Card (aggro) while batting, never both at once.
	var user_is_bowling: bool = bool(state.get("user_is_bowling", true))
	bowler_card.visible = user_is_bowling
	batsman_card.visible = not user_is_bowling
	_render_live_strip(state, live)
	_update_live_pitch(state, live)
	_render_stamina(state.get("bowler"))
	if summary_card.visible:
		_render_summary(state)
	_render_partnerships(live.get("partnerships", []))
	_sync_tactics(state)

	if match_completed:
		auto_play = false
		auto_timer.stop()
		auto_button.text = "AUTO: OFF"
		title_label.text = "MATCH DAY — %s" % state.get("result", "Match complete")
		# Reference (post-match scorecard screenshots): the match screen
		# stays exactly where the manager was looking (scorecard + Ball-
		# tracker), it does not jump to a separate summary view — only the
		# bottom-bar action changes from Next Ball to Continue.
		exit_button.text = "CONTINUE"
		next_ball_button.disabled = true
		over_button.disabled = true
		skip_button.disabled = true
		auto_button.disabled = true
		predict_button.disabled = true
		field_aggressive_button.disabled = true
		field_neutral_button.disabled = true
		field_defensive_button.disabled = true
		field_ground_view.interactive = false
		striker_row_aggro_slider.editable = false
		non_striker_row_aggro_slider.editable = false
		link_button.disabled = true
		bowling_aggro_slider.editable = false
		change_bowler_button.disabled = true
		drs_button.disabled = true
	else:
		title_label.text = "MATCH DAY — live"
		exit_button.text = "EXIT"
		next_ball_button.disabled = false
		over_button.disabled = false
		skip_button.disabled = false
		auto_button.disabled = false
		predict_button.disabled = false
		field_aggressive_button.disabled = false
		field_neutral_button.disabled = false
		field_defensive_button.disabled = false
		field_ground_view.interactive = true
		striker_row_aggro_slider.editable = true
		non_striker_row_aggro_slider.editable = true
		link_button.disabled = false
		bowling_aggro_slider.editable = true
		change_bowler_button.disabled = false
		drs_button.disabled = false


func _update_live_pitch(state: Dictionary, live: Dictionary) -> void:
	# Keep a prominent, non-interactive wagon-wheel/pitch view on screen. The
	# FIELD tab remains the editable field board; this is the broadcast camera
	# showing the latest shot and current field while the manager decides.
	var striker_name := str(state.get("striker", {}).get("name", "—")) if state.get("striker") else "—"
	var non_striker_name := str(state.get("non_striker", {}).get("name", "—")) if state.get("non_striker") else "—"
	var bowler_name := str(state.get("bowler", {}).get("name", "—")) if state.get("bowler") else "—"
	var shot: Dictionary = shot_events[-1] if not shot_events.is_empty() else {}
	if live_pitch_view.has_method("set_live_state"):
		live_pitch_view.set_live_state(striker_name, non_striker_name, bowler_name, shot)
	var layout: Dictionary = state.get("field_layout", {})
	if not layout.is_empty() and live_pitch_view.has_method("set_layout"):
		live_pitch_view.set_layout(layout)
	var user_is_bowling := bool(state.get("user_is_bowling", true))
	if user_is_bowling:
		perspective_label.text = "BOWLER PERSPECTIVE • set line & length on the pitch strip · field: %s" % str(state.get("field_preset", "Neutral"))
	else:
		perspective_label.text = "BATTER PERSPECTIVE • manage each batter’s aggression · %s on strike" % striker_name
	if commentary_events.is_empty():
		delivery_readout.text = "Waiting for the next ball…"
	else:
		var event: Dictionary = commentary_events[-1]
		var result := str(event.get("result", "•"))
		var commentary := str(event.get("commentary", "Delivery complete"))
		delivery_readout.text = "%s  •  %s" % [result, commentary]


## Current/required run rate, computed client-side from the raw ball counts
## get_match_state now exposes (v0.92.0) — balls_per_set/overs_limit are
## format-aware (The Hundred uses 5-ball sets), so this can't be guessed
## from the formatted "overs" display string alone.
func _rates_text(state: Dictionary, live: Dictionary) -> String:
	var legal_balls := int(live.get("legal_balls", 0))
	var balls_per_set := int(state.get("balls_per_set", 6))
	if legal_balls <= 0 or balls_per_set <= 0:
		return ""
	var runs := int(live.get("runs", 0))
	var overs_bowled: float = float(legal_balls) / float(balls_per_set)
	var crr: float = float(runs) / overs_bowled if overs_bowled > 0 else 0.0
	var text := "CRR %.2f" % crr
	var target = live.get("target")
	if target != null and str(state.get("format", "")) != "Test":
		var balls_total: int = int(state.get("overs_limit", 0)) * balls_per_set
		var balls_remaining: int = max(0, balls_total - legal_balls)
		var runs_needed: int = max(0, int(target) - runs)
		if balls_remaining > 0:
			var rrr: float = float(runs_needed) * balls_per_set / float(balls_remaining)
			text += "  •  RRR %.2f" % rrr
	return text


## Reference (Cricket Captain) layout: current batsmen and bowler figures
## visible at all times, not gated behind a tab — mirrors the always-on
## strip under the scoreboard in the reference screenshots.
func _render_live_strip(state: Dictionary, live: Dictionary) -> void:
	var batting_rows: Array = live.get("batting", [])
	var bowling_rows: Array = live.get("bowling", [])
	_set_batter_strip(striker_name_label, striker_figures_label, state.get("striker"), batting_rows)
	_set_batter_strip(non_striker_name_label, non_striker_figures_label, state.get("non_striker"), batting_rows)
	_set_bowler_strip(state.get("bowler"), bowling_rows)
	_update_bowler_card_figures(state.get("bowler"), bowling_rows)
	_set_batter_strip(striker_row_name, striker_row_figures, state.get("striker"), batting_rows)
	_set_batter_strip(non_striker_row_name, non_striker_row_figures, state.get("non_striker"), batting_rows)
	_set_batter_subtitle(_striker_subtitle, state.get("striker"))
	_set_batter_subtitle(_non_striker_subtitle, state.get("non_striker"))
	_update_mini_wagon(_striker_wagon, state.get("striker"))
	_update_mini_wagon(_non_striker_wagon, state.get("non_striker"))


func _set_batter_subtitle(label: Label, player) -> void:
	if label == null:
		return
	if player == null:
		label.text = "AVG —  SR —"
		return
	var avg := float(player.get("career_batting_average", 0.0))
	var sr := float(player.get("career_strike_rate", 0.0))
	if avg <= 0.0 and sr <= 0.0:
		label.text = "AVG —  SR —"
	else:
		label.text = "AVG %.2f  SR %.1f" % [avg, sr]


func _update_mini_wagon(canvas: MatchStatsCanvas, player) -> void:
	if canvas == null:
		return
	if player == null:
		canvas.shot_events = []
	else:
		var player_id := int(player.get("id", -1))
		canvas.shot_events = shot_events.filter(func(e): return int(e.get("player_id", -1)) == player_id)
	canvas.queue_redraw()


func _set_batter_strip(name_label: Label, figures_label: Label, player, batting_rows: Array) -> void:
	if player == null:
		name_label.text = "—"
		figures_label.text = ""
		return
	name_label.text = str(player.get("name", "?"))
	var player_id := int(player.get("id", -1))
	for row in batting_rows:
		if int(row.get("player_id", -1)) == player_id:
			var sr: float = row.get("strike_rate", 0.0)
			figures_label.text = "%d (%d) • SR %.1f" % [int(row.get("runs", 0)), int(row.get("balls", 0)), sr]
			return
	figures_label.text = "0 (0)"


func _set_bowler_strip(player, bowling_rows: Array) -> void:
	if player == null:
		strip_bowler_name_label.text = "—"
		strip_bowler_figures_label.text = ""
		return
	strip_bowler_name_label.text = str(player.get("name", "?"))
	var player_id := int(player.get("id", -1))
	for row in bowling_rows:
		if int(row.get("player_id", -1)) == player_id:
			strip_bowler_figures_label.text = "%s-%d-%d-%d (O-M-R-W)" % [
				JsonFormat.value(row.get("overs", "0.0")), int(row.get("maidens", 0)),
				int(row.get("runs", 0)), int(row.get("wickets", 0))]
			return
	strip_bowler_figures_label.text = "0.0-0-0-0 (O-M-R-W)"


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
## v4.52.0: once the match is completed, also shows the final result banner
## and Man of the Match (reference: the post-match scorecard screenshot's
## "Match Drawn" / "Man of the match: B McMillan" footer) — both come
## straight from ipc_server.py's _match_state (result/man_of_the_match),
## no client-side computation.
func _render_summary(state: Dictionary) -> void:
	for child in summary_list.get_children():
		summary_list.remove_child(child)
		child.queue_free()
	var innings_list: Array = state.get("innings", [])
	if innings_list.is_empty():
		var empty := Label.new()
		empty.text = "No innings played yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		summary_list.add_child(empty)
		return
	if bool(state.get("completed", false)):
		var result_label := Label.new()
		result_label.text = str(state.get("result", "Match complete"))
		result_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		result_label.add_theme_font_size_override("font_size", 16)
		result_label.add_theme_color_override("font_color", AppTheme.GOLD)
		summary_list.add_child(result_label)
		var motm: Variant = state.get("man_of_the_match")
		if motm != null:
			var motm_label := Label.new()
			motm_label.text = "Man of the match: %s" % str(motm.get("name", "?"))
			motm_label.add_theme_font_size_override("font_size", 13)
			motm_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
			summary_list.add_child(motm_label)
		summary_list.add_child(HSeparator.new())
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
	# NAME widened from 140 (v4.22.0 and earlier) to 185 — the scorecard's
	# only visible card now gets most of the right column's width to
	# itself (v4.20.0's restructure), and a dismissal suffix like
	# "(lbw b Haris Afridi)" needs the room; clip_text still guarantees a
	# fixed column width regardless of how long any name+dismissal gets.
	var widths: Array = [185, 40, 40, 36, 36, 50] if is_batting else [185, 50, 50, 40, 50]
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
			# v4.23.0: a long dismissal suffix ("(lbw b Haris Afridi)") made
			# the NAME label's natural text size exceed its
			# custom_minimum_size — Godot's Label reports max(minimum,
			# natural-text-size) as its actual layout size when clip_text is
			# off, so long names silently widened that one row and threw the
			# R/B/4s/6s/SR columns out of alignment with every other row.
			# clip_text keeps every column's width fixed regardless of
			# content length, so rows always line up.
			label.clip_text = true
			label.add_theme_font_size_override("font_size", 12)
			label.add_theme_color_override("font_color", AppTheme.GOLD if highlight else AppTheme.TEXT_PRIMARY)
			row.add_child(label)
		list.add_child(row)


func _dismissal_suffix(row_data: Dictionary) -> String:
	var dismissal: String = str(row_data.get("dismissal", ""))
	if dismissal == "" or dismissal == "not out" or dismissal == "did not bat":
		return ""
	return " (%s)" % dismissal


## Short "AW: No run." style feed (reference: the bowler/batter concept
## screenshots' Ball-tracker panel) — a coloured outcome dot plus a plain-
## English description per legal ball, newest at the top, capped to the
## last 6 so it never grows unbounded across a long innings.
const BALL_TRACKER_CAP := 6


func _initials(name: String) -> String:
	var parts: PackedStringArray = name.split(" ", false)
	if parts.size() >= 2:
		return "%s%s" % [parts[0].substr(0, 1), parts[-1].substr(0, 1)]
	elif parts.size() == 1 and parts[0].length() > 0:
		return parts[0].substr(0, min(2, parts[0].length()))
	return "?"


func _ball_description(event: Dictionary) -> String:
	if event.get("wicket") != null:
		return "OUT!"
	match int(event.get("runs", 0)):
		0: return "No run."
		1: return "One run."
		2: return "Two runs."
		3: return "Three runs."
		4: return "FOUR!"
		6: return "SIX!"
		_: return "%d runs." % int(event.get("runs", 0))


func _update_ball_tracker(event: Dictionary) -> void:
	if not bool(event.get("legal", true)):
		return
	var batter: Variant = event.get("batter")
	var initials: String = _initials(str(batter.get("name", "?"))) if batter else "??"
	var runs := int(event.get("runs", 0))
	var wicket = event.get("wicket")
	var colour: Color = AppTheme.DANGER if wicket != null else \
		(AppTheme.GOLD if runs in [4, 6] else (AppTheme.HEADER_GREEN if runs > 0 else AppTheme.TEXT_MUTED))
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	var name_label := Label.new()
	name_label.text = "%s:" % initials
	name_label.custom_minimum_size = Vector2(28, 0)
	name_label.add_theme_font_size_override("font_size", 10)
	name_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	row.add_child(name_label)
	var desc_label := Label.new()
	desc_label.text = _ball_description(event)
	desc_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	desc_label.add_theme_font_size_override("font_size", 10)
	desc_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	row.add_child(desc_label)
	var dot := Label.new()
	dot.text = "●"
	dot.add_theme_font_size_override("font_size", 10)
	dot.add_theme_color_override("font_color", colour)
	row.add_child(dot)
	var run_label := Label.new()
	run_label.text = ("W" if wicket != null else (str(runs) if runs > 0 else "."))
	run_label.custom_minimum_size = Vector2(14, 0)
	run_label.add_theme_font_size_override("font_size", 10)
	run_label.add_theme_color_override("font_color", colour)
	row.add_child(run_label)
	ball_tracker_list.add_child(row)
	ball_tracker_list.move_child(row, 0)
	while ball_tracker_list.get_child_count() > BALL_TRACKER_CAP:
		var last := ball_tracker_list.get_child(ball_tracker_list.get_child_count() - 1)
		ball_tracker_list.remove_child(last)
		last.queue_free()


## Mirrors ui/match_view.py's colour-coded commentary log: wickets in red,
## boundaries in gold, everything else muted, most recent entry at the
## bottom with the view auto-scrolled to follow it.
func _append_commentary(event: Dictionary) -> void:
	commentary_events.append(event)
	_update_ball_tracker(event)
	# Play audio for key events
	var event_kind: String = str(event.get("kind", "normal"))
	var event_result: String = str(event.get("result", ""))
	if event_kind == "wicket" and _audio:
		_audio.play_wicket()
	elif event_result == "6" and _audio:
		_audio.play_six()
	elif event_result == "4" and _audio:
		_audio.play_boundary()
	elif event_kind == "milestone" and _audio:
		_audio.play_applause()
	elif _audio:
		_audio.play_run()
	var panel := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.CARD
	box.set_corner_radius_all(6)
	box.set_border_width_all(1)
	box.border_color = AppTheme.BORDER
	box.content_margin_left = 10
	box.content_margin_right = 10
	box.content_margin_top = 6
	box.content_margin_bottom = 6
	panel.add_theme_stylebox_override("panel", box)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 2)
	# Header with over number and players
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 8)
	var over_label := Label.new()
	over_label.text = "Over %s" % str(event.get("over", "?"))
	over_label.add_theme_font_size_override("font_size", 10)
	over_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	header.add_child(over_label)
	var players_label := Label.new()
	players_label.text = "%s → %s" % [str(event.get("bowler", {}).get("name", "?")) if event.get("bowler") else "?",
		str(event.get("batter", {}).get("name", "?")) if event.get("batter") else "?"]
	players_label.add_theme_font_size_override("font_size", 10)
	players_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	header.add_child(players_label)
	vbox.add_child(header)
	# Commentary text
	var commentary_label := Label.new()
	commentary_label.text = str(event.get("commentary", ""))
	commentary_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	var kind: String = str(event.get("kind", "normal"))
	if kind == "wicket":
		commentary_label.add_theme_color_override("font_color", AppTheme.DANGER)
		box.border_color = AppTheme.DANGER
		box.border_width_left = 3
	elif event.get("result", "") in ["4", "6"]:
		commentary_label.add_theme_color_override("font_color", AppTheme.GOLD)
		box.border_color = AppTheme.GOLD
		box.border_width_left = 3
	elif kind == "milestone":
		commentary_label.add_theme_color_override("font_color", AppTheme.ACCENT)
		box.border_color = AppTheme.ACCENT
		box.border_width_left = 3
	else:
		commentary_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	commentary_label.add_theme_font_size_override("font_size", 12)
	vbox.add_child(commentary_label)
	# Add result badge if applicable
	var result: String = str(event.get("result", ""))
	if result in ["0", "1", "2", "3", "4", "6"]:
		var badge := Label.new()
		badge.text = result
		badge.add_theme_font_size_override("font_size", 14)
		badge.add_theme_color_override("font_color", AppTheme.GOLD if result in ["4", "6"] else AppTheme.TEXT_SECONDARY)
		vbox.add_child(badge)
	panel.add_child(vbox)
	# v4.26.0: the user asked to "go back as far as we want" — the old
	# 50-entry cap discarded early-innings history. A full Test innings
	# tops out well under 1000 balls, so this is effectively unlimited
	# without letting a pathological run grow the node tree forever.
	var was_at_bottom := commentary_scroll.get_v_scroll_bar().max_value <= 0 or \
		commentary_scroll.scroll_vertical >= commentary_scroll.get_v_scroll_bar().max_value - 40
	commentary_list.add_child(panel)
	var children := commentary_list.get_children()
	if children.size() > 1000:
		var evicted: Control = children[0]
		commentary_list.remove_child(evicted)
		# An evicted panel may still be referenced as some over's "first
		# ball" for the JUMP TO OVER chips — that over's chip and dict
		# entries must go with it, or a later click hits a freed instance.
		for over_index in over_first_panel.keys():
			if over_first_panel[over_index] == evicted:
				over_first_panel.erase(over_index)
				var chip: Button = over_chip_buttons.get(over_index)
				if chip:
					overs_list.remove_child(chip)
					chip.queue_free()
				over_chip_buttons.erase(over_index)
				break
		evicted.queue_free()
	_update_current_over_strip(event, panel)
	# Only follow new balls if the user was already at (or near) the
	# bottom — otherwise a manual scroll back through history keeps
	# getting yanked back down every single ball.
	if was_at_bottom:
		await get_tree().process_frame
		commentary_scroll.scroll_vertical = int(commentary_scroll.get_v_scroll_bar().max_value)


## Scrolls the commentary history to the clicked over's first ball.
## commentary_list (a VBoxContainer) is the ScrollContainer's sole direct
## child, so a panel's local Y position IS its scroll offset — simpler
## and more reliably immediate than ensure_control_visible, which needs
## the container's cached content size to already be fresh.
func _on_over_chip_pressed(over_index: int) -> void:
	var panel: Control = over_first_panel.get(over_index)
	if panel:
		commentary_scroll.scroll_vertical = int(panel.position.y)


## Always-visible "how is this over going" strip (v4.26.0) — the user
## wanted space to see every ball of the current over at a glance, not
## just the most recent one buried in the scrolling history below.
## v4.27.0: also registers a "JUMP TO OVER" chip per over (this ball's
## panel is remembered as that over's first entry) — click one to scroll
## the commentary history straight to it, per the user's explicit ask to
## "click on an over to check how it went" instead of manually scrolling.
func _update_current_over_strip(event: Dictionary, panel: Control) -> void:
	var over_str := str(event.get("over", "0"))
	var over_index := int(over_str.split(".")[0])
	if not over_first_panel.has(over_index):
		over_first_panel[over_index] = panel
		var chip := Button.new()
		chip.text = str(over_index + 1)
		chip.custom_minimum_size = Vector2(32, 24)
		chip.add_theme_font_size_override("font_size", 11)
		chip.pressed.connect(_on_over_chip_pressed.bind(over_index))
		overs_list.add_child(chip)
		over_chip_buttons[over_index] = chip
	if over_index != current_over_index:
		current_over_pills = []
		current_over_index = over_index
	var wicket = event.get("wicket")
	var pill_text: String = "W" if wicket != null else str(event.get("result", "."))
	current_over_pills.append(pill_text)
	current_over_header.text = "THIS OVER — %d" % (over_index + 1)
	for child in current_over_strip.get_children():
		current_over_strip.remove_child(child)
		child.queue_free()
	for pill in current_over_pills:
		var badge := PanelContainer.new()
		var box := StyleBoxFlat.new()
		box.set_corner_radius_all(12)
		box.content_margin_left = 8
		box.content_margin_right = 8
		box.content_margin_top = 3
		box.content_margin_bottom = 3
		var label := Label.new()
		label.text = str(pill)
		label.add_theme_font_size_override("font_size", 12)
		if pill == "W":
			box.bg_color = AppTheme.DANGER
			label.add_theme_color_override("font_color", AppTheme.CARD)
		elif pill in ["4", "6"]:
			box.bg_color = AppTheme.GOLD
			label.add_theme_color_override("font_color", AppTheme.CARD)
		elif pill in ["Wd", "Nb"]:
			box.bg_color = AppTheme.BORDER
			label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
		else:
			box.bg_color = AppTheme.SURFACE
			label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
		badge.add_theme_stylebox_override("panel", box)
		badge.add_child(label)
		current_over_strip.add_child(badge)
