extends Control
## The persistent chrome — top nav bar (mirrors main.py's NAV_GROUPS,
## docs/UX_ROADMAP.md's FM26-translated IA) and a content area that swaps
## screens. Section buttons on the top bar; sub-screen tab buttons on a
## second sub-nav bar. Screens not yet ported show the same "Coming Soon"
## placeholder the pygame client's BaseScreen falls back to.

const NAV_GROUPS := [
	["PORTAL", ["Dashboard", "Inbox"]],
	["BOOKMARKS", ["Bookmarks"]],
	["SQUAD", ["Squad", "Selection", "Training", "Youth Academy", "Medical Centre", "Compare", "Player Editor"]],
	["DATA HUB", ["Data Hub"]],
	["MATCH DAY", ["Match"]],
	["RECRUITMENT", ["Recruitment", "Transfers", "Offers"]],
	["CLUB", ["Staff", "Staff Market", "Finances", "Facilities", "Kit Editor", "Emblem Editor"]],
	["CAREER", ["Trophy Room", "Club Records", "Cup", "Press Conference", "Board", "Job Offers", "Legends", "About", "Achievements", "National Team", "Competition Editor"]],
]

## Hand-drawn nav_icon.gd glyph per screen — no icon asset pipeline exists,
## so related screens intentionally share a glyph (e.g. Staff/Staff Market
## both use "staff") rather than inventing sixteen distinct pictograms.
const NAV_ICONS := {
	"Dashboard": "dashboard", "Inbox": "inbox", "Bookmarks": "bookmarks",
	"Squad": "squad", "Selection": "selection",
	"Training": "training", "Youth Academy": "academy", 	"Medical Centre": "medical", "Compare": "squad", "Player Editor": "squad", "Match": "match",
	"Recruitment": "recruitment", "Transfers": "transfers", "Offers": "offers",
	"Data Hub": "data_hub",
	"Staff": "staff", "Staff Market": "staff", 	"Finances": "finances", "Facilities": "facilities", "Kit Editor": "settings", "Emblem Editor": "settings",
	"Trophy Room": "cup", "Club Records": "legends", "Cup": "cup", "Press Conference": "press",
	"Board": "dashboard", "Job Offers": "offers", "Legends": "legends", "About": "help", "Achievements": "legends", "National Team": "squad", "Competition Editor": "cup",
}

const DASHBOARD_SCENE := preload("res://scenes/dashboard_screen.tscn")
const BOOKMARKS_SCENE := preload("res://scenes/bookmarks_screen.tscn")
const DATA_HUB_SCENE := preload("res://scenes/data_hub_screen.tscn")
const RECRUITMENT_SCENE := preload("res://scenes/recruitment_screen.tscn")
const TABLE_SCENE := preload("res://scenes/table_screen.tscn")
const TRAINING_SCENE := preload("res://scenes/training_screen.tscn")
const YOUTH_ACADEMY_SCENE := preload("res://scenes/youth_academy_screen.tscn")
const BOARD_SCENE := preload("res://scenes/board_screen.tscn")
const MATCH_SCENE := preload("res://scenes/match_screen.tscn")
const PLACEHOLDER_SCENE := preload("res://scenes/placeholder_screen.tscn")
const ONBOARDING_OVERLAY_SCENE := preload("res://scenes/onboarding_overlay.tscn")
const MAIN_MENU_SCENE := preload("res://scenes/main_menu_screen.tscn")
const LOAD_GAME_SCENE := preload("res://scenes/load_game_screen.tscn")
const NEW_GAME_SETUP_SCENE := preload("res://scenes/new_game_setup_screen.tscn")
const CAREER_TEAM_SELECTION_SCENE := preload("res://scenes/career_team_selection_screen.tscn")
const WORLD_CUP_SETUP_SCENE := preload("res://scenes/world_cup_setup_screen.tscn")
const TOURNAMENT_SETUP_SCENE := preload("res://scenes/tournament_setup_screen.tscn")
const SETTINGS_SCENE := preload("res://scenes/settings_screen.tscn")
const HELP_SCENE := preload("res://scenes/help_screen.tscn")
const ABOUT_SCENE := preload("res://scenes/about_screen.tscn")
const ACHIEVEMENTS_SCENE := preload("res://scenes/achievements_screen.tscn")
const NATIONAL_TEAM_SCENE := preload("res://scenes/national_team_screen.tscn")
const PLAYER_COMPARISON_SCENE := preload("res://scenes/player_comparison_screen.tscn")
const KIT_EDITOR_SCENE := preload("res://scenes/kit_editor_screen.tscn")
const EMBLEM_EDITOR_SCENE := preload("res://scenes/emblem_editor_screen.tscn")
const PLAYER_EDITOR_SCENE := preload("res://scenes/player_editor_screen.tscn")
const COMPETITION_EDITOR_SCENE := preload("res://scenes/competition_editor_screen.tscn")
const TROPHY_ROOM_SCENE := preload("res://scenes/trophy_room_screen.tscn")
const SEASON_RECORDS_SCENE := preload("res://scenes/season_records_screen.tscn")
const PRESS_CONFERENCE_SCENE := preload("res://scenes/press_conference_screen.tscn")
const TOURNAMENT_BRACKET_SCENE := preload("res://scenes/tournament_bracket_screen.tscn")

## Pre-career screens shown chrome-less (no sidebar/header) — mirrors
## main.py's STARTUP_SCREEN_NAMES, which CricketManagerApp.build_interface()
## uses the same way to skip the sidebar/top-bar entirely.
const STARTUP_SCREEN_NAMES := ["Main Menu", "Load Game", "New Game Setup", "Career Team Selection",
	"World Cup Setup", "Tournament Setup", "Settings", "Help", "About"]

@onready var navbar: HBoxContainer = $Layout/NavBg/NavBar
@onready var subnav: HBoxContainer = $Layout/SubNavBg/SubNav
@onready var content: Control = $Layout/Content
@onready var crest_label: Label = $Layout/HeaderBg/Header/Crest/CrestLabel
@onready var team_name_label: Label = $Layout/HeaderBg/Header/TeamBox/TeamName
@onready var team_subtitle_label: Label = $Layout/HeaderBg/Header/TeamBox/TeamSubtitle
@onready var manager_label: Label = $Layout/HeaderBg/Header/TeamBox/ManagerLabel
@onready var advance_button: Button = $Layout/HeaderBg/Header/AdvanceButton

var current_screen: Control = null
var current_screen_name: String = ""
var _nav_buttons: Dictionary = {}
var _section_buttons: Dictionary = {}
var _current_section: String = ""

var _onboarding_overlay: Control = null
var _onboarding_steps: Array = []
var _onboarding_state: Dictionary = {}


func _ready() -> void:
	add_to_group("shell")
	theme = AppTheme.build()
	_build_navbar()
	_apply_subnav_style()
	_style_header()
	advance_button.pressed.connect(_on_advance_pressed)
	refresh_header()
	_setup_onboarding_overlay()
	if "--smoke-test" in OS.get_cmdline_user_args():
		_run_smoke_test()
	elif "--screenshot-test" in OS.get_cmdline_user_args():
		_run_screenshot_test()
	else:
		show_screen("Main Menu")


func _style_header() -> void:
	var header_bg := StyleBoxFlat.new()
	header_bg.bg_color = AppTheme.SURFACE
	header_bg.set_corner_radius_all(0)
	header_bg.set_border_width_all(0)
	$Layout/HeaderBg.add_theme_stylebox_override("panel", header_bg)
	var nav_bg := StyleBoxFlat.new()
	nav_bg.bg_color = AppTheme.CARD
	nav_bg.set_corner_radius_all(0)
	nav_bg.set_border_width_all(0)
	$Layout/NavBg.add_theme_stylebox_override("panel", nav_bg)
	var subnav_bg := StyleBoxFlat.new()
	subnav_bg.bg_color = AppTheme.BACKGROUND
	subnav_bg.set_corner_radius_all(0)
	subnav_bg.set_border_width_all(0)
	$Layout/SubNavBg.add_theme_stylebox_override("panel", subnav_bg)
	var crest_box := StyleBoxFlat.new()
	crest_box.bg_color = AppTheme.GOLD
	crest_box.set_corner_radius_all(24)
	$Layout/HeaderBg/Header/Crest.add_theme_stylebox_override("panel", crest_box)
	crest_label.add_theme_color_override("font_color", AppTheme.BACKGROUND)
	crest_label.add_theme_font_size_override("font_size", 16)
	team_subtitle_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	manager_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	var advance_box := StyleBoxFlat.new()
	advance_box.bg_color = AppTheme.DANGER
	advance_box.set_corner_radius_all(8)
	advance_box.content_margin_left = 16
	advance_box.content_margin_right = 16
	advance_button.add_theme_stylebox_override("normal", advance_box)
	var advance_hover := StyleBoxFlat.new()
	advance_hover.bg_color = AppTheme.DANGER.lightened(0.15)
	advance_hover.set_corner_radius_all(8)
	advance_hover.content_margin_left = 16
	advance_hover.content_margin_right = 16
	advance_button.add_theme_stylebox_override("hover", advance_hover)
	advance_button.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	advance_button.add_theme_color_override("font_hover_color", AppTheme.TEXT_PRIMARY)
	advance_button.add_theme_font_size_override("font_size", 12)


