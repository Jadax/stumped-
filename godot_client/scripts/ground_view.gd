extends Control
## A drawn cricket ground with the pitch and classic fielding positions —
## the "wagon wheel"-style ground diagram referenced from Cricket Captain's
## match-day screen. No live ball-by-ball feed exists yet (see
## docs/GRAPHICS_MIGRATION_PLAN.md), so this renders the *default field
## placement* for the given bowling style as a real, useful pre-match view
## rather than fabricating shot data that doesn't exist.

const TURF := Color("#2f6b3f")
const TURF_EDGE := Color("#255431")
const PITCH := Color("#c9b183")
const CREASE := Color("#f4efe8")
const FIELDER := Color("#f4efe8")
const FIELDER_KEEPER := Color("#e0a63c")
const LABEL_COLOR := Color("#d8e8dc")

## angle (degrees, 0 = straight down the ground toward the batsman's off
## side, clockwise) and radius (0-1 of the boundary) for a standard
## attacking field to a right-handed batsman.
const POSITIONS := [
	{"label": "WK", "angle": 180, "radius": 0.10, "keeper": true},
	{"label": "SLIP", "angle": 165, "radius": 0.14},
	{"label": "GULLY", "angle": 145, "radius": 0.20},
	{"label": "POINT", "angle": 95, "radius": 0.55},
	{"label": "COVER", "angle": 55, "radius": 0.62},
	{"label": "MID-OFF", "angle": 25, "radius": 0.45},
	{"label": "MID-ON", "angle": -25, "radius": 0.45},
	{"label": "MIDWICKET", "angle": -60, "radius": 0.62},
	{"label": "SQUARE LEG", "angle": -95, "radius": 0.55},
	{"label": "FINE LEG", "angle": -155, "radius": 0.85},
	{"label": "THIRD MAN", "angle": 160, "radius": 0.85},
]


func _ready() -> void:
	queue_redraw()
	resized.connect(queue_redraw)


func _draw() -> void:
	var center := size / 2.0
	var boundary_radius: float = min(size.x, size.y) / 2.0 - 8.0
	draw_circle(center, boundary_radius, TURF)
	draw_arc(center, boundary_radius, 0, TAU, 64, TURF_EDGE, 3.0)

	var pitch_length := boundary_radius * 0.62
	var pitch_width := boundary_radius * 0.09
	var pitch_rect := Rect2(center.x - pitch_width / 2.0, center.y - pitch_length / 2.0, pitch_width, pitch_length)
	draw_rect(pitch_rect, PITCH)
	draw_rect(Rect2(pitch_rect.position.x - 4, pitch_rect.position.y - 2, pitch_width + 8, 4), CREASE)
	draw_rect(Rect2(pitch_rect.position.x - 4, pitch_rect.end.y - 2, pitch_width + 8, 4), CREASE)

	var font := ThemeDB.fallback_font
	for pos in POSITIONS:
		var angle_rad: float = deg_to_rad(float(pos["angle"]) - 90.0)
		var r: float = float(pos["radius"]) * boundary_radius
		var point: Vector2 = center + Vector2(cos(angle_rad), sin(angle_rad)) * r
		var colour: Color = FIELDER_KEEPER if pos.get("keeper", false) else FIELDER
		draw_circle(point, 7.0, colour)
		draw_circle(point, 7.0, TURF_EDGE.lightened(0.1))
		var label: String = pos["label"]
		var text_size := font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, 11)
		draw_string(font, point + Vector2(-text_size.x / 2.0, 20), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, LABEL_COLOR)
