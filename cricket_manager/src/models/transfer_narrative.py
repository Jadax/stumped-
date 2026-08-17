"""v4.84.0: transfer window narrative — rumours, speculation, deadline-day drama.

Pure functions only; DB writes live in database.py (record_narrative_event +
create_inbox_message, called from competition.py advance_day).
"""
from __future__ import annotations
from datetime import date
from typing import Any

# Domestic window: Apr–Jun, International window: Jul–Aug
TRANSFER_WINDOW_MONTHS = {4, 5, 6, 7, 8}


def in_transfer_window(current_date: date | str) -> bool:
    """True if the in-game date falls inside either transfer window."""
    dt = current_date if isinstance(current_date, date) else date.fromisoformat(current_date)
    return dt.month in TRANSFER_WINDOW_MONTHS


def is_deadline_period(current_date: date | str) -> bool:
    """True on the last 2 days of a window month (Apr 29–30, Jun 29–30,
    Aug 30–31). These are the 'deadline day drama' trigger days."""
    dt = current_date if isinstance(current_date, date) else date.fromisoformat(current_date)
    if dt.month not in TRANSFER_WINDOW_MONTHS:
        return False
    import calendar
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    return dt.day >= last_day - 1


# --- Rumour templates ---

_OUTGOING_TEMPLATES = [
    "{buyer} reportedly interested in {player}",
    "{player} eyed by {buyer} as transfer target",
    "Sources: {buyer} monitoring {player}'s contract situation",
]

_INCOMING_TEMPLATES = [
    "{club} linked with move for {player} from {seller}",
    "Report: {club} considering bid for {player}",
    "{player} on {club}'s radar ahead of window opening",
]

_SLUMP_TEMPLATES = [
    "{player} considering options after difficult run of form",
    "Agent explores move for {player} amid form concerns",
]


def _pick_templates(rng: Any) -> list[str]:
    """Pick 1–2 templates randomly."""
    import random
    pool = _OUTGOING_TEMPLATES + _INCOMING_TEMPLATES + _SLUMP_TEMPLATES
    k = rng.randint(1, 2)
    return rng.sample(pool, min(k, len(pool)))


def generate_rumours(user_team_id: int, current_date: date | str,
                     squad: list[dict[str, Any]], other_players: list[dict[str, Any]],
                     rng_seed: str | None = None) -> list[dict[str, Any]]:
    """Generate 2–4 transfer rumours.  Pure function — no DB access.

    ``squad`` is the user's squad (list of player dicts with id, name, role,
    overall, morale, age, wage).  ``other_players`` is a sample of players
    from AI clubs (id, name, role, overall, team_name, age, wage).

    Returns list of {"title": str, "body": str, "importance": int, "player_id": int|None}.
    """
    import random
    rng = random.Random(rng_seed or str(current_date))

    dt = current_date if isinstance(current_date, date) else date.fromisoformat(current_date)
    rumours: list[dict[str, Any]] = []

    # --- Outgoing rumours: clubs interested in user's players ---
    valuable = [p for p in squad if p.get("overall", 0) >= 65 and p.get("age", 99) <= 30]
    if valuable:
        n_out = rng.randint(1, min(2, len(valuable)))
        targets = rng.sample(valuable, n_out)
        for player in targets:
            buyer = rng.choice(["a Premier Division club", "a Division 2 side",
                                "an overseas franchise", "a rivals' academy graduate"])
            tmpl = rng.choice(_OUTGOING_TEMPLATES)
            title = tmpl.format(player=player["name"], buyer=buyer)
            body = (f"{player['name']} ({player['role']}, OVR {player.get('overall', '?')}) "
                    f"has reportedly caught the attention of {buyer}. "
                    f"No formal offer yet, but the rumour mill is turning.")
            rumours.append({
                "title": title,
                "body": body,
                "importance": 2 if player.get("overall", 0) >= 75 else 1,
                "player_id": player.get("id"),
            })

    # --- Incoming rumours: user's club linked with AI players ---
    if other_players:
        n_in = rng.randint(1, min(2, len(other_players)))
        targets = rng.sample(other_players, n_in)
        for player in targets:
            tmpl = rng.choice(_INCOMING_TEMPLATES)
            title = tmpl.format(player=player["name"], club="Your club",
                                seller=player.get("team_name", "their current club"))
            body = (f"Your club has been linked with {player['name']} "
                    f"({player['role']}, OVR {player.get('overall', '?')}) "
                    f"from {player.get('team_name', 'an opposing club')}. "
                    f"Estimated fee: £{rng.randint(50, 500) * 1000:,}.")
            rumours.append({
                "title": title,
                "body": body,
                "importance": 2 if player.get("overall", 0) >= 75 else 1,
                "player_id": player.get("id"),
            })

    # --- Slump rumours: user's underperforming players may want out ---
    slumpers = [p for p in squad if (p.get("morale", 50) < 35
                                     and p.get("overall", 0) >= 60)]
    if slumpers and rng.random() < 0.4:
        player = rng.choice(slumpers)
        tmpl = rng.choice(_SLUMP_TEMPLATES)
        title = tmpl.format(player=player["name"])
        body = (f"{player['name']} has been unhappy with recent form and "
                f"playing time. An agent has reportedly been in contact with "
                f"other clubs about a possible move.")
        rumours.append({
            "title": title,
            "body": body,
            "importance": 1,
            "player_id": player.get("id"),
        })

    # Cap at 4
    return rumours[:4]


def generate_deadline_day_drama(current_date: date | str,
                                squad: list[dict[str, Any]],
                                other_players: list[dict[str, Any]],
                                rng_seed: str | None = None) -> list[dict[str, Any]]:
    """Generate 1–3 deadline-day drama messages.  Pure function — no DB access.

    Higher importance (2–3), time-stamped urgency.
    """
    import random
    rng = random.Random(rng_seed or str(current_date))
    drama: list[dict[str, Any]] = []

    # A last-minute bid for a user player
    valuable = [p for p in squad if p.get("overall", 0) >= 65]
    if valuable:
        player = rng.choice(valuable)
        fee = rng.randint(100, 800) * 1000
        drama.append({
            "title": f"Deadline alert: last-ditch bid for {player['name']}",
            "body": (f"11:45 PM — A late bid of £{fee:,} has been received for "
                     f"{player['name']}. The window closes at midnight. "
                     f"Do you accept or let the deal collapse?"),
            "importance": 3,
            "player_id": player.get("id"),
        })

    # A collapsed deal
    if other_players and rng.random() < 0.5:
        player = rng.choice(other_players)
        drama.append({
            "title": f"Deal collapsed: {player['name']}",
            "body": (f"11:30 PM — A deal for {player['name']} from "
                     f"{player.get('team_name', 'a rival club')} has fallen through "
                     f"at the last minute over personal terms. The player remains "
                     f"at their current club."),
            "importance": 2,
            "player_id": player.get("id"),
        })

    # A panic signing announcement
    if rng.random() < 0.3:
        drama.append({
            "title": "Window closing: clubs scramble for late signings",
            "body": ("11:55 PM — Across the division, clubs are scrambling to "
                     "complete last-minute deals before the window slams shut. "
                     "Several high-profile moves are reportedly on the verge of "
                     "completion."),
            "importance": 2,
            "player_id": None,
        })

    return drama