## The persistent header — team crest initials, name, next-fixture/date
## subtitle, and the Advance Day action — is fed by get_dashboard the same
## way DashboardScreen's own cards are, so both stay in sync without a
## second source of truth for team/fixture state.
func refresh_header() -> void:
	var response := IpcBridge.call_method("get_dashboard")
	if response.has("error"):
		team_name_label.text = "Stumped!"
		return
	var result: Dictionary = response["result"]
	var team: Dictionary = result.get("team", {})
	var name: String = team.get("name", "?")
	team_name_label.text = name
	var initials := ""
	for word in name.split(" ", false):
		if not word.is_empty():
			initials += word[0]
	crest_label.text = initials.substr(0, 2).to_upper()
	var fixture = result.get("fixture")
	var date_text: String = str(result.get("date", "?"))
	if fixture:
		var opponent: String = fixture.get("away_name", "?") if fixture.get("home_team") == team.get("id") else fixture.get("home_name", "?")
		team_subtitle_label.text = "%s — next: vs %s" % [date_text, opponent]
	else:
		team_subtitle_label.text = date_text
	manager_label.text = "Managed by %s" % str(result.get("manager_name", "Manager"))


## First-run guided tutorial (ports database.py's ONBOARDING_STEPS/
## get_onboarding_state/advance_onboarding/dismiss_onboarding, exposed over
## IPC since v0.68.0 but previously unused by any UI in either client).
## Steps are fetched once here; state is re-fetched only after a real
## navigation or a Next/Skip action, not every frame.
func _setup_onboarding_overlay() -> void:
	_onboarding_overlay = ONBOARDING_OVERLAY_SCENE.instantiate()
	add_child(_onboarding_overlay)
	_onboarding_overlay.advanced.connect(_on_onboarding_advanced)
	_onboarding_overlay.skipped.connect(_on_onboarding_skipped)
	var steps_response := IpcBridge.call_method("get_onboarding_steps")
	if not steps_response.has("error"):
		_onboarding_steps = steps_response["result"].get("steps", [])
	var state_response := IpcBridge.call_method("get_onboarding_state")
	if not state_response.has("error"):
		_onboarding_state = state_response["result"]


func _on_onboarding_advanced() -> void:
	var response := IpcBridge.call_method("advance_onboarding_step")
	if not response.has("error"):
		_onboarding_state = response["result"]
	_sync_onboarding_overlay()


func _on_onboarding_skipped() -> void:
	var response := IpcBridge.call_method("dismiss_onboarding")
	if not response.has("error"):
		_onboarding_state = response["result"]
	_sync_onboarding_overlay()


func _sync_onboarding_overlay() -> void:
	if _onboarding_overlay == null:
		return
	var step_id = _onboarding_state.get("current_step")
	if step_id == null or _onboarding_state.get("dismissed", false):
		_onboarding_overlay.hide_overlay()
		return
	var step_index := -1
	for i in range(_onboarding_steps.size()):
		if _onboarding_steps[i].get("id") == step_id:
			step_index = i
			break
	if step_index == -1 or _onboarding_steps[step_index].get("screen") != current_screen_name:
		_onboarding_overlay.hide_overlay()
		return
	_onboarding_overlay.show_step(_onboarding_steps[step_index], step_index + 1, _onboarding_steps.size())


func _on_advance_pressed() -> void:
	advance_button.disabled = true
	var response := IpcBridge.call_method("advance_day")
	advance_button.disabled = false
	if response.has("error"):
		push_error("Shell: advance_day failed: %s" % response["error"])
		return
	refresh_header()
	if current_screen and current_screen.has_method("refresh"):
		current_screen.refresh()


## Dev-only: captures a handful of screens to PNG so a visual theme/layout
## pass can actually be reviewed as pixels, not just smoke-test title text.
## Not wired into any shipped build path.
func _run_screenshot_test() -> void:
	var targets := ["Dashboard", "Inbox", "Squad", "Selection", "Training", "Youth Academy",
		"Medical Centre", "Match", "Recruitment", "Transfers", "Offers", "Staff", "Staff Market",
		"Finances", "Facilities", "Trophy Room", "Cup",
		# Pre-career/startup screens (v0.87.0) — never captured before; only
		# in-career screens were in this list. These render fine even
		# against an existing career save (their own refresh() calls fail
		# gracefully like every other screen's backend-error path), so it's
		# safe to snapshot them here without disrupting the in-career save.
		"Main Menu", "Load Game", "New Game Setup", "Career Team Selection", "Tournament Setup", "World Cup Setup",
		"Settings", "Help"]
	for i in range(targets.size()):
		show_screen(targets[i])
		await get_tree().process_frame
		await get_tree().process_frame
		var image := get_viewport().get_texture().get_image()
		image.save_png("res://../screenshots/godot_%s.png" % targets[i].to_lower().replace(" ", "_"))
	show_screen("Match")
	await get_tree().process_frame
	if "start_button" in current_screen and not current_screen.start_button.disabled:
		current_screen.start_button.pressed.emit()
		current_screen.next_ball_button.pressed.emit()
		current_screen.next_ball_button.pressed.emit()
		await get_tree().process_frame
		await get_tree().process_frame
		var image := get_viewport().get_texture().get_image()
		image.save_png("res://../screenshots/godot_match_live.png")
	show_screen("Help")
	await get_tree().process_frame
	if "article_list" in current_screen and current_screen.article_list.get_child_count() > 0:
		current_screen.article_list.get_child(0).pressed.emit()
		await get_tree().process_frame
		var image := get_viewport().get_texture().get_image()
		image.save_png("res://../screenshots/godot_help_article_expanded.png")
	show_screen("Selection")
	await get_tree().process_frame
	if "_tab_buttons" in current_screen and current_screen._tab_buttons.size() > 1:
		current_screen._tab_buttons[1].pressed.emit()
		await get_tree().process_frame
		await get_tree().process_frame
		var image := get_viewport().get_texture().get_image()
		image.save_png("res://../screenshots/godot_selection_aggression.png")
	show_screen("Squad")
	await get_tree().process_frame
	if "_hover_card" in current_screen and current_screen._hover_card != null:
		var row_list: VBoxContainer = current_screen.get_node("ScrollContainer/RowList")
		if row_list.get_child_count() > 1:
			row_list.get_child(1).get_child(0).mouse_entered.emit()
			await get_tree().process_frame
			var image := get_viewport().get_texture().get_image()
			image.save_png("res://../screenshots/godot_squad_hover_card.png")
			row_list.get_child(1).get_child(0).mouse_exited.emit()
	if "_profile_modal" in current_screen and current_screen._profile_modal != null:
		var row_list2: VBoxContainer = current_screen.get_node("ScrollContainer/RowList")
		if row_list2.get_child_count() > 1:
			var click := InputEventMouseButton.new()
			click.pressed = true
			click.button_index = MOUSE_BUTTON_LEFT
			row_list2.get_child(1).get_child(0).gui_input.emit(click)
			await get_tree().process_frame
			var profile_image := get_viewport().get_texture().get_image()
			profile_image.save_png("res://../screenshots/godot_squad_click_to_profile.png")
	get_tree().quit(0)


## Cycles through every registered screen, printing a pass/fail summary and
## exiting with a non-zero status if any screen's title shows a backend
## error — a scriptable, no-GUI way to catch regressions across the whole
## nav tree, not just one screen at a time.
func _run_smoke_test() -> void:
	var failures := []
	for group in NAV_GROUPS:
		for screen_name in group[1]:
			show_screen(screen_name)
			var summary := _describe_screen(current_screen)
			print("SMOKE TEST [%s]: %s" % [screen_name, summary])
			if "backend error" in summary:
				failures.append(screen_name)
	if not _exercise_advance_day():
		failures.append("Dashboard advance_day flow")
	if not _exercise_row_click("Inbox"):
		failures.append("Inbox mark-read row click")
	if not _exercise_row_click("Transfers"):
		failures.append("Transfers submit-offer row click")
	if not _exercise_row_button("Offers"):
		failures.append("Offers accept/reject row button")
	if not _exercise_row_click("Staff Market"):
		failures.append("Staff Market sign row click")
	if not _exercise_row_button("Facilities"):
		failures.append("Facilities upgrade row button")
	if not _exercise_row_button("Staff"):
		failures.append("Staff release row button")
	if not _exercise_row_click("Selection"):
		failures.append("Selection toggle-XI row click")
	if not _exercise_row_button("Selection"):
		failures.append("Selection captain/keeper row button")
	if not _exercise_batting_order():
		failures.append("Selection batting-order up/down row button")
	if not _exercise_squad_tabs():
		failures.append("Squad Attributes tab switch")
	if not _exercise_selection_aggression():
		failures.append("Selection Aggression tab style/aggro cycle")
	if not _exercise_hover_card():
		failures.append("Squad player hover card")
	if not _exercise_click_to_profile():
		failures.append("Squad click-to-profile")
	if not _exercise_training_interactivity():
		failures.append("Training programme/intensity cycle + simulate")
	if not _exercise_academy_interactivity():
		failures.append("Youth Academy focus cycle + recruit")
	if not _exercise_recruitment_nav():
		failures.append("Recruitment nav shortcut button")
	if not _exercise_live_match():
		failures.append("Match live ball-by-ball feed")
	if not _exercise_onboarding():
		failures.append("Onboarding tutorial overlay")
	if not _exercise_startup_flow():
		failures.append("Startup flow (Main Menu -> New Game -> Team Selection -> Dashboard)")
	if not _exercise_settings():
		failures.append("Settings cycle + save")
	if not _exercise_quit_to_menu():
		failures.append("Sidebar Quit to Main Menu")
	if not _exercise_help():
		failures.append("Help topic switch + article expand + search")
	if not _exercise_team_talk():
		failures.append("Dashboard team talk tone button")
	if not _exercise_press_conference():
		failures.append("Press Conference tone button")
	if not _exercise_save_slots():
		failures.append("Load Game save-slot create/list/delete")
	if failures.is_empty():
		print("SMOKE TEST: all %d screens OK" % _screen_count())
		get_tree().quit(0)
	else:
		print("SMOKE TEST: FAILED — %s" % ", ".join(failures))
		get_tree().quit(1)


