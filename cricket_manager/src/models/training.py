"""Interconnected training calculations used by UI, DB jobs, and AI."""
from __future__ import annotations
from typing import Mapping,Any

from src.models.player_development import training_age_factor

def development_multiplier(player:Mapping[str,Any], training_level:int, coach_quality:int=60,
                           intensity:str="Normal")->float:
    age=int(player.get("age",25)); room=max(0,int(player.get("potential",50))-int(player.get("overall",50)))
    age_factor = training_age_factor(age)
    return age_factor*(.35+min(1.15,room/18))*(1+(training_level-1)*.12)*(.7+coach_quality/200)*{"Light":.72,"Normal":1.,"Heavy":1.32}.get(intensity,1.)

def injury_risk(player:Mapping[str,Any], intensity:str, medical_level:int)->float:
    physical=player.get("physical",{}) or {}; fitness=physical.get("fitness",50); endurance=physical.get("endurance",50)
    base=.006+(100-(fitness*.55+endurance*.45))*.00013
    return round(base*{"Light":.55,"Normal":1.,"Heavy":1.9}.get(intensity,1.)*(1-(medical_level-1)*.09),4)
