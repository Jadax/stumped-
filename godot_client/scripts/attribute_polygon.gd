class_name AttributePolygon
extends Control
## Draws an FM-style attribute polygon (radar chart) for player attributes.
## Shows batting, bowling, fielding, mental, and physical attributes as
## a pentagon with each axis representing an attribute category.

var attributes: Dictionary = {}
var player_name: String = ""


func set_attributes(attrs: Dictionary, name: String = "") -> void:
	attributes = attrs
	player_name = name
	queue_redraw()


func _draw() -> void:
	if attributes.is_empty():
		_draw_centered_label("No attributes available.")
		return
	var centre := size / 2.0
	var radius: float = min(size.x, size.y) / 2.0 - 24.0
	if radius <= 0:
		return
	# Define the 5 axes: Batting, Bowling, Fielding, Mental, Physical
	var axis_names := ["Batting", "Bowling", "Fielding", "Mental", "Physical"]
	var axis_keys := ["batting", "bowling", "fielding", "mental", "physical"]
	var axis_count := axis_names.size()
	# Calculate average for each category
	var values := []
	for key in axis_keys:
		var attrs: Dictionary = attributes.get(key, {}) if attributes.get(key) is Dictionary else {}
		if attrs.is_empty():
			values.append(0.0)
		else:
			var total := 0.0
			for attr_key in attrs:
				total += float(attrs[attr_key])
			values.append(total / attrs.size())
	# Draw the polygon background (grey pentagon)
	var bg_points := PackedVector2Array()
	for i in range(axis_count):
		var angle: float = TAU * i / axis_count - PI / 2.0
		bg_points.append(centre + Vector2(cos(angle), sin(angle)) * radius)
	draw_colored_polygon(bg_points, Color(0.2, 0.2, 0.2, 0.3))
	# Draw the polygon outline
	draw_polyline(bg_points + PackedVector2Array([bg_points[0]]), AppTheme.BORDER, 1.5)
	# Draw axis lines and labels
	for i in range(axis_count):
		var angle: float = TAU * i / axis_count - PI / 2.0
		var end := centre + Vector2(cos(angle), sin(angle)) * radius
		draw_line(centre, end, AppTheme.BORDER, 1.0)
		# Draw axis label
		var label_pos := centre + Vector2(cos(angle), sin(angle)) * (radius + 14.0)
		var font := ThemeDB.fallback_font
		var text_size := font.get_string_size(axis_names[i], HORIZONTAL_ALIGNMENT_CENTER, -1, 10)
		draw_string(font, label_pos - text_size / 2.0, axis_names[i], HORIZONTAL_ALIGNMENT_LEFT, -1, 10, AppTheme.TEXT_PRIMARY)
	# Draw the player's attribute polygon
	var player_points := PackedVector2Array()
	for i in range(axis_count):
		var angle: float = TAU * i / axis_count - PI / 2.0
		var normalized := clampf(values[i] / 100.0, 0.0, 1.0)
		player_points.append(centre + Vector2(cos(angle), sin(angle)) * radius * normalized)
	# Draw filled polygon
	draw_colored_polygon(player_points, Color(AppTheme.ACCENT.r, AppTheme.ACCENT.g, AppTheme.ACCENT.b, 0.4))
	# Draw polygon outline
	draw_polyline(player_points + PackedVector2Array([player_points[0]]), AppTheme.ACCENT, 2.0)
	# Draw dots at each vertex
	for point in player_points:
		draw_circle(point, 4.0, AppTheme.ACCENT)
	# Draw player name at top
	if not player_name.is_empty():
		var font := ThemeDB.fallback_font
		var text_size := font.get_string_size(player_name, HORIZONTAL_ALIGNMENT_CENTER, -1, 12)
		draw_string(font, Vector2(centre.x - text_size.x / 2.0, 14.0), player_name, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, AppTheme.TEXT_PRIMARY)


func _draw_centered_label(_text: String) -> void:
	var font := ThemeDB.fallback_font
	var text_size := font.get_string_size(_text, HORIZONTAL_ALIGNMENT_CENTER, -1, 13)
	draw_string(font, size / 2.0 - text_size / 2.0, _text, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, AppTheme.TEXT_MUTED)
