extends Control
## Achievements screen — shows all achievements with unlock status,
## progress, and categories.

@onready var title_label: Label = $Title
@onready var progress_label: Label = $Header/Progress
@onready var categories_box: HBoxContainer = $Header/Categories
@onready var achievements_list: VBoxContainer = $Scroll/Achievements
@onready var back_button: Button = $Footer/BackButton

var _achievements: Dictionary = {}
var _current_category: String = "all"


func _ready() -> void:
	back_button.pressed.connect(_on_back)
	_build_categories()
	refresh()


func _on_back() -> void:
	var shell := get_tree().get_first_node_in_group("shell")
	if shell:
		var response := IpcBridge.call_method("get_dashboard")
		if not response.has("error") and response.get("result", {}).get("team"):
			shell.show_screen("Dashboard")
		else:
			shell.show_screen("Main Menu")


func _build_categories() -> void:
	for child in categories_box.get_children():
		child.queue_free()
	for cat in ["all", "career", "tactical", "management", "collection", "international"]:
		var button := Button.new()
		button.text = cat.to_upper()
		button.focus_mode = Control.FOCUS_NONE
		button.pressed.connect(_on_category_pressed.bind(cat))
		categories_box.add_child(button)


func _on_category_pressed(cat: String) -> void:
	_current_category = cat
	_render_achievements()


func refresh() -> void:
	var response := IpcBridge.call_method("get_achievements")
	if response.has("error"):
		title_label.text = "ACHIEVEMENTS — error: %s" % response["error"]
		return
	_achievements = response["result"]
	var unlocked: int = _achievements.get("unlocked_count", 0)
	var total: int = _achievements.get("total_count", 0)
	progress_label.text = "%d / %d unlocked" % [unlocked, total]
	title_label.text = "ACHIEVEMENTS"
	_render_achievements()


func _render_achievements() -> void:
	for child in achievements_list.get_children():
		achievements_list.remove_child(child)
		child.queue_free()
	var progress: Dictionary = _achievements.get("progress", {})
	var achievement_defs := [
		["first_win", "First Victory", "Win your first match", "career", "🏆"],
		["first_draw", "Hard Fought Draw", "Draw your first match", "career", "🤝"],
		["season_survivor", "Season Survivor", "Complete your first full season", "career", "📅"],
		["century_manager", "Century Manager", "Manage 100 matches", "career", "💯"],
		["winning_manager", "Winning Manager", "Achieve 50 wins", "career", "📊"],
		["hat_trick_hero", "Hat Trick Hero", "A bowler takes a hat-trick", "tactical", "🎩"],
		["double_century", "Double Century", "A batsman scores 200+", "tactical", "🏏"],
		["century_maker", "Century Maker", "A batsman scores 100+", "tactical", "💯"],
		["five_wicket_haul", "Five-Wicket Haul", "A bowler takes 5+ wickets", "tactical", "🎳"],
		["super_over_winner", "Super Over Hero", "Win a Super Over", "tactical", "⚡"],
		["promotion_party", "Promotion Party", "Get promoted to a higher division", "management", "📈"],
		["division_one_champion", "Division One Champion", "Win Division 1 title", "management", "🥇"],
		["cup_glory", "Cup Glory", "Win the Domestic Knockout Cup", "management", "🏆"],
		["treble_winner", "Treble Winner", "Win league, cup, and international", "management", "🏆"],
		["financial_wizard", "Financial Wizard", "Reach £10M in finances", "management", "💰"],
		["youth_developer", "Youth Developer", "Promote 5 from academy", "management", "🌱"],
		["facility_mogul", "Facility Mogul", "Upgrade all facilities to max", "management", "🏟️"],
		["player_collector", "Player Collector", "50 different players in career", "collection", "👥"],
		["international_export", "International Export", "5+ players called up", "collection", "🌍"],
		["scouting_network", "Scouting Network", "Scout 30+ players", "collection", "🔍"],
		["debut_callup", "International Debut", "First player called up", "international", "🌍"],
		["international_winner", "International Winner", "Your player's nation wins", "international", "🏆"],
		["ashes_legend", "Ashes Legend", "Your player scores 150+ in Ashes", "international", "⭐"],
	]
	for defn in achievement_defs:
		if _current_category != "all" and defn[3] != _current_category:
			continue
		var unlocked: bool = progress.get(defn[0], false)
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		var icon_label := Label.new()
		icon_label.text = defn[4]
		icon_label.add_theme_font_size_override("font_size", 20)
		row.add_child(icon_label)
		var info_box := VBoxContainer.new()
		info_box.add_theme_constant_override("separation", 2)
		var name_label := Label.new()
		name_label.text = defn[1]
		name_label.add_theme_font_size_override("font_size", 14)
		if unlocked:
			name_label.add_theme_color_override("font_color", AppTheme.GOLD)
		else:
			name_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		info_box.add_child(name_label)
		var desc_label := Label.new()
		desc_label.text = defn[2]
		desc_label.add_theme_font_size_override("font_size", 11)
		desc_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		info_box.add_child(desc_label)
		row.add_child(info_box)
		var status_label := Label.new()
		status_label.text = "✓ UNLOCKED" if unlocked else "LOCKED"
		status_label.add_theme_font_size_override("font_size", 11)
		status_label.add_theme_color_override("font_color", AppTheme.GOLD if unlocked else AppTheme.TEXT_MUTED)
		row.add_child(status_label)
		achievements_list.add_child(row)
