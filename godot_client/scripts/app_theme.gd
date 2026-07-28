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
