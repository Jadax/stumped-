# Cricket Manager — Windows development setup

This guide assumes Windows 10 or 11 (64-bit). SQLite is included with Python, so
you do **not** need to install a separate SQLite program.

## 1. Install Python

1. Open <https://www.python.org/downloads/windows/>.
2. Download a current 64-bit Python release (Python 3.10 or newer).
3. Run the installer and tick **Add python.exe to PATH**.
4. Choose **Install Now**.
5. Open PowerShell from the Start menu and verify:

   ```powershell
   python --version
   python -m pip --version
   ```

If Windows opens the Microsoft Store instead, disable the `python.exe` App
Execution Alias in Windows Settings, then reopen PowerShell.

## 2. Open the project folder

In PowerShell, move to the folder containing this project:

```powershell
cd C:\Dev\Game\cricket_manager
```

If you copied the project elsewhere, substitute that path.

## 3. Create an isolated environment (recommended)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once in the same window and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 4. Install the game libraries

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`pygame-ce` supplies the maintained `pygame` module. `pygame-gui` supplies the
professional widget toolkit. PyInstaller is included now for the later Windows
`.exe` packaging phase.

## 5. Run the game

```powershell
python main.py
```

On first launch, `data\cricket_manager.db` is created automatically and seeded
with 24 teams, 600 players, a first fixture, and 10 example Inbox messages. Use
the sidebar to switch among all eleven management screens.
Press **F11** to toggle fullscreen and **Escape** to leave fullscreen or quit.

### Current UI controls

- In **Selection**, click a player to add/remove them, use the row arrows to
  change batting order, and click each player's style label to cycle through
  Silly, Blitz, Build, and Rotate.
- In **Match**, use Batting/Bowling/Summary and the six analysis tabs to switch
  views. **Space** advances one ball; Next Ball, Play Over, Skip, Play, Auto,
  Predictor, field, DRS, and bowler controls are also available onscreen. The
  live display now uses the permanent format-aware ball-by-ball engine.
- Click the current batter or bowler card during a match to open their player
  profile. The Match Stats tab shows their live innings graph and chances.
- The top-bar **Save** button writes current selection and match UI state.
- **Transfers** supports scouting, incoming bid decisions, player listing, and
  outgoing offers. **Training** can run one or 30 development days.
- **Finances** controls ticket price, sponsorship renewal, matchday revenue, and
  the club ledger. **Facilities** upgrades complete after seven calendar days.
- Use **Advance Day** on Dashboard to process fixtures, training, wages,
  sponsorships, construction, and system Inbox messages.

## Verify the match engine

From the project folder, run the automated rules and accounting checks:

```powershell
python -m unittest discover -s tests -v
```

You can also simulate one complete match in every format without opening the
game window:

```powershell
python match_engine.py
```

## Troubleshooting

- **`python` is not recognized:** reinstall Python and select **Add Python to
  PATH**, then reopen PowerShell.
- **`No module named pygame`:** activate `.venv`, then rerun
  `python -m pip install -r requirements.txt`.
- **SDL or display error over Remote Desktop:** update the display driver and
  run in a normal desktop session. The game needs a graphical Windows session.
- **Corrupt test database:** close the game, rename
  `data\cricket_manager.db`, and launch again. A fresh database is generated.
- **Very small display:** Windows must expose at least 1280×720. The interface
  scales proportionally above that size, including 4K displays.

## Project layout

```text
cricket_manager/
├── main.py                 Application entry point and screen manager
├── database.py             SQLite schema, seed generation, save/load helpers
├── match_engine.py         T10, T20, Hundred, ODI, and Test simulation
├── competition.py          League, cup, calendar, and season progression
├── config.json             Display, theme, and gameplay defaults
├── requirements.txt        Python dependencies
├── ui/                     Modular screens and player modals
│   └── widgets/            Reusable cards, tables, charts, sliders and buttons
├── data/                   Local SQLite save file (created on first launch)
├── tests/                  Automated match-engine regression suite
└── assets/
    ├── fonts/              Future licensed font files
    └── images/             Future icons and artwork
```