## Exercises the first real interactive (write) flow end-to-end by emitting
## the Dashboard's actual button signal — not just calling the IPC method
## directly — so a broken signal connection would fail this too.
func _exercise_advance_day() -> bool:
	show_screen("Dashboard")
	var before_date := team_subtitle_label.text
	advance_button.pressed.emit()
	var summary := _describe_screen(current_screen)
	print("SMOKE TEST [Dashboard/advance_day]: %s -> %s (%s)" % [before_date, team_subtitle_label.text, summary])
	return "backend error" not in summary and team_subtitle_label.text != before_date


## Exercises a table_screen.gd row_action end-to-end by emitting a real
## mouse-click InputEvent on the first data row's gui_input signal — the
## same signal a genuine click delivers — not by calling the IPC method
## directly, so a broken wiring (wrong param names, unconnected signal)
## fails this too.
func _exercise_row_click(screen_name: String) -> bool:
	show_screen(screen_name)
	var screen := current_screen
	if not screen.has_node("ScrollContainer/RowList"):
		print("SMOKE TEST [%s/row-click]: not a table screen" % screen_name)
		return false
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	if row_list.get_child_count() < 2:
		print("SMOKE TEST [%s/row-click]: no data rows to click" % screen_name)
		return true
	var first_row := _row_hbox(row_list, 1)
	var event := InputEventMouseButton.new()
	event.pressed = true
	event.button_index = MOUSE_BUTTON_LEFT
	first_row.gui_input.emit(event)
	var summary := _describe_screen(current_screen)
	print("SMOKE TEST [%s/row-click]: %s" % [screen_name, summary])
	return "backend error" not in summary


## Exercises table_screen.gd's row_buttons (Accept/Reject-style multi-action
## rows) by pressing the first data row's first button — a real
## Button.pressed emit, same as _exercise_row_click does for whole-row
## actions.
func _exercise_row_button(screen_name: String) -> bool:
	show_screen(screen_name)
	var screen := current_screen
	if not screen.has_node("ScrollContainer/RowList"):
		print("SMOKE TEST [%s/row-button]: not a table screen" % screen_name)
		return false
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	if row_list.get_child_count() < 2:
		print("SMOKE TEST [%s/row-button]: no data rows with buttons" % screen_name)
		return true
	var first_row := _row_hbox(row_list, 1)
	var buttons := first_row.get_children().filter(func(c): return c is Button)
	if buttons.is_empty():
		print("SMOKE TEST [%s/row-button]: row has no buttons" % screen_name)
		return false
	buttons[0].pressed.emit()
	var summary := _describe_screen(current_screen)
	print("SMOKE TEST [%s/row-button]: %s" % [screen_name, summary])
	return "backend error" not in summary


## v0.81.0: real button-signal emit (not a direct IPC call) for the new
## Dashboard team-talk widget — confirms both the morale-changing call and
## the once-per-day disable actually happen through the wired-up UI.
func _exercise_team_talk() -> bool:
	show_screen("Dashboard")
	var screen := current_screen
	if not screen.has_node("Bottom/Left/FixtureCard/Box/TeamTalk/Tones"):
		print("SMOKE TEST [Dashboard/team-talk]: TeamTalk widget not found")
		return false
	var tones: HBoxContainer = screen.get_node("Bottom/Left/FixtureCard/Box/TeamTalk/Tones")
	var calm_button: Button = tones.get_node("Calm")
	if calm_button.disabled:
		print("SMOKE TEST [Dashboard/team-talk]: already unavailable before exercising (stale dev save?)")
		return true
	calm_button.pressed.emit()
	var reaction: Label = screen.get_node("Bottom/Left/FixtureCard/Box/TeamTalk/Reaction")
	print("SMOKE TEST [Dashboard/team-talk]: reaction=%s disabled_after=%s" % [reaction.text, calm_button.disabled])
	return reaction.text != "" and calm_button.disabled


## v0.81.0: real button-signal emit for the new Press Conference screen —
## confirms the answer round-trip actually updates the result label through
## the wired-up UI, not just via a direct IPC call.
func _exercise_press_conference() -> bool:
	show_screen("Press Conference")
	var screen := current_screen
	if not screen.has_node("Card/Box/Tones"):
		print("SMOKE TEST [Press Conference]: Tones widget not found")
		return false
	var tones: HBoxContainer = screen.get_node("Card/Box/Tones")
	var confident_button: Button = tones.get_node("Confident")
	if confident_button.disabled:
		print("SMOKE TEST [Press Conference]: already unavailable before exercising (stale dev save?)")
		return true
	confident_button.pressed.emit()
	var result: Label = screen.get_node("Card/Box/Result")
	print("SMOKE TEST [Press Conference]: result=%s disabled_after=%s" % [result.text, confident_button.disabled])
	return result.text != "" and confident_button.disabled


## Exercises move_batting_up/down end-to-end: adds a second player to the XI
## (so there's someone to swap with — the first exercises already put one
## player in the XI as the topmost row), presses the first row's DOWN
## button, then checks the row order actually changed — not just that the
## call returned without error, same real-state-change standard as every
## other write-flow exercise in this file.
func _exercise_batting_order() -> bool:
	show_screen("Selection")
	var screen := current_screen
	if not screen.has_node("ScrollContainer/RowList"):
		print("SMOKE TEST [Selection/batting-order]: not a table screen")
		return false
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	if row_list.get_child_count() < 3:
		print("SMOKE TEST [Selection/batting-order]: fewer than 2 data rows to swap")
		return true
	# Don't assume anything about state left over from earlier exercises or
	# earlier smoke-test runs against the same persistent dev save (its XI
	# may already have players in it, or none) — explicitly guarantee the
	# first two rows are XI members before testing the reorder itself.
	_ensure_row_in_xi(screen, 1)
	_ensure_row_in_xi(screen, 2)
	row_list = screen.get_node("ScrollContainer/RowList")
	var first_row := _row_hbox(row_list, 1)
	var name_before: String = (first_row.get_child(1) as Label).text
	var buttons := first_row.get_children().filter(func(c): return c is Button)
	if buttons.is_empty():
		print("SMOKE TEST [Selection/batting-order]: no row buttons found")
		return false
	buttons[buttons.size() - 1].pressed.emit()  # DOWN is configured last
	row_list = screen.get_node("ScrollContainer/RowList")
	var name_after: String = (_row_hbox(row_list, 1).get_child(1) as Label).text
	var summary := _describe_screen(current_screen)
	print("SMOKE TEST [Selection/batting-order]: %s -> %s (%s)" % [name_before, name_after, summary])
	return "backend error" not in summary and name_before != name_after


## Clicks a Selection row to add it to the XI, but only if it isn't already
## a member (empty ORDER/C/WK label) — so batting-order testing works the
## same whether the persistent dev save's XI is empty or already populated.
func _ensure_row_in_xi(screen: Control, index: int) -> void:
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	if row_list.get_child_count() <= index:
		return
	var row := _row_hbox(row_list, index)
	var status_label := row.get_child(5) as Label
	if status_label.text.is_empty():
		var click := InputEventMouseButton.new()
		click.pressed = true
		click.button_index = MOUSE_BUTTON_LEFT
		row.gui_input.emit(click)


## table_screen.gd wraps each data row in a PanelContainer (for the zebra
## background) whose only child is the HBoxContainer that actually carries
## the row's gui_input connection and Label/Button children — smoke-test
## helpers need that inner container, not the panel wrapper.
func _row_hbox(row_list: VBoxContainer, index: int) -> HBoxContainer:
	return row_list.get_child(index).get_child(0) as HBoxContainer


func _row_header_text(row_list: VBoxContainer) -> String:
	var parts := []
	for child in _row_hbox(row_list, 0).get_children():
		if child is Label:
			parts.append((child as Label).text)
	return "/".join(parts)


## Exercises table_screen.gd's tabbed sub-navigation (Squad's GENERAL
## INFO/ATTRIBUTES tabs) by pressing the second tab's real Button.pressed
## signal and checking the header row actually shows different columns
## afterwards — not just that no error was thrown.
func _exercise_squad_tabs() -> bool:
	show_screen("Squad")
	var screen := current_screen
	if not ("_tab_buttons" in screen) or screen._tab_buttons.size() < 2:
		print("SMOKE TEST [Squad/tabs]: expected at least 2 tabs")
		return false
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	var header_before := _row_header_text(row_list)
	screen._tab_buttons[1].pressed.emit()
	row_list = screen.get_node("ScrollContainer/RowList")
	var header_after := _row_header_text(row_list)
	print("SMOKE TEST [Squad/tabs]: %s -> %s" % [header_before, header_after])
	return header_before != header_after and "BATTING" in header_after


