class_name AppTheme
extends RefCounted
## v0.84.0: warm "sunlit ground" light theme, replacing the prior "Test at
## Dusk" dark palette outright (no toggle — see docs/CURRENT.md's Decisions
## made). Still the single design-token source built into a Godot Theme
## resource in code, not a hand-authored .tres, so the palette stays one
## file that's easy to read and diff. Every named constant below keeps its
## old semantic role (BACKGROUND is still the deepest layer, GOLD is still
## the accent/active colour, etc.) — only the actual hex values changed, so
## every screen that already references AppTheme.<TOKEN> repaints for free.

const BACKGROUND := Color("#efe7d3")
const SURFACE := Color("#f8f3e6")
const CARD := Color("#fffdf8")
const ROW_ALT := Color("#f1e9d6")
const HEADER_GREEN := Color("#2e8b52")
const ACCENT := Color("#2f7ab0")
const TEXT_PRIMARY := Color("#2c2418")
const TEXT_SECONDARY := Color("#6b5c46")
const TEXT_MUTED := Color("#7a6a52")
const BORDER := Color("#ddd0b0")
const GOLD := Color("#b8791f")
const DANGER := Color("#b83a2e")
const HOVER := Color("#eee1c2")
const ACTIVE := Color("#fbe9c0")
const PURPLE := Color("#7c53a5")
## A neutral mid-tone for the "solid, unremarkable" attribute tier — kept
## distinct from TEXT_PRIMARY (unlike the old dark theme, which reused its
## near-white text colour as a bar-fill tone; that doesn't survive a
## light/dark repaint since text colour and a "steady" tier colour are
## different concerns that happened to look similar only in the dark theme).
const NEUTRAL := Color("#8a7a5c")

const SPACING_XS := 4
const SPACING_SM := 8
const SPACING_MD := 16
const SPACING_LG := 24
const SPACING_XL := 32

const ROLE_COLOURS := {
	"Batsman": ACCENT,
	"Bowler": HEADER_GREEN,
	"Wicketkeeper": GOLD,
	"All-Rounder": PURPLE,
}


## FM-style attribute tiers (mirrors src/views/theme.py's attribute_colour):
## red (weak) -> amber (modest) -> neutral (solid) -> green (strong) ->
## gold (elite), used for 0-100 stats like form/morale bar meters.
static func attribute_colour(value: float) -> Color:
	if value >= 90: return Color("#d99a1f")
	if value >= 75: return HEADER_GREEN
	if value >= 60: return NEUTRAL
	if value >= 40: return GOLD
	return DANGER


## The colour for a role/status pill badge — a small fixed palette (mirrors
## the reference cricket-manager screenshots' coloured role tags) with a
## neutral fallback for values outside the known set (e.g. blank cells).
static func role_colour(value: String) -> Color:
	return ROLE_COLOURS.get(value, TEXT_MUTED)

static var _font: FontFile = load("res://assets/fonts/Inter-VariableFont_opsz,wght.ttf")

## Mirrors cricket_manager/ui/widgets/country_flag.py's ALIASES + ISO_CODES
## exactly, so the same "nationality" string on a player record maps to the
## same flag PNG in both clients (bundled Flagpedia set, public domain).
const FLAG_ALIASES := {
	"English": "England", "Australian": "Australia", "Indian": "India", "Pakistani": "Pakistan",
	"South African": "South Africa", "New Zealander": "New Zealand", "West Indian": "West Indies",
	"Sri Lankan": "Sri Lanka", "Bangladeshi": "Bangladesh", "Afghan": "Afghanistan",
	"Zimbabwean": "Zimbabwe", "Irish": "Ireland", "Dutch": "Netherlands", "Scottish": "Scotland",
	"American": "USA", "Emirati": "UAE", "Nepalese": "Nepal", "Omani": "Oman",
	"Namibian": "Namibia", "Papua New Guinean": "Papua New Guinea",
}
const FLAG_ISO_CODES := {
	"England": "gb-eng", "Australia": "au", "India": "in", "Pakistan": "pk",
	"South Africa": "za", "New Zealand": "nz", "Sri Lanka": "lk", "Bangladesh": "bd",
	"Afghanistan": "af", "Zimbabwe": "zw", "Ireland": "ie", "Netherlands": "nl",
	"Scotland": "gb-sct", "USA": "us", "UAE": "ae", "Nepal": "np", "Oman": "om",
	"Namibia": "na", "Papua New Guinea": "pg",
}
static var _flag_cache: Dictionary = {}


## The flag texture for a player's "nationality" field, or null for
## nationalities with no ISO flag (e.g. "West Indies" — a cricket entity,
## not a country) so the caller can fall back to a drawn placeholder.
static func flag_texture(nationality: String) -> Texture2D:
	var country: String = FLAG_ALIASES.get(nationality, nationality)
	var code = FLAG_ISO_CODES.get(country)
	if code == null:
		return null
	if _flag_cache.has(code):
		return _flag_cache[code]
	var path := "res://assets/images/flags/%s.png" % code
	if not ResourceLoader.exists(path):
		return null
	var texture: Texture2D = load(path)
	_flag_cache[code] = texture
	return texture


