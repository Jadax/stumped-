"""SQLite persistence and world generation for Cricket Manager.

The module has no third-party dependencies. Importing it does not modify disk;
call :func:`initialise_database` from the application entry point instead.
Complex attribute groups are stored as JSON strings while commonly queried
ratings remain normal SQLite columns.
"""

from __future__ import annotations

import json
import random
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence
from src.models.player import ATTRIBUTE_DEFAULTS, BOWLING_STYLES, expanded_groups, infer_bowling_style
from src.models.player_generation import wage_for_player


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "cricket_manager.db"

ROLE_WEIGHTS = {
    "Batsman": {"batting": 0.62, "bowling": 0.03, "fielding": 0.15, "mental": 0.20},
    "Bowler": {"batting": 0.05, "bowling": 0.60, "fielding": 0.15, "mental": 0.20},
    "All-Rounder": {"batting": 0.34, "bowling": 0.34, "fielding": 0.14, "mental": 0.18},
    "Wicketkeeper": {"batting": 0.45, "bowling": 0.00, "fielding": 0.37, "mental": 0.18},
}

_LEGACY_NAMES = {
    "English": (
        ["Oliver", "George", "Harry", "Jack", "Noah", "Charlie", "Thomas", "James", "Ben", "Sam"],
        ["Ashford", "Bellamy", "Carver", "Denshaw", "Elwick", "Fenner", "Grayson", "Hartley", "Iverson", "Jowett"],
    ),
    "Australian": (
        ["Liam", "Cooper", "Mitchell", "Josh", "Travis", "Cameron", "Marcus", "Nathan", "Alex", "Glenn"],
        ["Baxter", "Corwin", "Dacre", "Elston", "Farrow", "Grady", "Huxley", "Irwin", "Jansen", "Kells"],
    ),
    "Indian": (
        ["Arjun", "Rohan", "Viraj", "Aarav", "Shubham", "Ishan", "Rahul", "Dev", "Yash", "Ravi"],
        ["Ahuja", "Bhasin", "Chawla", "Dhamar", "Gokhale", "Kohar", "Luthra", "Madan", "Narang", "Sarin"],
    ),
    "Pakistani": (
        ["Ali", "Babar", "Fakhar", "Haris", "Imran", "Mohammad", "Saad", "Shadab", "Usman", "Zain"],
        ["Abbasi", "Bukhari", "Darzi", "Farooqi", "Haideri", "Jafri", "Kashif", "Nizami", "Qadri", "Tariq"],
    ),
    "South African": (
        ["Aiden", "David", "Marco", "Kagiso", "Reeza", "Ruan", "Tristan", "Wiaan", "Kyle", "Lutho"],
        ["Aucamp", "Bekker", "Cronjeveld", "Du Toit", "Esterzen", "Fourie", "Greeff", "Jordaan", "Louw", "Meyerhoff"],
    ),
    "New Zealander": (
        ["Finn", "Kane", "Rachin", "Daryl", "Tom", "Will", "Jacob", "Matt", "Henry", "Lockie"],
        ["Aldridge", "Bramwell", "Carterton", "Drummond", "Everett", "Falconer", "Gilmour", "Hawke", "Kauri", "Rutherford"],
    ),
    "West Indian": (
        ["Akeem", "Brandon", "Jermaine", "Keacy", "Nicholas", "Rovman", "Shai", "Shimron", "Alzarri", "Jayden"],
        ["Baptiste", "Cato", "Drakeson", "Francis", "Gittens", "Haynesworth", "Isaacs", "Lovelace", "Mercer", "Prescod"],
    ),
}


def _load_name_pools() -> dict[str, tuple[list[str], list[str]]]:
    """Load editable, country-authentic pools with legacy-save aliases."""
    path = PROJECT_ROOT / "src" / "data" / "names.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        pools = {country: (list(values["first_names"]), list(values["last_names"])) for country, values in raw.items()}
    except (OSError, ValueError, KeyError, TypeError):
        return dict(_LEGACY_NAMES)
    aliases = {"English": "England", "Australian": "Australia", "Indian": "India", "Pakistani": "Pakistan",
               "South African": "South Africa", "New Zealander": "New Zealand", "West Indian": "West Indies"}
    for alias, country in aliases.items():
        pools[alias] = pools[country]
    return pools


NAMES = _load_name_pools()

TEAM_DEFINITIONS = [
    ("Manchester Mavericks", 1, "English"),
    ("Sydney Sixers", 1, "Australian"),
    ("Mumbai Tigers", 1, "Indian"),
    ("Lahore Falcons", 1, "Pakistani"),
    ("Cape Town Cobras", 1, "South African"),
    ("Auckland Aces", 1, "New Zealander"),
    ("Kingston Kings", 1, "West Indian"),
    ("Birmingham Bears", 1, "English"),
    ("Melbourne Mariners", 2, "Australian"),
    ("Delhi Dynamos", 2, "Indian"),
    ("Karachi Knights", 2, "Pakistani"),
    ("Johannesburg Giants", 2, "South African"),
    ("Wellington Wolves", 2, "New Zealander"),
    ("Barbados Breakers", 2, "West Indian"),
    ("Leeds Lightning", 2, "English"),
    ("Perth Pioneers", 2, "Australian"),
    # IDs 1-16 are intentionally stable for existing careers. Expansion clubs
    # are appended so v0.8 saves migrate without changing fixture ownership.
    ("Chennai Chargers", 1, "Indian"),
    ("Brisbane Blaze", 1, "Australian"),
    ("Pretoria Pioneers", 1, "South African"),
    ("Christchurch Crusaders", 1, "New Zealander"),
    ("Nottingham Outlaws", 2, "English"),
    ("Hyderabad Hawks", 2, "Indian"),
    ("Rawalpindi Royals", 2, "Pakistani"),
    ("Trinidad Tridents", 2, "West Indian"),
]


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    """Round and constrain an attribute to cricket's 0–100 scale."""
    return max(low, min(high, int(round(value))))


def _group_average(group: Mapping[str, int]) -> float:
    return sum(group.values()) / max(1, len(group))


def calculate_overall(
    role: str,
    batting: Mapping[str, int],
    bowling: Mapping[str, int],
    fielding: Mapping[str, int],
    mental: Mapping[str, int],
) -> int:
    """Calculate a role-aware overall rating from every attribute group."""
    weights = ROLE_WEIGHTS[role]
    score = (
        _group_average(batting) * weights["batting"]
        + _group_average(bowling) * weights["bowling"]
        + _group_average(fielding) * weights["fielding"]
        + _group_average(mental) * weights["mental"]
    )
    return clamp(score)


def _age_for_roster_slot(slot: int, rng: random.Random) -> int:
    """Guarantee academy players while retaining a realistic senior age curve."""
    if slot < 4:
        return rng.randint(16, 19)
    roll = rng.random()
    if roll < 0.67:
        return rng.randint(20, 28)
    if roll < 0.94:
        return rng.randint(29, 35)
    return rng.randint(36, 40)


def _team_quality_modifier(cash: int, division: int) -> float:
    """A club's own cash (already randomised per-team at seed time within
    its division's range) becomes a small target-rating offset — richer
    clubs field statistically stronger squads instead of every club in a
    division sharing one identical distribution. +/-5 points at the
    division's own cash extremes, matching this project's existing
    finance-depth theme rather than inventing a separate reputation stat."""
    cash_lo, cash_hi = (8_000_000, 15_000_000) if division == 1 else (3_000_000, 8_000_000)
    normalised = (cash - cash_lo) / (cash_hi - cash_lo)
    return (max(0.0, min(1.0, normalised)) - 0.5) * 10


def _target_rating(division: int, age: int, rng: random.Random, team_modifier: float = 0.0) -> float:
    """Draw a current-ability target centred near 70 (D1) or 55 (D2),
    nudged by the club's own relative wealth within its division."""
    base = 70 if division == 1 else 55
    base += team_modifier
    age_modifier = -13 if age < 18 else -8 if age < 20 else 0
    if age > 35:
        age_modifier -= (age - 35) * 1.7

    # Most players sit near their league mean, with a deliberately tiny elite tail.
    target = rng.gauss(base + age_modifier, 7.0)
    rarity = rng.random()
    if rarity < 0.004:
        target = rng.uniform(96, 99)
    elif rarity < 0.025:
        target = rng.uniform(86, 95)
    elif rarity < 0.10:
        target = rng.uniform(75, 85)
    return max(22, min(99, target))


def _youth_current_and_potential(academy_level: int, rng: random.Random) -> tuple[int, int]:
    """A 16-year-old's current ability and ceiling — previously flat
    `randint(20, 50)`/`randint(40, 85)` rolls with no rarity structure,
    meaning genuine wonderkids (85+ potential) were as common as merely
    promising prospects. Mirrors `_target_rating`'s deliberate
    mostly-average-with-a-tiny-elite-tail shape instead."""
    current = clamp(rng.gauss(28 + academy_level * 1.5, 6))
    rarity = rng.random()
    if rarity < 0.01:
        potential = rng.uniform(88, 97)
    elif rarity < 0.05:
        potential = rng.uniform(78, 87)
    elif rarity < 0.20:
        potential = rng.uniform(66, 77)
    else:
        potential = rng.gauss(50 + academy_level * 2, 9)
    return current, clamp(max(current, potential))


def _attribute(rng: random.Random, centre: float, spread: float = 7.0) -> int:
    return clamp(rng.gauss(centre, spread))


def _make_attributes(role: str, target: float, age: int, rng: random.Random) -> tuple[dict, dict, dict, dict]:
    """Build varied skills whose weighted overall remains close to target."""
    off_skill = max(12, target - rng.uniform(25, 38))
    batting_centre = target if role in {"Batsman", "All-Rounder", "Wicketkeeper"} else off_skill
    bowling_centre = target if role in {"Bowler", "All-Rounder"} else off_skill
    fielding_centre = target + (5 if role == "Wicketkeeper" else -2)
    experience_penalty = max(0, 25 - age) * 1.25
    mental_centre = target - experience_penalty / 3

    batting = {
        "attack": _attribute(rng, batting_centre),
        "defence": _attribute(rng, batting_centre),
        "technique_vs_pace": _attribute(rng, batting_centre),
        "technique_vs_spin": _attribute(rng, batting_centre),
        "concentration": _attribute(rng, batting_centre),
        "power": _attribute(rng, batting_centre + (3 if role == "All-Rounder" else 0)),
        "timing": _attribute(rng, batting_centre),
        "running": _attribute(rng, batting_centre + (4 if age < 29 else -3)),
    }
    bowling = {
        "pace": _attribute(rng, bowling_centre),
        "accuracy": _attribute(rng, bowling_centre),
        "variation": _attribute(rng, bowling_centre),
        "stamina": _attribute(rng, bowling_centre),
        "swing_or_spin": _attribute(rng, bowling_centre),
        "control": _attribute(rng, bowling_centre),
        "deception": _attribute(rng, bowling_centre),
    }
    fielding = {
        "catching": _attribute(rng, fielding_centre),
        "throwing": _attribute(rng, fielding_centre),
        "reflexes": _attribute(rng, fielding_centre + (6 if role == "Wicketkeeper" else 0)),
        "agility": _attribute(rng, fielding_centre + (3 if age < 28 else -2)),
        "keeping": _attribute(rng, fielding_centre + 8 if role == "Wicketkeeper" else max(15, off_skill - 15)),
        "ground_fielding": _attribute(rng, fielding_centre),
    }
    mental = {
        "experience": _attribute(rng, min(96, mental_centre + max(0, age - 20) * 1.5)),
        "consistency": _attribute(rng, mental_centre),
        "big_match": _attribute(rng, mental_centre),
        "fitness": _attribute(rng, target + (4 if age < 30 else -(age - 29) * 1.5)),
        "morale": _attribute(rng, target, 10),
        "endurance": _attribute(rng, target + (4 if age < 29 else -3)),
        "leadership": _attribute(rng, mental_centre + max(0, age - 25) * .5),
    }
    return batting, bowling, fielding, mental


def _player_name(nationality: str, used_names: set[str], rng: random.Random) -> str:
    first_names, surnames = NAMES[nationality]
    for _ in range(60):
        candidate = f"{rng.choice(first_names)} {rng.choice(surnames)}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
    candidate = f"{rng.choice(first_names)} {rng.choice(surnames)} {len(used_names) + 1}"
    used_names.add(candidate)
    return candidate


def generate_player(
    team_id: int,
    division: int,
    home_nationality: str,
    roster_slot: int,
    rng: random.Random,
    used_names: set[str],
    team_modifier: float = 0.0,
) -> dict[str, Any]:
    """Generate one complete player record suitable for database insertion."""
    role_cycle = ["Batsman"] * 9 + ["Bowler"] * 8 + ["All-Rounder"] * 5 + ["Wicketkeeper"] * 3
    role = role_cycle[roster_slot % len(role_cycle)]
    age = _age_for_roster_slot(roster_slot, rng)
    nationality = home_nationality if rng.random() < 0.76 else rng.choice(list(NAMES))
    target = _target_rating(division, age, rng, team_modifier)
    batting, bowling, fielding, mental = _make_attributes(role, target, age, rng)
    overall = calculate_overall(role, batting, bowling, fielding, mental)

    growth_window = rng.randint(10, 28) if age < 21 else rng.randint(3, 14)
    if age >= 30:
        growth_window = rng.randint(0, 6)
    potential = clamp(max(overall, overall + growth_window))
    form = clamp(rng.gauss(55, 12))
    wage = wage_for_player(overall, age, role, potential, division)
    contract_years = rng.randint(1, 4)
    bio = f"A {age}-year-old {nationality.lower()} {role.lower()} with {potential} potential."
    return {
        "name": _player_name(nationality, used_names, rng),
        "age": age,
        "nationality": nationality,
        "role": role,
        "batting_json": json.dumps(batting, sort_keys=True),
        "bowling_json": json.dumps(bowling, sort_keys=True),
        "fielding_json": json.dumps(fielding, sort_keys=True),
        "mental_json": json.dumps(mental, sort_keys=True),
        "physical_json": json.dumps({"fitness": mental["fitness"], "endurance": mental["endurance"],
                                      "speed": fielding["agility"], "agility": fielding["agility"],
                                      "strength": clamp((mental["fitness"] + batting["power"]) / 2)}, sort_keys=True),
        "overall": overall,
        "form": form,
        "potential": potential,
        "team_id": team_id,
        "contract_years_remaining": contract_years,
        "wage": wage,
        "bio": bio,
        "bowling_style": infer_bowling_style({"id": roster_slot + team_id * 100, "bowling": bowling}),
        "batting_aggression": clamp(1 + batting["attack"] / 12, 1, 10),
        "bowling_aggression": clamp(1 + bowling["pace"] / 12, 1, 10),
    }


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    division INTEGER NOT NULL CHECK (division IN (1, 2)),
    cash INTEGER NOT NULL,
    stadium_capacity INTEGER NOT NULL,
    training_level INTEGER NOT NULL DEFAULT 1 CHECK (training_level BETWEEN 1 AND 5),
    medical_level INTEGER NOT NULL DEFAULT 1 CHECK (medical_level BETWEEN 1 AND 5),
    academy_level INTEGER NOT NULL DEFAULT 1 CHECK (academy_level BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age BETWEEN 16 AND 45),
    nationality TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Batsman', 'Bowler', 'All-Rounder', 'Wicketkeeper')),
    batting_json TEXT NOT NULL CHECK (json_valid(batting_json)),
    bowling_json TEXT NOT NULL CHECK (json_valid(bowling_json)),
    fielding_json TEXT NOT NULL CHECK (json_valid(fielding_json)),
    mental_json TEXT NOT NULL CHECK (json_valid(mental_json)),
    physical_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(physical_json)),
    overall INTEGER NOT NULL CHECK (overall BETWEEN 0 AND 100),
    form INTEGER NOT NULL CHECK (form BETWEEN 0 AND 100),
    potential INTEGER NOT NULL CHECK (potential BETWEEN 0 AND 100),
    team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    contract_years_remaining INTEGER NOT NULL DEFAULT 1,
    wage INTEGER NOT NULL DEFAULT 0,
    bio TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS player_records (
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    context TEXT NOT NULL CHECK(context IN ('League','Cup','Friendly','International')),
    record_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(record_json)),
    PRIMARY KEY(player_id, context)
);
CREATE TABLE IF NOT EXISTS player_form_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    match_date TEXT NOT NULL, performance REAL NOT NULL, context TEXT NOT NULL DEFAULT 'League'
);
CREATE TABLE IF NOT EXISTS player_match_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    match_id INTEGER, innings INTEGER NOT NULL DEFAULT 1, event_type TEXT NOT NULL,
    x REAL NOT NULL, y REAL NOT NULL, runs INTEGER NOT NULL DEFAULT 0, wicket INTEGER NOT NULL DEFAULT 0
);

