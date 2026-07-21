# UX Roadmap — FM26 IA translated to Stumped!

Source: user-supplied Football Manager 26 feature breakdown (six top-nav
tabs: Portal, Squad, Recruitment, Match Day, Club, Career). This maps each
FM26 concept onto a Stumped! (cricket) equivalent and records what already
exists vs. what's still to build. Sidebar groups in `main.py` (`NAV_GROUPS`)
now mirror this six-tab IA.

Status key: **Have** (shipped) · **Partial** (exists, thinner than FM26) ·
**Planned** (not started).

## Global tools

| FM26 | Stumped! equivalent | Status |
|---|---|---|
| Top nav tabs | Sidebar groups: Portal/Squad/Match Day/Recruitment/Club/Career/System | Have |
| Bookmarks | — | Planned |
| Enhanced search (entities + docs) | — | Planned |
| FMPedia / in-game glossary | `ui/help.py` (Help screen) | Partial — static help, not a linked glossary |
| Tutorials | — | Planned |
| Tile/Card system | Card widget (`ui/widgets/`) used throughout | Have (own visual language, not literal FM tiles) |

## Portal (→ Dashboard + Inbox)

| FM26 | Stumped! | Status |
|---|---|---|
| Messages & news | `ui/inbox.py` | Have |
| Fixtures & results | Dashboard | Have |
| League standings | Dashboard | Have |
| Calendar | Dashboard | Partial — next-fixture only, no month view |
| Filters (All/New/Tasks/Unread) | Inbox unread count | Partial — no Tasks filter |
| Advice dropdown (ask backroom) | Assistant Report exists (Squad Report) but not from Portal | Planned |

## Squad

| FM26 | Stumped! | Status |
|---|---|---|
| Overview (list, filter, sort, views) | `ui/squad.py` | Have |
| Squad Planner (timeline, contract predictions, recruitment focus) | — | Planned — biggest gap in Squad |
| Report (stats/comparison/assistant/experience matrix/best XI) | Squad Report tab | Partial — has stats+assistant text, no league comparison or experience matrix |
| Numbers | — | Planned (squad numbers not modelled) |
| Registration (competition eligibility rules) | — | Planned |
| International duty | — | Out of scope for now (no international calendar) |

## Recruitment

| FM26 | Stumped! | Status |
|---|---|---|
| Recruitment Hub (objectives/contract tile/requirements) | `ui/recruitment.py` | Have (v0.26.0) |
| Scouting assignments (send scout, JPA/JPP) | `create_scouting_assignment`/`advance_scouting_assignments`; UI in Transfers + Recruitment Hub | Have (v0.27.0) |
| Shortlists | — | Planned |
| Transfers (browse/bid/offers) | `ui/transfers.py` | Have |
| Staff recruitment (vacancies/database/search) | `ui/staff.py` Market tab | Have (merged into Staff screen rather than under Recruitment — see docs/CURRENT.md note) |

## Match Day

| FM26 | Stumped! | Status |
|---|---|---|
| Dual in/out-of-possession tactics | Field placements + bowling plans (`ui/selection.py`, match engine) | Partial — cricket's tactical surface (field settings, bowling changes, batting order) differs structurally from football formations; not a 1:1 translation |
| Visualiser | — | N/A for cricket in this form |
| Match plans (pre-set, switch mid-match) | Manual field/bowling changes each over | Partial |
| Opposition instructions | — | Planned (target a specific batter/bowler matchup) |
| Opposition report | — | Planned |
| In-match experience (commentary, speed) | `ui/match_view.py` — ball-by-ball text engine, commentary modes | Have (text-based, not 3D) |

## Club

| FM26 | Stumped! | Status |
|---|---|---|
| Club info | Dashboard header / Career screen | Partial |
| Club vision (board expectations) | `src/models/career.py` board confidence | Partial — confidence score exists, no explicit "vision" targets shown to user |
| Facilities | `ui/facilities.py` | Have |
| Staff + responsibilities delegation | `ui/staff.py` | Partial — roster/contracts/market done; delegating specific responsibilities (e.g. auto-pick XI, auto-training) not modelled |
| Board requests (budget/facilities/affiliate/B-team/stadium) | — | Planned |

## Career

| FM26 | Stumped! | Status |
|---|---|---|
| Manager creator (appearance/biography/badges/style/personality) | `New Game Setup` | Partial — team/difficulty selection, no manager persona |
| Manager profile (reputation, history) | `src/models/career.py` | Partial — reputation tracked, no dedicated profile screen |
| Coaching badges | — | Planned |
| Career stats (trophies, W/L) | `ui/career.py` season awards | Partial |
| International management | — | Out of scope (no national-team layer yet) |

## Priority order for next work

Kept consistent with `docs/CURRENT.md`'s existing backlog, re-ranked against
this roadmap:

1. ~~Squad Planner~~ — shipped v0.24.0.
2. ~~Recruitment Hub~~ — shipped v0.26.0.
3. ~~Active scouting assignments~~ — shipped v0.27.0.
4. **Opposition report** — pre-match scouting summary of the next opponent
   (formation-equivalent, key players, strengths/weaknesses, recent form),
   reuses existing player attribute data; feeds Match Day. Next up.
5. Everything else in this doc — tracked but not sequenced yet.

International management, 3D match visualisation, and manager-persona
creation are explicitly deprioritised: they don't fit Stumped!'s current
scope (single-nation league management, text/2D match engine) without a
much larger redesign, and aren't where the FM26 feature set is most
transferable to cricket.
