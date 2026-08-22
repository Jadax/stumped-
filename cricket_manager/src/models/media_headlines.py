"""Media headline generators — pure functions for dynamic news stories.

Generates structured headline dicts based on match results, milestones,
streaks, and other events. Each function returns a list of headline dicts
with keys: title, body, importance, category.

All functions are pure (no DB access) — callers wire persistence.
"""
from __future__ import annotations

import random as _rng
from typing import Any

# ── Match result headlines ──────────────────────────────────────────

_UPSET_TEMPLATES = [
    "Stunning upset as {loser} fall to {winner}",
    "{winner} pull off shock victory over {loser}",
    "Giant-killing act: {winner} triumph over favourites {loser}",
    "Disaster for {loser} as {winner} run riot",
    "Premier side {loser} stunned by spirited {winner}",
]

_BIG_WIN_TEMPLATES = [
    "{winner} demolish {loser} in dominant display",
    "{winner} crush {loser} with commanding performance",
    "No contest: {winner} hand {loser} a lesson",
    "{loser} thoroughly outplayed by clinical {winner}",
]

_DERBY_TEMPLATES = [
    "Derby day drama: {winner} edge past fierce rivals {loser}",
    "Local bragging rights go to {winner} after tense derby",
    "{winner} win the derby battle in front of packed house",
    "Rivalry renewed: {loser} fall short against {winner}",
]

_TITLE_DECIDER_TEMPLATES = [
    "Champions! {winner} seal the title with victory over {loser}",
    "{winner} crowned champions after beating {loser}",
    "Glory for {winner} as title bid confirmed with win",
]

_PROMOTION_TEMPLATES = [
    "Promotion sealed: {winner} go up after beating {loser}",
    "{winner} clinch promotion with victory over {loser}",
    "Up they go: {winner} earn their place in the division above",
]

_RELEGATION_TEMPLATES = [
    "Relegated: {loser} relegated after defeat to {winner}",
    "Heartbreak for {loser} as relegation confirmed",
    "{loser} drop down after falling to {winner}",
]


def match_headlines(
    home_name: str,
    away_name: str,
    home_runs: int,
    away_runs: int,
    winner: int | None,
    home_id: int,
    away_id: int,
    margin_comfortable: bool = False,
    is_derby: bool = False,
    title_decider: bool = False,
    promotion_decider: bool = False,
    relegation_decider: bool = False,
) -> list[dict[str, Any]]:
    """Generate media headlines for a completed match.

    Returns a list of headline dicts (0–3 entries depending on significance).
    """
    if winner is None:
        return []

    headlines: list[dict[str, Any]] = []
    is_home_winner = winner == home_id
    winner_name = home_name if is_home_winner else away_name
    loser_name = away_name if is_home_winner else home_name

    if title_decider:
        headlines.append(_pick(_TITLE_DECIDER_TEMPLATES, winner=winner_name, loser=loser_name, importance=3))
    elif promotion_decider:
        headlines.append(_pick(_PROMOTION_TEMPLATES, winner=winner_name, loser=loser_name, importance=3))
    elif relegation_decider:
        headlines.append(_pick(_RELEGATION_TEMPLATES, winner=winner_name, loser=loser_name, importance=3))
    elif is_derby:
        headlines.append(_pick(_DERBY_TEMPLATES, winner=winner_name, loser=loser_name, importance=3))
    elif margin_comfortable:
        headlines.append(_pick(_BIG_WIN_TEMPLATES, winner=winner_name, loser=loser_name, importance=2))

    return headlines


# ── Milestone headlines ─────────────────────────────────────────────

_CENTURY_TEMPLATES = [
    "{player} hits magnificent century for {team}",
    "Brilliant {player} notches up a ton",
    "{player} celebrates with a well-deserved hundred",
]

_FIVE_WICKET_TEMPLATES = [
    "{player} tears through batting line-up with five-wicket haul",
    "Five for {player}: a spell to remember",
    "{player} claims five wickets in stunning bowling display",
]

