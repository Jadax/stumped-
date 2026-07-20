"""Concrete gameplay modifiers for Easy, Normal, and Hard careers."""
from __future__ import annotations
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class DifficultyModifiers:
    ai_mistake_rate: float
    user_cash_bonus: float
    board_tolerance: float
    player_development_rate: float
    ai_aggression_accuracy: float
    ai_review_accuracy: float


class DifficultyManager:
    LEVELS = {
        "easy": DifficultyModifiers(.30, 1.20, 1.30, 1.20, .70, .55),
        "normal": DifficultyModifiers(.10, 1.00, 1.00, 1.00, .90, .75),
        "hard": DifficultyModifiers(.02, .85, .70, .90, .98, .92),
    }

    def __init__(self, level: str = "Normal") -> None:
        key = str(level).strip().lower()
        if key not in self.LEVELS:
            raise ValueError("Difficulty must be Easy, Normal, or Hard.")
        self.level, self.modifiers = key.title(), self.LEVELS[key]

    def __getattr__(self, name: str):
        return getattr(self.modifiers, name)

    def to_dict(self) -> dict[str, float | str]:
        return {"level": self.level, **asdict(self.modifiers)}