## Exercises Selection's AGGRESSION tab: ensures a player is in the XI,
## switches tabs, then presses the real STYLE and AGGRO buttons and checks
## the row's own text actually changed each time — real state, not just
## "no error".
func _exercise_selection_aggression() -> bool:
	show_screen("Selection")
	var screen := current_screen
	_ensure_row_in_xi(screen, 1)
	if not ("_tab_buttons" in screen) or screen._tab_buttons.size() < 2:
		print("SMOKE TEST [Selection/aggression]: expected an AGGRESSION tab")
		return false
	screen._tab_buttons[1].pressed.emit()
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	var row := _row_hbox(row_list, 1)
	var style_before: String = (row.get_child(2) as Label).text
	var buttons := row.get_children().filter(func(c): return c is Button)
	if buttons.size() < 2:
		print("SMOKE TEST [Selection/aggression]: expected STYLE/AGGRO buttons")
		return false
	buttons[0].pressed.emit()  # STYLE
	row_list = screen.get_node("ScrollContainer/RowList")
	row = _row_hbox(row_list, 1)
	var style_after: String = (row.get_child(2) as Label).text
	var aggro_before: String = (row.get_child(3) as Label).text
	buttons = row.get_children().filter(func(c): return c is Button)
	buttons[1].pressed.emit()  # AGGRO
	row_list = screen.get_node("ScrollContainer/RowList")
	row = _row_hbox(row_list, 1)
	var aggro_after: String = (row.get_child(3) as Label).text
	print("SMOKE TEST [Selection/aggression]: style %s -> %s, aggro %s -> %s" %
		[style_before, style_after, aggro_before, aggro_after])
	return style_before != style_after and aggro_before != aggro_after


## Exercises table_screen.gd's player hover card (ports
## ui/widgets/quick_card.py) by emitting the first data row's real
## mouse_entered/mouse_exited signals and checking the card actually
## shows/hides with the right player's name, not just that no error fired.
func _exercise_hover_card() -> bool:
	show_screen("Squad")
	var screen := current_screen
	if not ("_hover_card" in screen) or screen._hover_card == null:
		print("SMOKE TEST [Squad/hover-card]: no hover card found")
		return false
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	var row := _row_hbox(row_list, 1)
	var expected_name: String = (row.get_child(1) as Label).text
	row.mouse_entered.emit()
	var hover_card = screen._hover_card
	var visible_after_enter: bool = hover_card.visible
	var shown_name: String = hover_card.name_label.text
	row.mouse_exited.emit()
	var visible_after_exit: bool = hover_card.visible
	print("SMOKE TEST [Squad/hover-card]: shown=%s name=%s (expected %s) hidden_after_exit=%s" %
		[visible_after_enter, shown_name, expected_name, not visible_after_exit])
	return visible_after_enter and shown_name == expected_name and not visible_after_exit


## Exercises table_screen.gd's click-to-profile (ports
## ui/player_modals.py's PlayerDetailModal): emits a real left-click on the
## first Squad data row and checks the profile modal actually opens with
## the right player's name and attribute data, not just that no error fired.
func _exercise_click_to_profile() -> bool:
	show_screen("Squad")
	var screen := current_screen
	if not ("_profile_modal" in screen) or screen._profile_modal == null:
		print("SMOKE TEST [Squad/click-to-profile]: no profile modal found")
		return false
	var row_list: VBoxContainer = screen.get_node("ScrollContainer/RowList")
	var row := _row_hbox(row_list, 1)
	var expected_name: String = (row.get_child(1) as Label).text
	var event := InputEventMouseButton.new()
	event.pressed = true
	event.button_index = MOUSE_BUTTON_LEFT
	row.gui_input.emit(event)
	var modal: PlayerProfileModal = screen._profile_modal
	var visible_after_click: bool = modal.visible
	var shown_name: String = modal.name_label.text
	var has_attribute_rows: bool = modal.groups_box.get_child_count() > 0
	modal.hide_modal()
	print("SMOKE TEST [Squad/click-to-profile]: shown=%s name=%s (expected %s) attrs=%s hidden_after_close=%s" %
		[visible_after_click, shown_name, expected_name, has_attribute_rows, not modal.visible])
	return visible_after_click and shown_name == expected_name and has_attribute_rows and not modal.visible


## Exercises training_screen.gd's real interactivity (ports
## ui/training.py): emits the FOCUS button's real pressed signal and
## checks the selected player's programme actually changes on the backend
## (round-tripped through get_training on the next refresh), then presses
## SIMULATE 30 CALENDAR DAYS and checks it reports real points gained —
## not just that no error fired.
func _exercise_training_interactivity() -> bool:
	show_screen("Training")
	var screen := current_screen
	if not ("selected_id" in screen) or screen.selected_id == -1:
		print("SMOKE TEST [Training/interactivity]: no selected player")
		return false
	var focus_before: String = screen.focus_button.text
	screen.focus_button.pressed.emit()
	var focus_after: String = screen.focus_button.text
	var intensity_before: String = screen.intensity_button.text
	screen.intensity_button.pressed.emit()
	var days_before: String = screen.days_button.text
	screen.days_button.pressed.emit()
	screen.bulk_button.pressed.emit()
	var bulk_toast: String = screen.toast_label.text
	screen.month_button.pressed.emit()
	var toast: String = screen.toast_label.text
	print("SMOKE TEST [Training/interactivity]: focus %s -> %s, intensity %s -> %s, days %s -> %s, bulk=%s, toast=%s" %
		[focus_before, focus_after, intensity_before, screen.intensity_button.text,
		 days_before, screen.days_button.text, bulk_toast, toast])
	return (focus_before != focus_after and intensity_before != screen.intensity_button.text and
		days_before != screen.days_button.text and "applied" in bulk_toast and "points gained" in toast)


## Exercises youth_academy_screen.gd's real interactivity (ports
## ui/youth.py): emits the FOCUS button's real pressed signal and checks
## it round-trips through the backend, then emits RECRUIT YOUTH's pressed
## signal and checks the squad size actually grew (a real recruit_youth
## call, not just "no error") and a toast reports the count.
func _exercise_academy_interactivity() -> bool:
	show_screen("Youth Academy")
	var screen := current_screen
	if not ("players" in screen):
		print("SMOKE TEST [Youth Academy/interactivity]: not a recognised screen")
		return false
	var focus_before: String = screen.focus_button.text
	screen.focus_button.pressed.emit()
	var focus_after: String = screen.focus_button.text
	var count_before: int = screen.players.size()
	screen.recruit_button.pressed.emit()
	var count_after: int = screen.players.size()
	var toast: String = screen.toast_label.text
	print("SMOKE TEST [Youth Academy/interactivity]: focus %s -> %s, squad %d -> %d, toast=%s" %
		[focus_before, focus_after, count_before, count_after, toast])
	return focus_before != focus_after and count_after > count_before and "Recruited" in toast


## Exercises recruitment_screen.gd's shortcut nav buttons (ports
## ui/recruitment.py's tile buttons): emits the real "ACADEMY" button
## press and checks the shell actually navigated to Youth Academy.
func _exercise_recruitment_nav() -> bool:
	show_screen("Recruitment")
	var screen := current_screen
	if not screen.has_node("NavButtons/Academy"):
		print("SMOKE TEST [Recruitment/nav]: no nav buttons found")
		return false
	screen.get_node("NavButtons/Transfers").pressed.emit()
	var reached_transfers := current_screen_name == "Transfers"
	show_screen("Recruitment")
	current_screen.get_node("NavButtons/StaffMarket").pressed.emit()
	var reached_staff_market := current_screen_name == "Staff Market"
	if not (reached_transfers and reached_staff_market):
		print("SMOKE TEST [Recruitment/nav]: transfers=%s staff_market=%s" % [reached_transfers, reached_staff_market])
		return false
	show_screen("Recruitment")
	screen = current_screen
	screen.get_node("NavButtons/Academy").pressed.emit()
	var navigated := current_screen_name == "Youth Academy"
	print("SMOKE TEST [Recruitment/nav]: navigated_to=%s" % current_screen_name)
	return navigated


## Exercises match_screen.gd's real live ball-by-ball feed end to end
## (ports ui/match_view.py's simulate_ball() loop): emits the real
## START MATCH button press, checks the live view actually appears, emits
## a real NEXT BALL press and checks the commentary feed actually grew,
## then emits real SKIP presses until the match reports completed (a
## real match_engine.Match run to conclusion via the IPC bridge, not a
## mocked result) — bounded so a stalled match fails loudly instead of
## hanging the smoke test.
## Exercises match_screen.gd's pre-match extras (ports two backend
## features exposed over IPC since v0.63.0/v0.65.0 but never consumed by
## any UI in either client until now): a real PITCH button press that
## actually changes the selection (only meaningful when the user's team
## is the home side — skipped harmlessly otherwise), and a real
## OPPOSITION REPORT press that actually opens the modal with data.
func _exercise_pre_match_extras(screen: Control) -> bool:
	if screen._is_home_fixture:
		var pitch_before: String = screen.pitch_button.text
		screen.pitch_button.pressed.emit()
		if screen.pitch_button.text == pitch_before:
			print("SMOKE TEST [Match/pre-match]: PITCH button had no real effect")
			return false
	screen.opposition_button.pressed.emit()
	var report_visible: bool = screen._opposition_report_modal.visible
	var title_text: String = screen._opposition_report_modal.title_label.text
	screen._opposition_report_modal.hide_modal()
	print("SMOKE TEST [Match/pre-match]: home=%s opposition_report_shown=%s (%s)" %
		[screen._is_home_fixture, report_visible, title_text])
	return report_visible


