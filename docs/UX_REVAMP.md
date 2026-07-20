# UX Revamp & Feature Expansion Plan

Goal: make Stumped! the deep, modern cricket management game the niche lacks —
Football Manager-grade presentation applied to cricket, exceeding Cricket
Captain's simulation depth while fixing its dated UI.

## Competitor findings (researched 2026-07-20)

- **Cricket Captain 2025/26** (Childish Things): deepest incumbent. Recently
  redesigned to a cleaner light-blue UI; added player editor, kit/logo/emblem
  editors, 45 new domestic teams, smoother 3D highlight animations. Weaknesses
  players cite: dated presentation, thin career/personal progression, limited
  interaction outside matches.
- **Cricket Management 26** (Steam Early Access): FM-style ambition; playable
  matches, transfers, progression, finances — but unfinished balancing and
  presentation. Validates demand for a modern dark FM-style cricket UI.
- **From the Pavilion / Hattrick**: browser text sims. Strengths worth
  borrowing: long-horizon player development, scouting economy, community
  ratings ladders. No offline single-player depth.
- **Ashes Cricket / Cricket 26 (Big Ant)**: action games; management is
  shallow. Their strength is broadcast-style presentation — the bar for our
  matchday screens (score bugs, wagon wheels, beehives, ball-tracker).

Positioning: single-player depth of Cricket Captain + FM26-style dark, dense,
data-rich UI + broadcast-quality live match presentation.

## Design direction ("Midnight Pitch")

- Deep blue-black canvas (#0a0d16), cool elevated cards, electric sky-blue
  action accent (#4cc2ff), pitch green reserved for positive/CTA (#2fd06f),
  gold for elite/warnings.
- FM-style attribute tiers via `theme.attribute_colour()`: red <40, amber
  40–59, white 60–74, green 75–89, **gold 90+**.
- Gradient card headers, elevation shadows, accent rails (see `ui/widgets/card.py`).
- All colours/typography flow from `src/views/theme.py` + `ui/theme.json`;
  never hardcode hexes in screens.

## Phases

**Phase 1 — Design system (DONE, v0.10.0):** Midnight Pitch palette across
theme.py/theme.json/config/launcher, tiered attribute colours, gradient card
headers.

**Phase 2 — Player profile hub:** FM-style single player screen: header strip
(portrait, club, value, contract, morale), attribute columns with tier
colours, role suitability stars, form sparkline, season/career stat tabs,
comparison overlay, scout-report text. Files: `ui/player_modals.py`,
`src/views/screens/player_detail.py`, widgets.

**Phase 3 — Matchday broadcast presentation:** persistent score bug, session
markers, condition icon strip in top bar (weather/light/pitch/ball wear as in
Cricket Captain 25), per-ball beehive + pitch-map overlays, chances panel
(dropped catches, played & missed), momentum/worm graph, richer commentary
variety, crowd audio ducking on wickets. Files: `ui/match_view.py`,
`ui/widgets/*`, `src/controllers/audio_controller.py`, `match_engine.py`
(expose chance/near-miss events).

**Phase 4 — Career & world depth:** manager reputation, board confidence,
job offers/sackings, season reviews and awards, trophy cabinet, hall of fame,
international management pathway (already roadmapped), world player ratings
table (Test/ODI/T20 ranking points).

**Phase 5 — Systems depth:** live auctions option, deeper finances (monthly
P&L, forecasts), wicketkeeper specialisation, expanded youth academy with
regional scouting, T10/Hundred formats, in-game manual expansion with
screenshots.

Each phase: implement + tests + CHANGELOG + version bump + update
`docs/CURRENT.md` + push.

Sources: [Cricket Captain 2026](https://www.childishthings.com/),
[Cricket Captain 2025 on Steam](https://store.steampowered.com/app/3637540),
[Cricket Management 26 on Steam](https://store.steampowered.com/app/4738830/Cricket_Management_26/),
[From the Pavilion](https://www.fromthepavilion.org/).
