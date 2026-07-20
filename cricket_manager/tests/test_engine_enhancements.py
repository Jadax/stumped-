"""Coverage for the expanded contextual simulation model."""
from __future__ import annotations
import unittest
from match_engine import Match


def player(player_id: int, rating: int = 65, role: str = "Batsman") -> dict:
    return {"id":player_id,"name":f"Generated {player_id}","age":27,"role":role,"overall":rating,"potential":rating+10,"form":62,
            "batting":{"attack":rating,"defence":rating,"technique_vs_pace":rating,"technique_vs_spin":rating,"concentration":rating},
            "bowling":{"pace":rating,"accuracy":rating,"variation":rating,"stamina":rating,"swing_or_spin":rating},
            "fielding":{"catching":rating,"throwing":rating,"reflexes":rating,"agility":rating},
            "mental":{"experience":rating,"consistency":rating,"big_match":rating,"fitness":rating,"morale":rating}}


def lineup(start: int) -> list[dict]:
    return [player(start+i,66,"Wicketkeeper" if i==5 else "Bowler" if i>=7 else "All-Rounder" if i==6 else "Batsman") for i in range(11)]


class EngineEnhancementTests(unittest.TestCase):
    def make_match(self, pitch: str = "Worn", weather: str = "Cloudy") -> Match:
        return Match({"id":1,"name":"North"},{"id":2,"name":"South"},lineup(1),lineup(20),"T20",
                     pitch=pitch,weather=weather,seed=19,batting_first_id=1)

    def test_delivery_exposes_context_factors(self) -> None:
        match=self.make_match(); event=match.ball_outcome()
        self.assertIn("factors",event); self.assertIn("batting_rating",event["factors"])
        self.assertEqual(event["factors"]["pitch"],"Worn")

    def test_scorecard_has_partnerships_and_fall_of_wickets(self) -> None:
        match=self.make_match(); match.simulate()
        card=match.scorecard(0)
        self.assertIn("partnerships",card); self.assertIn("fall_of_wickets",card)

    def test_performance_updates_are_bounded(self) -> None:
        match=self.make_match(); match.simulate(); updates=match.performance_updates()
        self.assertTrue(updates)
        self.assertTrue(all(-5 <= change["form"] <= 5 for change in updates.values()))
        self.assertTrue(all(-.5 <= change["overall"] <= .5 for change in updates.values()))


if __name__=="__main__": unittest.main()
