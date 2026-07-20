"""ICC-style career record aggregation for every competition context."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Mapping, Sequence

CONTEXTS = ("League", "Cup", "Friendly", "International")

@dataclass
class CareerRecord:
    matches:int=0; innings:int=0; runs:int=0; balls:int=0; fours:int=0; sixes:int=0
    not_outs:int=0; highest_score:int=0; fifties:int=0; hundreds:int=0; ducks:int=0
    balls_bowled:int=0; maidens:int=0; runs_conceded:int=0; wickets:int=0
    best_wickets:int=0; best_runs:int=999; five_wickets:int=0; ten_wickets:int=0
    catches:int=0; stumpings:int=0; run_outs:int=0

    @property
    def batting_average(self): return round(self.runs/max(1,self.innings-self.not_outs),2)
    @property
    def strike_rate(self): return round(self.runs*100/max(1,self.balls),2)
    @property
    def overs(self): return f"{self.balls_bowled//6}.{self.balls_bowled%6}"
    @property
    def economy(self): return round(self.runs_conceded*6/max(1,self.balls_bowled),2)
    @property
    def bowling_average(self): return round(self.runs_conceded/max(1,self.wickets),2)
    @property
    def bowling_strike_rate(self): return round(self.balls_bowled/max(1,self.wickets),2)
    @property
    def dismissals(self): return self.catches+self.stumpings+self.run_outs
    def serialise(self):
        data=asdict(self); data.update(batting_average=self.batting_average,strike_rate=self.strike_rate,
            overs=self.overs,economy=self.economy,bowling_average=self.bowling_average,
            bowling_strike_rate=self.bowling_strike_rate,dismissals=self.dismissals); return data

def _entries(value: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [value]
    return list(value)


def update_record(record: CareerRecord,
                  batting: Mapping[str,Any] | Sequence[Mapping[str,Any]] | None=None,
                  bowling: Mapping[str,Any] | Sequence[Mapping[str,Any]] | None=None,
                  fielding: Mapping[str,Any]|None=None) -> CareerRecord:
    """Add one match, preserving separate innings/hauls in long-format cricket."""
    record.matches += 1
    for batting_line in _entries(batting):
        batting = batting_line
        runs, balls = int(batting.get("runs",0)), int(batting.get("balls",0)); record.innings += 1
        record.runs += runs; record.balls += balls; record.fours += int(batting.get("fours",0)); record.sixes += int(batting.get("sixes",0))
        record.not_outs += int(bool(batting.get("not_out",False))); record.highest_score=max(record.highest_score,runs)
        record.fifties += int(50<=runs<100); record.hundreds += int(runs>=100); record.ducks += int(runs==0 and balls>0)
    for bowling_line in _entries(bowling):
        bowling = bowling_line
        balls=int(bowling.get("balls",0)); wickets=int(bowling.get("wickets",0)); conceded=int(bowling.get("runs",0))
        record.balls_bowled+=balls; record.maidens+=int(bowling.get("maidens",0)); record.runs_conceded+=conceded; record.wickets+=wickets
        if wickets>record.best_wickets or (wickets==record.best_wickets and conceded<record.best_runs): record.best_wickets,record.best_runs=wickets,conceded
        record.five_wickets+=int(wickets>=5); record.ten_wickets+=int(wickets>=10)
    if fielding:
        record.catches+=int(fielding.get("catches",0)); record.stumpings+=int(fielding.get("stumpings",0)); record.run_outs+=int(fielding.get("run_outs",0))
    return record
