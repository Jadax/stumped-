class_name PlayerProfileModal
extends Control
## Single-view player profile, ported from pygame's ui/player_modals.py
## PlayerDetailModal — scoped down to one solid view (bio, contract, full
## attribute breakdown) rather than porting all six tabs (Records/Bat Form/
## Bowl Form/Personal/Match Stats/Comparison) in one pass. Those can follow
## as their own screens later.

const ATTRIBUTE_GROUPS := [
	["batting", "BATTING"], ["bowling", "BOWLING"], ["fielding", "FIELDING"],
	["mental", "MENTAL"], ["physical", "PHYSICAL"],
]

@onready var portrait: PlayerPortrait = $Center/Card/Margin/Box/Header/Portrait
@onready var flag_rect: TextureRect = $Center/Card/Margin/Box/Header/Flag
@onready var name_label: Label = $Center/Card/Margin/Box/Header/NameBox/Name
@onready var meta_label: Label = $Center/Card/Margin/Box/Header/NameBox/Meta
@onready var overall_label: Label = $Center/Card/Margin/Box/Header/Overall
@onready var potential_label: Label = $Center/Card/Margin/Box/Header/Potential
@onready var close_button: Button = $Center/Card/Margin/Box/Header/Close
@onready var groups_box: VBoxContainer = $Center/Card/Margin/Box/Scroll/Groups
@onready var wage_label: Label = $Center/Card/Margin/Box/Contract/Wage
@onready var contract_label: Label = $Center/Card/Margin/Box/Contract/ContractYears
@onready var status_box: HBoxContainer = $Center/Card/Margin/Box/Status
@onready var dim: ColorRect = $Dim


func _ready() -> void:
	close_button.pressed.connect(hide_modal)
	dim.gui_input.connect(_on_dim_input)
	var card_box := StyleBoxFlat.new()
	card_box.bg_color = AppTheme.CARD
	card_box.border_color = AppTheme.GOLD
	card_box.set_border_width_all(1)
	card_box.set_corner_radius_all(10)
	$Center/Card.add_theme_stylebox_override("panel", card_box)
	name_label.add_theme_color_override("font_color", AppTheme.TEXT_PRIMARY)
	meta_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
	overall_label.add_theme_color_override("font_color", AppTheme.GOLD)
	potential_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	wage_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	contract_label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)


func show_for(player: Dictionary) -> void:
	portrait.set_player(str(player.get("nationality", "England")), int(player.get("age", 25)), int(player.get("id", 0)))
	name_label.text = str(player.get("name", "—"))
	var role: String = str(player.get("role", "—"))
	meta_label.text = "%s • %s yrs • %s" % [role, JsonFormat.value(player.get("age", "—")), player.get("nationality", "—")]
	var overall := int(player.get("overall", 50))
	overall_label.text = str(overall)
	potential_label.text = "POT %s" % str(int(player.get("potential", overall)))
	var texture := AppTheme.flag_texture(str(player.get("nationality", "")))
	flag_rect.texture = texture
	flag_rect.visible = texture != null
	wage_label.text = "Weekly wage: %s" % str(player.get("wage_display", player.get("wage", "—")))
	contract_label.text = "Contract remaining: %s years" % JsonFormat.value(player.get("contract_years_remaining", "—"))
	_build_status_chips(player)
	_build_groups(player)
	visible = true


## FM-style status chip row (Happiness/Fitness/Form/Discipline in the
## reference screenshots) — previously this modal showed overall/potential
## but no form/fitness/morale at all, despite the hover card already
## surfacing all three; brings the full profile up to parity.
func _build_status_chips(player: Dictionary) -> void:
	for child in status_box.get_children():
		status_box.remove_child(child)
		child.queue_free()
	var mental: Dictionary = player.get("mental", {}) if player.get("mental") is Dictionary else {}
	status_box.add_child(AppTheme.make_status_chip("FORM", int(player.get("form", 50))))
	status_box.add_child(AppTheme.make_status_chip("FITNESS", int(mental.get("fitness", 50))))
	status_box.add_child(AppTheme.make_status_chip("MORALE", int(mental.get("morale", 50))))


func hide_modal() -> void:
	visible = false


func _on_dim_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		hide_modal()


func _build_groups(player: Dictionary) -> void:
	for child in groups_box.get_children():
		groups_box.remove_child(child)
		child.queue_free()
	for pair in ATTRIBUTE_GROUPS:
		var key: String = pair[0]
		var heading: String = pair[1]
		var attrs: Dictionary = player.get(key, {}) if player.get(key) is Dictionary else {}
		if attrs.is_empty():
			continue
		var heading_label := Label.new()
		heading_label.text = heading
		heading_label.add_theme_color_override("font_color", AppTheme.GOLD)
		heading_label.add_theme_font_size_override("font_size", 13)
		groups_box.add_child(heading_label)
		for attr_key in attrs:
			groups_box.add_child(_attribute_row(str(attr_key).replace("_", " ").capitalize(), int(attrs[attr_key])))


func _attribute_row(label_text: String, value: int) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	var label := Label.new()
	label.text = label_text
	label.custom_minimum_size = Vector2(180, 0)
	label.add_theme_font_size_override("font_size", 12)
	label.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	row.add_child(label)
	row.add_child(AppTheme.make_bar_meter(260.0, value, 12, AppTheme.TEXT_PRIMARY))
	return row
