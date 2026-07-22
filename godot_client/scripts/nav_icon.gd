class_name NavIcon
extends Control
## Small hand-drawn nav-rail icons — no icon asset pipeline exists yet, so
## these are simple geometric glyphs drawn in code (same approach as
## ground_view.gd), one distinct shape per nav section so the sidebar
## reads at a glance the way the FM26 reference's icon rail does.

var kind: String = "dot"
var icon_colour: Color = Color(0.8, 0.8, 0.82)

const SIZE := 18


func set_kind(p_kind: String) -> void:
	kind = p_kind
	queue_redraw()


func set_colour(p_colour: Color) -> void:
	icon_colour = p_colour
	queue_redraw()


func _ready() -> void:
	custom_minimum_size = Vector2(SIZE, SIZE)


func _draw() -> void:
	var c := icon_colour
	var s := float(SIZE)
	match kind:
		"dashboard":
			draw_rect(Rect2(2, 2, s * 0.42, s * 0.42), c, false, 1.6)
			draw_rect(Rect2(s * 0.56, 2, s * 0.42, s * 0.28), c, false, 1.6)
			draw_rect(Rect2(2, s * 0.56, s * 0.42, s * 0.4), c, false, 1.6)
			draw_rect(Rect2(s * 0.56, s * 0.42, s * 0.42, s * 0.54), c, false, 1.6)
		"inbox":
			draw_rect(Rect2(2, 4, s - 4, s - 8), c, false, 1.6)
			draw_line(Vector2(2, 4), Vector2(s / 2.0, s / 2.0 + 1), c, 1.6)
			draw_line(Vector2(s - 2, 4), Vector2(s / 2.0, s / 2.0 + 1), c, 1.6)
		"squad":
			draw_circle(Vector2(s / 2.0, s * 0.32), s * 0.2, c)
			draw_arc(Vector2(s / 2.0, s * 0.95), s * 0.4, PI, TAU, 16, c, 1.6)
		"selection":
			draw_line(Vector2(3, s * 0.3), Vector2(s - 3, s * 0.3), c, 1.6)
			draw_line(Vector2(3, s * 0.55), Vector2(s - 3, s * 0.55), c, 1.6)
			draw_line(Vector2(3, s * 0.8), Vector2(s * 0.65, s * 0.8), c, 1.6)
			draw_circle(Vector2(s - 5, s * 0.8), 2.0, c)
		"training":
			draw_line(Vector2(2, s / 2.0), Vector2(s - 2, s / 2.0), c, 2.4)
			draw_line(Vector2(s * 0.22, s * 0.3), Vector2(s * 0.22, s * 0.7), c, 2.4)
			draw_line(Vector2(s * 0.78, s * 0.3), Vector2(s * 0.78, s * 0.7), c, 2.4)
		"academy":
			var pts := PackedVector2Array([Vector2(s / 2.0, 3), Vector2(s - 2, s * 0.4), Vector2(s / 2.0, s * 0.7), Vector2(2, s * 0.4)])
			draw_polyline(pts, c, 1.6, true)
			draw_line(Vector2(s / 2.0, s * 0.7), Vector2(s / 2.0, s - 3), c, 1.6)
		"medical":
			draw_line(Vector2(s / 2.0, 3), Vector2(s / 2.0, s - 3), c, 2.6)
			draw_line(Vector2(3, s / 2.0), Vector2(s - 3, s / 2.0), c, 2.6)
		"match":
			draw_arc(Vector2(s / 2.0, s / 2.0), s * 0.42, 0, TAU, 24, c, 1.6)
			draw_line(Vector2(s * 0.3, s * 0.7), Vector2(s * 0.7, s * 0.3), c, 1.8)
		"recruitment":
			draw_circle(Vector2(s * 0.4, s * 0.35), s * 0.22, c)
			draw_arc(Vector2(s * 0.4, s * 0.9), s * 0.32, PI, TAU, 12, c, 1.6)
			draw_line(Vector2(s * 0.72, s * 0.5), Vector2(s * 0.94, s * 0.5), c, 1.6)
			draw_line(Vector2(s * 0.84, s * 0.4), Vector2(s * 0.94, s * 0.5), c, 1.6)
			draw_line(Vector2(s * 0.84, s * 0.6), Vector2(s * 0.94, s * 0.5), c, 1.6)
		"transfers":
			draw_line(Vector2(3, s * 0.35), Vector2(s - 5, s * 0.35), c, 1.6)
			draw_line(Vector2(s - 9, s * 0.25), Vector2(s - 3, s * 0.35), c, 1.6)
			draw_line(Vector2(s - 9, s * 0.45), Vector2(s - 3, s * 0.35), c, 1.6)
			draw_line(Vector2(5, s * 0.65), Vector2(s - 3, s * 0.65), c, 1.6)
			draw_line(Vector2(9, s * 0.55), Vector2(3, s * 0.65), c, 1.6)
			draw_line(Vector2(9, s * 0.75), Vector2(3, s * 0.65), c, 1.6)
		"staff":
			draw_circle(Vector2(s / 2.0, s * 0.32), s * 0.2, c)
			draw_arc(Vector2(s / 2.0, s * 0.95), s * 0.4, PI, TAU, 16, c, 1.6)
		"finances":
			draw_circle(Vector2(s / 2.0, s / 2.0), s * 0.4, c, false, 1.6)
			draw_line(Vector2(s / 2.0, s * 0.28), Vector2(s / 2.0, s * 0.72), c, 1.4)
		"facilities":
			draw_line(Vector2(3, s - 3), Vector2(s - 3, s - 3), c, 1.6)
			draw_line(Vector2(4, s - 3), Vector2(4, s * 0.3), c, 1.6)
			draw_line(Vector2(s - 4, s - 3), Vector2(s - 4, s * 0.3), c, 1.6)
			draw_line(Vector2(4, s * 0.3), Vector2(s / 2.0, 3), c, 1.6)
			draw_line(Vector2(s - 4, s * 0.3), Vector2(s / 2.0, 3), c, 1.6)
		"career":
			draw_arc(Vector2(s / 2.0, s * 0.4), s * 0.32, 0, TAU, 20, c, 1.6)
			draw_line(Vector2(s * 0.35, s * 0.68), Vector2(s * 0.65, s * 0.68), c, 1.6)
			draw_line(Vector2(s / 2.0, s * 0.68), Vector2(s / 2.0, s - 3), c, 1.6)
		_:
			draw_circle(Vector2(s / 2.0, s / 2.0), s * 0.15, c)
