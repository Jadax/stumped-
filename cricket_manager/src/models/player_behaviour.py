"""v4.85.0: player behaviour — transfer requests, playing-time complaints, retirements.

Pure functions only; DB writes live in database.py (record_narrative_event +
create_inbox_message, called from competition.py advance_day).
"""
from __future__ import annotations
from datetime import date
from typing import Any

# Personality types that affect complaint likelihood
_COMPLAINT_PRONE = {"Hot Head", "Mercenary", "Maverick"}
_LOYALIST = {"Loyalist", "Leader", "Professional"}


def check_transfer_requests(squad: list[dict[str, Any]], current_date: date | str,
                            last_match_xi: list[int] | None = None,
                            season_position: int = 10) -> list[dict[str, Any]]:
    """Scan the squad for players likely to request a transfer.

    Conditions:
    - morale < 30 for 3+ consecutive form entries (sustained unhappiness)
    - OR overall >= 70 but hasn't played in XI for 5+ matches
    - OR personality is 'Mercenary' and club is in bottom half

    Returns list of {"player_id": int, "name": str, "reason": str, "urgency": int}.
    """
    xi_set = set(last_match_xi or [])
    requests: list[dict[str, Any]] = []

    for p in squad:
        pid = p.get("id")
        name = p.get("name", "Unknown")
        overall = p.get("overall", 50)
        morale = p.get("morale", 50)
        personality = p.get("personality", "Professional")
        matches_out = p.get("matches_out_xi", 0)
        morale_streak = p.get("low_morale_streak", 0)

        # Condition 1: sustained low morale
        if morale_streak >= 3 and morale < 30:
            requests.append({
                "player_id": pid, "name": name,
                "reason": f"{name} has been unhappy for several matches and wants out.",
                "urgency": 2,
            })
            continue

        # Condition 2: high-quality player not being picked
        if overall >= 70 and matches_out >= 5:
            requests.append({
                "player_id": pid, "name": name,
                "reason": f"{name} (OVR {overall}) hasn't featured in the XI for {matches_out} matches.",
                "urgency": 2 if overall >= 80 else 1,
            })
            continue

        # Condition 3: mercenary in a struggling club
        if personality == "Mercenary" and season_position >= 8:
            if morale < 45:
                requests.append({
                    "player_id": pid, "name": name,
                    "reason": f"{name} is reportedly unhappy with the club's league position.",
                    "urgency": 1,
                })
                continue

    return requests


def check_playing_time_complaints(squad: list[dict[str, Any]],
                                  last_match_xi: list[int] | None = None) -> list[dict[str, Any]]:
    """High-value players not in recent XIs who might complain.

    Personality-dependent: 'Loyalist'/'Leader' never complain,
    'Hot Head' complains after just 2 matches out.
    """
    complaints: list[dict[str, Any]] = []
    for p in squad:
        pid = p.get("id")
        name = p.get("name", "Unknown")
        overall = p.get("overall", 50)
        personality = p.get("personality", "Professional")
        matches_out = p.get("matches_out_xi", 0)

        if personality in _LOYALIST:
            continue

        threshold = 2 if personality in {"Hot Head"} else 4
        if overall >= 65 and matches_out >= threshold:
            complaints.append({
                "player_id": pid, "name": name,
                "reason": f"{name} ({personality}) has been left out for {matches_out} matches and is growing frustrated.",
                "urgency": 1,
            })

    return complaints


def check_retirements(squad: list[dict[str, Any]], current_date: date | str) -> list[dict[str, Any]]:
    """Mid-season retirement announcements for players who are 38+ with
    declining form (overall < 45).  Distinct from end-of-season rollover."""
    dt = current_date if isinstance(current_date, date) else date.fromisoformat(current_date)
    retirements: list[dict[str, Any]] = []
    for p in squad:
        age = p.get("age", 30)
        overall = p.get("overall", 50)
        if age >= 38 and overall < 45:
            retirements.append({
                "player_id": p.get("id"),
                "name": p.get("name", "Unknown"),
                "reason": f"{p.get('name', 'Unknown')} (age {age}, OVR {overall}) has announced their retirement.",
                "urgency": 3,
                "career_stats": {
                    "age": age,
                    "overall": overall,
                    "role": p.get("role", "Unknown"),
                },
            })
    return retirements


def format_behaviour_event(event_type: str, event: dict[str, Any]) -> dict[str, str]:
    """Format a behaviour event into a ready-to-send inbox message + narrative event.

    Returns {"title": str, "body": str, "priority": str, "category": str}.
    """
    if event_type == "transfer_request":
        return {
            "title": f"Transfer request: {event['name']}",
            "body": event["reason"] + " You can accept, reject, or offer a new contract via the Squad screen.",
            "priority": "HIGH" if event.get("urgency", 1) >= 2 else "MEDIUM",
            "category": "TRANSFER_SAGA",
        }
    if event_type == "playing_time_complaint":
        return {
            "title": f"Playing-time complaint: {event['name']}",
            "body": event["reason"] + " Consider rotating your squad or speaking to the player.",
            "priority": "MEDIUM",
            "category": "PLAYER_BEHAVIOUR",
        }
    if event_type == "retirement":
        return {
            "title": f"Retirement announcement: {event['name']}",
            "body": (f"{event['name']} has decided to hang up their boots. "
                     f"{event.get('reason', '')} "
                     f"They will be available for selection until the end of the season."),
            "priority": "HIGH",
            "category": "MILESTONE",
        }
    return {"title": "Unknown event", "body": str(event), "priority": "LOW", "category": "PLAYER_BEHAVIOUR"}


def process_player_behaviour(squad: list[dict[str, Any]], current_date: date | str,
                             last_match_xi: list[int] | None = None,
                             season_position: int = 10) -> list[dict[str, Any]]:
    """Master function: checks all three behaviour types and returns formatted events.

    Returns list of {"title", "body", "priority", "category", "player_id"} dicts
    ready to be sent as inbox messages + narrative events.
    """
    all_events: list[dict[str, Any]] = []

    for req in check_transfer_requests(squad, current_date, last_match_xi, season_position):
        formatted = format_behaviour_event("transfer_request", req)
        formatted["player_id"] = req["player_id"]
        all_events.append(formatted)

    for cmp in check_playing_time_complaints(squad, last_match_xi):
        formatted = format_behaviour_event("playing_time_complaint", cmp)
        formatted["player_id"] = cmp["player_id"]
        all_events.append(formatted)

    for ret in check_retirements(squad, current_date):
        formatted = format_behaviour_event("retirement", ret)
        formatted["player_id"] = ret["player_id"]
        all_events.append(formatted)

    return all_events
