extends Control
## A drawn cricket ground with the pitch and classic fielding positions —
## the "wagon wheel"-style ground diagram referenced from Cricket Captain's
## match-day screen. No live ball-by-ball feed exists yet (see
## docs/GRAPHICS_MIGRATION_PLAN.md), so this renders the *default field
## placement* for the given bowling style as a real, useful pre-match view
## rather than fabricating shot data that doesn't exist.

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
const LABEL_COLOR := Color("#eef5f0")
const LABEL_SHADOW := Color(0, 0, 0, 0.55)

## angle (degrees, 0 = straight down the ground toward the batsman's off
## side, clockwise) and radius (0-1 of the boundary) for a standard
## attacking field to a right-handed batsman. "num" is the shirt-number
## style marker shown inside the dot (1 is always the keeper).
const POSITIONS := [
	{"label": "WK", "num": 1, "angle": 180, "radius": 0.16, "keeper": true},
	{"label": "SLIP", "num": 2, "angle": 160, "radius": 0.22},
	{"label": "GULLY", "num": 3, "angle": 135, "radius": 0.30},
	{"label": "POINT", "num": 4, "angle": 95, "radius": 0.55},
	{"label": "COVER", "num": 5, "angle": 55, "radius": 0.65},
	{"label": "MID-OFF", "num": 6, "angle": 22, "radius": 0.45},
	{"label": "MID-ON", "num": 7, "angle": -22, "radius": 0.45},
	{"label": "MIDWICKET", "num": 8, "angle": -55, "radius": 0.65},
	{"label": "SQUARE LEG", "num": 9, "angle": -95, "radius": 0.55},
	{"label": "FINE LEG", "num": 10, "angle": -155, "radius": 0.85},
	{"label": "THIRD MAN", "num": 11, "angle": 160, "radius": 0.85},
]

const DOT_RADIUS := 12.0


func _ready() -> void:
	queue_redraw()
	resized.connect(queue_redraw)


func _draw() -> void:
	var center := size / 2.0
	var boundary_radius: float = min(size.x, size.y) / 2.0 - 10.0

	# Ground: a soft radial-ish look via two turf tones plus a darker rim,
	# mown-stripe style rings for texture instead of one flat green disc.
	draw_circle(center, boundary_radius, TURF_EDGE)
	draw_circle(center, boundary_radius - 4.0, TURF)
	for ring in range(1, 4):
		var ring_r: float = boundary_radius * (float(ring) / 4.0)
		draw_arc(center, ring_r, 0, TAU, 48, TURF_LIGHT, 1.0)

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
		var angle_rad: float = deg_to_rad(float(pos["angle"]) - 90.0)
		var direction := Vector2(cos(angle_rad), sin(angle_rad))
		var r: float = float(pos["radius"]) * boundary_radius
		var point: Vector2 = center + direction * r
		var is_keeper: bool = pos.get("keeper", false)

		draw_circle(point, DOT_RADIUS + 2.5, FIELDER_RING)
		draw_circle(point, DOT_RADIUS, FIELDER_KEEPER if is_keeper else FIELDER_FILL)
		var num_text := str(pos["num"])
		var num_size := font.get_string_size(num_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12)
		draw_string(font, point - num_size / 2.0 + Vector2(0, num_size.y * 0.35), num_text,
			HORIZONTAL_ALIGNMENT_LEFT, -1, 12, FIELDER_TEXT)

		# Labels for tightly-clustered close-in fielders (WK/slip/gully) fan
		# out radially from the point instead of all stacking directly below
		# it, which is what made them overlap into unreadable text before.
		var label: String = pos["label"]
		var text_size := font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12)
		var label_point: Vector2 = point + direction * (DOT_RADIUS + 14.0) - Vector2(text_size.x / 2.0, -text_size.y * 0.3)
		draw_string(font, label_point + Vector2(1, 1), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, LABEL_SHADOW)
		draw_string(font, label_point, label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, LABEL_COLOR)


func _draw_stumps(base: Vector2, direction: float) -> void:
	for i in range(-1, 2):
		draw_line(base + Vector2(i * 4, 0), base + Vector2(i * 4, 14.0 * direction), STUMPS, 2.0)
