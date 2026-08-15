extends Control
## Lightweight, resolution-independent atmosphere layer.
## Everything is vector drawn so the client stays sharp from 1280p to 4K and
## does not ship copyrighted photography. It sits behind the shell chrome and
## uses a tiny number of primitives, keeping idle CPU/GPU cost negligible.

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
	# Layered night-sky bands avoid a flat, empty backdrop.
	for i in range(10):
		var t := float(i) / 9.0
		var band := Color(0.035 + t * 0.025, 0.055 + t * 0.035, 0.085 + t * 0.045, 1.0)
		draw_rect(Rect2(0, h * t, w, h / 9.0 + 1.0), band)
	# Soft green and blue light pools, drawn as transparent concentric circles.
	var pulse := 0.5 + 0.5 * sin(_time * 0.35)
	for i in range(6, 0, -1):
		var r := float(i) * 145.0
		var alpha := 0.012 + pulse * 0.004
		draw_circle(Vector2(w * 0.18, h * 0.83), r, Color(0.12, 0.55, 0.32, alpha))
		draw_circle(Vector2(w * 0.88, h * 0.18), r, Color(0.18, 0.40, 0.72, alpha * 0.8))
	# A quiet stadium silhouette gives every screen a cricket identity.
	var horizon := h * 0.76
	draw_rect(Rect2(0, horizon, w, h - horizon), Color(0.03, 0.12, 0.09, 0.62))
	for i in range(16):
		var x := float(i) / 15.0 * w
		var height := 22.0 + fmod(float(i * 29), 38.0)
		draw_rect(Rect2(x, horizon - height, maxf(2.0, w / 240.0), height), Color(0.12, 0.22, 0.24, 0.42))
	# Moving dust/turning points are deliberately subtle rather than noisy.
	for p in _particles:
		var px := fmod((float(p.x) + _time * float(p.speed)), 1.0) * w
		var py := float(p.y) * h
		var shimmer := 0.18 + 0.10 * sin(_time * 1.4 + px * 0.01)
		draw_circle(Vector2(px, py), float(p.size), Color(0.55, 0.82, 0.65, shimmer))
	# Thin vignette edges provide depth without hiding text.
	draw_rect(Rect2(0, 0, w, 3), Color(0.25, 0.75, 0.52, 0.18))
	draw_rect(Rect2(0, h - 3, w, 3), Color(0.03, 0.05, 0.08, 0.45))
