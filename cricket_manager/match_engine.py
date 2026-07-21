"""Deterministic, data-driven cricket match simulation.

The rendering layer deliberately knows nothing about probability or cricket
laws.  It asks :class:`Match` for one delivery at a time and receives a small
serialisable event dictionary.  This makes the same engine suitable for the
live screen, instant simulation, AI fixtures, save games, and unit tests.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import random
from typing import Any, Iterable
from src.models.difficulty import DifficultyManager
from src.models.player import PlayerTactics, SPIN_STYLES


FORMATS = {"T20", "ODI", "Test"}
PITCHES = {"Green", "Dry", "Dusty", "Flat", "Worn"}
WEATHER = {"Sunny", "Overcast", "Rain Threat", "Cloudy"}
FIELD_PRESETS = {"Aggressive", "Neutral", "Defensive"}

# Talents are deliberately data, not hard-coded branches in the UI.  Players
# may supply their own ``talents`` field (from an editor or Workshop database),
# while generated players receive deterministic talents inferred from skills.
PASSIVE_TALENTS = {"Gifted", "Skilled", "Iron Constitution", "Safe Hands"}
TRIGGERED_TALENTS = {
    "Accumulator", "Power Hitter", "Swing", "Yorker", "Slower Ball",
    "Doosra", "Reflex Catch", "Rocket Arm",
}


class BallEventPool:
    """Reuse short-lived delivery dictionaries during fast simulation."""

    def __init__(self, capacity: int = 64) -> None:
        self.capacity = capacity
        self._available: list[dict[str, Any]] = []

    def acquire(self, **values: Any) -> dict[str, Any]:
        event = self._available.pop() if self._available else {}
        event.clear(); event.update(values)
        return event

    def release(self, event: dict[str, Any]) -> None:
        if len(self._available) < self.capacity:
            event.clear(); self._available.append(event)


def overs_text(balls: int) -> str:
    """Convert a legal-ball count to cricket's ``overs.balls`` notation."""
    return f"{balls // 6}.{balls % 6}"


def _mean(values: Iterable[float], default: float = 50.0) -> float:
    values = list(values)
    return sum(values) / len(values) if values else default


def _attrs(player: dict[str, Any], group: str) -> dict[str, float]:
    """Return an attribute group, accepting DB-decoded or JSON-style players."""
    value = player.get(group, {})
    return value if isinstance(value, dict) else {}


def _role(player: dict[str, Any]) -> str:
    return str(player.get("role", "Batsman"))


@dataclass
class BatterLine:
    player_id: int
    name: str
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    dismissal: str = "did not bat"
    not_out: bool = True
    outcomes: list[Any] = field(default_factory=list)


@dataclass
class BowlerLine:
    player_id: int
    name: str
    balls: int = 0
    maidens: int = 0
    runs: int = 0
    wickets: int = 0
    wides: int = 0
    no_balls: int = 0
    current_over_runs: int = 0

    @property
    def economy(self) -> float:
        return self.runs * 6 / self.balls if self.balls else 0.0


@dataclass
class InningsState:
    number: int
    batting_team: int
    bowling_team: int
    batting_name: str
    bowling_name: str
    batting_order: list[dict[str, Any]]
    bowling_squad: list[dict[str, Any]]
    target: int | None = None
    runs: int = 0
    wickets: int = 0
    legal_balls: int = 0
    striker: int = 0
    non_striker: int = 1
    next_batter: int = 2
    current_bowler_id: int | None = None
    previous_bowler_id: int | None = None
    extras: dict[str, int] = field(default_factory=lambda: {"w": 0, "nb": 0, "lb": 0, "b": 0})
    batters: dict[int, BatterLine] = field(default_factory=dict)
    bowlers: dict[int, BowlerLine] = field(default_factory=dict)
    partnerships: list[dict[str, Any]] = field(default_factory=list)
    fall_of_wickets: list[dict[str, Any]] = field(default_factory=list)
    partnership_runs: int = 0
    partnership_balls: int = 0
    completed: bool = False
    declared: bool = False
    end_reason: str = ""

    def __post_init__(self) -> None:
        if not self.batters:
            self.batters = {
                int(p["id"]): BatterLine(int(p["id"]), str(p["name"]))
                for p in self.batting_order
            }
        if not self.bowlers:
            self.bowlers = {
                int(p["id"]): BowlerLine(int(p["id"]), str(p["name"]))
                for p in self.bowling_squad
            }
        for index in (0, 1):
            if index < len(self.batting_order):
                self.batters[int(self.batting_order[index]["id"])].dismissal = "not out"

    @property
    def striker_player(self) -> dict[str, Any]:
        return self.batting_order[min(self.striker, len(self.batting_order) - 1)]

    @property
    def non_striker_player(self) -> dict[str, Any]:
        return self.batting_order[min(self.non_striker, len(self.batting_order) - 1)]

    @property
    def overs(self) -> str:
        return overs_text(self.legal_balls)


