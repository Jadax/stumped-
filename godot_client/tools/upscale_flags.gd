extends SceneTree
## One-off dev tool (v0.91.0): re-exports every flag PNG at a larger fixed
## size (160x96, matching real flag 5:3 ratio) in full RGBA8 colour instead
## of the original 80x48 2-bit indexed export — same source flags, no new
## designs, just a proper anti-aliased upscale so they don't read as
## visibly low-res next to the new gradient-shaded portraits. Run once via
## `godot --headless --script godot_client/tools/upscale_flags.gd`, not
## part of any shipped build path.

const TARGET_WIDTH := 160
const TARGET_HEIGHT := 96


func _init() -> void:
	var dir := "res://assets/images/flags/"
	var files := DirAccess.get_files_at(dir)
	var processed := 0
	for file_name in files:
		if not file_name.ends_with(".png"):
			continue
		var path := dir + file_name
		var image := Image.load_from_file(path)
		if image == null:
			print("SKIP (failed to load): ", path)
			continue
		image.convert(Image.FORMAT_RGBA8)
		image.resize(TARGET_WIDTH, TARGET_HEIGHT, Image.INTERPOLATE_LANCZOS)
		var error := image.save_png(path)
		if error == OK:
			processed += 1
			print("Upscaled: ", file_name)
		else:
			print("FAILED to save: ", file_name, " error=", error)
	print("Done. %d flag(s) upscaled to %dx%d RGBA8." % [processed, TARGET_WIDTH, TARGET_HEIGHT])
	quit()