## A small horizontal progress-bar meter (track + tier-coloured fill + the
## raw number alongside) — used for every 0-100 stat shown as a bar
## (attributes, form/fitness/morale). Previously duplicated three times
## (table_screen.gd's _make_bar, player_hover_card.gd's _set_bar,
## player_profile_modal.gd's _attribute_row) with three copies to keep in
## sync on every palette change; one shared builder now.
static func make_bar_meter(track_width: float, value: float, value_font_size: int = 11,
						  value_colour: Color = TEXT_SECONDARY) -> Control:
	var wrap := Control.new()
	wrap.custom_minimum_size = Vector2(track_width + 34, 18)
	var track := ColorRect.new()
	track.color = BORDER
	track.position = Vector2(0, 7)
	track.size = Vector2(track_width, 4)
	wrap.add_child(track)
	var fill := ColorRect.new()
	fill.color = attribute_colour(value)
	fill.position = Vector2(0, 7)
	fill.size = Vector2(clampf(value / 100.0, 0.0, 1.0) * track_width, 4)
	wrap.add_child(fill)
	var label := Label.new()
	label.text = str(int(value))
	label.add_theme_font_size_override("font_size", value_font_size)
	label.add_theme_color_override("font_color", value_colour)
	label.position = Vector2(track_width + 6, -2)
	wrap.add_child(label)
	return wrap


## A small pill-shaped status chip (e.g. "FORM 72") — mirrors the
## reference screenshots' Happiness/Fitness/Form/Discipline chip row.
static func make_status_chip(caption: String, value: int) -> PanelContainer:
	var chip := PanelContainer.new()
	var box := _panel_box(CARD, attribute_colour(value), 8, 1)
	box.content_margin_left = 10
	box.content_margin_right = 10
	box.content_margin_top = 4
	box.content_margin_bottom = 4
	chip.add_theme_stylebox_override("panel", box)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	var caption_label := Label.new()
	caption_label.text = caption
	caption_label.add_theme_font_size_override("font_size", 10)
	caption_label.add_theme_color_override("font_color", TEXT_MUTED)
	row.add_child(caption_label)
	var value_label := Label.new()
	value_label.text = str(value)
	value_label.add_theme_font_size_override("font_size", 13)
	value_label.add_theme_color_override("font_color", attribute_colour(value))
	row.add_child(value_label)
	chip.add_child(row)
	return chip


## v4.19.0: optional content_margin — 0 by default (every existing call
## site keeps its exact prior behaviour), but any card-style panel that
## actually contains text near its edge should pass one explicitly rather
## than relying on the Theme's default "panel" stylebox, which only
## applies to a bare PanelContainer with NO per-instance override —
## every one of these _panel_box()-built styleboxes IS such an override,
## so the Theme-level fix (also v4.18.0) never reached them. This was the
## real reason the "text touching card borders" bug reportedly wasn't
## actually fixed everywhere: the Theme default and this shared factory
## are two entirely separate code paths, and most real cards in the app
## go through this one, not the Theme fallback.
static func _panel_box(bg: Color, border: Color = BORDER, radius: int = 8, border_width: int = 1,
					   content_margin: float = 0.0) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = bg
	box.set_corner_radius_all(radius)
	box.set_border_width_all(border_width)
	box.border_color = border
	if content_margin > 0.0:
		box.content_margin_left = content_margin
		box.content_margin_right = content_margin
		box.content_margin_top = content_margin * 0.85
		box.content_margin_bottom = content_margin * 0.85
	return box


static func make_card(elevated: bool = false) -> StyleBoxFlat:
	var box := _panel_box(CARD, BORDER, 10, 1, 14.0)
	if elevated:
		box.shadow_color = Color(0, 0, 0, 0.08)
		box.shadow_size = 4
		box.shadow_offset = Vector2(0, 2)
	return box


static func make_section_header() -> PanelContainer:
	var panel := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.bg_color = ACTIVE
	box.set_corner_radius_all(0)
	box.set_border_width_all(0)
	box.content_margin_left = 12
	box.content_margin_right = 12
	box.content_margin_top = 6
	box.content_margin_bottom = 6
	panel.add_theme_stylebox_override("panel", box)
	return panel


static func make_gold_accent_line() -> ColorRect:
	var line := ColorRect.new()
	line.color = GOLD
	line.custom_minimum_size = Vector2(0, 2)
	return line


