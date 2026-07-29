extends Control

@onready var title_label: Label = $Title

@onready var squad_size_label: Label = $Grid/SquadCard/Box/Value
@onready var avg_overall_label: Label = $Grid/SquadCard/Box/Overall
@onready var avg_age_label: Label = $Grid/SquadCard/Box/Age
@onready var batting_avg_label: Label = $Grid/AttrsCard/Box/Batting/Value
@onready var bowling_avg_label: Label = $Grid/AttrsCard/Box/Bowling/Value
@onready var fielding_avg_label: Label = $Grid/AttrsCard/Box/Fielding/Value

@onready var cash_label: Label = $Grid/FinanceCard/Box/CashValue
@onready var wage_label: Label = $Grid/FinanceCard/Box/WageValue
@onready var position_label: Label = $Grid/PositionCard/Box/PositionValue
@onready var confidence_label: Label = $Grid/PositionCard/Box/ConfidenceValue
@onready var trophy_label: Label = $Grid/PositionCard/Box/TrophyValue


func _ready() -> void:
	refresh()


func refresh() -> void:
	var response := IpcBridge.call_method("get_data_hub")
	if response.has("error"):
		title_label.text = "DATA HUB — backend error: %s" % response["error"]
		push_error("DataHubScreen: %s" % response["error"])
		return
	var d: Dictionary = response["result"]

	squad_size_label.text = str(d.get("squad_size", "—"))
	avg_overall_label.text = "AVG OVR %s" % str(d.get("avg_overall", "—"))
	avg_age_label.text = "AVG AGE %s" % str(d.get("avg_age", "—"))
	batting_avg_label.text = str(d.get("batting_avg", "—"))
	bowling_avg_label.text = str(d.get("bowling_avg", "—"))
	fielding_avg_label.text = str(d.get("fielding_avg", "—"))

	cash_label.text = JsonFormat.value(d.get("cash", 0))
	wage_label.text = "WAGE BILL: %s/wk" % JsonFormat.value(d.get("wage_bill", 0))

	var pos = d.get("league_position")
	position_label.text = "League: %s" % (("#%d" % pos) if pos else "—")
	var conf = d.get("board_confidence", 50)
	var conf_str = d.get("board_label", "Stable")
	confidence_label.text = "Board: %s (%d)" % [conf_str, conf]
	trophy_label.text = "Trophies: %d" % d.get("trophy_count", 0)

	title_label.text = "DATA HUB"
