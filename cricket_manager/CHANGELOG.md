# Changelog

All notable changes to **Stumped!** are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

## [0.22.0] - 2026-07-21

### Added

- **Coaching, Medical, and Scouting staff**: every club now fields a real
  named roster (Head/Batting/Bowling/Fielding/Fitness Coaches, Doctor,
  Physio, Chief Scout, Scout), each with role-appropriate 1-20 attributes
  (`src/models/staff.py`, new `staff` DB table). Existing saves are
  backfilled automatically.
  - **Coaches** now genuinely accelerate training: the assigned discipline's
    coach quality scales daily training gains (a poor coach can more than
    halve progress; an elite one boosts it by up to ~30%).
  - **Medical staff** reduce match injury likelihood and shorten recovery
    time on top of the Medical Centre facility level. A new **Medical
    Centre** screen shows active injuries, return dates, a physiotherapy
    risk-assessment rating, and players at elevated risk.
  - **Scouts** now genuinely matter: the Transfer Market shows an estimated
    OVR/POT with a scout confidence percentage instead of the exact true
    value — a poor scouting department's estimates carry real error; a
    world-class one is nearly exact.
  - Staff age and slowly improve or decline at each season rollover.
  - New **Staff** screen (Coaching/Medical/Scouting tabs with a detail panel).
- **ASTRAIVA (Pty) Ltd** publisher mark on the splash screen.

## [0.21.0] - 2026-07-21

### Added

- **Contract negotiation**: a full offer/counter/accept flow reachable from
  any player profile's NEGOTIATE button. Propose weekly wage, contract
  length, and a signing bonus; the player accepts, counters with a figure
  based on their true valuation, or rejects outright, weighing morale, age,
  and existing contract security (`src/models/contracts.py`). Agreed terms
  are written straight to the save.
- **Targeted academy recruitment**: the Youth Academy screen gained a
  "Scout For" role selector (Any / Batsman / Pace Bowler / Spin Bowler /
  All-Rounder / Wicketkeeper). Recruits generate with realistic role-true
  skills — a requested bowler will never quietly out-bat a requested
  batsman, and pace/spin focus genuinely biases each prospect's skill split.
- Real country flag artwork (public-domain Flagpedia PNGs) replaces the
  hand-drawn flag approximations throughout the game.
- Spatial analytics on the player Match Stats tab now has a **This
  Match / Season** filter and a much larger wagon-wheel/bowling-map area,
  so it stays legible as career data accumulates.
- A club crest now anchors the top bar, and the sidebar footer reads
  "© ASTRAIVA (Pty) Ltd" (all legal/credits text updated to match).

### Fixed

- **Match screen score-bug and action row overhaul**: the live header was
  cramming six unrelated fields into one 58px row with hardcoded pixel
  offsets, causing format/DRS/status text to visibly overlap and merge at
  1280x720. It's rebuilt as a six-column grid with fixed proportional
  widths and vertical dividers, so no two fields can ever collide. The
  ten-button action row (PREDICT/AUTO/NEXT BALL/…/EXIT) — badly cramped
  into one row — now spans two clearly-spaced rows.
- **Fullscreen text blur on common monitors**: the fullscreen logical
  canvas always targeted ~1920x1080, which is a *non-integer* stretch on
  a 2560x1440 desktop (1.33x) and blurs every glyph. Common resolutions
  (1440p, 4K, ultrawide, 5K) now resolve to an exact integer-scale logical
  canvas (2560x1440 → clean 2x from 1280x720; unchanged clean 2x for 4K).
- **Blocky text and jagged curves**: text now renders at native pixel size
  (the previous supersample-then-downscale pass had gone soft on larger
  monitors) and every remaining aliased circle/polygon outline (radar
  chart, portraits, gauges) now draws anti-aliased.
- Higher-detail procedural player portraits: 4x supersampling (was 3x), a
  simple kit collar, and a soft edge vignette.
- Removed the leftover "UI FOUNDATION 2.14+" placeholder label.

## [0.19.1] - 2026-07-21

### Fixed

