# Competitive Roadmap v2.0 — Realistic Cricket World

## Goal
Make Stumped! the best cricket management game on Steam with realistic
league structures, domestic cups, and match presentation matching
Cricket Captain 2026.

## Phase 1: Realistic League Structures (v2.0.0)
Rename divisions to real competition names.

### Division Names
- Division 1 → County Championship (England), Sheffield Shield (Australia),
  Ranji Trophy (India), Quaid-e-Azam Trophy (Pakistan), Plunket Shield
  (New Zealand), Currie Cup (South Africa), West Indies Championship
- Division 2 → County One-Day (England), Marsh Cup (Australia), Vijay
  Hazare Trophy (India), Pakistan Cup (India), Ford Trophy (New Zealand),
  One-Day Cup (South Africa), West Indies One-Day
- Division 3 → T20 Blast (England), Big Bash League (Australia), IPL
  (India), PSL (Pakistan), Super Smash (New Zealand), CSA T20 Challenge,
  CPL (West Indies)

### Domestic Cups per Country
1. England: County Championship, T20 Blast, One-Day Cup, The Hundred
2. Australia: Sheffield Shield, Big Bash League, Marsh Cup
3. India: Ranji Trophy, IPL, Vijay Hazare Trophy, Syed Mushtaq Ali Trophy
4. Pakistan: Quaid-e-Azam Trophy, PSL, Pakistan Cup
5. South Africa: CSA Provincial, CSA T20 Challenge, One-Day Cup
6. New Zealand: Plunket Shield, Super Smash, Ford Trophy
7. West Indies: West Indies Championship, CPL, West Indies One-Day

## Phase 2: Match Page Improvements (v2.1.0)
Make match page look like Cricket Captain.

### Score Bug (Bottom Bar)
- Team names with flags/crests
- Large score (runs/wickets)
- Overs progress bar
- Match status (Day 1 Session 2, etc.)

### Batting/Bowling Tabs
- Batting: Name, Dismissal, Runs, Balls, 4s, 6s, SR%
- Bowling: Name, Type, Overs, Maidens, Runs, Wickets, Econ

### Ball Tracker
- Wagon wheel with shot directions
- Colour-coded: 1, 2-3, 4-5, 6 runs
- Filter by batsman/bowler

### Tactic Controls
- Menu, Highlights, Predictor, Auto Play, Next Ball
- Field position with presets
- Aggression slider per batsman

## Phase 3: Realistic Player Stats (v2.2.0)
Better attribute distributions.

### Realistic Skill Ranges
- Top players: 80-95 overall
- Average players: 50-75 overall
- Developing players: 30-50 overall
- Youth: 20-40 overall

### Format-Specific Stats
- Test specialists: High technique, patience, red-ball bowling
- T20 specialists: High power, innovation, death bowling
- All-rounders: Balanced batting/bowling

## Phase 4: Additional Features (v2.3.0)
- Kit editor
- Emblem editor
- Competition logo editor
- Player editor (retirement controls)
- Network game (online PvP)
- Achievement tracking (already done in v1.2.0)

## Validation After Each Phase
- Godot smoke test: all screens pass
- Python tests: all pass
- Version bump
- Rebuild exe
- Commit and push
