extends Control
## A drawn cricket ground with the pitch and named fielding positions.
##
## v4.13.0/v4.14.0 (Match Day rebuild, Parts 1-2) gave match_engine.py a
## real per-fielder field_layout_by_team model — angle (degrees, 0 =
## straight down the ground, clockwise) and radius (0.0-1.0 of the
## boundary) per named position, exposed over IPC via get_field_layout/
## set_field_layout. This script now speaks that exact schema (position
## "name" strings match src match_engine.FIELD_POSITIONS 1:1: "WK",
## "Slip", "Gully", "Point", "Cover", "Mid-off", "Mid-on", "Midwicket",
## "Square Leg", "Fine Leg", "Third Man" — no lossy name/unit mapping
## needed anywhere).
##
## Two modes, one scene (reused, not duplicated):
## - `interactive = false` (default, the pre-match hub's use today):
##   read-only cosmetic preview of the default field, exactly as before.
## - `interactive = true` (the live-match Field tab, match_screen.gd):
##   every dot is draggable within the boundary; dragging emits
##   `layout_changed(positions)` on release, which the owning screen wires
##   to the `set_field_layout` IPC call.

signal layout_changed(positions: Dictionary)

const TURF := Color("#2f6b3f")
const TURF_LIGHT := Color("#357a46")
const TURF_EDGE := Color("#1d4529")
const PITCH := Color("#c9b183")
const PITCH_EDGE := Color("#a68a5f")
const STUMPS := Color("#f4efe8")
const FIELDER_FILL := Color("#e9e4da")
const FIELDER_RING := Color("#1d4529")
const FIELDER_KEEPER := Color("#e0a63c")
const FIELDER_TEXT := Color("#1d4529")
const FIELDER_DRAG := Color("#7fb8d8")
const LABEL_COLOR := Color("#eef5f0")
const LABEL_SHADOW := Color(0, 0, 0, 0.55)
const BATTER_MARK := Color("#f4efe8")
const BOWLER_MARK := Color("#7fb8d8")
const FLASH_WICKET := Color("#c33a2e")
const FLASH_BOUNDARY := Color("#c9982b")
const FLASH_NORMAL := Color("#4caf6d")

## Default (Neutral-preset-equivalent) angle/radius per named position —
## mirrors match_engine.py's FIELD_LAYOUT_PRESETS["Neutral"] exactly, so
## the pre-match cosmetic preview and a fresh live match's actual starting
## layout look identical. "num" is the shirt-number-style marker shown
## inside the dot (1 is always the keeper); "keeper" tints that dot gold.
const POSITIONS := [
	{"name": "WK", "num": 1, "angle": 180.0, "radius": 0.16, "keeper": true},
	{"name": "Slip", "num": 2, "angle": 160.0, "radius": 0.22},
	{"name": "Gully", "num": 3, "angle": 135.0, "radius": 0.30},
	{"name": "Point", "num": 4, "angle": 95.0, "radius": 0.55},
	{"name": "Cover", "num": 5, "angle": 55.0, "radius": 0.65},
	{"name": "Mid-off", "num": 6, "angle": 22.0, "radius": 0.45},
	{"name": "Mid-on", "num": 7, "angle": 338.0, "radius": 0.45},
	{"name": "Midwicket", "num": 8, "angle": 305.0, "radius": 0.65},
	{"name": "Square Leg", "num": 9, "angle": 265.0, "radius": 0.55},
	{"name": "Fine Leg", "num": 10, "angle": 205.0, "radius": 0.85},
	{"name": "Third Man", "num": 11, "angle": 160.0, "radius": 0.85},
]

const DOT_RADIUS := 12.0
const MIN_RADIUS := 0.08
const MAX_RADIUS := 1.0

@export var interactive: bool = false

## Working layout: {name: {"angle": float_degrees, "radius": float_0_1}}.
## Empty until set_layout() is called — _effective() falls back to each
## position's POSITIONS default so the read-only pre-match preview needs
## no wiring at all, matching its behaviour before this rewrite.
var _layout: Dictionary = {}
var _dragging_name: String = ""

## Live-match markers (v4.15.0/v4.16.0 Match Day rebuild, Part 4) — the
## PITCH tab's read-only ground view sets these; the FIELD tab's editable
## instance never does, so it renders exactly as before. `last_shot`, when
## non-empty, draws a highlighted line+dot at the most recent ball's
## landing spot ({"angle": degrees, "distance": 0-1, "kind": "wicket"|
## "boundary"|"normal"}) — the same coordinate space as everything else.
var live_striker: String = ""
var live_non_striker: String = ""
var live_bowler: String = ""
var last_shot: Dictionary = {}