-- No FK to players(id): the whole point of a legend row is that it
-- outlives the deleted players row (retirement removes the original,
-- ON DELETE CASCADE would otherwise wipe player_records at the same
-- time, so a snapshot is taken into career_record_json first).
CREATE TABLE IF NOT EXISTS legends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    nationality TEXT NOT NULL,
    role TEXT NOT NULL,
    final_team_id INTEGER,
    final_team_name TEXT NOT NULL DEFAULT '',
    final_overall INTEGER NOT NULL,
    retired_age INTEGER NOT NULL,
    retired_season INTEGER NOT NULL,
    retired_on TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT 'retired' CHECK (reason IN ('retired', 'released')),
    became_staff INTEGER NOT NULL DEFAULT 0,
    career_record_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(career_record_json))
);
CREATE INDEX IF NOT EXISTS idx_legends_nationality ON legends(nationality);

-- One row per club per season, written at rollover. top_scorer/top_wicket_taker
-- are that season's contribution only (diffed against a baseline snapshot of
-- cumulative player_records taken at the previous rollover), not career totals.
CREATE TABLE IF NOT EXISTS season_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    position INTEGER,
    played INTEGER NOT NULL DEFAULT 0,
    won INTEGER NOT NULL DEFAULT 0,
    lost INTEGER NOT NULL DEFAULT 0,
    top_scorer_name TEXT NOT NULL DEFAULT '',
    top_scorer_runs INTEGER NOT NULL DEFAULT 0,
    top_wicket_taker_name TEXT NOT NULL DEFAULT '',
    top_wicket_taker_wickets INTEGER NOT NULL DEFAULT 0,
    recorded_on TEXT NOT NULL,
    UNIQUE(team_id, season)
);
CREATE INDEX IF NOT EXISTS idx_season_records_team ON season_records(team_id);

CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_players_role ON players(role);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    home_team INTEGER NOT NULL REFERENCES teams(id),
    away_team INTEGER NOT NULL REFERENCES teams(id),
    format TEXT NOT NULL CHECK (format IN ('T20', 'ODI', 'Test')),
    date TEXT NOT NULL,
    venue TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
    result_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(result_json))
);

CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    season INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS league_standings (
    competition_id INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    played INTEGER NOT NULL DEFAULT 0,
    won INTEGER NOT NULL DEFAULT 0,
    lost INTEGER NOT NULL DEFAULT 0,
    tied INTEGER NOT NULL DEFAULT 0,
    points INTEGER NOT NULL DEFAULT 0,
    net_run_rate REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (competition_id, team_id)
);

CREATE TABLE IF NOT EXISTS transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES players(id),
    from_team INTEGER REFERENCES teams(id),
    to_team INTEGER REFERENCES teams(id),
    fee INTEGER NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_data (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_team_id INTEGER NOT NULL REFERENCES teams(id),
    current_date TEXT NOT NULL,
    game_speed TEXT NOT NULL DEFAULT 'Normal',
    sound_on INTEGER NOT NULL DEFAULT 1 CHECK (sound_on IN (0, 1)),
    master_volume INTEGER NOT NULL DEFAULT 70 CHECK (master_volume BETWEEN 0 AND 100),
    resolution TEXT NOT NULL DEFAULT '1280x720',
    auto_save_frequency TEXT NOT NULL DEFAULT 'Monthly',
    currency TEXT NOT NULL DEFAULT 'GBP'
);

CREATE TABLE IF NOT EXISTS game_state (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL CHECK (json_valid(value_json)),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inbox_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    read INTEGER NOT NULL DEFAULT 0 CHECK (read IN (0, 1)),
    action_required INTEGER NOT NULL DEFAULT 0 CHECK (action_required IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_inbox_timestamp ON inbox_messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_inbox_unread ON inbox_messages(read);

CREATE TABLE IF NOT EXISTS financial_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('INCOME', 'EXPENSE')),
    amount INTEGER NOT NULL CHECK (amount >= 0),
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS training_assignments (
    player_id INTEGER PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,
    focus TEXT NOT NULL DEFAULT 'None',
    progress_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(progress_json)),
    last_trained TEXT
);

CREATE TABLE IF NOT EXISTS transfer_offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    from_team INTEGER REFERENCES teams(id),
    to_team INTEGER REFERENCES teams(id),
    fee INTEGER NOT NULL,
    weekly_wage INTEGER NOT NULL DEFAULT 0,
    offer_type TEXT NOT NULL CHECK (offer_type IN ('INCOMING', 'OUTGOING')),
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS facility_upgrades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    facility TEXT NOT NULL,
    target_level INTEGER NOT NULL,
    cost INTEGER NOT NULL,
    completion_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'BUILDING'
);

CREATE TABLE IF NOT EXISTS sponsorships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    sponsor_name TEXT NOT NULL,
    monthly_value INTEGER NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS injuries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    severity TEXT NOT NULL CHECK (severity IN ('Minor', 'Moderate', 'Major')),
    start_date TEXT NOT NULL,
    return_date TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    nationality TEXT NOT NULL,
    role TEXT NOT NULL,
    group_name TEXT NOT NULL CHECK (group_name IN ('Coaching', 'Medical', 'Scouting')),
    attributes_json TEXT NOT NULL,
    wage INTEGER NOT NULL DEFAULT 500,
    contract_years_remaining INTEGER NOT NULL DEFAULT 2,
    assignment TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS staff_transfer_offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    from_team INTEGER NOT NULL REFERENCES teams(id),
    to_team INTEGER NOT NULL REFERENCES teams(id),
    fee INTEGER NOT NULL,
    wage INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'FAILED')),
    created_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scouting_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    scout_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    target_player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    days_remaining INTEGER NOT NULL,
    total_days INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'COMPLETE')),
    estimated_overall INTEGER,
    estimated_potential INTEGER,
    confidence INTEGER,
    created_date TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_financial_team_date ON financial_log(team_id, date);
