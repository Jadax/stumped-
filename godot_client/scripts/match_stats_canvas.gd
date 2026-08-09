class_name MatchStatsCanvas
extends Control
## Draws match_screen.gd's Stats Hub charts — wagon wheel, pitch/bowling
## map, worm, momentum, and Manhattan — ports of the pygame widgets in
## ui/widgets/shot_map.py and ui/widgets/bowling_map.py, plus the inline
## chart drawing in ui/match_view.py's Stats Hub (worm/manhattan have no
## dedicated pygame widget class; both clients compute them from the
## ball-by-ball stream rather than a stored per-over field, since
## match_engine.py doesn't track one).
##
## v4.61.0: Momentum is the exception — it USED to be reconstructed here
## client-side (a trailing 24-ball runs-minus-wickets*8 window, a real but
## independently-invented formula), duplicating the backend's own
## Innings.momentum (v4.60.0, already used by the live ScoreBar label).
## Two different things both called "momentum" was a real, confusing
## reconciliation gap — this now plots match_engine.py's real
## InningsState.momentum_history directly instead of recomputing anything.

var mode: String = "shot_map"
var shot_events: Array = []
var bowling_events: Array = []
var innings_overs: Array = []
var momentum_history: Array = []
var field_positions: Array = []  # Player positions on field

## When true, _draw_shot_map skips the fielding-position dots and legend —
## for tiny inline uses (e.g. a per-batter mini wagon wheel next to their
## name in the Match Day live strip) where that text would just overflow a
## ~56px canvas. The Stats Hub's full-size tab keeps compact = false.
var compact: bool = false


func set_mode(new_mode: String) -> void:
	mode = new_mode
	queue_redraw()


func set_field_positions(positions: Array) -> void:
	field_positions = positions
	queue_redraw()


func _draw() -> void:
	match mode:
		"shot_map":
			_draw_shot_map(shot_events, true)
		"boundary_map":
			_draw_shot_map(shot_events.filter(func(e): return int(e.get("runs", 0)) in [4, 6]), false)
		"pitch_map":
			_draw_pitch_map()
		"worm":
			_draw_worm()
		"manhattan":
			_draw_manhattan()
		"momentum":
			_draw_momentum()
		"field_positions":
			_draw_field_positions()


func _outcome_colour(runs: int, wicket: bool) -> Color:
	if wicket:
		return AppTheme.DANGER
	if runs >= 4:
		return AppTheme.GOLD
	if runs > 0:
		return AppTheme.HEADER_GREEN
	return AppTheme.TEXT_MUTED


