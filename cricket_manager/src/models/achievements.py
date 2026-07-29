"""Steam achievement definitions for Stumped! — 50+ achievements
covering career milestones, tactical feats, management accomplishments,
and collection goals. Each achievement has an ID, name, description,
and a check function that returns True when the condition is met.
"""
from __future__ import annotations
from typing import Any, Callable

# Achievement categories
CATEGORY_CAREER = "career"
CATEGORY_TACTICAL = "tactical"
CATEGORY_MANAGEMENT = "management"
CATEGORY_COLLECTION = "collection"
CATEGORY_INTERNATIONAL = "international"

# Achievement definitions: (id, name, description, category, icon)
ACHIEVEMENTS = [
    # Career milestones
    ("first_win", "First Victory", "Win your first match as manager", CATEGORY_CAREER, "🏆"),
    ("first_draw", "Hard Fought Draw", "Draw your first match as manager", CATEGORY_CAREER, "🤝"),
    ("season_survivor", "Season Survivor", "Complete your first full season", CATEGORY_CAREER, "📅"),
    ("two_season_veteran", "Two-Season Veteran", "Complete two full seasons", CATEGORY_CAREER, "🗓️"),
    ("five_season_legend", "Five-Season Legend", "Complete five full seasons", CATEGORY_CAREER, "⭐"),
    ("century_manager", "Century Manager", "Manage 100 matches", CATEGORY_CAREER, "💯"),
    ("winning_manager", "Winning Manager", "Achieve 50 wins as manager", CATEGORY_CAREER, "📊"),
    ("elite_manager", "Elite Manager", "Achieve 100 wins as manager", CATEGORY_CAREER, "👑"),

    # Tactical achievements
    ("hat_trick_hero", "Hat Trick Hero", "A bowler takes a hat-trick in a match", CATEGORY_TACTICAL, "🎩"),
    ("double_century", "Double Century", "A batsman scores 200+ in an innings", CATEGORY_TACTICAL, "🏏"),
    ("perfect_game", "Perfect Game", "Win a match without losing any wickets", CATEGORY_TACTICAL, "✨"),
    ("run_chase_master", "Run Chase Master", "Successfully chase 200+ in T20", CATEGORY_TACTICAL, "🎯"),
    ("defensive_masterclass", "Defensive Masterclass", "Win a Test match by bowling out opposition twice", CATEGORY_TACTICAL, "🛡️"),
    ("century_maker", "Century Maker", "A batsman scores 100+ in an innings", CATEGORY_TACTICAL, "💯"),
    ("five_wicket_haul", "Five-Wicket Haul", "A bowler takes 5+ wickets in an innings", CATEGORY_TACTICAL, "🎳"),
    ("ten_wicket_match", "Ten-Wicket Match", "A bowler takes 10+ wickets in a match", CATEGORY_TACTICAL, "🔥"),
    ("duck_hunter", "Duck Hunter", "Bowling team dismisses opposition for under 50", CATEGORY_TACTICAL, "🦆"),
    ("super_over_winner", "Super Over Hero", "Win a Super Over", CATEGORY_TACTICAL, "⚡"),

    # Management achievements
    ("promotion_party", "Promotion Party", "Get promoted to a higher division", CATEGORY_MANAGEMENT, "📈"),
    ("relegation_survivor", "Relegation Survivor", "Avoid relegation in final match of season", CATEGORY_MANAGEMENT, "📉"),
    ("division_one_champion", "Division One Champion", "Win Division 1 title", CATEGORY_MANAGEMENT, "🥇"),
    ("treble_winner", "Treble Winner", "Win league, cup, and international in same season", CATEGORY_MANAGEMENT, "🏆"),
    ("cup_glory", "Cup Glory", "Win the Domestic Knockout Cup or T20 Cup", CATEGORY_MANAGEMENT, "🏆"),
    ("undefeated_season", "Undefeated Season", "Complete a league season without losing", CATEGORY_MANAGEMENT, "💯"),
    ("financial_wizard", "Financial Wizard", "Reach £10M in club finances", CATEGORY_MANAGEMENT, "💰"),
    ("youth_developer", "Youth Developer", "Promote 5 players from academy to first team", CATEGORY_MANAGEMENT, "🌱"),
    ("staff_master", "Staff Master", "Hire coaches in all three departments", CATEGORY_MANAGEMENT, "👥"),
    ("facility_mogul", "Facility Mogul", "Upgrade all facilities to max level", CATEGORY_MANAGEMENT, "🏟️"),
    ("board_confidence", "Board favourite", "Reach 90+ board confidence", CATEGORY_MANAGEMENT, "🤝"),
    ("squad_depth", "Squad Depth", "Have 25+ players with 60+ overall", CATEGORY_MANAGEMENT, "📋"),
    ("transfer_master", "Transfer Master", "Sign 20 players through transfers", CATEGORY_MANAGEMENT, "📝"),
    ("contract_negotiator", "Contract Guru", "Successfully negotiate 10 contract renewals", CATEGORY_MANAGEMENT, "✍️"),

    # Collection achievements
    ("player_collector", "Player Collector", "Have 50 different players in your squad across career", CATEGORY_COLLECTION, "👥"),
    ("international_export", "International Export", "Have 5+ players called up to international duty", CATEGORY_COLLECTION, "🌍"),
    ("hat_trick_collector", "Hat Trick Collection", "Witness 3 different bowlers take hat-tricks", CATEGORY_COLLECTION, "🎩"),
    ("century_club", "Century Club", "Have 5 different batsmen score centuries", CATEGORY_COLLECTION, "🏏"),
    ("world_tour", "World Tour", "Play matches against teams from 5+ different nations", CATEGORY_COLLECTION, "🌏"),
    ("ground_hunter", "Ground Hunter", "Score a century at 5+ different grounds", CATEGORY_COLLECTION, "🏟️"),
    ("form_master", "Form Master", "Have a player reach 95+ form", CATEGORY_COLLECTION, "📈"),
    ("morale_boost", "Team Spirit", "Have all players above 80 morale", CATEGORY_COLLECTION, "😊"),
    ("scouting_network", "Scouting Network", "Scout 30+ players", CATEGORY_COLLECTION, "🔍"),
    ("record_breaker", "Record Breaker", "Set a new club record for highest score", CATEGORY_COLLECTION, "📊"),

    # International achievements
    ("debut_callup", "International Debut", "First player called up to international duty", CATEGORY_INTERNATIONAL, "🌍"),
    ("international_winner", "International Winner", "Your player's nation wins an international series", CATEGORY_INTERNATIONAL, "🏆"),
    ("world_cup_hero", "World Cup Hero", "Your player scores 100 in a World Cup match", CATEGORY_INTERNATIONAL, "🏏"),
    ("ashes_legend", "Ashes Legend", "Your player scores 150+ in an Ashes Test", CATEGORY_INTERNATIONAL, "⭐"),
    ("multiple_internationals", "International Factory", "Have 3+ players called up in same window", CATEGORY_INTERNATIONAL, "🌟"),
]