## Ball-flight animation (v4.20.0 Match Day rebuild): a genuine ball-by-ball
## visual, not an instant static flash — each new delivery's shot tweens a
## marker from the bowler's end to the landing point over a short beat.
## _flight_t reaches 1.0 (fully landed) almost immediately for shots not
## worth animating (dots/singles keep the view calm, only 4s/6s/wickets get
## the full flight treatment) so the live view doesn't feel busy every ball.
var _flight_t: float = 1.0
var _flight_tween: Tween = null


func set_live_state(striker: String, non_striker: String, bowler: String, shot: Dictionary) -> void:
	live_striker = striker
	live_non_striker = non_striker
	live_bowler = bowler
	var is_new_shot: bool = not shot.is_empty() and shot != last_shot
	last_shot = shot
	if is_new_shot:
		var kind := str(shot.get("kind", "normal"))
		if _flight_tween:
			_flight_tween.kill()
		if kind in ["wicket", "boundary"]:
			_flight_t = 0.0
			_flight_tween = create_tween()
			_flight_tween.tween_method(_set_flight_t, 0.0, 1.0, 0.45).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		else:
			_flight_t = 1.0
	queue_redraw()


func _set_flight_t(t: float) -> void:
	_flight_t = t
	queue_redraw()


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	queue_redraw()
	resized.connect(queue_redraw)


## Replace the working layout wholesale from an IPC-shaped
## {name: {angle, radius}} dict — accepts a partial dict (missing names
## fall back to their POSITIONS default via _effective()).
func set_layout(layout: Dictionary) -> void:
	_layout = layout.duplicate(true)
	queue_redraw()


func get_layout() -> Dictionary:
	var result := {}
	for pos in POSITIONS:
		result[pos["name"]] = _effective(pos["name"])
	return result


func _effective(name: String) -> Dictionary:
	if _layout.has(name):
		return _layout[name]
	for pos in POSITIONS:
		if pos["name"] == name:
			return {"angle": pos["angle"], "radius": pos["radius"]}
	return {"angle": 0.0, "radius": 0.5}


func _center() -> Vector2:
	return size / 2.0


func _boundary_radius() -> float:
	return min(size.x, size.y) / 2.0 - 10.0


func _point_for(name: String) -> Vector2:
	var pos: Dictionary = _effective(name)
	var angle_rad: float = deg_to_rad(float(pos["angle"]) - 90.0)
	var direction := Vector2(cos(angle_rad), sin(angle_rad))
	return _center() + direction * float(pos["radius"]) * _boundary_radius()


