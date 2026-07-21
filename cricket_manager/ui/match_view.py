"""Live cricket match hub: tactics, scorecards, analysis, and flow controls."""
from __future__ import annotations
from copy import deepcopy
import math
import random
import pygame
from database import (apply_match_player_updates, fetch_player_form,
                      fetch_player_match_events, fetch_player_records,
                      record_player_match_events, record_player_performance, save_game)
from match_engine import Match
from .player_modals import PlayerDetailModal
from .shared_components import BaseScreen
from .widgets import (AttributeBar, BowlingMap, Button, ButtonStyle, Card, Modal,
                      PitchDisplay, ShotMap, Slider, WeatherDisplay)
from .widgets.common import BG, BLUE, BORDER, CARD, CARD_ALT, DIM, GOLD, GREEN, MUTED, PANEL, RED, WHITE, text, clipped_text, wrap_text
from src.views.theme import ACCENT, vertical_gradient


class PredictorModal(Modal):
    def __init__(self, viewport: pygame.Rect, batting_name: str, probability: int):
        super().__init__(viewport, "Match Predictor", (560, 310)); self.batting_name, self.probability = batting_name, probability

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface); c = self.content_rect
        text(surface, "WIN PROBABILITY", (c.centerx, c.y + 25), 14, MUTED, bold=True, anchor="center")
        text(surface, f"{self.probability}%", (c.centerx, c.y + 86), 42, GOLD, bold=True, anchor="center")
        track = pygame.Rect(c.x + 45, c.y + 135, c.width - 90, 18)
        pygame.draw.rect(surface, CARD_ALT, track, border_radius=8)
        pygame.draw.rect(surface, GREEN, (track.x, track.y, int(track.width * self.probability / 100), track.height), border_radius=8)
        text(surface, self.batting_name, (c.centerx, c.y + 176), 14, WHITE, bold=True, anchor="center")


