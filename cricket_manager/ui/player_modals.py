"""Player detail, match-statistics, and side-by-side comparison modals."""
from __future__ import annotations
import random
import pygame
from src.models.currency import format_money
from src.models.transfer import transfer_value
from src.utilities.player_portraits import draw_portrait
from .shared_components import group_average
from .widgets import (AttributeBar, Button, ButtonStyle, Card, ComparisonPanel, ContractNegotiationModal,
                      FormGraph, Modal, RadarChart, ShotMap, BowlingMap, StarRating, TabBar, draw_country_flag)
from .widgets.common import ACCENT, BG, BLUE, BORDER, CARD, DIM, GOLD, GREEN, MUTED, PANEL, RED, WARNING, WHITE, text


def _profile_values(player: dict) -> dict[str, int]:
    return {"Batting": group_average(player, "batting"), "Bowling": group_average(player, "bowling"),
            "Fielding": group_average(player, "fielding"), "Mental": group_average(player, "mental"),
            "Physical": player.get("mental", {}).get("fitness", 50)}


class PlayerDetailModal(Modal):
    """Tabbed player hub; Match Stats mirrors the live innings analysis view."""
    TABS = ["Back", "Records", "Bat Form", "Bowl Form", "Personal", "Match Stats"]

    def __init__(self, viewport: pygame.Rect, player: dict, comparison_candidate: dict | None = None,
                 database_path: str | None = None):
        super().__init__(viewport, "Player Profile", (1080, 630))
        self.player, self.comparison_candidate = player, comparison_candidate
        self.database_path = database_path
        self.active_tab, self.open_comparison = "Personal", False
        self.compare_button = Button(pygame.Rect(self.rect.right - 175, self.rect.y + 11, 118, 30),
                                     "COMPARE", ButtonStyle.SUCCESS)
        tab_width = (self.rect.width - 36) // len(self.TABS)
        self.tab_buttons = []
        for index, label in enumerate(self.TABS):
            style = ButtonStyle.DANGER if label == "Back" else ButtonStyle.SECONDARY
            self.tab_buttons.append((label, Button(pygame.Rect(self.rect.x + 18 + index * tab_width,
                                                               self.rect.bottom - 40, tab_width - 4, 29), label.upper(), style,
                                                      selected=label == self.active_tab)))
        self.match_stats, self.ball_outcomes = self._build_match_stats()
        self.spatial_period = "This Match"
        self.spatial_bar = TabBar(pygame.Rect(0, 0, 260, 26), ["This Match", "Season"], self.spatial_period)
        self.contract_modal: ContractNegotiationModal | None = None
        self.contract_signed: dict[str, int] | None = None
        self.negotiate_button = Button(pygame.Rect(0, 0, 150, 28), "NEGOTIATE", ButtonStyle.SUCCESS)

    def _build_match_stats(self) -> tuple[dict, list[int | str]]:
        supplied = self.player.get("current_match_stats")
        if supplied:
            outcomes = supplied.get("outcomes", [])
            return supplied, outcomes
        rng = random.Random(self.player["id"] * 101 + self.player["form"])
        balls = rng.randint(28, 72); target = max(4, int(balls * (.45 + self.player["overall"] / 180)))
        outcomes: list[int | str] = []
        while len(outcomes) < balls:
            outcomes.append(rng.choices([0, 1, 2, 3, 4, 6], [35, 34, 10, 2, 15, 4])[0])
        scale = target / max(1, sum(int(v) for v in outcomes))
        # Preserve cricket outcomes while moving the generated innings near target.
        if scale < .7: outcomes = [0 if v == 1 and rng.random() < .3 else v for v in outcomes]
        runs = sum(int(v) for v in outcomes)
        return {"runs": runs, "balls": balls, "mins": balls + rng.randint(18, 55),
                "fours": outcomes.count(4), "sixes": outcomes.count(6),
                "sr": runs / balls * 100, "dropped": 0, "lbw": 1,
                "missed": rng.randint(0, 3), "catchable": rng.randint(0, 1)}, outcomes

    def process_event(self, event: pygame.event.Event) -> bool:
        if self.contract_modal is not None:
            closed = self.contract_modal.process_event(event)
            terms = self.contract_modal.agreed_terms
            if terms:
                self.contract_signed = terms
                self.player["wage"] = terms["wage"]
                self.player["contract_years_remaining"] = terms["years"]
                if self.database_path:
                    from database import renew_player_contract
                    renew_player_contract(self.player["id"], terms["wage"], terms["years"],
                                          terms["bonus"], self.database_path)
            if closed or terms:
                self.contract_modal = None
            return False
        if self.compare_button.process_event(event): self.open_comparison = True
        if self.active_tab == "Personal" and self.negotiate_button.process_event(event):
            self.contract_modal = ContractNegotiationModal(self.viewport, self.player)
            return False
        if self.active_tab == "Match Stats":
            chosen = self.spatial_bar.process_event(event)
            if chosen: self.spatial_period = chosen
        for label, button in self.tab_buttons:
            if button.process_event(event):
                if label == "Back": return True
                self.active_tab = label
                for other_label, other in self.tab_buttons: other.selected = other_label == label
        return super().process_event(event)

    def _draw_personal(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        left_w, centre_w = int(area.width * .27), int(area.width * .34)
        left = Card(pygame.Rect(area.x, area.y, left_w, area.height), "PROFILE")
        centre = Card(pygame.Rect(left.rect.right + 10, area.y, centre_w, area.height), "ABILITY PROFILE")
        right = Card(pygame.Rect(centre.rect.right + 10, area.y, area.right - centre.rect.right - 10, area.height), "CONTRACT & TRAITS")
        for card in (left, centre, right): card.draw(surface)
        avatar_rect = pygame.Rect(left.rect.centerx - 45, left.rect.y + 50, 90, 90)
        draw_portrait(surface, avatar_rect, self.player)
        pygame.draw.aacircle(surface, GREEN, avatar_rect.center, 45, 2)
        text(surface, self.player["name"], (left.rect.centerx, left.rect.y + 153), 18, bold=True, anchor="center")
        text(surface, f"{self.player['age']} • {self.player['role']}", (left.rect.centerx, left.rect.y + 180), 12, MUTED, anchor="center")
        flag = pygame.Rect(left.rect.centerx - 75, left.rect.y + 199, 28, 18)
        draw_country_flag(surface, flag, self.player["nationality"])
        text(surface, self.player["nationality"], (left.rect.centerx + 8, left.rect.y + 202), 12, MUTED, anchor="center")
        pygame.draw.aacircle(surface, GOLD, (left.rect.centerx, left.rect.y + 270), 39)
        text(surface, self.player["overall"], (left.rect.centerx, left.rect.y + 270), 27, BG, bold=True, anchor="center")
        text(surface, "OVERALL", (left.rect.centerx, left.rect.y + 318), 11, MUTED, bold=True, anchor="center")
        star_x = left.rect.x + 24
        star_w = left.rect.width - 48
        StarRating(pygame.Rect(star_x, left.rect.y + 338, star_w, 20), self.player["overall"], "Ability  ").draw(surface)
        StarRating(pygame.Rect(star_x, left.rect.y + 362, star_w, 20),
                   self.player.get("potential", self.player["overall"]), "Potential").draw(surface)
        RadarChart(pygame.Rect(centre.rect.x + 10, centre.rect.y + 40, centre.rect.width - 20, 205), _profile_values(self.player)).draw(surface)
        y = centre.rect.y + 252
        for label, value in _profile_values(self.player).items():
            AttributeBar(pygame.Rect(centre.rect.x + 20, y, centre.rect.width - 40, 27), label, value).draw(surface); y += 31
        self.negotiate_button.rect.topright = (right.rect.right - 14, right.rect.y + 11)
        self.negotiate_button.draw(surface)
        x, y = right.rect.x + 18, right.rect.y + 54
        details = [("Market value", format_money(transfer_value(self.player))),
                   ("Contract remaining", f"{self.player['contract_years_remaining']} years"),
                   ("Weekly wage", format_money(self.player['wage'])), ("Appearance bonus", format_money(self.player['wage']//8))]
        for label, value in details:
            text(surface, label, (x, y), 12, MUTED); text(surface, value, (right.rect.right - 18, y), 12, WHITE, bold=True, anchor="topright"); y += 27
        y += 8; text(surface, "TRAITS", (x, y), 11, MUTED, bold=True); y += 24
        traits = [("Composed under pressure", self.player["mental"]["big_match"]),
                  ("Reliable performer", self.player["mental"]["consistency"]), ("Athletic", self.player["mental"]["fitness"])]
        for label, value in traits:
            AttributeBar(pygame.Rect(x, y, right.rect.width - 36, 27), label, value).draw(surface); y += 35
        AttributeBar(pygame.Rect(x, y + 5, right.rect.width - 36, 27), "Morale", self.player["mental"]["morale"]).draw(surface)
        spark_top = y + 48
        spark_height = right.rect.bottom - spark_top - 30
        if spark_height >= 50:
            text(surface, "FORM (LAST 30)", (x, spark_top), 11, MUTED, bold=True)
            values = (self.player.get("form_history", {}).get("values") or [self.player["form"]])[-30:]
            FormGraph(pygame.Rect(x, spark_top + 18, right.rect.width - 36, spark_height - 18), values).draw(surface)

    def _draw_match_stats(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        gap = 10; top_h = int(area.height * .34); left_w = int(area.width * .43)
        stats_card = Card(pygame.Rect(area.x, area.y, left_w, top_h), "CURRENT MATCH STATS")
        chances_card = Card(pygame.Rect(area.x, stats_card.rect.bottom + gap, left_w,
                                        area.bottom - stats_card.rect.bottom - gap), "CHANCES")
        right_w = area.right - stats_card.rect.right - gap
        graph_card = Card(pygame.Rect(stats_card.rect.right + gap, area.y, right_w, top_h), "BALL-BY-BALL RUNS")
        legend_card = Card(pygame.Rect(graph_card.rect.x, graph_card.rect.bottom + gap, right_w,
                                       area.bottom - graph_card.rect.bottom - gap), "SPATIAL ANALYTICS")
        for card in (stats_card, graph_card, chances_card, legend_card): card.draw(surface)
        s = self.match_stats
        headers = ["RUNS", "BALLS", "MINS", "4s", "6s", "SR%"]
        values = [s["runs"], s["balls"], s["mins"], s["fours"], s["sixes"], f"{s['sr']:.1f}"]
        cw = (stats_card.rect.width - 24) // 6
        for i, (header, value) in enumerate(zip(headers, values)):
            cx = stats_card.rect.x + 12 + i * cw + cw // 2
            text(surface, header, (cx, stats_card.rect.y + 62), 10, MUTED, bold=True, anchor="center")
            text(surface, value, (cx, stats_card.rect.y + 91), 17, GOLD if i == 0 else WHITE, bold=True, anchor="center")
        text(surface, "INNINGS IN PROGRESS", (stats_card.rect.centerx, stats_card.rect.y + 135), 11, GREEN, bold=True, anchor="center")
        chances = [("Dropped catches", s["dropped"]), ("LBW appeals", s["lbw"]),
                   ("Played & missed", s["missed"]), ("Catchable shots", s["catchable"])]
        for i, (label, value) in enumerate(chances):
            yy = chances_card.rect.y + 55 + i * 25; text(surface, label, (chances_card.rect.x + 16, yy), 12, MUTED)
            text(surface, value, (chances_card.rect.right - 18, yy), 12, WHITE, bold=True, anchor="topright")
        self._draw_ball_graph(surface, graph_card.content_rect)

        # Period filter: "This Match" uses the live innings; "Season" pulls
        # every persisted delivery so the maps stay legible as data accumulates.
        self.spatial_bar.move_to((legend_card.rect.right - 14, legend_card.rect.y + 13), anchor="topright")
        self.spatial_bar.draw(surface)
        season_events = self.player.get("match_events", {})
        if self.spatial_period == "Season" and (season_events.get("shots") or season_events.get("deliveries")):
            events, deliveries = season_events.get("shots", []), season_events.get("deliveries", [])
        else:
            events = self.player.get("shot_events", [])
            if not events:
                rng = random.Random(int(self.player.get("id", 0)))
                events = [{"angle": rng.random() * 6.283, "distance": .25 + rng.random() * .72,
                           "runs": rng.choice([0, 1, 1, 2, 4, 4, 6]), "wicket": False} for _ in range(28)]
            deliveries = self.player.get("bowling_events", [])
            if not deliveries and self.player.get("role") in {"Bowler", "All-Rounder"}:
                rng = random.Random(1000 + int(self.player.get("id", 0)))
                deliveries = [{"x": rng.gauss(.58, .11), "y": rng.gauss(.50, .16),
                               "runs": rng.choice([0, 0, 1, 2, 4]), "wicket": rng.random() < .08} for _ in range(32)]
        content = pygame.Rect(legend_card.content_rect.x, legend_card.content_rect.y + 30,
                              legend_card.content_rect.width, legend_card.content_rect.height - 30)
        half = (content.width - 16) // 2
        text(surface, f"WAGON WHEEL ({len(events)} shots)", (content.x, content.y), 10, MUTED, bold=True)
        ShotMap(pygame.Rect(content.x, content.y + 16, half, content.height - 16), events).draw(surface)
        if deliveries or self.player.get("role") in {"Bowler", "All-Rounder"}:
            text(surface, f"BOWLING MAP ({len(deliveries)} balls)", (content.x + half + 16, content.y), 10, MUTED, bold=True)
            BowlingMap(pygame.Rect(content.x + half + 16, content.y + 16, half, content.height - 16),
                      deliveries).draw(surface)

    def _draw_ball_graph(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        plot = rect.inflate(-18, -22); pygame.draw.rect(surface, PANEL, plot)
        for i in range(5):
            y = plot.bottom - int(i * plot.height / 4); pygame.draw.line(surface, BORDER, (plot.x, y), (plot.right, y))
        total = max(1, sum(int(v) for v in self.ball_outcomes)); cumulative = 0; points = []
        colours = {0: DIM, 1: BLUE, 2: GREEN, 3: WARNING, 4: GOLD, 6: RED, "W": BG}
        for i, outcome in enumerate(self.ball_outcomes):
            if outcome != "W": cumulative += int(outcome)
            px = plot.x + int((i + 1) * plot.width / max(1, len(self.ball_outcomes)))
            py = plot.bottom - int(cumulative * plot.height / total)
            points.append((px, py, outcome))
        if len(points) > 1: pygame.draw.lines(surface, ACCENT, False, [(x, y) for x, y, _ in points], 2)
        for x, y, outcome in points: pygame.draw.aacircle(surface, colours.get(outcome, WHITE), (x, y), 3)
        text(surface, "BALLS FACED", (plot.centerx, plot.bottom + 8), 9, MUTED, anchor="midtop")

    def _draw_secondary(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        card = Card(area, self.active_tab.upper()); card.draw(surface)
        if self.active_tab in ("Bat Form", "Bowl Form"):
            history=self.player.get("form_history",{}); values=history.get("values") or [self.player["form"]]
            FormGraph(pygame.Rect(area.x + 45, area.y + 80, area.width - 90, area.height - 175), values[-30:]).draw(surface)
            text(surface,f"WEEK {history.get('week',self.player['form'])}   MONTH {history.get('month',self.player['form'])}   SEASON {history.get('season',self.player['form'])}   • {history.get('trend','Steady')}",(area.centerx,area.bottom-48),13,GOLD,True,anchor="center")
        elif self.active_tab == "Records":
            records=self.player.get("records",{}); contexts=("League","Cup","Friendly","International"); x=area.x+25; y=area.y+62; cw=(area.width-50)//4
            for i,context in enumerate(contexts):
                rec=records.get(context,{}); panel=pygame.Rect(x+i*cw,y,cw-8,area.height-90); Card(panel,context.upper()).draw(surface)
                lines=[("Matches",rec.get("matches",0)),("Runs",rec.get("runs",0)),("Average",rec.get("batting_average",0)),("Strike rate",rec.get("strike_rate",0)),("50s / 100s",f"{rec.get('fifties',0)} / {rec.get('hundreds',0)}"),("Highest",rec.get("highest_score",0)),("Wickets",rec.get("wickets",0)),("Overs",rec.get("overs",'0.0')),("Economy",rec.get("economy",0)),("5W / 10W",f"{rec.get('five_wickets',0)} / {rec.get('ten_wickets',0)}"),("Catches / stumpings",f"{rec.get('catches',0)} / {rec.get('stumpings',0)}")]
                for j,(label,value) in enumerate(lines):text(surface,label,(panel.x+12,panel.y+52+j*27),10,MUTED);text(surface,value,(panel.right-12,panel.y+52+j*27),11,WHITE,True,anchor="topright")
        else:
            groups=[("BATTING",self.player.get("batting",{})),("BOWLING",self.player.get("bowling",{})),("FIELDING",self.player.get("fielding",{})),("MENTAL",self.player.get("mental",{})),("PHYSICAL",self.player.get("physical",{}))]
            col=(area.width-60)//len(groups)
            for i,(heading,attrs) in enumerate(groups):
                x=area.x+20+i*col;text(surface,heading,(x,area.y+58),12,GOLD,True)
                for j,(label,value) in enumerate(attrs.items()):AttributeBar(pygame.Rect(x,area.y+84+j*35,col-12,27),label.replace('_',' ').title(),value).draw(surface)

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface); self.compare_button.draw(surface)
        area = pygame.Rect(self.content_rect.x, self.content_rect.y, self.content_rect.width, self.content_rect.height - 45)
        if self.active_tab == "Personal": self._draw_personal(surface, area)
        elif self.active_tab == "Match Stats": self._draw_match_stats(surface, area)
        else: self._draw_secondary(surface, area)
        for _, button in self.tab_buttons: button.draw(surface)
        if self.contract_modal is not None: self.contract_modal.draw(surface)


class PlayerComparisonModal(Modal):
    def __init__(self, viewport: pygame.Rect, player_a: dict, player_b: dict):
        super().__init__(viewport, "Player Comparison", (1160, 650)); self.player_a, self.player_b = player_a, player_b
        self.done_button = Button(pygame.Rect(self.rect.centerx - 60, self.rect.bottom - 45, 120, 32), "CLOSE", ButtonStyle.PRIMARY)

    def process_event(self, event: pygame.event.Event) -> bool:
        return self.done_button.process_event(event) or super().process_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface); gap = 12; content = self.content_rect; panel_w = (content.width - gap) // 2; height = content.height - 43
        ComparisonPanel(pygame.Rect(content.x, content.y, panel_w, height), self.player_a, self.player_b).draw(surface)
        ComparisonPanel(pygame.Rect(content.x + panel_w + gap, content.y, panel_w, height), self.player_b, self.player_a).draw(surface)
        self.done_button.draw(surface)
