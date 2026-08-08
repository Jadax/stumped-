# Competitive Research — Stumped! vs. the Cricket Management Market

_Added 2026-08-08 as the research deliverable behind the "most fun, best-selling
Steam cricket management game" goal. This doc records what the direct
competition actually ships, what makes their matchday screens work, and what
Steam success looks like for this genre — and turns it into a gap list for
Stumped!._

## 1. The reference: Cricket Captain (Childish Things)

The user's requirement: the matchday screen MUST be a copy of Cricket Captain's
matchday screen. Research was done on the 2024 release (and 2026-era marketing)
via the official Steam / App Store / Play Store pages and trailers.

### Confirmed feature set (2024)
- **7,500+ player database** with real, generated names — depth of squad data is
  the genre's core promise.
- **Score Predictor** — live win-expectation (run-chase %) computed from current
  score/wickets/overs; Stumped! already has this (`get_match_prediction`,
  exposed in-game as PREDICT).
- **Honours boards** — career trophy cabinet per club (Stumped! equivalent:
  Trophy Room screen, v4.x).
- **Commentary** by Daniel Norcross — named, characterful commentary.
- **Rebalanced scoring rates** so tallies match modern real-world cricket.
- **Custom match series** — set up bespoke series; Stumped! equivalent:
  Custom Tournament editor.
- **Phone and desktop layouts** — responsive layouts per platform.

### Matchday screen anatomy (the part we must copy)
Confirmed across the reference screenshots and the structural-realignment plan
(`ethereal-waddling-blum.md`, shipped in v4.54.0):
- **Top:** a broadcast-style scoreboard (teams, current score, overs), with a
  **Ball-tracker** of coloured-dot rows directly beneath it.
- **Left column:** scorecard + commentary as the primary read.
- **Right column (tactics):** one **Bowler card** (name/Change, Stamina bar,
  O/M/R/W/Econ row, "Format Bowling Avg" line) then **two separate batsman
  cards** — each its own bordered card with name+figures header, "Format
  Batting Avg/SR" subtitle, a small wagon wheel, a small pitch-with-batter
  icon, and a **VERTICAL aggression bar**.
- No third "broadcast camera" column — the per-batter mini wagon wheels cover
  that role.

### Where Stumped! now stands vs. that anatomy
- v4.54.0: column order fixed (scorecard/ball-tracker left, tactics right),
  bowler stamina + figures on the card, per-batter bordered cards.
- v4.55.0 (this change): batter cards are fully independent, aggression is a
  vertical `VSlider`, each card shows career "Format Batting Avg/SR", the
  bowler card shows "Format Bowling Avg", and a pitch-with-batter icon sits
  beside each aggression column. Real career figures come from the new
  `_career_figures()` helper in `ipc_server.py` (format-context preferred,
  combined career fallback).

## 2. Competitors in the same market

| Game | What it is | What Stumped! should take |
|---|---|---|
| **Cricket Captain 2024/2026** (Childish Things) | The genre benchmark — data-heavy, classic match engine, yearly release | Matchday layout (being copied), Score Predictor, honours boards, phone/desktop layouts |
| **Cricket Management Tycoon 2026** (Steam app 4717430) | Deep T20-first manager sim with England/Australia domestic tours, manager skill tree, XP/perks | Progression systems: skill trees + XP/perks as a sticky long-term hook |
| **Football Manager (matchday UX)** | The management genre's UX north star | Scoreboard top-left, "Match Day Info" dropdown, bottom event timeline, player conditioning bars, free-positionable widgets |
| **Big-box cricket games** (Cricket 26 era, EA/ICC-licensed) | Arcade/sim playable matches, huge budgets | NOT a model to copy for a management game; they own playable cricket |

### Football Manager matchday principles worth borrowing (from fmscout.com research)
- Scoreboard top-left; a **Match Day Info** dropdown top-right (tactics, stats).
- **Bottom event timeline bar** — match events scroll along a horizontal bar.
- **Player conditioning bars** on the pitch/lineup — Stumped! shows fatigue on
  the bowler card; a full-XI conditioning readout is a later-phase option.
- Widgets are **free-positionable** — low priority for a v1-2 release.

## 3. What actually makes a Steam sports-management hit

Esports Manager case study (Indie.io / viral-marketing analysis, 50k wishlists):
- **Store page + wishlists early.** Wishlists are the #1 launch-day ranking
  input. A barebones but real Steam page months before launch beats polishing
  in obscurity.
- **One viral moment.** A catchy trailer, a streamer drop, or a community
  post that crosses over beyond the niche.
- **Niche density beats breadth.** Sports-management buyers are a small,
  passionate, review-dense audience — a genuinely complete niche product (all
  of Cricket Captain's feature set, done well) converts that audience far
  better than a shallow "more features" pitch.

### Implications for Stumped!
1. **Finish the Cricket Captain matchday copy first** — it is the single most
   visible "this is a real cricket manager" signal and the user's explicit
   priority.
2. **Close the data-depth gaps** (7,500-player style database feel; career
   records everywhere) — depth is the genre's currency.
3. **Prepare Steam-facing assets early** — store text, capsule art, and a 60-90s
   trailer that leads with the matchday screen.
4. **Ship the phone/desktop layout story** — CC advertises it; responsive design
   is a listed roadmap item.

## 4. Stumped! gap list (priority order)

1. **Matchday parity with CC** — DONE for the 12 concept screens (v4.49–4.54);
   v4.55.0 closes the per-batter vertical-aggression cards. Remaining polish:
   full-XI conditioning readout, bottom event timeline, commentary narration
   voice/labels.
2. **Score Predictor visibility** — exists (`get_match_prediction`); make the
   win% a persistent element of the scoreboard, not a button-only readout.
3. **Data-depth surface** — career batting/bowling averages now reach the live
   cards; extend format-keyed records to more surfaces (opposition report,
   team talk, press conference).
4. **Manager progression** — T20-tycoon-style skill tree/XP is the strongest
   competitor hook not yet in Stumped! (roadmap candidate).
5. **Steam launch readiness** — store assets + trailer script + wishlist
   campaign plan (docs/STEAM_LAUNCH_PLAN.md, to be written).
6. **Phone/desktop layouts** — long-term; only after Steam launch.

## 5. Sources
- Cricket Captain 2024 — Childish Things official Steam/App Store/Play Store
  pages and trailer (feature list: 7,500-player DB, Score Predictor, honours
  boards, Norcross commentary, rebalanced scoring, custom series, phone/desktop).
- Cricket Management Tycoon 2026 — Steam app page (4717430): skill tree,
  XP/perks, England/Australia domestic tours, T20-first.
- Football Manager matchday UX — fmscout.com analysis of FM's match screen
  (scoreboard placement, Match Day Info dropdown, event timeline, conditioning).
- Steam success factors — Esports Manager case study coverage (wishlists,
  store-page timing, viral moment, publisher Indie.io).
- Internal: the 12 Cricket Captain reference screenshots supplied by the user
  and `C:\Users\Tushant\.claude\plans\ethereal-waddling-blum.md`.
