extends Control
## About/Version screen — shows game info, credits, changelog, and
## links. Replaces the previous empty placeholder.

@onready var title_label: Label = $Title
@onready var version_label: Label = $Card/Scroll/Info/Version
@onready var credits_label: Label = $Card/Scroll/Info/Credits
@onready var changelog_label: RichTextLabel = $Card/Scroll/Changelog
@onready var back_button: Button = $Footer/BackButton


func _ready() -> void:
	back_button.pressed.connect(_on_back)
	_build_info()
	_load_changelog()


func _on_back() -> void:
	var shell := get_tree().get_first_node_in_group("shell")
	if shell:
		var response := IpcBridge.call_method("get_dashboard")
		var fallback := "Dashboard" if not response.has("error") and response.get("result", {}).get("team") else "Main Menu"
		shell.return_from_utility(fallback)


func _build_info() -> void:
	version_label.text = "Stumped! v0.98.0"
	credits_label.text = """© 2026 ASTRAIVA (Pty) Ltd — South Africa
All rights reserved.

This is a procedurally generated cricket management simulation.
No real-world names, likenesses, or logos are used.

Built with Godot Engine 4.7.1
Backend: Python 3.14 + SQLite

Lead Developer: ASTRAIVA
Original Concept: Cricket management simulation

Licensed under proprietary terms.
See LEGAL_COMPLIANCE.md for details."""


func _load_changelog() -> void:
	changelog_label.text = ""
	var entries := [
		["v0.98.0 — 2026-07-29", "FM26-inspired UI overhaul: design system foundation, navigation icons, shell redesign, dashboard portal, table screen polish, player profile bookmarks, personality/traits display."],
		["v0.97.0 — 2026-07-28", "Player Personality system (10 archetypes), Player Traits system (10 phase-specific traits), Honours Boards (per-ground centuries & five-wicket hauls)."],
		["v0.96.0 — 2026-07-28", "Post-launch UX fixes initiative: Settings/Help chrome-less, sidebar footer, dropdown settings."],
		["v0.93.0 — 2026-07-28", "All 36 Help & Guide articles rewritten with search."],
		["v0.90.0 — 2026-07-27", "Multi-save slot system with auto-migration."],
		["v0.88.0 — 2026-07-27", "Domestic Knockout Cup bracket-tree screen."],
		["v0.84.0 — 2026-07-27", "Warm light theme (replacing dark), layout bug fixes, per-row hover highlighting."],
		["v0.76.0 — 2026-07-25", "Godot pre-career startup flow (Main Menu, New Game, Team Selection)."],
	]
	for entry in entries:
		changelog_label.append_text("[b]%s[/b]\n" % entry[0])
		changelog_label.append_text("%s\n\n" % entry[1])
