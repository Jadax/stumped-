extends Control
## A close, top-down bowling pitch strip — the Cricket Captain reference's
## "aim the next ball" widget (v4.21.0). Distinct from ground_view.gd's
## full 360° fielding ground: this is just the 22-yard strip between the
## stumps, split into a clickable line (Leg/Middle/Off/Wide) × length
## (Short/Good/Full/Yorker) grid that calls ipc_server.py's
## set_delivery_target — "make my bowler bowl to the three stumps" is
## exactly this: click the zone, next ball aims there (control-skill-based
## chance to land it, not a guarantee — see match_engine.py's
## _choose_delivery_line_length).

signal target_chosen(line: String, length: String)

const LINE_TARGETS := ["Leg Stump", "Middle", "Off Stump", "Wide"]
const LENGTH_TARGETS := ["Short", "Good", "Full", "Yorker"]

const PITCH := Color("#c9b183")
const PITCH_EDGE := Color("#a68a5f")
const STUMPS := Color("#f4efe8")
const CREASE := Color(0.96, 0.94, 0.9, 0.55)
const GRID_LINE := Color(0.96, 0.94, 0.9, 0.18)
const TARGET_MARK := Color("#2f6b3f")
const ZONE_HOVER := Color(0, 0, 0, 0.06)
const ZONE_LABEL := Color(0.30, 0.25, 0.18, 0.85)

@export var interactive: bool = true

var bowling_events: Array = []
var current_line: String = ""
var current_length: String = ""
var _hover_cell: Vector2i = Vector2i(-1, -1)


func set_target(line: String, length: String) -> void:
	current_line = line
	current_length = length
	queue_redraw()


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	queue_redraw()
	resized.connect(queue_redraw)


func _pitch_rect() -> Rect2:
	var margin_x: float = size.x * 0.12
	var margin_y: float = size.y * 0.08
	return Rect2(margin_x, margin_y, size.x - margin_x * 2.0, size.y - margin_y * 2.0)


