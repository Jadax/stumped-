class_name MatchStatsCanvas
extends Control
## Draws match_screen.gd's Stats Hub charts — wagon wheel, pitch/bowling
## map, worm, momentum, and Manhattan — ports of the pygame widgets in
## ui/widgets/shot_map.py and ui/widgets/bowling_map.py, plus the inline
## chart drawing in ui/match_view.py's Stats Hub (worm/momentum/manhattan
## have no dedicated pygame widget class; both clients compute them from
## the ball-by-ball stream rather than a stored per-over field, since
## match_engine.py doesn't track one).

var mode: String = "shot_map"
var shot_events: Array = []
var bowling_events: Array = []
var innings_overs: Array = []
var momentum_window: Array = []
var field_positions: Array = []  # Player positions on field


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
	var radius: float = min(size.x, size.y) / 2.0 - 18.0
	if radius <= 0:
		return
	draw_circle(centre, radius, Color(0.15, 0.35, 0.2, 1.0))
	draw_arc(centre, radius * 0.63, 0, TAU, 48, AppTheme.BORDER, 1.5)
	draw_rect(Rect2(centre - Vector2(12, 38), Vector2(24, 76)), AppTheme.TEXT_MUTED, false, 1.5)
	if show_field:
		var positions := {"Long On": Vector2(0, -1), "Long Off": Vector2(0.5, -0.87),
			"Cover": Vector2(0.87, -0.5), "Point": Vector2(1, 0), "Third Man": Vector2(0.87, 0.5),
			"Fine Leg": Vector2(-0.87, 0.5), "Square Leg": Vector2(-1, 0), "Mid Wicket": Vector2(-0.87, -0.5),
			"Long Leg": Vector2(-0.5, -0.87)}
		for label in positions:
			var point: Vector2 = centre + positions[label] * radius * 0.92
			draw_circle(point, 3.0, AppTheme.TEXT_SECONDARY)
	for event in events:
		var angle: float = float(event.get("angle", 0.0))
		var distance: float = float(event.get("distance", 0.2))
		var runs := int(event.get("runs", 0))
		var wicket: bool = bool(event.get("wicket", false))
		var end := centre + Vector2(cos(angle), sin(angle)) * radius * distance
		var colour := _outcome_colour(runs, wicket)
		draw_line(centre, end, colour, 1.5)
		draw_circle(end, 4.0, colour)
	if events.is_empty():
		_draw_centered_label("No shots recorded yet.")


## Ports ui/widgets/bowling_map.py's BowlingMap: a pitch-coloured rect
## with SHORT/GOOD/FULL/YORKER length guides and off/leg channel guides,
## one dot per delivery at its already-normalised (x, y).
func _draw_pitch_map() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.55, 0.47, 0.3, 1.0))
	for fraction in [0.25, 0.5, 0.72, 0.88]:
		var y: float = size.y * fraction
		draw_line(Vector2(0, y), Vector2(size.x, y), AppTheme.BORDER, 1.0)
	draw_line(Vector2(size.x / 3.0, 0), Vector2(size.x / 3.0, size.y), AppTheme.BORDER, 1.0)
	draw_line(Vector2(size.x * 2.0 / 3.0, 0), Vector2(size.x * 2.0 / 3.0, size.y), AppTheme.BORDER, 1.0)
	for event in bowling_events:
		var point := Vector2(float(event.get("x", 0.5)) * size.x, float(event.get("y", 0.5)) * size.y)
		var wicket: bool = bool(event.get("wicket", false))
		var runs := int(event.get("runs", 0))
		draw_circle(point, 10.0 if wicket else 6.0, _outcome_colour(runs, wicket))
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
			draw_polyline(points, colour, 2.0)
		draw_circle(points[-1], 3.5, colour)


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


## Rolling 24-ball (4-over) momentum swing: sum(runs) - 8*sum(wickets)
## in the trailing window, plotted as a line above/below a zero baseline.
func _draw_momentum() -> void:
	var margin := 24.0
	var plot := Rect2(margin, margin, size.x - margin * 2, size.y - margin * 2)
	draw_rect(plot, AppTheme.SURFACE)
	if momentum_window.size() < 2:
		_draw_centered_label("Not enough deliveries yet.")
		return
	var window_size := 24
	var values: Array = []
	for i in range(momentum_window.size()):
		var start: int = max(0, i - window_size + 1)
		var runs := 0
		var wickets := 0
		for j in range(start, i + 1):
			runs += int(momentum_window[j].get("runs", 0))
			wickets += int(momentum_window[j].get("wicket", false))
		values.append(runs - wickets * 8)
	var max_abs: float = 1.0
	for value in values:
		max_abs = max(max_abs, abs(float(value)))
	var zero_y: float = plot.position.y + plot.size.y / 2.0
	draw_line(Vector2(plot.position.x, zero_y), Vector2(plot.position.x + plot.size.x, zero_y), AppTheme.BORDER, 1.0)
	var points := PackedVector2Array()
	for i in range(values.size()):
		var x: float = plot.position.x + plot.size.x * (float(i) / max(1, values.size() - 1))
		var y: float = zero_y - (float(values[i]) / max_abs) * (plot.size.y / 2.0)
		points.append(Vector2(x, y))
	if points.size() > 1:
		draw_polyline(points, AppTheme.ACCENT, 2.0)


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
	draw_circle(centre, radius, Color(0.15, 0.35, 0.2, 1.0))
	draw_arc(centre, radius * 0.63, 0, TAU, 48, AppTheme.BORDER, 1.5)
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
		draw_circle(point, 8.0, AppTheme.CARD)
		draw_circle(point, 8.0, AppTheme.BORDER, false, 1.5)
		var font := ThemeDB.fallback_font
		var text_size := font.get_string_size(pos["name"], HORIZONTAL_ALIGNMENT_CENTER, -1, 10)
		draw_string(font, point - text_size / 2.0, pos["name"], HORIZONTAL_ALIGNMENT_LEFT, -1, 10, AppTheme.TEXT_PRIMARY)
	# Draw player positions if available
	for player in field_positions:
		var px: float = float(player.get("x", 0.5))
		var py: float = float(player.get("y", 0.5))
		var player_pos := Vector2(centre.x + (px - 0.5) * radius * 2, centre.y + (py - 0.5) * radius * 2)
		draw_circle(player_pos, 6.0, AppTheme.GOLD)
