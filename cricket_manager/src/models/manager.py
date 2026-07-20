"""Manager identity model.

The human user is a coach/manager, so this model stores only professional
identity information used by the management career.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


VALID_BACKGROUNDS = ("Ex-Player", "Coach", "Scout")


@dataclass(slots=True)
class Manager:
    """The identity and professional background of the human manager."""

    name: str
    nationality: str
    background: str

    def validate(self) -> None:
        self.name = self.name.strip()
        if len(self.name) < 2:
            raise ValueError("Enter a manager name with at least two characters.")
        if not self.nationality.strip():
            raise ValueError("Select a nationality.")
        if self.background not in VALID_BACKGROUNDS:
            raise ValueError("Select Ex-Player, Coach, or Scout as the background.")

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> "Manager":
        manager = cls(value.get("name", ""), value.get("nationality", ""), value.get("background", "Coach"))
        manager.validate()
        return manager
