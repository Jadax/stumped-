# Stumped! UI/UX Redesign — Research & Design Document

Status: **awaiting approval — no code written against this yet.**
Author: lead UI/UX design pass, 2026-07-21. Supersedes the visual notes in
`docs/UX_REVAMP.md` (which stays as the phase history).

---

## 1. Research findings

### Football Manager (FM24 → FM26)
- FM's three pillars — **Efficiency, Familiarity, Predictability** — are the
  genre's constitution. Every FM screen answers: fewest clicks, feels like
  football admin, you always know where things are.
- **FM26's Tile-and-Card overhaul is the single most instructive event in the
  genre in years — because it backfired.** Beta users reported *more* clicks
  to reach the same information, dead space around tiles, and missing
  at-a-glance data (nationality, star ratings) on the player search. The
  community's phrase was "a maze of screens"; SI publicly conceded
  adjustments were needed.
- **Lesson: management-sim players value information density and muscle
  memory over visual fashion. Modernise the skin, never the mental model.**
- What FM still does better than anyone: **one-glance status legibility** —
  any row anywhere (morale, fitness, contract, form) is readable without
  opening anything, and nothing is conveyed by colour alone.

### Motorsport Manager
- "Stark, flat, minimalist… looks like commercial business software" — and
  players praise it. Flat panels, one accent colour, department tabs, zero
  chrome. Its race-day screen changes tempo completely from management
  screens: full-bleed live view, minimal chrome, big numbers.
- Lesson: **two visual tempos** — calm office (management) vs. broadcast
  energy (live match) — make both feel better.

### Cricket Captain 2025/26
- Their headline was literally "completely re-designed, clean-look interface,
  reducing distractions" — the market rewarded a cleanup, not a rethink.
- Still visibly dated: fixed light-blue chrome, cramped dialogs, tiny type.
  Their strengths worth matching: condition icon strips, score predictor,
  ball-by-ball over rows, wagon wheels/beehives.
- Lesson: **cricket buyers accept traditional presentation; they upgrade for
  clarity and simulation trust, not spectacle.**

### OOTP / Eastside & Franchise Hockey Manager
- OOTP ships light-first, spreadsheet-dense, with an almanac's depth — proof
  that depth itself retains players for hundreds of hours. Its weakness is
  intimidation: new players bounce off undifferentiated tables.
- Lesson: **progressive disclosure** — default views curated, full tables one
  click away, never the reverse.

### Wider 2024–26 UI evidence
- Dark UIs are strongest for **data-dense dashboards**: charts and numbers
  become the loudest element; use dark charcoal (never pure black), off-white
  text (never pure white), medium font weights, restrained accents.
- Warm accents (reds/golds) measurably energise; but full warm/light themes
  suit long-form reading, not number-scanning, and full-bright screens
  fatigue during multi-hour sessions (the FM/MM/Steam norm is dark).
