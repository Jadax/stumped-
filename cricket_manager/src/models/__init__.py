"""Domain models used by startup and campaign controllers."""

from .manager import Manager

__all__ = ["Manager"]
"""Domain models shared by setup, simulation, and management systems."""

from .difficulty import DifficultyManager, DifficultyModifiers
from .manager import Manager

__all__ = ["DifficultyManager", "DifficultyModifiers", "Manager"]
