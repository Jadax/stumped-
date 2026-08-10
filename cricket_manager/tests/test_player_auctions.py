"""v4.63.0: live player auctions (roadmap.json's live_auctions item).
Also closes a real pre-existing gap: database.set_transfer_listed existed
but was never wired to any Godot IPC method, so a Godot manager had no way
to list their own player for sale at all (pygame's ui/transfers.py had a
plain listing toggle; Godot had nothing).
"""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, timedelta

import database
from competition import CompetitionEngine


def _fresh_db() -> str:
    db = os.path.join(tempfile.mkdtemp(), "auctions.db")
    database.initialise_database(db)
    return db


def _team_id(db: str) -> int:
    return database.load_game(db)["user"]["current_team_id"]


def _a_player_id(db: str, team_id: int) -> int:
    with database.connect(db) as connection:
        return connection.execute("SELECT id FROM players WHERE team_id=? LIMIT 1", (team_id,)).fetchone()[0]


class StartAuctionTests(unittest.TestCase):
    def test_starting_an_auction_lists_the_player_and_creates_an_open_auction(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        auction_id = database.start_player_auction(team_id, player_id, "2026-04-01", database_path=db)
        with database.connect(db) as connection:
            listed = connection.execute("SELECT transfer_listed FROM players WHERE id=?", (player_id,)).fetchone()[0]
            auction = connection.execute("SELECT * FROM auctions WHERE id=?", (auction_id,)).fetchone()
        self.assertEqual(listed, 1)
        self.assertEqual(auction["status"], "OPEN")
        self.assertEqual(auction["seller_team_id"], team_id)
        self.assertGreater(auction["reserve_price"], 0)

    def test_cannot_auction_a_player_you_do_not_own(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        with database.connect(db) as connection:
            other_player_id = connection.execute(
                "SELECT id FROM players WHERE team_id!=? LIMIT 1", (team_id,)
            ).fetchone()[0]
        with self.assertRaises(ValueError):
            database.start_player_auction(team_id, other_player_id, "2026-04-01", database_path=db)

    def test_cannot_open_a_second_auction_for_the_same_player(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        database.start_player_auction(team_id, player_id, "2026-04-01", database_path=db)
        with self.assertRaises(ValueError):
            database.start_player_auction(team_id, player_id, "2026-04-01", database_path=db)

    def test_explicit_reserve_price_is_respected(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        auction_id = database.start_player_auction(team_id, player_id, "2026-04-01", reserve_price=123_000, database_path=db)
        with database.connect(db) as connection:
            row = connection.execute("SELECT reserve_price, current_bid FROM auctions WHERE id=?", (auction_id,)).fetchone()
        self.assertEqual(row["reserve_price"], 123_000)
        self.assertEqual(row["current_bid"], 123_000)


class BiddingTests(unittest.TestCase):
    def test_a_rival_club_can_place_a_quick_bid_above_the_current_price(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        auction_id = database.start_player_auction(team_id, player_id, "2026-04-01", reserve_price=100_000, database_path=db)
        with database.connect(db) as connection:
            bidder_id = connection.execute("SELECT id FROM teams WHERE id!=? LIMIT 1", (team_id,)).fetchone()[0]
            connection.execute("UPDATE teams SET cash=? WHERE id=?", (10_000_000, bidder_id))
        result = database.place_auction_bid(auction_id, bidder_id, "2026-04-02", database_path=db)
        self.assertGreater(result["bid"], 100_000)
        with database.connect(db) as connection:
            row = connection.execute("SELECT current_bid, current_bidder_team_id FROM auctions WHERE id=?", (auction_id,)).fetchone()
        self.assertEqual(row["current_bid"], result["bid"])
        self.assertEqual(row["current_bidder_team_id"], bidder_id)

    def test_the_seller_cannot_bid_on_their_own_auction(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        auction_id = database.start_player_auction(team_id, player_id, "2026-04-01", database_path=db)
        with self.assertRaises(ValueError):
            database.place_auction_bid(auction_id, team_id, "2026-04-02", database_path=db)

    def test_a_bid_below_the_current_price_is_rejected_by_being_raised_to_the_minimum(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        auction_id = database.start_player_auction(team_id, player_id, "2026-04-01", reserve_price=100_000, database_path=db)
        with database.connect(db) as connection:
            bidder_id = connection.execute("SELECT id FROM teams WHERE id!=? LIMIT 1", (team_id,)).fetchone()[0]
            connection.execute("UPDATE teams SET cash=? WHERE id=?", (10_000_000, bidder_id))
        result = database.place_auction_bid(auction_id, bidder_id, "2026-04-02", amount=1, database_path=db)
        self.assertGreaterEqual(result["bid"], 105_000)

    def test_bidding_without_enough_cash_is_rejected(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        auction_id = database.start_player_auction(team_id, player_id, "2026-04-01", reserve_price=100_000, database_path=db)
        with database.connect(db) as connection:
            bidder_id = connection.execute("SELECT id FROM teams WHERE id!=? LIMIT 1", (team_id,)).fetchone()[0]
            connection.execute("UPDATE teams SET cash=0 WHERE id=?", (bidder_id,))
        with self.assertRaises(ValueError):
            database.place_auction_bid(auction_id, bidder_id, "2026-04-02", database_path=db)


class ResolutionTests(unittest.TestCase):
    def test_an_auction_with_a_winning_bid_transfers_the_player_and_moves_cash(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        auction_id = database.start_player_auction(team_id, player_id, "2026-04-01", reserve_price=100_000, database_path=db)
        with database.connect(db) as connection:
            bidder_id = connection.execute("SELECT id FROM teams WHERE id!=? LIMIT 1", (team_id,)).fetchone()[0]
            connection.execute("UPDATE teams SET cash=? WHERE id=?", (10_000_000, bidder_id))
            seller_cash_before = connection.execute("SELECT cash FROM teams WHERE id=?", (team_id,)).fetchone()[0]
        result = database.place_auction_bid(auction_id, bidder_id, "2026-04-02", database_path=db)
        deadline = (date(2026, 4, 1) + timedelta(days=5)).isoformat()
        events = database.advance_auctions(deadline, database_path=db)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["outcome"], "sold")
        with database.connect(db) as connection:
            player_row = connection.execute("SELECT team_id, transfer_listed FROM players WHERE id=?", (player_id,)).fetchone()
            seller_cash_after = connection.execute("SELECT cash FROM teams WHERE id=?", (team_id,)).fetchone()[0]
            auction_row = connection.execute("SELECT status FROM auctions WHERE id=?", (auction_id,)).fetchone()
        self.assertEqual(player_row["team_id"], bidder_id)
        self.assertEqual(player_row["transfer_listed"], 0)
        self.assertEqual(seller_cash_after, seller_cash_before + result["bid"])
        self.assertEqual(auction_row["status"], "SOLD")

    def test_an_auction_with_no_bids_is_marked_unsold_and_delists_the_player(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        database.start_player_auction(team_id, player_id, "2026-04-01", database_path=db)
        deadline = (date(2026, 4, 1) + timedelta(days=5)).isoformat()
        events = database.advance_auctions(deadline, database_path=db)
        self.assertEqual(events[0]["outcome"], "unsold")
        with database.connect(db) as connection:
            player_row = connection.execute("SELECT team_id, transfer_listed FROM players WHERE id=?", (player_id,)).fetchone()
        self.assertEqual(player_row["team_id"], team_id)
        self.assertEqual(player_row["transfer_listed"], 0)

    def test_open_auctions_before_their_deadline_are_not_resolved(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        database.start_player_auction(team_id, player_id, "2026-04-01", duration_days=5, database_path=db)
        events = database.advance_auctions("2026-04-02", database_path=db)
        self.assertEqual(events, [])


class CompetitionEngineIntegrationTests(unittest.TestCase):
    def test_advance_day_ticks_auctions_and_posts_an_inbox_message_on_resolution(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        engine = CompetitionEngine(db, seed=11)
        engine.ensure_season(2026)
        database.start_player_auction(team_id, player_id, "2026-04-01", duration_days=1, database_path=db)
        for _ in range(3):
            engine.advance_day(auto_sim_user=True)
        messages = database.fetch_inbox_messages(database_path=db)
        self.assertTrue(any("Auction" in m["title"] for m in messages))


class FetchActiveAuctionsTests(unittest.TestCase):
    def test_fetch_active_auctions_includes_player_and_seller_names(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        player_id = _a_player_id(db, team_id)
        database.start_player_auction(team_id, player_id, "2026-04-01", database_path=db)
        auctions = database.fetch_active_auctions(db)
        self.assertEqual(len(auctions), 1)
        self.assertIn("player_name", auctions[0])
        self.assertIn("seller_name", auctions[0])
        self.assertIsNone(auctions[0]["bidder_name"])


class IpcAuctionTests(unittest.TestCase):
    def _context(self) -> dict:
        from database import fetch_players, get_team_summary, initialise_database, load_game
        db = os.path.join(tempfile.mkdtemp(), "auction_ipc.db")
        initialise_database(db)
        game_data = load_game(db)
        team = get_team_summary(game_data["user"]["current_team_id"], db)
        return {"database_path": db, "team": team, "players": fetch_players(team["id"], db), "game_data": game_data}

    def test_start_get_and_bid_round_trip_through_ipc(self) -> None:
        import ipc_server
        ctx = self._context()
        player_id = int(ctx["players"][0]["id"])
        started = ipc_server._start_player_auction({"player_id": player_id}, ctx)
        self.assertIn("auction_id", started)
        listing = ipc_server._get_active_auctions({}, ctx)
        self.assertEqual(len(listing["auctions"]), 1)
        self.assertTrue(listing["auctions"][0]["is_mine"])


if __name__ == "__main__":
    unittest.main()
