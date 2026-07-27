extends Control
## Ports src/views/screens/help_screen.py: topic sidebar + expandable
## article list + search filter, sourced from the same JSON content via
## get_help_content (ipc_server.py) so both clients show identical text.
## Only reachable from Main Menu today (no in-career Help entry yet), so
## BACK always returns there — revisit if a later phase adds one.

@onready var search_edit: LineEdit = $SearchEdit
@onready var topic_list: VBoxContainer = $Row/NavCard/Box/Scroll/TopicList
@onready var section_title: Label = $Row/ArticleCard/Box/SectionTitle
@onready var article_list: VBoxContainer = $Row/ArticleCard/Box/Scroll/ArticleList
@onready var back_button: Button = $BackButton

var _sections: Array = []
var _active_index: int = 0
var _expanded_index: int = -1
var _topic_buttons: Array = []


func _ready() -> void:
	back_button.pressed.connect(func(): _shell().show_screen("Main Menu"))
	search_edit.text_changed.connect(func(_t): _expanded_index = -1; _render_articles())
	_load_content()


func _shell() -> Node:
	return get_tree().get_first_node_in_group("shell")


func _load_content() -> void:
	var response := IpcBridge.call_method("get_help_content")
	if response.has("error"):
		section_title.text = "Backend error: %s" % response["error"]
		return
	_sections = response["result"].get("sections", [])
	for child in topic_list.get_children():
		topic_list.remove_child(child)
		child.queue_free()
	_topic_buttons.clear()
	for i in range(_sections.size()):
		var button := Button.new()
		button.toggle_mode = true
		button.custom_minimum_size = Vector2(0, 34)
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.text = str(_sections[i].get("title", "?")).to_upper()
		button.button_pressed = i == 0
		button.pressed.connect(_on_topic_pressed.bind(i))
		topic_list.add_child(button)
		_topic_buttons.append(button)
	_render_articles()


func _on_topic_pressed(index: int) -> void:
	_active_index = index
	_expanded_index = -1
	for i in range(_topic_buttons.size()):
		_topic_buttons[i].set_pressed_no_signal(i == index)
	_render_articles()


func _filtered_articles() -> Array:
	if _sections.is_empty():
		return []
	var articles: Array = _sections[_active_index].get("articles", [])
	var query := search_edit.text.strip_edges().to_lower()
	if query.is_empty():
		return articles
	return articles.filter(func(a): return _matches_query(a, query))


func _matches_query(article: Dictionary, query: String) -> bool:
	return query in str(article.get("title", "")).to_lower() or query in str(article.get("body", "")).to_lower()


func _render_articles() -> void:
	if _sections.is_empty():
		return
	section_title.text = str(_sections[_active_index].get("title", "?"))
	for child in article_list.get_children():
		article_list.remove_child(child)
		child.queue_free()
	var articles := _filtered_articles()
	for i in range(articles.size()):
		var article: Dictionary = articles[i]
		var header := Button.new()
		header.custom_minimum_size = Vector2(0, 38)
		header.alignment = HORIZONTAL_ALIGNMENT_LEFT
		header.text = "%s  %s" % ["−" if i == _expanded_index else "+", str(article.get("title", "?"))]
		header.pressed.connect(_on_article_pressed.bind(i))
		article_list.add_child(header)
		if i == _expanded_index:
			var body := Label.new()
			body.text = str(article.get("body", ""))
			body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			body.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
			article_list.add_child(body)


func _on_article_pressed(index: int) -> void:
	_expanded_index = index if _expanded_index != index else -1
	_render_articles()
