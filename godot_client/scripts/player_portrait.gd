class_name PlayerPortrait
extends Control
## Deterministic, original player portraits — no photographs or third-party
## likenesses. Ports the visual design of cricket_manager/src/utilities/
## player_portraits.py's PlayerPortraitGenerator (skin-tone table, hair/
## style variety, age-based grey hair/wrinkles/beard chance, kit colour)
## to Godot's native vector drawing so it renders crisp and anti-aliased
## at any size, instead of pygame's software-rasterized 128px canvas.
##
## v0.91.0: every major shape (jaw, hair, bust) now fills with a real
## per-vertex gradient via draw_polygon() instead of a single flat
## draw_colored_polygon() fill — a directional light model (soft highlight
## toward the upper-left, shadow toward the lower-right) replaces the old
## flat-fill-plus-a-few-translucent-overlay-ellipses approximation, so
## portraits read as shaded volumes instead of flat cartoon cutouts. Same
## custom-drawn Control pattern as nav_icon.gd: set params, redraw.

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

## Light comes from the upper-left, same convention across every shape so
## the whole portrait reads as one consistent light source.
const LIGHT_DIR := Vector2(-0.6, -0.8)

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


## Per-vertex gradient fill: each point's colour shifts toward a highlight
## or shadow tone based on how far it sits along the light direction from
## the shape's centroid — a real Gouraud-shaded fill via draw_polygon()'s
## colours array, not draw_colored_polygon()'s single flat colour.
func _shaded_colours(points: PackedVector2Array, base_colour: Color, strength: float = 0.24) -> PackedColorArray:
	var centroid := Vector2.ZERO
	for p in points:
		centroid += p
	centroid /= max(1, points.size())
	var light := LIGHT_DIR.normalized()
	var colours := PackedColorArray()
	for p in points:
		var offset: Vector2 = p - centroid
		var amount: float = 0.0
		if offset.length() > 0.001:
			amount = clampf(-offset.normalized().dot(light) * strength, -strength, strength)
		if amount >= 0.0:
			colours.append(_mix(base_colour, Color8(255, 250, 240), amount))
		else:
			colours.append(_mix(base_colour, Color8(20, 14, 12), -amount * 0.75))
	return colours


func _draw_shaded_polygon(points: PackedVector2Array, base_colour: Color, strength: float = 0.24) -> void:
	draw_polygon(points, _shaded_colours(points, base_colour, strength))


