extends Control
## Lightweight, resolution-independent atmosphere layer.
## Everything is vector drawn so the client stays sharp from 1280p to 4K and
## does not ship copyrighted photography. It sits behind the shell chrome and
## uses a tiny number of primitives, keeping idle CPU/GPU cost negligible.
##
## v5.3.0: repainted for the light "sunlit ground" theme. The old night-sky
## bands (near-black blue-green) showed through the 16-32px gaps where a
## screen's own parchment Background doesn't reach (1280x720 content is
## 1248x538, so dark strips showed down the right edge and along the bottom).
## Every tone here is now in the parchment family so any gap shows a colour
## that belongs to the theme.

var _time := 0.0
var _particles: Array[Dictionary] = []

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	for i in range(18):
		_particles.append({
			"x": fmod(float(i * 83 + 31), 1000.0) / 1000.0,
			"y": 0.16 + fmod(float(i * 47 + 17), 680.0) / 680.0 * 0.72,
			"speed": 0.008 + fmod(float(i * 13), 17.0) / 10000.0,
			"size": 1.0 + fmod(float(i * 7), 3.0),
		})
	queue_redraw()

func _process(delta: float) -> void:
	_time += delta
	queue_redraw()

func _draw() -> void:
	var w := size.x
	var h := size.y
	if w <= 1.0 or h <= 1.0:
		return
	# Layered warm bands avoid a flat, empty backdrop (parchment family only).
	for i in range(10):
		var t := float(i) / 9.0
		var band := Color(0.925 + t * 0.045, 0.912 + t * 0.05, 0.862 + t * 0.066, 1.0)
		draw_rect(Rect2(0, h * t, w, h / 9.0 + 1.0), band)
	# Soft green and blue light pools, drawn as transparent concentric circles.
	var pulse := 0.5 + 0.5 * sin(_time * 0.35)
	for i in range(6, 0, -1):
		var r := float(i) * 145.0
		var alpha := 0.02 + pulse * 0.005
		draw_circle(Vector2(w * 0.18, h * 0.83), r, Color(0.35, 0.72, 0.45, alpha))
		draw_circle(Vector2(w * 0.88, h * 0.18), r, Color(0.4, 0.6, 0.82, alpha * 0.8))
	# A quiet stadium/sight-scalline silhouette keeps the cricket identity.
	var horizon := h * 0.76
	draw_rect(Rect2(0, horizon, w, h - horizon), Color(0.86, 0.88, 0.80, 0.45))
	for i in range(16):
		var x := float(i) / 15.0 * w
		var height := 22.0 + fmod(float(i * 29), 38.0)
		draw_rect(Rect2(x, horizon - height, maxf(2.0, w / 240.0), height), Color(0.78, 0.80, 0.70, 0.40))
	# Moving dust/turning points are deliberately subtle rather than noisy.
	for p in _particles:
		var px := fmod((float(p.x) + _time * float(p.speed)), 1.0) * w
		var py := float(p.y) * h
		var shimmer := 0.10 + 0.06 * sin(_time * 1.4 + px * 0.01)
		draw_circle(Vector2(px, py), float(p.size), Color(0.35, 0.55, 0.40, shimmer))
	# Thin edge framing provides depth without hiding text.
	draw_rect(Rect2(0, 0, w, 3), Color(0.55, 0.80, 0.60, 0.10))
	draw_rect(Rect2(0, h - 3, w, 3), Color(0.75, 0.72, 0.64, 0.25))
