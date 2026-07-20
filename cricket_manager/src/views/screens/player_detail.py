"""Canonical player-profile entry point.

The desktop UI presents profiles as modals so managers retain the context of
the squad, selection, transfer, or match screen that opened them.  This module
provides the requested feature-path without duplicating that substantial view.
"""
from ui.player_modals import PlayerComparisonModal, PlayerDetailModal

PlayerDetailScreen = PlayerDetailModal

__all__ = ["PlayerDetailScreen", "PlayerDetailModal", "PlayerComparisonModal"]