CREATE INDEX IF NOT EXISTS idx_transfer_offer_team ON transfer_offers(to_team, from_team, status);
CREATE INDEX IF NOT EXISTS idx_scouting_assignment_team ON scouting_assignments(team_id, status);
CREATE INDEX IF NOT EXISTS idx_injuries_player_active ON injuries(player_id, active);
CREATE INDEX IF NOT EXISTS idx_staff_team_group ON staff(team_id, group_name);
CREATE INDEX IF NOT EXISTS idx_staff_offer_team ON staff_transfer_offers(to_team, from_team, status);
"""


@contextmanager
def connect(database_path: str | Path = DEFAULT_DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    """Open a transaction-safe connection whose rows support name lookup."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_tables(connection: sqlite3.Connection) -> None:
    """Create or safely migrate the Phase 1 tables."""
    connection.executescript(SCHEMA)
    _ensure_column(connection, "teams", "ticket_price", "INTEGER NOT NULL DEFAULT 24")
    _ensure_column(connection, "teams", "stadium_level", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(connection, "teams", "commercial_level", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(connection, "teams", "scouting_level", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(connection, "teams", "grounds_level", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(connection, "teams", "country_id", "TEXT NOT NULL DEFAULT 'england'")
    _ensure_column(connection, "players", "transfer_listed", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "players", "academy_squad", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "players", "physical_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "players", "bowling_style", "TEXT NOT NULL DEFAULT 'Medium'")
    _ensure_column(connection, "players", "batting_aggression", "INTEGER NOT NULL DEFAULT 5")
    _ensure_column(connection, "players", "bowling_aggression", "INTEGER NOT NULL DEFAULT 5")
    _ensure_column(connection, "players", "fatigue", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "training_assignments", "intensity", "TEXT NOT NULL DEFAULT 'Normal'")
    _ensure_column(connection, "training_assignments", "days_json", "TEXT NOT NULL DEFAULT '[0,2,4]'")
    _ensure_column(connection, "matches", "competition_id", "INTEGER REFERENCES competitions(id)")
    _ensure_column(connection, "matches", "round_name", "TEXT NOT NULL DEFAULT 'League'")
    _ensure_column(connection, "user_data", "master_volume", "INTEGER NOT NULL DEFAULT 70 CHECK (master_volume BETWEEN 0 AND 100)")
    _ensure_column(connection, "user_data", "currency", "TEXT NOT NULL DEFAULT 'GBP'")
    _ensure_column(connection, "competitions", "tournament_id", "INTEGER REFERENCES custom_tournaments(id)")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS custom_tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            format TEXT NOT NULL CHECK (format IN ('T10','T20','ODI','Hundred','Test')),
            season INTEGER NOT NULL,
            groups_json TEXT NOT NULL,
            advance_per_group INTEGER NOT NULL DEFAULT 2,
            status TEXT NOT NULL DEFAULT 'group_stage' CHECK (status IN ('group_stage','knockout','complete'))
        );
    """)
    _rebuild_matches_format_if_needed(connection)
    _rebuild_custom_tournaments_format_if_needed(connection)
    connection.executescript("""
        CREATE INDEX IF NOT EXISTS idx_players_team_overall ON players(team_id, overall DESC);
        CREATE INDEX IF NOT EXISTS idx_players_team_age ON players(team_id, age);
        CREATE INDEX IF NOT EXISTS idx_matches_date_complete ON matches(date, completed);
        CREATE INDEX IF NOT EXISTS idx_matches_home_date ON matches(home_team, date);
        CREATE INDEX IF NOT EXISTS idx_matches_away_date ON matches(away_team, date);
        CREATE INDEX IF NOT EXISTS idx_standings_team ON league_standings(team_id, competition_id);
        CREATE INDEX IF NOT EXISTS idx_transfers_player_status ON transfers(player_id, status);
        CREATE INDEX IF NOT EXISTS idx_training_player_focus ON training_assignments(player_id, focus);
        CREATE INDEX IF NOT EXISTS idx_facility_team_status ON facility_upgrades(team_id, status);
        CREATE INDEX IF NOT EXISTS idx_form_player_date ON player_form_history(player_id, match_date);
        CREATE INDEX IF NOT EXISTS idx_events_player_type ON player_match_events(player_id, event_type);
    """)
    country_aliases = {"English": "england", "Australian": "australia", "Indian": "india",
                       "Pakistani": "pakistan", "South African": "south_africa",
                       "New Zealander": "new_zealand", "West Indian": "west_indies"}
    country_ids = [country_aliases[nationality] for _, _, nationality in TEAM_DEFINITIONS]
    connection.executemany("UPDATE teams SET country_id=? WHERE id=?", [(country, index + 1) for index, country in enumerate(country_ids)])
    _migrate_expanded_players(connection)


def _migrate_expanded_players(connection: sqlite3.Connection) -> None:
    """Fill new attributes deterministically without altering established skills."""
    for row in connection.execute("SELECT * FROM players").fetchall():
        raw = dict(row)
        for group in ("batting", "bowling", "fielding", "mental", "physical"):
            raw[group] = json.loads(raw.get(f"{group}_json") or "{}")
        groups = expanded_groups(raw)
        connection.execute("""UPDATE players SET batting_json=?,bowling_json=?,fielding_json=?,mental_json=?,physical_json=?,
            bowling_style=? WHERE id=?""", (json.dumps(groups["batting"]),json.dumps(groups["bowling"]),
            json.dumps(groups["fielding"]),json.dumps(groups["mental"]),json.dumps(groups["physical"]),
            infer_bowling_style(raw),row["id"]))
        connection.executemany("INSERT OR IGNORE INTO player_records(player_id,context,record_json) VALUES (?,?, '{}')",
                               [(row["id"], context) for context in ("League","Cup","Friendly","International")])


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    """Add a column once when opening saves created by an earlier phase."""
    existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _rebuild_matches_format_if_needed(connection: sqlite3.Connection) -> None:
    """Safely add modern limited-overs formats to existing save constraints."""
    info = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='matches'").fetchone()
    if not info:
        return
    ddl = info[0]
    if "'Hundred'" in ddl:
        return
    new_ddl = ddl.replace(
        "CHECK (format IN ('T20', 'ODI', 'Test'))",
        "CHECK (format IN ('T10', 'T20', 'ODI', 'Hundred', 'Test'))",
    )
    new_ddl = new_ddl.replace(
        "CHECK (format IN ('T10','T20','ODI','Test'))",
        "CHECK (format IN ('T10','T20','ODI','Hundred','Test'))",
    )
    connection.executescript("""
        PRAGMA foreign_keys=OFF;
        ALTER TABLE matches RENAME TO matches_old;
        """ + new_ddl + """;
        INSERT INTO matches SELECT * FROM matches_old;
        DROP TABLE matches_old;
        PRAGMA foreign_keys=ON;
    """)


def _rebuild_custom_tournaments_format_if_needed(connection: sqlite3.Connection) -> None:
    """Extend legacy custom-tournament saves without discarding brackets."""
    info = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='custom_tournaments'").fetchone()
    if not info or "'Hundred'" in info[0]:
        return
    ddl = info[0]
    new_ddl = ddl.replace(
        "CHECK (format IN ('T10','T20','ODI','Test'))",
        "CHECK (format IN ('T10','T20','ODI','Hundred','Test'))",
    )
    if new_ddl == ddl:
        return
    connection.executescript("""
        PRAGMA foreign_keys=OFF;
        ALTER TABLE custom_tournaments RENAME TO custom_tournaments_old;
        """ + new_ddl + ";" + """
        INSERT INTO custom_tournaments SELECT * FROM custom_tournaments_old;
        DROP TABLE custom_tournaments_old;
        PRAGMA foreign_keys=ON;
    """)


def _generate_staff_for_team(connection: sqlite3.Connection, team_id: int, nationality: str,
                             division: int, rng: random.Random, used_names: set[str]) -> None:
    """Seed one club's full coaching/medical/scouting roster."""
    from src.models.staff import ROLES, generate_staff_member
    club_quality = 13.0 if division == 1 else 9.0
    for role, group, _ in ROLES:
        name = _player_name(nationality, used_names, rng)
        member = generate_staff_member(role, group, nationality, name, rng, club_quality)
        connection.execute(
            """INSERT INTO staff (team_id, name, age, nationality, role, group_name,
                                  attributes_json, wage, contract_years_remaining)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (team_id, member["name"], member["age"], member["nationality"], member["role"],
             member["group_name"], json.dumps(member["attributes"]), member["wage"],
             member["contract_years_remaining"]),
        )


def _ensure_staff_for_all_teams(connection: sqlite3.Connection, seed: int) -> None:
    """Backfill a full staff roster for any team that predates the staff system."""
    rng = random.Random(seed + 7)
    used_names: set[str] = set(row[0] for row in connection.execute("SELECT name FROM staff"))
    country_aliases = {"English": "england", "Australian": "australia", "Indian": "india",
                       "Pakistani": "pakistan", "South African": "south_africa",
                       "New Zealander": "new_zealand", "West Indian": "west_indies"}
    missing = connection.execute(
        """SELECT t.id, t.division, t.country_id FROM teams t
           LEFT JOIN staff s ON s.team_id = t.id
           GROUP BY t.id HAVING COUNT(s.id) = 0"""
    ).fetchall()
    reverse_alias = {value: key for key, value in country_aliases.items()}
    for row in missing:
        nationality = reverse_alias.get(row["country_id"], "English")
        _generate_staff_for_team(connection, row["id"], nationality, row["division"], rng, used_names)


def seed_database(connection: sqlite3.Connection, seed: int = 20260401) -> None:
    """Populate a new database. Existing team data is never duplicated."""
    if connection.execute("SELECT COUNT(*) FROM teams").fetchone()[0] > 0:
        _expand_world_to_twenty_four(connection, seed)
        _seed_phase_25_data(connection)
        _seed_phase_3_data(connection)
        _ensure_staff_for_all_teams(connection, seed)
        return

    rng = random.Random(seed)
    used_names: set[str] = set()
    country_aliases = {"English": "england", "Australian": "australia", "Indian": "india",
                       "Pakistani": "pakistan", "South African": "south_africa",
                       "New Zealander": "new_zealand", "West Indian": "west_indies"}
    for team_id, (name, division, nationality) in enumerate(TEAM_DEFINITIONS, start=1):
        capacity = rng.randrange(18_000, 36_001, 500) if division == 1 else rng.randrange(8_000, 20_001, 500)
        cash = rng.randrange(8_000_000, 15_000_001, 250_000) if division == 1 else rng.randrange(3_000_000, 8_000_001, 250_000)
        team_modifier = _team_quality_modifier(cash, division)
        connection.execute(
            """INSERT INTO teams
               (id, name, division, cash, stadium_capacity, training_level, medical_level, academy_level, country_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (team_id, name, division, cash, capacity, 3 if division == 1 else 2, 2, 2,
             country_aliases[nationality]),
        )

        for slot in range(25):
            player = generate_player(team_id, division, nationality, slot, rng, used_names, team_modifier)
            columns = ", ".join(player)
            placeholders = ", ".join("?" for _ in player)
            connection.execute(
                f"INSERT INTO players ({columns}) VALUES ({placeholders})",
                tuple(player.values()),
            )
        _generate_staff_for_team(connection, team_id, nationality, division, rng, used_names)

    current_year = date.today().year
    cursor = connection.execute(
        "INSERT INTO competitions (name, type, season) VALUES (?, ?, ?)",
        ("World Cricket League", "League", current_year),
    )
    competition_id = cursor.lastrowid
    connection.executemany(
        "INSERT INTO league_standings (competition_id, team_id) VALUES (?, ?)",
        [(competition_id, team_id) for team_id in range(1, len(TEAM_DEFINITIONS) + 1)],
    )
    connection.execute(
        """INSERT INTO user_data
           (id, current_team_id, current_date, game_speed, sound_on, resolution, auto_save_frequency)
           VALUES (1, 1, '2026-04-01', 'Normal', 1, '1280x720', 'Monthly')"""
    )
    _migrate_expanded_players(connection)
    _seed_phase_25_data(connection)
    _seed_phase_3_data(connection)


def _expand_world_to_twenty_four(connection: sqlite3.Connection, seed: int) -> None:
    """Append v0.9 expansion clubs without changing any established team ID."""
    existing_ids = {int(row[0]) for row in connection.execute("SELECT id FROM teams")}
    missing = [(index, definition) for index, definition in enumerate(TEAM_DEFINITIONS, 1)
               if index not in existing_ids]
    if not missing:
        return
    rng = random.Random(seed + 900)
    used_names = {str(row[0]) for row in connection.execute("SELECT name FROM players")}
    aliases = {"English": "england", "Australian": "australia", "Indian": "india",
               "Pakistani": "pakistan", "South African": "south_africa",
               "New Zealander": "new_zealand", "West Indian": "west_indies"}
    for team_id, (name, division, nationality) in missing:
        capacity = rng.randrange(18_000, 36_001, 500) if division == 1 else rng.randrange(8_000, 20_001, 500)
        cash = rng.randrange(8_000_000, 15_000_001, 250_000) if division == 1 else rng.randrange(3_000_000, 8_000_001, 250_000)
        team_modifier = _team_quality_modifier(cash, division)
        connection.execute(
            """INSERT INTO teams
               (id,name,division,cash,stadium_capacity,training_level,medical_level,academy_level,country_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (team_id, name, division, cash, capacity, 3 if division == 1 else 2, 2, 2, aliases[nationality]),
        )
        for slot in range(25):
            player = generate_player(team_id, division, nationality, slot, rng, used_names, team_modifier)
            columns = ", ".join(player)
            placeholders = ", ".join("?" for _ in player)
            connection.execute(f"INSERT INTO players ({columns}) VALUES ({placeholders})", tuple(player.values()))
        # Add the club to any already-created league table that covers it.
        for competition in connection.execute("SELECT id,name,type FROM competitions WHERE type='League'").fetchall():
            name_lower = str(competition["name"]).lower()
            if "division 1" in name_lower and division != 1: continue
            if "division 2" in name_lower and division != 2: continue
            connection.execute("INSERT OR IGNORE INTO league_standings(competition_id,team_id) VALUES (?,?)",
                               (competition["id"], team_id))
    _migrate_expanded_players(connection)


def _seed_phase_25_data(connection: sqlite3.Connection) -> None:
    """Add UI demonstration records once, including during save migration."""
    if connection.execute("SELECT COUNT(*) FROM inbox_messages").fetchone()[0] == 0:
        messages = [
            ("2026-04-01 08:00", "HIGH", "Opening fixture selection due", "Submit your starting XI before the season opener against Sydney Sixers.", 0, 1),
            ("2026-03-31 16:20", "HIGH", "Fitness test: Oliver Root", "Oliver Root reported hamstring tightness. Medical staff recommend a late fitness test.", 0, 1),
            ("2026-03-31 11:05", "MEDIUM", "Scouting report available", "Recruitment has completed reports on ten overseas pace bowlers.", 0, 0),
            ("2026-03-30 14:40", "MEDIUM", "Sponsor objective confirmed", "Main sponsor Greenline expects a top-four league finish this season.", 0, 0),
            ("2026-03-29 18:10", "LOW", "Academy intake scheduled", "The annual academy trial will take place during the second week of April.", 0, 0),
            ("2026-03-28 09:15", "LOW", "Ground staff update", "The opening-match pitch should retain a healthy covering of grass.", 1, 0),
            ("2026-03-27 17:30", "MEDIUM", "Contract talks requested", "Two senior players would like to discuss contract extensions this month.", 1, 1),
            ("2026-03-26 12:00", "LOW", "Season tickets reach 82%", "Supporters purchased 82% of the available season-ticket allocation.", 1, 0),
            ("2026-03-25 10:45", "LOW", "Training report", "Coaches noted strong progress from the club's young wicketkeepers.", 1, 0),
            ("2026-03-24 15:25", "MEDIUM", "Transfer enquiry received", "Mumbai Tigers made an informal enquiry about one of your all-rounders.", 1, 0),
        ]
        connection.executemany(
            """INSERT INTO inbox_messages
               (timestamp, priority, title, content, read, action_required)
               VALUES (?, ?, ?, ?, ?, ?)""",
            messages,
        )
    if connection.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 0:
        connection.execute(
            """INSERT INTO matches
               (home_team, away_team, format, date, venue, completed, result_json)
               VALUES (1, 2, 'T20', '2026-04-04', 'Mavericks Cricket Ground', 0, '{}')"""
        )


def _seed_phase_3_data(connection: sqlite3.Connection) -> None:
    """Seed operational records for the first playable management systems."""
    connection.execute("UPDATE players SET academy_squad = 1 WHERE age < 20")
    connection.execute(
        """INSERT OR IGNORE INTO training_assignments (player_id, focus, progress_json)
           SELECT id, 'None', '{}' FROM players"""
    )
    if connection.execute("SELECT COUNT(*) FROM financial_log WHERE team_id = 1").fetchone()[0] == 0:
        rng = random.Random(30303)
        categories = [
            ("Sponsorships", "INCOME", 420_000), ("TV Rights", "INCOME", 275_000),
            ("Matchday Revenue", "INCOME", 310_000), ("Wages", "EXPENSE", 515_000),
            ("Facilities Maintenance", "EXPENSE", 85_000), ("Youth Academy", "EXPENSE", 42_000),
        ]
        rows = []
        for month_index in range(12):
            year = 2025 + (3 + month_index) // 12
            month = (3 + month_index) % 12 + 1
            for category, kind, base in categories:
                amount = max(10_000, int(base * rng.uniform(.82, 1.18)))
                rows.append((1, f"{year:04d}-{month:02d}-01", category, kind, amount, f"Monthly {category.lower()}"))
        connection.executemany(
            """INSERT INTO financial_log (team_id, date, category, kind, amount, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            rows,
        )
    if connection.execute("SELECT COUNT(*) FROM sponsorships WHERE team_id = 1").fetchone()[0] == 0:
        connection.execute(
            """INSERT INTO sponsorships (team_id, sponsor_name, monthly_value, end_date, status)
               VALUES (1, 'Greenline Financial', 420000, '2026-09-30', 'ACTIVE')"""
        )
    if connection.execute("SELECT COUNT(*) FROM transfer_offers").fetchone()[0] == 0:
        players = connection.execute(
            "SELECT id, wage, overall FROM players WHERE team_id = 1 ORDER BY overall DESC LIMIT 3"
        ).fetchall()
        for index, player in enumerate(players):
            connection.execute(
                """INSERT INTO transfer_offers
                   (player_id, from_team, to_team, fee, weekly_wage, offer_type, status, created_date)
                   VALUES (?, 1, ?, ?, ?, 'INCOMING', 'PENDING', '2026-04-01')""",
                (player["id"], 3 + index, int(player["overall"] ** 3 * 15), int(player["wage"] * 1.15)),
            )


def initialise_database(database_path: str | Path = DEFAULT_DATABASE_PATH) -> Path:
    """Create, validate, and seed the local save database; return its path."""
    path = Path(database_path)
    with connect(path) as connection:
        create_tables(connection)
        seed_database(connection)
    return path


def save_game(state: Mapping[str, Any], database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Atomically save arbitrary JSON-compatible game state by key.

    Core entities live in their own relational tables; this store is intended
    for transient campaign state such as news, selections, and pending events.
    """
    with connect(database_path) as connection:
        create_tables(connection)
        for key, value in state.items():
            serialised = json.dumps(value, ensure_ascii=False)
            connection.execute(
                """INSERT INTO game_state (key, value_json, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(key) DO UPDATE SET
                       value_json = excluded.value_json,
                       updated_at = CURRENT_TIMESTAMP""",
                (key, serialised),
            )


def load_game(database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Load user settings, current club details, and flexible campaign state."""
    initialise_database(database_path)
    with connect(database_path) as connection:
        user_row = connection.execute(
            """SELECT u.*, t.name AS team_name, t.cash, t.division
               FROM user_data u JOIN teams t ON t.id = u.current_team_id
               WHERE u.id = 1"""
        ).fetchone()
        if user_row is None:
            raise RuntimeError("The save database does not contain a user profile.")
        result: dict[str, Any] = {"user": dict(user_row), "state": {}}
        for row in connection.execute("SELECT key, value_json FROM game_state"):
            result["state"][row["key"]] = json.loads(row["value_json"])
        return result


def fetch_players(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Return a team's players, decoding the four attribute JSON documents."""
    with connect(database_path) as connection:
        rows: Sequence[sqlite3.Row] = connection.execute(
            "SELECT * FROM players WHERE team_id = ? ORDER BY overall DESC, name", (team_id,)
        ).fetchall()
    players = []
    for row in rows:
        player = dict(row)
        for field in ("batting_json", "bowling_json", "fielding_json", "mental_json"):
            player[field.removesuffix("_json")] = json.loads(player.pop(field))
        players.append(player)
    return players


def get_team_summary(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Return the compact club data required by the persistent top bar."""
    with connect(database_path) as connection:
        row = connection.execute(
            """SELECT t.*, COUNT(p.id) AS player_count, ROUND(AVG(p.overall), 1) AS average_overall
               FROM teams t LEFT JOIN players p ON p.team_id = t.id
               WHERE t.id = ? GROUP BY t.id""",
            (team_id,),
        ).fetchone()
    if row is None:
        raise KeyError(f"Unknown team id: {team_id}")
    summary = dict(row)
    summary["physio_rating"] = team_physio_rating(team_id, database_path)
    return summary


def fetch_teams(database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Return every selectable club with compact squad and budget metrics."""
    with connect(database_path) as connection:
        rows = connection.execute(
            """SELECT t.*, COUNT(p.id) AS squad_size,
                      ROUND(AVG(p.overall), 1) AS average_rating
               FROM teams t LEFT JOIN players p ON p.team_id = t.id
               GROUP BY t.id ORDER BY t.division, average_rating DESC, t.name"""
        ).fetchall()
    return [dict(row) for row in rows]


def set_current_team(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Assign the human manager to an existing club after setup validation."""
    with connect(database_path) as connection:
        exists = connection.execute("SELECT 1 FROM teams WHERE id=?", (int(team_id),)).fetchone()
        if not exists:
            raise KeyError(f"Unknown team id: {team_id}")
        connection.execute("UPDATE user_data SET current_team_id=? WHERE id=1", (int(team_id),))


def apply_difficulty_starting_cash(team_id: int, multiplier: float,
                                   database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Apply the selected difficulty's starting budget once per career."""
    with connect(database_path) as connection:
        marker = connection.execute(
            "SELECT 1 FROM game_state WHERE key='difficulty_cash_applied'"
        ).fetchone()
        if marker:
            return
        row = connection.execute("SELECT cash FROM teams WHERE id=?", (int(team_id),)).fetchone()
        if row is None:
            raise KeyError(f"Unknown team id: {team_id}")
        connection.execute("UPDATE teams SET cash=? WHERE id=?",
                           (round(row[0] * float(multiplier)), int(team_id)))
        connection.execute(
            "INSERT INTO game_state(key,value_json) VALUES('difficulty_cash_applied','true')"
        )


def apply_match_player_updates(updates: Mapping[int, Mapping[str, float]], injuries: Sequence[Mapping[str, Any]],
                               current_date: str, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Persist bounded form/progression changes, post-match fatigue, and
    match injuries atomically.

    Fatigue is an absolute reading (this match's end-of-game tiredness),
    not a delta like form/overall — match_engine.Match.performance_updates()
    always includes it for every player who took the field, but the
    CASE guard keeps this safe if a future caller omits it.
    """
    from datetime import timedelta
    start = date.fromisoformat(current_date)
    with connect(database_path) as connection:
        for player_id, change in updates.items():
            fatigue = change.get("fatigue")
            connection.execute(
                """UPDATE players SET
                       form=MAX(0, MIN(100, form + ?)),
                       overall=MAX(0, MIN(potential, overall + ?)),
                       fatigue=CASE WHEN ? IS NOT NULL THEN MAX(0, MIN(100, ?)) ELSE fatigue END
                   WHERE id=?""",
                (float(change.get("form", 0)), float(change.get("overall", 0)),
                 fatigue, fatigue, int(player_id)),
            )
        for injury in injuries:
            days = max(1, int(injury.get("days", 7)))
            connection.execute(
                """INSERT INTO injuries(player_id, severity, start_date, return_date, active)
                   VALUES (?, ?, ?, ?, 1)""",
                (int(injury["player_id"]), str(injury["severity"]), current_date, (start + timedelta(days=days)).isoformat()),
            )


def adjust_players_morale(player_ids: Sequence[int], delta: int,
                          database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Bounded morale delta (mental.morale, 0-100) for specific players —
    used for individual events (being dropped from the XI, a signed
    contract). See src/models/morale.py for the event constants."""
    if not player_ids or not delta:
        return
    with connect(database_path) as connection:
        connection.executemany(
            """UPDATE players SET mental_json = json_set(mental_json, '$.morale',
                   MAX(0, MIN(100, CAST(json_extract(mental_json, '$.morale') AS INTEGER) + ?)))
               WHERE id = ?""",
            [(int(delta), int(player_id)) for player_id in player_ids],
        )


def adjust_team_morale(team_id: int, delta: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Bounded morale delta applied to a whole squad — used for team-wide
    events (match result, promotion/relegation)."""
    if not delta:
        return
    with connect(database_path) as connection:
        connection.execute(
            """UPDATE players SET mental_json = json_set(mental_json, '$.morale',
                   MAX(0, MIN(100, CAST(json_extract(mental_json, '$.morale') AS INTEGER) + ?)))
               WHERE team_id = ?""",
            (int(delta), int(team_id)),
        )


FATIGUE_DAILY_RECOVERY = 12


def recover_daily_fatigue(database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Every calendar day recovers some fatigue for every player — called
    once per advance_day(). A player who plays a demanding match has their
    fatigue overwritten to a fresh absolute reading by
    apply_match_player_updates() on match day; this is what brings it back
    down again on the rest days in between, matching real cricket workload
    management (roughly a week of rest to fully recover from a hard game)."""
    with connect(database_path) as connection:
        connection.execute("UPDATE players SET fatigue = MAX(0, fatigue - ?)", (FATIGUE_DAILY_RECOVERY,))


def fetch_inbox_messages(
    limit: int | None = None, database_path: str | Path = DEFAULT_DATABASE_PATH
) -> list[dict[str, Any]]:
    """Return newest inbox messages first."""
    sql = "SELECT * FROM inbox_messages ORDER BY timestamp DESC, id DESC"
    params: tuple[Any, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (limit,)
    with connect(database_path) as connection:
        return [dict(row) for row in connection.execute(sql, params).fetchall()]


def mark_inbox_read(message_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Mark one notification read without changing its action status."""
    with connect(database_path) as connection:
        connection.execute("UPDATE inbox_messages SET read = 1 WHERE id = ?", (message_id,))


def unread_inbox_count(database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    with connect(database_path) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM inbox_messages WHERE read = 0").fetchone()[0])


def fetch_league_standings(database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Return Division 1 standings ordered by points then net run rate."""
    with connect(database_path) as connection:
        competition = connection.execute(
            "SELECT id FROM competitions WHERE name='Domestic Division 1' ORDER BY season DESC, id DESC LIMIT 1"
        ).fetchone()
        if not competition:
            competition = connection.execute("SELECT competition_id FROM league_standings ORDER BY competition_id LIMIT 1").fetchone()
        rows = connection.execute(
            """SELECT t.id AS team_id, t.name, s.played, s.won, s.lost, s.tied,
                      s.points, s.net_run_rate
               FROM league_standings s JOIN teams t ON t.id = s.team_id
               WHERE t.division = 1 AND s.competition_id = ?
               ORDER BY s.points DESC, s.won DESC, s.net_run_rate DESC, t.name""", (competition[0],)
        ).fetchall() if competition else []
    return [dict(row) for row in rows]


def fetch_next_fixture(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any] | None:
    """Get the next incomplete match for a team, including readable club names."""
    with connect(database_path) as connection:
        row = connection.execute(
            """SELECT m.*, h.name AS home_name, a.name AS away_name
               FROM matches m JOIN teams h ON h.id = m.home_team JOIN teams a ON a.id = m.away_team
               WHERE m.completed = 0 AND (m.home_team = ? OR m.away_team = ?)
               ORDER BY m.date LIMIT 1""",
            (team_id, team_id),
        ).fetchone()
    return dict(row) if row else None


def create_inbox_message(priority: str, title: str, content: str, action_required: bool = False,
                         timestamp: str | None = None, database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    """Publish a system notification and return its database id."""
    stamp = timestamp or f"{date.today().isoformat()} 09:00"
    with connect(database_path) as connection:
        cursor = connection.execute(
            """INSERT INTO inbox_messages (timestamp, priority, title, content, read, action_required)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (stamp, priority, title, content, int(action_required)),
        )
        return int(cursor.lastrowid)


def _ensure_honours_table(connection) -> None:
    """Lazily created so pre-0.14.0 saves migrate on first use."""
    connection.execute(
        """CREATE TABLE IF NOT EXISTS honours (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               team_id INTEGER NOT NULL,
               title TEXT NOT NULL,
               season INTEGER NOT NULL,
               awarded_on TEXT NOT NULL)"""
    )


def record_honour(team_id: int, title: str, season: int, awarded_on: str,
                  database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    """Add a trophy/honour to a club's permanent cabinet."""
    with connect(database_path) as connection:
        _ensure_honours_table(connection)
        cursor = connection.execute(
            "INSERT INTO honours (team_id, title, season, awarded_on) VALUES (?, ?, ?, ?)",
            (int(team_id), title, int(season), awarded_on),
        )
        return int(cursor.lastrowid)


def fetch_honours(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """A club's honours, most recent first."""
    with connect(database_path) as connection:
        _ensure_honours_table(connection)
        rows = connection.execute(
            "SELECT title, season, awarded_on FROM honours WHERE team_id=? ORDER BY season DESC, id DESC",
            (int(team_id),),
        ).fetchall()
    return [dict(row) for row in rows]


#: Mirrors CompetitionEngine._advance_cup_if_ready's next-round mapping in
#: competition.py — the only place round order is otherwise encoded (as a
#: dict of transitions, not an ordered list), so this is redefined here as
#: an explicit sequence for get_cup_bracket's column ordering.
CUP_ROUND_ORDER = ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final"]


def get_cup_bracket(database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """The current season's Domestic Knockout Cup, shaped as a bracket
    (round name -> ordered list of matches) for a tree-style UI. Unlike
    get_tournament_bracket (the separate, in-career "custom tournament"
    system), this covers the one cup competition every save automatically
    has — there was no bracket-shaped endpoint for it at all before
    v0.88.0, only flat fixture-list queries elsewhere."""
    with connect(database_path) as connection:
        competition = connection.execute(
            "SELECT id, season FROM competitions WHERE type='Cup' ORDER BY season DESC, id DESC LIMIT 1"
        ).fetchone()
        if not competition:
            return {"bracket": {}, "rounds": [], "status": "not_started", "season": None}
        teams = {row["id"]: row["name"] for row in connection.execute("SELECT id, name FROM teams")}
        rows = connection.execute(
            "SELECT * FROM matches WHERE competition_id=? ORDER BY id", (competition["id"],)
        ).fetchall()
    bracket: dict[str, list[dict[str, Any]]] = {}
    final_completed = False
    for row in rows:
        try:
            result = json.loads(row["result_json"]) if row["result_json"] else {}
        except (ValueError, TypeError):
            result = {}
        winner_id = result.get("winner")
        entry = {
            "match_id": row["id"], "home": teams.get(row["home_team"], "?"),
            "away": teams.get(row["away_team"], "?"), "home_runs": result.get("home_runs"),
            "away_runs": result.get("away_runs"), "completed": bool(row["completed"]),
            "winner": teams.get(winner_id) if winner_id is not None else None,
        }
        bracket.setdefault(row["round_name"], []).append(entry)
        if row["round_name"] == "Final" and row["completed"]:
            final_completed = True
    status = "complete" if final_completed else ("in_progress" if bracket else "not_started")
    rounds = [name for name in CUP_ROUND_ORDER if name in bracket]
    return {"bracket": bracket, "rounds": rounds, "status": status, "season": competition["season"]}


def record_legend(player: Mapping[str, Any], final_team_name: str, retired_age: int, season: int,
                  retired_on: str, reason: str = "retired", became_staff: bool = False,
                  database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    """Archive a retiring/released player before their `players` row is
    deleted. `player_records` cascades on that delete, so a snapshot of
    the career record is taken here — the only place it survives."""
    record_snapshot = fetch_player_records(int(player["id"]), database_path)
    with connect(database_path) as connection:
        cursor = connection.execute(
            """INSERT INTO legends (player_id, name, nationality, role, final_team_id, final_team_name,
                                    final_overall, retired_age, retired_season, retired_on, reason,
                                    became_staff, career_record_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (int(player["id"]), player["name"], player["nationality"], player["role"],
             player.get("team_id"), final_team_name, int(player["overall"]), int(retired_age),
             int(season), retired_on, reason, int(bool(became_staff)), json.dumps(record_snapshot)),
        )
        return int(cursor.lastrowid)


def fetch_legends(nationality: str | None = None, limit: int = 200,
                  database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """The Hall of Fame: retired/released players, most recently retired
    first. Visible-but-unsignable — there is deliberately no function that
    reinserts a legend into `players`."""
    query = "SELECT * FROM legends"
    params: list[Any] = []
    if nationality:
        query += " WHERE nationality=?"
        params.append(nationality)
    query += " ORDER BY retired_season DESC, id DESC LIMIT ?"
    params.append(int(limit))
    with connect(database_path) as connection:
        rows = connection.execute(query, params).fetchall()
    legends = []
    for row in rows:
        entry = dict(row)
        entry["career_record"] = json.loads(entry.pop("career_record_json") or "{}")
        legends.append(entry)
    return legends


def record_season_stats(team_id: int, season: int, position: int | None, played: int, won: int, lost: int,
                        top_scorer_name: str, top_scorer_runs: int, top_wicket_taker_name: str,
                        top_wicket_taker_wickets: int, recorded_on: str,
                        database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    """Archive one club's season leaders, written once at rollover."""
    with connect(database_path) as connection:
        cursor = connection.execute(
            """INSERT INTO season_records (team_id, season, position, played, won, lost, top_scorer_name,
                                           top_scorer_runs, top_wicket_taker_name, top_wicket_taker_wickets, recorded_on)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(team_id, season) DO UPDATE SET
                   position=excluded.position, played=excluded.played, won=excluded.won, lost=excluded.lost,
                   top_scorer_name=excluded.top_scorer_name, top_scorer_runs=excluded.top_scorer_runs,
                   top_wicket_taker_name=excluded.top_wicket_taker_name,
                   top_wicket_taker_wickets=excluded.top_wicket_taker_wickets, recorded_on=excluded.recorded_on""",
            (int(team_id), int(season), position if position is None else int(position), int(played), int(won),
             int(lost), top_scorer_name, int(top_scorer_runs), top_wicket_taker_name, int(top_wicket_taker_wickets),
             recorded_on),
        )
        return int(cursor.lastrowid)


def fetch_season_records(team_id: int, limit: int = 100,
                         database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """A club's season-by-season history, most recent first."""
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM season_records WHERE team_id=? ORDER BY season DESC LIMIT ?",
            (int(team_id), int(limit)),
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_club_records(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """All-time club bests/worsts, derived on the fly from completed matches
    (there is no dedicated records table — `matches.result_json` already has
    everything needed, and club history is small enough to scan directly)."""
    with connect(database_path) as connection:
        rows = connection.execute(
            """SELECT home_team, away_team, result_json, format, date, venue FROM matches
               WHERE completed=1 AND (home_team=? OR away_team=?)""",
            (int(team_id), int(team_id)),
        ).fetchall()
    highest_score: dict[str, Any] | None = None
    heaviest_defeat: dict[str, Any] | None = None
    biggest_win: dict[str, Any] | None = None
    for row in rows:
        try:
            result = json.loads(row["result_json"])
        except (ValueError, TypeError):
            continue
        is_home = row["home_team"] == team_id
        own_runs = result.get("home_runs") if is_home else result.get("away_runs")
        opp_runs = result.get("away_runs") if is_home else result.get("home_runs")
        if own_runs is None or opp_runs is None:
            continue
        if highest_score is None or own_runs > highest_score["runs"]:
            highest_score = {"runs": int(own_runs), "opponent_runs": int(opp_runs), "format": row["format"],
                             "date": row["date"], "venue": row["venue"]}
        won = result.get("winner") == team_id
        margin = own_runs - opp_runs if won else opp_runs - own_runs
        entry = {"margin": int(margin), "own_runs": int(own_runs), "opponent_runs": int(opp_runs),
                 "format": row["format"], "date": row["date"], "venue": row["venue"]}
        if won and (biggest_win is None or margin > biggest_win["margin"]):
            biggest_win = entry
        elif not won and result.get("winner") is not None and (heaviest_defeat is None or margin > heaviest_defeat["margin"]):
            heaviest_defeat = entry
    return {"highest_score": highest_score, "biggest_win": biggest_win, "heaviest_defeat": heaviest_defeat,
           "matches_played": len(rows)}


def renew_player_contract(player_id: int, weekly_wage: int, years: int, signing_bonus: int = 0,
                          database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Apply an agreed contract renewal, pay the signing bonus, and lift the
    player's morale — this only ever runs once negotiate() has already
    returned "accept" (see src/models/contracts.py), so getting the terms
    they wanted is a genuine morale event, not a neutral database write."""
    from src.models.morale import CONTRACT_SIGNED_MORALE_BONUS
    with connect(database_path) as connection:
        connection.execute("UPDATE players SET wage = ?, contract_years_remaining = ? WHERE id = ?",
                           (int(weekly_wage), max(1, int(years)), int(player_id)))
        if signing_bonus:
            team_row = connection.execute("SELECT team_id, name FROM players WHERE id = ?", (int(player_id),)).fetchone()
            if team_row:
                connection.execute("UPDATE teams SET cash = cash - ? WHERE id = ?", (int(signing_bonus), team_row["team_id"]))
    adjust_players_morale([player_id], CONTRACT_SIGNED_MORALE_BONUS, database_path)


def fetch_staff(team_id: int, group: str | None = None,
               database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """A club's coaching/medical/scouting roster, decoded and star-ready."""
    with connect(database_path) as connection:
        sql = "SELECT * FROM staff WHERE team_id = ?"
        params: list[Any] = [team_id]
        if group:
            sql += " AND group_name = ?"
            params.append(group)
        rows = connection.execute(sql + " ORDER BY group_name, role", params).fetchall()
    from src.models.staff import ROLES
    headline_key = {role: key for role, _, key in ROLES}
    staff = []
    for row in rows:
        member = dict(row)
        attributes = json.loads(member.pop("attributes_json"))
        member["attributes"] = attributes
        key = headline_key.get(member["role"])
        if key == "judging_ability":
            member["overall"] = round((attributes.get("judging_ability", 10) + attributes.get("judging_potential", 10)) / 2)
        else:
            member["overall"] = attributes.get(key, 10)
        staff.append(member)
    return staff


def team_coach_rating(team_id: int, discipline: str,
                      database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    """The coaching attribute driving training gains for one discipline group."""
    from src.models.staff import COACH_DISCIPLINE
    role = next((role for role, disc in COACH_DISCIPLINE.items() if disc == discipline), None)
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT attributes_json FROM staff WHERE team_id = ? AND role = ?", (team_id, role)
        ).fetchone() if role else None
        if row is None:
            row = connection.execute(
                "SELECT attributes_json FROM staff WHERE team_id = ? AND role = 'Head Coach'", (team_id,)
            ).fetchone()
    if row is None:
        return 10
    return int(json.loads(row["attributes_json"]).get("coaching", 10))


def team_physio_rating(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    """The club's best physiotherapy attribute (Doctor or Physio)."""
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT attributes_json FROM staff WHERE team_id = ? AND group_name = 'Medical'", (team_id,)
        ).fetchall()
    ratings = [json.loads(row["attributes_json"]).get("physiotherapy", 10) for row in rows]
    return max(ratings) if ratings else 10


def team_scout_rating(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> tuple[int, int]:
    """The club's best (judging_ability, judging_potential) among its scouts."""
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT attributes_json FROM staff WHERE team_id = ? AND group_name = 'Scouting'", (team_id,)
        ).fetchall()
    if not rows:
        return 10, 10
    best = max(rows, key=lambda row: json.loads(row["attributes_json"]).get("judging_ability", 10))
    attrs = json.loads(best["attributes_json"])
    return int(attrs.get("judging_ability", 10)), int(attrs.get("judging_potential", 10))


def staff_transfer_value(overall: int, age: int) -> int:
    """A simple fee model: overall dominates, with an age discount for veterans."""
    base = 15_000 + (overall / 20) ** 2.4 * 220_000
    age_factor = 1.0 if age < 50 else max(.35, 1 - (age - 50) * .03)
    return int(round(base * age_factor / 500) * 500)


def browse_staff_market(group: str = "All", exclude_team: int = 1, limit: int = 30,
                        database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Other clubs' staff, priced and ready for a transfer offer."""
    with connect(database_path) as connection:
        sql = "SELECT s.*, t.name AS club_name FROM staff s JOIN teams t ON t.id = s.team_id WHERE s.team_id != ?"
        params: list[Any] = [exclude_team]
        if group != "All":
            sql += " AND s.group_name = ?"
            params.append(group)
        sql += " ORDER BY t.name, s.role LIMIT ?"
        params.append(limit)
        rows = connection.execute(sql, params).fetchall()
    from src.models.staff import ROLES
    headline_key = {role: key for role, _, key in ROLES}
    market = []
    for row in rows:
        member = dict(row)
        attributes = json.loads(member.pop("attributes_json"))
        member["attributes"] = attributes
        key = headline_key.get(member["role"])
        member["overall"] = (round((attributes.get("judging_ability", 10) + attributes.get("judging_potential", 10)) / 2)
                             if key == "judging_ability" else attributes.get(key, 10))
        member["fee"] = staff_transfer_value(member["overall"], member["age"])
        market.append(member)
    return market


def make_staff_offer(staff_id: int, from_team: int, to_team: int, fee: int, wage: int,
                     created_date: str, database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    """Submit a bid for another club's staff member; returns the offer id."""
    with connect(database_path) as connection:
        cursor = connection.execute(
            """INSERT INTO staff_transfer_offers (staff_id, from_team, to_team, fee, wage, status, created_date)
               VALUES (?, ?, ?, ?, ?, 'PENDING', ?)""",
            (staff_id, from_team, to_team, fee, wage, created_date),
        )
        return int(cursor.lastrowid)


def resolve_staff_offer(offer_id: int, accepted: bool,
                        database_path: str | Path = DEFAULT_DATABASE_PATH) -> bool:
    """Apply an accepted staff transfer: move the staff member and swap cash."""
    with connect(database_path) as connection:
        offer = connection.execute("SELECT * FROM staff_transfer_offers WHERE id = ?", (offer_id,)).fetchone()
        if offer is None or offer["status"] != "PENDING":
            return False
        if not accepted:
            connection.execute("UPDATE staff_transfer_offers SET status='REJECTED' WHERE id=?", (offer_id,))
            return True
        buyer_cash = connection.execute("SELECT cash FROM teams WHERE id = ?", (offer["to_team"],)).fetchone()[0]
        if buyer_cash < offer["fee"]:
            connection.execute("UPDATE staff_transfer_offers SET status='FAILED' WHERE id=?", (offer_id,))
            return False
        connection.execute("UPDATE teams SET cash = cash - ? WHERE id = ?", (offer["fee"], offer["to_team"]))
        connection.execute("UPDATE teams SET cash = cash + ? WHERE id = ?", (offer["fee"], offer["from_team"]))
        connection.execute("UPDATE staff SET team_id = ?, wage = ? WHERE id = ?",
                          (offer["to_team"], offer["wage"], offer["staff_id"]))
        connection.execute("UPDATE staff_transfer_offers SET status='ACCEPTED' WHERE id=?", (offer_id,))
        return True


def sell_staff_member(staff_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    """Release a staff member to another interested club for an immediate fee.

    Leaves the department vacant on purpose — the manager must hire a
    replacement from the Market, exactly as choosing to sell a player does.
    """
    with connect(database_path) as connection:
        row = connection.execute("SELECT team_id, role, age, attributes_json FROM staff WHERE id = ?",
                                 (staff_id,)).fetchone()
        if row is None:
            return 0
        from src.models.staff import ROLES
        headline_key = {role: key for role, _, key in ROLES}
        attributes = json.loads(row["attributes_json"])
        key = headline_key.get(row["role"])
        overall = (round((attributes.get("judging_ability", 10) + attributes.get("judging_potential", 10)) / 2)
                  if key == "judging_ability" else attributes.get(key, 10))
        fee = staff_transfer_value(overall, row["age"])
        connection.execute("UPDATE teams SET cash = cash + ? WHERE id = ?", (fee, row["team_id"]))
        connection.execute("DELETE FROM staff WHERE id = ?", (staff_id,))
        return fee


def fetch_incoming_staff_offers(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Pending bids from other clubs for this club's staff."""
    with connect(database_path) as connection:
        rows = connection.execute(
            """SELECT o.*, s.name AS staff_name, s.role AS staff_role, t.name AS to_name
               FROM staff_transfer_offers o
               JOIN staff s ON s.id = o.staff_id
               JOIN teams t ON t.id = o.to_team
               WHERE o.from_team = ? AND o.status = 'PENDING'
               ORDER BY o.created_date DESC""", (team_id,),
        ).fetchall()
    return [dict(row) for row in rows]


#: Staff careers run longer than playing careers; retirement is rare below this.
STAFF_RETIREMENT_AGE = 66


def age_staff_at_rollover(season: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, list[str]]:
    """Season-rollover companion to player ageing: staff age, drift, retire,
    and — so no department is ever left empty — get replaced."""
    from src.models.staff import age_staff_member, generate_staff_member
    rng = random.Random(season * 97 + 3)
    retired: list[str] = []
    with connect(database_path) as connection:
        rows = connection.execute("SELECT id, age, attributes_json FROM staff").fetchall()
        for row in rows:
            new_age = row["age"] + 1
            drifted = age_staff_member(json.loads(row["attributes_json"]), new_age, rng)
            connection.execute("UPDATE staff SET age = ?, attributes_json = ? WHERE id = ?",
                              (new_age, json.dumps(drifted), row["id"]))
        retirement_chance = lambda age: 0.0 if age < STAFF_RETIREMENT_AGE else min(.9, (age - STAFF_RETIREMENT_AGE + 1) * .18)
        candidates = connection.execute(
            "SELECT id, name, age, team_id, role, group_name FROM staff WHERE age >= ?",
            (STAFF_RETIREMENT_AGE,),
        ).fetchall()
        used_names: set[str] = set(row[0] for row in connection.execute("SELECT name FROM staff"))
        country_aliases = {"English": "england", "Australian": "australia", "Indian": "india",
                           "Pakistani": "pakistan", "South African": "south_africa",
                           "New Zealander": "new_zealand", "West Indian": "west_indies"}
        reverse_alias = {value: key for key, value in country_aliases.items()}
        for candidate in candidates:
            if rng.random() >= retirement_chance(candidate["age"]):
                continue
            retired.append(f"{candidate['name']} ({candidate['role']})")
            connection.execute("DELETE FROM staff WHERE id = ?", (candidate["id"],))
            team_row = connection.execute("SELECT division, country_id FROM teams WHERE id = ?",
                                          (candidate["team_id"],)).fetchone()
            nationality = reverse_alias.get(team_row["country_id"], "English") if team_row else "English"
            club_quality = 13.0 if (team_row and team_row["division"] == 1) else 9.0
            replacement = generate_staff_member(candidate["role"], candidate["group_name"], nationality,
                                                _player_name(nationality, used_names, rng), rng, club_quality)
            connection.execute(
                """INSERT INTO staff (team_id, name, age, nationality, role, group_name,
                                      attributes_json, wage, contract_years_remaining)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (candidate["team_id"], replacement["name"], min(replacement["age"], 45), replacement["nationality"],
                 replacement["role"], replacement["group_name"], json.dumps(replacement["attributes"]),
                 replacement["wage"], replacement["contract_years_remaining"]),
            )
    return {"retired": retired}


def fetch_active_injuries(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Currently-active injuries for a club's players, most recent first."""
    with connect(database_path) as connection:
        rows = connection.execute(
            """SELECT i.*, p.name AS player_name, p.role AS player_role FROM injuries i
               JOIN players p ON p.id = i.player_id
               WHERE p.team_id = ? AND i.active = 1
               ORDER BY i.start_date DESC""", (team_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def clear_expired_injuries(current_date: str, database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    """Deactivate injuries whose return date has passed; return the count cleared."""
    with connect(database_path) as connection:
        cursor = connection.execute(
            "UPDATE injuries SET active = 0 WHERE active = 1 AND return_date <= ?", (current_date,)
        )
        return cursor.rowcount


def fetch_financial_log(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        return [dict(row) for row in connection.execute(
            "SELECT * FROM financial_log WHERE team_id = ? ORDER BY date, id", (team_id,)
        ).fetchall()]


def add_financial_transaction(team_id: int, transaction_date: str, category: str, kind: str,
                              amount: int, description: str,
                              database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Record a ledger line and immediately update cash."""
    signed = amount if kind == "INCOME" else -amount
    with connect(database_path) as connection:
        connection.execute(
            "INSERT INTO financial_log (team_id, date, category, kind, amount, description) VALUES (?, ?, ?, ?, ?, ?)",
            (team_id, transaction_date, category, kind, int(amount), description),
        )
        connection.execute("UPDATE teams SET cash = cash + ? WHERE id = ?", (signed, team_id))


def set_ticket_price(team_id: int, price: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    with connect(database_path) as connection:
        connection.execute("UPDATE teams SET ticket_price = ? WHERE id = ?", (max(5, min(100, int(price))), team_id))


def renew_sponsorship(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Create a simplified renewed sponsor contract with a small value increase."""
    with connect(database_path) as connection:
        current = connection.execute(
            "SELECT * FROM sponsorships WHERE team_id = ? ORDER BY id DESC LIMIT 1", (team_id,)
        ).fetchone()
        commercial_level = connection.execute("SELECT commercial_level FROM teams WHERE id=?", (team_id,)).fetchone()[0]
        value = int((current["monthly_value"] if current else 350_000) * (1.06 + commercial_level * .025))
        connection.execute("UPDATE sponsorships SET status = 'EXPIRED' WHERE team_id = ?", (team_id,))
        cursor = connection.execute(
            """INSERT INTO sponsorships (team_id, sponsor_name, monthly_value, end_date, status)
               VALUES (?, 'Boundary Bank', ?, '2027-09-30', 'ACTIVE')""",
            (team_id, value),
        )
        return dict(connection.execute("SELECT * FROM sponsorships WHERE id = ?", (cursor.lastrowid,)).fetchone())


def fetch_transfer_offers(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute(
            """SELECT o.*, p.name AS player_name, p.overall, p.role,
                      f.name AS from_name, t.name AS to_name
               FROM transfer_offers o JOIN players p ON p.id = o.player_id
               LEFT JOIN teams f ON f.id = o.from_team LEFT JOIN teams t ON t.id = o.to_team
               WHERE (o.from_team = ? OR o.to_team = ?) AND o.status = 'PENDING'
               ORDER BY o.created_date DESC, o.id DESC""",
            (team_id, team_id),
        ).fetchall()
    return [dict(row) for row in rows]


def resolve_transfer_offer(offer_id: int, accepted: bool,
                           database_path: str | Path = DEFAULT_DATABASE_PATH) -> bool:
    """Accept/reject an offer and apply the player/cash movement atomically."""
    with connect(database_path) as connection:
        offer = connection.execute("SELECT * FROM transfer_offers WHERE id = ? AND status = 'PENDING'", (offer_id,)).fetchone()
        if not offer:
            return False
        status = "ACCEPTED" if accepted else "REJECTED"
        connection.execute("UPDATE transfer_offers SET status = ? WHERE id = ?", (status, offer_id))
        if not accepted:
            return True
        buyer, seller = offer["to_team"], offer["from_team"]
        buyer_cash = connection.execute("SELECT cash FROM teams WHERE id = ?", (buyer,)).fetchone()[0]
        if buyer_cash < offer["fee"]:
            connection.execute("UPDATE transfer_offers SET status = 'FAILED' WHERE id = ?", (offer_id,))
            return False
        connection.execute("UPDATE teams SET cash = cash - ? WHERE id = ?", (offer["fee"], buyer))
        connection.execute("UPDATE teams SET cash = cash + ? WHERE id = ?", (offer["fee"], seller))
        connection.execute("UPDATE players SET team_id = ?, wage = ?, transfer_listed = 0 WHERE id = ?",
                           (buyer, offer["weekly_wage"], offer["player_id"]))
        connection.execute(
            "INSERT INTO transfers (player_id, from_team, to_team, fee, date, status) VALUES (?, ?, ?, ?, ?, 'COMPLETED')",
            (offer["player_id"], seller, buyer, offer["fee"], offer["created_date"]),
        )
        return True


def submit_transfer_offer(player_id: int, buying_team: int, fee: int, wage: int, offer_date: str,
                          database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    with connect(database_path) as connection:
        player = connection.execute("SELECT team_id FROM players WHERE id = ?", (player_id,)).fetchone()
        if not player or player["team_id"] == buying_team:
            raise ValueError("Select a player from another club.")
        cursor = connection.execute(
            """INSERT INTO transfer_offers
               (player_id, from_team, to_team, fee, weekly_wage, offer_type, status, created_date)
               VALUES (?, ?, ?, ?, ?, 'OUTGOING', 'PENDING', ?)""",
            (player_id, player["team_id"], buying_team, max(0, int(fee)), max(0, int(wage)), offer_date),
        )
        return int(cursor.lastrowid)


def scout_players(role: str = "All", minimum_age: int = 16, maximum_age: int = 45,
                  minimum_overall: int = 0, maximum_overall: int = 100,
                  nationality: str = "All", exclude_team: int = 1, limit: int | None = None,
                  database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    clauses = ["team_id != ?", "age BETWEEN ? AND ?", "overall BETWEEN ? AND ?"]
    params: list[Any] = [exclude_team, minimum_age, maximum_age, minimum_overall, maximum_overall]
    if role != "All": clauses.append("role = ?"); params.append(role)
    if nationality != "All": clauses.append("nationality = ?"); params.append(nationality)
    with connect(database_path) as connection:
        row = connection.execute("SELECT scouting_level FROM teams WHERE id=?", (exclude_team,)).fetchone()
        scouting_level = row[0] if row else 1
        sql = f"SELECT * FROM players WHERE {' AND '.join(clauses)} ORDER BY overall DESC, potential DESC, name"
        if limit is not None:
            params.append(max(1, int(limit) + max(0, scouting_level - 1) * 2))
            sql += " LIMIT ?"
        rows = connection.execute(sql, params).fetchall()
        team_finances = {r["id"]: (r["cash"], r["division"]) for r in
                         connection.execute("SELECT id, cash, division FROM teams")}
    from src.models.transfer import sale_assessment
    from src.models.staff import apply_scouting_estimate
    scout_rating = team_scout_rating(exclude_team, database_path)
    decoded = []
    for row in rows:
        player = _decode_player_row(row)
        # Availability/price reflect the *player's own club's* finances, not
        # the scouting team's — a cash-strapped seller is more likely to
        # part with a player, and a Division 1 club can command a higher
        # price (used here as a reputation proxy; teams have no dedicated
        # reputation field yet — see docs/CURRENT.md).
        owner_cash, owner_division = team_finances.get(player["team_id"], (8_000_000, 2))
        owner_reputation = 70 if owner_division == 1 else 50
        assessment = sale_assessment(player, team_cash=owner_cash, team_reputation=owner_reputation)
        player.update({"for_sale": assessment["available"], "sale_reason": assessment["reason"],
                       "asking_price": assessment["price"]})
        estimate = apply_scouting_estimate(player, scout_rating, random.Random(f"scout:{player['id']}"))
        player.update(estimate)
        decoded.append(player)
    return decoded


def create_scouting_assignment(team_id: int, scout_id: int, target_player_id: int, days: int,
                               created_date: str, database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    """Send a named scout to file a report on a specific player over N days."""
    with connect(database_path) as connection:
        scout = connection.execute("SELECT id FROM staff WHERE id=? AND team_id=? AND group_name='Scouting'",
                                   (scout_id, team_id)).fetchone()
        if not scout:
            raise ValueError("Select one of your own scouts.")
        active = connection.execute("SELECT id FROM scouting_assignments WHERE scout_id=? AND status='ACTIVE'",
                                    (scout_id,)).fetchone()
        if active:
            raise ValueError("That scout is already on assignment.")
        days = max(1, int(days))
        cursor = connection.execute(
            """INSERT INTO scouting_assignments
               (team_id, scout_id, target_player_id, days_remaining, total_days, status, created_date)
               VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)""",
            (team_id, scout_id, target_player_id, days, days, created_date))
        return int(cursor.lastrowid)


def fetch_scouting_assignments(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Every assignment for this club, newest first, with scout/target names attached."""
    with connect(database_path) as connection:
        rows = connection.execute(
            """SELECT a.*, s.name AS scout_name, p.name AS target_name, p.role AS target_role,
                      t.name AS target_club
               FROM scouting_assignments a
               JOIN staff s ON s.id = a.scout_id
               JOIN players p ON p.id = a.target_player_id
               JOIN teams t ON t.id = p.team_id
               WHERE a.team_id = ? ORDER BY a.id DESC""", (team_id,)).fetchall()
    return [dict(row) for row in rows]


def advance_scouting_assignments(current_date: str, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Tick every active assignment by a day; file reports for any that finish today.

    A longer assignment sharpens the read: the scout's effective judging
    ability rises slightly with total days invested, on top of their base
    rating — mirroring how a proper scouting trip beats a rushed once-over.
    """
    from src.models.staff import apply_scouting_estimate
    completed: list[dict[str, Any]] = []
    with connect(database_path) as connection:
        active = connection.execute("SELECT * FROM scouting_assignments WHERE status='ACTIVE'").fetchall()
        for row in active:
            assignment = dict(row)
            remaining = assignment["days_remaining"] - 1
            if remaining > 0:
                connection.execute("UPDATE scouting_assignments SET days_remaining=? WHERE id=?",
                                   (remaining, assignment["id"]))
                continue
            player_row = connection.execute("SELECT * FROM players WHERE id=?", (assignment["target_player_id"],)).fetchone()
            staff_row = connection.execute("SELECT attributes_json FROM staff WHERE id=?", (assignment["scout_id"],)).fetchone()
            if not player_row or not staff_row:
                connection.execute("DELETE FROM scouting_assignments WHERE id=?", (assignment["id"],))
                continue
            player = _decode_player_row(player_row)
            attrs = json.loads(staff_row["attributes_json"])
            bonus = min(4, assignment["total_days"] // 5)
            scout_rating = (min(20, attrs.get("judging_ability", 10) + bonus), min(20, attrs.get("judging_potential", 10) + bonus))
            estimate = apply_scouting_estimate(player, scout_rating, random.Random(f"assignment:{assignment['id']}"))
            connection.execute(
                """UPDATE scouting_assignments
                   SET status='COMPLETE', days_remaining=0, estimated_overall=?, estimated_potential=?, confidence=?
                   WHERE id=?""",
                (estimate["estimated_overall"], estimate["estimated_potential"], estimate["confidence"], assignment["id"]))
            completed.append({**assignment, **estimate, "target_name": player["name"]})
    return completed


def set_transfer_listed(player_id: int, listed: bool,
                        database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    with connect(database_path) as connection:
        connection.execute("UPDATE players SET transfer_listed = ? WHERE id = ?", (int(listed), player_id))


def generate_ai_transfer_offers(current_date: str, user_team_id: int,
                                database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """AI clubs evaluate their squad needs and bid for players from other clubs.

    Runs weekly during advance_day. Each AI team checks for squad gaps
    (fewer than 2 players in a key role), finds the best available target,
    and submits an offer if they can afford it. Returns a list of offers
    created (for inbox notifications).
    """
    from src.models.transfer import transfer_value
    offers: list[dict[str, Any]] = []
    rng = random.Random(f"ai_transfers:{current_date}")
    with connect(database_path) as connection:
        teams = [dict(r) for r in connection.execute(
            "SELECT id, name, cash, division FROM teams WHERE id != ?", (user_team_id,)
        ).fetchall()]
        for team in teams:
            if team["cash"] < 200_000:
                continue
            squad = [dict(r) for r in connection.execute(
                "SELECT id, role, overall, age, wage, contract_years_remaining, transfer_listed FROM players WHERE team_id = ?",
                (team["id"],)
            ).fetchall()]
            if len(squad) < 8:
                continue
            role_counts: dict[str, int] = {}
            for p in squad:
                role_counts[p["role"]] = role_counts.get(p["role"], 0) + 1
            needed_role = None
            for role in ("Batsman", "Bowler", "All-Rounder", "Wicketkeeper"):
                if role_counts.get(role, 0) < 2:
                    needed_role = role
                    break
            if not needed_role:
                continue
            if rng.random() > 0.15:
                continue
            candidates = [dict(r) for r in connection.execute(
                """SELECT p.*, t.name AS selling_team_name
                   FROM players p JOIN teams t ON t.id = p.team_id
                   WHERE p.team_id != ? AND p.role = ? AND p.age BETWEEN 18 AND 33
                     AND p.overall >= 45 AND (p.transfer_listed = 1 OR p.contract_years_remaining <= 1)
                   ORDER BY p.overall DESC LIMIT 10""",
                (team["id"], needed_role)
            ).fetchall()]
            if not candidates:
                continue
            target = rng.choice(candidates[:5])
            fee = transfer_value(target, team_reputation=50)
            if fee > team["cash"] * 0.4:
                fee = int(team["cash"] * rng.uniform(0.15, 0.35))
            fee = max(25_000, int(round(fee / 5_000) * 5_000))
            wage = max(500, int(target.get("wage", 1000) * rng.uniform(0.9, 1.3)))
            existing = connection.execute(
                "SELECT id FROM transfer_offers WHERE player_id=? AND to_team=? AND status='PENDING'",
                (target["id"], team["id"])
            ).fetchone()
            if existing:
                continue
            connection.execute(
                """INSERT INTO transfer_offers
                   (player_id, from_team, to_team, fee, weekly_wage, offer_type, status, created_date)
                   VALUES (?, ?, ?, ?, ?, 'INCOMING', 'PENDING', ?)""",
                (target["id"], target["team_id"], team["id"], fee, wage, current_date),
            )
            offers.append({
                "player_id": target["id"], "player_name": target["name"],
                "from_team": target["team_id"], "from_team_name": target["selling_team_name"],
                "to_team": team["id"], "to_team_name": team["name"],
                "fee": fee, "wage": wage,
            })
    return offers


def get_opposition_report(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any] | None:
    """Pre-match scouting summary of the next opponent.

    Returns key players, squad composition, strengths/weaknesses, and
    recent form — all from data the user's scouts would reasonably know.
    """
    fixture = fetch_next_fixture(team_id, database_path)
    if not fixture:
        return None
    opponent_id = fixture["away_team"] if fixture["home_team"] == team_id else fixture["home_team"]
    opponent_name = fixture["away_name"] if fixture["home_team"] == team_id else fixture["home_name"]
    with connect(database_path) as connection:
        players = [dict(r) for r in connection.execute(
            """SELECT p.name, p.role, p.overall, p.age, p.nationality, p.batting_json, p.bowling_json,
                      p.form, p.contract_years_remaining
               FROM players p WHERE p.team_id = ?
               ORDER BY p.overall DESC""",
            (opponent_id,)
        ).fetchall()]
    if not players:
        return None
    for p in players:
        p["batting"] = json.loads(p.pop("batting_json"))
        p["bowling"] = json.loads(p.pop("bowling_json"))
    xi = sorted(players, key=lambda p: p["overall"], reverse=True)[:11]
    role_counts: dict[str, int] = {}
    for p in players:
        role_counts[p["role"]] = role_counts.get(p["role"], 0) + 1
    bowlers = [p for p in xi if any(v > 40 for v in (p.get("bowling") or {}).values())]
    batters = [p for p in xi if any(v > 50 for v in (p.get("batting") or {}).values())]
    key_bowler = max(bowlers, key=lambda p: p["overall"]) if bowlers else None
    key_batter = max(batters, key=lambda p: p["overall"]) if batters else None
    avg_overall = sum(p["overall"] for p in xi) / max(1, len(xi))
    strengths, weaknesses = [], []
    if avg_overall >= 65:
        strengths.append("Strong overall squad")
    if len(bowlers) >= 5:
        strengths.append("Deep bowling attack")
    if key_bowler and key_bowler["overall"] >= 70:
        strengths.append(f"Key bowler: {key_bowler['name']} ({key_bowler['overall']})")
    if key_batter and key_batter["overall"] >= 70:
        strengths.append(f"Key batter: {key_batter['name']} ({key_batter['overall']})")
    if role_counts.get("All-Rounder", 0) >= 3:
        strengths.append("All-rounder depth")
    if avg_overall < 55:
        weaknesses.append("Weaker overall squad")
    if len(bowlers) < 3:
        weaknesses.append("Limited bowling options")
    if not any(p["overall"] >= 65 for p in xi):
        weaknesses.append("No standout performers")
    if any(p["age"] >= 35 for p in xi):
        weaknesses.append(" ageing squad members")
    return {
        "opponent_name": opponent_name,
        "opponent_id": opponent_id,
        "fixture_date": fixture["date"],
        "venue": fixture["venue"],
        "format": fixture["format"],
        "squad_size": len(players),
        "average_overall": round(avg_overall, 1),
        "role_distribution": role_counts,
        "key_players": [{"name": p["name"], "role": p["role"], "overall": p["overall"],
                         "age": p["age"], "form": p["form"]}
                        for p in xi[:5]],
        "xi": [{"name": p["name"], "role": p["role"], "overall": p["overall"]}
               for p in xi],
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


def _decode_player_row(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
    player = dict(row)
    for field in ("batting_json", "bowling_json", "fielding_json", "mental_json", "physical_json"):
        if field in player:
            player[field.removesuffix("_json")] = json.loads(player.pop(field))
    return player


def select_national_xi(nationality: str, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """The best 11 eligible players of a nationality, drawn from every
    club in the game world (not just the user's) — mirrors ipc_server.py's
    _best_xi() fallback (a guaranteed keeper slot, then best-by-overall)
    since there's no separate "international squad" concept to pick from."""
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM players WHERE nationality = ? ORDER BY overall DESC", (nationality,)
        ).fetchall()
    players = [_decode_player_row(row) for row in rows]
    keepers = [p for p in players if p["role"] == "Wicketkeeper"]
    rest = [p for p in players if p not in keepers[:1]]
    return (keepers[:1] + rest)[:11]


def fetch_training_assignments(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[int, dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute(
            """SELECT a.* FROM training_assignments a JOIN players p ON p.id = a.player_id
               WHERE p.team_id = ?""", (team_id,)
        ).fetchall()
    return {row["player_id"]: {"focus": row["focus"], "progress": json.loads(row["progress_json"]),
                               "last_trained": row["last_trained"],
                               "intensity": row["intensity"] if "intensity" in row.keys() else "Normal",
                               "days": json.loads(row["days_json"] or "[0,2,4]") if "days_json" in row.keys() else [0, 2, 4]}
            for row in rows}


def set_training_focus(player_id: int, focus: str, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    allowed = {"None", "Batting Focus", "Bowling Focus", "Fielding Focus", "Fitness", "All-Round"}
    if focus not in allowed:
        raise ValueError(f"Unknown training focus: {focus}")
    with connect(database_path) as connection:
        connection.execute(
            """INSERT INTO training_assignments (player_id, focus, progress_json)
               VALUES (?, ?, '{}') ON CONFLICT(player_id) DO UPDATE SET focus = excluded.focus""",
            (player_id, focus),
        )


def set_training_schedule(player_id: int, focus: str, intensity: str = "Normal",
                          days: Sequence[int] = (0, 2, 4),
                          database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    if intensity not in {"Light", "Normal", "Heavy"}: raise ValueError("Unknown training intensity")
    if not days or any(int(day) not in range(7) for day in days): raise ValueError("Invalid training days")
    set_training_focus(player_id, focus, database_path)
    with connect(database_path) as connection:
        connection.execute("UPDATE training_assignments SET intensity=?,days_json=? WHERE player_id=?",
                           (intensity, json.dumps(sorted(set(map(int, days)))), player_id))


def fetch_player_records(player_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, dict[str, Any]]:
    from src.models.player_records import CareerRecord
    with connect(database_path) as connection:
        rows = connection.execute("SELECT context,record_json FROM player_records WHERE player_id=?", (player_id,)).fetchall()
    output = {}
    for row in rows:
        data = json.loads(row["record_json"] or "{}")
        record = CareerRecord(**{key: value for key, value in data.items() if key in CareerRecord.__dataclass_fields__})
        output[row["context"]] = record.serialise()
    return output


def fetch_player_form(player_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    from src.models.player_form import PlayerForm
    with connect(database_path) as connection:
        values = [row[0] for row in connection.execute(
            "SELECT performance FROM player_form_history WHERE player_id=? ORDER BY match_date,id", (player_id,)).fetchall()]
    form = PlayerForm(list(map(float, values)))
    return {"values": form.values, "week": form.week, "month": form.month, "season": form.season, "trend": form.trend}


def fetch_player_match_events(player_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, list[dict[str, Any]]]:
    with connect(database_path) as connection:
        rows=[dict(row) for row in connection.execute("SELECT * FROM player_match_events WHERE player_id=? ORDER BY id DESC LIMIT 500",(player_id,)).fetchall()]
    shots=[]; deliveries=[]
    for row in rows:
        if row["event_type"] == "shot":
            shots.append({**row, "angle": row["x"], "distance": row["y"], "wicket": bool(row["wicket"])})
        else:
            deliveries.append({**row, "wicket": bool(row["wicket"])})
    return {"shots":shots, "deliveries":deliveries}


def record_player_match_events(match_id: int | None, innings: int,
                               shots: Sequence[Mapping[str, Any]], deliveries: Sequence[Mapping[str, Any]],
                               database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Persist compact spatial analytics used by profile maps."""
    rows=[]
    for event in shots:
        rows.append((int(event["player_id"]), match_id, int(event.get("innings", innings)), "shot", float(event.get("angle",0)),
                     float(event.get("distance",0)), int(event.get("runs",0)), int(bool(event.get("wicket")))))
    for event in deliveries:
        rows.append((int(event["player_id"]), match_id, int(event.get("innings", innings)), "delivery", float(event.get("x",.5)),
                     float(event.get("y",.5)), int(event.get("runs",0)), int(bool(event.get("wicket")))))
    with connect(database_path) as connection:
        connection.executemany("INSERT INTO player_match_events(player_id,match_id,innings,event_type,x,y,runs,wicket) VALUES (?,?,?,?,?,?,?,?)", rows)


def record_player_performance(player_id: int, match_date: str, context: str,
                              batting: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
                              bowling: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
                              fielding: Mapping[str, Any] | None = None,
                              database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    from src.models.player_records import CareerRecord, update_record
    with connect(database_path) as connection:
        row = connection.execute("SELECT record_json FROM player_records WHERE player_id=? AND context=?", (player_id, context)).fetchone()
        raw = json.loads(row[0]) if row else {}
        record = CareerRecord(**{key: value for key, value in raw.items() if key in CareerRecord.__dataclass_fields__})
        update_record(record, batting, bowling, fielding)
        connection.execute("INSERT INTO player_records(player_id,context,record_json) VALUES (?,?,?) ON CONFLICT(player_id,context) DO UPDATE SET record_json=excluded.record_json",
                           (player_id, context, json.dumps({key: getattr(record,key) for key in CareerRecord.__dataclass_fields__})))
        batting_entries = [batting] if isinstance(batting, Mapping) else list(batting or [])
        bowling_entries = [bowling] if isinstance(bowling, Mapping) else list(bowling or [])
        scored = sum(int(line.get("runs", 0)) for line in batting_entries)
        wickets = sum(int(line.get("wickets", 0)) for line in bowling_entries)
        score = 50 + min(35, scored * .35) + min(25, wickets * 6)
        connection.execute("INSERT INTO player_form_history(player_id,match_date,performance,context) VALUES (?,?,?,?)",
                           (player_id, match_date, max(0,min(100,score)), context))


def apply_daily_training(team_id: int, training_date: str,
                         database_path: str | Path = DEFAULT_DATABASE_PATH) -> int:
    """Run scheduled training only on assigned weekdays (Mon/Wed/Fri by default)."""
    focus_groups = {"Batting Focus": ["batting"], "Bowling Focus": ["bowling"],
                    "Fielding Focus": ["fielding"], "Fitness": ["mental"],
                    "All-Round": ["batting", "bowling", "fielding", "mental"]}
    changed = 0
    with connect(database_path) as connection:
        facility = connection.execute("SELECT training_level FROM teams WHERE id = ?", (team_id,)).fetchone()[0]
        rows = connection.execute(
            """SELECT p.*, a.focus, a.progress_json, a.intensity, a.days_json FROM players p
               JOIN training_assignments a ON a.player_id = p.id
               WHERE p.team_id = ? AND a.focus != 'None'""", (team_id,)
        ).fetchall()
        difficulty_row = connection.execute(
            "SELECT value_json FROM game_state WHERE key='new_game_setup'"
        ).fetchone()
        difficulty = json.loads(difficulty_row[0]).get("difficulty", "Normal") if difficulty_row else "Normal"
        from src.models.difficulty import DifficultyManager
        from src.models.staff import coach_training_multiplier
        development_rate = DifficultyManager(difficulty).player_development_rate
        coach_multipliers = {
            group: coach_training_multiplier(team_coach_rating(team_id, group, database_path))
            for group in ("batting", "bowling", "fielding", "mental")
        }
        for row in rows:
            if date.fromisoformat(training_date).weekday() not in json.loads(row["days_json"]):
                continue
            if row["overall"] >= row["potential"]:
                continue
            groups = focus_groups[row["focus"]]; progress = json.loads(row["progress_json"])
            documents = {name: json.loads(row[f"{name}_json"]) for name in ("batting", "bowling", "fielding", "mental")}
            rng = random.Random(f"{row['id']}:{training_date}")
            age_factor = 1.28 if row["age"] < 21 else 1.0 if row["age"] < 29 else .72 if row["age"] < 34 else .45
            potential_room = max(0, row["potential"] - row["overall"])
            potential_factor = .35 + min(1.15, potential_room / 18)
            intensity_factor = {"Light": .72, "Normal": 1.0, "Heavy": 1.32}.get(row["intensity"], 1.0)
            for group in groups:
                keys = ["fitness"] if row["focus"] == "Fitness" and group == "mental" else list(documents[group])
                for key in keys:
                    token = f"{group}.{key}"
                    # Roughly 1-3 focused points per season for an ordinary
                    # senior, with high-potential youth and elite facilities
                    # visibly progressing faster.
                    gain = rng.uniform(.045, .105) * (1 + (facility - 1) * .12) * development_rate
                    gain *= age_factor * potential_factor * intensity_factor * coach_multipliers[group]
                    # A focused regimen always devotes a meaningful share to
                    # its lead attribute. This avoids weeks of invisible UI
                    # progress for veterans whose overall potential remains in
                    # another attribute group.
                    if key == keys[0]:
                        gain += .04 * intensity_factor
                    progress[token] = progress.get(token, 0.0) + gain
                    if progress[token] >= 1 and documents[group][key] < 100:
                        documents[group][key] += 1; progress[token] -= 1; changed += 1
            overall = calculate_overall(row["role"], documents["batting"], documents["bowling"], documents["fielding"], documents["mental"])
            connection.execute(
                """UPDATE players SET batting_json=?, bowling_json=?, fielding_json=?, mental_json=?, overall=? WHERE id=?""",
                (json.dumps(documents["batting"]), json.dumps(documents["bowling"]), json.dumps(documents["fielding"]),
                 json.dumps(documents["mental"]), min(overall, row["potential"]), row["id"]),
            )
            connection.execute("UPDATE training_assignments SET progress_json=?, last_trained=? WHERE player_id=?",
                               (json.dumps(progress), training_date, row["id"]))
    return changed


#: Academy targeted-recruitment options. "Pace Bowler"/"Spin Bowler" both
#: generate role="Bowler" but bias the pace/swing_or_spin split so the
#: resulting player realistically plays as a seamer or a spinner.
ACADEMY_ROLE_FOCUSES = ["Any", "Batsman", "Pace Bowler", "Spin Bowler", "All-Rounder", "Wicketkeeper"]


def recruit_youth(team_id: int, focus_nationality: str = "English", count: int | None = None,
                  role_focus: str = "Any",
                  database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    rng = random.Random()
    count = count or rng.randint(3, 5); created_ids = []
    used_names: set[str] = set()
    with connect(database_path) as connection:
        team_row = connection.execute("SELECT academy_level,country_id FROM teams WHERE id = ?", (team_id,)).fetchone()
        academy_level = team_row["academy_level"]
        country_names = {"england":"England","australia":"Australia","india":"India","pakistan":"Pakistan",
                         "south_africa":"South Africa","new_zealand":"New Zealand","west_indies":"West Indies",
                         "bangladesh":"Bangladesh","sri_lanka":"Sri Lanka","afghanistan":"Afghanistan"}
        focus_nationality = country_names.get(team_row["country_id"], focus_nationality)
        used_names.update(row[0] for row in connection.execute("SELECT name FROM players"))
        roles = ["Batsman", "Bowler", "All-Rounder", "Wicketkeeper"]
        forced_role = {"Batsman": "Batsman", "Pace Bowler": "Bowler", "Spin Bowler": "Bowler",
                      "All-Rounder": "All-Rounder", "Wicketkeeper": "Wicketkeeper"}.get(role_focus)
        for _ in range(count):
            role = forced_role or rng.choice(roles)
            current, potential = _youth_current_and_potential(academy_level, rng)
            batting, bowling, fielding, mental = _make_attributes(role, current, 16, rng)
            if role_focus in ("Pace Bowler", "Spin Bowler"):
                # Keep the realistic bowler-vs-batter skill gap from
                # _make_attributes, but skew the seam/spin split so a
                # requested pace prospect plays genuinely quick, and a
                # requested spin prospect turns the ball, rather than
                # landing as an ambiguous medium-pacer.
                shift = rng.randint(14, 22)
                if role_focus == "Pace Bowler":
                    bowling["pace"] = clamp(bowling["pace"] + shift)
                    bowling["swing_or_spin"] = clamp(bowling["swing_or_spin"] - shift * .6)
                else:
                    bowling["swing_or_spin"] = clamp(bowling["swing_or_spin"] + shift)
                    bowling["pace"] = clamp(bowling["pace"] - shift * .6)
            physical = {"fitness":mental["fitness"],"endurance":mental["endurance"],"speed":fielding["agility"],
                        "agility":fielding["agility"],"strength":clamp((mental["fitness"]+batting["power"])/2)}
            overall = calculate_overall(role, batting, bowling, fielding, mental)
            name = _player_name(focus_nationality, used_names, rng)
            cursor = connection.execute(
                """INSERT INTO players
                   (name, age, nationality, role, batting_json, bowling_json, fielding_json, mental_json, physical_json,
                    overall, form, potential, team_id, contract_years_remaining, wage, bio, academy_squad)
                   VALUES (?,16,?,?,?,?,?,?,?,?,50,?,?,3,500,?,1)""",
                (name, focus_nationality, role, json.dumps(batting), json.dumps(bowling), json.dumps(fielding),
                 json.dumps(mental), json.dumps(physical), overall, potential, team_id, f"A newly recruited 16-year-old {role.lower()}."),
            )
            created_ids.append(int(cursor.lastrowid))
            connection.execute("INSERT INTO training_assignments (player_id, focus, progress_json) VALUES (?, 'None', '{}')",
                               (cursor.lastrowid,))
        placeholders = ",".join("?" for _ in created_ids)
        rows = connection.execute(f"SELECT * FROM players WHERE id IN ({placeholders})", created_ids).fetchall()
    return [_decode_player_row(row) for row in rows]


def start_facility_upgrade(team_id: int, facility: str, current_date: str,
                           database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    columns = {"Stadium": "stadium_level", "Training Ground": "training_level",
               "Medical Centre": "medical_level", "Academy": "academy_level",
               "Commercial Office": "commercial_level", "Scouting Network": "scouting_level",
               "Grounds Department": "grounds_level"}
    if facility not in columns:
        raise ValueError("Unknown facility")
    with connect(database_path) as connection:
        pending = connection.execute(
            "SELECT 1 FROM facility_upgrades WHERE team_id=? AND facility=? AND status='BUILDING'", (team_id, facility)
        ).fetchone()
        if pending: raise ValueError("An upgrade is already in progress.")
        level, cash = connection.execute(f"SELECT {columns[facility]}, cash FROM teams WHERE id=?", (team_id,)).fetchone()
        if level >= 5: raise ValueError("This facility is already at maximum level.")
        base_cost = {"Stadium": 2_500_000, "Training Ground": 1_400_000,
                     "Medical Centre": 1_100_000, "Academy": 1_250_000,
                     "Commercial Office": 900_000, "Scouting Network": 1_050_000,
                     "Grounds Department": 800_000}[facility]
        cost = int(base_cost * (1 + (level - 1) * .75))
        if cash < cost: raise ValueError("The club does not have enough cash.")
        completion = date.fromisoformat(current_date).fromordinal(date.fromisoformat(current_date).toordinal() + 7).isoformat()
        connection.execute("UPDATE teams SET cash = cash - ? WHERE id = ?", (cost, team_id))
        cursor = connection.execute(
            """INSERT INTO facility_upgrades (team_id, facility, target_level, cost, completion_date, status)
               VALUES (?, ?, ?, ?, ?, 'BUILDING')""", (team_id, facility, level + 1, cost, completion))
        row = connection.execute("SELECT * FROM facility_upgrades WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(row)


def complete_due_facility_upgrades(team_id: int, current_date: str,
                                   database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[str]:
    columns = {"Stadium": "stadium_level", "Training Ground": "training_level",
               "Medical Centre": "medical_level", "Academy": "academy_level",
               "Commercial Office": "commercial_level", "Scouting Network": "scouting_level",
               "Grounds Department": "grounds_level"}
    completed = []
    with connect(database_path) as connection:
        rows = connection.execute(
            """SELECT * FROM facility_upgrades WHERE team_id=? AND status='BUILDING' AND completion_date<=?""",
            (team_id, current_date),
        ).fetchall()
        for row in rows:
            connection.execute(f"UPDATE teams SET {columns[row['facility']]}=? WHERE id=?", (row["target_level"], team_id))
            if row["facility"] == "Stadium":
                connection.execute("UPDATE teams SET stadium_capacity = stadium_capacity + 5000 WHERE id=?", (team_id,))
            connection.execute("UPDATE facility_upgrades SET status='COMPLETE' WHERE id=?", (row["id"],))
            completed.append(row["facility"])
    return completed


def fetch_facility_upgrades(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        return [dict(row) for row in connection.execute(
            "SELECT * FROM facility_upgrades WHERE team_id=? ORDER BY id DESC", (team_id,)
        ).fetchall()]


ACCESSIBILITY_COLUMNS = {"reduced_motion": "INTEGER DEFAULT 0",
                         "colour_blind_mode": "INTEGER DEFAULT 1",
                         "ui_scale": "REAL DEFAULT 1.0"}


def update_user_settings(settings: Mapping[str, Any], database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    allowed = {"game_speed", "sound_on", "master_volume", "resolution", "auto_save_frequency",
               "currency", *ACCESSIBILITY_COLUMNS}
    updates = [(key, value) for key, value in settings.items() if key in allowed]
    if not updates: return
    with connect(database_path) as connection:
        for column, definition in ACCESSIBILITY_COLUMNS.items():
            try:
                connection.execute(f"ALTER TABLE user_data ADD COLUMN {column} {definition}")
            except sqlite3.OperationalError:
                pass  # column already exists (post-0.19 saves)
        assignment = ", ".join(f"{key}=?" for key, _ in updates)
        connection.execute(f"UPDATE user_data SET {assignment} WHERE id=1", tuple(value for _, value in updates))


def set_board_objectives(team_id: int, objectives: dict[str, Any],
                         database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Store season objectives for the user's club in game_state."""
    key = f"board_objectives_{team_id}"
    save_game({key: objectives}, database_path)


def get_board_objectives(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Retrieve season objectives, returning sensible defaults if unset."""
    key = f"board_objectives_{team_id}"
    with connect(database_path) as connection:
        row = connection.execute("SELECT value_json FROM game_state WHERE key=?", (key,)).fetchone()
    if row:
        return json.loads(row[0])
    return {"league_position": 6, "minimum_cash": 100_000, "youth_developed": 0}


def record_board_confidence(team_id: int, score: int, label: str, match_date: str,
                             database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Append a board-confidence snapshot to the history ring in game_state."""
    key = f"board_confidence_history_{team_id}"
    with connect(database_path) as connection:
        row = connection.execute("SELECT value_json FROM game_state WHERE key=?", (key,)).fetchone()
    history = json.loads(row[0]) if row else []
    history.append({"date": match_date, "score": score, "label": label})
    if len(history) > 20:
        history = history[-20:]
    save_game({key: history}, database_path)


def get_board_confidence_history(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict]:
    """Retrieve stored board-confidence snapshots."""
    key = f"board_confidence_history_{team_id}"
    with connect(database_path) as connection:
        row = connection.execute("SELECT value_json FROM game_state WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else []


def evaluate_board_objectives(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Score current progress against the board's season objectives.

    Returns objectives, current standings position, cash, and a progress
    dict for each objective so callers can render a live tracker.
    """
    objectives = get_board_objectives(team_id, database_path)
    with connect(database_path) as connection:
        user = connection.execute("SELECT current_date FROM user_data WHERE id=1").fetchone()
        current_date = user["current_date"] if user else date.today().isoformat()
        team = connection.execute("SELECT cash FROM teams WHERE id=?", (team_id,)).fetchone()
        cash = int(team[0]) if team else 0
        comp = connection.execute(
            "SELECT id FROM competitions WHERE name='Domestic Division 1' AND season=?",
            (date.fromisoformat(current_date).year,),
        ).fetchone()
        position = None
        if comp:
            row = connection.execute(
                """SELECT team_id, position FROM (
                    SELECT team_id, ROW_NUMBER() OVER (ORDER BY points DESC, net_run_rate DESC) AS position
                    FROM league_standings WHERE competition_id=?) WHERE team_id=?""",
                (comp[0], team_id),
            ).fetchone()
            position = row["position"] if row else None
            if row is None:
                standings_row = connection.execute(
                    "SELECT team_id FROM league_standings WHERE competition_id=? ORDER BY points DESC, won DESC, net_run_rate DESC",
                    (comp[0],)
                ).fetchall()
                position = next((i + 1 for i, r in enumerate(standings_row) if r[0] == team_id), None)
    league_target = objectives.get("league_position", 6)
    cash_target = objectives.get("minimum_cash", 100_000)
    progress: dict[str, Any] = {
        "league_position": {"target": league_target, "current": position, "met": position is not None and position <= league_target},
        "cash_balance": {"target": cash_target, "current": cash, "met": cash >= cash_target},
    }
    return {"objectives": objectives, "progress": progress, "current_date": current_date}


PITCH_TYPES = ["Green", "Dry", "Dusty", "Flat", "Worn"]
PITCH_DESCRIPTIONS = {
    "Green": "Grassy surface favouring seam and swing bowlers. Pace and bounce are amplified.",
    "Dry": "Hard, arid pitch offering some assistance to spinners. Moderate pace, low bounce.",
    "Dusty": "Loose surface that deteriorates quickly. Spinners extract big turn from day one.",
    "Flat": "Hard, true-bouncing deck. Batters dominate; high-scoring matches expected.",
    "Worn": "Old pitch with variable bounce and cracks. Favours spin and reverse swing.",
}


def set_pitch_selection(team_id: int, pitch: str, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Store the home team's chosen pitch for their next match."""
    if pitch not in PITCH_TYPES:
        raise ValueError(f"Invalid pitch type: {pitch}. Must be one of {PITCH_TYPES}")
    key = f"pitch_selection_{team_id}"
    save_game({key: {"pitch": pitch}}, database_path)


def get_pitch_selection(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> str:
    """Retrieve the home team's chosen pitch, defaulting to 'Green'."""
    key = f"pitch_selection_{team_id}"
    with connect(database_path) as connection:
        row = connection.execute("SELECT value_json FROM game_state WHERE key=?", (key,)).fetchone()
    if row:
        data = json.loads(row[0])
        return data.get("pitch", "Green")
    return "Green"


def generate_job_offers(user_team_id: int, user_reputation: int,
                        database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Generate job offers from clubs whose AI manager is underperforming.

    Clubs in the bottom half with low cash or poor standings may seek a
    new manager. Offers scale with the user's reputation — higher reputation
    attracts offers from better clubs.
    """
    offers: list[dict[str, Any]] = []
    rng = random.Random(f"job_offers:{user_team_id}:{user_reputation}")
    with connect(database_path) as connection:
        user_division = connection.execute(
            "SELECT division FROM teams WHERE id=?", (user_team_id,)
        ).fetchone()
        if not user_division:
            return offers
        user_div = user_division[0]
        teams = [dict(r) for r in connection.execute(
            "SELECT id, name, division, cash FROM teams WHERE id != ?",
            (user_team_id,)
        ).fetchall()]
        for team in teams:
            if rng.random() > 0.12:
                continue
            if team["cash"] < 50_000:
                continue
            squad_size = connection.execute(
                "SELECT COUNT(*) FROM players WHERE team_id=?", (team["id"],)
            ).fetchone()[0]
            if squad_size < 10:
                continue
            avg_overall = connection.execute(
                "SELECT ROUND(AVG(overall),1) FROM players WHERE team_id=?", (team["id"],)
            ).fetchone()[0] or 50
            eligible = (avg_overall >= 55 and team["division"] <= user_div)
            if not eligible:
                continue
            competition = connection.execute(
                """SELECT c.id FROM competitions c
                   JOIN league_standings ls ON ls.competition_id = c.id
                   WHERE c.name = ? AND c.season = (SELECT strftime('%Y', current_date) FROM user_data WHERE id=1)
                   LIMIT 1""",
                (f"Domestic Division {team['division']}",)
            ).fetchone()
            position = None
            if competition:
                standings = connection.execute(
                    """SELECT team_id, ROW_NUMBER() OVER (ORDER BY points DESC, net_run_rate DESC) AS pos
                       FROM league_standings WHERE competition_id=?""",
                    (competition[0],)
                ).fetchall()
                for row in standings:
                    if row[0] == team["id"]:
                        position = row[1]
                        break
            if position and position <= 6:
                continue
            wage = max(1_000, int(avg_overall * rng.uniform(40, 80)))
            offer = {
                "offer_id": f"job_{team['id']}_{user_team_id}",
                "team_id": team["id"],
                "team_name": team["name"],
                "division": team["division"],
                "squad_size": squad_size,
                "average_overall": avg_overall,
                "position": position,
                "wage": wage,
                "description": _job_offer_description(team, position, avg_overall),
            }
            offers.append(offer)
    offers.sort(key=lambda o: o["average_overall"], reverse=True)
    return offers[:5]


def _job_offer_description(team: dict, position: int | None, avg_overall: float) -> str:
    pos_str = f"currently {position}" if position else "mid-table"
    if avg_overall >= 70:
        ambition = "A strong squad with title ambitions."
    elif avg_overall >= 60:
        ambition = "A competitive squad looking to push up the table."
    else:
        ambition = "A rebuilding project with young talent to develop."
    return f"{team['name']} ({pos_str}) — {ambition}"


def get_job_offers(database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Retrieve pending job offers from game_state."""
    with connect(database_path) as connection:
        user_team = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()
        if not user_team:
            return []
    key = f"job_offers_{user_team[0]}"
    with connect(database_path) as connection:
        row = connection.execute("SELECT value_json FROM game_state WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else []


def store_job_offers(team_id: int, offers: list[dict],
                     database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Persist generated job offers in game_state."""
    key = f"job_offers_{team_id}"
    save_game({key: offers}, database_path)


def accept_job_offer(offer_id: str, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Accept a job offer: switch the manager to the new club.

    Returns details of the move for the caller to display.
    """
    offers = get_job_offers(database_path)
    offer = next((o for o in offers if o["offer_id"] == offer_id), None)
    if not offer:
        raise ValueError(f"Unknown or expired job offer: {offer_id}")
    new_team_id = offer["team_id"]
    new_team_name = offer["team_name"]
    old_team_id = None
    with connect(database_path) as connection:
        row = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()
        if row:
            old_team_id = row[0]
        connection.execute("UPDATE user_data SET current_team_id=? WHERE id=1", (new_team_id,))
    remaining = [o for o in offers if o["offer_id"] != offer_id]
    store_job_offers(new_team_id, remaining, database_path)
    return {
        "old_team_id": old_team_id,
        "new_team_id": new_team_id,
        "new_team_name": new_team_name,
        "wage": offer["wage"],
    }


def decline_job_offer(offer_id: str, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Remove a job offer from the pending list."""
    offers = get_job_offers(database_path)
    remaining = [o for o in offers if o["offer_id"] != offer_id]
    with connect(database_path) as connection:
        user_team = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()
        if user_team:
            store_job_offers(user_team[0], remaining, database_path)


def check_sacking(user_team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any] | None:
    """Check if the manager should be sacked based on board confidence.

    Returns a sacking dict if confidence has been at 'Ultimatum' for 3+
    consecutive reviews, otherwise None.
    """
    history = get_board_confidence_history(user_team_id, database_path)
    if len(history) < 3:
        return None
    recent = history[-3:]
    all_ultimatum = all(h["label"] == "Ultimatum" for h in recent)
    if not all_ultimatum:
        return None
    with connect(database_path) as connection:
        team = connection.execute("SELECT name FROM teams WHERE id=?", (user_team_id,)).fetchone()
        team_name = team[0] if team else "Unknown"
    return {
        "sacked": True,
        "team_id": user_team_id,
        "team_name": team_name,
        "reason": "The board has lost confidence after three consecutive Ultimatum reviews.",
    }


# ---------------------------------------------------------------------------
# Custom tournaments
# ---------------------------------------------------------------------------

TOURNAMENT_FORMATS = {"T10", "T20", "ODI", "Hundred", "Test"}


def _generate_round_robin(team_ids: list[int], home_away: bool = True) -> list[tuple[int, int]]:
    """Circle-method round-robin fixture pairs.

    Returns unique pairings.  When *home_away* is True both legs are
    returned (home ↔ away).
    """
    teams = list(team_ids)
    n = len(teams)
    rotation = list(teams)
    rounds: list[list[tuple[int, int]]] = []
    for _ in range(n - 1):
        pairs = [(rotation[i], rotation[-1 - i]) for i in range(n // 2)]
        rounds.append(pairs)
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    all_pairs = [p for rnd in rounds for p in rnd]
    if home_away:
        all_pairs += [(away, home) for home, away in all_pairs]
    return all_pairs


def create_custom_tournament(
    name: str,
    match_format: str,
    team_ids: list[int],
    advance_per_group: int,
    season: int,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Create a custom tournament with group stage (round-robin) fixtures.

    Teams are assigned to groups alphabetically by seeded order.  Each
    group becomes a ``'League'`` competition so that
    ``CompetitionEngine.simulate_fixture`` updates standings automatically.

    Returns a summary dict with tournament_id and group details.
    """
    if match_format not in TOURNAMENT_FORMATS:
        raise ValueError(f"Unsupported format: {match_format}")
    if len(team_ids) < 4:
        raise ValueError("A tournament requires at least 4 teams.")
    if advance_per_group < 1:
        raise ValueError("At least 1 team must advance from each group.")

    group_count = 2 if len(team_ids) <= 8 else 3 if len(team_ids) <= 16 else 4
    groups: dict[int, list[int]] = {i: [] for i in range(group_count)}
    for idx, team_id in enumerate(team_ids):
        groups[idx % group_count].append(team_id)

    with connect(database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO custom_tournaments (name, format, season, groups_json, advance_per_group, status) "
            "VALUES (?,?,?,?,?,?)",
            (name, match_format, season, json.dumps({str(k): v for k, v in groups.items()}),
             advance_per_group, "group_stage"),
        )
        tournament_id = cursor.lastrowid
        competition_ids: dict[int, int] = {}
        start_date = date(season, 4, 15)
        for g_idx, g_teams in groups.items():
            group_label = chr(65 + g_idx)
            comp_name = f"{name} — Group {group_label}"
            comp_id = connection.execute(
                "INSERT INTO competitions (name, type, season, tournament_id) VALUES (?,'League',?,?)",
                (comp_name, season, tournament_id),
            ).lastrowid
            competition_ids[g_idx] = comp_id
            connection.executemany(
                "INSERT OR IGNORE INTO league_standings (competition_id,team_id) VALUES (?,?)",
                [(comp_id, tid) for tid in g_teams],
            )
            pairs = _generate_round_robin(g_teams, home_away=True)
            for pair_idx, (home, away) in enumerate(pairs):
                match_date = start_date + timedelta(days=pair_idx * 3)
                venue = connection.execute(
                    "SELECT name FROM teams WHERE id=?", (home,)
                ).fetchone()[0] + " Ground"
                connection.execute(
                    """INSERT INTO matches
                       (home_team,away_team,format,date,venue,completed,result_json,
                        competition_id,round_name)
                       VALUES (?,?,?,?,?,'0','{}',?,?)""",
                    (home, away, match_format, match_date.isoformat(), venue,
                     comp_id, f"Group {group_label} Round {pair_idx + 1}"),
                )
        connection.execute(
            "INSERT INTO game_state (key,value_json) VALUES (?,?)",
            (f"tournament_competitions_{tournament_id}",
             json.dumps({str(k): v for k, v in competition_ids.items()})),
        )
    return {"tournament_id": tournament_id, "groups": {chr(65 + k): v for k, v in groups.items()},
            "competition_ids": competition_ids}


def get_custom_tournaments(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> list[dict[str, Any]]:
    """Return all custom tournaments."""
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM custom_tournaments ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_custom_tournament(
    tournament_id: int,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any] | None:
    """Return full details of a custom tournament including group assignments."""
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM custom_tournaments WHERE id=?", (tournament_id,)
        ).fetchone()
        if not row:
            return None
        tournament = dict(row)
        groups_raw = json.loads(tournament["groups_json"])
        groups: dict[str, list[dict[str, Any]]] = {}
        for g_label, team_ids in groups_raw.items():
            team_list = []
            for tid in team_ids:
                trow = connection.execute(
                    "SELECT id, name, division FROM teams WHERE id=?", (tid,)
                ).fetchone()
                if trow:
                    team_list.append(dict(trow))
            groups[g_label] = team_list
        tournament["groups"] = groups
        del tournament["groups_json"]
        comp_key = f"tournament_competitions_{tournament_id}"
        comp_row = connection.execute(
            "SELECT value_json FROM game_state WHERE key=?", (comp_key,)
        ).fetchone()
        tournament["competition_ids"] = json.loads(comp_row[0]) if comp_row else {}
    return tournament


def get_tournament_standings(
    tournament_id: int,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Return group standings for a custom tournament."""
    comp_key = f"tournament_competitions_{tournament_id}"
    with connect(database_path) as connection:
        comp_row = connection.execute(
            "SELECT value_json FROM game_state WHERE key=?", (comp_key,)
        ).fetchone()
        if not comp_row:
            return {"groups": {}}
        comp_ids = json.loads(comp_row[0])
        groups: dict[str, list[dict[str, Any]]] = {}
        for g_label, comp_id in comp_ids.items():
            standings = [dict(r) for r in connection.execute(
                """SELECT ls.*, t.name AS team_name FROM league_standings ls
                   JOIN teams t ON t.id = ls.team_id
                   WHERE ls.competition_id=?
                   ORDER BY ls.points DESC, ls.net_run_rate DESC""",
                (comp_id,),
            ).fetchall()]
            groups[g_label] = standings
    return {"groups": groups}


def advance_tournament_to_knockout(
    tournament_id: int,
    season: int,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any] | None:
    """When all group matches are complete, create the knockout bracket.

    Returns the bracket dict or ``None`` if groups are not yet finished.
    """
    comp_key = f"tournament_competitions_{tournament_id}"
    with connect(database_path) as connection:
        tournament = connection.execute(
            "SELECT * FROM custom_tournaments WHERE id=?", (tournament_id,)
        ).fetchone()
        if not tournament or tournament["status"] != "group_stage":
            return None
        comp_row = connection.execute(
            "SELECT value_json FROM game_state WHERE key=?", (comp_key,)
        ).fetchone()
        if not comp_row:
            return None
        comp_ids = json.loads(comp_row[0])
        advance_count = tournament["advance_per_group"]
        winners: list[int] = []
        for g_label in sorted(comp_ids.keys()):
            comp_id = comp_ids[g_label]
            unfinished = connection.execute(
                "SELECT COUNT(*) FROM matches WHERE competition_id=? AND completed=0",
                (comp_id,),
            ).fetchone()[0]
            if unfinished > 0:
                return None
            rows = connection.execute(
                """SELECT team_id FROM league_standings
                   WHERE competition_id=?
                   ORDER BY points DESC, net_run_rate DESC LIMIT ?""",
                (comp_id, advance_count),
            ).fetchall()
            winners.extend(r[0] for r in rows)
        match_format = tournament["format"]
        cup_name = f"{tournament['name']} — Knockout"
        cup_comp_id = connection.execute(
            "INSERT INTO competitions (name, type, season, tournament_id) VALUES (?,'Cup',?,?)",
            (cup_name, season, tournament_id),
        ).lastrowid
        connection.execute(
            "UPDATE custom_tournaments SET status='knockout' WHERE id=?", (tournament_id,)
        )
        bracket: dict[str, list[dict[str, Any]]] = {}
        if len(winners) < 2:
            return {"bracket": bracket, "winner": winners[0] if winners else None}
        rng = random.Random(tournament_id)
        rng.shuffle(winners)
        round_name = _knockout_round_name(len(winners))
        bracket[round_name] = []
        knockout_date = date(season, 7, 1)
        for i in range(0, len(winners), 2):
            if i + 1 >= len(winners):
                break
            home, away = winners[i], winners[i + 1]
            venue = connection.execute(
                "SELECT name FROM teams WHERE id=?", (home,)
            ).fetchone()[0] + " Ground"
            connection.execute(
                """INSERT INTO matches
                   (home_team,away_team,format,date,venue,completed,result_json,
                    competition_id,round_name)
                   VALUES (?,?,?,?,?,'0','{}',?,?)""",
                (home, away, match_format, knockout_date.isoformat(), venue,
                 cup_comp_id, round_name),
            )
            bracket[round_name].append({"home": home, "away": away})
        comp_ids["knockout"] = cup_comp_id
        connection.execute(
            "UPDATE game_state SET value_json=? WHERE key=?",
            (json.dumps(comp_ids), comp_key),
        )
    return {"bracket": bracket, "round_name": round_name}


def _knockout_round_name(num_teams: int) -> str:
    """Map team count to a round name."""
    mapping = {2: "Final", 4: "Semi-final", 8: "Quarter-final",
               16: "Round of 16", 32: "Round of 32"}
    return mapping.get(num_teams, f"Round of {num_teams}")


def get_tournament_bracket(
    tournament_id: int,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Return the knockout bracket for a custom tournament."""
    comp_key = f"tournament_competitions_{tournament_id}"
    with connect(database_path) as connection:
        tournament = connection.execute(
            "SELECT status FROM custom_tournaments WHERE id=?", (tournament_id,)
        ).fetchone()
        if not tournament:
            return {"bracket": {}, "status": None}
        comp_row = connection.execute(
            "SELECT value_json FROM game_state WHERE key=?", (comp_key,)
        ).fetchone()
        if not comp_row:
            return {"bracket": {}, "status": tournament["status"]}
        comp_ids = json.loads(comp_row[0])
        knockout_id = comp_ids.get("knockout")
        if not knockout_id:
            return {"bracket": {}, "status": tournament["status"]}
        rounds: dict[str, list[dict[str, Any]]] = {}
        matches = connection.execute(
            "SELECT * FROM matches WHERE competition_id=? ORDER BY date",
            (knockout_id,),
        ).fetchall()
        for m in matches:
            rnd = m["round_name"]
            if rnd not in rounds:
                rounds[rnd] = []
            result = json.loads(m["result_json"]) if m["result_json"] != "{}" else None
            rounds[rnd].append({
                "match_id": m["id"],
                "home": m["home_team"],
                "away": m["away_team"],
                "completed": bool(m["completed"]),
                "result": result,
            })
    return {"bracket": rounds, "status": tournament["status"]}


# ---------------------------------------------------------------------------
# Onboarding tutorial
# ---------------------------------------------------------------------------

ONBOARDING_STEPS: list[dict[str, Any]] = [
    {
        "id": "welcome",
        "title": "Welcome to your new club!",
        "description": (
            "This is your Dashboard — the nerve centre of your club. "
            "Check today's fixture, league standing, and board confidence "
            "at a glance. Use the sidebar to navigate to any screen."
        ),
        "screen": "Dashboard",
        "position": "centre",
    },
    {
        "id": "squad",
        "title": "Meet your squad",
        "description": (
            "The Squad screen shows every player at your club. Sort by "
            "rating, role, age or form. Click any player to see their "
            "full profile with batting, bowling and fielding attributes."
        ),
        "screen": "Squad",
        "position": "centre",
    },
    {
        "id": "selection",
        "title": "Pick your XI",
        "description": (
            "Before each match, choose your starting eleven in the "
            "Selection screen. Drag players into position, set the "
            "batting order, assign a captain and wicketkeeper."
        ),
        "screen": "Selection",
        "position": "centre",
    },
    {
        "id": "training",
        "title": "Develop your players",
        "description": (
            "Training lets you focus development on Batting, Bowling, "
            "Fielding or Fitness. Better coaches earn faster gains — "
            "visit the Staff screen to hire specialists."
        ),
        "screen": "Training",
        "position": "centre",
    },
    {
        "id": "transfers",
        "title": "Strengthen your squad",
        "description": (
            "The Transfer Market lists players available from every club. "
            "Scout targets to reveal their true attributes, then submit "
            "an offer with a fee and wage contract."
        ),
        "screen": "Transfers",
        "position": "centre",
    },
    {
        "id": "match_day",
        "title": "Match day!",
        "description": (
            "When your fixture arrives, click Sim to Match to enter the "
            "live ball-by-ball engine. Set fielding presets, change "
            "bowlers, review DRS decisions, and watch the action unfold."
        ),
        "screen": "Match",
        "position": "centre",
    },
    {
        "id": "finances",
        "title": "Mind the budget",
        "description": (
            "Your club's Finances screen tracks income from tickets, "
            "sponsorships and prize money against wage bills and transfer "
            "spending. Keep the board happy with healthy cash reserves."
        ),
        "screen": "Finances",
        "position": "centre",
    },
]


def _onboarding_key() -> str:
    return "onboarding_state"


def get_onboarding_state(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Return the current onboarding tutorial state.

    If no state exists yet, returns the initial state with the first
    step active and no steps completed.
    """
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT value_json FROM game_state WHERE key=?",
            (_onboarding_key(),),
        ).fetchone()
    if row:
        return json.loads(row[0])
    return {"completed_steps": [], "current_step": "welcome", "dismissed": False}


def advance_onboarding(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Advance to the next onboarding step.

    Marks the current step as completed and activates the next one.
    Returns the updated state.
    """
    state = get_onboarding_state(database_path)
    completed = list(state.get("completed_steps", []))
    current = state.get("current_step")
    if current and current not in completed:
        completed.append(current)
    step_ids = [s["id"] for s in ONBOARDING_STEPS]
    try:
        idx = step_ids.index(current) if current else -1
    except ValueError:
        idx = -1
    next_step = step_ids[idx + 1] if idx + 1 < len(step_ids) else None
    new_state = {
        "completed_steps": completed,
        "current_step": next_step,
        "dismissed": next_step is None,
    }
    save_game({_onboarding_key(): new_state}, database_path)
    return new_state


def dismiss_onboarding(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Dismiss (skip) the entire onboarding tutorial.

    Marks all steps as completed and sets dismissed=True.
    Returns the updated state.
    """
    step_ids = [s["id"] for s in ONBOARDING_STEPS]
    new_state = {
        "completed_steps": step_ids,
        "current_step": None,
        "dismissed": True,
    }
    save_game({_onboarding_key(): new_state}, database_path)
    return new_state


if __name__ == "__main__":
    created_path = initialise_database()
    game = load_game(created_path)
    club = get_team_summary(game["user"]["current_team_id"], created_path)
    print(f"Database ready: {created_path}")
    print(f"{club['name']}: {club['player_count']} players, average overall {club['average_overall']}")
