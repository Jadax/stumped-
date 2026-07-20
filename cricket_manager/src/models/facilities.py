"""Central facility definitions and cross-system effects."""
from __future__ import annotations
FACILITIES={
"Stadium":{"base_cost":2_500_000,"benefit":"Capacity, atmosphere and matchday revenue","effect":.08},
"Training Ground":{"base_cost":1_400_000,"benefit":"Attribute growth and development speed","effect":.12},
"Medical Centre":{"base_cost":1_100_000,"benefit":"Injury prevention and recovery","effect":.09},
"Academy":{"base_cost":1_250_000,"benefit":"Youth current ability and potential quality","effect":.08},
"Commercial Office":{"base_cost":900_000,"benefit":"Sponsor and merchandise revenue","effect":.06},
"Scouting Network":{"base_cost":1_050_000,"benefit":"Scouting range, accuracy and discoveries","effect":.12},
"Grounds Department":{"base_cost":800_000,"benefit":"Pitch preparation and outfield quality","effect":.10}}
def upgrade_cost(name:str,level:int)->int:return int(FACILITIES[name]["base_cost"]*(1+(level-1)*.75))
def effect(name:str,level:int)->float:return round(1+(level-1)*FACILITIES[name]["effect"],3)
