# Match Engine Research Notes

The simulation is an original implementation. It uses public rules and research concepts, not copied game code or proprietary probability tables.

## Rules baseline

- [MCC Laws of Cricket](https://www.lords.org/mcc/the-laws): innings, results, follow-on, declarations, overs, extras, boundaries, and dismissals.
- ICC playing conditions are treated as the competition layer for powerplays, bowler limits, reviews, and interrupted limited-overs matches.
- [ICC current playing conditions](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) are the versioned source of truth; the code keeps competition-specific limits outside the delivery sampler.
- [ICC DRS overview](https://www.icc-cricket.com/about/cricket/rules-and-regulations/decision-review-system) confirms the distinction between umpire and player reviews.
- The official DLS resource tables are proprietary. Stumped! therefore labels and uses a simplified resource curve rather than reproducing those tables.

## Statistical architecture

- Asif and McHale's dynamic logistic work motivates separate chase-state features: score relative to par, wickets, balls remaining, and target pressure.
- Ball-by-ball Markov research motivates treating `(runs, wickets, balls, striker, bowler, phase)` as a changing state rather than drawing from a fixed innings distribution.
- Phase-aware T20 optimisation research motivates distinct powerplay, middle-over, and death-over AI decisions.
- The public [From the Pavilion match-engine manual](https://www.fromthepavilion.org/rules.htm?rulespage=matchengine) supports treating tactical orders as guidelines and deriving starting energy from endurance and fatigue. Stumped! implements these ideas independently with its own formulas and calibration.
- Hattrick's public weighted-chance explanation motivates transparent relative-strength sampling. No Hattrick source code, constants, ratings, or event tables are used.

## Refinement architecture

- A persistent 0-100 energy pool is initialised from fitness, bowling stamina and imported pre-match fatigue. Batting, bowling, general fielding, wicketkeeping and captaincy consume different amounts.
- Drinks and innings intervals restore bounded energy. Low energy produces nonlinear scoring, dismissal, accuracy and fielding penalties.
- Manager orders remain the baseline. Every over the batter's effective aggression responds to early wickets, platform strength, innings phase, wickets in hand and chase progress.
- Passive talents affect execution continuously; triggered talents are contextual delivery events and are shown in commentary in square brackets.
- Wicket opportunities and their completion are separate. Catches, run-outs and stumpings perform individual catching, throwing, reflex, keeper and energy checks; missed chances remain visible events.
- The live predictor uses deterministic Monte Carlo sampling from the current conditional delivery distribution. Its cache updates on a new legal state, so pausing does not make the number flicker.

## Implemented factors

Player attack, defence, pace/spin technique, concentration, form, morale, experience, big-match temperament, bowling accuracy, movement, variation, pace, stamina, individual fielding, keeper quality, energy, passive and triggered talents, pitch, weather, ball age, powerplay, chase progress, dot-ball pressure, field setting, contextual aggression, workload, home/away squad strength, and match format all alter the engine or predictor.

The validation tool reports aggregate run rates, wickets, extras, and completion rates across seeded batches. Tuning targets are intentionally broad enough to preserve player and condition variance.
