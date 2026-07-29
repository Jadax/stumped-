class_name NavIcon
extends Control
## Small hand-drawn nav-rail icons — no icon asset pipeline exists yet, so
## these are simple geometric glyphs drawn in code (same approach as
## ground_view.gd), one distinct shape per nav section so the sidebar
## reads at a glance the way the FM26 reference's icon rail does.

var kind: String = "dot"
var icon_colour: Color = Color(0.8, 0.8, 0.82)

const SIZE := 22


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
			draw_rect(Rect2(2, 2, s * 0.42, s * 0.42), c, false, 2.0)
			draw_rect(Rect2(s * 0.56, 2, s * 0.42, s * 0.28), c, false, 2.0)
			draw_rect(Rect2(2, s * 0.56, s * 0.42, s * 0.4), c, false, 2.0)
			draw_rect(Rect2(s * 0.56, s * 0.42, s * 0.42, s * 0.54), c, false, 2.0)
		"inbox":
			draw_rect(Rect2(2, 4, s - 4, s - 8), c, false, 2.0)
			draw_line(Vector2(2, 4), Vector2(s / 2.0, s / 2.0 + 1), c, 2.0)
			draw_line(Vector2(s - 2, 4), Vector2(s / 2.0, s / 2.0 + 1), c, 2.0)
		"squad":
			draw_circle(Vector2(s / 2.0, s * 0.32), s * 0.2, c)
			draw_arc(Vector2(s / 2.0, s * 0.95), s * 0.4, PI, TAU, 16, c, 2.0)
		"selection":
			draw_line(Vector2(3, s * 0.3), Vector2(s - 3, s * 0.3), c, 2.0)
			draw_line(Vector2(3, s * 0.55), Vector2(s - 3, s * 0.55), c, 2.0)
			draw_line(Vector2(3, s * 0.8), Vector2(s * 0.65, s * 0.8), c, 2.0)
			draw_circle(Vector2(s - 5, s * 0.8), 2.0, c)
		"training":
			draw_line(Vector2(2, s / 2.0), Vector2(s - 2, s / 2.0), c, 2.8)
			draw_line(Vector2(s * 0.22, s * 0.3), Vector2(s * 0.22, s * 0.7), c, 2.8)
			draw_line(Vector2(s * 0.78, s * 0.3), Vector2(s * 0.78, s * 0.7), c, 2.8)
		"academy":
			var pts := PackedVector2Array([Vector2(s / 2.0, 3), Vector2(s - 2, s * 0.4), Vector2(s / 2.0, s * 0.7), Vector2(2, s * 0.4)])
			draw_polyline(pts, c, 1.6, true)
			draw_line(Vector2(s / 2.0, s * 0.7), Vector2(s / 2.0, s - 3), c, 2.0)
		"medical":
			draw_line(Vector2(s / 2.0, 3), Vector2(s / 2.0, s - 3), c, 3.0)
			draw_line(Vector2(3, s / 2.0), Vector2(s - 3, s / 2.0), c, 3.0)
		"match":
			draw_arc(Vector2(s / 2.0, s / 2.0), s * 0.42, 0, TAU, 24, c, 2.0)
			draw_line(Vector2(s * 0.3, s * 0.7), Vector2(s * 0.7, s * 0.3), c, 2.2)
		"recruitment":
			draw_circle(Vector2(s * 0.4, s * 0.35), s * 0.22, c)
			draw_arc(Vector2(s * 0.4, s * 0.9), s * 0.32, PI, TAU, 12, c, 2.0)
			draw_line(Vector2(s * 0.72, s * 0.5), Vector2(s * 0.94, s * 0.5), c, 2.0)
			draw_line(Vector2(s * 0.84, s * 0.4), Vector2(s * 0.94, s * 0.5), c, 2.0)
			draw_line(Vector2(s * 0.84, s * 0.6), Vector2(s * 0.94, s * 0.5), c, 2.0)
		"transfers":
			draw_line(Vector2(3, s * 0.35), Vector2(s - 5, s * 0.35), c, 2.0)
			draw_line(Vector2(s - 9, s * 0.25), Vector2(s - 3, s * 0.35), c, 2.0)
			draw_line(Vector2(s - 9, s * 0.45), Vector2(s - 3, s * 0.35), c, 2.0)
			draw_line(Vector2(5, s * 0.65), Vector2(s - 3, s * 0.65), c, 2.0)
			draw_line(Vector2(9, s * 0.55), Vector2(3, s * 0.65), c, 2.0)
			draw_line(Vector2(9, s * 0.75), Vector2(3, s * 0.65), c, 2.0)
		"staff":
			draw_circle(Vector2(s / 2.0, s * 0.32), s * 0.2, c)
			draw_arc(Vector2(s / 2.0, s * 0.95), s * 0.4, PI, TAU, 16, c, 2.0)
		"finances":
			draw_circle(Vector2(s / 2.0, s / 2.0), s * 0.4, c, false, 2.0)
			draw_line(Vector2(s / 2.0, s * 0.28), Vector2(s / 2.0, s * 0.72), c, 2.2)
		"facilities":
			draw_line(Vector2(3, s - 3), Vector2(s - 3, s - 3), c, 2.0)
			draw_line(Vector2(4, s - 3), Vector2(4, s * 0.3), c, 2.0)
			draw_line(Vector2(s - 4, s - 3), Vector2(s - 4, s * 0.3), c, 2.0)
			draw_line(Vector2(4, s * 0.3), Vector2(s / 2.0, 3), c, 2.0)
			draw_line(Vector2(s - 4, s * 0.3), Vector2(s / 2.0, 3), c, 2.0)
		"career":
			draw_arc(Vector2(s / 2.0, s * 0.4), s * 0.32, 0, TAU, 20, c, 2.0)
			draw_line(Vector2(s * 0.35, s * 0.68), Vector2(s * 0.65, s * 0.68), c, 2.0)
			draw_line(Vector2(s / 2.0, s * 0.68), Vector2(s / 2.0, s - 3), c, 2.0)
		"settings":
			draw_circle(Vector2(s / 2.0, s / 2.0), s * 0.18, c, false, 2.0)
			for i in range(6):
				var a := TAU * i / 6.0
				var inner := Vector2(s / 2.0, s / 2.0) + Vector2(cos(a), sin(a)) * s * 0.24
				var outer := Vector2(s / 2.0, s / 2.0) + Vector2(cos(a), sin(a)) * s * 0.42
				draw_line(inner, outer, c, 2.0)
		"help":
			draw_arc(Vector2(s / 2.0, s / 2.0), s * 0.4, 0, TAU, 20, c, 2.0)
			draw_arc(Vector2(s / 2.0, s * 0.4), s * 0.16, PI * 0.9, TAU * 0.85, 10, c, 2.0)
			draw_circle(Vector2(s / 2.0, s * 0.68), 1.4, c)
		"bookmarks":
			var star := PackedVector2Array()
			for i in range(5):
				var a := -PI / 2.0 + TAU * i / 5.0
				var inner_a := -PI / 2.0 + TAU * (i + 0.5) / 5.0
				star.append(Vector2(s / 2.0, s / 2.0) + Vector2(cos(a), sin(a)) * s * 0.42)
				star.append(Vector2(s / 2.0, s / 2.0) + Vector2(cos(inner_a), sin(inner_a)) * s * 0.2)
			draw_polyline(star, c, 1.4, true)
		"data_hub":
			for i in range(4):
				var h := 0.25 + i * 0.18
				var x := 3.0 + i * (s - 6.0) / 4.0
				var w := (s - 6.0) / 5.0
				draw_rect(Rect2(x, s - 3 - h * s, w, h * s), c, false, 2.2)
		"quit":
			draw_rect(Rect2(3, s * 0.22, s * 0.42, s * 0.56), c, false, 2.0)
			draw_line(Vector2(s * 0.42, s / 2.0), Vector2(s - 3, s / 2.0), c, 2.0)
			draw_line(Vector2(s - 8, s * 0.38), Vector2(s - 3, s / 2.0), c, 2.0)
			draw_line(Vector2(s - 8, s * 0.62), Vector2(s - 3, s / 2.0), c, 2.0)
		"press":
			draw_arc(Vector2(s / 2.0, s * 0.38), s * 0.22, 0, TAU, 20, c, 2.0)
			draw_line(Vector2(s / 2.0, s * 0.6), Vector2(s / 2.0, s * 0.82), c, 2.0)
			draw_line(Vector2(s * 0.35, s * 0.82), Vector2(s * 0.65, s * 0.82), c, 2.0)
		"cup":
			draw_arc(Vector2(s / 2.0, s * 0.35), s * 0.28, 0, PI, 16, c, 2.0)
			draw_line(Vector2(s * 0.28, s * 0.35), Vector2(s * 0.28, s * 0.55), c, 2.0)
			draw_line(Vector2(s * 0.72, s * 0.35), Vector2(s * 0.72, s * 0.55), c, 2.0)
			draw_line(Vector2(s / 2.0, s * 0.62), Vector2(s / 2.0, s * 0.78), c, 2.0)
			draw_line(Vector2(s * 0.35, s * 0.78), Vector2(s * 0.65, s * 0.78), c, 2.0)
		"legends":
			var star := PackedVector2Array()
			for i in range(5):
				var a := -PI / 2.0 + TAU * i / 5.0
				var inner_a := -PI / 2.0 + TAU * (i + 0.5) / 5.0
				star.append(Vector2(s / 2.0, s * 0.42) + Vector2(cos(a), sin(a)) * s * 0.38)
				star.append(Vector2(s / 2.0, s * 0.42) + Vector2(cos(inner_a), sin(inner_a)) * s * 0.18)
			draw_polyline(star, c, 1.8, true)
			draw_line(Vector2(s * 0.35, s * 0.78), Vector2(s * 0.65, s * 0.78), c, 2.0)
		"offers":
			draw_rect(Rect2(3, s * 0.28, s * 0.56, s * 0.48), c, false, 2.0)
			draw_line(Vector2(s * 0.59, s * 0.28), Vector2(s * 0.59, s * 0.22), c, 2.0)
			draw_line(Vector2(s * 0.45, s * 0.22), Vector2(s * 0.73, s * 0.22), c, 2.0)
		_:
			draw_circle(Vector2(s / 2.0, s / 2.0), s * 0.15, c)
