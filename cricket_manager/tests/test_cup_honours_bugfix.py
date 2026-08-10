"""v4.67.0: a real, pre-existing bug found while adding a third Cup-type
competition (the Academy Cup). `rollover_season`'s cup-final lookup used to
pick a single "most recent Cup final" (`ORDER BY date DESC LIMIT 1`) with
no competition-name filter — once a second cup (the T20 Cup) existed,
only whichever cup's final happened to land latest in the season ever
actually got a "Cup Winners" honour/inbox message; the other cup's real
winner was silently skipped every single season.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import database
from competition import CompetitionEngine


def _fresh_db() -> str:
    db = os.path.join(tempfile.mkdtemp(), "cup_honours.db")
    database.initialise_database(db)
    return db


class CupHonoursMultiCupTests(unittest.TestCase):
    def test_award_season_honours_awards_a_title_per_cup_not_just_the_latest(self) -> None:
        db = _fresh_db()
        engine = CompetitionEngine(db, seed=3)
        cup_finals = {
            "Domestic Knockout Cup": '{"winner": 1}',
            "T20 Cup": '{"winner": 2}',
            "Academy Cup": '{"winner": 3}',
        }
        engine._award_season_honours(2026, {}, cup_finals, user_team_id=1)
        self.assertEqual({h["title"] for h in database.fetch_honours(1, db)}, {"Knockout Cup Winners"})
        self.assertEqual({h["title"] for h in database.fetch_honours(2, db)}, {"T20 Cup Winners"})
        self.assertEqual({h["title"] for h in database.fetch_honours(3, db)}, {"Academy Cup Winners"})

    def test_none_cup_finals_is_still_accepted(self) -> None:
        db = _fresh_db()
        engine = CompetitionEngine(db, seed=3)
        engine._award_season_honours(2026, {}, None, user_team_id=1)
        self.assertEqual(database.fetch_honours(1, db), [])


if __name__ == "__main__":
    unittest.main()
