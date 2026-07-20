"""Simulate 1,200 seeded matches and report aggregate realism metrics."""
from __future__ import annotations
from collections import defaultdict
from match_engine import Match


def player(player_id: int, role: str, rating: int) -> dict:
    return {"id":player_id,"name":f"Generated Player {player_id}","age":27,"role":role,"overall":rating,
            "potential":min(100,rating+8),"form":50,
            "batting":{"attack":rating,"defence":rating,"technique_vs_pace":rating,"technique_vs_spin":rating,"concentration":rating},
            "bowling":{"pace":rating,"accuracy":rating,"variation":rating,"stamina":rating,"swing_or_spin":rating},
            "fielding":{"catching":rating,"throwing":rating,"reflexes":rating,"agility":rating},
            "mental":{"experience":rating,"consistency":rating,"big_match":rating,"fitness":rating,"morale":rating}}


def lineup(start: int, rating: int) -> list[dict]:
    roles=["Batsman"]*5+["All-Rounder"]*2+["Bowler"]*3+["Wicketkeeper"]
    return [player(start+i,role,rating+(i%3)-1) for i,role in enumerate(roles)]


def validate(sample_sizes: dict[str, int] | None = None) -> dict:
    summary=defaultdict(lambda:{"matches":0,"innings":0,"runs":0,"wickets":0,"balls":0,"completed":0})
    sample_sizes=sample_sizes or {"T20":480,"ODI":480,"Test":40}
    for format_name in ("T20","ODI","Test"):
        for seed in range(sample_sizes[format_name]):
            match=Match({"id":1,"name":"North"},{"id":2,"name":"South"},lineup(1,68),lineup(20,67),
                        format_name,pitch=("Green","Dry","Dusty","Flat")[seed%4],
                        weather=("Sunny","Overcast","Cloudy")[seed%3],seed=seed,batting_first_id=1)
            match.simulate(); item=summary[format_name]; item["matches"]+=1; item["completed"]+=int(match.completed)
            item["innings"]+=len(match.innings)
            item["runs"]+=sum(innings.runs for innings in match.innings)
            item["wickets"]+=sum(innings.wickets for innings in match.innings)
            item["balls"]+=sum(innings.legal_balls for innings in match.innings)
    for item in summary.values():
        item["runs_per_over"]=round(item["runs"]*6/max(1,item["balls"]),2)
        innings_count = item.pop("innings")
        item["wickets_per_innings"]=round(item["wickets"]/max(1,innings_count),2)
    return dict(summary)


if __name__=="__main__":
    for format_name,metrics in validate().items(): print(format_name,metrics)
