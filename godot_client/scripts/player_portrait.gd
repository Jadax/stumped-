class_name PlayerPortrait
extends Control
## Deterministic, original player portraits — no photographs or third-party
## likenesses. Ports the visual design of cricket_manager/src/utilities/
## player_portraits.py's PlayerPortraitGenerator (skin-tone table, hair/
## style variety, age-based grey hair/wrinkles/beard chance, kit colour)
## to Godot's native vector drawing so it renders crisp and anti-aliased
## at any size, instead of pygame's software-rasterized 128px canvas —
## this is the concrete fix for "player profile pictures... very pixely".
## Same custom-drawn Control pattern as nav_icon.gd: set params, redraw.

const TONE_RANGES := {
	"england": [Color8(238, 196, 164), Color8(177, 121, 91)],
	"australia": [Color8(236, 190, 151), Color8(168, 109, 78)],
	"new zealand": [Color8(225, 175, 139), Color8(153, 101, 73)],
	"india": [Color8(196, 132, 86), Color8(104, 63, 42)],
	"pakistan": [Color8(202, 143, 96), Color8(107, 68, 46)],
	"bangladesh": [Color8(190, 126, 80), Color8(100, 61, 40)],
	"sri lanka": [Color8(183, 115, 72), Color8(88, 51, 35)],
	"south africa": [Color8(209, 154, 111), Color8(72, 43, 31)],
	"west indies": [Color8(132, 82, 58), Color8(54, 33, 27)],
	"afghanistan": [Color8(196, 137, 91), Color8(101, 62, 42)],
	"zimbabwe": [Color8(145, 89, 59), Color8(58, 35, 28)],
}
const HAIR_PALETTE := [Color8(25, 20, 18), Color8(46, 31, 23), Color8(78, 49, 31), Color8(126, 86, 52), Color8(170, 132, 84)]
const KIT_PALETTE := [Color8(46, 160, 67), Color8(42, 105, 184), Color8(190, 59, 66), Color8(214, 154, 27), Color8(92, 73, 176)]
const EYE_COLOURS := [Color8(43, 30, 24), Color8(57, 72, 51), Color8(48, 62, 82)]
const DARK_HAIR_NATIONS := ["india", "pakistan", "bangladesh", "sri lanka", "south africa", "west indies", "afghanistan", "zimbabwe"]

var _nationality: String = "England"
var _age: int = 25
var _player_id: int = 0


static func _tone_key(nationality: String) -> String:
	var value := nationality.to_lower().replace("english", "england").replace("australian", "australia")
	for candidate in TONE_RANGES:
		if value.find(candidate) != -1:
			return candidate
	return "england"


static func _mix(a: Color, b: Color, amount: float) -> Color:
	return a.lerp(b, amount)


func set_player(nationality: String, age: int, player_id: int) -> void:
	_nationality = nationality
	_age = age
	_player_id = player_id
	queue_redraw()


func _ellipse_points(center: Vector2, radius: Vector2, segments: int = 28) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for i in range(segments):
		var angle := TAU * i / segments
		pts.append(center + Vector2(cos(angle) * radius.x, sin(angle) * radius.y))
	return pts


func _draw_ellipse_fill(center: Vector2, radius: Vector2, color: Color, segments: int = 28) -> void:
	if radius.x <= 0 or radius.y <= 0:
		return
	draw_colored_polygon(_ellipse_points(center, radius, segments), color)


func _rng() -> RandomNumberGenerator:
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("portrait-godot:%d:%s:%d" % [_player_id, _nationality, _age])
	return rng


