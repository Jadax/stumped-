# Stumped! system interconnections

This document is the balancing contract for v0.9.0. It explains why every
visible player and club value matters and gives future tuning work one source
of truth.

## Player attributes

- Batting attack, power, timing and the individual aggression order increase
  scoring opportunities, while defence, concentration and pace/spin technique
  protect the wicket. Running influences converted singles and doubles.
- Bowling pace, accuracy, control, swing/spin, variation and deception shape
  line, length, extras, scoring pressure and wicket probability. A player's
  bowling style changes the pitch and weather bonuses they receive.
- Catching, throwing, reflexes, agility, keeping and ground fielding drive the
  individual checks for catches, stumpings, run-outs, missed chances and saved
  runs.
- Experience, consistency, big-match temperament, leadership, morale and form
  alter performance variance and AI selection. Fitness and endurance govern
  starting energy, depletion, injury risk and late-spell effectiveness.

## Career and development

- Training runs only on scheduled weekdays. Focus and intensity determine the
  attributes trained; age, ability-to-potential headroom, coach quality and the
  training-ground level determine speed. Heavy work raises injury risk and a
  better medical centre reduces it.
- Form is recorded after matches and exposed as week, month and season values.
  The engine uses current form, while selectors and AI use form, fitness,
  morale, role balance and conditions.
- Potential caps growth. Age slows development and eventually introduces
  decline. Ability, potential, age, role, form, contract length and league
  strength feed wages, market value and asking-price logic.

## Club infrastructure

- Stadium: capacity, atmosphere and matchday income.
- Training Ground: attribute growth rate.
- Medical Centre: injury prevention and recovery.
- Academy: youth intake ability and potential.
- Commercial Office: sponsor and merchandise income.
- Scouting Network: search knowledge and detailed report capacity.
- Grounds Department: pitch preparation and slower deterioration.

Every facility has five levels. An upgrade costs cash, occupies seven calendar
days and applies only after completion.

## Match conditions and analysis

- Weather evolves during play. Sun favours batting, cloud and overcast skies
  help movement, and rain can reduce a limited-overs match and recalculate its
  target.
- Green, dry, dusty, flat and worn surfaces apply different pace, spin,
  batting and variability modifiers. Test pitches wear as legal balls accrue.
- Ring shows every shot and the current field. Boundary filters the same data
  to fours and sixes. Manhattan groups runs by over; Partnerships groups runs
  by wicket stand. Wagon wheels and line-and-length maps persist to the player
  profile and career database.

## Competition and economy

Each division contains 12 clubs. The top two and bottom two exchange divisions
at season end, and all 24 clubs enter the knockout cup. Results update points,
net run rate, form, career records, income, objectives and AI squad decisions.
