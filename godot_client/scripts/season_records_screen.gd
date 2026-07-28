extends Control
## New in v0.80.0: no season-indexed stats existed anywhere before this —
## player_records was always career-cumulative. Left card derives all-time
## club bests live from matches.result_json (get_club_records); right card
## is the season-by-season leader archive written at each rollover
## (get_season_records), sourced from a game_state baseline diff so it
## didn't need touching every match-recording call site.

@onready var title_label: Label = $Title
@onready var records_list: VBoxContainer = $Row/RecordsCard/Box/List
@onready var seasons_list: VBoxContainer = $Row/SeasonsCard/Box/Scroll/List


func _ready() -> void:
	refresh()


func refresh() -> void:
	var records_response := IpcBridge.call_method("get_club_records")
	if records_response.has("error"):
		title_label.text = "CLUB RECORDS — backend error: %s" % records_response["error"]
		push_error("SeasonRecordsScreen: %s" % records_response["error"])
		return
	var seasons_response := IpcBridge.call_method("get_season_records")
	if seasons_response.has("error"):
		title_label.text = "CLUB RECORDS — backend error: %s" % seasons_response["error"]
		push_error("SeasonRecordsScreen: %s" % seasons_response["error"])
		return
	_render_records(records_response["result"])
	_render_seasons(seasons_response["result"].get("seasons", []))
	title_label.text = "CLUB RECORDS"


func _clear(list: VBoxContainer) -> void:
	for child in list.get_children():
		list.remove_child(child)
		child.queue_free()


func _stat_row(label_text: String, value_text: String, colour: Color = AppTheme.TEXT_PRIMARY) -> Control:
	var row := VBoxContainer.new()
	row.add_theme_constant_override("separation", 2)
	var label := Label.new()
	label.text = label_text
	label.add_theme_font_size_override("font_size", 11)
	label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	row.add_child(label)
	var value := Label.new()
	value.text = value_text
	value.add_theme_font_size_override("font_size", 16)
	value.add_theme_color_override("font_color", colour)
	row.add_child(value)
	return row


func _render_records(records: Dictionary) -> void:
	_clear(records_list)
	if records.get("matches_played", 0) == 0:
		var empty := Label.new()
		empty.text = "No completed matches yet — records will appear once the season is underway."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		empty.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		records_list.add_child(empty)
		return
	var highest: Variant = records.get("highest_score")
	if highest:
		records_list.add_child(_stat_row("HIGHEST TEAM SCORE",
			"%d (%s vs %d, %s)" % [highest["runs"], highest["format"], highest["opponent_runs"], highest["date"]],
			AppTheme.HEADER_GREEN))
	var win: Variant = records.get("biggest_win")
	if win:
		records_list.add_child(_stat_row("BIGGEST WIN",
			"%d-%d (%s, %s)" % [win["own_runs"], win["opponent_runs"], win["format"], win["date"]], AppTheme.GOLD))
	var defeat: Variant = records.get("heaviest_defeat")
	if defeat:
		records_list.add_child(_stat_row("HEAVIEST DEFEAT",
			"%d-%d (%s, %s)" % [defeat["own_runs"], defeat["opponent_runs"], defeat["format"], defeat["date"]],
			AppTheme.DANGER))
	records_list.add_child(_stat_row("MATCHES PLAYED", str(records.get("matches_played", 0))))


func _render_seasons(seasons: Array) -> void:
	_clear(seasons_list)
	if seasons.is_empty():
		var empty := Label.new()
		empty.text = "No seasons completed yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		seasons_list.add_child(empty)
		return
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 10)
	for text in ["SEASON", "POS", "W-L", "TOP SCORER", "TOP WICKETS"]:
		var head := Label.new()
		head.text = text
		head.add_theme_font_size_override("font_size", 10)
		head.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		head.custom_minimum_size = Vector2(90, 0) if text != "SEASON" else Vector2(60, 0)
		header.add_child(head)
	seasons_list.add_child(header)
	seasons_list.add_child(HSeparator.new())
	for entry in seasons:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 10)
		var season_label := Label.new()
		season_label.text = str(entry.get("season", "—"))
		season_label.custom_minimum_size = Vector2(60, 0)
		row.add_child(season_label)
		var pos_label := Label.new()
		var position = entry.get("position")
		pos_label.text = str(position) if position != null else "—"
		pos_label.custom_minimum_size = Vector2(90, 0)
		row.add_child(pos_label)
		var record_label := Label.new()
		record_label.text = "%d-%d" % [entry.get("won", 0), entry.get("lost", 0)]
		record_label.custom_minimum_size = Vector2(90, 0)
		row.add_child(record_label)
		var scorer_label := Label.new()
		var scorer_name: String = entry.get("top_scorer_name", "")
		scorer_label.text = "%s (%d)" % [scorer_name, entry.get("top_scorer_runs", 0)] if scorer_name != "" else "—"
		scorer_label.custom_minimum_size = Vector2(90, 0)
		scorer_label.add_theme_font_size_override("font_size", 11)
		row.add_child(scorer_label)
		var wickets_label := Label.new()
		var wicket_name: String = entry.get("top_wicket_taker_name", "")
		wickets_label.text = "%s (%d)" % [wicket_name, entry.get("top_wicket_taker_wickets", 0)] if wicket_name != "" else "—"
		wickets_label.custom_minimum_size = Vector2(90, 0)
		wickets_label.add_theme_font_size_override("font_size", 11)
		row.add_child(wickets_label)
		seasons_list.add_child(row)