func _draw() -> void:
	var center := _center()
	var boundary_radius := _boundary_radius()
	if boundary_radius <= 0:
		return

	# Ground: a soft radial-ish look via two turf tones plus a darker rim,
	# mown-stripe style rings for texture instead of one flat green disc.
	# antialiased=true everywhere below — Godot's draw_circle/draw_arc/
	# draw_line default to false, which is what made this whole view read
	# as jagged/pixelated at the card's actual on-screen size.
	draw_circle(center, boundary_radius, TURF_EDGE, true, -1.0, true)
	draw_circle(center, boundary_radius - 4.0, TURF, true, -1.0, true)
	for ring in range(1, 4):
		var ring_r: float = boundary_radius * (float(ring) / 4.0)
		draw_arc(center, ring_r, 0, TAU, 48, TURF_LIGHT, 1.0, true)

	var pitch_length := boundary_radius * 0.62
	var pitch_width := boundary_radius * 0.1
	var pitch_rect := Rect2(center.x - pitch_width / 2.0, center.y - pitch_length / 2.0, pitch_width, pitch_length)
	draw_rect(pitch_rect.grow(2.0), PITCH_EDGE)
	draw_rect(pitch_rect, PITCH)
	_draw_stumps(Vector2(center.x, pitch_rect.position.y), -1.0)
	_draw_stumps(Vector2(center.x, pitch_rect.end.y), 1.0)
	draw_rect(Rect2(pitch_rect.position.x - 4, pitch_rect.position.y - 2, pitch_width + 8, 3), STUMPS)
	draw_rect(Rect2(pitch_rect.position.x - 4, pitch_rect.end.y - 1, pitch_width + 8, 3), STUMPS)

	var font := ThemeDB.fallback_font
	for pos in POSITIONS:
		var name: String = pos["name"]
		var point: Vector2 = _point_for(name)
		var is_keeper: bool = pos.get("keeper", false)
		var is_dragging: bool = interactive and name == _dragging_name

		draw_circle(point, DOT_RADIUS + 2.5, FIELDER_DRAG if is_dragging else FIELDER_RING, true, -1.0, true)
		draw_circle(point, DOT_RADIUS, FIELDER_KEEPER if is_keeper else FIELDER_FILL, true, -1.0, true)
		var num_text := str(pos["num"])
		var num_size := font.get_string_size(num_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12)
		draw_string(font, point - num_size / 2.0 + Vector2(0, num_size.y * 0.35), num_text,
			HORIZONTAL_ALIGNMENT_LEFT, -1, 12, FIELDER_TEXT)

		# Labels for tightly-clustered close-in fielders (WK/slip/gully) fan
		# out radially from the point instead of all stacking directly below
		# it, which is what made them overlap into unreadable text before.
		var direction: Vector2 = (point - center).normalized() if point != center else Vector2.UP
		var label: String = name.to_upper()
		var text_size := font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12)
		var label_point: Vector2 = point + direction * (DOT_RADIUS + 14.0) - Vector2(text_size.x / 2.0, -text_size.y * 0.3)
		draw_string(font, label_point + Vector2(1, 1), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, LABEL_SHADOW)
		draw_string(font, label_point, label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, LABEL_COLOR)

	if interactive:
		var hint := "Drag a fielder to reposition" if _dragging_name.is_empty() else _dragging_name.to_upper()
		var hint_size := font.get_string_size(hint, HORIZONTAL_ALIGNMENT_CENTER, -1, 12)
		draw_string(font, Vector2(center.x - hint_size.x / 2.0, size.y - 8.0), hint,
			HORIZONTAL_ALIGNMENT_LEFT, -1, 12, LABEL_COLOR)

	if not live_striker.is_empty():
		var striker_point := Vector2(center.x, pitch_rect.end.y + 10.0)
		var bowler_point := Vector2(center.x, pitch_rect.position.y - 14.0)
		draw_circle(striker_point, 5.0, BATTER_MARK, true, -1.0, true)
		draw_circle(bowler_point, 5.0, BOWLER_MARK, true, -1.0, true)
		_draw_name_tag(font, striker_point + Vector2(0, 14.0), live_striker)
		_draw_name_tag(font, Vector2(center.x - pitch_length * 0.32, center.y), live_non_striker)
		_draw_name_tag(font, bowler_point + Vector2(0, -12.0), live_bowler)
		if not last_shot.is_empty():
			var angle_deg: float = float(last_shot.get("angle", 0.0))
			var distance: float = clampf(float(last_shot.get("distance", 0.3)), 0.0, 1.0)
			var kind: String = str(last_shot.get("kind", "normal"))
			var colour: Color = FLASH_WICKET if kind == "wicket" else FLASH_BOUNDARY if kind == "boundary" else FLASH_NORMAL
			var angle_rad: float = deg_to_rad(angle_deg - 90.0)
			var end: Vector2 = center + Vector2(cos(angle_rad), sin(angle_rad)) * boundary_radius * distance
			# The travelled portion of the shot so far (v4.20.0 flight tween) —
			# a fresh 4/6/wicket draws its line growing outward and the ball
			# marker chasing the tip, instead of popping in fully formed.
			var travelled: Vector2 = center.lerp(end, _flight_t)
			draw_line(center, travelled, colour, 2.5, true)
			if _flight_t >= 1.0:
				draw_arc(end, 9.0, 0, TAU, 24, colour.lightened(0.4), 2.0, true)
			draw_circle(travelled, 6.0, colour, true, -1.0, true)


func _draw_name_tag(font: Font, point: Vector2, text: String) -> void:
	if text.is_empty():
		return
	var text_size := font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, 11)
	var top_left := point - Vector2(text_size.x / 2.0, -text_size.y * 0.3)
	draw_string(font, top_left + Vector2(1, 1), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, LABEL_SHADOW)
	draw_string(font, top_left, text, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, LABEL_COLOR)


func _draw_stumps(base: Vector2, direction: float) -> void:
	for i in range(-1, 2):
		draw_line(base + Vector2(i * 4, 0), base + Vector2(i * 4, 14.0 * direction), STUMPS, 2.0, true)


func _gui_input(event: InputEvent) -> void:
	if not interactive:
		return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			var hit := _find_dot_at(event.position)
			if hit != "":
				_dragging_name = hit
				queue_redraw()
		elif not _dragging_name.is_empty():
			_dragging_name = ""
			queue_redraw()
			layout_changed.emit(get_layout())
	elif event is InputEventMouseMotion and not _dragging_name.is_empty():
		_drag_to(event.position)


func _find_dot_at(point: Vector2) -> String:
	var closest := ""
	var closest_dist := DOT_RADIUS * 2.2
	for pos in POSITIONS:
		var name: String = pos["name"]
		var dist: float = _point_for(name).distance_to(point)
		if dist < closest_dist:
			closest_dist = dist
			closest = name
	return closest


func _drag_to(point: Vector2) -> void:
	var center := _center()
	var boundary_radius := _boundary_radius()
	if boundary_radius <= 0:
		return
	var offset := point - center
	var angle_deg := rad_to_deg(offset.angle()) + 90.0
	angle_deg = fmod(angle_deg + 360.0, 360.0)
	var radius: float = clampf(offset.length() / boundary_radius, MIN_RADIUS, MAX_RADIUS)
	_layout[_dragging_name] = {"angle": angle_deg, "radius": radius}
	queue_redraw()
