"""Rolling weekly, monthly, and seasonal form with trend detection."""
from __future__ import annotations
from dataclasses import dataclass, field
from statistics import mean

@dataclass
class PlayerForm:
    values:list[float]=field(default_factory=list)
    def add(self, performance:float): self.values.append(max(0,min(100,float(performance)))); self.values=self.values[-80:]
    def average(self,count:int): return round(mean(self.values[-count:]),1) if self.values else 50.0
    @property
    def week(self): return self.average(2)
    @property
    def month(self): return self.average(8)
    @property
    def season(self): return self.average(40)
    @property
    def trend(self):
        if len(self.values)<4:return "Steady"
        delta=mean(self.values[-2:])-mean(self.values[-4:-2])
        return "Improving" if delta>3 else "Declining" if delta<-3 else "Steady"
