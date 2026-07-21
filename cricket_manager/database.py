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
from datetime import date
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


def _target_rating(division: int, age: int, rng: random.Random) -> float:
    """Draw a current-ability target centred near 70 (D1) or 55 (D2)."""
    base = 70 if division == 1 else 55
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
) -> dict[str, Any]:
    """Generate one complete player record suitable for database insertion."""
    role_cycle = ["Batsman"] * 9 + ["Bowler"] * 8 + ["All-Rounder"] * 5 + ["Wicketkeeper"] * 3
    role = role_cycle[roster_slot % len(role_cycle)]
    age = _age_for_roster_slot(roster_slot, rng)
    nationality = home_nationality if rng.random() < 0.76 else rng.choice(list(NAMES))
    target = _target_rating(division, age, rng)
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

CREATE INDEX IF NOT EXISTS idx_financial_team_date ON financial_log(team_id, date);
CREATE INDEX IF NOT EXISTS idx_transfer_offer_team ON transfer_offers(to_team, from_team, status);
CREATE INDEX IF NOT EXISTS idx_injuries_player_active ON injuries(player_id, active);
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
    _ensure_column(connection, "training_assignments", "intensity", "TEXT NOT NULL DEFAULT 'Normal'")
    _ensure_column(connection, "training_assignments", "days_json", "TEXT NOT NULL DEFAULT '[0,2,4]'")
    _ensure_column(connection, "matches", "competition_id", "INTEGER REFERENCES competitions(id)")
    _ensure_column(connection, "matches", "round_name", "TEXT NOT NULL DEFAULT 'League'")
    _ensure_column(connection, "user_data", "master_volume", "INTEGER NOT NULL DEFAULT 70 CHECK (master_volume BETWEEN 0 AND 100)")
    _ensure_column(connection, "user_data", "currency", "TEXT NOT NULL DEFAULT 'GBP'")
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


def seed_database(connection: sqlite3.Connection, seed: int = 20260401) -> None:
    """Populate a new database. Existing team data is never duplicated."""
    if connection.execute("SELECT COUNT(*) FROM teams").fetchone()[0] > 0:
        _expand_world_to_twenty_four(connection, seed)
        _seed_phase_25_data(connection)
        _seed_phase_3_data(connection)
        return

    rng = random.Random(seed)
    used_names: set[str] = set()
    country_aliases = {"English": "england", "Australian": "australia", "Indian": "india",
                       "Pakistani": "pakistan", "South African": "south_africa",
                       "New Zealander": "new_zealand", "West Indian": "west_indies"}
    for team_id, (name, division, nationality) in enumerate(TEAM_DEFINITIONS, start=1):
        capacity = rng.randrange(18_000, 36_001, 500) if division == 1 else rng.randrange(8_000, 20_001, 500)
        cash = rng.randrange(8_000_000, 15_000_001, 250_000) if division == 1 else rng.randrange(3_000_000, 8_000_001, 250_000)
        connection.execute(
            """INSERT INTO teams
               (id, name, division, cash, stadium_capacity, training_level, medical_level, academy_level, country_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (team_id, name, division, cash, capacity, 3 if division == 1 else 2, 2, 2,
             country_aliases[nationality]),
        )

        for slot in range(25):
            player = generate_player(team_id, division, nationality, slot, rng, used_names)
            columns = ", ".join(player)
            placeholders = ", ".join("?" for _ in player)
            connection.execute(
                f"INSERT INTO players ({columns}) VALUES ({placeholders})",
                tuple(player.values()),
            )

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
        connection.execute(
            """INSERT INTO teams
               (id,name,division,cash,stadium_capacity,training_level,medical_level,academy_level,country_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (team_id, name, division, cash, capacity, 3 if division == 1 else 2, 2, 2, aliases[nationality]),
        )
        for slot in range(25):
            player = generate_player(team_id, division, nationality, slot, rng, used_names)
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
    return dict(row)


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
    """Persist bounded form/progression changes and match injuries atomically."""
    from datetime import timedelta
    start = date.fromisoformat(current_date)
    with connect(database_path) as connection:
        for player_id, change in updates.items():
            connection.execute(
                """UPDATE players SET
                       form=MAX(0, MIN(100, form + ?)),
                       overall=MAX(0, MIN(potential, overall + ?))
                   WHERE id=?""",
                (float(change.get("form", 0)), float(change.get("overall", 0)), int(player_id)),
            )
        for injury in injuries:
            days = max(1, int(injury.get("days", 7)))
            connection.execute(
                """INSERT INTO injuries(player_id, severity, start_date, return_date, active)
                   VALUES (?, ?, ?, ?, 1)""",
                (int(injury["player_id"]), str(injury["severity"]), current_date, (start + timedelta(days=days)).isoformat()),
            )


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
               ORDER BY s.points DESC, s.net_run_rate DESC, t.name""", (competition[0],)
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
    from src.models.transfer import sale_assessment
    decoded = []
    for row in rows:
        player = _decode_player_row(row)
        assessment = sale_assessment(player, team_cash=8_000_000, team_reputation=60)
        player.update({"for_sale": assessment["available"], "sale_reason": assessment["reason"],
                       "asking_price": assessment["price"]})
        decoded.append(player)
    return decoded


def set_transfer_listed(player_id: int, listed: bool,
                        database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    with connect(database_path) as connection:
        connection.execute("UPDATE players SET transfer_listed = ? WHERE id = ?", (int(listed), player_id))


def _decode_player_row(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
    player = dict(row)
    for field in ("batting_json", "bowling_json", "fielding_json", "mental_json", "physical_json"):
        if field in player:
            player[field.removesuffix("_json")] = json.loads(player.pop(field))
    return player


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
        development_rate = DifficultyManager(difficulty).player_development_rate
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
                    gain *= age_factor * potential_factor * intensity_factor
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


def recruit_youth(team_id: int, focus_nationality: str = "English", count: int | None = None,
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
        for _ in range(count):
            role = rng.choice(roles); current = rng.randint(20, 50); potential = min(90, rng.randint(40, 85) + academy_level - 1)
            batting, bowling, fielding, mental = _make_attributes(role, current, 16, rng)
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


def update_user_settings(settings: Mapping[str, Any], database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    allowed = {"game_speed", "sound_on", "master_volume", "resolution", "auto_save_frequency", "currency"}
    updates = [(key, value) for key, value in settings.items() if key in allowed]
    if not updates: return
    with connect(database_path) as connection:
        assignment = ", ".join(f"{key}=?" for key, _ in updates)
        connection.execute(f"UPDATE user_data SET {assignment} WHERE id=1", tuple(value for _, value in updates))


if __name__ == "__main__":
    created_path = initialise_database()
    game = load_game(created_path)
    club = get_team_summary(game["user"]["current_team_id"], created_path)
    print(f"Database ready: {created_path}")
    print(f"{club['name']}: {club['player_count']} players, average overall {club['average_overall']}")
