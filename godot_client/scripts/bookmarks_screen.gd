extends Control

@onready var title_label: Label = $Title
@onready var list: VBoxContainer = $Row/Card/Box/Scroll/List


func _ready() -> void:
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_bookmarks")
	if response.has("error"):
		title_label.text = "BOOKMARKS — backend error: %s" % response["error"]
		push_error("BookmarksScreen: %s" % response["error"])
		return
	var items: Array = response["result"]
	for child in list.get_children():
		list.remove_child(child)
		child.queue_free()
	if items.is_empty():
		var empty := Label.new()
		empty.text = "No bookmarks yet. Star items from their detail pages to add them here."
		empty.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		list.add_child(empty)
	else:
		for item in items:
			var row := HBoxContainer.new()
			row.add_theme_constant_override("separation", 10)
			var label := Label.new()
			label.text = str(item.get("label", "—"))
			label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(label)
			var sublabel := Label.new()
			var sub = item.get("sublabel", "")
			sublabel.text = sub if sub else ""
			sublabel.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
			sublabel.add_theme_font_size_override("font_size", 11)
			row.add_child(sublabel)
			var remove_btn := Button.new()
			remove_btn.text = "REMOVE"
			remove_btn.pressed.connect(_on_remove_pressed.bind(item["id"]))
			row.add_child(remove_btn)
			list.add_child(row)
	title_label.text = "BOOKMARKS"


func _on_remove_pressed(bookmark_id: int) -> void:
	var response := IpcBridge.call_method("remove_bookmark", {"bookmark_id": bookmark_id})
	if response.has("error"):
		push_error("BookmarksScreen: remove_bookmark failed: %s" % response["error"])
		return
	refresh()