func _exercise_live_match() -> bool:
	show_screen("Match")
	var screen := current_screen
	if not ("live_match_box" in screen):
		print("SMOKE TEST [Match/live-feed]: not a recognised screen")
		return false
	if screen.pre_match_box.visible == false:
		print("SMOKE TEST [Match/live-feed]: pre-match view not shown initially")
		return false
	if not _exercise_pre_match_extras(screen):
		return false
	screen.start_button.pressed.emit()
	if not screen.live_match_box.visible:
		print("SMOKE TEST [Match/live-feed]: live view did not appear after START MATCH")
		return false
	var commentary_before: int = screen.commentary_list.get_child_count()
	screen.next_ball_button.pressed.emit()
	var commentary_after: int = screen.commentary_list.get_child_count()
	if commentary_after <= commentary_before:
		print("SMOKE TEST [Match/live-feed]: commentary feed did not grow after NEXT BALL")
		return false
	screen.predict_button.pressed.emit()
	var field_before: String = screen.field_button.text
	screen.field_button.pressed.emit()
	screen.change_bowler_button.pressed.emit()
	print("SMOKE TEST [Match/tactics]: prediction=%s field %s -> %s" %
		[screen.prediction_label.text, field_before, screen.field_button.text])
	if screen.prediction_label.text.is_empty() or field_before == screen.field_button.text:
		print("SMOKE TEST [Match/tactics]: PREDICT or FIELD button had no real effect")
		return false
	screen.drs_button.pressed.emit()
	if not screen.status_label.text.begins_with("DRS"):
		print("SMOKE TEST [Match/tactics]: DRS button had no effect on status_label (got: %s)" % screen.status_label.text)
		return false
	var speed_before: String = screen.speed_button.text
	screen.speed_button.pressed.emit()
	screen.auto_button.pressed.emit()
	var auto_started: bool = screen.auto_play and not screen.auto_timer.is_stopped()
	screen.auto_button.pressed.emit()
	var auto_stopped: bool = not screen.auto_play and screen.auto_timer.is_stopped()
	print("SMOKE TEST [Match/tactics]: DRS=%s speed %s -> %s, auto started=%s stopped=%s" %
		[screen.status_label.text, speed_before, screen.speed_button.text, auto_started, auto_stopped])
	if speed_before == screen.speed_button.text or not auto_started or not auto_stopped:
		print("SMOKE TEST [Match/tactics]: SPEED or AUTO button had no real effect")
		return false
	screen.over_button.pressed.emit()
	if not _exercise_stats_hub(screen):
		return false
	var attempts := 0
	while not screen.match_completed and attempts < 20:
		screen.skip_button.pressed.emit()
		attempts += 1
	print("SMOKE TEST [Match/live-feed]: commentary %d -> %d, completed=%s after %d skip(s)" %
		[commentary_before, commentary_after, screen.match_completed, attempts])
	return screen.match_completed


## Exercises match_screen.gd's Stats Hub tabs (ports ui/match_view.py's
## Worm/Momentum/Manhattan/Ring/Boundary/Pitch-map/Partnerships): emits
## real tab-button presses and checks the client-side accumulators
## actually captured data from the balls already simulated (shot_events/
## bowling_events non-empty after an over) and that switching tabs
## actually changes stats_canvas' render mode and toggles the right
## panel visible — not just that no error fired.
func _exercise_stats_hub(screen: Control) -> bool:
	if screen.shot_events.is_empty() or screen.bowling_events.is_empty():
		print("SMOKE TEST [Match/stats-hub]: no shot/bowling events captured after an over")
		return false
	screen.get_node("LiveMatchBox/StatsTabBar/ShotMapTab").pressed.emit()
	var shot_map_ok: bool = screen.stats_card.visible and screen.stats_canvas.mode == "shot_map"
	screen.get_node("LiveMatchBox/StatsTabBar/WormTab").pressed.emit()
	var worm_ok: bool = screen.stats_card.visible and screen.stats_canvas.mode == "worm"
	screen.get_node("LiveMatchBox/StatsTabBar/PartnershipsTab").pressed.emit()
	var partnerships_ok: bool = screen.partnerships_card.visible and not screen.scorecard_row.visible
	# v0.86.0: Batting/Bowling/Summary replaced the single always-both-visible
	# scorecard row — exercise each tab's real button-signal emit and check
	# the right card (and only that card) actually shows.
	screen.get_node("LiveMatchBox/StatsTabBar/BattingTab").pressed.emit()
	var batting_ok: bool = (screen.scorecard_row.visible and screen.batting_card.visible
		and not screen.bowling_card.visible and not screen.stats_card.visible and not screen.partnerships_card.visible)
	screen.get_node("LiveMatchBox/StatsTabBar/BowlingTab").pressed.emit()
	var bowling_ok: bool = (screen.scorecard_row.visible and screen.bowling_card.visible
		and not screen.batting_card.visible and screen.stamina_label.text != "")
	screen.get_node("LiveMatchBox/StatsTabBar/SummaryTab").pressed.emit()
	var summary_ok: bool = (screen.summary_card.visible and not screen.scorecard_row.visible
		and screen.summary_list.get_child_count() > 0)
	# v0.92.0: LiveStripCard sits outside the tab-gated scorecard_row, so it
	# must stay visible across every tab switch above, with real bowler
	# figures (not the "0.0-0-0-0" placeholder) once a ball's been bowled.
	var strip_ok: bool = (screen.live_strip_card.visible and screen.striker_name_label.text != "—"
		and screen.strip_bowler_name_label.text != "—" and "(O-M-R-W)" in screen.strip_bowler_figures_label.text)
	print("SMOKE TEST [Match/stats-hub]: shot_map=%s worm=%s partnerships=%s batting=%s bowling=%s summary=%s strip=%s (events: %d shots, %d deliveries)" %
		[shot_map_ok, worm_ok, partnerships_ok, batting_ok, bowling_ok, summary_ok, strip_ok, screen.shot_events.size(), screen.bowling_events.size()])
	return shot_map_ok and worm_ok and partnerships_ok and batting_ok and bowling_ok and summary_ok and strip_ok


## Exercises the onboarding overlay end-to-end: real NEXT/SKIP TUTORIAL
## Button.pressed emits (not direct IPC calls), checking the card actually
## shows only on its matching screen and actually hides after each action —
## idempotent against a persistent dev save where a prior run already
## dismissed the tutorial.
func _exercise_onboarding() -> bool:
	var state_response := IpcBridge.call_method("get_onboarding_state")
	if state_response.has("error"):
		print("SMOKE TEST [Onboarding]: backend error")
		return false
	if state_response["result"].get("dismissed", false):
		show_screen("Dashboard")
		var hidden_ok: bool = not _onboarding_overlay.visible
		print("SMOKE TEST [Onboarding]: already dismissed, overlay hidden=%s" % hidden_ok)
		return hidden_ok
	show_screen("Dashboard")
	var shown_on_dashboard: bool = _onboarding_overlay.visible
	var title_before: String = _onboarding_overlay.title_label.text
	_onboarding_overlay.next_button.pressed.emit()
	var hidden_after_next: bool = not _onboarding_overlay.visible
	show_screen("Squad")
	var shown_on_squad: bool = _onboarding_overlay.visible
	_onboarding_overlay.skip_button.pressed.emit()
	var hidden_after_skip: bool = not _onboarding_overlay.visible
	show_screen("Training")
	var stays_hidden: bool = not _onboarding_overlay.visible
	print("SMOKE TEST [Onboarding]: dashboard_shown=%s (%s) hidden_after_next=%s squad_shown=%s hidden_after_skip=%s stays_hidden=%s" %
		[shown_on_dashboard, title_before, hidden_after_next, shown_on_squad, hidden_after_skip, stays_hidden])
	return shown_on_dashboard and hidden_after_next and shown_on_squad and hidden_after_skip and stays_hidden


