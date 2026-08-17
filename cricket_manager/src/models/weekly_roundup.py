"""v4.83.0: weekly news roundup — the FM-style digest that makes the world feel alive.

The inbox only shows YOUR events.  A weekly review surfaces what happened
across the division: results, top performers, table snapshot, transfers,
and injury news.  Pure functions only; DB helpers live in database.py.
"""
from __future__ import annotations
from typing import Any


def build_roundup(user_results: list[dict], division_results: list[dict],
                  top_performers: list[dict], table_snapshot: list[dict],
                  transfer_activity: list[dict], injury_news: list[dict],
                  storyline_highlights: list[dict],
                  week_ending: str) -> dict[str, Any]:
    """Assemble a roundup dict from pre-fetched data.  Pure function."""
    return {
        "week_ending": week_ending,
        "user_results": user_results,
        "division_results": division_results,
        "top_performers": top_performers,
        "table_snapshot": table_snapshot,
        "transfer_activity": transfer_activity,
        "injury_news": injury_news,
        "storyline_highlights": storyline_highlights,
    }


def format_roundup_as_text(roundup: dict[str, Any]) -> str:
    """Render a roundup dict into a human-readable inbox message body."""
    sections: list[str] = []

    # --- Your results ---
    if roundup["user_results"]:
        lines = []
        for r in roundup["user_results"]:
            lines.append(f"  {r['home_name']} {r['home_score']} vs {r['away_name']} {r['away_score']}"
                         + (f" — {r['result_text']}" if r.get("result_text") else ""))
        sections.append("RESULTS (your team)\n" + "\n".join(lines))

    # --- Division results ---
    if roundup["division_results"]:
        lines = []
        for r in roundup["division_results"][:10]:
            lines.append(f"  {r['home_name']} {r['home_score']} vs {r['away_name']} {r['away_score']}"
                         + (f" — {r['result_text']}" if r.get("result_text") else ""))
        if len(roundup["division_results"]) > 10:
            lines.append(f"  ...and {len(roundup['division_results']) - 10} more")
        sections.append("DIVISION RESULTS\n" + "\n".join(lines))

    # --- Top performers ---
    if roundup["top_performers"]:
        lines = []
        for p in roundup["top_performers"][:5]:
            lines.append(f"  {p['name']}: {p['stat_line']}")
        sections.append("TOP PERFORMERS\n" + "\n".join(lines))

    # --- Table snapshot ---
    if roundup["table_snapshot"]:
        lines = []
        for i, t in enumerate(roundup["table_snapshot"][:6], 1):
            lines.append(f"  {i}. {t['name']} — {t['points']}pts (P{t['played']})")
        sections.append("STANDINGS\n" + "\n".join(lines))

    # --- Transfer activity ---
    if roundup["transfer_activity"]:
        lines = []
        for tr in roundup["transfer_activity"]:
            lines.append(f"  {tr['player_name']}: {tr['from_name']} → {tr['to_name']} (£{tr['fee']:,})")
        section_title = "TRANSFERS" if roundup["transfer_activity"] else ""
        sections.append(section_title + "\n" + "\n".join(lines))

    # --- Injury news ---
    if roundup["injury_news"]:
        lines = []
        for inj in roundup["injury_news"]:
            lines.append(f"  {inj['player_name']} ({inj['team_name']}) — {inj['severity']}, "
                         f"out until {inj['return_date']}")
        sections.append("INJURY NEWS\n" + "\n".join(lines))

    # --- Storyline highlights ---
    if roundup["storyline_highlights"]:
        lines = []
        for s in roundup["storyline_highlights"]:
            lines.append(f"  {s['title']}")
        sections.append("STORYLINES\n" + "\n".join(lines))

    if not sections:
        return "Quiet week across the division — no notable events to report."
    return "\n\n".join(sections)
