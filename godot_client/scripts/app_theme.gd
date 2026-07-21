class_name AppTheme
extends RefCounted
## Ports the pygame client's "Test at Dusk" design tokens
## (cricket_manager/src/views/theme.py) to a Godot Theme resource, so both
## clients share one visual identity instead of the Godot client using the
## engine's unstyled default gray theme. Built in code (not a hand-authored
## .tres) so the palette stays a single source of truth that's easy to read
## and diff.

const BACKGROUND := Color("#12100e")
const SURFACE := Color("#1a1714")
const CARD := Color("#221e1a")
const ROW_ALT := Color("#2b2620")
const HEADER_GREEN := Color("#4caf6d")
const ACCENT := Color("#7fb8d8")
const TEXT_PRIMARY := Color("#f4efe8")
const TEXT_SECONDARY := Color("#a79e92")
const TEXT_MUTED := Color("#5a5248")
const BORDER := Color("#3a332b")
const GOLD := Color("#e0a63c")
const DANGER := Color("#d6493f")
const HOVER := Color("#2b2620")
const ACTIVE := Color("#342e26")
const PURPLE := Color("#a685d8")

const ROLE_COLOURS := {
	"Batsman": ACCENT,
	"Bowler": HEADER_GREEN,
	"Wicketkeeper": GOLD,
	"All-Rounder": PURPLE,
}


## The colour for a role/status pill badge — a small fixed palette (mirrors
## the reference cricket-manager screenshots' coloured role tags) with a
## neutral fallback for values outside the known set (e.g. blank cells).
static func role_colour(value: String) -> Color:
	return ROLE_COLOURS.get(value, TEXT_MUTED)

static var _font: FontFile = load("res://assets/fonts/Inter-VariableFont_opsz,wght.ttf")


static func _panel_box(bg: Color, border: Color = BORDER, radius: int = 8, border_width: int = 1) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = bg
	box.set_corner_radius_all(radius)
	box.set_border_width_all(border_width)
	box.border_color = border
	return box


static func _button_box(bg: Color, border: Color) -> StyleBoxFlat:
	var box := _panel_box(bg, border, 6, 1)
	box.content_margin_left = 14
	box.content_margin_right = 14
	box.content_margin_top = 6
	box.content_margin_bottom = 6
	return box


static func build() -> Theme:
	var theme := Theme.new()
	theme.default_font = _font
	theme.default_font_size = 14

	theme.set_color("font_color", "Label", TEXT_PRIMARY)

	var button_normal := _button_box(CARD, BORDER)
	var button_hover := _button_box(ROW_ALT, ACCENT)
	var button_pressed := _button_box(ACTIVE, GOLD)
	theme.set_stylebox("normal", "Button", button_normal)
	theme.set_stylebox("hover", "Button", button_hover)
	theme.set_stylebox("pressed", "Button", button_pressed)
	theme.set_stylebox("focus", "Button", button_hover)
	theme.set_color("font_color", "Button", TEXT_PRIMARY)
	theme.set_color("font_hover_color", "Button", TEXT_PRIMARY)
	theme.set_color("font_pressed_color", "Button", GOLD)

	var panel_box := _panel_box(SURFACE, BORDER, 10, 1)
	theme.set_stylebox("panel", "PanelContainer", panel_box)
	theme.set_stylebox("panel", "Panel", panel_box)

	var scroll_panel := _panel_box(BACKGROUND, BORDER, 0, 0)
	theme.set_stylebox("panel", "ScrollContainer", scroll_panel)

	return theme


## A nav-rail button: flat until active, then filled with the accent colour
## — mirrors FM's left-rail highlight for the current section.
static func style_nav_button(button: Button, active: bool) -> void:
	if active:
		button.add_theme_stylebox_override("normal", _panel_box(ACTIVE, GOLD, 6, 1))
		button.add_theme_stylebox_override("hover", _panel_box(ACTIVE, GOLD, 6, 1))
		button.add_theme_color_override("font_color", GOLD)
		button.add_theme_color_override("font_hover_color", GOLD)
	else:
		var flat := StyleBoxFlat.new()
		flat.bg_color = Color(0, 0, 0, 0)
		flat.content_margin_left = 14
		flat.content_margin_right = 14
		flat.content_margin_top = 6
		flat.content_margin_bottom = 6
		button.add_theme_stylebox_override("normal", flat)
		button.add_theme_stylebox_override("hover", _panel_box(HOVER, BORDER, 6, 1))
		button.add_theme_color_override("font_color", TEXT_SECONDARY)
		button.add_theme_color_override("font_hover_color", TEXT_PRIMARY)