func _draw_shaded_ellipse(center: Vector2, radius: Vector2, base_colour: Color, segments: int = 28, strength: float = 0.24) -> void:
	if radius.x <= 0 or radius.y <= 0:
		return
	var points := _ellipse_points(center, radius, segments)
	draw_polygon(points, _shaded_colours(points, base_colour, strength))


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

	# Bust, neck, simple V collar — gradient-shaded so the kit reads as
	# fabric with real volume instead of a flat coloured blob.
	_draw_shaded_ellipse(Vector2(u.call(64), u.call(120)), Vector2(u.call(56), u.call(29)), _mix(kit, Color8(10, 15, 22), .18), 28, .2)
	_draw_shaded_ellipse(Vector2(u.call(64), u.call(120)), Vector2(u.call(50), u.call(24)), kit, 28, .26)
	draw_rect(Rect2(u.call(50), u.call(77), u.call(28), u.call(29)), shade, true)
	var collar: Color = _mix(kit, Color8(245, 245, 240), .55)
	draw_line(Vector2(u.call(50), u.call(100)), Vector2(u.call(64), u.call(112)), collar, u.call(2.2), true)
	draw_line(Vector2(u.call(78), u.call(100)), Vector2(u.call(64), u.call(112)), collar, u.call(2.2), true)

	# Jaw/face polygon (7-point silhouette, mirrors the pygame jaw shape),
	# now gradient-shaded per vertex instead of a flat fill + separate
	# translucent shading ellipses layered on top.
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
	_draw_shaded_polygon(jaw, skin, .26)
	_draw_shaded_ellipse(Vector2(u.call(fx - 0.5), u.call(fy + 43.5)), Vector2(u.call(5.5), u.call(11.5)), skin, 14, .2)
	_draw_shaded_ellipse(Vector2(u.call(fx + face_w - 0.5), u.call(fy + 43.5)), Vector2(u.call(5.5), u.call(11.5)), skin, 14, .2)

	# Fine, deterministic skin texture so large areas don't read as flat.
	for _i in range(60):
		var px: float = rng.randf_range(fx + 7, fx + face_w - 8)
		var py: float = rng.randf_range(fy + 19, fy + face_h - 9)
		var ellipse_test: float = pow((px - 64) / max(1.0, face_w * .50), 2) + pow((py - (fy + face_h * .52)) / max(1.0, face_h * .54), 2)
		if ellipse_test <= 1.0:
			var pore: Color = _mix(skin, highlight if rng.randf() < .47 else shade, rng.randf_range(.08, .18))
			_draw_ellipse_fill(Vector2(u.call(px), u.call(py)), Vector2(u.call(.5), u.call(.5)), pore, 8)

	# Hair styles are age-appropriate; 7 variants (5 original + 2 new for
	# v0.91.0's variety pass), each gradient-shaded like every other shape.
	var style: int = rng.randi_range(0, 6)
	if style == 0 or style == 1:
		_draw_shaded_ellipse(Vector2(u.call(fx + 1 + (face_w - 2) / 2.0), u.call(fy - 7 + 14.5)), Vector2(u.call((face_w - 2) / 2.0), u.call(14.5)), hair, 24, .3)
		if style == 1:
			draw_rect(Rect2(u.call(fx), u.call(fy + 5), u.call(8), u.call(25)), hair, true)
	elif style == 2:
		var x := fx + 3
		while x < fx + face_w - 2:
			_draw_shaded_ellipse(Vector2(u.call(x), u.call(fy + rng.randf_range(0, 8))), Vector2(u.call(7), u.call(7)), hair, 12, .28)
			x += 6
	elif style == 3:
		var hair_poly := PackedVector2Array([
			Vector2(u.call(fx + 1), u.call(fy + 20)), Vector2(u.call(fx + 8), u.call(fy - 5)),
			Vector2(u.call(fx + face_w - 4), u.call(fy)), Vector2(u.call(fx + face_w), u.call(fy + 20)),
			Vector2(u.call(64), u.call(fy + 10)),
		])
		_draw_shaded_polygon(hair_poly, hair, .3)
	elif style == 4:
		draw_arc(Vector2(u.call(fx + 3 + (face_w - 6) / 2.0), u.call(fy - 2 + 15)), u.call((face_w - 6) / 2.0), 3.1, 6.2, 16, hair, u.call(7), true)
	elif style == 5:
		# Short, cropped, textured — a scatter of small gradient tufts
		# hugging the scalp rather than one smooth dome.
		var tx := fx + 2
		while tx < fx + face_w - 1:
			_draw_shaded_ellipse(Vector2(u.call(tx), u.call(fy - 2 + rng.randf_range(0, 5))), Vector2(u.call(4.5), u.call(9)), hair, 10, .32)
			tx += 4.5
	else:
		# Long with a side part — an asymmetric swept dome (two offset
		# gradient-shaded ellipses, guaranteed simple/convex so triangulation
		# never fails, unlike a hand-built concave polygon) rather than a
		# centred dome, mirroring the pygame set's intent to vary silhouette,
		# not just colour.
		var part_offset: float = rng.randf_range(-6.0, 6.0)
		_draw_shaded_ellipse(Vector2(u.call(64 + part_offset - 4), u.call(fy + 8)), Vector2(u.call(face_w / 2.0 + 3), u.call(16)), hair, 24, .3)
		_draw_shaded_ellipse(Vector2(u.call(fx + face_w + 1), u.call(fy + 14)), Vector2(u.call(6), u.call(15)), hair, 16, .3)

	# Eyes: whites, iris, pupil, highlight, eyelid arc, eyebrow.
	var eye_y: float = fy + 35
	var eye_dx: float = rng.randf_range(12, 15)
	var eye_colour: Color = EYE_COLOURS[rng.randi_range(0, EYE_COLOURS.size() - 1)]
	for ex in [64 - eye_dx, 64 + eye_dx]:
		_draw_ellipse_fill(Vector2(u.call(ex), u.call(eye_y)), Vector2(u.call(5), u.call(2.5)), _mix(Color8(242, 239, 229), skin, .18), 14)
		draw_circle(Vector2(u.call(ex), u.call(eye_y)), u.call(1.8), eye_colour, true, -1.0, true)
		draw_circle(Vector2(u.call(ex), u.call(eye_y)), max(1.0, u.call(.75)), Color8(18, 18, 17), true, -1.0, true)
		draw_circle(Vector2(u.call(ex - .6), u.call(eye_y - .7)), max(1.0, u.call(.3)), Color8(235, 238, 230), true, -1.0, true)
		draw_arc(Vector2(u.call(ex), u.call(eye_y - .5)), u.call(6), 3.25, 6.05, 10, shade, u.call(1), true)
		draw_line(Vector2(u.call(ex - 6), u.call(eye_y - 7)), Vector2(u.call(ex + 5), u.call(eye_y - 7)), _mix(hair, skin, .18), u.call(1.4), true)

	# Nose and mouth.
	var nose_x: float = 61 + rng.randf_range(0, 6)
	draw_line(Vector2(u.call(64), u.call(eye_y + 5)), Vector2(u.call(nose_x), u.call(eye_y + 20)), _mix(shade, skin, .22), u.call(1.2), true)
	draw_arc(Vector2(u.call(64.5), u.call(eye_y + 19)), u.call(5.5), .2, 2.9, 10, shade, u.call(1), true)
	var mouth_y: float = eye_y + 29
	var lip: Color = _mix(skin, Color8(118, 50, 50), .32)
	draw_arc(Vector2(u.call(64), u.call(mouth_y + .5)), u.call(9), .10, 3.03, 12, lip, u.call(1.2), true)
	draw_arc(Vector2(u.call(64), u.call(mouth_y + 2.5)), u.call(8), 3.25, 6.05, 12, _mix(lip, shade, .22), u.call(1.3), true)

	# Beard, age-gated probability, with light stubble texture.
	var beard_chance: float = .03 if _age < 19 else .34 if _age < 31 else .55
	if rng.randf() < beard_chance:
		var beard: Color = _mix(hair, skin, .20)
		draw_arc(Vector2(u.call(fx + 6 + (face_w - 12) / 2.0), u.call(fy + 31 + (face_h - 24) / 2.0)),
			u.call((face_w - 12) / 2.0), 3.15, 6.2, 16, beard, u.call(rng.randf_range(2, 4)), true)
		if rng.randf() < .58:
			draw_line(Vector2(u.call(57), u.call(mouth_y - 4)), Vector2(u.call(71), u.call(mouth_y - 4)), beard, u.call(2), true)
		for _i in range(35):
			var bx: float = rng.randf_range(fx + 9, fx + face_w - 10)
			var by: float = rng.randf_range(mouth_y - 4, fy + face_h - 7)
			if absf(bx - 64) > (by - mouth_y) * .55 or by > mouth_y + 6:
				_draw_ellipse_fill(Vector2(u.call(bx), u.call(by)), Vector2(u.call(.5), u.call(.5)), _mix(beard, skin, .18), 8)

	# Wrinkles at the outer eye corners, plus mouth-frame lines past 42.
	if _age >= 36:
		var wrinkle: Color = _mix(skin, Color8(86, 68, 61), .35)
		for offset in [-10, 10]:
			draw_line(Vector2(u.call(64 + offset - 4), u.call(eye_y + 8)), Vector2(u.call(64 + offset + 4), u.call(eye_y + 8)), wrinkle, u.call(1), true)
		if _age >= 42:
			draw_arc(Vector2(u.call(64), u.call(mouth_y + 5)), u.call(11), .2, 2.9, 12, wrinkle, u.call(1), true)

	# Soft edge vignette so portraits don't end abruptly in dense lists.
	for radius in range(62, 52, -2):
		var alpha: float = (62.0 - radius) / 10.0 * .22
		draw_polyline(_ellipse_points(Vector2(u.call(64), u.call(61)), Vector2(u.call(radius), u.call(radius)), 32), Color(.05, .06, .09, alpha), u.call(2), true)