## Ports ui/widgets/shot_map.py's ShotMap: a green field circle, an inner
## 30-yard-circle ring, a pitch strip at the centre, and one line+dot per
## shot event from centre out to (angle, distance) — angle in radians,
## distance a fixed 0-1 lookup by runs scored (set by the engine itself).
func _draw_shot_map(events: Array, show_field: bool) -> void:
	var centre := size / 2.0
	var margin: float = 6.0 if compact else 18.0
	var radius: float = min(size.x, size.y) / 2.0 - margin
	if radius <= 0:
		return
	# Draw field background
	draw_circle(centre, radius, Color(0.15, 0.35, 0.2, 1.0), true, -1.0, true)
	# Draw 30-yard circle
	draw_arc(centre, radius * 0.63, 0, TAU, 48, AppTheme.BORDER, 1.5, true)
	# Draw pitch strip — a fixed 24x76 reads fine on a full-size (~250px)
	# canvas but swamps a compact ~50px inline one, so scale it to the
	# field radius instead of using absolute pixels there.
	if compact:
		draw_rect(Rect2(centre - Vector2(radius * 0.14, radius * 0.42), Vector2(radius * 0.28, radius * 0.84)), AppTheme.TEXT_MUTED, false, 1.0)
	else:
		draw_rect(Rect2(centre - Vector2(12, 38), Vector2(24, 76)), AppTheme.TEXT_MUTED, false, 1.5)
	# Draw fielding positions
	if show_field and not compact:
		var positions := {"Long On": Vector2(0, -1), "Long Off": Vector2(0.5, -0.87),
			"Cover": Vector2(0.87, -0.5), "Point": Vector2(1, 0), "Third Man": Vector2(0.87, 0.5),
			"Fine Leg": Vector2(-0.87, 0.5), "Square Leg": Vector2(-1, 0), "Mid Wicket": Vector2(-0.87, -0.5),
			"Long Leg": Vector2(-0.5, -0.87)}
		for label in positions:
			var point: Vector2 = centre + positions[label] * radius * 0.92
			draw_circle(point, 3.0, AppTheme.TEXT_SECONDARY, true, -1.0, true)
	# Draw shot lines with colour coding
	for event in events:
		var angle: float = float(event.get("angle", 0.0))
		var distance: float = float(event.get("distance", 0.2))
		var runs := int(event.get("runs", 0))
		var wicket: bool = bool(event.get("wicket", false))
		var end := centre + Vector2(cos(angle), sin(angle)) * radius * distance
		var colour := _outcome_colour(runs, wicket)
		# Draw shot line with varying thickness based on runs
		var line_width: float = 1.5
		if runs >= 6:
			line_width = 3.0
		elif runs >= 4:
			line_width = 2.5
		elif runs > 0:
			line_width = 2.0
		draw_line(centre, end, colour, line_width, true)
		# Draw endpoint dot
		var dot_size: float = 4.0
		if runs >= 6:
			dot_size = 6.0
		elif runs >= 4:
			dot_size = 5.0
		if compact:
			dot_size *= 0.6
		draw_circle(end, dot_size, colour, true, -1.0, true)
	# Legend/empty-state text would overflow a compact inline canvas — the
	# caller (e.g. player_profile_modal.gd/match_screen.gd) already labels
	# the widget with a caption, so skip both here.
	if compact:
		return
	# Draw legend
	var legend_x: float = 10.0
	var legend_y: float = size.y - 60.0
	var legend_items := [
		["1 Run", AppTheme.HEADER_GREEN],
		["2-3 Runs", AppTheme.HEADER_GREEN],
		["4 Runs", AppTheme.GOLD],
		["6 Runs", AppTheme.ACCENT],
		["Wicket", AppTheme.DANGER],
	]
	for item in legend_items:
		draw_circle(Vector2(legend_x + 5, legend_y + 5), 4.0, item[1], true, -1.0, true)
		var font := ThemeDB.fallback_font
		draw_string(font, Vector2(legend_x + 14, legend_y + 9), item[0], HORIZONTAL_ALIGNMENT_LEFT, -1, 10, AppTheme.TEXT_PRIMARY)
		legend_y += 14.0
	if events.is_empty():
		_draw_centered_label("No shots recorded yet.")


## Ports ui/widgets/bowling_map.py's BowlingMap: a pitch-coloured rect
## with SHORT/GOOD/FULL/YORKER length guides and off/leg channel guides,
## one dot per delivery at its already-normalised (x, y).
func _draw_pitch_map() -> void:
	# Draw pitch background
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.55, 0.47, 0.3, 1.0))
	# Draw length zones
	var zones := [
		["YORKER", 0.88, AppTheme.DANGER],
		["FULL", 0.72, AppTheme.GOLD],
		["GOOD", 0.5, AppTheme.HEADER_GREEN],
		["SHORT", 0.25, AppTheme.ACCENT],
	]
	for zone in zones:
		var y: float = size.y * zone[1]
		draw_line(Vector2(0, y), Vector2(size.x, y), zone[2], 1.5, true)
		var font := ThemeDB.fallback_font
		draw_string(font, Vector2(5, y - 3), zone[0], HORIZONTAL_ALIGNMENT_LEFT, -1, 9, zone[2])
	# Draw off/leg channels
	draw_line(Vector2(size.x / 3.0, 0), Vector2(size.x / 3.0, size.y), AppTheme.BORDER, 1.0, true)
	draw_line(Vector2(size.x * 2.0 / 3.0, 0), Vector2(size.x * 2.0 / 3.0, size.y), AppTheme.BORDER, 1.0, true)
	# Draw channel labels
	var font := ThemeDB.fallback_font
	draw_string(font, Vector2(5, size.y / 2.0), "LEG", HORIZONTAL_ALIGNMENT_LEFT, -1, 10, AppTheme.TEXT_SECONDARY)
	draw_string(font, Vector2(size.x / 2.0 - 8, size.y / 2.0), "OFF", HORIZONTAL_ALIGNMENT_LEFT, -1, 10, AppTheme.TEXT_SECONDARY)
	# Draw delivery dots
	for event in bowling_events:
		var point := Vector2(float(event.get("x", 0.5)) * size.x, float(event.get("y", 0.5)) * size.y)
		var wicket: bool = bool(event.get("wicket", false))
		var runs := int(event.get("runs", 0))
		var dot_size: float = 10.0 if wicket else 6.0
		draw_circle(point, dot_size, _outcome_colour(runs, wicket), true, -1.0, true)
	# Draw legend
	var legend_x: float = size.x - 80.0
	var legend_y: float = 10.0
	var legend_items := [
		["Wicket", AppTheme.DANGER],
		["Boundary", AppTheme.GOLD],
		["Single", AppTheme.HEADER_GREEN],
		["Dot", AppTheme.TEXT_MUTED],
	]
	for item in legend_items:
		draw_circle(Vector2(legend_x + 5, legend_y + 5), 4.0, item[1], true, -1.0, true)
		draw_string(font, Vector2(legend_x + 14, legend_y + 9), item[0], HORIZONTAL_ALIGNMENT_LEFT, -1, 10, AppTheme.TEXT_PRIMARY)
		legend_y += 14.0
	if bowling_events.is_empty():
		_draw_centered_label("No deliveries recorded yet.")