static func style_tab_button(button: Button, active: bool) -> void:
	if active:
		button.add_theme_stylebox_override("normal", _panel_box(Color(0, 0, 0, 0), Color(0, 0, 0, 0), 0, 0))
		button.add_theme_stylebox_override("hover", _panel_box(Color(0, 0, 0, 0), Color(0, 0, 0, 0), 0, 0))
		button.add_theme_color_override("font_color", GOLD)
		button.add_theme_color_override("font_hover_color", GOLD)
		var underline := _panel_box(GOLD, GOLD, 0, 0)
		underline.set_border_width_all(0)
		underline.border_width_bottom = 2
		underline.content_margin_bottom = 4
		button.add_theme_stylebox_override("focus", underline)
	else:
		var flat := StyleBoxFlat.new()
		flat.bg_color = Color(0, 0, 0, 0)
		flat.content_margin_left = 10
		flat.content_margin_right = 10
		flat.content_margin_top = 6
		flat.content_margin_bottom = 6
		button.add_theme_stylebox_override("normal", flat)
		button.add_theme_stylebox_override("hover", _panel_box(HOVER, Color(0, 0, 0, 0), 4, 0))
		button.add_theme_color_override("font_color", TEXT_MUTED)
		button.add_theme_color_override("font_hover_color", TEXT_PRIMARY)


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

	# v4.18.0: every PanelContainer that doesn't wrap its own content in a
	# MarginContainer (most of them — New Game Setup's MANAGER PROFILE/GAME
	# SETUP/STARTING LEAGUE cards, and others across the app) previously
	# fell through to _panel_box()'s zero content_margin default, so
	# headers/fields sat flush against the card border on every one of
	# those screens. This is the single shared default every PanelContainer
	# inherits unless it overrides its own stylebox, so fixing it here
	# fixes it everywhere at once rather than screen-by-screen.
	var panel_box := _panel_box(SURFACE, BORDER, 10, 1)
	panel_box.content_margin_left = 16
	panel_box.content_margin_right = 16
	panel_box.content_margin_top = 14
	panel_box.content_margin_bottom = 14
	theme.set_stylebox("panel", "PanelContainer", panel_box)
	theme.set_stylebox("panel", "Panel", panel_box)

	var scroll_panel := _panel_box(BACKGROUND, BORDER, 0, 0)
	theme.set_stylebox("panel", "ScrollContainer", scroll_panel)

	# LineEdit/OptionButton previously fell through to the engine's default
	# grey box — never styled since Theme.build() only covered Label/
	# Button/PanelContainer/ScrollContainer — a visible sore thumb on New
	# Game Setup's manager-name field once every other control was styled.
	var field_box := _panel_box(CARD, BORDER, 6, 1)
	field_box.content_margin_left = 10
	field_box.content_margin_right = 10
	field_box.content_margin_top = 4
	field_box.content_margin_bottom = 4
	var field_focus := _panel_box(CARD, ACCENT, 6, 1)
	field_focus.content_margin_left = 10
	field_focus.content_margin_right = 10
	field_focus.content_margin_top = 4
	field_focus.content_margin_bottom = 4
	theme.set_stylebox("normal", "LineEdit", field_box)
	theme.set_stylebox("focus", "LineEdit", field_focus)
	theme.set_stylebox("read_only", "LineEdit", field_box)
	theme.set_color("font_color", "LineEdit", TEXT_PRIMARY)
	theme.set_color("font_placeholder_color", "LineEdit", TEXT_MUTED)
	theme.set_stylebox("normal", "OptionButton", field_box)
	theme.set_stylebox("hover", "OptionButton", _panel_box(ROW_ALT, ACCENT, 6, 1))
	theme.set_stylebox("pressed", "OptionButton", _panel_box(ACTIVE, GOLD, 6, 1))
	theme.set_stylebox("focus", "OptionButton", field_focus)
	theme.set_color("font_color", "OptionButton", TEXT_PRIMARY)
	theme.set_color("font_hover_color", "OptionButton", TEXT_PRIMARY)

	return theme


## A nav-rail button: flat until active, then filled with the accent colour
## — mirrors FM's left-rail highlight for the current section.
static func style_nav_button(button: Button, active: bool) -> void:
	if active:
		var active_box := StyleBoxFlat.new()
		active_box.bg_color = ACTIVE
		active_box.set_corner_radius_all(6)
		active_box.set_border_width_all(0)
		active_box.content_margin_left = 14
		active_box.content_margin_right = 14
		active_box.content_margin_top = 8
		active_box.content_margin_bottom = 8
		button.add_theme_stylebox_override("normal", active_box)
		button.add_theme_stylebox_override("hover", active_box)
		button.add_theme_color_override("font_color", GOLD)
		button.add_theme_color_override("font_hover_color", GOLD)
		button.add_theme_font_size_override("font_size", 13)
	else:
		var flat := StyleBoxFlat.new()
		flat.bg_color = Color(0, 0, 0, 0)
		flat.content_margin_left = 14
		flat.content_margin_right = 14
		flat.content_margin_top = 8
		flat.content_margin_bottom = 8
		button.add_theme_stylebox_override("normal", flat)
		button.add_theme_stylebox_override("hover", _panel_box(HOVER, Color(0, 0, 0, 0), 6, 0))
		button.add_theme_color_override("font_color", TEXT_SECONDARY)
		button.add_theme_color_override("font_hover_color", TEXT_PRIMARY)
		button.add_theme_font_size_override("font_size", 13)