- Retention in management sims comes from **loop clarity** (always an obvious
  next action), **trustworthy simulation feedback** (visible cause→effect),
  and **session rhythm** (natural stopping points that invite "one more
  match").

## 2. The five questions

1. **Biggest problem with our current UI:** no opinionated information
   hierarchy — screens are grids of equally-weighted cards with no single
   primary action, no persistent "what should I do next", and the club/date
   context lives in a thin top bar that doesn't anchor the experience. It
   reads competent, not premium.
2. **The one thing FM does best:** one-glance row legibility — every list
   row carries complete, colour-plus-icon status without opening anything.
3. **Our signature element:** the **Over Beads** — the six-ball bead strip
   (● 1 2 4 W ●) used everywhere: live match footer, dashboard last-over
   widget, match reports, player form (last 6 innings as beads). Instantly
   cricket, instantly readable, ownable. Secondary signature: the pitch-wear
   meter already shipped.
4. **Warm vs dark:** dark base, warm blood. Dark charcoal for data density
   and Steam-market fit; warm accents (cricket-ball red, gold, pitch green)
   for energy. A full cream theme would fight every table in the game and
   force a risky rewrite of working screens.
5. **Density vs readability:** FM's answer, adopted: default views curated
   (8–12 columns), "Full" view one tab away; row height ≥ 24 px at 1280×720;
   nothing conveyed by colour alone (always paired with number/icon); every
   screen declares one primary action button.

## 3. Decisions (firm)

### 3.1 Colour scheme — "Test at Dusk" (custom, evolves Midnight Pitch)
Dark warm-charcoal base + cricket-ball red signature. Not FM teal, not
Cricket Captain light-blue — ownable and cricket-red at first sight.

| Token | Hex | Use |
|---|---|---|
| `bg` | `#12100E` | app canvas (warm near-black) |
| `surface` | `#1A1714` | sidebar/top bar |
| `card` | `#221E1A` | panels |
| `raised` | `#2B2620` | hover/alt rows |
| `border` | `#3A332B` | hairlines |
| `text` | `#F4EFE8` | primary text (warm off-white) |
| `muted` | `#A79E92` | secondary text |
| `red` | `#D6493F` | **signature**: primary actions, live indicators, wickets |
| `gold` | `#E0A63C` | ratings, elite tiers, highlights |
| `green` | `#4CAF6D` | positive, money-in, availability |
| `sky` | `#7FB8D8` | links/info/selection (cool relief accent) |

Attribute tiers keep the shipped 5-tier logic, re-tinted: red < 40, amber,
off-white, green, gold 90+. All pairs meet WCAG AA on their backgrounds.

### 3.2 Layout philosophy
- **Two navigation levels, never three**: grouped sidebar → screen tabs.
  Filters/dropdowns live inside the content, not as a third chrome level.
- **Tables-first, cards-as-summaries**: cards only ever summarise and link;
  they never replace a table (the FM26 mistake). Dashboard is the only
  bento-grid screen.
- **Club header band** replaces the thin top bar: crest, club name, division
  & position, cash, date, and one context-aware **Continue** button (FM's
  strongest loop device) that always advances to the next meaningful event.
- **Two tempos**: management screens calm and flat; Match screen full-bleed
  broadcast with its own chrome.

### 3.3 Keep / Change / Add / Remove
**Keep (working, validated):** match engine and all backend; screen set;
Career hub content; player profile stars/value/sparkline; momentum chart,
pitch-wear meter, over beads concept in match footer; crowd audio; Inter.

**Change (redesign):** global palette → Test at Dusk; top bar → club header
band with Continue; sidebar → grouped sections with icons; every screen gets
a consistent tab row + one declared primary action; tables get a shared
sortable DataTable with status icon set; Dashboard → bento "morning
briefing"; Selection → drag order with role-balance meter; Match → three-zone
broadcast layout.

**Add:** context-aware Continue; universal player quick-card popover
(hover/click any player name anywhere); Over Beads as reusable component;
News/inbox digest cards with actions ("View offer" jumps deep); onboarding
hints layer (first-season tooltips, dismissable); colour-blind-safe icon
pairing pass; keyboard map (Space next ball, arrows tabs, Enter primary).

**Remove:** duplicate stat blocks on Dashboard; the separate thin top bar;
per-screen ad-hoc button styles (all buttons from the library); dead
"Operations module" placeholder cards.

### 3.4 Navigation structure
Sidebar (icons + labels, grouped, collapsible to icons at <1440 px):
- **CLUB**: Dashboard, Inbox
- **SQUAD**: Squad, Selection, Training, Youth
- **MATCH**: Fixtures/Pre-Match, Live Match (pulses red on match day)
- **BUSINESS**: Transfers, Finances, Facilities
- **WORLD**: Career, League/Stats
- footer: Settings, Help, Save/Continue status

## 4. Screen-by-screen specifications

Format: layout → tabs → primary/secondary action → default vs hidden.

**Dashboard** — bento grid 2×3: Next Fixture hero (crest v crest, countdown,
pitch/weather, PRIMARY: Continue/Go to Selection) • Position & form (last 5
as beads) • Inbox digest (top 3, actionable) • Squad status (fitness/morale
exceptions only — never the full list) • Finances sparkline • Season
objective progress. Everything links deeper; nothing scrolls.

**Squad** — tabs: Overview / Batting / Bowling / Fielding / Contracts /
Stats. One DataTable, tab switches column set; search + role filter chips;
click row → player quick-card, double-click → full profile. Primary:
Compare; secondary: Offer contract.

**Selection** — tabs: XI & Order / Roles / Opposition. Left: pitch-ordered
XI list with drag handles and over-beads recent form; right: balance meter
(bat depth, bowling options, keeper, spin/pace mix) that updates live —
cricket's version of FM's tactic familiarity bar. Primary: Confirm XI
(disabled until valid, with reason text). Secondary: Auto-pick.

**Match (most important)** — three zones. Top: broadcast score bug band
(score, batters, bowler, session/day, conditions strip, DRS pips). Centre
tabs: Live (commentary + wagon wheel + field) / Scorecard / Analytics
(worm, momentum, manhattan, partnerships, beehive) / Tactics (aggression,
field presets, bowling plan). Bottom: **Over Beads strip** + speed controls +
PRIMARY red button cycling Next Ball → Next Over → Auto. Wicket = full-band
red flash + ambience duck (shipped) + slide-in dismissal card. No sidebar
during play; Exit confirms.

**Transfers** — tabs: Search / Shortlist / Offers In / Offers Out / History.
Search defaults to curated "Scouted for you" cards above the full table
(progressive disclosure). Primary: Make Offer; secondary: Shortlist.

**Training** — tabs: Schedule / Individual / Development. Weekly M/W/F board
as cards; Individual = table with focus dropdowns + intensity sliders +
injury-risk badge; Development = sparkline grid of last-90-day attribute
deltas (green/red). Primary: Save schedule.

**Finances** — tabs: Overview / Ledger / Projection / Sponsors. Overview:
cash hero number + 12-month sparkline + monthly P&L digest cards (shipped
data). Ledger: filterable DataTable. Projection: season cashflow curve with
break-even line. Primary: Set budgets.

**Youth Academy** — tabs: Intake / Development / Staff. Intake day becomes
an event: sealed-envelope card flips to reveal each prospect (gold shimmer
on high potential). Primary: Promote to squad.

**Facilities** — tabs: Grounds / Performance / Commercial. Isometric-flat
club map replacing the table-of-upgrades; click building → upgrade card
with cost/benefit/duration. Primary: Start upgrade.

**Inbox** — tabs: All / Club / Transfers / Board / Reports. Two-pane:
list + reading pane; every message with a verb gets an action button that
deep-links. Unread badge on sidebar (shipped). Primary: contextual action.

**Career** — tabs as shipped (Overview / Ratings / Awards / Trophies) with
new skin; trophy shelf gets simple gold trophy silhouettes per honour type.

**Settings** — tabs: Display / Audio / Gameplay / Accessibility (new: UI
scale 100/115/130 %, colour-blind icon mode, reduced motion, always-show-
numbers). **Help** — searchable manual (shipped) restyled; sidebar TOC.

## 5. Component specifications

- **Card**: flat `card` fill, 1 px `border`, 10 px radius, no shadow at
  rest; 4 px left accent rail only when semantic (red=live, gold=award,
  green=money). Header 13 px semibold caps `muted`.
- **Buttons**: Primary (red fill, off-white text) — exactly one per screen;
  Secondary (outline); Tertiary (text-only); Danger (red outline). States:
  hover +6 % lightness, active −4 %, disabled 40 % alpha with reason
  tooltip. Heights 32/28 px.
- **DataTable** (one shared component): sticky 24 px header, sortable with
  arrow, 26 px rows, zebra `raised`, hover row lighten, selected 2 px gold
  inset; status icons (fitness heart, morale face, form beads, contract
  clock) always icon+value; column sets swap per tab.
- **Tabs**: text + 2 px red underline slide (120 ms); inactive `muted`;
  count badges where useful (Offers 3).
- **Modals**: 200 ms fade+4 px rise, scrim 60 %, max 720 px, Esc closes,
  focus trapped.
- **Sliders**: 6 px track, `raised` unfilled / red filled, 14 px handle,
  value bubble on drag, tick labels at extremes ("Defensive/Attacking").
- **Badges**: 10 px caps pills — red live, gold award, green money-in, sky
  info.
- **Over Beads**: 18 px circles, muted outline default; filled green (runs),
  gold (boundary), red (W), hollow (dot); tooltip per ball.
- **Forms**: 32 px inputs, `bg` fill, border → sky on focus; inline
  validation below field in red 12 px.

## 6. Typography
Inter (shipped, OFL). Display 28 semibold (hero numbers 32 bold tabular),
H1 22 semibold, H2 16 semibold, body 14 regular, table 13, caption/labels
12 & 11 caps +0.4 letter-spacing. Numbers in tables always tabular-lining.
Colour hierarchy: `text` → `muted` → accent-only-with-meaning. Minimum
rendered size 11 px; UI-scale setting multiplies the whole ramp.

## 7. Animation & interaction
120 ms standard / 200 ms modals / 300 ms match-event flashes; ease-out;
nothing blocks input; "reduced motion" kills all non-feedback animation.
Screen changes: 80 ms crossfade (no slides — speed reads as efficiency).
Hover: lighten + pointer; rows underline player names. Feedback: button
press dip, save toast bottom-right 2 s, wicket band flash, boundary gold
sweep on the bead. Loading: skeleton rows (no spinners) for DB-heavy tabs.

## 8. Accessibility
AA contrast enforced per token pair (checked at build via test); never
colour-only (icon/number pairing everywhere, beads carry glyphs • 4 6 W in
colour-blind mode); keyboard: full tab-order, Space=next ball,
←→=tabs, Enter=primary, Esc=back/close; UI scale to 130 %; reduced-motion
toggle; screen-reader groundwork limited to focus order + readable labels
(pygame constraint — full SR support is out of scope, stated honestly).

## 9. Asset requirements
All procedural/vector-drawn in-engine (copyright-clean, resolution-free):
sidebar icon set (14 glyphs, 2 px stroke, 20×20 grid); trophy silhouettes
(3); facility isometric-flat building set (7, two-tone); crest generator
retint to palette (shipped generator); envelope/intake card art (drawn);
weather glyph set (5). No raster/licensed assets. Steam capsule art is a
separate marketing task — flag for later.

## 10. Delivery order (after approval)
1 Theme tokens → 2 component library (Card, Button, DataTable, Tabs, Beads,
Slider, Modal, Badge, quick-card) → 3 shell (sidebar groups + club header +
Continue) → 4 Dashboard → 5 Squad → 6 Selection → 7 **Match** → 8 Transfers
→ 9 Training → 10 Finances → 11 Youth → 12 Facilities → 13 Inbox → 14
Career/Help/Settings → 15 animation pass → 16 accessibility pass → 17
integration & full test suite → 18 packaged build. Each step: tests + screen
render checks + version bump + exe rebuild + push (per AGENTS.md).

## 11. Risks
- FM26's lesson applied to ourselves: we are re-skinning and re-organising,
  **not** changing the data model of any screen — density stays.
- pygame-gui theming limits some polish (focus rings, popovers) — the custom
  widget layer already carries most chrome, so impact is contained.
- Scope: 14 screens × components is multi-session; the delivery order above
  keeps the game shippable after every step.
