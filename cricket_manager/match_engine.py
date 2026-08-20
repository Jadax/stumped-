"""Deterministic, data-driven cricket match simulation.

The rendering layer deliberately knows nothing about probability or cricket
laws.  It asks :class:`Match` for one delivery at a time and receives a small
serialisable event dictionary.  This makes the same engine suitable for the
live screen, instant simulation, AI fixtures, save games, and unit tests.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import json
import random
from typing import Any, Iterable

from src.models.player_development import post_match_delta
from src.models.difficulty import DifficultyManager
from src.models.player import PlayerTactics, SPIN_STYLES


FORMATS = {"T10", "T20", "ODI", "Hundred", "Test"}
PITCHES = {"Green", "Dry", "Dusty", "Flat", "Worn"}
WEATHER = {"Sunny", "Overcast", "Rain Threat", "Cloudy"}
FIELD_PRESETS = {"Aggressive", "Neutral", "Defensive"}

# Real per-fielder field positions (v4.13.0) — angle in degrees (0-360,
# clockwise, same convention as godot_client/scripts/ground_view.gd's
# static ground diagram so both speak the same coordinate space with no
# lossy conversion layer) and radius 0.0-1.0 of the boundary. Previously
# FIELD_PRESETS only nudged one flat aggregate weight in _weights(); these
# layouts are the real thing a field_layout_by_team entry is built from,
# and what the drag editor mutates via set_field_layout().
FIELD_POSITIONS = ["WK", "Slip", "Gully", "Point", "Cover", "Mid-off", "Mid-on",
                   "Midwicket", "Square Leg", "Fine Leg", "Third Man"]

FIELD_LAYOUT_PRESETS: dict[str, dict[str, dict[str, float]]] = {
    "Neutral": {
        "WK": {"angle": 180.0, "radius": 0.16}, "Slip": {"angle": 160.0, "radius": 0.22},
        "Gully": {"angle": 135.0, "radius": 0.30}, "Point": {"angle": 95.0, "radius": 0.55},
        "Cover": {"angle": 55.0, "radius": 0.65}, "Mid-off": {"angle": 22.0, "radius": 0.45},
        "Mid-on": {"angle": 338.0, "radius": 0.45}, "Midwicket": {"angle": 305.0, "radius": 0.65},
        "Square Leg": {"angle": 265.0, "radius": 0.55}, "Fine Leg": {"angle": 205.0, "radius": 0.85},
        "Third Man": {"angle": 160.0, "radius": 0.85},
    },
    # More men in the ring (catches), fewer on the boundary — real risk/
    # reward: the target radius for a catch check (~0.35) sits right in
    # this layout's ring; the boundary-save check (~0.90) mostly misses it.
    "Aggressive": {
        "WK": {"angle": 180.0, "radius": 0.16}, "Slip": {"angle": 160.0, "radius": 0.18},
        "Gully": {"angle": 135.0, "radius": 0.24}, "Point": {"angle": 95.0, "radius": 0.38},
        "Cover": {"angle": 55.0, "radius": 0.42}, "Mid-off": {"angle": 22.0, "radius": 0.32},
        "Mid-on": {"angle": 338.0, "radius": 0.32}, "Midwicket": {"angle": 305.0, "radius": 0.40},
        "Square Leg": {"angle": 265.0, "radius": 0.38}, "Fine Leg": {"angle": 205.0, "radius": 0.55},
        "Third Man": {"angle": 160.0, "radius": 0.55},
    },
    # Boundary riders pushed out near the rope (real coverage of the ~0.90
    # boundary-save target radius) at the cost of a threadbare ring.
    "Defensive": {
        "WK": {"angle": 180.0, "radius": 0.16}, "Slip": {"angle": 160.0, "radius": 0.30},
        "Gully": {"angle": 135.0, "radius": 0.40}, "Point": {"angle": 95.0, "radius": 0.70},
        "Cover": {"angle": 55.0, "radius": 0.75}, "Mid-off": {"angle": 22.0, "radius": 0.60},
        "Mid-on": {"angle": 338.0, "radius": 0.60}, "Midwicket": {"angle": 305.0, "radius": 0.85},
        "Square Leg": {"angle": 265.0, "radius": 0.80}, "Fine Leg": {"angle": 205.0, "radius": 0.95},
        "Third Man": {"angle": 160.0, "radius": 0.95},
    },
}

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


def overs_text(balls: int, balls_per_set: int = 6) -> str:
    """Format legal deliveries as ``sets.balls``.

    Standard cricket uses six-ball overs.  The Hundred uses five-ball sets,
    so the same compact notation remains useful without misreporting 100
    legal balls as 16.4 overs.
    """
    balls_per_set = max(1, int(balls_per_set))
    return f"{balls // balls_per_set}.{balls % balls_per_set}"


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
    balls_per_set: int = 6

    @property
    def economy(self) -> float:
        return self.runs * self.balls_per_set / self.balls if self.balls else 0.0


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
    balls_per_set: int = 6
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
    session_data: list[dict[str, Any]] = field(default_factory=list)
    phase_data: list[dict[str, Any]] = field(default_factory=list)
    # v4.60.0: a running -100..100 swing (positive favours the batting side)
    # and a structured timeline of the moments that moved it — additive
    # display state built from signals the engine already computes (wickets,
    # boundaries, milestones), not a new outcome-weight mechanic. See
    # Match._update_momentum.
    momentum: int = 0
    key_moments: list[dict[str, Any]] = field(default_factory=list)
    # v4.61.0: the per-ball trail of `momentum` values — lets a client plot
    # a real trend line instead of maintaining its own parallel
    # reconstruction. Godot's Stats Hub "Momentum" tab previously
    # recomputed a similar-but-different swing (runs - wickets*8 over a
    # trailing 24-ball client-side window, built from the raw ball-event
    # stream) independently of this backend value — two different
    # formulas both called "momentum" was a real, confusing duplication.
    # This history is the single source of truth both the live ScoreBar
    # label (v4.60.0) and that chart now share.
    momentum_history: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.batters:
            self.batters = {
                int(p["id"]): BatterLine(int(p["id"]), str(p["name"]))
                for p in self.batting_order
            }
        if not self.bowlers:
            self.bowlers = {
                int(p["id"]): BowlerLine(int(p["id"]), str(p["name"]), balls_per_set=self.balls_per_set)
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
        return overs_text(self.legal_balls, self.balls_per_set)


class Match:
    """A complete limited-overs or Test match with ball-by-ball state.

    Team IDs may be database IDs or any stable integer. Players are ordinary
    dictionaries returned by ``database.fetch_players``.
    """

    MAX_BALLS = {"T10": 60, "T20": 120, "ODI": 300, "Hundred": 100, "Test": None}
    MAX_BOWLER_BALLS = {"T10": 12, "T20": 24, "ODI": 60, "Hundred": 20, "Test": None}

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
        ground_info: dict[str, Any] | None = None,
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
        # v4.53.0: a genuine "no result decided" Test draw (time expired,
        # both sides still had wickets/overs in hand) is a different real
        # outcome from a scores-level tie — both previously collapsed into
        # the same "winner_id is None" signal downstream (league standings'
        # "tied" column), losing the distinction a real County Championship
        # table needs (P/W/L/D, not P/W/L/T). Set True only at the two
        # actual draw sites below; a scores-level tie leaves this False.
        self.drawn = False
        self.is_super_over = False
        self.super_over_scores: dict[int, int] = {}
        self.commentary: list[dict[str, Any]] = []
        self.last_six: list[str] = []
        # v4.60.0: an optional multiplier on the existing home-grounds
        # advantage nudge below (see _weights' home_grounds_pct) — 1.0 by
        # default (identical to pre-v4.60.0 behaviour for every match that
        # doesn't explicitly set this), settable by the caller (ipc_server's
        # _start_match) from real crowd/atmosphere signals (ground capacity,
        # a rivalry fixture, cup-final stakes). Deliberately reuses the
        # existing mechanic rather than adding a new one — see docs/CURRENT.md.
        self.crowd_boost: float = 1.0
        # v4.95.0: cached squad cohesion for both teams — read once at
        # match start, applied as a small modifier in _ratings().
        self.cohesion_modifiers: dict[int, float] = {}
        for tid in (self.home_team_id, self.away_team_id):
            try:
                from database import fetch_squad_cohesion
                from src.models.squad_cohesion import match_modifier
                self.cohesion_modifiers[tid] = match_modifier(fetch_squad_cohesion(tid))
            except Exception:
                self.cohesion_modifiers[tid] = 0.0
        self.field_setting = "Neutral"
        # Real per-fielder layout per team (v4.13.0) — seeded to the
        # Neutral preset, replaced wholesale by set_field()'s preset branch
        # or set_field_layout()'s custom drag-editor branch. Deep-copied so
        # mutating one team's layout can never corrupt FIELD_LAYOUT_PRESETS
        # or the other team's independently-set layout.
        self.field_layout_by_team: dict[int, dict[str, dict[str, float]]] = {
            self.home_team_id: {k: dict(v) for k, v in FIELD_LAYOUT_PRESETS["Neutral"].items()},
            self.away_team_id: {k: dict(v) for k, v in FIELD_LAYOUT_PRESETS["Neutral"].items()},
        }
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
        # chances panel: dropped/missed_stumping/missed_runout (a fielding
        # attempt was rolled and failed), catchable (a "caught" dismissal was
        # rolled at all, taken or dropped — a real edge/lofted shot), lbw_appeals
        # (an lbw roll — the engine always upholds an lbw roll, see
        # _fielding_attempt, so this doubles as the lbw dismissal count), and
        # played_and_missed (a dot ball whose flavour text genuinely describes
        # the batter being beaten, not just blocking/leaving — see
        # BEATEN_DOT_PHRASES/_is_played_and_missed).
        self.chance_log: dict[int, dict[str, int]] = {}
        self._prediction_cache: dict[tuple[int, int, int, int], int] = {}
        self.ground_info = ground_info or {}
        self.captains = {
            team_id: int(max(squad, key=lambda p: _attrs(p, "mental").get("experience", 50))["id"])
            for team_id, squad in self.lineups.items()
        }
        self._initialise_energy()
        self._start_innings(first, second)

    def overs_limit(self) -> int:
        """Scheduled six-ball overs, or five-ball sets for The Hundred."""
        return (self.MAX_BALLS[self.format] or 540) // self.balls_per_set

    @property
    def balls_per_set(self) -> int:
        """Number of legal deliveries in the format's bowling unit."""
        return 5 if self.format == "Hundred" else 6

    @property
    def unit_label(self) -> str:
        return "sets" if self.format == "Hundred" else "overs"

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
        interval=25 if self.format == "Hundred" else 30 if self.format in ("T10", "T20") else 60 if self.format == "ODI" else 90
        match_balls=sum(item.legal_balls for item in self.innings)
        index=min(len(self.weather_forecast)-1,match_balls//interval)
        if index!=self.weather_index:
            self.weather_index=index; self.weather=self.weather_forecast[index]
            self._comment(f"Conditions update: {self.weather.lower()} skies now over the ground.","milestone")
        wear_rate={"T10":.030,"T20":.035,"ODI":.055,"Hundred":.040,"Test":.085}[self.format]
        grounds=float(self.teams[innings.batting_team].get("grounds_level",1))
        self.pitch_wear=min(100.0,match_balls*wear_rate/max(.8,1+(grounds-1)*.04))
        if self.format=="Test" and self.pitch_wear>=62 and self.pitch not in {"Worn","Dusty"}: self.pitch="Worn"
        if (self.format != "Test" and self.weather == "Rain Threat" and not self.rain_interruption_applied
                and self.current_innings.legal_balls >= 30 and self.rng.random() < .055):
            maximum = self.overs_limit()
            completed = self.current_innings.legal_balls // self.balls_per_set
            reduced = max(completed + 3, maximum - self.rng.randint(2, 8 if self.format in ("T10", "T20", "Hundred") else 18))
            self.apply_rain_interruption(min(maximum, reduced))

    def apply_rain_interruption(self, revised_overs: int) -> int:
        """Apply a live limited-overs rain reduction and refresh a chase target."""
        if self.format == "Test":
            self._comment("Rain stops play; lost time may affect the declaration and result.", "milestone")
            return 0
        maximum = self.overs_limit()
        completed = self.current_innings.legal_balls // self.balls_per_set
        self.rain_overs = max(completed + 1, min(maximum, int(revised_overs)))
        self.rain_interruption_applied = True
        if len(self.innings) >= 2:
            self.current_innings.target = self.dls_target(self.innings[0].runs)
        target = self.current_innings.target or 0
        suffix = f" Revised target: {target}." if target else ""
        self._comment(f"Rain interruption: the innings is reduced to {self.rain_overs} {self.unit_label}.{suffix}", "milestone")
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
            balls_per_set=self.balls_per_set,
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
            # A malformed or injury-hit XI can contain too few specialist
            # bowlers to complete a limited-overs innings.  Use another squad
            # member before breaking a format's hard individual workload cap.
            if not candidates:
                candidates = [p for p in innings.bowling_squad
                              if innings.bowlers[int(p["id"])].balls < maximum]
        return candidates

    def choose_bowler(self, critical: bool | None = None) -> int:
        """Choose an AI bowler using quality, fatigue, economy, and match phase."""
        innings = self.current_innings
        candidates = self._eligible_bowlers()
        if not candidates:
            candidates = list(innings.bowling_squad)
        if len(candidates) > 1 and self.format != "Hundred":
            alternatives = [p for p in candidates if int(p["id"]) != innings.previous_bowler_id]
            candidates = alternatives or candidates
        remaining = (self.MAX_BALLS[self.format] or 9999) - innings.legal_balls
        critical = critical if critical is not None else remaining <= (30 if self.format in ("T10", "T20", "Hundred") else 60)

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
        if player_id not in eligible or (self.format != "Hundred" and player_id == innings.previous_bowler_id):
            return False
        innings.current_bowler_id = player_id
        return True

    def set_field(self, preset: str | None = None) -> str:
        """Set a manual preset, or let the AI infer one from match state.

        Also loads that preset's real per-fielder layout into
        field_layout_by_team for whichever team is currently bowling
        (v4.13.0) — this is what actually drives catch/boundary-save
        coverage now, not just the flat field_setting nudge in _weights().
        """
        if preset in FIELD_PRESETS:
            self.field_setting = preset
            self.field_layout_by_team[self.current_innings.bowling_team] = \
                {k: dict(v) for k, v in FIELD_LAYOUT_PRESETS[preset].items()}
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
        self.field_layout_by_team[innings.bowling_team] = \
            {k: dict(v) for k, v in FIELD_LAYOUT_PRESETS[optimal].items()}
        return self.field_setting

    # v4.22.0: real Law-41.5-style leg-side limit — never more than two
    # fielders (besides the keeper) behind the popping crease on the leg
    # side, regardless of format. In this angle convention (0 = straight
    # down the ground, 180 = straight behind the stumps, clockwise) "behind
    # square on the leg side" is the open arc (180, 270).
    LEG_SIDE_BEHIND_SQUARE_MAX = 2
    # Circle-fielder caps: tight during the powerplay, looser once it ends.
    # Test cricket has no fielding restrictions at all. CIRCLE_RADIUS is
    # calibrated to this app's own preset geometry (FIELD_LAYOUT_PRESETS'
    # "boundary rider" spots sit around 0.75-0.95) rather than a literal
    # 30-yard-vs-90m-boundary ratio, so the built-in Neutral/Aggressive/
    # Defensive presets — which a custom edit always starts from — stay
    # legal to fine-tune from rather than being pre-emptively illegal.
    CIRCLE_RADIUS = 0.75
    CIRCLE_MAX_POWERPLAY = 3
    CIRCLE_MAX_STANDARD = 5

    def _field_legality_error(self, layout: dict[str, dict[str, float]]) -> str | None:
        """None if legal, else a human-readable reason — real cricket
        fielding-restriction rules, not a rubber-stamp. Positions are
        checked by their ACTUAL dragged angle/radius, not just their
        canonical name, since a player can drag any fielder anywhere."""
        outfielders = {name: pos for name, pos in layout.items() if name != "WK"}
        behind_square_leg = sum(1 for pos in outfielders.values() if 180.0 < pos["angle"] < 270.0)
        if behind_square_leg > self.LEG_SIDE_BEHIND_SQUARE_MAX:
            return (f"Illegal field: {behind_square_leg} fielders behind square on the leg side "
                    f"(law allows at most {self.LEG_SIDE_BEHIND_SQUARE_MAX}, excluding the keeper).")
        if self.format != "Test":
            outside_circle = sum(1 for pos in outfielders.values() if pos["radius"] > self.CIRCLE_RADIUS)
            circle_max = self.CIRCLE_MAX_POWERPLAY if self.powerplay else self.CIRCLE_MAX_STANDARD
            if outside_circle > circle_max:
                phase = "powerplay" if self.powerplay else "this phase of the innings"
                return (f"Illegal field: {outside_circle} fielders outside the 30-yard circle "
                        f"(max {circle_max} allowed during {phase}).")
        return None

    def set_field_layout(self, team_id: int, positions: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        """Apply a fully custom per-fielder layout for one team — the real
        drag-and-place editor's target. Unknown position names are dropped
        rather than rejected outright, so a client can round-trip whatever
        it has without the whole call failing over one bad key; angle/
        radius are clamped to sane ranges either way. The resulting layout
        must still be a LEGAL field (see _field_legality_error) — this is
        checked last, against the full merged layout, so a client sending
        only the one dot that moved is validated against where everyone
        else already stands, not in isolation."""
        if team_id not in self.teams:
            raise ValueError(f"Unknown team_id: {team_id}")
        # Merge onto the team's EXISTING layout (not a blank slate) so
        # legality is checked against where everyone actually stands, not
        # just the one dot a client happened to include this call — but
        # "did the caller supply anything real" is judged on the incoming
        # positions alone, so an all-garbage payload still fails loudly
        # instead of silently no-op'ing against the pre-existing baseline.
        layout: dict[str, dict[str, float]] = dict(self.field_layout_by_team.get(team_id, {}))
        applied_any = False
        for name, pos in positions.items():
            if name not in FIELD_POSITIONS:
                continue
            applied_any = True
            angle = float(pos.get("angle", 0.0)) % 360.0
            radius = max(0.05, min(1.0, float(pos.get("radius", 0.5))))
            layout[name] = {"angle": angle, "radius": radius}
        if not applied_any:
            raise ValueError("No valid field positions supplied")
        error = self._field_legality_error(layout)
        if error:
            raise ValueError(error)
        self.field_layout_by_team[team_id] = layout
        return layout

    def _covering_fielder(self, angle_deg: float, target_radius: float,
                          layout: dict[str, dict[str, float]]) -> tuple[str | None, float]:
        """Nearest named fielding position to a shot's landing angle, if
        close enough in both angle and depth to plausibly matter — this is
        the real hook that makes field_layout_by_team affect outcomes
        (catch conversion, boundary saves) instead of being cosmetic.
        Returns (position_name, coverage 0-1), or (None, 0.0) when the shot
        lands in a gap nobody's covering — leaving a gap open is meant to
        matter, so this deliberately does not fall back to "nearest
        anything regardless of distance"."""
        best_name: str | None = None
        best_strength = 0.0
        for name, pos in layout.items():
            angle_diff = abs(((angle_deg - pos["angle"] + 180.0) % 360.0) - 180.0)
            if angle_diff > 25.0:
                continue
            angular = 1.0 - angle_diff / 25.0
            radial = max(0.0, 1.0 - abs(target_radius - pos["radius"]) / 0.35)
            strength = angular * radial
            if strength > best_strength:
                best_strength = strength; best_name = name
        return (best_name, best_strength) if best_strength > 0.12 else (None, 0.0)

    def adjust_aggression(self) -> int:
        """Let the batting AI choose an aggression level from 1–10."""
        innings = self.current_innings
        if innings.target:
            required = self.required_rate
            optimal = max(2, min(10, round(required + 1.5)))
        elif self.format in ("T10", "T20", "Hundred"):
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
            current_rate = innings.runs * self.balls_per_set / max(self.balls_per_set, innings.legal_balls)
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
        balls_left = max(1, (self.rain_overs or self.overs_limit()) * self.balls_per_set - innings.legal_balls)
        return max(0, innings.target - innings.runs) * self.balls_per_set / balls_left

    @property
    def powerplay(self) -> bool:
        over = self.current_innings.legal_balls // self.balls_per_set + 1
        if self.format == "T10":
            return over <= 3
        if self.format == "Hundred":
            return self.current_innings.legal_balls < 25
        if self.format == "T20":
            return over <= 6
        if self.format == "ODI":
            return over <= 10 or over >= 41
        return False

    def _choose_delivery_line_length(self, bowler: dict[str, Any]) -> tuple[str, str]:
        """Pick this ball's actual line/length — real bowlers vary delivery
        to delivery, they don't hold one fixed tactic all spell. Death overs
        skew toward yorkers/full (containment), a low-control bowler drifts
        short more often (loss of discipline), and spinners drift towards
        the stumps rather than channel outside off like a seamer does.
        preferred_line/preferred_length (PlayerTactics) are never actually
        set anywhere in either client today, so this replaces what was
        previously always-the-same-default cosmetic pitch-map dots with a
        real per-ball choice that also now feeds match outcome weights.

        v4.21.0: a manager-set delivery target (bowler["_target_line"]/
        ["_target_length"], from ipc_server.py's set_delivery_target — the
        pitch-strip click-to-aim UI) is honoured here with a control-skill
        -based execution chance rather than a guarantee, same spirit as a
        real bowler not nailing every instruction from the captain."""
        bowl = _attrs(bowler, "bowling")
        tactics = PlayerTactics.from_player(bowler)
        control = bowl.get("control", bowl.get("accuracy", 50))
        target_line = bowler.get("_target_line")
        target_length = bowler.get("_target_length")
        if target_line and target_length:
            hit_chance = 0.35 + control / 100.0 * 0.5
            if self.rng.random() < hit_chance:
                return target_line, target_length
        maximum = (self.rain_overs or self.overs_limit()) * self.balls_per_set
        is_death = self.format != "Test" and self.current_innings.legal_balls >= maximum * .85

        length_weights = {"Yorker": 35, "Full": 25, "Good": 20, "Short": 20} if is_death else \
            {"Good": 55, "Full": 20, "Short": 15, "Yorker": 10}
        length_weights = dict(length_weights)
        if control >= 70:
            length_weights["Good"] += 15; length_weights["Short"] = max(3, length_weights["Short"] - 10)
        elif control < 45:
            length_weights["Short"] += 15; length_weights["Good"] = max(3, length_weights["Good"] - 10)
        length = self.rng.choices(list(length_weights), weights=list(length_weights.values()), k=1)[0]

        if tactics.bowling_style in SPIN_STYLES:
            line_weights = {"Middle": 32, "Leg Stump": 25, "Off Stump": 30, "Wide": 13}
        else:
            line_weights = {"Off Stump": 45, "Middle": 25, "Leg Stump": 15, "Wide": 15}
        line = self.rng.choices(list(line_weights), weights=list(line_weights.values()), k=1)[0]
        return line, length

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
        # v4.95.0: squad cohesion modifier — familiar XIs play better together
        batter_team = int(batter.get("team_id", 0))
        bowler_team = int(bowler.get("team_id", 0))
        batting += self.cohesion_modifiers.get(batter_team, 0.0)
        bowling += self.cohesion_modifiers.get(bowler_team, 0.0)
        batter_personality = batter.get("personality", "Professional")
        bowler_personality = bowler.get("personality", "Professional")
        from database import PERSONALITIES as _P
        # Keeper batting role: specialist keepers bat more defensively
        # (they know their keeping is their main value, so they play
        # within themselves), while keeper-batsmen bat more freely.
        if _role(batter) == "Wicketkeeper":
            from database import classify_keeper_batting_role
            kb_role = classify_keeper_batting_role(batter)
            if kb_role == "keeper_batsman":
                batting += 1.5  # confident, plays shots
            elif kb_role == "specialist_keeper":
                batting -= 1.0  # plays within limits, defends more
        if batter_personality in _P:
            bp = _P[batter_personality]
            big_bonus = bp["big_match_bonus"] * .015 if self.knockout else 0
            batting += big_bonus
            batting += (mental.get("morale", 50) - 50) * .05 * (bp["morale_mult"] - 1.0)
        if bowler_personality in _P:
            bwp = _P[bowler_personality]
            big_bonus_bowl = bwp["big_match_bonus"] * .015 if self.knockout else 0
            bowling += big_bonus_bowl
        pressure = 0.0
        if innings.target:
            pressure = max(0.0, self.required_rate - (6.5 if self.format in ("T10", "T20", "Hundred") else 5.2)) + innings.wickets * .25
            composure = mental.get("experience", 50) * .6 + mental.get("big_match", 50) * .4
            resist = _P.get(batter_personality, {}).get("pressure_resist", 1.0) if batter_personality in _P else 1.0
            batting -= pressure * max(.15, (70 - composure) / 35) / resist
        balls_so_far = innings.legal_balls
        overs_total = self.overs_limit()
        is_powerplay = balls_so_far < {"T10": 12, "T20": 36, "ODI": 60, "Hundred": 25, "Test": 9999}.get(self.format, 9999)
        is_death = balls_so_far >= max(0, (overs_total * self.balls_per_set) - {"T10": 12, "T20": 24, "ODI": 60, "Hundred": 20, "Test": 9999}.get(self.format, 9999))
        is_middle = not is_powerplay and not is_death and self.format != "Test"
        is_early = balls_so_far < 15
        from database import PLAYER_TRAITS as _T
        batter_traits = json.loads(batter.get("traits", "[]"))
        bowler_traits = json.loads(bowler.get("traits", "[]"))
        for tid in batter_traits:
            if tid not in _T: continue
            t = _T[tid]
            phase = t.get("phase", "any")
            if phase == "powerplay" and is_powerplay: pass
            elif phase == "death" and is_death: pass
            elif phase == "middle" and is_middle: pass
            elif phase == "early" and is_early: pass
            elif phase == "rebuild" and self.current_innings.wickets >= 3: pass
            elif phase != "any": continue
            for attr, val in t.get("batting", {}).items():
                if attr in bat: batting += val * .015
            if tid == "Nervous Starter" and balls_so_far < t.get("settle_balls", 15):
                batting -= 3
        for tid in bowler_traits:
            if tid not in _T: continue
            t = _T[tid]
            phase = t.get("phase", "any")
            if phase == "powerplay" and is_powerplay: pass
            elif phase == "death" and is_death: pass
            elif phase == "middle" and is_middle: pass
            elif phase == "early" and is_early: pass
            elif phase != "any": continue
            for attr, val in t.get("bowling", {}).items():
                if attr in bowl: bowling += val * .015
            for attr, val in t.get("fielding", {}).items():
                if attr in _attrs(bowler, "fielding"): pass
        fielding_values = [
            _mean(_attrs(p, "fielding").values()) - max(0.0, 50 - self.player_energy(int(p["id"]))) * .18
            for p in innings.bowling_squad
        ]
        fielding = _mean(fielding_values)
        ball_age = innings.legal_balls / self.balls_per_set
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

    def _weights(self, batter: dict[str, Any], bowler: dict[str, Any],
                line: str = "Off Stump", length: str = "Good") -> dict[str, float]:
        batting, bowling, fielding = self._ratings(batter, bowler)
        advantage = max(-30, min(30, batting - bowling))
        aggression = self.effective_batting_aggression
        # Baseline sits inside the requested ranges; modifiers redistribute it.
        wicket = {"T10": 3.0, "T20": 3.2, "ODI": 4.0, "Hundred": 3.4, "Test": 5.2}[self.format]
        wicket += -advantage * .055 + max(0, aggression - 6) * .45
        # Halved in v4.13.0: real per-fielder coverage (field_layout_by_team,
        # see _covering_fielder) now does most of the work this flat nudge
        # used to carry alone; it stays as a small residual aggression tilt.
        wicket += 0.4 if self.field_setting == "Aggressive" else -0.2 if self.field_setting == "Defensive" else 0
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
        if self.format in ("T10", "T20", "Hundred"):
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
        # This ball's actual line/length (chosen per-delivery by
        # _choose_delivery_line_length, real cricket bowling tactics) now
        # has a real mechanical effect, not just cosmetic pitch-map dots.
        if length == "Yorker": wicket += .5; dot += 1.0; four -= .6; six -= .6
        elif length == "Full": four += .8; six += .3; wicket += .3; dot -= .3
        elif length == "Good": dot += 1.2; four -= .5; six -= .4; wicket -= .3
        elif length == "Short": four += .3; six += .6; wicket += .4; dot -= .4
        grounds_level = int(self.teams.get(self.home_team_id, {}).get("grounds_level", 1))
        if grounds_level > 1:
            home_grounds_pct = (grounds_level - 1) * 0.25 * self.crowd_boost
            if batter.get("team_id") is not None and int(batter["team_id"]) == self.home_team_id:
                one += home_grounds_pct * 1.5; two += home_grounds_pct * 0.6; four += home_grounds_pct * 0.4
            if bowler.get("team_id") is not None and int(bowler["team_id"]) == self.home_team_id:
                wicket += home_grounds_pct * 1.0; dot += home_grounds_pct * 0.8; four -= home_grounds_pct * 0.3
        if line == "Off Stump": wicket += .4; dot += .3
        elif line == "Leg Stump": four += .4; wicket += .2; dot -= .2
        elif line == "Middle": dot += .5; wicket -= .1
        elif line == "Wide": dot -= .3; wicket -= .3; four += .3
        boundary = self.ground_info.get("boundary_size", 75)
        if boundary < 70:
            four -= 0.8; six -= 0.5
        elif boundary > 80:
            four += 0.7; six += 0.4
        outfield = self.ground_info.get("outfield_speed", "medium")
        if outfield == "fast":
            two += 0.8; three += 0.3
        elif outfield == "slow":
            two -= 0.5; three -= 0.2
        affinity = self.ground_info.get("pitch_affinity", "balanced")
        bowler_style = _attrs(bowler, "bowling").get("style", "Medium")
        pace_bowler = bowler_style in ("Fast", "Medium-Fast", "Medium") or any(p in bowler_style.lower() for p in ("fast", "medium"))
        if affinity == "pace" and pace_bowler:
            wicket += 0.6; dot += 0.5; four -= 0.3
        elif affinity == "spin" and not pace_bowler:
            wicket += 0.6; dot += 0.5; four -= 0.3
        elif affinity == "pace" and not pace_bowler:
            wicket -= 0.3; four += 0.3
        elif affinity == "spin" and pace_bowler:
            wicket -= 0.3; four += 0.3
        dot_ceiling = {"T10": 36, "T20": 42, "ODI": 52, "Hundred": 40, "Test": 70}[self.format]
        return {
            "dot": max(20, min(dot_ceiling, dot)), "1": max(20, min(35, one)),
            "2": max(5, min(10, two)), "3": max(1, min(3, three)),
            "4": max(5, min(15, four)), "6": max(1, min(5, six)),
            "W": max(2, min(10, wicket)), "extra": extras,
        }

    def _fielding_attempt(self, batter: dict[str, Any], bowler: dict[str, Any],
                          angle_deg: float | None = None) -> dict[str, Any]:
        """Resolve the individual skill check behind a possible dismissal.

        ``angle_deg`` (v4.13.0) is this ball's shot-landing angle, already
        rolled by the caller before the wicket check — when the wicket type
        is "caught", it's checked against the bowling team's real
        field_layout_by_team so a well-covered angle genuinely catches more
        often than an open gap, replacing what used to be a flavor-only
        random position label with a real coverage check.
        """
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
        covering_position: str | None = None
        coverage = 0.0
        if wicket_type == "caught" and angle_deg is not None:
            layout = self.field_layout_by_team.get(innings.bowling_team, {})
            covering_position, coverage = self._covering_fielder(angle_deg, 0.35, layout)
        # _wicket_commentary formats this into "caught at {position}" —
        # keep it a bare place name (not a phrase) either way.
        position = covering_position.lower() if covering_position else self.rng.choice(
            ["deep midwicket", "long-on", "long-off", "deep cover"])
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
            # Real field coverage (v4.13.0): a shot hit straight at a
            # covering fielder is meaningfully more likely to be taken; an
            # aerial shot into an open gap is meaningfully less likely to
            # be — the floor drops well below the old flat .48 when nobody
            # covers that angle, so leaving a gap in the field now matters.
            chance += coverage * .22 if covering_position else -.12
            if "Reflex Catch" in triggered and self.rng.random() < .09:
                chance += .16; proc = "Reflex Catch"
            floor = .40 if covering_position else .24
            success = self.rng.random() < max(floor, min(.96, chance))
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
        if legal_balls <= 0 or legal_balls % self.balls_per_set: return False
        over = legal_balls // self.balls_per_set
        if self.format == "T10": return over == 5
        if self.format == "Hundred": return over == 10
        if self.format == "T20": return over == 10
        if self.format == "ODI": return over in {15, 30, 40}
        return over % 30 == 0

    def _maybe_partnership_landmark(self, innings: InningsState) -> None:
        runs = innings.partnership_runs
        if 0 < runs < 50:
            return
        landmark = runs // 50 * 50
        if runs % 50 == 0 or (runs > landmark and runs - self.balls_per_set < landmark):
            a_name = innings.striker_player["name"]
            b_name = innings.non_striker_player["name"]
            self._comment(self.rng.choice(self.PARTNERSHIP_LINES).format(runs=runs, a=a_name, b=b_name), "milestone")
            if runs % 100 == 0 and runs >= 100:
                self._comment(self.rng.choice(self.CENTURY_PARTNERSHIP_LINES).format(runs=runs, a=a_name, b=b_name), "milestone")

    def _format_session_name(self) -> str:
        if self.format != "Test":
            return ""
        session_map = {1: "Morning", 2: "Afternoon", 3: "Evening"}
        return f"Day {self.day}, {session_map.get(self.session, '')} Session"

    def _session_wrapup(self) -> None:
        innings = self.current_innings
        name = self._format_session_name()
        if not name:
            return
        rr = innings.runs / max(1, innings.legal_balls) * self.balls_per_set
        session_period = name.split(", ")[1] if ", " in name else name
        self._comment(self.rng.choice(self.SESSION_WRAP_LINES).format(
            name=name, team=innings.batting_name, runs=innings.runs,
            wickets=innings.wickets, overs=innings.overs, rr=rr, session=session_period), "milestone")

    def _update_momentum(self, innings: InningsState, kind: str, runs: int,
                         wicket_type: str | None, batter: dict[str, Any], bowler: dict[str, Any]) -> None:
        """v4.60.0: a running -100..100 swing (positive favours the batting
        side) built entirely from signals this ball's outcome already
        produced — no new randomness, no change to any outcome-weight
        formula. Decays toward zero each ball so it reflects recent form,
        not the whole innings, before this ball's delta is applied.
        Also appends a structured key-moment entry for the swings worth
        surfacing on a timeline (wickets, boundaries, milestones)."""
        innings.momentum = round(innings.momentum * 0.94)
        description = None
        if wicket_type:
            delta = -15
            description = f"WICKET — {batter['name']} out ({wicket_type})"
        elif runs == 6:
            delta = 10
            description = f"SIX — {batter['name']} off {bowler['name']}"
        elif runs == 4:
            delta = 6
            description = f"FOUR — {batter['name']} off {bowler['name']}"
        elif runs == 0:
            delta = -2
        else:
            delta = 1
        innings.momentum = max(-100, min(100, innings.momentum + delta))
        innings.momentum_history.append(innings.momentum)
        # Same "just crossed the line this ball" check the commentary block
        # above already uses (batting_line.runs vs batting_line.runs - runs)
        # — reused here rather than re-derived, so this can never disagree
        # with what the commentary actually announced.
        batting_line = innings.batters[int(batter["id"])]
        if wicket_type is None:
            if batting_line.runs >= 100 and batting_line.runs - runs < 100:
                description = f"CENTURY — {batter['name']}"
            elif batting_line.runs >= 50 and batting_line.runs - runs < 50:
                description = f"FIFTY — {batter['name']}"
        if description:
            innings.key_moments.append({"over": innings.overs, "description": description, "swing": delta})

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
        if innings.legal_balls % self.balls_per_set == 0:
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
        line, length = self._choose_delivery_line_length(bowler)
        weights = self._weights(batter, bowler, line, length)
        labels, chances = zip(*weights.items())
        selected = self.rng.choices(labels, weights=chances, k=1)[0]
        bowl_x=max(0.03,min(.97,self.rng.gauss({"Leg Stump":.38,"Middle":.5,"Off Stump":.62,"Wide":.78}.get(line,.62),.11)))
        bowl_y=max(0.03,min(.97,self.rng.gauss({"Yorker":.83,"Full":.68,"Good":.5,"Short":.28}.get(length,.5),.12)))
        # v4.13.0: rolled once per ball, before the wicket/boundary check
        # (previously rolled after, purely for the wagon-wheel display) so
        # the real field_layout_by_team can be checked against it — see
        # _covering_fielder and its two call sites below.
        angle = self.rng.uniform(-3.14159, 3.14159)
        angle_deg = (angle * 180.0 / 3.14159265 + 360.0) % 360.0
        legal = True
        runs = 0
        kind = "normal"
        wicket_type = None
        fielder = None
        fielder_player = None
        missed_chance = None
        wicket_attempt = None
        boundary_saved_by = None

        # A weighted wicket event still needs an individual execution check.
        if selected == "W":
            wicket_attempt = self._fielding_attempt(batter, bowler, angle_deg)
            log = self.chance_log.setdefault(int(batter["id"]), self._empty_chance_log())
            if wicket_attempt["type"] == "caught":
                log["catchable"] += 1
            elif wicket_attempt["type"] == "lbw":
                log["lbw_appeals"] += 1
            if not wicket_attempt["success"]:
                wicket_type = str(wicket_attempt["type"])
                fielder_player = wicket_attempt["fielder"]
                fielder_name = fielder_player["name"] if fielder_player else "the fielder"
                if wicket_type == "caught": missed_chance = self.rng.choice(self.DROPPED_LINES).format(fielder_name=fielder_name)
                elif wicket_type == "stumped": missed_chance = self.rng.choice(self.MISSED_STUMP_LINES).format(fielder_name=fielder_name)
                else: missed_chance = self.rng.choice(self.MISSED_RUNOUT_LINES).format(fielder_name=fielder_name, batter_name=batter['name'])
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
            bo = bowler['name']
            if selected == 'Wd':
                commentary = self.rng.choice(self.WIDE_LINES).format(bo=bo, b=batter['name'])
            else:
                commentary = self.rng.choice(self.NOBALL_LINES).format(bo=bo)
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
            self._maybe_partnership_landmark(innings)
            innings.partnerships.append({"a": batter["name"], "b": innings.non_striker_player["name"],
                                         "runs": innings.partnership_runs, "balls": innings.partnership_balls})
            innings.partnership_runs = innings.partnership_balls = 0
            if innings.next_batter < len(innings.batting_order):
                innings.striker = innings.next_batter; innings.next_batter += 1
                innings.batters[int(innings.striker_player["id"])].dismissal = "not out"
        else:
            # v4.13.0: a firmly-struck four hit straight at a covering
            # boundary fielder has a real chance of being cut off — sixes
            # are deliberately excluded, since by definition the ball has
            # already crossed the rope on the full and no fielder can save
            # it (only a boundary catch could stop one, a bigger change
            # left for a future pass; see the plan's Verification note).
            if selected == "4":
                layout = self.field_layout_by_team.get(innings.bowling_team, {})
                covering, strength = self._covering_fielder(angle_deg, 0.90, layout)
                if covering:
                    save_candidates = [p for p in innings.bowling_squad
                                       if int(p["id"]) != int(bowler["id"])] or list(innings.bowling_squad)
                    saver = self.rng.choice(save_candidates)
                    save_attrs = _attrs(saver, "fielding")
                    save_chance = .06 + strength * .22
                    save_chance += (save_attrs.get("ground_fielding", 50) - 50) * .0030
                    save_chance += (save_attrs.get("agility", 50) - 50) * .0020
                    if self.rng.random() < max(.03, min(.48, save_chance)):
                        selected = str(self.rng.choice([1, 1, 2, 2, 3]))
                        boundary_saved_by = saver["name"]
            runs = 0 if selected == "dot" else int(selected)
            batting_line.runs += runs; batting_line.balls += 1
            batting_line.fours += int(runs == 4); batting_line.sixes += int(runs == 6)
            batting_line.outcomes.append(runs)
            innings.runs += runs; innings.partnership_runs += runs; innings.partnership_balls += 1
            innings.legal_balls += 1; bowling_line.balls += 1; bowling_line.runs += runs; bowling_line.current_over_runs += runs
            if selected != "dot":
                self._maybe_partnership_landmark(innings)
            if runs % 2:
                innings.striker, innings.non_striker = innings.non_striker, innings.striker
            kind = "run" if runs >= 4 else "normal"
            commentary = self._run_commentary(batter, runs, line, length)
            if runs == 0 and self._is_played_and_missed(commentary):
                log = self.chance_log.setdefault(int(batter["id"]), self._empty_chance_log())
                log["played_and_missed"] += 1
            if runs == 0:
                # Wicketkeeping depth: weak glovework leaks byes on missed takes.
                keeper = next((p for p in innings.bowling_squad if _role(p) == "Wicketkeeper"), None)
                glove = _attrs(keeper, "fielding").get("catching", 50) if keeper else 40
                if self.rng.random() < max(.002, (72 - glove) * .00042):
                    byes = self.rng.choice([1, 1, 1, 2, 4])
                    innings.runs += byes; innings.extras["b"] += byes
                    if byes % 2:
                        innings.striker, innings.non_striker = innings.non_striker, innings.striker
                    keeper_name = keeper["name"] if keeper else "the keeper"
                    s = 's' if byes > 1 else ''
                    commentary = self.rng.choice(self.BYE_LINES).format(keeper_name=keeper_name, byes=byes, s=s)
                    kind = "run"
            if boundary_saved_by:
                commentary = self.rng.choice(self.BOUNDARY_SAVE_LINES).format(saver=boundary_saved_by, commentary=commentary)
            if missed_chance:
                commentary = f"{missed_chance} {commentary}"
            if batting_line.runs >= 100 and batting_line.runs - runs < 100:
                commentary = f"{self.rng.choice(self.CENTURY_LINES).format(name=batter['name'])} {commentary}"
            elif batting_line.runs >= 50 and batting_line.runs - runs < 50:
                commentary = f"{self.rng.choice(self.FIFTY_LINES).format(name=batter['name'])} {commentary}"
            selected = "•" if selected == "dot" else selected

        self._update_momentum(innings, kind, runs, wicket_type, batter, bowler)
        talent = (wicket_attempt or {}).get("proc") or self.last_triggered_talent
        if talent:
            commentary = f"[{talent}] {commentary}"
        self._delivery_energy_costs(batter, bowler, legal, runs)
        # angle was already rolled earlier this ball (see the comment near
        # its declaration above) so the field-coverage checks and this
        # wagon-wheel event use the exact same landing spot — distance is
        # still a proxy for the ball's *final* runs (post-save/post-catch),
        # not independent geometry.
        distance={0:.12,1:.32,2:.55,3:.72,4:.92,6:1.0}.get(runs,.15)
        innings_number = self.current_innings_index + 1
        shot={"player_id":int(batter["id"]),"innings":innings_number,"angle":angle,"distance":distance,"runs":runs,"wicket":bool(wicket_type)}
        delivery={"player_id":int(bowler["id"]),"innings":innings_number,"x":bowl_x,"y":bowl_y,"wicket":bool(wicket_type),"runs":runs}
        self.shot_events.append(shot); self.bowling_events.append(delivery)
        injury = self._maybe_injury(batter, bowler, bowling_line)
        if legal and innings.legal_balls % self.balls_per_set == 0:
            if bowling_line.current_over_runs == 0:
                bowling_line.maidens += 1
                self._comment(self.rng.choice(self.MAIDEN_LINES).format(bo=bowler['name'], b=batter['name']), "normal")
            bowling_line.current_over_runs = 0
            innings.striker, innings.non_striker = innings.non_striker, innings.striker
            innings.previous_bowler_id = innings.current_bowler_id
            innings.current_bowler_id = self.choose_bowler()
            if self._is_drinks_break(innings.legal_balls):
                self._recover_energy(amount=4.5)
                self._comment(self.rng.choice(self.DRINKS_LINES), "milestone")
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
        if self.format != "Test":
            self._record_phase()
            return
        prev_session = self.session
        prev_day = self.day
        match_balls = sum(state.legal_balls for state in self.innings)
        self.day = min(5, match_balls // 540 + 1)
        self.session = min(3, (match_balls % 540) // 180 + 1)
        if self.session != prev_session or self.day != prev_day:
            self._record_session_data()
            self._session_wrapup()

    def _record_session_data(self) -> None:
        """Snapshot the current innings at session boundaries."""
        innings = self.current_innings
        innings.session_data.append({
            "day": self.day, "session": self.session,
            "runs": innings.runs, "wickets": innings.wickets,
            "legal_balls": innings.legal_balls, "overs": innings.overs,
            "rr": round(innings.runs / max(1, innings.legal_balls / self.balls_per_set), 2),
        })

    def _record_phase(self) -> None:
        """Snapshot limited-overs phase (powerplay/middle/death) at transitions."""
        innings = self.current_innings
        overs_completed = innings.legal_balls // self.balls_per_set
        if self.format in ("T10", "T20", "Hundred"):
            new_phase = "powerplay" if overs_completed < 6 else "middle" if overs_completed < 16 else "death"
        elif self.format == "ODI":
            new_phase = "powerplay" if overs_completed < 10 else "middle" if overs_completed < 40 else "death"
        else:
            return
        if not innings.phase_data or innings.phase_data[-1].get("phase") != new_phase:
            innings.phase_data.append({
                "phase": new_phase, "over": overs_completed,
                "runs": innings.runs, "wickets": innings.wickets,
                "legal_balls": innings.legal_balls,
            })

    def _maybe_injury(self, batter: dict[str, Any], bowler: dict[str, Any], line: BowlerLine) -> dict[str, Any] | None:
        """Generate a rare, fitness-driven injury under sustained workload."""
        for player, workload in ((batter, 0), (bowler, max(0, line.balls - 72))):
            physical = _attrs(player, "physical")
            fitness = physical.get("fitness", _attrs(player, "mental").get("fitness", 50))
            endurance = physical.get("endurance", _attrs(player, "mental").get("endurance", fitness))
            team_id = next((team_id for team_id, squad in self.lineups.items()
                            if any(int(member["id"]) == int(player["id"]) for member in squad)), self.home_team_id)
            medical_level = float(self.teams[team_id].get("medical_level", 1))
            physio_rating = int(self.teams[team_id].get("physio_rating", 10))
            chance = .00004 + max(0, 55 - fitness) * .000004 + workload * .0000008
            chance += max(0, 50 - endurance) * .000002
            # A player who came into the match already carrying fatigue
            # from insufficient rest is more injury-prone than endurance
            # alone accounts for — the real-world case for squad rotation.
            chance += max(0.0, float(player.get("fatigue", 0))) * .0000015
            chance *= max(.55, 1 - (medical_level - 1) * .11)
            from src.models.staff import medical_injury_multiplier
            chance *= medical_injury_multiplier(physio_rating)
            if self.rng.random() < chance:
                severity = self.rng.choices(["Minor", "Moderate", "Major"], [72, 23, 5], k=1)[0]
                base_days = {"Minor": 7, "Moderate": 14, "Major": 35}[severity]
                recovery_factor = max(.72, 1 - (physio_rating - 10) * .018)
                days = max(3, round(base_days * recovery_factor))
                record = {"player_id": int(player["id"]), "player": player["name"], "severity": severity, "days": days}
                self.injuries.append(record)
                return record
        return None

    @staticmethod
    def _empty_chance_log() -> dict[str, int]:
        return {"dropped": 0, "missed_stumping": 0, "missed_runout": 0,
                "catchable": 0, "lbw_appeals": 0, "played_and_missed": 0}

    # A subset of DOT_LINES whose flavour text genuinely describes the batter
    # being beaten by the ball (edge missed, bounce/nip beats the bat) rather
    # than a solid block or a deliberate leave — used to derive a real
    # "played & missed" chances count instead of counting every dot ball.
    BEATEN_DOT_PHRASES = ("beaten but the stumps stay intact", "plays inside the line and misses",
        "Beaten by the extra bounce", "watches it go past the outside edge",
        "Short balls are becoming a problem")

    @classmethod
    def _is_played_and_missed(cls, commentary: str) -> bool:
        return any(phrase in commentary for phrase in cls.BEATEN_DOT_PHRASES)

    # Dot/1/2/3 phrasing pools — the most frequent outcomes by far, so this
    # is where varying the text matters most for not feeling repetitive.
    DOT_LINES = ("{b} defends; no run.", "{b} lets it go through to the keeper.",
                "{b} plays it back down the pitch.", "{b} is beaten but the stumps stay intact.",
                "{b} blocks it out solidly.", "Good ball — {b} can only smother it.",
                "{b} shoulders arms; that one nipped back.", "{b} watches it go past the outside edge.",
                "No shot offered; a probing delivery outside off.", "{b} dead-bats it into the covers.",
                "Dot ball — {b} is tied down.", "Sharp bounce beats {b}'s attempted cut.",
                "{b} defends off the front foot to mid-off.", "{b} gets into line and blocks.",
                "{b} pushes it to cover-point; no run there.", "Beaten by the extra bounce — {b} is lucky.",
                "{b} plays inside the line and misses.", "Stifled appeal as the ball dies on the pitch.",
                "{b} is happy to leave that outside off.", "Short balls are becoming a problem — {b} can't connect.",
                "{b} pats it gently to the fielder at cover.", "A yorker and {b} digs it out.",
                "{b} drops to one knee and defends.", "The ball seams away and {b} withdraws the bat.",
                "Good length from the bowler — {b} can only block.", "{b} is rapped on the pads — but it's going down leg.",
                "Played with soft hands straight back to the bowler.", "{b} gets forward and smothers the spin.",
                "The bouncer sails through safely — {b} ducks just in time.", "Lovely outswing — {b} doesn't touch it.",
                "{b} watches it all the way through to the keeper's gloves.", "A brute of a delivery — {b} fends it away.",
                "{b} gets behind the line and pushes it back.", "Nothing doing for {b} — the fielding is tight.",
                "{b} covers up and blocks.", "The ball dies on the pitch — no run on offer.",
                "{b} lets it go and it bounces harmlessly through.", "A Play and a miss! {b} is beaten on the outside edge.",
                "Quick bouncer — {b} sees it late and lets it go.", "{b} is completely tied down here.")
    ONE_LINES = ("{b} works it into space for one.", "{b} taps it and they scamper through for a single.",
                "{b} nudges it into the leg side for one.", "Quick single — {b} and the non-striker cross.",
                "{b} steers it to the fielder and they take the run.",
                "{b} pushes into the off side for a quick single.", "{b} turns it off the hip for one.",
                "Soft hands from {b}; they dash through for a single.", "{b} works the ball behind square.",
                "{b} glances it fine and they take the easy run.", "Punched down the ground for a single.",
                "Nudged into the gap on the leg side; one taken.", "{b} drops it into no-man's land for a single.",
                "A gentle push and they scamper across.", "{b} tickles it round the corner for a single.",
                "Neatly worked through midwicket for one.", "{b} dabs it down to third man for a single.",
                "They take a quick single; good running between the wickets.",
                "{b} works it through mid-on for a single.", "A gentle dab and {b} is off the mark.",
                "{b} pushes it to point and sets off.", "Flicked off the pads for a quick single.",
                "{b} guides it down to third man.", "A careful push into the covers — one taken.",
                "Rotates the strike with a single to midwicket.", "{b} gets a thick edge but it drops safely for one.",
                "Crisp defence and they sprint through.", "{b} nudges into the gap at square leg.",
                "Off the pad and they sneak a bye-level single.", "Pushed into the off side and they cross quickly.",
                "{b} drops the wrists and pushes behind square.", "A single — {b} keeps the scoreboard ticking.",
                "{b} works it through the gap for one.", "Quick running from the batting pair.")
    TWO_LINES = ("{b} finds the gap and they come back for two.", "{b} places it well and they run two.",
                "Good running from {b} — two taken.", "{b} works the angle and picks up a couple.",
                "Driven through the gap; the sweeper keeps it to two.",
                "Turned into the deep and they hustle back for two.",
                "{b} splits the fielders and they push for two.", "Excellent placement — they run hard and get two.",
                "Clubbed into the deep but the fielder cuts it off; two runs.",
                "Flicked through square leg — the outfield slows it to two.",
                "They push hard and convert the single into a brace.",
                "{b} times it well through extra cover and they return for two.",
                "Driven wide of long-on — they settle for two.", "A firm push through the covers brings two.",
                "Hit to deep midwicket — the fielder charges in; two taken.",
                "{b} picks the gap and they run a comfortable pair.",
                "Pushed to long-off — good running for two.", "Crisp shot through the gap and they come back for the second.",
                "Worked through the on side — they push for two.", "{b} scampers back for a second; good running.",
                "A firm drive and the deep fielder keeps it to two.", "The sweeper chases — two runs.")
    THREE_LINES = ("Excellent running from {b}; three completed.", "{b} finds the gap in the deep — three runs.",
                  "Hard running gets {b} a third.", "They push for three! Brilliant running.",
                  "Drilled through the covers — the fielder chases and they take three.",
                  "Superb running turns two into three.", "The outfield is quick and they gamble for three.",
                  "{b} places it perfectly and they race through for three.",
                  "Punched through the covers and they run hard — three taken.",
                  "Hit to the deep — the fielder picks up and fires but they make three.",
                  "Driven down the ground and they push for the third.",
                  "Swept behind square — they sprint three.", "A firm push and they come back for three.",
                  "Through the infield and they take three with confident running.",
                  "Worked to the leg side boundary; three runs.", "Chased down by the deep fielder — three.")

    # Boundary shot descriptors, keyed by a coarse (side, height) zone
    # derived from this ball's actual line/length — the same values that
    # now also feed the outcome weights, so a yorker outside off really
    # does read as a yorker outside off, not a generic "drives through
    # cover" no matter what was actually bowled.
    FOUR_SHOTS = {
        ("off", "up"): ["drives it through extra cover", "threads it through cover for four",
                       "drives it wide of mid-off", "cracks it through the covers",
                       "drives on the up through the off side",
                       "lofts it over the infield through covers",
                       "punches a full delivery through extra cover",
                       "leans into a drive through the off side"],
        ("off", "down"): ["cuts it away through point", "carves it over backward point",
                         "slices it fine through third man", "runs it down to third man for four",
                         "guides it past the slip cordon",
                         "cuts it square and beats the fielder",
                         "steers it behind point for four",
                         "fends it off the back foot past gully"],
        ("leg", "up"): ["clips it through midwicket", "whips it away off the pads",
                       "flicks it through square leg", "drives it through the leg side gap",
                       "works it off the hip through midwicket",
                       "clips it off the toes through the on side",
                       "drives it through the gap between mid-on and midwicket",
                       "flicks it wristily through midwicket"],
        ("leg", "down"): ["pulls it away through square leg", "rocks back and pulls it fine",
                         "helps it round the corner for four", "swivels and pulls it through midwicket",
                         "tucks it off the back foot past square leg",
                         "glances it fine off the hips",
                         "pulls a short ball through the leg side",
                         "hooks it behind square for four"],
        ("straight", "up"): ["drives it straight down the ground", "strikes it back past the bowler",
                            "lofts it wide of long-on", "drives it straight back past the stumps",
                            "sends it back down the ground past the bowler",
                            "drives a full ball straight back for four",
                            "whips it past the bowler through mid-on",
                            "straight-drives it back past the bowler's outstretched hand"],
        ("straight", "down"): ["works it straight back past the bowler", "steers it into the gap at cover",
                              "guides it away off the back foot", "punches it down the ground off the back foot",
                              "dabs it into the gap at cover",
                              "steers it past the bowler for four",
                              "punches a length ball down the ground",
                              "works it off the back foot past the bowler"],
    }
    SIX_SHOTS = {
        ("off", "up"): ["smashes it back over the bowler's head", "lofts it high over extra cover",
                       "drives it big down the ground", "launches it over long-off",
                       "lifts it cleanly over the cover boundary",
                       "clears long-off with a magnificent lofted drive",
                       "sends it soaring over the off side boundary",
                       "cleans it up and deposits it over long-off"],
        ("off", "down"): ["cuts it away over backward point", "slashes it high over the covers",
                         "hacks it over point for six",
                         "slices it over the ropes at backward point",
                         "launches it over the point region",
                         "slashes hard and it sails over point"],
        ("leg", "up"): ["flicks it over midwicket for six", "clears the ropes over square leg",
                       "whips it over the leg side for maximum",
                       "swivels and lifts it over the leg side boundary",
                       "clips it over deep midwicket",
                       "slog-swept over deep midwicket for six"],
        ("leg", "down"): ["hooks it flat over square leg", "pulls it into the stands",
                         "rocks back and deposits it over midwicket",
                         "pulls a short ball into the crowd",
                         "hooks it over deep backward square",
                         "swivels and hammers it over the leg side"],
        ("straight", "up"): ["launches it back over long-on", "smashes it out of the ground",
                            "pumps it straight back over the bowler's head",
                            "lofts it straight back over long-on",
                            "sends it soaring straight down the ground",
                            "drives it straight back over the bowler for six"],
        ("straight", "down"): ["picks the length early and pulls it out of the park",
                              "rocks back and clears the rope over midwicket",
                              "slogs it straight back over the bowler's head",
                              "pulls it straight back over long-on",
                              "rocks back and launches it over the bowler",
                              "back-foot punch clears long-on by a mile"],
    }

    @staticmethod
    def _shot_zone(line: str, length: str) -> tuple[str, str]:
        side = "leg" if line == "Leg Stump" else "off" if line in ("Off Stump", "Wide") else "straight"
        height = "up" if length in ("Yorker", "Full") else "down"
        return side, height

    def _run_commentary(self, batter: dict[str, Any], runs: int, line: str = "Off Stump", length: str = "Good") -> str:
        b = batter["name"]
        if runs == 0: return self.rng.choice(self.DOT_LINES).format(b=b)
        if runs == 1: return self.rng.choice(self.ONE_LINES).format(b=b)
        if runs == 2: return self.rng.choice(self.TWO_LINES).format(b=b)
        if runs == 3: return self.rng.choice(self.THREE_LINES).format(b=b)
        zone = self._shot_zone(line, length)
        if runs == 4:
            shot = self.rng.choice(self.FOUR_SHOTS[zone])
            return f"FOUR! {b} {shot}."
        shot = self.rng.choice(self.SIX_SHOTS[zone])
        return f"SIX! {b} {shot}."

    BOWLED_LINES = ("{bo} uproots {b}'s middle stump.", "{bo} sends the off stump cartwheeling.",
                    "{bo} sneaks one through the gate to castle {b}.", "{bo} cleans {b} up with a beauty.",
                    "{bo} knocks over the off stump!", "Bowled through the gate — {b} had no answer.",
                    "A beauty from {bo} — {b} is a spectator as the stumps are disturbed.",
                    "{b} plays on! A thick inside edge crashes into the stumps.",
                    "{bo} strikes timber! {b} cannot believe it.",
                    "Off stump knocked back — {b} is on his way.",
                    "A thunderbolt from {bo} — the middle stump is flattened.",
                    "Late swing from {bo} and {b} is completely comprehended.",
                    "Pins it back and sends the off stump for a walk.",
                    "{bo} gets one to nip back and castle {b}.",
                    "An absolute jaffa from {bo} — {b} didn't pick the line.",
                    "The stumps are scattered — {bo} has a beauty!",
                    "Straightens off the deck and {b} is bowled neck and crop.",
                    "A brute of a delivery from {bo} — middle stump goes flying.",
                    "Inside edge from {b} and the stumps are shattered.",
                    "Yorker from {bo} — {b} is too late on it and the stumps are broken.")
    CAUGHT_LINES = ("{b} is caught at {f} off {bo}.", "{b} picks out {f} perfectly.",
                    "{b} top-edges it straight to {f}.", "{bo} induces the edge and {f} takes a good catch.",
                    "{b} slices it to {f} who holds on!", "{f} pouches it safely — {bo} has his wicket.",
                    "A leading edge and {f} takes a sharp catch.", "{b} edges it to {f} — gone!",
                    "Driven in the air and {f} takes a fine catch.", "{b} is caught behind off {bo}!",
                    "{f} dives forward and takes a brilliant catch!",
                    "Short ball does the trick — {b} is caught at {f}.",
                    "A thick outside edge flies to {f} — caught!",
                    "{b} tries to force it through the off side and finds {f}.",
                    "Straight down the throat of {f} — simple catch.",
                    "{b} skies it and {f} settles under it comfortably.",
                    "Nicked! {f} takes a low catch at second slip.",
                    "Punched in the air — {f} moves to his right and takes the catch.",
                    "{b} is caught and bowled by {bo}! He puts it down nicely.",
                    "A soft chip and {f} runs in from the outfield to claim it.",
                    "{f} holds on at long-on — the big shot doesn't pay off.",
                    "Thick edge and {f} pouches it at slip! What a catch!",
                    "Looped up and {b} drives it straight back to {f}.",
                    "A regulation catch for {f} at mid-off — {bo} celebrates.")
    LBW_LINES = ("{b} is trapped in front by {bo}.", "{b} is plumb in front — that's out lbw.",
                "{bo} pins {b} on the crease, given lbw.", "Rapped on the pads — {bo} appeals and up goes the finger.",
                "That is dead in front. {bo} wins the lbw appeal.",
                "Playing across the line — {b} is a dead man walking.",
                "{bo} strikes {b} on the knee roll right in front of middle.",
                "Coming back in and {b} is hit on the pads — given out!",
                "A big appeal and the umpire raises the finger — {b} is gone.",
                "Nipping back off the seam — {b} is trapped in front.",
                "Hitting the pads first — {bo} is convinced and so is the umpire.",
                "That has hit {b} in line with middle stump — out LBW!",
                "Going nowhere but back to the bowler — {bo} has {b} trapped.",
                "The ball sneaks through and hits {b} in front — given!")
    STUMPED_LINES = ("{b} is beaten in flight and stumped.", "Quick hands — {b} is stumped well outside the crease.",
                    "{b} is done by the turn and stumped in a flash.",
                    "Lured out of the crease and left stranded by the keeper.",
                    "Down the track and beaten — {b} is stumped by a mile.",
                    "Drift and turn do for {b} — stumped by a country mile.",
                    "The keeper whips the bails off — {b} is miles out of his ground.",
                    "Brilliant work behind the stumps — {b} is stumped!",
                    "{b} comes down the wicket and is beaten — the keeper does the rest.",
                    "Flighted delivery, {b} lunges forward, and the keeper is alert.",
                    "Sneaks it past the bat and the keeper takes the bails off in a flash.",
                    "Tossed up beautifully — {b} is nowhere near the crease when the stumps are broken.")
    RUN_OUT_LINES = ("Sharp fielding ends {b}'s innings.", "A direct hit ends {b}'s stay at the crease.",
                    "{b} is caught short by a brilliant piece of fielding.",
                    "A mix-up in the middle and {b} is run out.",
                    "Excellent work in the deep; {b} is well short of the crease.",
                    "Direct hit from the deep — {b} has to go.",
                    "A quick pick-up and throw — {b} is gone by a whisker!",
                    "Terrific fielding! The stumps are broken with {b} short of the crease.",
                    "A mix-up between the wickets and {b} pays the price.",
                    "The throw comes in and {b} is well out — run out!",
                    "One too many this time — the fielder's throw finds the stumps.",
                    "A brilliant relay from the deep — {b} is run out by a distance.")

    # Extras template pools — wide and no-ball commentary.
    WIDE_LINES = ("{bo} drifts too wide — the umpire signals wide.",
                  "A wide from {bo} — too far outside off for {b} to reach.",
                  "Straying down the leg side — wide called.",
                  "{bo} fires it wide of the stumps — that's a wide.",
                  "The umpire's arms go wide — a poor delivery from {bo}.",
                  "Too far outside off — {bo} can't find the line.")
    NOBALL_LINES = ("{bo} oversteps — no-ball called.",
                    "A no-ball from {bo} — the front foot is too far forward.",
                    "The umpire signals no-ball — {bo} has overstepped.",
                    "Height no-ball! {bo} has strangled one down the leg side.",
                    "{bo} bends his back too far — no-ball for height.",
                    "The big boot lands over the line — free hit coming.")
    # Byes — wicketkeeping depth misses.
    BYE_LINES = ("Through {keeper_name} — {byes} bye{s}!",
                 "The ball gets past {keeper_name} — {byes} bye{s}.",
                 "{keeper_name} can't get a glove on it — {byes} bye{s}.",
                 "Slips through {keeper_name}'s legs — {byes} bye{s}!",
                 "Wide of {keeper_name} and racing away — {byes} bye{s}.",
                 "Down the leg side and past {keeper_name} — {byes} bye{s}.")
    # Boundary saves by a covering fielder.
    BOUNDARY_SAVE_LINES = ("Well saved by {saver} in the deep! {commentary}",
                           "Brilliant effort from {saver} to cut it off! {commentary}",
                           "{saver} dives to his left and saves a certain boundary! {commentary}",
                           "Superb fielding by {saver} in the deep! {commentary}",
                           "That was heading for the rope but {saver} had other ideas! {commentary}")
    # Missed chance commentary pools.
    DROPPED_LINES = ("Dropped by {fielder_name}! A sitter goes down!",
                     "Spilled by {fielder_name}! That should have been taken!",
                     "{fielder_name} puts it down! A simple catch gone begging!",
                     "The catch goes down — {fielder_name} cannot believe it!")
    MISSED_STUMP_LINES = ("{fielder_name} misses the stumping chance.",
                          "A stumping opportunity goes begging — {fielder_name} is slow to collect.",
                          "The keeper fumbles — {fielder_name} should have had the bails off!",
                          "{fielder_name} can't gather cleanly — the stumping chance is lost.")
    MISSED_RUNOUT_LINES = ("{fielder_name} cannot complete the run-out.",
                           "A run-out chance goes awry — {fielder_name}'s throw is off target.",
                           "{fielder_name} misses the direct hit — {batter_name} survives!",
                           "The throw misses the stumps — {fielder_name} rues that one.")
    # Milestone commentary — centuries and fifties.
    CENTURY_LINES = ("CENTURY! {name} reaches three figures! A magnificent innings!",
                     "What a player! {name} brings up a well-deserved century!",
                     "100 up for {name}! The crowd rises to acknowledge a brilliant knock!",
                     "A landmark knock — {name} celebrates a splendid century!")
    FIFTY_LINES = ("FIFTY! {name} brings up a well-earned half-century.",
                   "Half-century for {name}! A knock to remember.",
                   "50 runs for {name} — a fine contribution to the team.",
                   "A superb fifty from {name} — he's in fine form today.")
    # Drinks break variants.
    DRINKS_LINES = ("Drinks break: both sides recover some energy.",
                    "A welcome drinks interval — the players take a breather.",
                    "The players gather for a drinks break — a chance to regroup.",
                    "Stumps are removed for the drinks break — time to rehydrate.",
                    "A brief pause for drinks — both teams catch their breath.")
    # Partnership landmark variants.
    PARTNERSHIP_LINES = ("Partnership of {runs} runs between {a} and {b}.",
                         "These two have put on {runs} together — superb batting.",
                         "A valuable stand of {runs} between {a} and {b}.",
                         "They've added {runs} for the wicket — {a} and {b} are in control.",
                         "A partnership worth {runs} and counting — {a} and {b} are combining well.")
    CENTURY_PARTNERSHIP_LINES = ("Century partnership! {runs} runs for this wicket!",
                                 "A magnificent 100-run stand! {a} and {b} have been superb!",
                                 "100 runs between them! {a} and {b} have built something special!",
                                 "A century stand! These two are putting on a masterclass!")
    # DRS review commentary.
    DRS_LINES = ("DRS: {message}",
                 "The big screen confirms it — {message}",
                 "A tense wait — the third umpire delivers: {message}",
                 "DRS review — {message}",
                 "Upstairs we go — the review result: {message}")
    # Session wrap-up (Test matches).
    SESSION_WRAP_LINES = ("End of {name}: {team} {runs}/{wickets} ({overs}, RR {rr:.2f}).",
                          "That's the session done. {team} finish on {runs}/{wickets} ({overs}, RR {rr:.2f}).",
                          "Close of the {session} session — {team} {runs}/{wickets} ({overs}, RR {rr:.2f}).",
                          "Stumps are drawn for the session — {team} {runs}/{wickets} ({overs}, RR {rr:.2f}).")
    # Maiden over commentary.
    MAIDEN_LINES = ("A maiden over from {bo} — dot, dot, dot.",
                    "Nothing doing for {b} — a maiden from {bo}.",
                    "Maiden over! {bo} strangles the run rate.",
                    "Dot after dot — {bo} bowls a superb maiden.",
                    "A wicket-maiden over from {bo}! The batter is under real pressure.",
                    "Tight bowling from {bo} — a deserved maiden.")

    def _wicket_commentary(self, batter: dict[str, Any], bowler: dict[str, Any], wicket_type: str, fielder: str | None) -> str:
        b, bo, f = batter["name"], bowler["name"], fielder or "the fielder"
        if wicket_type == "bowled": return f"BOWLED! {self.rng.choice(self.BOWLED_LINES).format(bo=bo, b=b)}"
        if wicket_type == "caught": return f"OUT! {self.rng.choice(self.CAUGHT_LINES).format(b=b, f=f, bo=bo)}"
        if wicket_type == "lbw": return f"LBW! {self.rng.choice(self.LBW_LINES).format(b=b, bo=bo)}"
        if wicket_type == "stumped": return f"STUMPED! {self.rng.choice(self.STUMPED_LINES).format(b=b, bo=bo)}"
        return f"RUN OUT! {self.rng.choice(self.RUN_OUT_LINES).format(b=b)}"

    def innings_complete(self) -> str | None:
        innings = self.current_innings
        if innings.wickets >= 10: return "all out"
        if innings.target and innings.runs >= innings.target: return "target reached"
        if self.format != "Test":
            max_balls = (self.rain_overs * self.balls_per_set if self.rain_overs else self.MAX_BALLS[self.format]) or 0
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
        original = self.overs_limit()
        available = max(5, min(original, self.rain_overs or original))
        resource = (1 - pow(2.718281828, -available / (original * .38)))
        full_resource = (1 - pow(2.718281828, -1 / .38))
        wickets_lost = self.current_innings.wickets if len(self.innings) >= 2 else 0
        wicket_adjustment = 1 + wickets_lost * .018
        return max(1, round(first_innings_score * resource / full_resource * wicket_adjustment) + 1)

    def apply_rain_reduction(self, overs_available: int) -> int:
        if self.format == "Test":
            raise ValueError("DLS only applies to limited-overs matches")
        maximum = self.overs_limit()
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
        self._comment(self.rng.choice(self.DRS_LINES).format(message=message), "milestone")
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
                item = asdict(line); item["overs"] = overs_text(line.balls, self.balls_per_set); item["economy"] = line.economy
                bowling.append(item)
        return {"team": state.batting_name, "runs": state.runs, "wickets": state.wickets,
                "overs": state.overs, "extras": dict(state.extras), "batting": batting,
                "bowling": bowling, "target": state.target, "end_reason": state.end_reason,
                "partnerships": list(state.partnerships), "fall_of_wickets": list(state.fall_of_wickets),
                "legal_balls": state.legal_balls, "session_data": list(state.session_data),
                "phase_data": list(state.phase_data), "momentum": state.momentum,
                "key_moments": list(state.key_moments), "momentum_history": list(state.momentum_history)}

    def match_status(self) -> str:
        if self.completed: return self.result
        innings = self.current_innings
        if innings.target:
            needed = max(0, innings.target - innings.runs)
            balls = max(0, ((self.rain_overs or self.overs_limit()) * self.balls_per_set) - innings.legal_balls) if self.format != "Test" else 0
            suffix = f" from {balls} balls" if self.format != "Test" else ""
            return f"{innings.batting_name} need {needed} runs{suffix}"
        if self.format == "Test" and len(self.innings) > 1:
            totals = self.team_totals; lead_team = max(totals, key=totals.get); lead = abs(totals[self.home_team_id] - totals[self.away_team_id])
            return f"{self.team_name(lead_team)} lead by {lead} runs" if lead else "Scores level"
        return f"{innings.batting_name} {innings.runs}/{innings.wickets} after {innings.overs} {self.unit_label}"

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
        maximum = (self.rain_overs or self.overs_limit()) * self.balls_per_set if self.format != "Test" else max(innings.legal_balls, 540)
        rate = innings.runs * self.balls_per_set / max(self.balls_per_set * 2, innings.legal_balls)
        wicket_factor = max(.62, 1 - innings.wickets * .035)
        phase_boost = 1.0 + max(0, 10 - innings.wickets) * (.012 if self.format != "Test" else .002)
        return max(innings.runs, round(innings.runs + (maximum - innings.legal_balls) / self.balls_per_set * rate * wicket_factor * phase_boost))

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

        maximum = (self.rain_overs or self.overs_limit()) * self.balls_per_set
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
                baseline = (85 if self.format == "T10" else 135 if self.format == "Hundred" else 155 if self.format == "T20" else 255) + (opposition_quality - batting_quality) * 1.1
                opposing_score = rng.gauss(baseline, 16 if self.format == "T10" else 22 if self.format == "Hundred" else 25 if self.format == "T20" else 42)
                batting_won = score > opposing_score
                if abs(score - opposing_score) < .5: ties += 1
            winner = innings.batting_team if batting_won else innings.bowling_team
            wins += int(winner == team_id)
        return max(1, min(99, round((wins + ties * .5) * 100 / simulations)))

    def performance_updates(self) -> dict[int, dict[str, float]]:
        """Return bounded post-match form/development deltas plus an
        absolute post-match fatigue reading, for persistence.

        Fatigue is the complement of self.energy (which _initialise_energy
        already derives partly from the player's *incoming* fatigue) —
        so it round-trips: today's post-match tiredness becomes tomorrow's
        starting-energy penalty, instead of every player starting every
        match fully fresh regardless of recent workload."""
        updates: dict[int, dict[str, float]] = {}
        for innings in self.innings:
            for player in innings.batting_order:
                line = innings.batters[int(player["id"])]
                batting_score = line.runs + line.runs * 100 / max(1, line.balls) * .12
                form_delta = max(-5.0, min(5.0, (batting_score - 38) / 14))
                potential = float(player.get("potential", player.get("overall", 50)))
                overall = float(player.get("overall", 50)); age = int(player.get("age", 27))
                overall_delta = post_match_delta(age, int(potential), int(overall))
                updates[int(player["id"])] = {"form": round(form_delta, 2), "overall": round(overall_delta, 2)}
            for player in innings.bowling_squad:
                line = innings.bowlers[int(player["id"])]
                if not line.balls: continue
                bowling_delta = max(-5.0, min(5.0, line.wickets * 1.4 + (6.5 - line.economy) * .45 - 1.0))
                record = updates.setdefault(int(player["id"]), {"form": 0.0, "overall": 0.0})
                record["form"] = round(max(-5.0, min(5.0, record["form"] + bowling_delta)), 2)
        for player_id, energy in self.energy.items():
            record = updates.setdefault(player_id, {"form": 0.0, "overall": 0.0})
            record["fatigue"] = round(max(0.0, min(100.0, 100.0 - energy)), 1)
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
            self.drawn = self.format == "Test"
            self.completed = True
        return self.result

    def to_dict(self) -> dict[str, Any]:
        """Create a JSON-safe match result/save snapshot."""
        return {
            "format": self.format, "pitch": self.pitch, "weather": self.weather,
            "home_team": self.home_team_id, "away_team": self.away_team_id,
            "completed": self.completed, "winner_id": self.winner_id, "drawn": self.drawn, "result": self.result,
            "day": self.day, "session": self.session, "status": self.match_status(),
            "innings": [self.scorecard(i) for i in range(len(self.innings))],
            "super_over": dict(self.super_over_scores), "commentary": list(self.commentary),
            "key_moments": self.key_moments(),
            "injuries": list(self.injuries), "performance_updates": self.performance_updates(),
            "energy": {str(pid): round(value, 1) for pid, value in self.energy.items()},
        }

    def key_moments(self) -> list[dict[str, Any]]:
        """Extract meaningful events from commentary for analytics display."""
        moments: list[dict[str, Any]] = []
        for entry in self.commentary:
            kind = entry.get("kind", "")
            if kind in ("wicket", "milestone") or ("FOUR!" in entry["text"]) or ("SIX!" in entry["text"]):
                moments.append(entry)
        return moments[-50:]


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
