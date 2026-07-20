"""Weekly training schedules; Python weekday numbers use Monday=0."""
from __future__ import annotations
from dataclasses import dataclass

DAY_NAMES=("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday")
@dataclass(frozen=True)
class TrainingSchedule:
    days:tuple[int,...]=(0,2,4); intensity:str="Normal"
    def active_on(self, day:int)->bool:return day in self.days
    @property
    def label(self):return ", ".join(DAY_NAMES[d][:3] for d in self.days)
    @property
    def injury_multiplier(self):return {"Light":.65,"Normal":1.0,"Heavy":1.75}.get(self.intensity,1.0)
