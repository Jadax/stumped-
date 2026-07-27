# Stumped!

**Build the club. Read the pitch. Win every session.**

Stumped! is a data-driven cricket management simulation for Windows. Take
control of a professional club across league, cup, and friendly cricket; build
a balanced squad; develop young players; manage contracts and finances; and
make the tactical decisions that turn close matches.

The live match experience combines ball-by-ball simulation with fast,
meaningful choices. Select the XI, set the batting order, assign bowlers and
leadership, react to pitch and weather conditions, alter aggression and field
placements, and use DRS when the moment demands it. Away from the ground,
players age, develop, lose form, sustain injuries, change clubs, and eventually
retire, while the domestic competition continues around you.

The interface is deliberately modelled on polished management software: dark,
responsive, card-based screens; readable statistics; consistent controls; and
support from 1280×720 through 4K.

## Features

- T10, T20, The Hundred (100 balls), ODI, and four-innings Test cricket
- Attribute-driven ball-by-ball match engine
- Persistent player energy, fatigue, drinks-break recovery, situational tactical overrides, and triggered talents
- Individual catching, run-out, stumping, keeping, and fielding-opportunity checks
- Deterministic Monte Carlo score predictor and sub-second fast simulation
- Powerplays, wides, no-balls, DRS, DLS, follow-ons, declarations, and Super Overs
- Live batting cards, bowling figures, partnerships, commentary, and match analysis
- Two 12-club domestic divisions with two-up/two-down promotion and relegation
- Knockout cup, friendlies, fixtures, standings, and net run rate
- 600 generated players across 24 clubs, with country-correct youth intakes
- Player development, form, potential, aging, decline, and retirement
- Squad selection, batting styles, designated bowlers, captain, and wicketkeeper
- Transfer scouting, incoming offers, bids, wages, and transfer listing
- Scheduled Monday/Wednesday/Friday training, individual focus and intensity,
  facility/age/potential-driven progression, and visible development history
- Comprehensive League, Cup, Friendly, and International career records
- Season/month/week form trends plus wagon-wheel and line-and-length analytics
- Individual batter and bowler aggression, bowling styles, live perspectives,
  changing weather, evolving pitches, and real-time DLS interruptions
- An all-player transfer database with explainable availability and asking prices
- Stadium, training, medical, academy, commercial, scouting, and grounds upgrades
- Matchday income, sponsorship, wages, budgets, and financial projections
- Ten display currencies with GBP-base accounting that avoids save-game rounding drift
- Persistent SQLite saves and configurable autosaving
- Responsive windowed and fullscreen modes
- High-DPI fullscreen rendering with an exact 2x logical canvas on 4K displays
- Optional match-day crowd effects with mute and volume control; no background music
- Rotating diagnostic logs and user-friendly crash reporting
- Easy, Normal, and Hard careers with genuinely different AI decision quality,
  budgets, board tolerance, and player development
- Searchable in-game cricket manual and match-engine FAQ
- Country-aware name generation and deterministic original player portraits with no external likeness rights
- Supersampled, geometric team crests with no licensed logo dependencies

## Windows installation for development

1. Install **Python 3.14 (64-bit)** from
   [python.org](https://www.python.org/downloads/windows/) — this is the
   version the project is developed and packaged against (pygame-ce 2.5.7
   and PyInstaller 6.21.0 both ship official `cp314` wheels; 3.10+ still
   works if you have an older interpreter already, but 3.14 is what CI-style
   validation in this repo uses). During installation,
   select **Add Python to PATH**.
2. Open PowerShell and move to the project folder:

   ```powershell
   cd C:\Dev\Game\cricket_manager
   ```

3. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. If PowerShell blocks activation, allow it for the current window:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

5. Install the dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

6. Start the game:

   ```powershell
   python main.py
   ```

The first launch creates the local database and all required writable folders.
The packaged Windows edition does not require Python.

## How to play

1. Review the Dashboard for the next fixture, league position, squad status,
   objectives, finances, and recent messages.
2. Open Selection, choose exactly eleven players, assign five bowling options,
   name a captain and wicketkeeper, and arrange the batting order.
3. Set player batting styles and team aggression, then confirm the XI.
4. Review the toss and both lineups on the pre-match screen.
5. During a match, use **Next Ball**, **Play Over**, **Auto**, or **Skip** to
   control pacing. Change bowlers, field presets, and aggression as conditions
   evolve.
6. Between fixtures, improve the squad through transfers, training, youth
   recruitment, facilities, and careful financial management.

### Controls

- **Left mouse button:** select, activate, drag sliders, and sort tables
- **Space:** simulate the next delivery on the Match screen
- **F11:** toggle fullscreen
- **Escape:** leave fullscreen or exit the application
- **Top-bar Save:** save the current campaign immediately

## Save data and logs

- Development save: `data/cricket_manager.db`
- Recovery save: `data/recovery.db`
- Diagnostic log: `logs/error.log`

Back up the SQLite file to preserve a campaign. Never edit it while the game is
running.

## Automated tests

```powershell
python -m unittest discover -s tests -v
```

The test suite uses temporary databases and does not modify the main campaign.

## Building the Windows edition

After installing the requirements, run:

```powershell
python build_and_package.py
```

The release executable and ZIP archive are written to `dist/`. See
`build_windows.bat` for the direct PyInstaller build command.

## Screenshots

Internal render-audit screenshots are generated in `artifacts/`. Final Steam
store captures will be produced from the signed release candidate.

## Minimum requirements

- Windows 10 or Windows 11, 64-bit
- 2 GB RAM
- 250 MB available storage
- 1280×720 display

## Credits

- Design and development: ASTRAIVA (Pty) Ltd
- Frameworks: Python, pygame-ce, pygame-gui, SQLite, and PyInstaller
- Placeholder audio: procedurally generated for this project
- Interface typeface: Inter, distributed under the SIL Open Font License 1.1
- UI inspiration: the broader sports-management genre

Stumped! does not contain licensed real-world teams, competitions, player
likenesses, or third-party game assets.

## License

Copyright © 2026 ASTRAIVA (Pty) Ltd. All rights reserved.

This repository and its assets are proprietary development material. No right
is granted to redistribute, sell, sublicense, reverse engineer, or create
derivative commercial products without written permission from the copyright
holder. Third-party libraries remain subject to their respective licenses.

## Community and release links

- Steam store: coming soon
- Discord: coming soon
- Support: coming soon
- Press kit: coming soon