class Match:
    """A complete T20, ODI, or Test match with ball-by-ball state.

    Team IDs may be database IDs or any stable integer. Players are ordinary
    dictionaries returned by ``database.fetch_players``.
    """

    MAX_BALLS = {"T20": 120, "ODI": 300, "Test": None}
    MAX_BOWLER_BALLS = {"T20": 24, "ODI": 60, "Test": None}

    def __init__(
        self,
        home_team: dict[str, Any],
        away_team: dict[str, Any],
        home_xi: list[dict[str, Any]],
        away_xi: list[dict[str, Any]],
        match_format: str = "T20",
        *,
        pitch: str = "Green",
        weather: str = "Overcast",
        knockout: bool = False,
        seed: int | None = None,
        batting_first_id: int | None = None,
        difficulty: str = "Normal",
    ) -> None:
        if match_format not in FORMATS:
            raise ValueError(f"Unsupported format: {match_format}")
        if len(home_xi) != 11 or len(away_xi) != 11:
            raise ValueError("A match requires exactly eleven players per team")
        self.rng = random.Random(seed)
        self.format = match_format
        self.pitch = pitch if pitch in PITCHES else "Green"
        self.weather = weather if weather in WEATHER else "Overcast"
        self.weather_forecast = self._build_weather_forecast(self.weather)
        self.weather_index = 0
        self.pitch_wear = 0.0
        self.shot_events: list[dict[str, Any]] = []
        self.bowling_events: list[dict[str, Any]] = []
        self.knockout = knockout
        self.difficulty = DifficultyManager(difficulty)
        self.teams = {int(home_team["id"]): home_team, int(away_team["id"]): away_team}
        self.lineups = {int(home_team["id"]): list(home_xi), int(away_team["id"]): list(away_xi)}
        self.home_team_id, self.away_team_id = int(home_team["id"]), int(away_team["id"])
        first = batting_first_id or self.rng.choice([self.home_team_id, self.away_team_id])
        if first not in self.teams:
            raise ValueError("batting_first_id must identify one of the two teams")
        second = self.other_team(first)
        self.innings_order = [first, second] if self.format != "Test" else [first, second, first, second]
        self.innings: list[InningsState] = []
        self.current_innings_index = 0
        self.completed = False
        self.result = ""
        self.winner_id: int | None = None
        self.is_super_over = False
        self.super_over_scores: dict[int, int] = {}
        self.commentary: list[dict[str, Any]] = []
        self.last_six: list[str] = []
        self.field_setting = "Neutral"
        self.batting_aggression = 5
        self.effective_batting_aggression = 5
        self.bowling_aggression = 5
        self.day = 1
        self.session = 1
        self.reviews = {self.home_team_id: 2, self.away_team_id: 2}
        self.pending_review: dict[str, Any] | None = None
        self._pre_ball_state: InningsState | None = None
        self.rain_overs: int | None = None
        self.rain_interruption_applied = False
        self.event_pool = BallEventPool()
        self.last_factors: dict[str, float | str | bool] = {}
        self.injuries: list[dict[str, Any]] = []
        self.energy: dict[int, float] = {}
        self.starting_energy: dict[int, float] = {}
        self.last_triggered_talent: str | None = None
        # Real fielding-chance tallies per batter id, surfaced on the UI's
        # chances panel: {"dropped": n, "missed_stumping": n, "missed_runout": n}.
        self.chance_log: dict[int, dict[str, int]] = {}
        self._prediction_cache: dict[tuple[int, int, int, int], int] = {}
        self.captains = {
            team_id: int(max(squad, key=lambda p: _attrs(p, "mental").get("experience", 50))["id"])
            for team_id, squad in self.lineups.items()
        }
        self._initialise_energy()
        self._start_innings(first, second)

    def _build_weather_forecast(self, opening: str) -> list[str]:
        transitions={"Sunny":["Sunny","Sunny","Cloudy","Overcast"],"Cloudy":["Cloudy","Overcast","Sunny","Rain Threat"],
                     "Overcast":["Overcast","Cloudy","Rain Threat","Sunny"],"Rain Threat":["Rain Threat","Overcast","Cloudy","Sunny"]}
        forecast=[opening]
        for _ in range(11):
            options=transitions[forecast[-1]]; forecast.append(self.rng.choices(options,[55,22,15,8],k=1)[0])
        return forecast

    def _update_conditions(self) -> None:
        """Evolve weather by match phase and wear the pitch every legal ball."""
        innings=self.current_innings
        interval=30 if self.format=="T20" else 60 if self.format=="ODI" else 90
        match_balls=sum(item.legal_balls for item in self.innings)
        index=min(len(self.weather_forecast)-1,match_balls//interval)
        if index!=self.weather_index:
            self.weather_index=index; self.weather=self.weather_forecast[index]
            self._comment(f"Conditions update: {self.weather.lower()} skies now over the ground.","milestone")
        wear_rate={"T20":.035,"ODI":.055,"Test":.085}[self.format]
        grounds=float(self.teams[innings.batting_team].get("grounds_level",1))
        self.pitch_wear=min(100.0,match_balls*wear_rate/max(.8,1+(grounds-1)*.04))
        if self.format=="Test" and self.pitch_wear>=62 and self.pitch not in {"Worn","Dusty"}: self.pitch="Worn"
        if (self.format != "Test" and self.weather == "Rain Threat" and not self.rain_interruption_applied
                and self.current_innings.legal_balls >= 30 and self.rng.random() < .055):
            maximum = 20 if self.format == "T20" else 50
            completed = self.current_innings.legal_balls // 6
            reduced = max(completed + 3, maximum - self.rng.randint(2, 8 if self.format == "T20" else 18))
            self.apply_rain_interruption(min(maximum, reduced))

    def apply_rain_interruption(self, revised_overs: int) -> int:
        """Apply a live limited-overs rain reduction and refresh a chase target."""
        if self.format == "Test":
            self._comment("Rain stops play; lost time may affect the declaration and result.", "milestone")
            return 0
        maximum = 20 if self.format == "T20" else 50
        completed = self.current_innings.legal_balls // 6
        self.rain_overs = max(completed + 1, min(maximum, int(revised_overs)))
        self.rain_interruption_applied = True
        if len(self.innings) >= 2:
            self.current_innings.target = self.dls_target(self.innings[0].runs)
        target = self.current_innings.target or 0
        suffix = f" Revised target: {target}." if target else ""
        self._comment(f"Rain interruption: the innings is reduced to {self.rain_overs} overs.{suffix}", "milestone")
        return target

    def _initialise_energy(self) -> None:
        """Give every player a match energy pool derived from endurance.

        ``mental.fitness`` represents general conditioning and bowling stamina
        represents repeat-effort endurance.  Imported databases may also expose
        a 0-100 ``fatigue`` value; it safely reduces the starting pool.
        """
        for squad in self.lineups.values():
            for player in squad:
                pid = int(player["id"])
                mental = _attrs(player, "mental")
                physical = _attrs(player, "physical")
                fitness = physical.get("fitness", mental.get("fitness", 50))
                stamina = _attrs(player, "bowling").get("stamina", fitness)
                endurance = physical.get("endurance", mental.get("endurance", fitness)) * .55 + fitness * .25 + stamina * .20
                fatigue = max(0.0, min(100.0, float(player.get("fatigue", 0))))
                value = max(42.0, min(100.0, 68 + endurance * .32 - fatigue * .38))
                self.starting_energy[pid] = value
                self.energy[pid] = value

    def player_energy(self, player_id: int) -> float:
        """Return the player's current energy on the public 0-100 scale."""
        return round(self.energy.get(int(player_id), 100.0), 1)

    def _spend_energy(self, player_id: int, amount: float) -> None:
        pid = int(player_id)
        self.energy[pid] = max(0.0, self.energy.get(pid, 100.0) - max(0.0, amount))

    def _recover_energy(self, team_id: int | None = None, amount: float = 6.0) -> None:
        ids = {int(p["id"]) for tid, squad in self.lineups.items() if team_id is None or tid == team_id for p in squad}
        for pid in ids:
            ceiling = self.starting_energy.get(pid, 100.0)
            self.energy[pid] = min(ceiling, self.energy.get(pid, ceiling) + amount)

    def talents_for(self, player: dict[str, Any]) -> dict[str, list[str]]:
        """Return passive/triggered talents, supporting editor-authored data."""
        supplied = player.get("talents")
        if isinstance(supplied, dict):
            return {
                "passive": [str(v) for v in supplied.get("passive", []) if str(v) in PASSIVE_TALENTS],
                "triggered": [str(v) for v in supplied.get("triggered", []) if str(v) in TRIGGERED_TALENTS],
            }
        batting, bowling, fielding = _attrs(player, "batting"), _attrs(player, "bowling"), _attrs(player, "fielding")
        passive: list[str] = []
        triggered: list[str] = []
        if float(player.get("potential", 0)) >= 88: passive.append("Gifted")
        if float(player.get("overall", 0)) >= 82: passive.append("Skilled")
        if _attrs(player, "mental").get("fitness", 0) >= 82: passive.append("Iron Constitution")
        if fielding.get("catching", 0) >= 82: passive.append("Safe Hands")
        if batting.get("concentration", 0) >= 72: triggered.append("Accumulator")
        if batting.get("attack", 0) >= 76: triggered.append("Power Hitter")
        if bowling.get("swing_or_spin", 0) >= 76: triggered.append("Swing" if bowling.get("pace", 50) >= 58 else "Doosra")
        if bowling.get("accuracy", 0) >= 78: triggered.append("Yorker")
        if bowling.get("variation", 0) >= 76: triggered.append("Slower Ball")
        if fielding.get("reflexes", 0) >= 80: triggered.append("Reflex Catch")
        if fielding.get("throwing", 0) >= 80: triggered.append("Rocket Arm")
        # Cap inferred talent density and vary equally rated generated players.
        offset = int(player.get("id", 0)) % max(1, len(triggered)) if triggered else 0
        triggered = (triggered[offset:] + triggered[:offset])[:2]
        return {"passive": passive[:2], "triggered": triggered}

    def _talent_proc(self, batter: dict[str, Any], bowler: dict[str, Any]) -> tuple[str | None, str | None]:
        """Select at most one contextual batting and bowling proc per ball."""
        innings = self.current_innings
        recent = innings.batters[int(batter["id"])].outcomes[-6:]
        bat_choices = self.talents_for(batter)["triggered"]
        bowl_choices = self.talents_for(bowler)["triggered"]
        batting_proc = None
        bowling_proc = None
        for name in bat_choices:
            eligible = (name == "Accumulator" and recent.count(0) >= 2) or (name == "Power Hitter" and self.effective_batting_aggression >= 7)
            if eligible and self.rng.random() < .075:
                batting_proc = name; break
        for name in bowl_choices:
            eligible = (
                (name == "Swing" and (self.weather in {"Overcast", "Cloudy"} or innings.legal_balls < 60))
                or (name == "Yorker" and (self.required_rate >= 8 or self.effective_batting_aggression >= 7))
                or (name == "Slower Ball" and self.effective_batting_aggression >= 6)
                or (name == "Doosra" and self.pitch in {"Dry", "Dusty", "Worn"})
            )
            if eligible and self.rng.random() < .075:
                bowling_proc = name; break
        self.last_triggered_talent = bowling_proc or batting_proc
        return batting_proc, bowling_proc

    @property
    def current_innings(self) -> InningsState:
        return self.innings[self.current_innings_index]

    def other_team(self, team_id: int) -> int:
        return self.away_team_id if team_id == self.home_team_id else self.home_team_id

    def team_name(self, team_id: int) -> str:
        return str(self.teams[team_id].get("name", f"Team {team_id}"))

    def _start_innings(self, batting_id: int, bowling_id: int, target: int | None = None) -> None:
        # The interval is meaningful recovery, especially for all-rounders who
        # bowled before batting. Recovery never exceeds their match-day ceiling.
        self._recover_energy(amount=8.0)
        state = InningsState(
            number=len(self.innings) + 1,
            batting_team=batting_id,
            bowling_team=bowling_id,
            batting_name=self.team_name(batting_id),
            bowling_name=self.team_name(bowling_id),
            batting_order=self.lineups[batting_id],
            bowling_squad=self.lineups[bowling_id],
            target=target,
        )
        self.innings.append(state)
        self.current_innings_index = len(self.innings) - 1
        state.current_bowler_id = self.choose_bowler()
        self._comment(f"{state.batting_name} begin innings {state.number}.", "milestone")

    def _comment(self, text: str, kind: str = "normal") -> None:
        event = {"over": self.current_innings.overs, "text": text, "kind": kind}
        self.commentary.append(event)
        self.commentary = self.commentary[-300:]

    def _eligible_bowlers(self) -> list[dict[str, Any]]:
        innings = self.current_innings
        specialists = [p for p in innings.bowling_squad if _role(p) in {"Bowler", "All-Rounder"}]
        candidates = specialists or list(innings.bowling_squad)
        maximum = self.MAX_BOWLER_BALLS[self.format]
        if maximum is not None:
            candidates = [p for p in candidates if innings.bowlers[int(p["id"])].balls < maximum]
        return candidates

    def choose_bowler(self, critical: bool | None = None) -> int:
        """Choose an AI bowler using quality, fatigue, economy, and match phase."""
        innings = self.current_innings
        candidates = self._eligible_bowlers()
        if not candidates:
            candidates = list(innings.bowling_squad)
        if len(candidates) > 1:
            alternatives = [p for p in candidates if int(p["id"]) != innings.previous_bowler_id]
            candidates = alternatives or candidates
        remaining = (self.MAX_BALLS[self.format] or 9999) - innings.legal_balls
        critical = critical if critical is not None else remaining <= (30 if self.format == "T20" else 60)

        def score(player: dict[str, Any]) -> float:
            attrs = _attrs(player, "bowling")
            mental = _attrs(player, "mental")
            line = innings.bowlers[int(player["id"])]
            quality = .30 * attrs.get("accuracy", 50) + .25 * attrs.get("swing_or_spin", 50)
            quality += .20 * attrs.get("variation", 50) + .15 * attrs.get("pace", 50) + .10 * attrs.get("stamina", 50)
            quality += (float(player.get("form", 50)) - 50) * .12
            quality += (mental.get("experience", 50) - 50) * (.08 if critical else .03)
            quality += (mental.get("big_match", 50) - 50) * (.06 if critical else .01)
            fatigue = max(0, line.balls - 90) * (0.10 if self.format == "Test" else 0.03)
            fatigue += max(0.0, 55 - self.player_energy(int(player["id"]))) * .35
            economy_bonus = max(-15, 8 - line.economy) if line.balls else 2
            unused_death_bonus = 8 if critical and line.balls < 18 and quality >= 65 else 0
            striker = innings.striker_player
            bat = _attrs(striker, "batting")
            pace_bowler = attrs.get("pace", 50) >= 58
            weakness = 100 - bat.get("technique_vs_pace" if pace_bowler else "technique_vs_spin", 50)
            matchup = weakness * .10
            phase_bonus = 5 if critical and attrs.get("variation", 50) >= 65 else 0
            return quality + economy_bonus + unused_death_bonus + matchup + phase_bonus - fatigue + self.rng.random() * 4

        ranked = sorted(candidates, key=score, reverse=True)
        if len(ranked) > 1 and self.rng.random() < self.difficulty.ai_mistake_rate:
            ranked = ranked[max(1, len(ranked) // 2):]
        return int(ranked[0]["id"])

    def set_bowler(self, player_id: int) -> bool:
        """Apply a legal manual bowling change. Returns ``False`` if invalid."""
        innings = self.current_innings
        eligible = {int(p["id"]) for p in self._eligible_bowlers()}
        if player_id not in eligible or player_id == innings.previous_bowler_id:
            return False
        innings.current_bowler_id = player_id
        return True

    def set_field(self, preset: str | None = None) -> str:
        """Set a manual preset, or let the AI infer one from match state."""
        if preset in FIELD_PRESETS:
            self.field_setting = preset
            return preset
        innings = self.current_innings
        required = self.required_rate
        if innings.wickets >= 7 or (innings.target and required < 5):
            optimal = "Aggressive"
        elif required > 9 or innings.legal_balls >= int((self.MAX_BALLS[self.format] or 9999) * .75):
            optimal = "Defensive"
        else:
            optimal = "Neutral"
        if self.rng.random() < self.difficulty.ai_mistake_rate:
            optimal = self.rng.choice(sorted(FIELD_PRESETS - {optimal}))
        self.field_setting = optimal
        return self.field_setting

    def adjust_aggression(self) -> int:
        """Let the batting AI choose an aggression level from 1–10."""
        innings = self.current_innings
        if innings.target:
            required = self.required_rate
            optimal = max(2, min(10, round(required + 1.5)))
        elif self.format == "T20":
            optimal = 8 if innings.wickets < 6 else 6
        elif self.format == "ODI":
            phase = innings.legal_balls / 300
            optimal = 4 if phase < .25 else 6 if phase < .75 else 8
        else:
            optimal = 4 if innings.wickets < 5 else 3
        error_span = max(0, round((1 - self.difficulty.ai_aggression_accuracy) * 10))
        if error_span and self.rng.random() < self.difficulty.ai_mistake_rate * 1.6:
            optimal += self.rng.randint(-error_span, error_span)
        self.batting_aggression = max(1, min(10, optimal))
        self.effective_batting_aggression = self._situational_aggression(self.batting_aggression)
        return self.batting_aggression

    def _situational_aggression(self, order: int | None = None) -> int:
        """Interpret a manager's order as a guideline in the match context."""
        innings = self.current_innings
        value = float(self.batting_aggression if order is None else order)
        maximum = self.MAX_BALLS[self.format] or 540
        phase = innings.legal_balls / max(1, maximum)
        # Early clusters of wickets trigger a consolidation period, even for
        # players sent out with attacking orders.
        if innings.wickets >= 4 and phase < .45:
            value -= 2.2
        elif innings.wickets >= 3 and phase < .25:
            value -= 1.4
        # A platform and wickets in hand invite controlled acceleration.
        if innings.wickets <= 3 and phase >= (.55 if self.format != "Test" else .70):
            value += 1.5
        if innings.target and self.format != "Test":
            current_rate = innings.runs * 6 / max(6, innings.legal_balls)
            gap = self.required_rate - current_rate
            value += max(-1.5, min(3.0, gap * .55))
            if innings.wickets >= 7:
                value -= .8
        if self.format == "Test" and self.day >= 5:
            value += .8
        return max(1, min(10, round(value)))

    def ai_should_review(self, estimated_correctness: float) -> bool:
        """Let difficulty control how accurately AI teams judge DRS chances."""
        certainty = max(0.0, min(1.0, float(estimated_correctness)))
        noise = self.rng.uniform(-1, 1) * (1 - self.difficulty.ai_review_accuracy)
        return certainty + noise >= .58

    @property
    def required_rate(self) -> float:
        innings = self.current_innings
        if not innings.target or self.format == "Test":
            return 0.0
        balls_left = max(1, (self.rain_overs or (20 if self.format == "T20" else 50)) * 6 - innings.legal_balls)
        return max(0, innings.target - innings.runs) * 6 / balls_left

    @property
    def powerplay(self) -> bool:
        over = self.current_innings.legal_balls // 6 + 1
        if self.format == "T20":
            return over <= 6
        if self.format == "ODI":
            return over <= 10 or over >= 41
        return False

    def _ratings(self, batter: dict[str, Any], bowler: dict[str, Any]) -> tuple[float, float, float]:
        bat = _attrs(batter, "batting")
        bowl = _attrs(bowler, "bowling")
        mental = _attrs(batter, "mental")
        bowler_mental = _attrs(bowler, "mental")
        pace_bowler = bowl.get("pace", 50) >= 58
        technique = bat.get("technique_vs_pace" if pace_bowler else "technique_vs_spin", 50)
        batter_tactics=PlayerTactics.from_player(batter); bowler_tactics=PlayerTactics.from_player(bowler)
        self.effective_batting_aggression = self._situational_aggression(batter_tactics.batting_aggression)
        self.bowling_aggression = bowler_tactics.bowling_aggression
        attack_weight = .22 + self.effective_batting_aggression * .018
        batting = attack_weight * bat.get("attack", 50) + .24 * bat.get("defence", 50)
        batting += .20 * technique + .14 * bat.get("concentration", 50) + .10*bat.get("timing",50)+.06*bat.get("power",50)
        batting += .08 * mental.get("consistency", 50)+.02*mental.get("big_match",50)
        bowling = .25 * bowl.get("accuracy", 50) + .22 * bowl.get("variation", 50)
        bowling += .20 * bowl.get("swing_or_spin", 50) + .13 * bowl.get("pace", 50) + .10 * bowl.get("stamina", 50)
        bowling += .08*bowl.get("control",50)+.07*bowl.get("deception",50)
        if bowler_tactics.bowling_style in SPIN_STYLES: bowling += (bowl.get("swing_or_spin",50)-50)*.05
        elif bowler_tactics.bowling_style in {"Fast","Left-Arm Fast"}: bowling += (bowl.get("pace",50)-50)*.05
        innings = self.current_innings
        line = innings.bowlers[int(bowler["id"])]
        batter_line = innings.batters[int(batter["id"])]
        fatigue_start = 72 + max(25, bowl.get("stamina", 50)) * .30 if self.format == "Test" else 24 + max(25, bowl.get("stamina", 50)) * .18
        fatigue = max(0.0, line.balls - fatigue_start) / 7
        batting_fatigue = max(0.0, batter_line.balls - (80 + mental.get("fitness", 50) * 1.6)) / 18
        batter_energy = self.player_energy(int(batter["id"]))
        bowler_energy = self.player_energy(int(bowler["id"]))
        energy_bat_penalty = max(0.0, 55 - batter_energy) * .22
        energy_bowl_penalty = max(0.0, 55 - bowler_energy) * .25
        bowling -= fatigue + energy_bowl_penalty; batting -= batting_fatigue + energy_bat_penalty
        batting += (float(batter.get("form", 50)) - 50) * .14 + (mental.get("morale", 50) - 50) * .05
        bowling += (float(bowler.get("form", 50)) - 50) * .14 + (bowler_mental.get("morale", 50) - 50) * .05
        pressure = 0.0
        if innings.target:
            pressure = max(0.0, self.required_rate - (6.5 if self.format == "T20" else 5.2)) + innings.wickets * .25
            composure = mental.get("experience", 50) * .6 + mental.get("big_match", 50) * .4
            batting -= pressure * max(.15, (70 - composure) / 35)
        fielding_values = [
            _mean(_attrs(p, "fielding").values()) - max(0.0, 50 - self.player_energy(int(p["id"]))) * .18
            for p in innings.bowling_squad
        ]
        fielding = _mean(fielding_values)
        ball_age = innings.legal_balls / 6
        if self.pitch == "Green" and pace_bowler:
            bowling += 7
        elif self.pitch == "Dusty" and not pace_bowler:
            bowling += 8
        elif self.pitch == "Flat":
            batting += 7
        elif self.pitch == "Dry" and not pace_bowler:
            bowling += 4
        elif self.pitch == "Worn":
            bowling += 8 if not pace_bowler else 3; batting -= 4
        if self.format == "Test" and self.day >= 4:
            bowling += 4 if not pace_bowler else 1; batting -= 2
        if self.weather == "Overcast" and pace_bowler:
            bowling += 5
        elif self.weather == "Cloudy" and pace_bowler:
            bowling += 3
        elif self.weather == "Sunny":
            batting += 3
        if ball_age <= 10 and pace_bowler:
            bowling += 5
        elif 11 <= ball_age <= 35:
            batting += 2
        elif ball_age >= 40 and not pace_bowler:
            bowling += min(7, (ball_age - 40) * .15)
        elif ball_age >= 45 and pace_bowler and bowl.get("variation", 50) >= 65:
            bowling += 2.5
        self.last_factors = {"batting_rating": round(batting, 2), "bowling_rating": round(bowling, 2),
                             "fielding_rating": round(fielding, 2), "ball_age_overs": round(ball_age, 1),
                             "bowler_fatigue": round(fatigue, 2), "batter_fatigue": round(batting_fatigue, 2),
                             "batter_energy": batter_energy, "bowler_energy": bowler_energy,
                             "effective_aggression": self.effective_batting_aggression,
                             "pressure": round(pressure, 2), "powerplay": self.powerplay,
                             "pitch": self.pitch, "pitch_wear":round(self.pitch_wear,1), "weather": self.weather,
                             "batting_aggression":self.effective_batting_aggression,"bowling_aggression":self.bowling_aggression,
                             "bowling_style":bowler_tactics.bowling_style}
        return batting, bowling, fielding

    def _weights(self, batter: dict[str, Any], bowler: dict[str, Any]) -> dict[str, float]:
        batting, bowling, fielding = self._ratings(batter, bowler)
        advantage = max(-30, min(30, batting - bowling))
        aggression = self.effective_batting_aggression
        # Baseline sits inside the requested ranges; modifiers redistribute it.
        wicket = {"T20": 3.2, "ODI": 4.0, "Test": 5.2}[self.format]
        wicket += -advantage * .055 + max(0, aggression - 6) * .45
        wicket += 0.8 if self.field_setting == "Aggressive" else -0.4 if self.field_setting == "Defensive" else 0
        wicket += (self.bowling_aggression - 5) * .20
        dot = 28 - advantage * .18 - (aggression - 5) * 1.1 + (self.bowling_aggression - 5) * .45
        field_delta = fielding - 55
        one = 27 - field_delta * .018 - abs(aggression - 5) * .35
        two = 7 + advantage * .03 - field_delta * .025
        three = 1.5
        four = 9 + advantage * .12 + (aggression - 5) * .75 - field_delta * .035
        six = 2.5 + advantage * .055 + (aggression - 5) * .55
        extras = max(2.0, min(5.0, 4.5 - _attrs(bowler, "bowling").get("accuracy", 50) * .025))
        extras += max(0, self.bowling_aggression - 7) * .18
        recent = self.current_innings.batters[int(batter["id"])].outcomes[-6:]
        dot_pressure = sum(outcome == 0 for outcome in recent)
        if dot_pressure >= 3:
            wicket += (dot_pressure - 2) * .35; dot += .5; one -= .4
        if self.powerplay:
            four += 1.3; six += .5
        if self.current_innings.target and self.required_rate > 9:
            four += 1.5; six += 1.0; wicket += .8; dot -= 1.5
        # Format baselines reflect the very different tempo of the three games.
        # Tests contain substantially more leaves/blocks; ODI middle overs trade
        # boundaries for rotation; T20 retains the widest attacking range.
        if self.format == "T20":
            dot += 6; four -= 1.5; six -= .6
        elif self.format == "ODI":
            dot += 23; four -= 4; six -= 1.5; wicket -= 1
        else:
            dot += 50; one += 5; four -= 5; six -= 2; wicket -= 2
        dot += field_delta * .055
        # Low-energy bowlers lose their line; tired batters both score slower
        # and offer more chances.  This is intentionally nonlinear below 45.
        bowler_energy = self.player_energy(int(bowler["id"]))
        batter_energy = self.player_energy(int(batter["id"]))
        if bowler_energy < 50:
            extras += (50 - bowler_energy) * .055; four += (50 - bowler_energy) * .035; dot -= (50 - bowler_energy) * .05
        if batter_energy < 50:
            dot += (50 - batter_energy) * .08; wicket += (50 - batter_energy) * .055; four -= (50 - batter_energy) * .045
        batting_proc, bowling_proc = self._talent_proc(batter, bowler)
        if batting_proc == "Accumulator": one += 2.2; two += .8; dot -= 1.2
        elif batting_proc == "Power Hitter": four += 1.2; six += 1.5; wicket += .35
        if bowling_proc == "Swing": wicket += 1.25; dot += 1.0
        elif bowling_proc == "Yorker": wicket += 1.0; six -= .7
        elif bowling_proc == "Slower Ball": wicket += .75; dot += .8; four -= .5
        elif bowling_proc == "Doosra": wicket += 1.1; dot += .6
        dot_ceiling = {"T20": 42, "ODI": 52, "Test": 70}[self.format]
        return {
            "dot": max(20, min(dot_ceiling, dot)), "1": max(20, min(35, one)),
            "2": max(5, min(10, two)), "3": max(1, min(3, three)),
            "4": max(5, min(15, four)), "6": max(1, min(5, six)),
            "W": max(2, min(10, wicket)), "extra": extras,
        }

    def _fielding_attempt(self, batter: dict[str, Any], bowler: dict[str, Any]) -> dict[str, Any]:
        """Resolve the individual skill check behind a possible dismissal."""
        innings = self.current_innings
        bowl_attrs = _attrs(bowler, "bowling")
        pace_bowler = bowl_attrs.get("pace", 50) >= 58
        keeper = next((p for p in innings.bowling_squad if _role(p) == "Wicketkeeper"), None)
        keeper_skill = _mean(_attrs(keeper, "fielding").values()) if keeper else 45
        weights = [25.0, 40.0, 20.0, 9.0, 6.0]
        if pace_bowler:
            weights[0] += 4; weights[2] += 3; weights[4] = max(1, weights[4] - 3)
        else:
            weights[4] += max(0, (keeper_skill - 45) / 6); weights[1] += 2
        wicket_type = self.rng.choices(["bowled", "caught", "lbw", "run out", "stumped"], weights, k=1)[0]
        positions = ["slip", "gully", "point", "cover", "mid-off", "mid-on", "midwicket", "fine leg", "long-on", "deep square"]
        position = self.rng.choice(positions)
        candidates = [p for p in innings.bowling_squad if int(p["id"]) != int(bowler["id"])] or list(innings.bowling_squad)
        fielder = keeper if wicket_type == "stumped" and keeper else self.rng.choice(candidates)
        attrs = _attrs(fielder, "fielding") if fielder else {}
        energy = self.player_energy(int(fielder["id"])) if fielder else 50
        passive = self.talents_for(fielder)["passive"] if fielder else []
        triggered = self.talents_for(fielder)["triggered"] if fielder else []
        proc = None
        if wicket_type in {"bowled", "lbw"}:
            success = True
        elif wicket_type == "caught":
            chance = .47 + attrs.get("catching", 50) * .0043 + attrs.get("reflexes", 50) * .0012
            chance += (energy - 55) * .0022 + (.055 if "Safe Hands" in passive else 0)
            if "Reflex Catch" in triggered and self.rng.random() < .09:
                chance += .16; proc = "Reflex Catch"
            success = self.rng.random() < max(.48, min(.96, chance))
        elif wicket_type == "run out":
            chance = .30 + attrs.get("throwing", 50) * .0048 + attrs.get("reflexes", 50) * .0015
            chance += (energy - 55) * .002
            if "Rocket Arm" in triggered and self.rng.random() < .09:
                chance += .18; proc = "Rocket Arm"
            success = self.rng.random() < max(.35, min(.91, chance))
        else:
            chance = .40 + attrs.get("reflexes", 50) * .0047 + attrs.get("catching", 50) * .0015
            chance += (energy - 55) * .002
            success = self.rng.random() < max(.42, min(.94, chance))
        return {"success": success, "type": wicket_type, "position": position,
                "fielder": fielder, "proc": proc}

    def _delivery_energy_costs(self, batter: dict[str, Any], bowler: dict[str, Any], legal: bool, runs: int) -> None:
        """Apply role-specific exertion after a delivery."""
        innings = self.current_innings
        if legal:
            self._spend_energy(int(batter["id"]), .10 + self.effective_batting_aggression * .012 + max(0, runs) * .015)
            self._spend_energy(int(bowler["id"]), .38 + self.bowling_aggression * .022)
            for player in innings.bowling_squad:
                self._spend_energy(int(player["id"]), .012)
            keeper = next((p for p in innings.bowling_squad if _role(p) == "Wicketkeeper"), None)
            if keeper: self._spend_energy(int(keeper["id"]), .035)
            self._spend_energy(self.captains[innings.bowling_team], .012)
            self._spend_energy(self.captains[innings.batting_team], .004)
        else:
            self._spend_energy(int(bowler["id"]), .18)

    def _is_drinks_break(self, legal_balls: int) -> bool:
        if legal_balls <= 0 or legal_balls % 6: return False
        over = legal_balls // 6
        if self.format == "T20": return over == 10
        if self.format == "ODI": return over in {15, 30, 40}
        return over % 30 == 0

    def ball_outcome(self) -> dict[str, Any]:
        """Simulate and apply one delivery, returning a UI-friendly event."""
        if self.completed:
            return self.event_pool.acquire(result="END", legal=False, commentary=self.result, match_complete=True)
        innings = self.current_innings
        if innings.completed:
            self._advance_innings()
            if self.completed:
                return self.event_pool.acquire(result="END", legal=False, commentary=self.result, match_complete=True)
            innings = self.current_innings
        if innings.legal_balls % 6 == 0:
            # The next bowler is selected at the previous over's end (or when
            # the innings is created). Do not choose again here: doing so used
            # to silently overwrite a manager's manual bowling change.
            if innings.current_bowler_id is None:
                innings.current_bowler_id = self.choose_bowler()
            self._update_conditions()
        batter = innings.striker_player
        bowler = next(p for p in innings.bowling_squad if int(p["id"]) == innings.current_bowler_id)
        batting_line = innings.batters[int(batter["id"])]
        bowling_line = innings.bowlers[int(bowler["id"])]
        # A rollback snapshot is only required for a reviewable dismissal.
        # Copying an entire innings before every ordinary delivery dominated
        # instant-simulation time and created avoidable short-lived objects.
        self._pre_ball_state = None
        self.pending_review = None
        weights = self._weights(batter, bowler)
        labels, chances = zip(*weights.items())
        selected = self.rng.choices(labels, weights=chances, k=1)[0]
        line = PlayerTactics.from_player(bowler).preferred_line
        length = PlayerTactics.from_player(bowler).preferred_length
        bowl_x=max(0.03,min(.97,self.rng.gauss({"Leg Stump":.38,"Middle":.5,"Off Stump":.62,"Wide":.78}.get(line,.62),.11)))
        bowl_y=max(0.03,min(.97,self.rng.gauss({"Yorker":.83,"Full":.68,"Good":.5,"Short":.28}.get(length,.5),.12)))
        legal = True
        runs = 0
        kind = "normal"
        wicket_type = None
        fielder = None
        fielder_player = None
        missed_chance = None
        wicket_attempt = None

        # A weighted wicket event still needs an individual execution check.
        if selected == "W":
            wicket_attempt = self._fielding_attempt(batter, bowler)
            if not wicket_attempt["success"]:
                wicket_type = str(wicket_attempt["type"])
                fielder_player = wicket_attempt["fielder"]
                fielder_name = fielder_player["name"] if fielder_player else "the fielder"
                if wicket_type == "caught": missed_chance = f"Dropped by {fielder_name}!"
                elif wicket_type == "stumped": missed_chance = f"{fielder_name} misses the stumping chance."
                else: missed_chance = f"{fielder_name} cannot complete the run-out."
                log = self.chance_log.setdefault(int(batter["id"]),
                                                 {"dropped": 0, "missed_stumping": 0, "missed_runout": 0})
                log["dropped" if wicket_type == "caught" else
                    "missed_stumping" if wicket_type == "stumped" else "missed_runout"] += 1
                selected = "1" if wicket_type in {"caught", "run out"} else "dot"

        if selected == "extra":
            legal = False
            selected = "Wd" if self.rng.random() < .72 else "Nb"
            innings.runs += 1; bowling_line.runs += 1; bowling_line.current_over_runs += 1
            key = "w" if selected == "Wd" else "nb"
            innings.extras[key] += 1
            if selected == "Nb" and self.rng.random() < .18:
                extra_runs = self.rng.choice([1, 2, 4, 6])
                innings.runs += extra_runs; batting_line.runs += extra_runs
                bowling_line.runs += extra_runs; bowling_line.current_over_runs += extra_runs
                runs = extra_runs + 1
            commentary = f"{bowler['name']} sends down a {'wide' if selected == 'Wd' else 'no-ball'}."
        elif selected == "W":
            self._pre_ball_state = deepcopy(innings)
            wicket_type = str(wicket_attempt["type"] if wicket_attempt else "bowled")
            fielder_player = wicket_attempt["fielder"] if wicket_attempt else None
            fielder = wicket_attempt["position"] if wicket_attempt else None
            legal = True; batting_line.balls += 1; batting_line.outcomes.append("W")
            innings.legal_balls += 1; innings.partnership_balls += 1; bowling_line.balls += 1
            innings.wickets += 1; kind = "wicket"
            innings.fall_of_wickets.append({"wicket": innings.wickets, "score": innings.runs,
                                             "player": batter["name"], "over": innings.overs})
            if wicket_type == "caught":
                catcher = fielder_player["name"] if fielder_player else str(fielder)
                batting_line.dismissal = f"c {catcher} b {bowler['name']}"
            elif wicket_type == "bowled": batting_line.dismissal = f"b {bowler['name']}"
            elif wicket_type == "lbw": batting_line.dismissal = f"lbw b {bowler['name']}"
            elif wicket_type == "stumped": batting_line.dismissal = f"stumped b {bowler['name']}"
            else: batting_line.dismissal = "run out"
            batting_line.not_out = False
            if wicket_type != "run out": bowling_line.wickets += 1
            reviewable = wicket_type in {"lbw", "caught"}
            umpire_correct = self.rng.random() >= .12 if reviewable else True
            if reviewable:
                self.pending_review = {"team_id": innings.batting_team, "correct": umpire_correct, "wicket_type": wicket_type}
            commentary = self._wicket_commentary(batter, bowler, wicket_type, fielder)
            innings.partnerships.append({"a": batter["name"], "b": innings.non_striker_player["name"],
                                         "runs": innings.partnership_runs, "balls": innings.partnership_balls})
            innings.partnership_runs = innings.partnership_balls = 0
            if innings.next_batter < len(innings.batting_order):
                innings.striker = innings.next_batter; innings.next_batter += 1
                innings.batters[int(innings.striker_player["id"])].dismissal = "not out"
        else:
            runs = 0 if selected == "dot" else int(selected)
            batting_line.runs += runs; batting_line.balls += 1
            batting_line.fours += int(runs == 4); batting_line.sixes += int(runs == 6)
            batting_line.outcomes.append(runs)
            innings.runs += runs; innings.partnership_runs += runs; innings.partnership_balls += 1
            innings.legal_balls += 1; bowling_line.balls += 1; bowling_line.runs += runs; bowling_line.current_over_runs += runs
            if runs % 2:
                innings.striker, innings.non_striker = innings.non_striker, innings.striker
            kind = "run" if runs >= 4 else "normal"
            commentary = self._run_commentary(batter, runs)
            if missed_chance:
                commentary = f"{missed_chance} {commentary}"
            selected = "•" if selected == "dot" else selected

        talent = (wicket_attempt or {}).get("proc") or self.last_triggered_talent
        if talent:
            commentary = f"[{talent}] {commentary}"
        self._delivery_energy_costs(batter, bowler, legal, runs)
        angle=self.rng.uniform(-3.14159,3.14159); distance={0:.12,1:.32,2:.55,3:.72,4:.92,6:1.0}.get(runs,.15)
        innings_number = self.current_innings_index + 1
        shot={"player_id":int(batter["id"]),"innings":innings_number,"angle":angle,"distance":distance,"runs":runs,"wicket":bool(wicket_type)}
        delivery={"player_id":int(bowler["id"]),"innings":innings_number,"x":bowl_x,"y":bowl_y,"wicket":bool(wicket_type),"runs":runs}
        self.shot_events.append(shot); self.bowling_events.append(delivery)
        injury = self._maybe_injury(batter, bowler, bowling_line)
        if legal and innings.legal_balls % 6 == 0:
            if bowling_line.current_over_runs == 0: bowling_line.maidens += 1
            bowling_line.current_over_runs = 0
            innings.striker, innings.non_striker = innings.non_striker, innings.striker
            innings.previous_bowler_id = innings.current_bowler_id
            innings.current_bowler_id = self.choose_bowler()
            if self._is_drinks_break(innings.legal_balls):
                self._recover_energy(amount=4.5)
                self._comment("Drinks break: both sides recover some energy.", "milestone")
        if legal:
            self._update_match_clock()
        self.last_six.append(selected); self.last_six = self.last_six[-6:]
        self._comment(commentary, kind)
        event = self.event_pool.acquire(
            result=selected, runs=runs, legal=legal, wicket=wicket_type,
            fielder=fielder, commentary=commentary, kind=kind,
            over=innings.overs, reviewable=self.pending_review is not None,
            innings_complete=False, match_complete=False, factors=dict(self.last_factors), injury=injury,
            shot=shot, delivery=delivery, weather=self.weather, pitch=self.pitch, pitch_wear=round(self.pitch_wear,1),
            chance=(str(wicket_attempt["type"]) if missed_chance else None),
        )
        reason = self.innings_complete()
        if reason:
            innings.completed = True; innings.end_reason = reason
            event["innings_complete"] = True
            self._comment(f"Innings complete: {innings.batting_name} {innings.runs}/{innings.wickets} ({innings.overs}).", "milestone")
            self._advance_innings()
            event["match_complete"] = self.completed
        return event

    def _update_match_clock(self) -> None:
        """Advance Test day/session markers from aggregate legal deliveries."""
        if self.format != "Test": return
        match_balls = sum(state.legal_balls for state in self.innings)
        self.day = min(5, match_balls // 540 + 1)
        self.session = min(3, (match_balls % 540) // 180 + 1)

    def _maybe_injury(self, batter: dict[str, Any], bowler: dict[str, Any], line: BowlerLine) -> dict[str, Any] | None:
        """Generate a rare, fitness-driven injury under sustained workload."""
        for player, workload in ((batter, 0), (bowler, max(0, line.balls - 72))):
            physical = _attrs(player, "physical")
            fitness = physical.get("fitness", _attrs(player, "mental").get("fitness", 50))
            endurance = physical.get("endurance", _attrs(player, "mental").get("endurance", fitness))
            team_id = next((team_id for team_id, squad in self.lineups.items()
                            if any(int(member["id"]) == int(player["id"]) for member in squad)), self.home_team_id)
            medical_level = float(self.teams[team_id].get("medical_level", 1))
            chance = .00004 + max(0, 55 - fitness) * .000004 + workload * .0000008
            chance += max(0, 50 - endurance) * .000002
            chance *= max(.55, 1 - (medical_level - 1) * .11)
            if self.rng.random() < chance:
                severity = self.rng.choices(["Minor", "Moderate", "Major"], [72, 23, 5], k=1)[0]
                days = {"Minor": 7, "Moderate": 14, "Major": 35}[severity]
                record = {"player_id": int(player["id"]), "player": player["name"], "severity": severity, "days": days}
                self.injuries.append(record)
                return record
        return None

    def _run_commentary(self, batter: dict[str, Any], runs: int) -> str:
        if runs == 0: return f"{batter['name']} defends; no run."
        if runs == 1: return f"{batter['name']} works it into space for one."
        if runs == 2: return f"{batter['name']} finds the gap and they come back for two."
        if runs == 3: return f"Excellent running from {batter['name']}; three completed."
        if runs == 4: return f"FOUR! {batter['name']} drives crisply through cover."
        return f"SIX! {batter['name']} launches it cleanly over the rope."

    @staticmethod
    def _wicket_commentary(batter: dict[str, Any], bowler: dict[str, Any], wicket_type: str, fielder: str | None) -> str:
        if wicket_type == "bowled": return f"BOWLED! {bowler['name']} uproots {batter['name']}'s middle stump."
        if wicket_type == "caught": return f"OUT! {batter['name']} is caught at {fielder} off {bowler['name']}."
        if wicket_type == "lbw": return f"LBW! {batter['name']} is trapped in front by {bowler['name']}."
        if wicket_type == "stumped": return f"STUMPED! {batter['name']} is beaten in flight."
        return f"RUN OUT! Sharp fielding ends {batter['name']}'s innings."

    def innings_complete(self) -> str | None:
        innings = self.current_innings
        if innings.wickets >= 10: return "all out"
        if innings.target and innings.runs >= innings.target: return "target reached"
        if self.format != "Test":
            max_balls = (self.rain_overs * 6 if self.rain_overs else self.MAX_BALLS[self.format]) or 0
            if innings.legal_balls >= max_balls: return "overs complete"
        if innings.declared: return "declared"
        return None

    def declare(self) -> bool:
        if self.format != "Test" or self.current_innings.completed:
            return False
        self.current_innings.declared = True
        self.current_innings.completed = True
        self.current_innings.end_reason = "declared"
        self._advance_innings()
        return True

    def should_declare(self) -> bool:
        """AI declaration decision using lead, time, weather, and workload."""
        if self.format != "Test" or self.current_innings.completed:
            return False
        innings = self.current_innings
        if innings.number == 1:
            weather_urgency = 35 if self.weather == "Rain Threat" else 0
            return innings.runs >= 390 - weather_urgency and innings.legal_balls >= 480
        totals = self.team_totals
        lead = totals[innings.batting_team] - totals[innings.bowling_team]
        time_pressure = self.day * 3 + self.session
        desired_lead = 300 if time_pressure <= 9 else 240 if time_pressure <= 12 else 180
        if self.weather == "Rain Threat": desired_lead -= 35
        bowler_workload = max((line.balls for line in innings.bowlers.values()), default=0)
        return lead >= desired_lead and (innings.wickets >= 5 or innings.legal_balls >= 360 or bowler_workload >= 120)

    def _advance_innings(self) -> None:
        if self.completed: return
        finished = self.current_innings
        if self.format != "Test":
            if len(self.innings) == 1:
                target = self.dls_target(finished.runs) if self.rain_overs else finished.runs + 1
                self._start_innings(finished.bowling_team, finished.batting_team, target)
            else:
                self._finish_limited_match()
            return
        if len(self.innings) == 1:
            self._start_innings(finished.bowling_team, finished.batting_team)
        elif len(self.innings) == 2:
            first, second = self.innings[0], self.innings[1]
            lead = first.runs - second.runs
            if lead >= 200 and self.should_enforce_follow_on(lead):
                # The leading side enforces the follow-on.
                self.innings_order = [first.batting_team, second.batting_team, second.batting_team, first.batting_team]
                self._start_innings(second.batting_team, first.batting_team)
            else:
                self._start_innings(first.batting_team, second.batting_team)
        elif len(self.innings) == 3:
            totals = self.team_totals
            next_team = self.other_team(finished.batting_team)
            if totals[finished.batting_team] < totals[next_team] and finished.batting_team == self.innings[1].batting_team:
                self._finish_test_match()  # innings defeat after a failed follow-on
            else:
                target = totals[finished.batting_team] - totals[next_team] + 1
                self._start_innings(next_team, finished.batting_team, max(1, target))
        else:
            self._finish_test_match()

    def should_enforce_follow_on(self, lead: int) -> bool:
        """AI follow-on choice; preserve time unless fatigue makes batting safer."""
        if lead < 200: return False
        bowling_load = sum(line.balls for line in self.current_innings.bowlers.values())
        average_load = bowling_load / max(1, len(self.current_innings.bowlers))
        if self.day >= 5: return True
        if lead >= 260: return True
        return average_load < 72 or self.day <= 3

    @property
    def team_totals(self) -> dict[int, int]:
        totals = {self.home_team_id: 0, self.away_team_id: 0}
        for innings in self.innings: totals[innings.batting_team] += innings.runs
        return totals

    def _finish_limited_match(self) -> None:
        first, second = self.innings[0], self.innings[1]
        if second.runs > first.runs:
            self.winner_id = second.batting_team
            wickets = 10 - second.wickets
            self.result = f"{second.batting_name} won by {wickets} wickets"
        elif first.runs > second.runs:
            self.winner_id = first.batting_team
            margin = first.runs - second.runs
            self.result = f"{first.batting_name} won by {margin} run{'s' if margin != 1 else ''}"
        elif self.knockout:
            self._run_super_over()
        else:
            self.result = "Match tied"
        self.completed = True

    def _run_super_over(self) -> None:
        self.is_super_over = True
        for team_id in (self.innings[0].batting_team, self.innings[1].batting_team):
            batting = sorted(self.lineups[team_id], key=lambda p: _mean(_attrs(p, "batting").values()), reverse=True)[:2]
            bowling_team = self.other_team(team_id)
            bowler = max(self.lineups[bowling_team], key=lambda p: _mean(_attrs(p, "bowling").values()))
            quality = _mean(_attrs(batting[0], "batting").values()) - _mean(_attrs(bowler, "bowling").values())
            score = max(0, round(self.rng.gauss(10 + quality * .08, 4)))
            self.super_over_scores[team_id] = score
        a, b = self.super_over_scores
        if self.super_over_scores[a] == self.super_over_scores[b]:
            # Repeat using a one-ball sudden death abstraction; it always resolves.
            self.super_over_scores[self.rng.choice([a, b])] += 1
        self.winner_id = max(self.super_over_scores, key=self.super_over_scores.get)
        self.result = f"{self.team_name(self.winner_id)} won the Super Over"

    def _finish_test_match(self) -> None:
        totals = self.team_totals
        a, b = self.home_team_id, self.away_team_id
        if totals[a] == totals[b]:
            self.result = "Test match drawn"
        else:
            self.winner_id = a if totals[a] > totals[b] else b
            loser = self.other_team(self.winner_id)
            winner_innings = sum(i.batting_team == self.winner_id for i in self.innings)
            loser_innings = sum(i.batting_team == loser for i in self.innings)
            margin = totals[self.winner_id] - totals[loser]
            if winner_innings < loser_innings:
                self.result = f"{self.team_name(self.winner_id)} won by an innings and {margin} runs"
            elif self.current_innings.batting_team == self.winner_id and self.current_innings.target:
                self.result = f"{self.team_name(self.winner_id)} won by {10 - self.current_innings.wickets} wickets"
            else:
                self.result = f"{self.team_name(self.winner_id)} won by {margin} run{'s' if margin != 1 else ''}"
        self.completed = True

    def dls_target(self, first_innings_score: int) -> int:
        """Return a DLS-style resource-adjusted target for reduced overs.

        The commercial DLS tables are proprietary. This uses the published
        resource-percentage principle with a smooth exponential approximation,
        producing realistic and deterministic targets without embedding tables.
        """
        original = 20 if self.format == "T20" else 50
        available = max(5, min(original, self.rain_overs or original))
        resource = (1 - pow(2.718281828, -available / (original * .38)))
        full_resource = (1 - pow(2.718281828, -1 / .38))
        wickets_lost = self.current_innings.wickets if len(self.innings) >= 2 else 0
        wicket_adjustment = 1 + wickets_lost * .018
        return max(1, round(first_innings_score * resource / full_resource * wicket_adjustment) + 1)

    def apply_rain_reduction(self, overs_available: int) -> int:
        if self.format == "Test":
            raise ValueError("DLS only applies to limited-overs matches")
        maximum = 20 if self.format == "T20" else 50
        self.rain_overs = max(5, min(maximum, int(overs_available)))
        if len(self.innings) >= 2:
            self.current_innings.target = self.dls_target(self.innings[0].runs)
        return self.current_innings.target or self.dls_target(self.current_innings.runs)

    def review_last_decision(self, team_id: int) -> dict[str, Any]:
        """Review the latest caught/LBW dismissal and restore state if wrong."""
        pending = self.pending_review
        if not pending or pending["team_id"] != team_id:
            return {"available": False, "message": "No reviewable decision."}
        if self.reviews.get(team_id, 0) <= 0:
            return {"available": False, "message": "No reviews remaining."}
        overturned = not pending["correct"]
        if overturned and self._pre_ball_state is not None:
            self.innings[self.current_innings_index] = self._pre_ball_state
            self.last_six = self.last_six[:-1]
            message = "Decision overturned — NOT OUT."
        else:
            self.reviews[team_id] -= 1
            message = "Decision upheld — OUT."
        self.pending_review = None
        self._comment(f"DRS: {message}", "milestone")
        return {"available": True, "overturned": overturned, "message": message, "remaining": self.reviews[team_id]}

    def scorecard(self, innings_index: int | None = None) -> dict[str, Any]:
        state = self.innings[self.current_innings_index if innings_index is None else innings_index]
        batting = []
        for player in state.batting_order:
            line = state.batters[int(player["id"])]
            item = asdict(line)
            item["strike_rate"] = line.runs * 100 / line.balls if line.balls else 0.0
            batting.append(item)
        bowling = []
        for player in state.bowling_squad:
            line = state.bowlers[int(player["id"])]
            if line.balls or line.runs or line.wickets:
                item = asdict(line); item["overs"] = overs_text(line.balls); item["economy"] = line.economy
                bowling.append(item)
        return {"team": state.batting_name, "runs": state.runs, "wickets": state.wickets,
                "overs": state.overs, "extras": dict(state.extras), "batting": batting,
                "bowling": bowling, "target": state.target, "end_reason": state.end_reason,
                "partnerships": list(state.partnerships), "fall_of_wickets": list(state.fall_of_wickets)}

    def match_status(self) -> str:
        if self.completed: return self.result
        innings = self.current_innings
        if innings.target:
            needed = max(0, innings.target - innings.runs)
            balls = max(0, ((self.rain_overs or (20 if self.format == "T20" else 50)) * 6) - innings.legal_balls) if self.format != "Test" else 0
            suffix = f" from {balls} balls" if self.format != "Test" else ""
            return f"{innings.batting_name} need {needed} runs{suffix}"
        if self.format == "Test" and len(self.innings) > 1:
            totals = self.team_totals; lead_team = max(totals, key=totals.get); lead = abs(totals[self.home_team_id] - totals[self.away_team_id])
            return f"{self.team_name(lead_team)} lead by {lead} runs" if lead else "Scores level"
        return f"{innings.batting_name} {innings.runs}/{innings.wickets} after {innings.overs} overs"

    def win_probability(self, team_id: int) -> int:
        """Return a cached Monte Carlo win estimate for the requested team."""
        if self.completed: return 100 if self.winner_id == team_id else 0
        innings = self.current_innings
        key = (innings.number, innings.legal_balls, innings.runs, innings.wickets)
        if key not in self._prediction_cache:
            self._prediction_cache = {key: self.monte_carlo_win_probability(innings.batting_team, 240)}
        batting_probability = self._prediction_cache[key]
        return batting_probability if team_id == innings.batting_team else 100 - batting_probability

    def projected_score(self) -> int:
        """Immediate, resource-aware innings projection used by the live HUD."""
        innings = self.current_innings
        maximum = (self.rain_overs or (20 if self.format == "T20" else 50)) * 6 if self.format != "Test" else max(innings.legal_balls, 540)
        rate = innings.runs * 6 / max(12, innings.legal_balls)
        wicket_factor = max(.62, 1 - innings.wickets * .035)
        phase_boost = 1.0 + max(0, 10 - innings.wickets) * (.012 if self.format != "Test" else .002)
        return max(innings.runs, round(innings.runs + (maximum - innings.legal_balls) / 6 * rate * wicket_factor * phase_boost))

    def monte_carlo_win_probability(self, team_id: int, simulations: int = 500) -> int:
        """Estimate win probability without mutating the live match.

        The remainder of a limited-overs innings is sampled ball by ball from
        the same conditional distribution as the live engine. Test estimates
        model remaining time, wickets and aggregate lead. A stable state seed
        prevents the predictor jumping while the match is paused.
        """
        if self.completed: return 100 if self.winner_id == team_id else 0
        simulations = max(50, min(5000, int(simulations)))
        innings = self.current_innings
        state_seed = (innings.number * 1_000_003 + innings.legal_balls * 10_007 + innings.runs * 101 + innings.wickets * 17)
        rng = random.Random(state_seed)
        wins = ties = 0
        if self.format == "Test":
            totals = self.team_totals
            lead = totals[team_id] - totals[self.other_team(team_id)]
            balls_left = max(0, 2700 - sum(i.legal_balls for i in self.innings))
            wicket_resource = max(1, 10 - innings.wickets)
            for _ in range(simulations):
                swing = rng.gauss(lead, 55 + balls_left / 22)
                decisive = min(1.0, balls_left / 720) * min(1.0, wicket_resource / 6)
                if rng.random() > decisive:
                    ties += 1
                elif swing > 0: wins += 1
            return max(1, min(99, round((wins + ties * .5) * 100 / simulations)))

        maximum = (self.rain_overs or (20 if self.format == "T20" else 50)) * 6
        batter = innings.striker_player
        bowler = next(p for p in innings.bowling_squad if int(p["id"]) == innings.current_bowler_id)
        weights = self._weights(batter, bowler)
        labels = list(weights)
        chances = list(weights.values())
        for _ in range(simulations):
            score, wickets, balls = innings.runs, innings.wickets, innings.legal_balls
            while balls < maximum and wickets < 10:
                outcome = rng.choices(labels, weights=chances, k=1)[0]
                if outcome == "extra": score += 1; continue
                balls += 1
                if outcome == "W": wickets += 1
                elif outcome != "dot": score += int(outcome)
                if innings.target and score >= innings.target: break
            if innings.target:
                batting_won = score >= innings.target
            else:
                # First-innings prediction: compare the sampled total with an
                # opponent chase drawn from relative squad strength and format.
                batting_quality = _mean(float(p.get("overall", 50)) for p in self.lineups[innings.batting_team])
                opposition_quality = _mean(float(p.get("overall", 50)) for p in self.lineups[innings.bowling_team])
                baseline = (155 if self.format == "T20" else 255) + (opposition_quality - batting_quality) * 1.1
                opposing_score = rng.gauss(baseline, 25 if self.format == "T20" else 42)
                batting_won = score > opposing_score
                if abs(score - opposing_score) < .5: ties += 1
            winner = innings.batting_team if batting_won else innings.bowling_team
            wins += int(winner == team_id)
        return max(1, min(99, round((wins + ties * .5) * 100 / simulations)))

    def performance_updates(self) -> dict[int, dict[str, float]]:
        """Return bounded post-match form and development deltas for persistence."""
        updates: dict[int, dict[str, float]] = {}
        for innings in self.innings:
            for player in innings.batting_order:
                line = innings.batters[int(player["id"])]
                batting_score = line.runs + line.runs * 100 / max(1, line.balls) * .12
                form_delta = max(-5.0, min(5.0, (batting_score - 38) / 14))
                potential = float(player.get("potential", player.get("overall", 50)))
                overall = float(player.get("overall", 50)); age = int(player.get("age", 27))
                development = min(.5, max(0.0, potential - overall) * .012) if age <= 30 else 0.0
                decline = min(.5, max(0, age - 34) * .08)
                updates[int(player["id"])] = {"form": round(form_delta, 2), "overall": round(development - decline, 2)}
            for player in innings.bowling_squad:
                line = innings.bowlers[int(player["id"])]
                if not line.balls: continue
                bowling_delta = max(-5.0, min(5.0, line.wickets * 1.4 + (6.5 - line.economy) * .45 - 1.0))
                record = updates.setdefault(int(player["id"]), {"form": 0.0, "overall": 0.0})
                record["form"] = round(max(-5.0, min(5.0, record["form"] + bowling_delta)), 2)
        return updates

    def simulate(self, max_deliveries: int = 8000) -> str:
        """Auto-play to completion, declaring long Test innings sensibly."""
        deliveries = 0
        while not self.completed and deliveries < max_deliveries:
            innings = self.current_innings
            self.adjust_aggression(); self.set_field()
            event = self.ball_outcome(); deliveries += 1
            self.event_pool.release(event)
            if self.format == "Test" and not self.completed and not self.current_innings.completed:
                current = self.current_innings
                if self.should_declare() or current.legal_balls >= 720:
                    self.declare()
        if not self.completed:
            self.result = "Match drawn (time expired)" if self.format == "Test" else "Match abandoned"
            self.completed = True
        return self.result

    def to_dict(self) -> dict[str, Any]:
        """Create a JSON-safe match result/save snapshot."""
        return {
            "format": self.format, "pitch": self.pitch, "weather": self.weather,
            "home_team": self.home_team_id, "away_team": self.away_team_id,
            "completed": self.completed, "winner_id": self.winner_id, "result": self.result,
            "day": self.day, "session": self.session, "status": self.match_status(),
            "innings": [self.scorecard(i) for i in range(len(self.innings))],
            "super_over": dict(self.super_over_scores), "commentary": list(self.commentary),
            "injuries": list(self.injuries), "performance_updates": self.performance_updates(),
            "energy": {str(pid): round(value, 1) for pid, value in self.energy.items()},
        }


def create_match(*args: Any, **kwargs: Any) -> Match:
    """Stable public factory retained for UI and future Steam/Workshop clients."""
    return Match(*args, **kwargs)


def _demo_player(player_id: int, role: str, rating: int) -> dict[str, Any]:
    return {
        "id": player_id, "name": f"Player {player_id}", "role": role, "overall": rating,
        "batting": {"attack": rating, "defence": rating, "technique_vs_pace": rating,
                    "technique_vs_spin": rating, "concentration": rating},
        "bowling": {"pace": rating, "accuracy": rating, "variation": rating,
                    "stamina": rating, "swing_or_spin": rating},
        "fielding": {"catching": rating, "throwing": rating, "reflexes": rating},
        "mental": {"experience": rating, "consistency": rating, "big_match": rating,
                   "fitness": rating, "morale": rating},
    }


if __name__ == "__main__":
    # Dependency-free smoke test for non-coders: ``python match_engine.py``.
    home = {"id": 1, "name": "Manchester Mavericks"}
    away = {"id": 2, "name": "Mumbai Tigers"}
    first = [_demo_player(i, "Bowler" if i >= 7 else "Batsman", 68) for i in range(1, 12)]
    second = [_demo_player(i, "Bowler" if i >= 18 else "Batsman", 67) for i in range(12, 23)]
    for format_name in ("T20", "ODI", "Test"):
        match = Match(home, away, first, second, format_name, seed=42, batting_first_id=1)
        print(format_name, "—", match.simulate())
        for index in range(len(match.innings)):
            card = match.scorecard(index)
            print(f"  {card['team']}: {card['runs']}/{card['wickets']} ({card['overs']})")
