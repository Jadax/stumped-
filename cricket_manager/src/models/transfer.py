"""Transparent AI sale decisions and valuations."""
from __future__ import annotations
from typing import Mapping,Any

def sale_assessment(player:Mapping[str,Any], team_cash:int, team_reputation:int=60,
                    squad_rank:int=1, squad_size:int=25)->dict[str,Any]:
    morale=(player.get("mental",{}) or {}).get("morale",50); years=int(player.get("contract_years_remaining",1))
    reasons=[]
    if morale<38: reasons.append("Unhappy")
    if squad_rank>18 and squad_size>=23: reasons.append("Surplus to requirements")
    if years<=1: reasons.append("Contract expiring")
    if team_cash<2_000_000: reasons.append("Club needs funds")
    if player.get("wants_to_leave"): reasons.append("Wants to leave")
    available=bool(player.get("transfer_listed")) or bool(reasons)
    return {"available":available,"reason":reasons[0] if reasons else "Not for sale",
            "price":transfer_value(player,team_reputation)*(1 if available else 1.65)}

def transfer_value(player:Mapping[str,Any], team_reputation:int=60)->int:
    overall=int(player.get("overall",50)); potential=int(player.get("potential",overall)); age=int(player.get("age",25))
    form=int(player.get("form",50)); years=int(player.get("contract_years_remaining",1))
    age_factor=1.18 if 21<=age<=28 else 1.05 if age<21 else .88 if age<=33 else .58
    value=(overall/100)**3*18_000_000*age_factor*(1+max(0,potential-overall)*.018)
    value*=.8+form/250; value*=.78+min(5,years)*.12; value*=.75+team_reputation/240
    return max(25_000,int(round(value/5_000)*5_000))