## Cumulative-runs-per-over line for every innings played so far — real
## data throughout, since Godot already receives every ball via
## simulate_balls (pygame's equivalent Worm tab fakes the second line).
func _draw_worm() -> void:
	var margin := 24.0
	var plot := Rect2(margin, margin, size.x - margin * 2, size.y - margin * 2)
	draw_rect(plot, AppTheme.SURFACE)
	if innings_overs.is_empty() or innings_overs.all(func(o): return o.is_empty()):
		_draw_centered_label("No overs completed yet.")
		return
	var max_runs: float = 1.0
	var max_overs: int = 1
	for overs_array in innings_overs:
		if not overs_array.is_empty():
			max_runs = max(max_runs, float(overs_array[-1]))
			max_overs = max(max_overs, overs_array.size())
	var colours := [AppTheme.HEADER_GREEN, AppTheme.GOLD]
	for i in range(innings_overs.size()):
		var overs_array: Array = innings_overs[i]
		if overs_array.is_empty():
			continue
		var points := PackedVector2Array()
		points.append(Vector2(plot.position.x, plot.position.y + plot.size.y))
		for over_index in range(overs_array.size()):
			var x: float = plot.position.x + plot.size.x * (float(over_index + 1) / max_overs)
			var y: float = plot.position.y + plot.size.y * (1.0 - float(overs_array[over_index]) / max_runs)
			points.append(Vector2(x, y))
		var colour: Color = colours[i % colours.size()]
		if points.size() > 1:
			draw_polyline(points, colour, 2.0, true)
		draw_circle(points[-1], 3.5, colour, true, -1.0, true)


## Runs-per-over bar chart for the current (in-progress) innings.
func _draw_manhattan() -> void:
	var margin := 24.0
	var plot := Rect2(margin, margin, size.x - margin * 2, size.y - margin * 2)
	draw_rect(plot, AppTheme.SURFACE)
	if innings_overs.is_empty() or innings_overs[-1].is_empty():
		_draw_centered_label("No overs completed yet.")
		return
	var cumulative: Array = innings_overs[-1]
	var per_over: Array = []
	var previous := 0
	for value in cumulative:
		per_over.append(int(value) - previous)
		previous = int(value)
	var max_value: float = 1.0
	for value in per_over:
		max_value = max(max_value, float(value))
	var bar_width: float = plot.size.x / max(1, per_over.size())
	for i in range(per_over.size()):
		var height: float = plot.size.y * (float(per_over[i]) / max_value)
		var bar_rect := Rect2(plot.position.x + i * bar_width + 2, plot.position.y + plot.size.y - height,
			bar_width - 4, height)
		draw_rect(bar_rect, AppTheme.attribute_colour(clampf(float(per_over[i]) * 8, 0, 100)))


