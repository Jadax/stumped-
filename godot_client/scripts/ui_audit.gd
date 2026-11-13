extends RefCounted
## v5.3.0 dev-only UI audit (`-- --ui-audit --res=1920x1080`). Visits every
## navigable screen plus the startup flow, saves a PNG of each, and writes a
## report of objectively detectable layout defects:
##   OVERLAP  — two visible text controls whose rectangles intersect
##              (neither containing the other), i.e. text drawn on text;
##   OVERFLOW — a single-line label whose text is wider than its box;
##   OFFSCREEN— a visible text control extending past the window.
## Pixels still need a human eye; this catches the regressions mechanically.

const STARTUP_SCREENS := ["Main Menu", "Load Game", "New Game Setup", "Career Team Selection",
	"Tournament Setup", "World Cup Setup", "Settings", "Help"]


static func run(shell: Control, nav_groups: Array) -> void:
	var size := Vector2i(1280, 720)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--res="):
			var parts: PackedStringArray = arg.substr(6).split("x")
			if parts.size() == 2:
				size = Vector2i(int(parts[0]), int(parts[1]))
	var window := shell.get_window()
	window.mode = Window.MODE_WINDOWED
	window.size = size
	for _i in range(6):
		await shell.get_tree().process_frame
	var folder := "res://../screenshots/audit/%dx%d" % [size.x, size.y]
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(folder))
	var screens: Array = []
	for group in nav_groups:
		for screen_name in group[1]:
			if screen_name not in screens:
				screens.append(screen_name)
	screens.append_array(STARTUP_SCREENS)
	var report := PackedStringArray()
	var total := 0
	for screen_name in screens:
		shell.show_screen(screen_name)
		await shell.get_tree().create_timer(0.45).timeout
		# The first-run tutorial overlay is meant to cover the screen.
		var overlay = shell.get("_onboarding_overlay")
		if overlay is CanvasItem:
			(overlay as CanvasItem).visible = false
		await shell.get_tree().process_frame
		var image := shell.get_viewport().get_texture().get_image()
		var slug: String = screen_name.to_lower().replace(" ", "_")
		image.save_png("%s/%s.png" % [folder, slug])
		var issues := audit(shell, shell.get_viewport().get_visible_rect())
		total += issues.size()
		report.append("== %s (%d)" % [screen_name, issues.size()])
		for issue in issues:
			report.append("  " + issue)
	report.insert(0, "UI AUDIT %dx%d — %d issue(s) across %d screens" % [size.x, size.y, total, screens.size()])
	var file := FileAccess.open("%s/report.txt" % folder, FileAccess.WRITE)
	file.store_string("\n".join(report))
	file.close()
	print("UI AUDIT %dx%d: %d issue(s) -> %s/report.txt" % [size.x, size.y, total, folder])
	shell.get_tree().quit()


static func _clip_rect(control: Control) -> Rect2:
	## The control's on-screen rect, cut to any scrolling/clipping ancestor.
	var rect := control.get_global_rect()
	var node := control.get_parent()
	while node:
		if node is Control and (node is ScrollContainer or (node as Control).clip_contents):
			rect = rect.intersection((node as Control).get_global_rect())
		node = node.get_parent()
	return rect


static func _text_of(control: Control) -> String:
	if control is Label:
		return (control as Label).text
	if control is Button:
		return (control as Button).text
	if control is LineEdit:
		return (control as LineEdit).text
	return ""


static func _collect(node: Node, out: Array) -> void:
	if node is CanvasItem and not (node as CanvasItem).visible:
		return
	if node is Control and (node is Label or node is Button) and not _text_of(node).strip_edges().is_empty():
		var rect := _clip_rect(node)
		if rect.size.x > 1 and rect.size.y > 1:
			out.append([node, rect])
	for child in node.get_children():
		_collect(child, out)


static func _path(node: Node) -> String:
	return "%s '%s'" % [node.name, _text_of(node).left(28).replace("\n", " ")]


static func audit(root: Node, viewport: Rect2) -> PackedStringArray:
	var issues := PackedStringArray()
	var items: Array = []
	_collect(root, items)
	for entry in items:
		var control: Control = entry[0]
		var rect: Rect2 = entry[1]
		var full := control.get_global_rect()
		if full.end.x > viewport.end.x + 2 or full.end.y > viewport.end.y + 2 or full.position.x < -2:
			if not _inside_scroll(control):
				issues.append("OFFSCREEN %s at %s" % [_path(control), str(full)])
		if control is Label:
			var label := control as Label
			if label.autowrap_mode == TextServer.AUTOWRAP_OFF and not label.clip_text \
					and label.text_overrun_behavior == TextServer.OVERRUN_NO_TRIMMING:
				var font := label.get_theme_font("font")
				var font_size := label.get_theme_font_size("font_size")
				var widest := 0.0
				for line in label.text.split("\n"):
					widest = max(widest, font.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x)
				if widest > full.size.x + 3:
					issues.append("OVERFLOW %s text %dpx > box %dpx" % [_path(control), int(widest), int(full.size.x)])
	for i in range(items.size()):
		for j in range(i + 1, items.size()):
			var a: Control = items[i][0]
			var b: Control = items[j][0]
			if a.is_ancestor_of(b) or b.is_ancestor_of(a):
				continue
			var overlap: Rect2 = (items[i][1] as Rect2).intersection(items[j][1])
			if overlap.size.x < 3 or overlap.size.y < 3:
				continue
			var smaller: float = min((items[i][1] as Rect2).get_area(), (items[j][1] as Rect2).get_area())
			if overlap.get_area() > smaller * 0.12:
				issues.append("OVERLAP %s <> %s" % [_path(a), _path(b)])
	return issues


static func _inside_scroll(control: Node) -> bool:
	var node := control.get_parent()
	while node:
		if node is ScrollContainer:
			return true
		node = node.get_parent()
	return false
