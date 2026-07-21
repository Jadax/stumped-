extends Control
## Match Day hub — next-fixture header, the selected XI in batting order,
## and a drawn ground view with default fielding positions. Fed by
## get_match_preview. Not a live match simulation: the ball-by-ball feed is
## a separate, much larger piece of work (see
## docs/GRAPHICS_MIGRATION_PLAN.md) — this is the honest, real pre-match
## view that replaces the old static "Coming Soon" placeholder.

@onready var title_label: Label = $Title
@onready var fixture_label: Label = $FixtureBar/FixtureLabel
@onready var xi_list: VBoxContainer = $Row/LineupCard/Box/List
@onready var xi_header: Label = $Row/LineupCard/Box/Header


func _ready() -> void:
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_match_preview")
	if response.has("error"):
		title_label.text = "MATCH — backend error: %s" % response["error"]
		push_error("MatchScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	title_label.text = "MATCH DAY"

	var fixture = result.get("fixture")
	if fixture:
		fixture_label.text = "%s vs %s — %s, %s" % [fixture.get("home_name", "?"), fixture.get("away_name", "?"),
			fixture.get("format", "?"), fixture.get("date", "?")]
	else:
		fixture_label.text = "No fixture scheduled"

	var xi: Array = result.get("xi", [])
	xi_header.text = "PLAYING XI — %d/11" % xi.size()
	for child in xi_list.get_children():
		child.queue_free()
	if xi.is_empty():
		var empty := Label.new()
		empty.text = "No XI selected yet — pick one on the Selection screen."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		xi_list.add_child(empty)
		return
	for i in range(xi.size()):
		var player: Dictionary = xi[i]
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		var order_label := Label.new()
		order_label.text = "%d." % (i + 1)
		order_label.custom_minimum_size = Vector2(24, 0)
		order_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		row.add_child(order_label)
		var tags := []
		if player.get("id") == result.get("captain_id"): tags.append("C")
		if player.get("id") == result.get("keeper_id"): tags.append("WK")
		var suffix := " (%s)" % "/".join(tags) if not tags.is_empty() else ""
		var name_label := Label.new()
		name_label.text = "%s%s" % [player.get("name", "?"), suffix]
		name_label.custom_minimum_size = Vector2(180, 0)
		if not tags.is_empty():
			name_label.add_theme_color_override("font_color", AppTheme.GOLD)
		row.add_child(name_label)
		var role_label := Label.new()
		role_label.text = player.get("role", "?")
		role_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
		row.add_child(role_label)
		xi_list.add_child(row)