## Exercises the full pre-career flow end-to-end via real Button.pressed
## emits: Main Menu -> New Game Setup (manager identity) -> Career Team
## Selection -> Dashboard, checking the created manager's name actually
## reaches the persistent header — not just that no error fired. Ports
## src/views/screens/new_game_setup.py + career_team_selection.py, which
## previously had zero Godot equivalent (fell through to a placeholder).
## Run last: it switches the actively managed club entirely, so any
## earlier exercise's squad/XI state on the original default team no
## longer applies afterwards.
func _exercise_startup_flow() -> bool:
	show_screen("Main Menu")
	var chrome_hidden_on_menu: bool = not $Layout/HeaderBg.visible and not $Layout/NavBg.visible
	var menu_screen := current_screen
	menu_screen.get_node("Menu/NewGameButton").pressed.emit()
	var reached_setup: bool = current_screen_name == "New Game Setup"
	if not reached_setup:
		print("SMOKE TEST [Startup flow]: NEW GAME did not reach New Game Setup (got %s)" % current_screen_name)
		return false
	var setup_screen := current_screen
	var name_edit: LineEdit = setup_screen.get_node("Row/ProfileCard/Box/NameEdit")
	name_edit.text = "Smoke Test Manager"
	setup_screen.get_node("Footer/ContinueButton").pressed.emit()
	var reached_team_selection: bool = current_screen_name == "Career Team Selection"
	if not reached_team_selection:
		print("SMOKE TEST [Startup flow]: SAVE & CONTINUE did not reach Career Team Selection (got %s)" % current_screen_name)
		return false
	var team_screen := current_screen
	var has_selection: bool = team_screen._selected_id != -1
	team_screen.get_node("Footer/ConfirmButton").pressed.emit()
	var reached_dashboard: bool = current_screen_name == "Dashboard"
	var chrome_visible_after: bool = $Layout/HeaderBg.visible and $Layout/NavBg.visible
	var manager_name_shown: bool = manager_label.text.find("Smoke Test Manager") != -1
	print("SMOKE TEST [Startup flow]: chrome_hidden_on_menu=%s reached_setup=%s reached_team_selection=%s has_selection=%s reached_dashboard=%s chrome_visible_after=%s manager_shown=%s (%s)" %
		[chrome_hidden_on_menu, reached_setup, reached_team_selection, has_selection, reached_dashboard, chrome_visible_after, manager_name_shown, manager_label.text])
	return (chrome_hidden_on_menu and reached_setup and reached_team_selection and has_selection
		and reached_dashboard and chrome_visible_after and manager_name_shown)


## Exercises settings_screen.gd's real interactivity (ports ui/settings.py):
## cycles GAME SPEED via a real Button.pressed emit, saves, then re-fetches
## get_user_settings directly to confirm the change actually persisted —
## not just that the button's own label text changed.
func _exercise_settings() -> bool:
	show_screen("Settings")
	var screen := current_screen
	if not ("save_button" in screen):
		print("SMOKE TEST [Settings]: not a recognised screen")
		return false
	var speed_dropdown: OptionButton = screen._cycle_buttons["game_speed"]
	var speed_before: String = speed_dropdown.get_item_text(speed_dropdown.selected)
	speed_dropdown.selected = (speed_dropdown.selected + 1) % speed_dropdown.item_count
	speed_dropdown.item_selected.emit(speed_dropdown.selected)
	var speed_after: String = speed_dropdown.get_item_text(speed_dropdown.selected)
	screen.save_button.pressed.emit()
	var response := IpcBridge.call_method("get_user_settings")
	var persisted_speed: String = str(response.get("result", {}).get("settings", {}).get("game_speed", ""))
	print("SMOKE TEST [Settings]: speed %s -> %s, persisted=%s, message=%s" %
		[speed_before, speed_after, persisted_speed, screen.message_label.text])
	var back_ok := _exercise_settings_back_context()
	return (speed_before != speed_after and persisted_speed == speed_after
		and screen.message_label.text == "Settings saved" and back_ok)


## v0.89.0: confirms the Back button's destination actually depends on
## whether a career is active — real Button.pressed emit each way, not a
## direct function call, so a broken signal connection fails this too.
func _exercise_settings_back_context() -> bool:
	show_screen("Settings")
	var screen := current_screen
	screen.back_button.pressed.emit()
	var landed_in_career: bool = current_screen_name == "Dashboard"
	print("SMOKE TEST [Settings/back]: landed_on=%s (expected Dashboard, since this dev save has an active career)" % current_screen_name)
	return landed_in_career


## Exercises help_screen.gd's real interactivity (ports src/views/screens/
## help_screen.py): switches topic via a real Button.pressed emit, expands
## an article, then filters via search — checking the article list and
## section heading actually change, not just that no error fired.
func _exercise_help() -> bool:
	show_screen("Help")
	var screen := current_screen
	if not ("article_list" in screen):
		print("SMOKE TEST [Help]: not a recognised screen")
		return false
	if screen._topic_buttons.size() < 2:
		print("SMOKE TEST [Help]: expected at least 2 topics")
		return false
	var section_before: String = screen.section_title.text
	screen._topic_buttons[1].pressed.emit()
	var section_after: String = screen.section_title.text
	var count_before: int = screen.article_list.get_child_count()
	if count_before > 0:
		screen.article_list.get_child(0).pressed.emit()
	var count_after_expand: int = screen.article_list.get_child_count()
	screen.search_edit.text = "zzzzznomatch"
	screen._render_articles()
	var count_after_search: int = screen.article_list.get_child_count()
	# v0.93.0: search now spans every topic, not just the active one —
	# confirm a term known to appear in several topics' bodies (see
	# src/data/help_content.json) actually surfaces results from more than
	# one topic, and that clicking a topic afterwards clears the search.
	screen.search_edit.text = "bowler"
	screen._render_articles()
	var cross_topic_results: Array = screen._filtered_articles()
	var distinct_topics := {}
	for article in cross_topic_results:
		distinct_topics[article.get("topic", "")] = true
	var cross_topic_ok: bool = distinct_topics.size() > 1
	screen._topic_buttons[0].pressed.emit()
	var search_cleared_after_topic_click: bool = screen.search_edit.text == ""
	print("SMOKE TEST [Help]: section %s -> %s, articles %d -> %d (expand), %d (no-match search), cross_topic_results=%d across %d topics, cleared_on_topic_click=%s" %
		[section_before, section_after, count_before, count_after_expand, count_after_search,
		 cross_topic_results.size(), distinct_topics.size(), search_cleared_after_topic_click])
	return (section_before != section_after and count_after_expand > count_before and count_after_search == 0
		and cross_topic_ok and search_cleared_after_topic_click)


## Exercises the nav-bar "✕" button — real Button.pressed emit, confirming
## it actually lands on Main Menu with chrome hidden.
func _exercise_quit_to_menu() -> bool:
	show_screen("Dashboard")
	var quit_btn: Button = navbar.get_child(navbar.get_child_count() - 1) as Button
	if quit_btn == null or quit_btn.text != "✕":
		print("SMOKE TEST [Quit to Main Menu]: ✕ button not found in navbar")
		return false
	quit_btn.pressed.emit()
	var landed_on_menu: bool = current_screen_name == "Main Menu"
	var chrome_hidden: bool = not $Layout/HeaderBg.visible and not $Layout/NavBg.visible
	print("SMOKE TEST [Quit to Main Menu]: landed_on=%s chrome_hidden=%s" % [current_screen_name, chrome_hidden])
	return landed_on_menu and chrome_hidden


## Finds a Load Game row's DELETE/CONFIRM DELETE? button by its display
## name — mirrors _row_hbox's pattern of reaching into runtime-built UI,
## needed twice here since the list rebuilds (and the old button node
## becomes stale) between the arm and confirm clicks.
func _find_save_row_button(display_name: String, button_index: int) -> Button:
	var list: VBoxContainer = current_screen.get_node("Card/Box/Scroll/List")
	for row in list.get_children():
		if row.get_child_count() == 0:
			continue
		var box := row.get_child(0) as HBoxContainer
		if box == null or box.get_child_count() == 0:
			continue
		var info := box.get_child(0) as VBoxContainer
		if info == null or info.get_child_count() == 0:
			continue
		var name_label := info.get_child(0) as Label
		if name_label != null and name_label.text == display_name:
			return box.get_child(button_index) as Button
	return null


## v0.90.0: exercises the real multi-save-slot system end to end. Creates a
## throwaway save (same IPC method the Main Menu NEW GAME button uses),
## confirms it appears in a real Load Game screen list, deletes it via two
## real DELETE button presses (arm + confirm — the row's own two-click
## pattern), and confirms it's gone — then reloads back to the save
## _exercise_startup_flow already made active, so every exercise after this
## one still runs against a valid, playable career.
func _exercise_save_slots() -> bool:
	var before_response := IpcBridge.call_method("list_saves")
	if before_response.has("error"):
		print("SMOKE TEST [Saves]: backend error listing saves")
		return false
	var active_id_before: String = str(before_response["result"].get("active_save_id", ""))
	var count_before: int = before_response["result"].get("saves", []).size()
	var create_response := IpcBridge.call_method("create_save", {"display_name": "Smoke Test Throwaway"})
	if create_response.has("error"):
		print("SMOKE TEST [Saves]: backend error creating throwaway save")
		return false
	# create_save makes the new save active (so New Game Setup targets it) —
	# delete_save correctly refuses to delete the active save, so switch back
	# to the original save first, same as a real player would never delete
	# the career they're currently playing.
	var restore_response := IpcBridge.call_method("load_save", {"id": active_id_before})
	if restore_response.has("error"):
		print("SMOKE TEST [Saves]: backend error restoring original save before delete")
		return false
	show_screen("Load Game")
	var count_after_create: int = current_screen.get_node("Card/Box/Scroll/List").get_child_count()
	var arm_button := _find_save_row_button("Smoke Test Throwaway", 2)
	if arm_button == null:
		print("SMOKE TEST [Saves]: throwaway save not found in Load Game list")
		return false
	arm_button.pressed.emit()
	var confirm_button := _find_save_row_button("Smoke Test Throwaway", 2)
	if confirm_button == null:
		print("SMOKE TEST [Saves]: DELETE button did not re-arm to CONFIRM DELETE?")
		return false
	confirm_button.pressed.emit()
	var after_delete_response := IpcBridge.call_method("list_saves")
	var count_after_delete: int = after_delete_response.get("result", {}).get("saves", []).size()
	refresh_header()
	show_screen("Dashboard")
	print("SMOKE TEST [Saves]: count %d -> %d (create) -> %d (delete)" %
		[count_before, count_after_create, count_after_delete])
	return count_after_create == count_before + 1 and count_after_delete == count_before


