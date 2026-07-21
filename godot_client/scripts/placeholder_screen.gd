extends Control
## Mirrors ui/shared_components.py BaseScreen's "Coming Soon" fallback for
## screens not yet ported to Godot (docs/GRAPHICS_MIGRATION_PLAN.md Phase 2).

@onready var title_label: Label = $Title
@onready var subtitle_label: Label = $Subtitle

var _pending_screen_name: String = "SCREEN"


## Safe to call before this node enters the tree (before @onready vars are
## ready) — table_screen.gd/dashboard_screen.gd store config the same way
## and apply it in _ready(), not at call time.
func set_screen_name(screen_name: String) -> void:
	_pending_screen_name = screen_name
	if is_node_ready():
		_apply()


func _ready() -> void:
	_apply()


func _apply() -> void:
	title_label.text = _pending_screen_name
	subtitle_label.text = "%s — Coming Soon (not yet ported from the pygame client)" % _pending_screen_name
