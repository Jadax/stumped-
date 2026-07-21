class_name JsonFormat
extends RefCounted
## Godot's JSON parser returns every JSON number as a float (there's no
## int/float distinction in the JSON spec) — without this, every numeric
## column across every screen displays "25.0" instead of "25". Route any
## value coming straight from an IpcBridge response through value() before
## displaying it.

static func value(v) -> String:
	if typeof(v) == TYPE_FLOAT and v == floor(v) and abs(v) < 1e15:
		return str(int(v))
	return str(v)