- Crash when hovering a Squad row: the Skills-tab mental average had
  overwritten each row's mental attribute dictionary, breaking the player
  quick-card (and profile modal). The average now lives under its own key,
  the quick-card is defensive against malformed rows, and a regression test
  hovers real table rows.

## [0.19.0] - 2026-07-21

### Added

- **Player quick-card**: hovering any row on the Squad table shows a compact
  popover — portrait, role, age, nationality, tier-coloured overall,
  potential stars, and form/fitness/morale bars — clamped to the window.
- **Squad view tabs**: Overview / Skills / Contracts swap the shared table's
  column sets (per-discipline averages and potential on Skills; value, wage,
  and years remaining on Contracts).
- **Accessibility settings** (persisted to the save, applied live):
  - Reduced Motion — disables the wicket flash and hover growth.
  - Colour-blind Glyphs — forces result glyphs on the Over Beads.
  - UI Scale — 100% / 110% / 120% interface text.
- **Matchday polish**: DRS review pips in the score bug and a fading red
  band flash on wickets (suppressed by Reduced Motion).

## [0.18.0] - 2026-07-21

### Changed

- **Sharper, modern rendering pass**: all UI text is now supersampled (drawn
  at 2× and smooth-downscaled, with a render cache) for crisper glyph edges,
  and every circle in the interface — beads, portraits, gauges, menu motifs —
  is anti-aliased.
- Card accent rails and hover borders follow the signature red / sky accent
  instead of the legacy green.

### Added

- **XI Balance meter** on the Selection screen: live batting depth, bowling
  options, pace/spin mix, and wicketkeeper checks, tier-coloured, updating as
  the XI changes — cricket's answer to FM's tactic familiarity bar.

## [0.17.0] - 2026-07-21

### Added

- **Grouped sidebar navigation** — CLUB / SQUAD / MATCH / BUSINESS / WORLD /
  SYSTEM section headers per the approved redesign.
- **CONTINUE ▸** — the context-aware loop button in the header band: advances
  one day and stops on the Pre-Match screen when a fixture is due; SAVE
  becomes a quiet secondary control.
- **TabBar** component — text tabs with the sliding signature-red underline,
  adopted on the Career screen.

### Fixed

- Card headers and gradients now render in fully headless contexts (render
  audits before a display exists).

## [0.16.0] - 2026-07-21

### Changed

- New **"Test at Dusk"** skin per the approved redesign (docs/DESIGN.md):
  warm near-black canvas, warm charcoal surfaces, cricket-ball red as the
  signature action colour, gold ratings, pitch green positives, and a cool
  sky accent reserved for links and info.
- Button hierarchy redesigned: primary actions are now signature red,
  confirm/positive actions green, and destructive actions render as red
  outline buttons; sidebar selection and the top action button follow the
  signature red.
- The live match header band is tinted signature red — management screens
  stay calm, match screens carry broadcast energy.

### Added

- **Over Beads** — Stumped!'s signature six-ball strip widget (hollow dot,
  green runs, gold boundary, red wicket, sky extras), now rendering the
  current over on the live match footer.
- Automated WCAG contrast tests: primary text AAA on canvas, secondary text
  AA on cards, bold text AA on the signature red.

## [0.15.0] - 2026-07-21

### Added

- **T10 format**: a fully playable 10-over format (60 balls, 12-ball bowler
  limit, 3-over powerplay, over-5 drinks break, tuned scoring baselines),
  selectable in custom tournament setup.
- **Wicketkeeping depth**: weak glovework now leaks byes on missed takes —
  byes are credited to extras, rotate the strike correctly, and produce their
  own commentary; totals reconcile exactly.
- **Deeper finances**: a monthly profit-and-loss inbox digest on the 1st of
  each month with per-category income/expense lines and the closing balance.

### Changed

- The engine's overs limits are now derived from a single `overs_limit()`
  helper instead of scattered T20/ODI conditionals, so new formats inherit
  projections, DLS reductions, and declaration logic automatically.

## [0.14.0] - 2026-07-21

### Added