class MatchScreen(BaseScreen):
    """Presentation-ready match screen backed by the Phase 2 UI simulator."""
    dynamic = True
    MAIN_TABS = ["Batting", "Bowling", "Summary"]
    STAT_TABS = ["Scorecard", "Worm", "Momentum", "Ring", "Boundary", "Manhattan", "Partnerships"]
    STYLES = {"Silly": 10, "Blitz": 8, "Build": 5, "Rotate": 3}
    SPEEDS = {"Normal": .9, "Fast": .22, "Instant": .012}

    def build(self) -> None:
        setup = self.context.get("match_setup", {})
        user_xi = deepcopy(setup.get("user_xi") or self.context["players"][:11])
        opponent_xi = deepcopy(setup.get("opponent_xi") or list(reversed(self.context["players"][-11:])))
        selection = self.context.get("selection", {})
        styles = {int(pid): value for pid, value in selection.get("batting_styles", {}).items()}
        bat_orders = {int(pid): int(value) for pid, value in selection.get("batting_aggression", {}).items()}
        bowl_orders = {int(pid): int(value) for pid, value in selection.get("bowling_aggression", {}).items()}
        for player in user_xi:
            player["batting_style"] = styles.get(player["id"], selection.get("default_batting_style", "Build"))
            player["batting_aggression"] = bat_orders.get(player["id"], 5)
            player["bowling_aggression"] = bowl_orders.get(player["id"], 5)
        self.fixture = setup.get("fixture") or {}
        self.match_format = self.fixture.get("format", "T20")
        self.team_name = self.context["team"]["name"]
        self.opponent_name = self.fixture.get("away_name", "Sydney Sixers")
        user_id = int(self.context["team"]["id"])
        home_id = int(self.fixture.get("home_team", user_id))
        away_id = int(self.fixture.get("away_team", user_id + 1))
        opponent_id = away_id if home_id == user_id else home_id
        if opponent_id == user_id: opponent_id = user_id + 1
        opponent_name = (self.fixture.get("away_name") if home_id == user_id else self.fixture.get("home_name")) or self.opponent_name
        # Carry facility levels into the engine: medical investment lowers
        # injury risk and the grounds department slows pitch deterioration.
        user_team = dict(self.context["team"])
        user_team.update({"id": user_id, "name": self.team_name})
        opponent_team = {"id": opponent_id, "name": opponent_name}
        home_team, away_team = (user_team, opponent_team) if home_id == user_id else (opponent_team, user_team)
        home_xi, away_xi = (user_xi, opponent_xi) if home_id == user_id else (opponent_xi, user_xi)
        difficulty = self.context.get("new_game_setup", {}).get("difficulty", "Normal")
        self.engine = Match(home_team, away_team, home_xi, away_xi, self.match_format,
                            pitch=setup.get("pitch", "Green"), weather=setup.get("weather", "Overcast"),
                            knockout=bool(self.fixture.get("competition_type") == "Cup"), batting_first_id=user_id,
                            difficulty=difficulty)
        self.user_team_id = user_id
        self.bowler_index = 0
        self.runs = self.wickets = self.legal_balls = self.partnership_runs = self.partnership_balls = 0
        self.extras = {"nb": 0, "w": 0, "lb": 0}
        self.batters, self.bowlers, self.batter_stats, self.bowler_stats = [], [], {}, {}
        self.partnerships: list[tuple[str, str, int, int]] = []
        self.ball_history: list[dict] = []
        self.commentary: list[tuple[str, str]] = []
        self.batting_styles = {int(pid): value for pid, value in selection.get("batting_styles", {}).items()}
        self.default_style = selection.get("default_batting_style", "Build")
        aggression = selection.get("aggression", [5, 5, 5])
        self.batting_slider = Slider(pygame.Rect(0, 0, 150, 37), "Batting Aggression", 1, 10, aggression[0])
        self.bowling_slider = Slider(pygame.Rect(0, 0, 150, 37), "Bowling Aggression", 1, 10, aggression[1])
        self.field_preset, self.active_tab, self.active_stat, self.hub_mode = "Neutral", "Batting", "Scorecard", "Stats Hub"
        self.perspective = "Batter"
        self.auto_play, self.paused, self.speed, self.accumulator = False, True, "Normal", 0.0
        self.result_recorded = False
        self.day, self.session, self.session_seconds = 1, 1, 300
        self.drs_remaining, self.status = 2, f"{self.team_name} innings in progress"
        self._sync_from_engine()
        self._build_controls()
        self._add_commentary("The field is set and the opening bowler begins the spell.", "milestone")

    def _build_controls(self) -> None:
        x, y = self.content_rect.x + 18, self.content_rect.y + 73
        self.main_tab_buttons = []
        for label in self.MAIN_TABS:
            button = Button(pygame.Rect(x, y, 92, 28), label.upper(), ButtonStyle.PRIMARY if label == "Batting" else ButtonStyle.SECONDARY,
                            selected=label == self.active_tab)
            self.main_tab_buttons.append((label, button)); x += 98
        self.hub_button = Button(pygame.Rect(self.content_rect.right - 148, y, 130, 28), "STATS HUB", ButtonStyle.SUCCESS)
        self.perspective_button = Button(pygame.Rect(self.content_rect.right - 286, y, 132, 28), "VIEW: BATTER", ButtonStyle.SECONDARY)
        self.stat_buttons = []
        x = self.content_rect.x + 18; stat_y = self.content_rect.y + 106
        sw = (self.content_rect.width - 36 - 25) // len(self.STAT_TABS)
        for label in self.STAT_TABS:
            self.stat_buttons.append((label, Button(pygame.Rect(x, stat_y, sw, 24), label.upper(), ButtonStyle.SECONDARY,
                                                        selected=label == self.active_stat))); x += sw + 5
        control_y = self.content_rect.bottom - 183
        self.batting_slider.rect.topleft = (self.content_rect.x + 20, control_y)
        self.bowling_slider.rect.topleft = (self.content_rect.x + 184, control_y)
        labels = [("PREDICT", ButtonStyle.SUCCESS), ("AUTO: OFF", ButtonStyle.PRIMARY),
                  ("NEXT BALL", ButtonStyle.PRIMARY), ("OVER", ButtonStyle.SECONDARY),
                  ("CHANGE", ButtonStyle.SECONDARY), ("FIELD", ButtonStyle.SECONDARY),
                  ("DRS 2", ButtonStyle.SUCCESS), ("SKIP", ButtonStyle.SECONDARY),
                  ("PLAY", ButtonStyle.PRIMARY), ("EXIT", ButtonStyle.DANGER)]
        self.action_buttons = []
        x = self.content_rect.x + 348
        bw = max(58, (self.content_rect.right - 18 - x - 5 * (len(labels) - 1)) // len(labels))
        for label, style in labels:
            self.action_buttons.append(Button(pygame.Rect(x, control_y + 5, bw, 31), label, style)); x += bw + 5
        self.speed_buttons = []
        x = self.content_rect.right - 252
        for name in self.SPEEDS:
            self.speed_buttons.append((name, Button(pygame.Rect(x, self.content_rect.y + 15, 72, 25), name.upper(),
                                                        ButtonStyle.SECONDARY, selected=name == self.speed))); x += 76

    @property
    def striker(self): return self.batters[min(self.striker_index, len(self.batters) - 1)]
    @property
    def non_striker(self): return self.batters[min(self.non_striker_index, len(self.batters) - 1)]
    @property
    def bowler(self):
        current_id = self.engine.current_innings.current_bowler_id
        return next((p for p in self.bowlers if p["id"] == current_id), self.bowlers[0])

    def overs_text(self, balls: int | None = None) -> str:
        balls = self.legal_balls if balls is None else balls
        return f"{balls // 6}.{balls % 6}"

    def batting_style(self, player: dict | None = None) -> str:
        player = player or self.striker
        return self.batting_styles.get(player["id"], self.default_style)

    def _add_commentary(self, line: str, kind: str = "normal") -> None:
        self.commentary.append((line, kind)); self.commentary = self.commentary[-100:]

    def _sync_from_engine(self) -> None:
        """Copy the active engine innings into the presentation model."""
        innings = self.engine.current_innings
        self.batters, self.bowlers = innings.batting_order, innings.bowling_squad
        self.team_name, self.opponent_name = innings.batting_name, innings.bowling_name
        self.runs, self.wickets, self.legal_balls = innings.runs, innings.wickets, innings.legal_balls
        self.striker_index, self.non_striker_index, self.next_batter = innings.striker, innings.non_striker, innings.next_batter
        self.partnership_runs, self.partnership_balls = innings.partnership_runs, innings.partnership_balls
        self.extras = {"nb": innings.extras["nb"], "w": innings.extras["w"], "lb": innings.extras["lb"] + innings.extras["b"]}
        self.partnerships = [(p["a"], p["b"], p["runs"], p["balls"]) for p in innings.partnerships]
        self.batter_stats = {pid: {"runs": line.runs, "balls": line.balls, "fours": line.fours,
                                   "sixes": line.sixes, "not_out": line.not_out,
                                   "dismissal": line.dismissal, "outcomes": list(line.outcomes)}
                             for pid, line in innings.batters.items()}
        self.bowler_stats = {}
        for pid, line in innings.bowlers.items():
            stamina = self.engine.player_energy(pid)
            self.bowler_stats[pid] = {"runs": line.runs, "balls": line.balls, "maidens": line.maidens,
                                      "wickets": line.wickets, "over_runs": line.current_over_runs, "stamina": stamina}
        self.status = self.engine.match_status()
        self.day, self.session = self.engine.day, self.engine.session
        self.drs_remaining = self.engine.reviews.get(self.user_team_id, 0)

    def simulate_ball(self) -> None:
        if self.engine.completed: return
        striker = self.striker
        style_value = self.STYLES.get(self.batting_style(striker), 5)
        striker["batting_aggression"] = round((float(self.batting_slider.value) + style_value) / 2)
        self.bowler["bowling_aggression"] = round(float(self.bowling_slider.value))
        self.engine.set_field(self.field_preset)
        event = self.engine.ball_outcome()
        event_bus = self.context.get("event_bus")
        if event_bus: event_bus.emit("match.delivery", event)
        self.ball_history.append({"result": event["result"], "kind": event.get("kind", "normal"),
                                  "runs": event.get("runs", 0)})
        self.ball_history = self.ball_history[-120:]
        self._add_commentary(f"Over {event.get('over', self.overs_text())}: {event['commentary']}", event.get("kind", "normal"))
        self._sync_from_engine()
        if striker in self.batters and striker["id"] in self.batter_stats: self._sync_player_match_stats(striker)
        if event.get("innings_complete"): self._add_commentary("INNINGS COMPLETE — players change roles.", "milestone")
        if event.get("match_complete"):
            self.auto_play = False; self.paused = True
            self.action_buttons[1].label = "AUTO: OFF"; self.action_buttons[8].label = "PLAY"
            self._add_commentary(self.engine.result, "milestone")
            self._record_result()
        self.engine.event_pool.release(event)

    def _record_result(self) -> None:
        """Complete the calendar fixture exactly once and update its table."""
        fixture_id = self.fixture.get("id")
        competition = self.context.get("competition_engine")
        if self.result_recorded or not fixture_id or competition is None: return
        home_id, away_id = int(self.fixture["home_team"]), int(self.fixture["away_team"])
        totals = self.engine.team_totals
        wickets = {team_id: sum(i.wickets for i in self.engine.innings if i.batting_team == team_id)
                   for team_id in (home_id, away_id)}
        result = {"home_runs": totals[home_id], "home_wickets": wickets[home_id],
                  "away_runs": totals[away_id], "away_wickets": wickets[away_id],
                  "winner": self.engine.winner_id, "tied": self.engine.winner_id is None,
                  "overs": self.engine.overs_limit(),
                  "summary": self.engine.result, "scorecards": self.engine.to_dict()["innings"]}
        competition.record_played_fixture(int(fixture_id), result)
        steam = self.context.get("steam")
        if steam: steam.evaluate_match(self.engine.to_dict(), self.user_team_id)
        self.result_recorded = True
        apply_match_player_updates(self.engine.performance_updates(), self.engine.injuries,
                                   self.context.get("current_date", "2026-04-01"), self.context["database_path"])
        record_context = "Cup" if self.fixture.get("competition_type") == "Cup" else "Friendly" if not self.fixture.get("competition_id") else "League"
        match_date = self.context.get("current_date", "2026-04-01")
        career_lines: dict[int, dict[str, list[dict]]] = {}
        for innings in self.engine.innings:
            for player in innings.batting_order:
                line = innings.batters[int(player["id"])]
                if line.balls or line.dismissal != "did not bat":
                    career_lines.setdefault(int(player["id"]), {"batting": [], "bowling": []})["batting"].append(vars(line).copy())
            for player in innings.bowling_squad:
                line = innings.bowlers[int(player["id"])]
                if line.balls:
                    career_lines.setdefault(int(player["id"]), {"batting": [], "bowling": []})["bowling"].append(vars(line).copy())
        for player_id, lines in career_lines.items():
            record_player_performance(player_id, match_date, record_context,
                                      lines["batting"] or None, lines["bowling"] or None,
                                      database_path=self.context["database_path"])
        record_player_match_events(int(fixture_id), 1, self.engine.shot_events, self.engine.bowling_events,
                                   self.context["database_path"])
        save_game({"last_match": self.engine.to_dict(), "current_match_ui": {}}, self.context["database_path"])

    def _sync_player_match_stats(self, player: dict) -> None:
        s = self.batter_stats[player["id"]]
        chances = self.engine.chance_log.get(int(player["id"]), {})
        dropped = int(chances.get("dropped", 0))
        survived = dropped + int(chances.get("missed_stumping", 0)) + int(chances.get("missed_runout", 0))
        player["current_match_stats"] = {"runs": s["runs"], "balls": s["balls"], "mins": max(s["balls"], int(s["balls"] * 1.45)),
                                         "fours": s["fours"], "sixes": s["sixes"], "sr": s["runs"] / max(1, s["balls"]) * 100,
                                         "dropped": dropped, "lbw": 1 if s["balls"] > 8 else 0, "missed": s["balls"] // 17,
                                         "catchable": survived, "outcomes": list(s["outcomes"])}

    def _profile(self, player: dict) -> dict:
        profile = dict(player)
        profile["records"] = fetch_player_records(player["id"], self.context["database_path"])
        profile["form_history"] = fetch_player_form(player["id"], self.context["database_path"])
        profile["match_events"] = fetch_player_match_events(player["id"], self.context["database_path"])
        return profile

    def update(self, time_delta: float) -> None:
        if self.auto_play and not self.paused:
            self.session_seconds = max(0, self.session_seconds - time_delta)
            if self.session_seconds <= 0:
                self.session += 1
                if self.session > 3: self.day += 1; self.session = 1
                self.session_seconds = 300; self.paused = True; self._add_commentary("SESSION COMPLETE — players leave the field.", "milestone")
            self.accumulator += time_delta; interval = self.SPEEDS[self.speed]; count = 0
            while self.accumulator >= interval and count < (35 if self.speed == "Instant" else 2):
                self.accumulator -= interval; self.simulate_ball(); count += 1

    def _play_over(self) -> None:
        innings_index = self.engine.current_innings_index
        target = self.legal_balls + (6 - self.legal_balls % 6)
        attempts = 0
        while self.legal_balls < target and attempts < 15 and not self.engine.completed:
            self.simulate_ball(); attempts += 1
            if self.engine.current_innings_index != innings_index: break

    def _skip(self) -> None:
        wickets = self.wickets; target_session = self.session_seconds
        for _ in range(90):
            self.simulate_ball()
            if self.wickets > wickets or self.engine.completed: break
        self.session_seconds = max(0, target_session - 90)

    def process_event(self, event: pygame.event.Event) -> None:
        if self.modal:
            if self.modal.process_event(event): self.modal = None
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            body_y, body_bottom = self.content_rect.y + 136, self.content_rect.bottom - 198
            left_width = int((self.content_rect.width - 48) * .67)
            right = pygame.Rect(self.content_rect.x + 18 + left_width + 12, body_y,
                                self.content_rect.right - 18 - (self.content_rect.x + 18 + left_width + 12), body_bottom - body_y)
            if right.collidepoint(event.pos):
                player = self.bowler if event.pos[1] < right.centery else self.striker
                if player in self.batters: self._sync_player_match_stats(player)
                candidate = self.non_striker if player is self.striker else self.bowlers[(self.bowler_index + 1) % len(self.bowlers)]
                self.modal = PlayerDetailModal(self.content_rect, self._profile(player), self._profile(candidate))
                return
        for label, button in self.main_tab_buttons:
            if button.process_event(event):
                self.active_tab = label
                for other, b in self.main_tab_buttons: b.selected = other == label
        if self.hub_button.process_event(event):
            self.hub_mode = "Tactics Hub" if self.hub_mode == "Stats Hub" else "Stats Hub"
            self.hub_button.label = self.hub_mode.upper(); self.active_tab = "Summary"
        if self.perspective_button.process_event(event):
            self.perspective = "Bowler" if self.perspective == "Batter" else "Batter"
            self.perspective_button.label = f"VIEW: {self.perspective.upper()}"
            self.active_tab = "Batting" if self.perspective == "Batter" else "Bowling"
        for label, button in self.stat_buttons:
            if button.process_event(event):
                self.active_stat, self.active_tab, self.hub_mode = label, "Summary", "Stats Hub"
                for other, b in self.stat_buttons: b.selected = other == label
        self.batting_slider.process_event(event); self.bowling_slider.process_event(event)
        for name, button in self.speed_buttons:
            if button.process_event(event):
                self.speed = name
                for other, b in self.speed_buttons: b.selected = other == name
        if self.action_buttons[0].process_event(event):
            probability = self.engine.win_probability(self.user_team_id)
            self.modal = PredictorModal(self.content_rect, self.context["team"]["name"], probability)
        if self.action_buttons[1].process_event(event):
            self.auto_play = not self.auto_play; self.paused = not self.auto_play
            self.action_buttons[1].label = f"AUTO: {'ON' if self.auto_play else 'OFF'}"; self.action_buttons[1].selected = self.auto_play
            self.action_buttons[8].label = "PAUSE" if self.auto_play else "PLAY"
        if self.action_buttons[2].process_event(event): self.simulate_ball()
        if self.action_buttons[3].process_event(event): self._play_over()
        if self.action_buttons[4].process_event(event):
            options = self.engine._eligible_bowlers()
            ids = [int(player["id"]) for player in options]
            if ids:
                current = self.engine.current_innings.current_bowler_id
                start = (ids.index(current) + 1) % len(ids) if current in ids else 0
                for offset in range(len(ids)):
                    if self.engine.set_bowler(ids[(start + offset) % len(ids)]): break
                self._sync_from_engine()
        if self.action_buttons[5].process_event(event):
            presets = ["Aggressive", "Neutral", "Defensive"]
            self.field_preset = presets[(presets.index(self.field_preset) + 1) % len(presets)]
            self.engine.set_field(self.field_preset)
        if self.action_buttons[6].process_event(event) and self.drs_remaining:
            review = self.engine.review_last_decision(self.user_team_id)
            if review.get("available"):
                self._sync_from_engine(); self.action_buttons[6].label = f"DRS {self.drs_remaining}"
                self._add_commentary(f"DRS review: {review['message']}", "milestone")
        if self.action_buttons[7].process_event(event): self._skip()
        if self.action_buttons[8].process_event(event):
            self.paused = not self.paused
            if not self.paused:
                self.auto_play = True; self.action_buttons[1].label = "AUTO: ON"; self.action_buttons[1].selected = True
            self.action_buttons[8].label = "PLAY" if self.paused else "PAUSE"
        if self.action_buttons[9].process_event(event):
            if self.navigate: self.navigate("Dashboard")
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE: self.simulate_ball()

    def _draw_header(self, surface: pygame.Surface) -> None:
        rect = pygame.Rect(self.content_rect.x + 18, self.content_rect.y + 8, self.content_rect.width - 36, 58)
        surface.blit(vertical_gradient(rect.size, PANEL.lerp(ACCENT, .12), PANEL), rect)
        pygame.draw.rect(surface, BORDER, rect, 1)
        pygame.draw.rect(surface, ACCENT, (rect.x, rect.bottom - 2, rect.width, 2))
        stats = self.batter_stats[self.striker["id"]]; crr = self.runs / max(1, self.legal_balls) * 6
        text(surface, self.team_name.upper(), (rect.x + 14, rect.y + 8), 10, MUTED, bold=True)
        text(surface, f"{self.runs}/{self.wickets} ({self.overs_text()})", (rect.x + 14, rect.y + 25), 21, GOLD, bold=True)
        text(surface, f"★ {self.striker['name']}  {stats['runs']} ({stats['balls']})", (rect.x + 220, rect.y + 12), 14, WHITE, bold=True)
        text(surface, f"CRR {crr:.2f}", (rect.x + 220, rect.y + 35), 12, GREEN, bold=True)
        ball_age = float(self.engine.last_factors.get("ball_age_overs", self.legal_balls / 6))
        weather_colours = {"Sunny": GOLD, "Overcast": MUTED, "Humid": GREEN, "Rain": BLUE, "Drizzle": BLUE}
        pygame.draw.circle(surface, weather_colours.get(self.engine.weather, MUTED), (rect.x + 356, rect.y + 17), 4)
        text(surface, f"{self.engine.weather} • Ball {ball_age:.1f} ov", (rect.x + 366, rect.y + 12), 10, MUTED, bold=True)
        wear = max(0.0, min(100.0, float(getattr(self.engine, "pitch_wear", 0))))
        wear_track = pygame.Rect(rect.x + 480, rect.y + 15, 52, 6)
        pygame.draw.rect(surface, CARD_ALT, wear_track, border_radius=3)
        wear_colour = GREEN if wear < 40 else GOLD if wear < 70 else RED
        pygame.draw.rect(surface, wear_colour, (wear_track.x, wear_track.y, int(wear_track.width * wear / 100), 6), border_radius=3)
        text(surface, f"{self.engine.pitch} pitch", (wear_track.x, wear_track.y + 9), 9, MUTED)
        if self.engine.current_innings.target:
            metric = f"RRR {self.engine.required_rate:.2f}"
        else:
            maximum = self.engine.overs_limit() if self.match_format != "Test" else max(90, self.legal_balls / 6)
            metric = f"PROJECTED {self.engine.projected_score()}"
        text(surface, metric, (rect.x + 350, rect.y + 35), 12, GOLD, bold=True)
        time_text = f"{int(self.session_seconds // 60)} mins left"
        session_label = f"Day {self.day} Session {self.session}" if self.match_format == "Test" else self.match_format
        text(surface, session_label, (rect.centerx + 55, rect.y + 10), 13, WHITE, bold=True)
        text(surface, time_text if self.match_format == "Test" else self.field_preset.upper(), (rect.centerx + 55, rect.y + 34), 11, GOLD)
        text(surface, clipped_text(self.status, 275, 11), (rect.right - 270, rect.y + 34), 11, MUTED, anchor="topright")
        for _, button in self.speed_buttons: button.draw(surface)

    def _draw_batting_table(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        card = Card(rect, "BATTING CARD", f"{self.match_format.upper()} INNINGS"); card.draw(surface)
        headers = [("Name", .04), ("Runs", .61), ("Balls", .70), ("4s", .79), ("6s", .87), ("SR%", .96)]
        y = rect.y + 48; pygame.draw.rect(surface, PANEL, (rect.x + 10, y, rect.width - 20, 24))
        for label, frac in headers: text(surface, label.upper(), (rect.x + int(rect.width * frac), y + 7), 9, MUTED, bold=True, anchor="topright" if frac > .5 else "topleft")
        y += 25; row_h = max(18, min(23, (rect.height - 112) // 11))
        current_ids = {self.striker["id"], self.non_striker["id"]}
        for index, player in enumerate(self.batters):
            stat = self.batter_stats[player["id"]]; row = pygame.Rect(rect.x + 10, y + index * row_h, rect.width - 20, row_h)
            colour = CARD.lerp(GOLD, .22) if player["id"] == self.striker["id"] else CARD_ALT if index % 2 else CARD
            pygame.draw.rect(surface, colour, row)
            if player["id"] == self.striker["id"]: pygame.draw.rect(surface, GOLD, row, 1)
            marker = "*" if player["id"] in current_ids and stat["not_out"] else ""
            text(surface, clipped_text(player["name"] + marker, int(rect.width * .38), 10), (row.x + 8, row.y + 4), 10, WHITE, bold=player["id"] in current_ids)
            text(surface, stat["dismissal"], (rect.x + int(rect.width * .43), row.y + 4), 9, GREEN if stat["not_out"] else MUTED)
            values = [stat["runs"], stat["balls"], stat["fours"], stat["sixes"], f"{stat['runs']/max(1,stat['balls'])*100:.1f}"]
            for value, frac in zip(values, [.61, .70, .79, .87, .96]): text(surface, value, (rect.x + int(rect.width * frac), row.y + 4), 10, GOLD if frac == .61 else WHITE, bold=frac == .61, anchor="topright")
        footer_y = y + row_h * 11 + 3
        extras_total = sum(self.extras.values())
        text(surface, f"Extras (nb {self.extras['nb']}, w {self.extras['w']}, lb {self.extras['lb']})", (rect.x + 17, footer_y), 10, MUTED)
        text(surface, extras_total, (rect.right - 18, footer_y), 10, WHITE, bold=True, anchor="topright")
        text(surface, f"Total ({self.wickets} wkts, {self.overs_text()} overs)", (rect.x + 17, footer_y + 20), 12, WHITE, bold=True)
        text(surface, self.runs, (rect.right - 18, footer_y + 20), 13, GOLD, bold=True, anchor="topright")

    def _draw_bowling_table(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        card = Card(rect, "BOWLING FIGURES", self.opponent_name.upper()); card.draw(surface)
        y = rect.y + 52; headers = ["Bowler", "O", "M", "R", "W", "Econ", "Stam"]
        fractions = [.03, .56, .64, .72, .80, .90, .98]
        for h, f in zip(headers, fractions): text(surface, h.upper(), (rect.x + int(rect.width * f), y), 10, MUTED, bold=True, anchor="topright" if f > .5 else "topleft")
        y += 24
        options = [p for p in self.bowlers if p["role"] in ("Bowler", "All-Rounder")] or self.bowlers
        for i, player in enumerate(options[:8]):
            s = self.bowler_stats[player["id"]]; row = pygame.Rect(rect.x + 10, y + i * 31, rect.width - 20, 29)
            pygame.draw.rect(surface, CARD.lerp(GOLD, .22) if player["id"] == self.bowler["id"] else CARD_ALT if i % 2 else CARD, row)
            text(surface, clipped_text(player["name"], int(rect.width * .38), 11), (row.x + 8, row.y + 8), 11, WHITE, bold=player["id"] == self.bowler["id"])
            values = [self.overs_text(s["balls"]), s["maidens"], s["runs"], s["wickets"], f"{s['runs']/(s['balls']/6):.2f}" if s["balls"] else "0.00", s["stamina"]]
            for value, f in zip(values, fractions[1:]): text(surface, value, (rect.x + int(rect.width * f), row.y + 8), 11, GREEN if f == .98 else WHITE, anchor="topright")

    def _draw_player_cards(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        gap = 8; half = (rect.height - gap) // 2
        bow_card = Card(pygame.Rect(rect.x, rect.y, rect.width, half), "CURRENT BOWLER")
        bat_card = Card(pygame.Rect(rect.x, rect.y + half + gap, rect.width, rect.height - half - gap), "AT THE CREASE")
        bow_card.draw(surface); bat_card.draw(surface)
        bow, bs = self.bowler, self.bowler_stats[self.bowler["id"]]
        bowl_type = "RF" if bow["bowling"]["pace"] >= 60 else "SLA"
        text(surface, f"{bow['name']}  {bowl_type}", (bow_card.rect.x + 14, bow_card.rect.y + 51), 14, WHITE, bold=True)
        figure = f"{self.overs_text(bs['balls'])}-{bs['maidens']}-{bs['runs']}-{bs['wickets']}"
        text(surface, figure, (bow_card.rect.right - 14, bow_card.rect.y + 51), 14, GOLD, bold=True, anchor="topright")
        text(surface, "O-M-R-W", (bow_card.rect.right - 14, bow_card.rect.y + 73), 9, MUTED, anchor="topright")
        economy = bs["runs"] * 6 / max(1, bs["balls"])
        text(surface, f"Econ {economy:.2f}", (bow_card.rect.x + 14, bow_card.rect.y + 73), 10, MUTED)
        AttributeBar(pygame.Rect(bow_card.rect.x + 14, bow_card.rect.y + 84, bow_card.rect.width - 28, 27), "Stamina", bs["stamina"]).draw(surface)
        text(surface, f"{self.match_format} bowling avg: {max(18, 47-bow['overall']/3):.2f}", (bow_card.rect.x + 14, bow_card.rect.bottom - 20), 10, MUTED)
        bat, stat = self.striker, self.batter_stats[self.striker["id"]]; sr = stat["runs"] / max(1, stat["balls"]) * 100
        text(surface, f"{bat['name']}*", (bat_card.rect.x + 14, bat_card.rect.y + 49), 14, WHITE, bold=True)
        text(surface, self.batting_style(bat).upper(), (bat_card.rect.right - 14, bat_card.rect.y + 49), 11, GOLD, bold=True, anchor="topright")
        columns = [("R", stat["runs"]), ("B", stat["balls"]), ("4s", stat["fours"]), ("6s", stat["sixes"]), ("SR", f"{sr:.1f}")]
        cw = (bat_card.rect.width - 28) // len(columns)
        for i, (label, value) in enumerate(columns):
            cx = bat_card.rect.x + 14 + i * cw + cw // 2; text(surface, label, (cx, bat_card.rect.y + 77), 9, MUTED, bold=True, anchor="center"); text(surface, value, (cx, bat_card.rect.y + 98), 13, WHITE, bold=True, anchor="center")
        text(surface, f"{self.match_format} batting avg: {25 + bat['overall']/2.4:.2f}  •  Form {bat.get('form', 50)}",
             (bat_card.rect.x + 14, bat_card.rect.bottom - 37), 10, MUTED)
        text(surface, f"Partnership: {self.partnership_runs} runs ({self.partnership_balls} balls)", (bat_card.rect.x + 14, bat_card.rect.bottom - 19), 10, GREEN, bold=True)

    def _draw_pitch(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, pygame.Color("#173f24"), rect)
        centre, radius = rect.center, min(rect.width, rect.height) // 2 - 20
        pygame.draw.circle(surface, pygame.Color("#d7e0d7"), centre, radius, 2); pygame.draw.circle(surface, MUTED, centre, radius // 2, 1)
        pygame.draw.line(surface, WHITE, (centre[0], centre[1] - 45), (centre[0], centre[1] + 45), 2)
        rng = random.Random(len(self.ball_history) + 7)
        for i, ball in enumerate(self.ball_history[-20:]):
            angle = rng.random() * math.tau; distance = radius * (.35 + rng.random() * .6)
            point = (int(centre[0] + math.cos(angle) * distance), int(centre[1] + math.sin(angle) * distance))
            colour = RED if ball["result"] == "6" else GOLD if ball["result"] == "4" else GREEN
            pygame.draw.line(surface, colour, centre, point, 1); pygame.draw.circle(surface, colour, point, 3)

    def _draw_summary(self, surface: pygame.Surface, left: pygame.Rect, right: pygame.Rect) -> None:
        if self.hub_mode == "Tactics Hub":
            pitch_card = Card(left, f"{self.perspective.upper()} PERSPECTIVE", f"FIELD: {self.field_preset.upper()}"); pitch_card.draw(surface)
            map_rect = pitch_card.content_rect.inflate(-24, -42)
            if self.perspective == "Bowler": BowlingMap(map_rect, self.engine.bowling_events[-90:]).draw(surface)
            else: ShotMap(map_rect, self.engine.shot_events[-90:]).draw(surface)
            card = Card(right, "TACTICAL PLAN"); card.draw(surface)
            y = card.rect.y + 55
            for label, value in [("Batting style", self.batting_style()), ("Field preset", self.field_preset),
                                 ("Bat aggression", f"{self.batting_slider.value:g}/10"), ("Bowl aggression", f"{self.bowling_slider.value:g}/10")]:
                text(surface, label, (card.rect.x + 15, y), 11, MUTED); text(surface, value, (card.rect.right - 15, y), 12, GOLD if "style" in label else WHITE, bold=True, anchor="topright"); y += 31
            presets = ["Aggressive", "Neutral", "Defensive"]
            for i, preset in enumerate(presets):
                box = pygame.Rect(card.rect.x + 14, card.rect.y + 188 + i * 31, card.rect.width - 28, 26)
                pygame.draw.rect(surface, GREEN if preset == self.field_preset else CARD_ALT, box)
                text(surface, preset, box.center, 11, WHITE, bold=True, anchor="center")
            mini_y = card.rect.bottom - 107
            WeatherDisplay(pygame.Rect(card.rect.x + 14, mini_y, card.rect.width - 28, 55), self.engine.weather,
                           self.engine.weather_forecast[self.engine.weather_index:self.engine.weather_index + 6]).draw(surface)
            PitchDisplay(pygame.Rect(card.rect.x + 14, card.rect.bottom - 45, card.rect.width - 28, 30),
                         self.engine.pitch, self.engine.pitch_wear).draw(surface)
        else:
            stats_card = Card(left, self.active_stat.upper(), "STATS HUB"); stats_card.draw(surface)
            self._draw_stat_visual(surface, stats_card.content_rect)
            session = Card(right, "SESSION SUMMARY"); session.draw(surface)
            session_runs = sum(b["runs"] for b in self.ball_history[-30:]); session_wkts = sum(b["result"] == "W" for b in self.ball_history[-30:])
            innings = self.engine.current_innings
            fow = innings.fall_of_wickets[-1] if innings.fall_of_wickets else None
            rows = [("Day / Session", f"{self.day} / {self.session}"), ("Session runs", session_runs),
                    ("Session wickets", session_wkts), ("Current RR", f"{self.runs/max(1,self.legal_balls)*6:.2f}"),
                    ("Boundaries", sum(s["fours"] + s["sixes"] for s in self.batter_stats.values())),
                    ("Partnership", f"{self.partnership_runs} ({self.partnership_balls})"),
                    ("Conditions", f"{self.engine.pitch} / {self.engine.weather}"),
                    ("Ball age", f"{float(self.engine.last_factors.get('ball_age_overs', self.legal_balls/6)):.1f} overs"),
                    ("Last FOW", f"{fow['score']}/{fow['wicket']} ({fow['over']})" if fow else "None")]
            y = session.rect.y + 58
            for label, value in rows:
                text(surface, label, (session.rect.x + 16, y), 10, MUTED); text(surface, value, (session.rect.right - 16, y), 11, WHITE, bold=True, anchor="topright"); y += 27

    def _draw_stat_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if self.active_stat == "Scorecard": self._draw_batting_table(surface, rect.inflate(12, 12)); return
        if self.active_stat in ("Ring", "Boundary"):
            events = self.engine.shot_events if self.active_stat == "Ring" else [event for event in self.engine.shot_events if event.get("runs") in {4, 6}]
            graphic = rect.inflate(-30, -38)
            ShotMap(graphic, events[-80:], show_field=self.active_stat == "Ring").draw(surface)
            explanation = ("Ring: every scoring shot, dismissal and current field context." if self.active_stat == "Ring" else
                           "Boundary: only fours and sixes, revealing boundary-scoring zones.")
            text(surface, explanation, (rect.centerx, rect.bottom - 5), 10, MUTED, anchor="midbottom")
            return
        if self.active_stat == "Worm":
            pygame.draw.rect(surface, PANEL, rect); cumulative = 0; pts = []
            for i, ball in enumerate(self.ball_history):
                cumulative += ball["runs"]; pts.append((rect.x + int((i+1)*rect.width/max(1,len(self.ball_history))), rect.bottom - int(cumulative*rect.height/max(1,self.runs))))
            if len(pts)>1: pygame.draw.lines(surface, GREEN, False, pts, 2)
            opponent = [(rect.x, rect.bottom), (rect.centerx, rect.centery + 20), (rect.right, rect.y + 30)]; pygame.draw.lines(surface, RED, False, opponent, 2)
            text(surface, "Mavericks", (rect.x+8, rect.y+8), 10, GREEN); text(surface, "Opponent", (rect.x+88, rect.y+8), 10, RED)
        elif self.active_stat == "Momentum":
            pygame.draw.rect(surface, PANEL, rect)
            zero_y = rect.centery
            pygame.draw.line(surface, BORDER, (rect.x, zero_y), (rect.right, zero_y))
            window = 24
            values = []
            for i in range(len(self.ball_history)):
                recent = self.ball_history[max(0, i - window + 1):i + 1]
                values.append(sum(b["runs"] for b in recent) - 8 * sum(b["result"] == "W" for b in recent))
            if values:
                peak = max(24, max(abs(v) for v in values))
                step = rect.width / max(1, len(values))
                points = [(rect.x + int((i + 1) * step), zero_y - int(v * (rect.height / 2 - 14) / peak))
                          for i, v in enumerate(values)]
                for (x1, y1), (x2, y2) in zip(points, points[1:]):
                    colour = GREEN if (y1 + y2) / 2 <= zero_y else RED
                    pygame.draw.line(surface, colour, (x1, y1), (x2, y2), 2)
                last = points[-1]
                pygame.draw.circle(surface, GOLD, last, 4)
            text(surface, "Momentum: rolling 4-over swing — runs minus wicket damage.",
                 (rect.centerx, rect.bottom - 3), 10, MUTED, anchor="midbottom")
        elif self.active_stat == "Manhattan":
            over_runs = []
            for i in range(0, len(self.ball_history), 6): over_runs.append(sum(b["runs"] for b in self.ball_history[i:i+6]))
            bw = max(4, rect.width // max(1, len(over_runs)) - 3)
            for i, value in enumerate(over_runs):
                h = int(value / max(1, max(over_runs, default=1)) * (rect.height - 25)); pygame.draw.rect(surface, GOLD, (rect.x+i*(bw+3), rect.bottom-h, bw, h))
            text(surface, "Manhattan: runs scored in each over.", (rect.centerx, rect.bottom - 3), 10, MUTED, anchor="midbottom")
        else:
            partnerships = self.partnerships + [(self.striker["name"], self.non_striker["name"], self.partnership_runs, self.partnership_balls)]
            y = rect.y + 5
            for a, b, runs, balls in partnerships[-6:]:
                text(surface, f"{a} / {b}", (rect.x, y), 11, WHITE); text(surface, f"{runs} ({balls})", (rect.right, y), 11, GOLD, bold=True, anchor="topright")
                bar = pygame.Rect(rect.x, y + 19, rect.width, 6); pygame.draw.rect(surface, CARD_ALT, bar); pygame.draw.rect(surface, GREEN, (bar.x,bar.y,int(bar.width*min(1,runs/100)),bar.height)); y += 42
            text(surface, "Partnerships: runs added by each batting pair.", (rect.centerx, rect.bottom - 3), 10, MUTED, anchor="midbottom")

    def _draw_controls(self, surface: pygame.Surface) -> None:
        y = self.content_rect.bottom - 190
        card = Card(pygame.Rect(self.content_rect.x + 18, y, self.content_rect.width - 36, 54))
        card.draw(surface); self.batting_slider.draw(surface); self.bowling_slider.draw(surface)
        for button in self.action_buttons: button.draw(surface)
        # Current over ball tracker and auto-scrolling commentary share the footer.
        comm = Card(pygame.Rect(self.content_rect.x + 18, self.content_rect.bottom - 128, self.content_rect.width - 36, 110), "BALL TRACKER & COMMENTARY", "LATEST DELIVERY AUTO-SCROLL")
        comm.draw(surface)
        balls = self.ball_history[-6:]; bx = comm.rect.right - 222
        recent_overs = [sum(ball["runs"] for ball in self.ball_history[i:i+6]) for i in range(0, len(self.ball_history), 6)][-4:]
        text(surface, "Recent overs: " + "  |  ".join(map(str, recent_overs)) if recent_overs else "Recent overs: —",
             (comm.rect.right - 222, comm.rect.y + 44), 9, MUTED)
        for ball in balls:
            result = ball["result"]; colour = RED if result == "W" else GOLD if result in ("4", "6") else BLUE if result in ("Wd", "Nb") else GREEN if result != "•" else DIM
            pygame.draw.circle(surface, BG, (bx, comm.rect.y + 67), 14); pygame.draw.circle(surface, colour, (bx, comm.rect.y + 67), 14, 2)
            text(surface, result, (bx, comm.rect.y + 67), 10, colour, bold=True, anchor="center"); bx += 34
        colours = {"run": GREEN, "wicket": RED, "milestone": GOLD, "normal": WHITE}
        yy = comm.rect.y + 51
        for line, kind in self.commentary[-3:]:
            text(surface, clipped_text(line, comm.rect.width - 270, 11), (comm.rect.x + 14, yy), 11, colours[kind], bold=kind != "normal"); yy += 19

    def draw(self, surface: pygame.Surface) -> None:
        self._draw_header(surface)
        for _, button in self.main_tab_buttons: button.draw(surface)
        self.hub_button.draw(surface)
        self.perspective_button.draw(surface)
        for _, button in self.stat_buttons: button.draw(surface)
        body_y, body_bottom = self.content_rect.y + 136, self.content_rect.bottom - 198
        left = pygame.Rect(self.content_rect.x + 18, body_y, int((self.content_rect.width - 48) * .67), body_bottom - body_y)
        right = pygame.Rect(left.right + 12, body_y, self.content_rect.right - 18 - left.right - 12, body_bottom - body_y)
        if self.active_tab == "Batting": self._draw_batting_table(surface, left); self._draw_player_cards(surface, right)
        elif self.active_tab == "Bowling": self._draw_bowling_table(surface, left); self._draw_player_cards(surface, right)
        else: self._draw_summary(surface, left, right)
        self._draw_controls(surface)
        if self.context.get("toast"): text(surface, self.context.pop("toast"), (self.content_rect.right - 22, self.content_rect.y + 47), 11, GREEN, anchor="topright")
        if self.modal: self.modal.draw(surface)

    def kill(self) -> None:
        from src.controllers.audio_controller import AudioManager
        AudioManager().stop_ambience()
        for player in self.batters: self._sync_player_match_stats(player)
        self.context["match_state"] = {"runs": self.runs, "wickets": self.wickets, "balls": self.legal_balls,
                                       "day": self.day, "session": self.session, "engine": self.engine.to_dict()}
        save_game({"current_match_ui": self.context["match_state"]}, self.context["database_path"])
        super().kill()