class AchievementTracker:
    """Tracks achievement progress and unlocks."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        self._unlocked: set[str] = set()
        self._load_unlocked()

    def _load_unlocked(self) -> None:
        """Load previously unlocked achievements from database."""
        from database import connect
        with connect(self.database_path) as connection:
            try:
                rows = connection.execute(
                    "SELECT achievement_id FROM achievements"
                ).fetchall()
                self._unlocked = {row[0] for row in rows}
            except Exception:
                self._unlocked = set()

    def check_all(self, game_state: dict[str, Any]) -> list[dict[str, Any]]:
        """Check all achievements against current game state.
        Returns list of newly unlocked achievements."""
        newly_unlocked = []
        for achievement_id, name, description, category, icon in ACHIEVEMENTS:
            if achievement_id in self._unlocked:
                continue
            if self._check_achievement(achievement_id, game_state):
                self._unlock(achievement_id)
                newly_unlocked.append({
                    "id": achievement_id,
                    "name": name,
                    "description": description,
                    "category": category,
                    "icon": icon,
                })
        return newly_unlocked

    def _check_achievement(self, achievement_id: str, state: dict[str, Any]) -> bool:
        """Check if a specific achievement condition is met."""
        checks: dict[str, Callable] = {
            "first_win": lambda s: s.get("wins", 0) >= 1,
            "first_draw": lambda s: s.get("draws", 0) >= 1,
            "season_survivor": lambda s: s.get("seasons_completed", 0) >= 1,
            "two_season_veteran": lambda s: s.get("seasons_completed", 0) >= 2,
            "five_season_legend": lambda s: s.get("seasons_completed", 0) >= 5,
            "century_manager": lambda s: s.get("matches_managed", 0) >= 100,
            "winning_manager": lambda s: s.get("wins", 0) >= 50,
            "elite_manager": lambda s: s.get("wins", 0) >= 100,
            "hat_trick_hero": lambda s: s.get("hat_tricks", 0) >= 1,
            "double_century": lambda s: s.get("double_centuries", 0) >= 1,
            "perfect_game": lambda s: s.get("perfect_games", 0) >= 1,
            "run_chase_master": lambda s: s.get("successful_chases_200", 0) >= 1,
            "defensive_masterclass": lambda s: s.get("test_wins_by_innings", 0) >= 1,
            "century_maker": lambda s: s.get("centuries", 0) >= 1,
            "five_wicket_haul": lambda s: s.get("five_wicket_hauls", 0) >= 1,
            "ten_wicket_match": lambda s: s.get("ten_wicket_matches", 0) >= 1,
            "duck_hunter": lambda s: s.get("bowled_out_for_under_50", 0) >= 1,
            "super_over_winner": lambda s: s.get("super_over_wins", 0) >= 1,
            "promotion_party": lambda s: s.get("promotions", 0) >= 1,
            "relegation_survivor": lambda s: s.get("relegations_avoided", 0) >= 1,
            "division_one_champion": lambda s: s.get("division_one_titles", 0) >= 1,
            "treble_winner": lambda s: s.get("trebles", 0) >= 1,
            "cup_glory": lambda s: s.get("cup_wins", 0) >= 1,
            "undefeated_season": lambda s: s.get("undefeated_seasons", 0) >= 1,
            "financial_wizard": lambda s: s.get("max_cash", 0) >= 10_000_000,
            "youth_developer": lambda s: s.get("academy_promotions", 0) >= 5,
            "staff_master": lambda s: s.get("all_staff_hired", False),
            "facility_mogul": lambda s: s.get("all_facilities_max", False),
            "board_confidence": lambda s: s.get("max_board_confidence", 0) >= 90,
            "squad_depth": lambda s: s.get("squad_60_plus", 0) >= 25,
            "transfer_master": lambda s: s.get("transfers_signed", 0) >= 20,
            "contract_negotiator": lambda s: s.get("contracts_renewed", 0) >= 10,
            "player_collector": lambda s: s.get("unique_players", 0) >= 50,
            "international_export": lambda s: s.get("international_callups", 0) >= 5,
            "hat_trick_collector": lambda s: s.get("unique_hat_tricks", 0) >= 3,
            "century_club": lambda s: s.get("unique_centuries", 0) >= 5,
            "world_tour": lambda s: s.get("nations_played", 0) >= 5,
            "ground_hunter": lambda s: s.get("grounds_century", 0) >= 5,
            "form_master": lambda s: s.get("max_form", 0) >= 95,
            "morale_boost": lambda s: s.get("all_morale_80_plus", False),
            "scouting_network": lambda s: s.get("players_scouted", 0) >= 30,
            "record_breaker": lambda s: s.get("new_club_record", False),
            "debut_callup": lambda s: s.get("international_callups", 0) >= 1,
            "international_winner": lambda s: s.get("international_series_wins", 0) >= 1,
            "world_cup_hero": lambda s: s.get("world_cup_centuries", 0) >= 1,
            "ashes_legend": lambda s: s.get("ashes_150_plus", 0) >= 1,
            "multiple_internationals": lambda s: s.get("simultaneous_callups", 0) >= 3,
        }
        check_fn = checks.get(achievement_id)
        if check_fn:
            return check_fn(state)
        return False

    def _unlock(self, achievement_id: str) -> None:
        """Record an achievement unlock."""
        from database import connect
        with connect(self.database_path) as connection:
            try:
                connection.execute(
                    "INSERT INTO achievements (achievement_id, unlocked_at) VALUES (?, datetime('now'))",
                    (achievement_id,)
                )
            except Exception:
                pass
        self._unlocked.add(achievement_id)

    def get_progress(self) -> dict[str, bool]:
        """Return dict of all achievements and their unlock status."""
        return {a[0]: a[0] in self._unlocked for a in ACHIEVEMENTS}

    def get_unlocked_count(self) -> int:
        """Return count of unlocked achievements."""
        return len(self._unlocked)

    def get_total_count(self) -> int:
        """Return total number of achievements."""
        return len(ACHIEVEMENTS)