func _draw() -> void:
	var s: float = min(size.x, size.y) / 128.0
	if s <= 0:
		return
	var u := func(v: float) -> float: return v * s
	var rng := _rng()

	var key := _tone_key(_nationality)
	var tones: Array = TONE_RANGES.get(key, TONE_RANGES["england"])
	var skin: Color = _mix(tones[0], tones[1], rng.randf())
	var shade: Color = _mix(skin, Color8(38, 25, 23), .22)
	var highlight: Color = _mix(skin, Color8(255, 238, 216), .18)
	var dark_bias: float = .78 if key in DARK_HAIR_NATIONS else .48
	var hair: Color = HAIR_PALETTE[rng.randi_range(0, 2)] if rng.randf() < dark_bias else HAIR_PALETTE[rng.randi_range(0, 4)]
	if _age >= 34 and rng.randf() < min(.78, (_age - 30) / 18.0):
		hair = _mix(hair, Color8(174, 174, 169), rng.randf_range(.25, .72))
	var kit: Color = KIT_PALETTE[rng.randi_range(0, KIT_PALETTE.size() - 1)]

	# Softly graded studio backdrop, closest in spirit to the pygame
	# version's concentric-circle vignette.
	for radius in range(62, 8, -6):
		var amount: float = (62.0 - radius) / 54.0
		var colour: Color = _mix(Color8(22, 30, 42), Color8(53, 65, 78), amount * .55)
		_draw_ellipse_fill(Vector2(u.call(64), u.call(61)), Vector2(u.call(radius), u.call(radius)), colour, 20)

	# Bust, neck, simple V collar.
	_draw_ellipse_fill(Vector2(u.call(64), u.call(120)), Vector2(u.call(56), u.call(29)), _mix(kit, Color8(10, 15, 22), .18), 24)
	_draw_ellipse_fill(Vector2(u.call(64), u.call(120)), Vector2(u.call(50), u.call(24)), kit, 24)
	draw_rect(Rect2(u.call(50), u.call(77), u.call(28), u.call(29)), shade, true)
	var collar: Color = _mix(kit, Color8(245, 245, 240), .55)
	draw_line(Vector2(u.call(50), u.call(100)), Vector2(u.call(64), u.call(112)), collar, u.call(2.2))
	draw_line(Vector2(u.call(78), u.call(100)), Vector2(u.call(64), u.call(112)), collar, u.call(2.2))

	# Jaw/face polygon (7-point silhouette, mirrors the pygame jaw shape).
	var face_w: float = rng.randf_range(55, 65)
	var face_h: float = rng.randf_range(71, 81)
	var fx: float = 64 - face_w / 2.0
	var fy: float = rng.randf_range(14, 17)
	var jaw := PackedVector2Array([
		Vector2(u.call(fx + 5), u.call(fy + 8)), Vector2(u.call(fx + face_w - 5), u.call(fy + 8)),
		Vector2(u.call(fx + face_w), u.call(fy + 43)), Vector2(u.call(fx + face_w - 11), u.call(fy + face_h - 7)),
		Vector2(u.call(64), u.call(fy + face_h)), Vector2(u.call(fx + 10), u.call(fy + face_h - 7)),
		Vector2(u.call(fx), u.call(fy + 43)),
	])
	var jaw_shadow := PackedVector2Array()
	for p in jaw:
		jaw_shadow.append(p + Vector2(u.call(2), u.call(3)))
	draw_colored_polygon(jaw_shadow, shade)
	draw_colored_polygon(jaw, skin)
	_draw_ellipse_fill(Vector2(u.call(fx - 0.5), u.call(fy + 43.5)), Vector2(u.call(5.5), u.call(11.5)), skin, 12)
	_draw_ellipse_fill(Vector2(u.call(fx + face_w - 0.5), u.call(fy + 43.5)), Vector2(u.call(5.5), u.call(11.5)), skin, 12)
	_draw_ellipse_fill(Vector2(u.call(fx + 15.5), u.call(fy + 21)), Vector2(u.call(face_w / 6.0), u.call(face_h / 4.0)), Color(highlight.r, highlight.g, highlight.b, .35), 16)

	# Layered translucent lighting planes (temple fall-off, cheek volume,
	# jaw shadow, nose highlight) — same trick as the pygame version, drawn
	# directly with alpha since Godot canvas draws already blend in order.
	_draw_ellipse_fill(Vector2(u.call(fx + face_w * .53 + face_w * .215), u.call(fy + 8 + face_h * .36)),
		Vector2(u.call(face_w * .215), u.call(face_h * .36)), Color(shade.r, shade.g, shade.b, .28), 18)
	_draw_ellipse_fill(Vector2(u.call(fx + 8 + face_w * .21), u.call(fy + 24 + face_h * .17)),
		Vector2(u.call(face_w * .21), u.call(face_h * .17)), Color(highlight.r, highlight.g, highlight.b, .23), 18)
	_draw_ellipse_fill(Vector2(u.call(fx + 9 + (face_w - 18) / 2.0), u.call(fy + face_h * .66 + face_h * .125)),
		Vector2(u.call((face_w - 18) / 2.0), u.call(face_h * .125)), Color(shade.r, shade.g, shade.b, .21), 18)

	# Fine, deterministic skin texture so large areas don't read as flat.
	for _i in range(60):
		var px: float = rng.randf_range(fx + 7, fx + face_w - 8)
		var py: float = rng.randf_range(fy + 19, fy + face_h - 9)
		var ellipse_test: float = pow((px - 64) / max(1.0, face_w * .50), 2) + pow((py - (fy + face_h * .52)) / max(1.0, face_h * .54), 2)
		if ellipse_test <= 1.0:
			var pore: Color = _mix(skin, highlight if rng.randf() < .47 else shade, rng.randf_range(.08, .18))
			_draw_ellipse_fill(Vector2(u.call(px), u.call(py)), Vector2(u.call(.5), u.call(.5)), pore, 8)

	# Hair styles are age-appropriate; 5 variants mirroring the pygame set.
	var style: int = rng.randi_range(0, 4)
	if style == 0 or style == 1:
		_draw_ellipse_fill(Vector2(u.call(fx + 1 + (face_w - 2) / 2.0), u.call(fy - 7 + 14.5)), Vector2(u.call((face_w - 2) / 2.0), u.call(14.5)), hair, 22)
		if style == 1:
			draw_rect(Rect2(u.call(fx), u.call(fy + 5), u.call(8), u.call(25)), hair, true)
	elif style == 2:
		var x := fx + 3
		while x < fx + face_w - 2:
			_draw_ellipse_fill(Vector2(u.call(x), u.call(fy + rng.randf_range(0, 8))), Vector2(u.call(7), u.call(7)), hair, 12)
			x += 6
	elif style == 3:
		var hair_poly := PackedVector2Array([
			Vector2(u.call(fx + 1), u.call(fy + 20)), Vector2(u.call(fx + 8), u.call(fy - 5)),
			Vector2(u.call(fx + face_w - 4), u.call(fy)), Vector2(u.call(fx + face_w), u.call(fy + 20)),
			Vector2(u.call(64), u.call(fy + 10)),
		])
		draw_colored_polygon(hair_poly, hair)
	else:
		draw_arc(Vector2(u.call(fx + 3 + (face_w - 6) / 2.0), u.call(fy - 2 + 15)), u.call((face_w - 6) / 2.0), 3.1, 6.2, 16, hair, u.call(7))

	# Eyes: whites, iris, pupil, highlight, eyelid arc, eyebrow.
	var eye_y: float = fy + 35
	var eye_dx: float = rng.randf_range(12, 15)
	var eye_colour: Color = EYE_COLOURS[rng.randi_range(0, EYE_COLOURS.size() - 1)]
	for ex in [64 - eye_dx, 64 + eye_dx]:
		_draw_ellipse_fill(Vector2(u.call(ex), u.call(eye_y)), Vector2(u.call(5), u.call(2.5)), _mix(Color8(242, 239, 229), skin, .18), 14)
		draw_circle(Vector2(u.call(ex), u.call(eye_y)), u.call(1.8), eye_colour)
		draw_circle(Vector2(u.call(ex), u.call(eye_y)), max(1.0, u.call(.75)), Color8(18, 18, 17))
		draw_circle(Vector2(u.call(ex - .6), u.call(eye_y - .7)), max(1.0, u.call(.3)), Color8(235, 238, 230))
		draw_arc(Vector2(u.call(ex), u.call(eye_y - .5)), u.call(6), 3.25, 6.05, 10, shade, u.call(1))
		draw_line(Vector2(u.call(ex - 6), u.call(eye_y - 7)), Vector2(u.call(ex + 5), u.call(eye_y - 7)), _mix(hair, skin, .18), u.call(1.4))

	# Nose and mouth.
	var nose_x: float = 61 + rng.randf_range(0, 6)
	draw_line(Vector2(u.call(64), u.call(eye_y + 5)), Vector2(u.call(nose_x), u.call(eye_y + 20)), _mix(shade, skin, .22), u.call(1.2))
	draw_arc(Vector2(u.call(64.5), u.call(eye_y + 19)), u.call(5.5), .2, 2.9, 10, shade, u.call(1))
	var mouth_y: float = eye_y + 29
	var lip: Color = _mix(skin, Color8(118, 50, 50), .32)
	draw_arc(Vector2(u.call(64), u.call(mouth_y + .5)), u.call(9), .10, 3.03, 12, lip, u.call(1.2))
	draw_arc(Vector2(u.call(64), u.call(mouth_y + 2.5)), u.call(8), 3.25, 6.05, 12, _mix(lip, shade, .22), u.call(1.3))

	# Beard, age-gated probability, with light stubble texture.
	var beard_chance: float = .03 if _age < 19 else .34 if _age < 31 else .55
	if rng.randf() < beard_chance:
		var beard: Color = _mix(hair, skin, .20)
		draw_arc(Vector2(u.call(fx + 6 + (face_w - 12) / 2.0), u.call(fy + 31 + (face_h - 24) / 2.0)),
			u.call((face_w - 12) / 2.0), 3.15, 6.2, 16, beard, u.call(rng.randf_range(2, 4)))
		if rng.randf() < .58:
			draw_line(Vector2(u.call(57), u.call(mouth_y - 4)), Vector2(u.call(71), u.call(mouth_y - 4)), beard, u.call(2))
		for _i in range(35):
			var bx: float = rng.randf_range(fx + 9, fx + face_w - 10)
			var by: float = rng.randf_range(mouth_y - 4, fy + face_h - 7)
			if absf(bx - 64) > (by - mouth_y) * .55 or by > mouth_y + 6:
				_draw_ellipse_fill(Vector2(u.call(bx), u.call(by)), Vector2(u.call(.5), u.call(.5)), _mix(beard, skin, .18), 8)

	# Wrinkles at the outer eye corners, plus mouth-frame lines past 42.
	if _age >= 36:
		var wrinkle: Color = _mix(skin, Color8(86, 68, 61), .35)
		for offset in [-10, 10]:
			draw_line(Vector2(u.call(64 + offset - 4), u.call(eye_y + 8)), Vector2(u.call(64 + offset + 4), u.call(eye_y + 8)), wrinkle, u.call(1))
		if _age >= 42:
			draw_arc(Vector2(u.call(64), u.call(mouth_y + 5)), u.call(11), .2, 2.9, 12, wrinkle, u.call(1))

	# Soft edge vignette so portraits don't end abruptly in dense lists.
	for radius in range(62, 52, -2):
		var alpha: float = (62.0 - radius) / 10.0 * .22
		draw_polyline(_ellipse_points(Vector2(u.call(64), u.call(61)), Vector2(u.call(radius), u.call(radius)), 32), Color(.05, .06, .09, alpha), u.call(2), true)