func _draw() -> void:
	var rect := _pitch_rect()
	if rect.size.x <= 0 or rect.size.y <= 0:
		return
	draw_rect(rect.grow(3.0), PITCH_EDGE)
	draw_rect(rect, PITCH)
	# Faint mown-stripe texture, four vertical bands.
	for i in range(1, 4):
		var x: float = rect.position.x + rect.size.x * (float(i) / 4.0)
		draw_line(Vector2(x, rect.position.y), Vector2(x, rect.end.y), Color(1, 1, 1, 0.04), 2.0)

	var col_w: float = rect.size.x / 4.0
	var row_h: float = rect.size.y / 4.0

	# Grid + zone labels (line across the top, length down the left).
	for i in range(1, 4):
		draw_line(Vector2(rect.position.x + col_w * i, rect.position.y),
			Vector2(rect.position.x + col_w * i, rect.end.y), GRID_LINE, 1.0)
		draw_line(Vector2(rect.position.x, rect.position.y + row_h * i),
			Vector2(rect.end.x, rect.position.y + row_h * i), GRID_LINE, 1.0)

	var font := ThemeDB.fallback_font
	for c in range(4):
		var label: String = LINE_TARGETS[c].replace(" Stump", "").to_upper()
		draw_string(font, Vector2(rect.position.x + col_w * c + 4, rect.position.y - 4),
			label, HORIZONTAL_ALIGNMENT_LEFT, col_w - 8, 9, ZONE_LABEL)
	for r in range(4):
		draw_string(font, Vector2(rect.position.x + 4, rect.position.y + row_h * r + 11),
			LENGTH_TARGETS[r].to_upper(), HORIZONTAL_ALIGNMENT_LEFT, col_w - 8, 8, ZONE_LABEL)

	# Hover + selected-target highlight.
	if interactive and _hover_cell.x >= 0:
		var hover_rect := Rect2(rect.position.x + col_w * _hover_cell.x, rect.position.y + row_h * _hover_cell.y, col_w, row_h)
		draw_rect(hover_rect, ZONE_HOVER)
	if not current_line.is_empty() and not current_length.is_empty():
		var lc: int = LINE_TARGETS.find(current_line)
		var lr: int = LENGTH_TARGETS.find(current_length)
		if lc >= 0 and lr >= 0:
			var target_rect := Rect2(rect.position.x + col_w * lc, rect.position.y + row_h * lr, col_w, row_h)
			draw_rect(target_rect, TARGET_MARK, false, 2.5)
			var center := target_rect.get_center()
			draw_arc(center, 7.0, 0, TAU, 20, TARGET_MARK, 2.0, true)
			draw_line(center - Vector2(10, 0), center + Vector2(10, 0), TARGET_MARK, 2.0)
			draw_line(center - Vector2(0, 10), center + Vector2(0, 10), TARGET_MARK, 2.0)

	# Creases (batting crease near the bottom, bowling crease at the top).
	draw_line(Vector2(rect.position.x, rect.position.y + rect.size.y * 0.08), Vector2(rect.end.x, rect.position.y + rect.size.y * 0.08), CREASE, 1.5)
	draw_line(Vector2(rect.position.x, rect.end.y - rect.size.y * 0.08), Vector2(rect.end.x, rect.end.y - rect.size.y * 0.08), CREASE, 1.5)
	_draw_stumps(Vector2(rect.get_center().x, rect.position.y), -1.0)
	_draw_stumps(Vector2(rect.get_center().x, rect.end.y), 1.0)

	# Real pitch marks from actual deliveries this innings, coloured by
	# outcome — the same normalised (x, y) space match_stats_canvas.gd's
	# PITCH MAP tab already uses, so a wicket/boundary reads consistently
	# everywhere in the app.
	var recent: Array = bowling_events.slice(max(0, bowling_events.size() - 18), bowling_events.size())
	for i in range(recent.size()):
		var event: Dictionary = recent[i]
		var point := Vector2(rect.position.x + float(event.get("x", 0.5)) * rect.size.x,
			rect.position.y + float(event.get("y", 0.5)) * rect.size.y)
		var wicket: bool = bool(event.get("wicket", false))
		var runs := int(event.get("runs", 0))
		var colour: Color = Color("#c33a2e") if wicket else (Color("#c9982b") if runs in [4, 6] else Color("#eef5f0"))
		var is_last: bool = i == recent.size() - 1
		var alpha: float = 1.0 if is_last else lerp(0.25, 0.7, float(i) / max(1.0, float(recent.size() - 1)))
		colour.a = alpha
		draw_circle(point, 5.0 if is_last else 3.5, colour, true, -1.0, true)


func _draw_stumps(base: Vector2, direction: float) -> void:
	for i in range(-1, 2):
		draw_line(base + Vector2(i * 5, 0), base + Vector2(i * 5, 12.0 * direction), STUMPS, 2.0, true)


func _gui_input(event: InputEvent) -> void:
	if not interactive:
		return
	if event is InputEventMouseMotion:
		var cell := _cell_at(event.position)
		if cell != _hover_cell:
			_hover_cell = cell
			queue_redraw()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		var cell := _cell_at(event.position)
		if cell.x >= 0:
			current_line = LINE_TARGETS[cell.x]
			current_length = LENGTH_TARGETS[cell.y]
			queue_redraw()
			target_chosen.emit(current_line, current_length)


func _cell_at(point: Vector2) -> Vector2i:
	var rect := _pitch_rect()
	if not rect.has_point(point):
		return Vector2i(-1, -1)
	var local := point - rect.position
	var col := int(clampf(floor(local.x / (rect.size.x / 4.0)), 0, 3))
	var row := int(clampf(floor(local.y / (rect.size.y / 4.0)), 0, 3))
	return Vector2i(col, row)
