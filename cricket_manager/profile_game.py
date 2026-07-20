"""Repeatable performance benchmark for release checks."""
from __future__ import annotations

import cProfile
import io
from pathlib import Path
import pstats
import tempfile
from tempfile import TemporaryDirectory
from time import perf_counter

from database import fetch_players, get_team_summary, initialise_database
from match_engine import Match


def profile_release() -> dict[str, float]:
    with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        database = Path(directory) / "profile.db"
        initialise_database(database)
        home, away = get_team_summary(1, database), get_team_summary(2, database)
        home_xi, away_xi = fetch_players(1, database)[:11], fetch_players(2, database)[:11]
        profiler = cProfile.Profile(); profiler.enable()
        started = perf_counter()
        match = Match(home, away, home_xi, away_xi, "ODI", seed=2026, batting_first_id=1)
        match.simulate()
        match_seconds = perf_counter() - started
        query_started = perf_counter()
        for _ in range(100): fetch_players(1, database)
        query_seconds = perf_counter() - query_started
        profiler.disable()
        output = io.StringIO()
        pstats.Stats(profiler, stream=output).sort_stats("cumtime").print_stats(20)
        profile_path = Path("logs/profile.txt")
        try:
            profile_path.parent.mkdir(exist_ok=True); profile_path.write_text(output.getvalue(), encoding="utf-8")
        except OSError:
            profile_path = Path(tempfile.gettempdir()) / "Stumped" / "profile.txt"
            profile_path.parent.mkdir(parents=True, exist_ok=True); profile_path.write_text(output.getvalue(), encoding="utf-8")
        return {"odi_seconds": match_seconds, "one_hundred_squad_queries": query_seconds,
                "profile_path": str(profile_path.resolve())}


if __name__ == "__main__":
    results = profile_release()
    print(f"ODI simulation: {results['odi_seconds']:.4f}s")
    print(f"100 squad queries: {results['one_hundred_squad_queries']:.4f}s")
    print(f"Detailed profile: {results['profile_path']}")
