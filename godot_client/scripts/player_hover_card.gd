class_name PlayerHoverCard
extends PanelContainer
## Compact player summary shown near the cursor on row hover — ports
## ui/widgets/quick_card.py's QuickCard exactly (name/role/age/nationality,
## overall, form/fitness/morale bars) so both clients behave the same way.
## Only shown for rows that look like a player (have "overall" and "role"
## keys) — non-player tables (Facilities, Finances, ...) never trigger it.

@onready var name_label: Label = $Margin/Box/Header/Name
@onready var overall_label: Label = $Margin/Box/Header/Overall
@onready var meta_label: Label = $Margin/Box/Meta
@onready var form_bar: Control = $Margin/Box/FormRow/Bar
@onready var form_value: Label = $Margin/Box/FormRow/Value
@onready var fitness_bar: Control = $Margin/Box/FitnessRow/Bar
@onready var fitness_value: Label = $Margin/Box/FitnessRow/Value
@onready var morale_bar: Control = $Margin/Box/MoraleRow/Bar
@onready var morale_value: Label = $Margin/Box/MoraleRow/Value

const SIZE := Vector2(240, 140)


func _ready() -> void:
	visible = false
	custom_minimum_size = SIZE
	size = SIZE
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var box := StyleBoxFlat.new()
	box.bg_color = AppTheme.CARD
	box.border_color = AppTheme.BORDER
	box.set_border_width_all(1)
	box.set_corner_radius_all(8)
	box.content_margin_left = 12
	box.content_margin_right = 12
	box.content_margin_top = 10
	box.content_margin_bottom = 10
	add_theme_stylebox_override("panel", box)
	name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	name_label.add_theme_font_size_override("font_size", 15)
	meta_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	meta_label.add_theme_font_size_override("font_size", 11)


## Only rows that look like a player (has "overall") get a hover card.
static func is_player_row(row_data: Dictionary) -> bool:
	return row_data.has("overall") and row_data.has("role")


func show_for(row_data: Dictionary, screen_position: Vector2, screen_size: Vector2) -> void:
	name_label.text = str(row_data.get("name", "—"))
	# row_data holds the raw IPC values (JSON numbers arrive as float, e.g.
	# 92.0) rather than the already-formatted display strings the table
	# cells show — int() truncates a float/int Variant directly, no string
	# round-trip needed (an earlier is_valid_int() check on str(92.0) here
	# always failed since that string contains a decimal point).
	var overall := int(row_data.get("overall", 50))
	overall_label.text = str(overall)
	overall_label.add_theme_color_override("font_color", AppTheme.attribute_colour(overall))
	meta_label.text = "%s • %s yrs • %s" % [row_data.get("role", "—"), JsonFormat.value(row_data.get("age", "—")), row_data.get("nationality", "—")]

	var mental: Dictionary = row_data.get("mental", {}) if row_data.get("mental") is Dictionary else {}
	_set_bar(form_bar, form_value, int(row_data.get("form", 50)))
	_set_bar(fitness_bar, fitness_value, int(mental.get("fitness", 50)))
	_set_bar(morale_bar, morale_value, int(mental.get("morale", 50)))

	# Clamp so the card never renders off the right/bottom edge of the
	# viewport, mirroring QuickCard.draw()'s bounds.clamp behaviour.
	var pos := screen_position + Vector2(18, 14)
	if pos.x + SIZE.x > screen_size.x - 8:
		pos.x = screen_position.x - SIZE.x - 18
	if pos.y + SIZE.y > screen_size.y - 8:
		pos.y = screen_position.y - SIZE.y - 12
	position = pos
	visible = true


func hide_card() -> void:
	visible = false


func _set_bar(bar: Control, value_label: Label, value: int) -> void:
	for child in bar.get_children():
		child.queue_free()
	var track_width: float = bar.custom_minimum_size.x
	var track := ColorRect.new()
	track.color = AppTheme.BORDER
	track.position = Vector2(0, 5)
	track.size = Vector2(track_width, 5)
	bar.add_child(track)
	var fill := ColorRect.new()
	fill.color = AppTheme.attribute_colour(value)
	fill.position = Vector2(0, 5)
	fill.size = Vector2(clampf(value / 100.0, 0.0, 1.0) * track_width, 5)
	bar.add_child(fill)
	value_label.text = str(value)