func _describe_screen(screen: Control) -> String:
	if screen.has_node("Title"):
		return (screen.get_node("Title") as Label).text
	return "(no title label — placeholder or unrecognised screen)"


func _screen_count() -> int:
	var total := 0
	for group in NAV_GROUPS:
		total += group[1].size()
	return total


func _build_navbar() -> void:
	for group in NAV_GROUPS:
		var section_name: String = group[0]
		var button := Button.new()
		button.focus_mode = Control.FOCUS_NONE
		button.custom_minimum_size = Vector2(0, 36)
		var icon_kind: String = NAV_ICONS.get(group[1][0], "dot")
		var hbox := HBoxContainer.new()
		hbox.add_theme_constant_override("separation", 6)
		var icon := NavIcon.new()
		icon.set_kind(icon_kind)
		icon.custom_minimum_size = Vector2(20, 20)
		hbox.add_child(icon)
		var label := Label.new()
		label.text = section_name
		label.add_theme_font_size_override("font_size", 12)
		hbox.add_child(label)
		button.add_child(hbox)
		button.pressed.connect(_on_section_pressed.bind(section_name))
		navbar.add_child(button)
		_section_buttons[section_name] = button
		for screen_name in group[1]:
			var sub_btn := Button.new()
			sub_btn.focus_mode = Control.FOCUS_NONE
			sub_btn.custom_minimum_size = Vector2(0, 30)
			sub_btn.text = screen_name
			sub_btn.pressed.connect(_on_subnav_pressed.bind(screen_name))
			_nav_buttons[screen_name] = sub_btn
	navbar.add_child(Control.new())  # spacer to push footer buttons right
	var settings_btn := Button.new()
	settings_btn.focus_mode = Control.FOCUS_NONE
	settings_btn.text = "⚙"
	settings_btn.pressed.connect(func(): show_screen("Settings"))
	navbar.add_child(settings_btn)
	var help_btn := Button.new()
	help_btn.focus_mode = Control.FOCUS_NONE
	help_btn.text = "?"
	help_btn.pressed.connect(func(): show_screen("Help"))
	navbar.add_child(help_btn)
	var quit_btn := Button.new()
	quit_btn.focus_mode = Control.FOCUS_NONE
	quit_btn.text = "✕"
	quit_btn.pressed.connect(func(): show_screen("Main Menu"))
	navbar.add_child(quit_btn)


func _on_section_pressed(section_name: String) -> void:
	_rebuild_subnav(section_name)
	var screens: Array = []
	for group in NAV_GROUPS:
		if group[0] == section_name:
			screens = group[1]
			break
	if not screens.is_empty():
		show_screen(screens[0])


func _on_subnav_pressed(screen_name: String) -> void:
	show_screen(screen_name)


func _rebuild_subnav(section_name: String) -> void:
	for child in subnav.get_children():
		child.queue_free()
	var screens: Array = []
	for group in NAV_GROUPS:
		if group[0] == section_name:
			screens = group[1]
			break
	for screen_name in screens:
		var btn := _nav_buttons.get(screen_name) as Button
		if btn:
			if btn.get_parent():
				btn.get_parent().remove_child(btn)
			subnav.add_child(btn)
	_current_section = section_name


func _apply_subnav_style() -> void:
	for btn in _nav_buttons.values():
		AppTheme.style_tab_button(btn, false)
		btn.add_theme_font_size_override("font_size", 12)


func _find_section(screen_name: String) -> String:
	for group in NAV_GROUPS:
		if screen_name in group[1]:
			return group[0]
	return ""


## Shared fade+slide-up used by every screen swap, so ported screens get a
## modern/snappy feel for free without a bespoke animation each. Cheap: only
## the incoming screen animates (no cross-fade with the outgoing one, which
## is already freed synchronously above) — a real Tween, not an instant swap.
func _animate_screen_in(node: Control) -> void:
	var target_position := node.position
	node.position = target_position + Vector2(0, 14)
	node.modulate.a = 0.0
	var tween := create_tween()
	tween.set_parallel(true)
	tween.set_trans(Tween.TRANS_CUBIC)
	tween.set_ease(Tween.EASE_OUT)
	tween.tween_property(node, "modulate:a", 1.0, 0.18)
	tween.tween_property(node, "position", target_position, 0.22)


func show_screen(screen_name: String) -> void:
	if current_screen:
		content.remove_child(current_screen)
		current_screen.queue_free()
		current_screen = null
	var instance := _instantiate(screen_name)
	content.add_child(instance)
	current_screen = instance
	_animate_screen_in(instance)
	# Un-highlight previous subnav button
	if current_screen_name in _nav_buttons:
		AppTheme.style_tab_button(_nav_buttons[current_screen_name], false)
	current_screen_name = screen_name
	# Highlight new subnav button and section
	if screen_name in _nav_buttons:
		AppTheme.style_tab_button(_nav_buttons[screen_name], true)
	# Highlight section button
	var section := _find_section(screen_name)
	if section and section in _section_buttons:
		for s_name in _section_buttons:
			var sb: Button = _section_buttons[s_name]
			AppTheme.style_nav_button(sb, s_name == section)
		if section != _current_section:
			_rebuild_subnav(section)
	var chrome_visible: bool = screen_name not in STARTUP_SCREEN_NAMES
	$Layout/HeaderBg.visible = chrome_visible
	$Layout/NavBg.visible = chrome_visible
	$Layout/SubNavBg.visible = chrome_visible
	_sync_onboarding_overlay()


