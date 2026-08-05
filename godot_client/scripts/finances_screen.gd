extends Control
## v4.29.0: was a single flat chronological transaction table with no
## totals anywhere — the user asked for income on one side, expenses on
## the other, running totals, and a recurring periodic figure. Backend's
## get_finances now returns income/expenses split plus a summary block
## (database.summarise_finances); this screen renders both.

@onready var title_label: Label = $Title
@onready var income_total_label: Label = $MainCol/Tiles/IncomeTile/Box/Value
@onready var expenses_total_label: Label = $MainCol/Tiles/ExpensesTile/Box/Value
@onready var net_total_label: Label = $MainCol/Tiles/NetTile/Box/Value
@onready var cash_label: Label = $MainCol/Tiles/CashTile/Box/Value
@onready var month_label: Label = $MainCol/MonthCard/MonthLabel
@onready var forecast_summary_label: Label = $MainCol/ForecastCard/Box/Summary
@onready var forecast_list: VBoxContainer = $MainCol/ForecastCard/Box/Scroll/List
@onready var income_list: VBoxContainer = $MainCol/Row/IncomeCard/Box/Scroll/List
@onready var expenses_list: VBoxContainer = $MainCol/Row/ExpensesCard/Box/Scroll/List


func _ready() -> void:
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_finances")
	if response.has("error"):
		title_label.text = "FINANCES — backend error: %s" % response["error"]
		push_error("FinancesScreen: %s" % response["error"])
		return
	var result: Dictionary = response["result"]
	var summary: Dictionary = result.get("summary", {})
	income_total_label.text = str(summary.get("total_income_display", "—"))
	expenses_total_label.text = str(summary.get("total_expenses_display", "—"))
	var net := int(summary.get("net", 0))
	net_total_label.text = str(summary.get("net_display", "—"))
	net_total_label.add_theme_color_override("font_color",
		AppTheme.HEADER_GREEN if net >= 0 else AppTheme.DANGER)
	cash_label.text = str(summary.get("cash_display", "—"))
	var latest_month = summary.get("latest_month")
	if latest_month:
		month_label.text = "THIS MONTH (%s) — Income %s  •  Expenses %s  •  Net %s" % [
			str(latest_month), str(summary.get("month_income_display", "—")),
			str(summary.get("month_expenses_display", "—")), str(summary.get("month_net_display", "—"))]
	else:
		month_label.text = "No transactions recorded yet."
	_render_column(income_list, result.get("income", []), AppTheme.HEADER_GREEN)
	_render_column(expenses_list, result.get("expenses", []), AppTheme.DANGER)
	_refresh_forecast()
	title_label.text = "FINANCES"


func _refresh_forecast() -> void:
	var response := IpcBridge.call_method("get_financial_forecast")
	if response.has("error"):
		forecast_summary_label.text = "Projection unavailable: %s" % response["error"]
		return
	var fc: Dictionary = response["result"]
	var ending: String = str(fc.get("ending_cash_display", "—"))
	var board_min: String = str(fc.get("minimum_cash_display", "—"))
	forecast_summary_label.text = "Projected 12-month balance: %s  •  Board minimum: %s" % [ending, board_min]
	var risk: Array = fc.get("risk_months", [])
	if not risk.is_empty():
		var risk_text := ""
		for month_key in risk:
			if not risk_text.is_empty():
				risk_text += ", "
			risk_text += str(month_key)
		forecast_summary_label.text += "  •  Risk months: %s" % risk_text
		forecast_summary_label.add_theme_color_override("font_color", AppTheme.DANGER)
	else:
		forecast_summary_label.add_theme_color_override("font_color", AppTheme.HEADER_GREEN)
	_render_forecast_months(fc.get("months", []))


func _render_forecast_months(months: Array) -> void:
	for child in forecast_list.get_children():
		forecast_list.remove_child(child)
		child.queue_free()
	if months.is_empty():
		var empty := Label.new()
		empty.text = "No projection available."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		forecast_list.add_child(empty)
		return
	for month in months:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		var month_label_node := Label.new()
		month_label_node.text = _month_label(str(month.get("month", "?")))
		month_label_node.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		month_label_node.add_theme_font_size_override("font_size", 11)
		row.add_child(month_label_node)
		var net_label := Label.new()
		net_label.text = str(month.get("net_display", "—"))
		net_label.add_theme_font_size_override("font_size", 11)
		net_label.add_theme_color_override("font_color",
			AppTheme.HEADER_GREEN if int(month.get("net", 0)) >= 0 else AppTheme.DANGER)
		row.add_child(net_label)
		var cash_label_node := Label.new()
		cash_label_node.text = str(month.get("cash_display", "—"))
		cash_label_node.add_theme_font_size_override("font_size", 11)
		cash_label_node.add_theme_color_override("font_color",
			AppTheme.HEADER_GREEN if int(month.get("cash", 0)) >= 0 else AppTheme.DANGER)
		row.add_child(cash_label_node)
		forecast_list.add_child(row)


func _month_label(month: String) -> String:
	# "2026-09" -> "SEP 2026"
	var parts := month.split("-")
	if parts.size() != 2:
		return month
	var names: Array = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
	var index := int(parts[1]) - 1
	if index < 0 or index >= names.size():
		return month
	return "%s %s" % [names[index], parts[0]]


func _render_column(list: VBoxContainer, rows: Array, accent: Color) -> void:
	for child in list.get_children():
		list.remove_child(child)
		child.queue_free()
	if rows.is_empty():
		var empty := Label.new()
		empty.text = "No transactions yet."
		empty.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		list.add_child(empty)
		return
	for row in rows:
		var panel := PanelContainer.new()
		var box := StyleBoxFlat.new()
		box.bg_color = AppTheme.CARD
		box.set_corner_radius_all(4)
		box.border_width_left = 3
		box.border_color = accent
		box.content_margin_left = 10
		box.content_margin_right = 10
		box.content_margin_top = 6
		box.content_margin_bottom = 6
		panel.add_theme_stylebox_override("panel", box)
		var vbox := VBoxContainer.new()
		vbox.add_theme_constant_override("separation", 2)
		var top := HBoxContainer.new()
		top.add_theme_constant_override("separation", 10)
		var category_label := Label.new()
		category_label.text = str(row.get("category", "?"))
		category_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		category_label.add_theme_font_size_override("font_size", 13)
		top.add_child(category_label)
		var amount_label := Label.new()
		amount_label.text = str(row.get("amount_display", ""))
		amount_label.add_theme_font_size_override("font_size", 13)
		amount_label.add_theme_color_override("font_color", accent)
		top.add_child(amount_label)
		vbox.add_child(top)
		var meta_label := Label.new()
		meta_label.text = "%s  •  %s" % [str(row.get("date", "?")), str(row.get("description", ""))]
		meta_label.add_theme_font_size_override("font_size", 11)
		meta_label.add_theme_color_override("font_color", AppTheme.TEXT_MUTED)
		vbox.add_child(meta_label)
		panel.add_child(vbox)
		list.add_child(panel)
