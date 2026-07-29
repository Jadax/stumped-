# UI Overhaul Plan — Godot Client (v0.98.0)

## Goal
Make Stumped!'s Godot client visually competitive with FM26, Cricket Captain 2025,
and Cricket 24. All-at-one-session pass. Keep warm light theme + top nav bar.

## Design Decisions
- **Theme:** Keep warm light (`#efe7d3` background). Refine with elevation, shadows, cards.
- **Navigation:** Keep top nav bar. Add icons to section buttons. Better active states.
- **Typography:** Inter font, clear hierarchy (24/18/14/12/10px sizes)
- **Spacing:** Consistent 8px grid (padding: 8, 12, 16, 24, 32)
- **Cards:** Rounded corners (10px), subtle borders, elevation on hover

## Phase 1: Design System Foundation

### 1.1 Theme Refinement (`app_theme.gd`)
- Add shadow/elevation tokens: `SHADOW_SM`, `SHADOW_MD`
- Add spacing constants: `SPACING_XS=4, SPACING_SM=8, SPACING_MD=16, SPACING_LG=24`
- Add card style helpers: `make_card()`, `make_card_elevated()`
- Add divider/separator helper
- Refine `style_nav_button()` with icon support
- Add `style_section_button()` for section headers with icons

### 1.2 Navigation Icons (`nav_icon.gd`)
- Increase glyph size from 18px to 22px
- Increase line weight from 1.6px to 2.0px
- Add new glyphs: bookmarks (star), data_hub (chart), press (mic), career (trophy)
- Section buttons show icons inline with text

### 1.3 Shell Redesign (`shell.tscn` + `shell.gd`)
- Header: team crest with shadow, team name in larger font, date badge
- Nav bar: section buttons with icons, better spacing, active indicator line
- Sub-nav: proper tab strip with underline indicator (not just bg colour)
- Content area: 16px padding on all sides
- Screen transition: keep tween but add subtle scale (0.98 -> 1.0)

## Phase 2: Dashboard Portal Redesign

### 2.1 Dashboard (`dashboard_screen.gd` + `.tscn`)
**Current:** 3 cards in a row (Fixture, Standings, Inbox)
**New:** FM26-style portal with:

**Top row (4 stat tiles):**
- Squad: "25 players · OVR 68.2"
- League: "#3 · 42 pts"
- Finances: "£2.4M"
- Confidence: "Content (65)"

**Middle row:**
- Left (60%): Next Fixture card with team crests, date, venue, format
- Right (40%): League Standings (top 6 with position badges)

**Bottom row:**
- Left (50%): Recent Results (last 5 matches, W/L/D indicators)
- Right (50%): Inbox (last 5 messages with priority dots)

**Design:**
- Cards have 10px border radius, subtle border, 1px gold top accent line
- Stat tiles have larger numbers (24px), smaller labels (10px)
- Fixture card is the most prominent (larger, gold border)

## Phase 3: Screen-by-Screen Polish

### 3.1 Table Screen (base for ~15 screens)
- Sticky header row (position: sticky at top of scroll)
- Column dividers (1px vertical lines between columns)
- Better row hover (slight elevation + bg change)
- Empty state: illustration + "No data" message
- Tab bar: underline indicator style (gold bottom border, no bg)
- Add column sort indicators (▲/▼) on clickable headers

### 3.2 Squad Screen
- Add summary card at top: "25 players · Avg Age 26.4 · Avg OVR 68.2"
- Add role distribution bar (Batsman/Bowler/AR/WK visual breakdown)
- Column headers: NAME, AGE, ROLE (pill), STYLE, OVR, FORM, MORALE, FRESH
- Attributes tab: grouped bars with section headers

### 3.3 Match Day
**Score Bar Redesign:**
- Team names with crests on each side
- Score in large font (32px) with wickets as dots
- Overs as "12.3/20" with progress bar
- Run rate and required rate labels

**Commentary Cards:**
- Each over is a card with over number header
- Individual balls as rows with outcome colour coding
- Wickets get red accent, boundaries get gold accent
- Milestones (50/100) get special highlight card

**Tactics Bar:**
- Group buttons by category (Fielding, Batting, Match Control)
- Icons on each button (not just text)
- Active state shows current setting

**Stats Tabs:**
- Icons on each tab (not just text)
- Better tab strip with underline indicator

### 3.4 Player Profile Modal
- Larger portrait (96x96)
- Attribute hexagon/polygon visualization (FM-style)
- Personality + Traits section (already added)
- Comparison mode button (compare with another player)
- Contract section with wage graph

### 3.5 Bookmarks Screen
- Card-based layout (not just a list)
- Each bookmark is a card with player/team info
- Quick actions: View Profile, Remove

### 3.6 Data Hub
- 2x2 grid of stat cards (already exists, refine styling)
- Add sparkline/trend indicators
- Better card spacing and borders

## Phase 4: Micro-Interactions

### 4.1 Hover Effects
- Cards: subtle shadow lift on hover
- Rows: bg colour change + slight left border accent
- Buttons: bg colour transition (0.1s ease)

### 4.2 Selection States
- Active nav: gold underline indicator
- Active tab: gold underline indicator
- Selected row: gold left border accent

### 4.3 Transitions
- Screen swap: 0.18s fade + slide-up (already exists)
- Card hover: 0.1s shadow transition
- Tab switch: 0.15s underline slide

## Files to Modify

### Core
- `godot_client/scripts/app_theme.gd` — design tokens, helpers
- `godot_client/scripts/shell.gd` — nav, header, transitions
- `godot_client/scenes/shell.tscn` — layout structure
- `godot_client/scripts/nav_icon.gd` — icon glyphs

### Screens
- `godot_client/scripts/dashboard_screen.gd` + `.tscn` — portal redesign
- `godot_client/scripts/table_screen.gd` — sticky header, dividers, sorting
- `godot_client/scripts/match_screen.gd` — score bug, commentary cards
- `godot_client/scripts/player_profile_modal.gd` + `.tscn` — hexagon, comparison
- `godot_client/scripts/bookmarks_screen.gd` + `.tscn` — card layout
- `godot_client/scripts/data_hub_screen.gd` + `.tscn` — refine cards

### Widgets
- `godot_client/scripts/player_hover_card.gd` — better styling
- `godot_client/scripts/player_portrait.gd` — larger sizes

## Validation
- Godot smoke test: all 24 screens pass
- Python tests: all 399 pass (no backend changes)
- Visual: screenshot test at 1280x720 and 1920x1080

## Version
- Bump to v0.98.0
- Update CHANGELOG.md
- Update docs/CURRENT.md
- Rebuild dist/Stumped.exe
- Commit and push