- Permanent honours: league champions of both divisions and the Knockout Cup
  winners are written to a new `honours` table at season end (older saves
  migrate automatically), and the Career screen's Trophy Cabinet now shows the
  club's real silverware.
- Season-end inbox briefings: a silverware celebration when the user's club
  wins a title, the full individual Season Awards list, and a board season
  review whose tone follows the board-confidence model.
- The match engine now logs real fielding chances per batter (dropped
  catches, missed stumpings, missed run-outs) and surfaces them on each
  delivery event; the player Match Stats chances panel now shows genuine
  dropped-catch and let-off counts instead of estimates.

## [0.13.0] - 2026-07-21

### Added

- New **Career** screen in the sidebar with four tabs:
  - **Overview** — board confidence and manager reputation gauges with a
    written board verdict, plus season position, record, points, and NRR.
  - **World Ratings** — ICC-style 0–1000 ranking points for the top 20
    batters, bowlers, and all-rounders across every club in the world.
  - **Awards** — live season-award leaders (Batter, Bowler, Young Player, and
    Player of the Season).
  - **Trophies** — the club's trophy cabinet, ready to collect honours.
- `src/models/career.py`: pure, tested models for board confidence, manager
  reputation, world rating points, and season awards, shared with future
  season-end processing.

## [0.12.0] - 2026-07-21

### Added

- Momentum chart in the match Stats Hub: a rolling four-over swing line
  (runs scored minus wicket damage) coloured green/red around the axis.
- Continuous low crowd ambience during live matches, started on the first
  delivery and faded out when leaving the match screen.
- Broadcast-style audio ducking: the crowd bed dips under the wicket roar and
  swells back in over a few seconds.

### Changed

- Live match header restyled as a broadcast score bug: accent gradient,
  underline rail, a coloured weather pip, and a pitch-wear meter that shifts
  green → amber → red as the surface deteriorates.

## [0.11.0] - 2026-07-20

### Added

- FM-style five-star ability and potential ratings (half-star precision) on
  the player profile, via a new reusable `StarRating` widget.
- Market value on the player profile's contract card, computed from the live
  transfer valuation model.
- A 30-match form sparkline on the player profile's contract and traits card.
- Headless render tests covering the star widget, attribute colour tiers, and
  every player-profile tab.

## [0.10.0] - 2026-07-20

### Changed

- New "Midnight Pitch" interface skin: deeper blue-black canvas, electric
  sky-blue action accent, refreshed surfaces, borders, and text colours across
  every screen, the pygame-gui theme, and the packaged defaults.
- Football-Manager-style five-tier attribute colouring (red/amber/white/green
  and gold for elite 90+ ratings) applied through a single shared
  `attribute_colour()` token used by all attribute meters.
- Card headers now render with a subtle accent gradient and retained accent rail.

### Added

- `docs/UX_REVAMP.md`: competitor research (Cricket Captain 25/26, Cricket
  Management 26, From the Pavilion, Big Ant titles) and a five-phase UI/UX and
  feature-depth roadmap covering the player profile hub, broadcast-style
  matchday presentation, career depth, and systems depth.

## [0.9.0] - 2026-07-20

### Added

- Expanded player attributes, individual match tactics, bowling styles, energy,
  form, career records, spatial shot data, and delivery maps.
- Country-correct youth recruitment and country-specific generated identities.
- Scheduled, facility-aware training with intensity and injury-risk modelling.
- Dynamic weather, pitch wear, rain interruptions, and condition-aware AI.
- Twelve-team divisions, promotion and relegation, and an expanded domestic cup.
- Full transfer-market search, willingness-to-sell logic, and calculated prices.
- Seven upgradeable club facilities with interconnected sporting and financial effects.
- Detailed player, selection, match-perspective, weather, pitch, and analytics views.

### Changed

- Refined the warm dark interface for 1280x720 through 4K displays.
- Improved fictional procedural portraits, generated team identities, tables,
  widgets, help content, and accessibility of match analytics.
- Existing 16-team saves now migrate safely into the 24-team competition model.

### Verified

- 50 automated tests pass.
- Packaged startup diagnostics pass.
- Fifty-over fast simulation completes in under one second on the build machine.
