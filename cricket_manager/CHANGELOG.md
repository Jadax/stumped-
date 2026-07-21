# Changelog

All notable changes to **Stumped!** are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

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