## The real backend momentum trail (match_engine.py's InningsState.
## momentum, -100..100, positive favours the batting side) plotted as a
## line above/below a zero baseline — the same value the live ScoreBar
## label already shows, just over time instead of as a single number.
func _draw_momentum() -> void:
	var margin := 24.0
	var plot := Rect2(margin, margin, size.x - margin * 2, size.y - margin * 2)
	draw_rect(plot, AppTheme.SURFACE)
	if momentum_history.size() < 2:
		_draw_centered_label("Not enough deliveries yet.")
		return
	var zero_y: float = plot.position.y + plot.size.y / 2.0
	draw_line(Vector2(plot.position.x, zero_y), Vector2(plot.position.x + plot.size.x, zero_y), AppTheme.BORDER, 1.0, true)
	var points := PackedVector2Array()
	for i in range(momentum_history.size()):
		var x: float = plot.position.x + plot.size.x * (float(i) / max(1, momentum_history.size() - 1))
		var y: float = zero_y - (float(momentum_history[i]) / 100.0) * (plot.size.y / 2.0)
		points.append(Vector2(x, y))
	if points.size() > 1:
		draw_polyline(points, AppTheme.ACCENT, 2.0, true)


func _draw_centered_label(_text: String) -> void:
	var font := ThemeDB.fallback_font
	var text_size := font.get_string_size(_text, HORIZONTAL_ALIGNMENT_CENTER, -1, 13)
	draw_string(font, size / 2.0 - text_size / 2.0, _text, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, AppTheme.TEXT_MUTED)


func _draw_field_positions() -> void:
	var centre := size / 2.0
	var radius: float = min(size.x, size.y) / 2.0 - 18.0
	if radius <= 0:
		return
	# Draw field
	draw_circle(centre, radius, Color(0.15, 0.35, 0.2, 1.0), true, -1.0, true)
	draw_arc(centre, radius * 0.63, 0, TAU, 48, AppTheme.BORDER, 1.5, true)
	# Draw pitch
	draw_rect(Rect2(centre - Vector2(12, 38), Vector2(24, 76)), AppTheme.TEXT_MUTED, false, 1.5)
	# Draw fielding positions
	var positions := [
		{"name": "WK", "pos": Vector2(0, 0.15)},  # Wicketkeeper
		{"name": "SL", "pos": Vector2(-0.15, 0.1)},  # Slip
		{"name": "GL", "pos": Vector2(0.15, 0.1)},  # Gully
		{"name": "PT", "pos": Vector2(0.3, 0)},  # Point
		{"name": "CO", "pos": Vector2(0.4, -0.2)},  # Cover
		{"name": "MO", "pos": Vector2(0.3, -0.4)},  # Mid Off
		{"name": "LO", "pos": Vector2(0.2, -0.6)},  # Long Off
		{"name": "LN", "pos": Vector2(-0.2, -0.6)},  # Long On
		{"name": "MI", "pos": Vector2(-0.3, -0.4)},  # Mid On
		{"name": "MW", "pos": Vector2(-0.4, -0.2)},  # Mid Wicket
		{"name": "SL2", "pos": Vector2(-0.3, 0)},  # Square Leg
		{"name": "FL", "pos": Vector2(-0.15, 0.3)},  # Fine Leg
	]
	for pos in positions:
		var point: Vector2 = centre + pos["pos"] * radius
		draw_circle(point, 8.0, AppTheme.CARD, true, -1.0, true)
		draw_circle(point, 8.0, AppTheme.BORDER, false, 1.5, true)
		var font := ThemeDB.fallback_font
		var text_size := font.get_string_size(pos["name"], HORIZONTAL_ALIGNMENT_CENTER, -1, 10)
		draw_string(font, point - text_size / 2.0, pos["name"], HORIZONTAL_ALIGNMENT_LEFT, -1, 10, AppTheme.TEXT_PRIMARY)
	# Draw player positions if available
	for player in field_positions:
		var px: float = float(player.get("x", 0.5))
		var py: float = float(player.get("y", 0.5))
		var player_pos := Vector2(centre.x + (px - 0.5) * radius * 2, centre.y + (py - 0.5) * radius * 2)
		draw_circle(player_pos, 6.0, AppTheme.GOLD, true, -1.0, true)