func _instantiate(screen_name: String) -> Control:
	match screen_name:
		"Dashboard":
			return DASHBOARD_SCENE.instantiate()
		"Bookmarks":
			return BOOKMARKS_SCENE.instantiate()
		"Data Hub":
			return DATA_HUB_SCENE.instantiate()
		"Squad":
			var s := TABLE_SCENE.instantiate()
			s.configure("SQUAD", "get_squad", [
				{"key": "nationality", "header": "", "width": 36, "portrait": true},
				{"key": "name", "header": "NAME", "width": 200},
				{"key": "age", "header": "AGE", "width": 80},
				{"key": "role", "header": "ROLE", "width": 160, "pill": true},
				{"key": "bowling_style", "header": "STYLE", "width": 110, "muted": true},
				{"key": "overall", "header": "OVR", "width": 80},
				{"key": "form", "header": "FORM", "width": 90, "bar": true},
				{"key": "morale", "header": "MORALE", "width": 90, "bar": true},
				{"key": "freshness", "header": "FRESH", "width": 90, "bar": true},
			], "players", {}, {}, "", [], [
				{"label": "ATTRIBUTES", "columns": [
					{"key": "nationality", "header": "", "width": 36, "portrait": true},
					{"key": "name", "header": "NAME", "width": 200},
					{"key": "batting_avg", "header": "BATTING", "width": 100, "bar": true},
					{"key": "bowling_avg", "header": "BOWLING", "width": 100, "bar": true},
					{"key": "fielding_avg", "header": "FIELDING", "width": 100, "bar": true},
					{"key": "mental_avg", "header": "MENTAL", "width": 100, "bar": true},
				]},
			])
			return s
		"Training":
			return TRAINING_SCENE.instantiate()
		"Match":
			return MATCH_SCENE.instantiate()
		"Selection":
			var s := TABLE_SCENE.instantiate()
			s.configure("SELECTION", "get_selection", [
				{"key": "nationality", "header": "", "width": 36, "portrait": true},
				{"key": "name", "header": "NAME", "width": 160},
				{"key": "role", "header": "ROLE", "width": 120, "pill": true},
				{"key": "overall", "header": "OVR", "width": 60},
				{"key": "freshness", "header": "FRESH", "width": 80, "bar": true},
				{"key": "xi_status", "header": "ORDER/C/WK", "width": 90},
			], "players", {}, {"method": "toggle_xi", "params_from_row": {"player_id": "id"}}, "",
			[
				{"label": "CAPT", "method": "set_captain", "params_from_row": {"player_id": "id"}, "width": 56},
				{"label": "WK", "method": "set_keeper", "params_from_row": {"player_id": "id"}, "width": 44},
				{"label": "UP", "method": "move_batting_up", "params_from_row": {"player_id": "id"}, "width": 44},
				{"label": "DOWN", "method": "move_batting_down", "params_from_row": {"player_id": "id"}, "width": 56},
			], [
				{"label": "AGGRESSION", "columns": [
					{"key": "nationality", "header": "", "width": 36, "portrait": true},
					{"key": "name", "header": "NAME", "width": 180},
					{"key": "batting_style", "header": "STYLE", "width": 100, "muted": true},
					{"key": "batting_aggression", "header": "AGGRO/10", "width": 90},
				], "row_buttons": [
					{"label": "STYLE", "method": "cycle_batting_style", "params_from_row": {"player_id": "id"}, "width": 70},
					{"label": "AGGRO", "method": "cycle_batting_aggression", "params_from_row": {"player_id": "id"}, "width": 70},
				]},
			])
			return s
		"Inbox":
			var s := TABLE_SCENE.instantiate()
			s.configure("INBOX", "get_inbox", [
				{"key": "priority", "header": "PRI", "width": 60},
				{"key": "title", "header": "TITLE", "width": 420},
				{"key": "timestamp", "header": "WHEN", "width": 160},
			], "messages", {}, {"method": "mark_message_read", "params_from_row": {"message_id": "id"}}, "read")
			return s
		"Recruitment":
			return RECRUITMENT_SCENE.instantiate()
		"Transfers":
			var s := TABLE_SCENE.instantiate()
			s.configure("TRANSFER MARKET", "get_transfer_market", [
				{"key": "nationality", "header": "", "width": 32, "flag": true},
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "age", "header": "AGE", "width": 60},
				{"key": "role", "header": "ROLE", "width": 140, "pill": true},
				{"key": "estimated_overall", "header": "OVR~", "width": 80},
				{"key": "asking_price_display", "header": "PRICE", "width": 120},
			], "players", {}, {"method": "submit_transfer_offer",
				"params_from_row": {"player_id": "id", "fee": "asking_price"},
				"params_fixed": {"wage": 5000}})
			return s
		"Offers":
			var s := TABLE_SCENE.instantiate()
			s.configure("TRANSFER OFFERS", "get_transfer_market", [
				{"key": "player_name", "header": "PLAYER", "width": 180},
				{"key": "from_name", "header": "FROM", "width": 160},
				{"key": "to_name", "header": "TO", "width": 160},
				{"key": "fee_display", "header": "FEE", "width": 120},
				{"key": "status", "header": "STATUS", "width": 100},
			], "offers", {}, {}, "", [
				{"label": "ACCEPT", "method": "resolve_transfer_offer",
					"params_from_row": {"offer_id": "id"}, "params_fixed": {"accept": true}},
				{"label": "REJECT", "method": "resolve_transfer_offer",
					"params_from_row": {"offer_id": "id"}, "params_fixed": {"accept": false}},
			])
			return s
		"Staff":
			var s := TABLE_SCENE.instantiate()
			s.configure("STAFF", "get_staff", [
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "role", "header": "ROLE", "width": 160},
				{"key": "group_name", "header": "DEPT", "width": 120},
				{"key": "age", "header": "AGE", "width": 60},
				{"key": "overall", "header": "OVR", "width": 80},
			], "staff", {}, {}, "", [
				{"label": "RELEASE", "method": "release_staff", "params_from_row": {"staff_id": "id"}},
			])
			return s
		"Staff Market":
			var s := TABLE_SCENE.instantiate()
			s.configure("STAFF MARKET", "get_staff_market", [
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "role", "header": "ROLE", "width": 160},
				{"key": "club_name", "header": "CLUB", "width": 160},
				{"key": "overall", "header": "OVR", "width": 70},
				{"key": "fee_display", "header": "FEE", "width": 110},
				{"key": "wage_display", "header": "WAGE", "width": 100},
			], "staff", {}, {"method": "sign_staff",
				"params_from_row": {"staff_id": "id", "from_team": "team_id", "fee": "fee", "wage": "wage"}})
			return s
		"Finances":
			var s := TABLE_SCENE.instantiate()
			s.configure("FINANCES", "get_finances", [
				{"key": "date", "header": "DATE", "width": 120},
				{"key": "category", "header": "CATEGORY", "width": 180},
				{"key": "kind", "header": "TYPE", "width": 100},
				{"key": "amount_display", "header": "AMOUNT", "width": 140},
				{"key": "description", "header": "NOTE", "width": 300},
			], "transactions")
			return s
		"Facilities":
			var s := TABLE_SCENE.instantiate()
			s.configure("FACILITIES", "get_facilities", [
				{"key": "facility", "header": "FACILITY", "width": 220},
				{"key": "level", "header": "LEVEL", "width": 100},
				{"key": "status", "header": "STATUS", "width": 140},
			], "facilities", {}, {}, "", [
				{"label": "UPGRADE", "method": "upgrade_facility", "params_from_row": {"facility": "facility"}},
			])
			return s
		"Youth Academy":
			return YOUTH_ACADEMY_SCENE.instantiate()
		"Medical Centre":
			var s := TABLE_SCENE.instantiate()
			s.configure("MEDICAL CENTRE", "get_medical", [
				{"key": "player_name", "header": "PLAYER", "width": 180},
				{"key": "player_role", "header": "ROLE", "width": 140},
				{"key": "severity", "header": "SEVERITY", "width": 120},
				{"key": "start_date", "header": "SINCE", "width": 130},
				{"key": "return_date", "header": "RETURNS", "width": 130},
			], "injuries")
			return s
		"Trophy Room":
			# Ports database.py's fetch_honours (v0.80.0) — was a bare flat
			# list capped visually at the last 12 entries, with no sense of
			# which competitions had actually been won how often.
			return TROPHY_ROOM_SCENE.instantiate()
		"Club Records":
			# Ports database.py's record_season_stats/fetch_season_records +
			# fetch_club_records (v0.80.0) — the first season-indexed stats
			# archive; previously player_records was career-cumulative only.
			return SEASON_RECORDS_SCENE.instantiate()
		"Cup":
			# Ports database.py's get_cup_bracket (v0.88.0) — no bracket-tree
			# visual existed anywhere before this, Godot or pygame; the only
			# other bracket endpoint (get_tournament_bracket) covers the
			# separate custom-tournament system, not the main season Cup.
			return TOURNAMENT_BRACKET_SCENE.instantiate()
		"Press Conference":
			# Ports src/models/press_conference.py (v0.81.0) — the first
			# manager-driven lever on board confidence; previously it only
			# ever moved via the passive season-end review.
			return PRESS_CONFERENCE_SCENE.instantiate()
		"Board":
			return BOARD_SCENE.instantiate()
		"Legends":
			# Ports database.py's fetch_legends (v0.79.0) — a Hall of Fame for
			# retired/released players, previously hard-deleted from players
			# with no trace anywhere once age>40 or overall<20. Visible but
			# deliberately unsignable: no IPC method reinserts a legend.
			var s := TABLE_SCENE.instantiate()
			s.configure("LEGENDS", "get_legends", [
				{"key": "nationality", "header": "", "width": 32, "flag": true},
				{"key": "name", "header": "NAME", "width": 180},
				{"key": "role", "header": "ROLE", "width": 130, "pill": true},
				{"key": "final_team_name", "header": "LAST CLUB", "width": 180},
				{"key": "final_overall", "header": "OVR", "width": 70},
				{"key": "retired_age", "header": "AGE", "width": 70},
				{"key": "retired_season", "header": "SEASON", "width": 90},
				{"key": "status", "header": "STATUS", "width": 130, "pill": true},
			], "legends")
			return s
		"Job Offers":
			# Ports database.py's accept_job_offer/decline_job_offer (exposed
			# over IPC since v0.66.0 but never consumed by any UI in either
			# client until now — pygame's job market shipped backend-only
			# too, see v0.72.0's stability-audit-style catch-up pass).
			var s := TABLE_SCENE.instantiate()
			s.configure("JOB OFFERS", "get_job_offers", [
				{"key": "team_name", "header": "CLUB", "width": 180},
				{"key": "division", "header": "DIV", "width": 60},
				{"key": "squad_size", "header": "SQUAD", "width": 70},
				{"key": "average_overall", "header": "AVG OVR", "width": 90},
				{"key": "wage", "header": "WAGE/WK", "width": 100},
				{"key": "description", "header": "NOTES", "width": 260, "muted": true},
			], "offers", {}, {}, "", [
				{"label": "ACCEPT", "method": "accept_job_offer", "params_from_row": {"offer_id": "offer_id"}},
				{"label": "DECLINE", "method": "decline_job_offer", "params_from_row": {"offer_id": "offer_id"}},
			])
			return s
		"Main Menu":
			return MAIN_MENU_SCENE.instantiate()
		"Load Game":
			return LOAD_GAME_SCENE.instantiate()
		"New Game Setup":
			return NEW_GAME_SETUP_SCENE.instantiate()
		"Career Team Selection":
			return CAREER_TEAM_SELECTION_SCENE.instantiate()
		"World Cup Setup":
			return WORLD_CUP_SETUP_SCENE.instantiate()
		"Tournament Setup":
			return TOURNAMENT_SETUP_SCENE.instantiate()
		"Settings":
			return SETTINGS_SCENE.instantiate()
		"Help":
			return HELP_SCENE.instantiate()
		"About":
			return ABOUT_SCENE.instantiate()
		"Achievements":
			return ACHIEVEMENTS_SCENE.instantiate()
		"National Team":
			return NATIONAL_TEAM_SCENE.instantiate()
		"Compare":
			return PLAYER_COMPARISON_SCENE.instantiate()
		"Kit Editor":
			return KIT_EDITOR_SCENE.instantiate()
		"Emblem Editor":
			return EMBLEM_EDITOR_SCENE.instantiate()
		"Player Editor":
			return PLAYER_EDITOR_SCENE.instantiate()
		"Competition Editor":
			return COMPETITION_EDITOR_SCENE.instantiate()
		_:
			var placeholder := PLACEHOLDER_SCENE.instantiate()
			placeholder.set_screen_name(screen_name)
			return placeholder
