extends Control
## v5.3.1: sponsor negotiation. Shows the club's current main sponsor and,
## when a deal is due, competing offers (top dollar / long-term partner /
## performance). The manager can accept an offer as it stands or ask for
## more — each sponsor has a hidden ceiling and limited patience, and may
## withdraw. The board signs the best offer on 15 March if nobody has.

var _status: Label
var _deal_label: Label
var _offers_row: HBoxContainer


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var root := VBoxContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	# Same insets as the Finances screen beside it in the Club section.
	root.offset_left = 24
	root.offset_top = 16
	root.offset_right = -24
	root.offset_bottom = -24
	root.add_theme_constant_override("separation", AppTheme.SPACING_MD)
	add_child(root)
	var title := Label.new()
	title.text = "SPONSORS"
	title.add_theme_font_size_override("font_size", 22)
	root.add_child(title)
	var deal_card := PanelContainer.new()
	deal_card.add_theme_stylebox_override("panel", AppTheme.make_card())
	root.add_child(deal_card)
	_deal_label = Label.new()
	_deal_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	deal_card.add_child(_deal_label)
	_status = Label.new()
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_status.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	root.add_child(_status)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	root.add_child(scroll)
	_offers_row = HBoxContainer.new()
	_offers_row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_offers_row.add_theme_constant_override("separation", AppTheme.SPACING_MD)
	scroll.add_child(_offers_row)
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_sponsorship")
	if response.has("error"):
		_status.text = "Sponsorship unavailable: %s" % response["error"]
		return
	var result: Dictionary = response["result"]
	var deal = result.get("deal")
	if deal is Dictionary and not deal.is_empty():
		var bonuses := ""
		if int(deal.get("trophy_bonus", 0)) > 0:
			bonuses += "  •  Trophy bonus %s" % str(deal.get("trophy_bonus_display", ""))
		if int(deal.get("promotion_bonus", 0)) > 0:
			bonuses += "  •  Promotion bonus %s" % str(deal.get("promotion_bonus_display", ""))
		_deal_label.text = "MAIN SPONSOR: %s — %s a month until %s%s" % [
			str(deal.get("sponsor_name", "")), str(deal.get("monthly_display", "")),
			str(deal.get("end_date", "")), bonuses]
	else:
		_deal_label.text = "NO MAIN SPONSOR — choose one of the offers below. The board will sign the best offer on 15 March if you have not."
	for child in _offers_row.get_children():
		_offers_row.remove_child(child)
		child.queue_free()
	var offers: Array = result.get("offers", [])
	if offers.is_empty() and _status.text.is_empty():
		_status.text = "No offers on the table. New offers arrive when your current deal ends."
	for offer in offers:
		_offers_row.add_child(_offer_card(offer))


func _offer_card(offer: Dictionary) -> PanelContainer:
	var card := PanelContainer.new()
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	card.add_theme_stylebox_override("panel", AppTheme.make_card(true))
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", AppTheme.SPACING_SM)
	card.add_child(box)
	var name_label := Label.new()
	name_label.text = str(offer.get("sponsor_name", ""))
	name_label.add_theme_font_size_override("font_size", 16)
	box.add_child(name_label)
	var style := Label.new()
	style.text = str(offer.get("style", "")).to_upper()
	style.add_theme_font_size_override("font_size", 11)
	style.add_theme_color_override("font_color", AppTheme.ACCENT)
	box.add_child(style)
	var details := Label.new()
	details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	var lines := "%s a month for %d season(s)" % [str(offer.get("monthly_display", "")), int(offer.get("years", 1))]
	if int(offer.get("trophy_bonus", 0)) > 0:
		lines += "\nTrophy bonus: %s each" % str(offer.get("trophy_bonus_display", ""))
	if int(offer.get("promotion_bonus", 0)) > 0:
		lines += "\nPromotion bonus: %s" % str(offer.get("promotion_bonus_display", ""))
	details.text = lines
	box.add_child(details)
	var ask_caption := Label.new()
	ask_caption.text = "ASK FOR (PER MONTH)"
	ask_caption.add_theme_font_size_override("font_size", 10)
	ask_caption.add_theme_color_override("font_color", AppTheme.TEXT_SECONDARY)
	box.add_child(ask_caption)
	var ask := SpinBox.new()
	ask.min_value = 0
	ask.max_value = 100000000
	ask.step = 1000
	ask.value = round(float(offer.get("monthly_value", 0)) * 1.1 / 1000.0) * 1000.0
	box.add_child(ask)
	var buttons := HBoxContainer.new()
	buttons.add_theme_constant_override("separation", AppTheme.SPACING_SM)
	box.add_child(buttons)
	var negotiate := Button.new()
	negotiate.text = "NEGOTIATE"
	negotiate.pressed.connect(func(): _negotiate(int(offer.get("id", 0)), int(ask.value)))
	buttons.add_child(negotiate)
	var accept := Button.new()
	accept.text = "ACCEPT"
	accept.pressed.connect(func(): _accept(int(offer.get("id", 0))))
	buttons.add_child(accept)
	return card


func _negotiate(offer_id: int, ask: int) -> void:
	var response := IpcBridge.call_method("negotiate_sponsor", {"offer_id": offer_id, "ask": ask})
	if response.has("error"):
		_status.text = str(response["error"])
		return
	var result: Dictionary = response["result"]
	match str(result.get("outcome", "")):
		"accept":
			_status.text = "Deal signed with %s at %s a month." % [str(result.get("sponsor_name", "")),
				str(result.get("monthly_display", ""))]
		_:
			_status.text = str(result.get("reason", ""))
	refresh()


func _accept(offer_id: int) -> void:
	var response := IpcBridge.call_method("accept_sponsor", {"offer_id": offer_id})
	if response.has("error"):
		_status.text = str(response["error"])
		return
	var result: Dictionary = response["result"]
	_status.text = "Deal signed with %s at %s a month until %s." % [str(result.get("sponsor_name", "")),
		str(result.get("monthly_display", "")), str(result.get("end_date", ""))]
	refresh()