_CAREER_BEST_BATTING_TEMPLATES = [
    "New personal best: {player} surpasses career-high score",
    "{player} writes name into record books with career-best knock",
]

_CAREER_BEST_BOWLING_TEMPLATES = [
    "{player} delivers career-best bowling figures",
    "Record-breaking spell: {player} posts career-best with the ball",
]

_DEBUT_CENTURY_TEMPLATES = [
    "Dream debut: {player} marks first appearance with a century",
    "What a way to start: {player} scores hundred on debut",
]


def milestone_headlines(
    player_name: str,
    team_name: str,
    milestone_type: str,
    value: int = 0,
    is_debut: bool = False,
) -> list[dict[str, Any]]:
    """Generate media headlines for a player milestone.

    milestone_type: 'century', 'five_wickets', 'career_best_batting',
                    'career_best_bowling'.
    """
    if milestone_type == "century" and is_debut:
        return [_pick(_DEBUT_CENTURY_TEMPLATES, player=player_name, team=team_name, importance=3)]
    if milestone_type == "century":
        return [_pick(_CENTURY_TEMPLATES, player=player_name, team=team_name, importance=2)]
    if milestone_type == "five_wickets":
        return [_pick(_FIVE_WICKET_TEMPLATES, player=player_name, team=team_name, importance=2)]
    if milestone_type == "career_best_batting":
        return [_pick(_CAREER_BEST_BATTING_TEMPLATES, player=player_name, team=team_name, importance=2)]
    if milestone_type == "career_best_bowling":
        return [_pick(_CAREER_BEST_BOWLING_TEMPLATES, player=player_name, team=team_name, importance=2)]
    return []


# ── Streak headlines ────────────────────────────────────────────────

_WIN_STREAK_TEMPLATES = [
    "{team} extend winning run to {count} matches",
    "Red-hot {team} make it {count} wins on the bounce",
    "Incredible form: {team} now on a {count}-match winning streak",
]

_LOSS_STREAK_TEMPLATES = [
    "Crisis deepens: {team} suffer {count}th consecutive defeat",
    "{team}'s poor run extends to {count} losses in a row",
    "Trouble at {team} as losing streak hits {count}",
]


def streak_headlines(team_name: str, streak_type: str, count: int) -> list[dict[str, Any]]:
    """Generate media headlines for a winning/losing streak."""
    if streak_type == "win" and count >= 3:
        return [_pick(_WIN_STREAK_TEMPLATES, team=team_name, count=count, importance=2)]
    if streak_type == "loss" and count >= 3:
        return [_pick(_LOSS_STREAK_TEMPLATES, team=team_name, count=count, importance=2)]
    return []


# ── Fan sentiment headlines ─────────────────────────────────────────

_FAN_ANGRY_TEMPLATES = [
    "Fan fury grows as {team} continue to struggle",
    "Supporters demand answers as {team} slump continues",
    "Patience wearing thin: {team} fans voice their displeasure",
]

_FAN_HAPPY_TEMPLATES = [
    "Fan favourite: {team} supporters revel in outstanding form",
    "The stands are buzzing: {team} fans loving life",
    "Optimism soars among {team} faithful",
]


def fan_sentiment_headlines(team_name: str, morale: int) -> list[dict[str, Any]]:
    """Generate headlines about fan mood at extreme morale levels."""
    if morale <= 15:
        return [_pick(_FAN_ANGRY_TEMPLATES, team=team_name, importance=2)]
    if morale >= 85:
        return [_pick(_FAN_HAPPY_TEMPLATES, team=team_name, importance=2)]
    return []


# ── Helper ──────────────────────────────────────────────────────────

def _pick(templates: list[str], importance: int = 1, **kwargs: Any) -> dict[str, Any]:
    title = _rng.choice(templates).format(**kwargs)
    return {"title": title, "body": title, "importance": importance}
