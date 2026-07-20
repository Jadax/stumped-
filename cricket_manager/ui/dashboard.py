"""Responsive command-centre dashboard with a strict non-overlapping grid."""
from __future__ import annotations

from datetime import date, timedelta
import pygame
from src.models.currency import format_money

from database import fetch_inbox_messages, fetch_league_standings, fetch_next_fixture, fetch_players
from src.utilities.graphics import draw_crest
from .shared_components import BaseScreen, group_average, estimated_value
from .widgets import Button, ButtonStyle, Card
from .widgets.common import BORDER, CARD, CARD_ALT, GOLD, GREEN, MUTED, RED, WHITE, clipped_text, text
from .widgets.spacing import columns, rows


class DashboardScreen(BaseScreen):
    title = "Dashboard"

    def build(self) -> None:
        db, team = self.context["database_path"], self.context["team"]
        self.fixture = fetch_next_fixture(team["id"], db)
        self.messages = fetch_inbox_messages(5, db)
        self.players = self.context["players"]
        manager = self.context.get("new_game_setup", {}).get("manager", {})
        self.manager_name = manager.get("name", "Manager")
        opponent_id = 2
        if self.fixture:
            opponent_id = self.fixture["away_team"] if self.fixture["home_team"] == team["id"] else self.fixture["home_team"]
        self.opponent_players = fetch_players(opponent_id, db)
        self.standings = [dict(position=i + 1, **row) for i, row in enumerate(fetch_league_standings(db))]
        self.buttons = []
        actions = [("Sim to Match", ButtonStyle.SUCCESS, "Pre-Match"),
                   ("View Squad", ButtonStyle.PRIMARY, "Squad"),
                   ("Transfers", ButtonStyle.SECONDARY, "Transfers"),
                   ("Training", ButtonStyle.SECONDARY, "Training")]
        width, gap = 110, 7
        x = self.content_rect.right - 20 - len(actions) * width - (len(actions) - 1) * gap
        for label, style, destination in actions:
            self.buttons.append((Button(pygame.Rect(x, self.content_rect.y + 23, width, 30), label, style), destination)); x += width + gap

    def process_event(self, event: pygame.event.Event) -> None:
        for button, destination in self.buttons:
            if button.process_event(event):
                if destination == "Advance Day" and self.context.get("advance_day"): self.context["advance_day"]()
                elif self.navigate: self.navigate(destination)

    @staticmethod
    def _ranked(players: list[dict], group: str) -> list[dict]:
        return sorted(players, key=lambda player: group_average(player, group), reverse=True)[:3]

    def _opponent_name(self) -> str:
        if not self.fixture: return "Next opponent pending"
        return self.fixture["away_name"] if self.fixture["home_team"] == self.context["team"]["id"] else self.fixture["home_name"]

    def _next_fixture(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        fixture = self.fixture or {"format":"T20","date":"2026-04-04","venue":"Club Cricket Ground"}
        opponent = self._opponent_name()
        Card(rect, "NEXT FIXTURE", f"{fixture['format']} • {fixture['date']}").draw(surface)
        cx1, cx2, cy = rect.x + 86, rect.right - 86, rect.y + 86
        draw_crest(surface, (cx1, cy), 54, self.context["team"]["name"], self.context["team"]["name"][:2])
        draw_crest(surface, (cx2, cy), 54, opponent, opponent[:2])
        text(surface, clipped_text(self.context["team"]["name"], 180, 14, True), (cx1, cy + 39), 14, GOLD, True, anchor="center")
        text(surface, clipped_text(opponent, 180, 14, True), (cx2, cy + 39), 14, WHITE, True, anchor="center")
        text(surface, "VS", (rect.centerx, cy - 8), 24, MUTED, True, anchor="center")
        venue = fixture.get("venue", "Club Cricket Ground")
        text(surface, clipped_text(f"{venue} • Green surface — pace friendly", rect.width - 40, 12),
             (rect.centerx, cy + 54), 12, MUTED, anchor="center")
        pygame.draw.line(surface, BORDER, (rect.x + 14, rect.y + 155), (rect.right - 14, rect.y + 155))
        groups = [("YOUR BATTERS", self._ranked(self.players,"batting"), "batting"),
                  ("YOUR BOWLERS", self._ranked(self.players,"bowling"), "bowling"),
                  ("OPP BATTERS", self._ranked(self.opponent_players,"batting"), "batting"),
                  ("OPP BOWLERS", self._ranked(self.opponent_players,"bowling"), "bowling")]
        col_w = (rect.width - 30) // 4
        for col, (heading, players, group) in enumerate(groups):
            x = rect.x + 15 + col * col_w
            text(surface, heading, (x, rect.y + 164), 10, MUTED, True)
            for index, player in enumerate(players):
                yy = rect.y + 183 + index * 17
                text(surface, clipped_text(player["name"], col_w - 42, 10), (x, yy), 10, WHITE)
                text(surface, group_average(player, group), (x + col_w - 7, yy), 10, GOLD, True, anchor="topright")

    def _recent_form(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        Card(rect, "RECENT FORM", "60% WIN RATE").draw(surface)
        results = ["L", "W", "W", "W", "L"]
        box = min(36, (rect.width - 52) // 5); gap = 8
        x = rect.centerx - (box * 5 + gap * 4) // 2
        for result in results:
            colour = GREEN if result == "W" else RED if result == "L" else GOLD
            rr = pygame.Rect(x, rect.y + 52, box, 28); pygame.draw.rect(surface, colour, rr, border_radius=4)
            text(surface, result, rr.center, 14, WHITE, True, anchor="center"); x += box + gap
        text(surface, "L  W  W  W  L", (rect.centerx, rect.bottom - 17), 11, MUTED, True, anchor="center")

    def _finance(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        Card(rect, "FINANCIAL SNAPSHOT", "CURRENT SEASON").draw(surface)
        values = [("Cash", format_money(self.context['team']['cash']), GREEN),
                  ("Wage budget", f"{format_money(184_500, compact=True)} / {format_money(230_000, compact=True)}", WHITE),
                  ("Last match revenue", format_money(286_400), GOLD)]
        for index, (label, value, colour) in enumerate(values):
            y = rect.y + 49 + index * 19; text(surface, label, (rect.x + 15, y), 11, MUTED)
            text(surface, value, (rect.right - 15, y), 12, colour, True, anchor="topright")

    def _objectives(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        Card(rect, "BOARD OBJECTIVES", "0/4 COMPLETE").draw(surface)
        goals = ["Qualify for Playoffs", "Win First 3 Matches", "Win 7+ Home Matches", "Achieve Positive NRR"]
        available = max(18, (rect.height - 52) // len(goals))
        for i, goal in enumerate(goals):
            y = rect.y + 51 + i * available
            pygame.draw.rect(surface, MUTED, (rect.x + 15, y + 2, 11, 11), 1)
            text(surface, clipped_text(goal, rect.width - 48, 12), (rect.x + 34, y), 12, WHITE)

    def _standings(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        Card(rect, "LEAGUE STANDINGS", "DIVISION 1").draw(surface)
        widths = [28, rect.width - 166, 34, 54, 42]
        x, y = rect.x + 10, rect.y + 49
        for header, width in zip(("#","TEAM","W","NRR","PTS"), widths):
            text(surface, header, (x + 3, y), 10, MUTED, True); x += width
        show = self.standings[:5]
        for i, row in enumerate(show):
            rr = pygame.Rect(rect.x + 8, y + 19 + i * 25, rect.width - 16, 23)
            colour = CARD.lerp(GREEN, .28) if i < 2 else CARD.lerp(RED, .25) if i >= len(show)-2 else CARD_ALT if i%2 else CARD
            pygame.draw.rect(surface, colour, rr)
            mine = row["team_id"] == self.context["team"]["id"]
            if mine: pygame.draw.rect(surface, GOLD, rr, 2)
            vals = [row["position"], clipped_text(row["name"], widths[1]-8, 11), row["won"], f"{row['net_run_rate']:+.2f}", row["points"]]
            x = rect.x + 10
            for value, width in zip(vals, widths): text(surface, value, (x+3,rr.y+6), 11, GOLD if mine else WHITE, mine); x += width

    def _squad(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        available = sum(1 for player in self.players if player["mental"].get("fitness", 0) >= 55)
        Card(rect, "SQUAD STATUS", f"{available}/{len(self.players)} AVAILABLE").draw(surface)
        for i, player in enumerate(sorted(self.players,key=lambda p:p["mental"].get("fitness",50))[:3]):
            fitness = player["mental"].get("fitness", 50); status = "Fit" if fitness >=55 else "Minor knock" if fitness >=40 else "Injured"
            colour = GREEN if status=="Fit" else GOLD if status=="Minor knock" else RED
            y=rect.y+51+i*24; pygame.draw.circle(surface,colour,(rect.x+17,y+6),5)
            text(surface,clipped_text(player["name"],rect.width-110,11),(rect.x+31,y),11,WHITE)
            text(surface,status,(rect.right-14,y),11,colour,True,anchor="topright")

    def _upcoming(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        Card(rect, "UPCOMING FIXTURES", "NEXT 3").draw(surface)
        base=date.fromisoformat(self.fixture.get("date","2026-04-04") if self.fixture else "2026-04-04")
        opponents=[self._opponent_name(),"Birmingham Bears","Melbourne Mariners"]
        for i,opponent in enumerate(opponents):
            y=rect.y+51+i*24; text(surface,(base+timedelta(days=i*4)).strftime("%b %d"),(rect.x+14,y),11,MUTED)
            text(surface,clipped_text(opponent,max(30,rect.width-150),11),(rect.x+70,y),11,WHITE)
            text(surface,"CUP" if i==1 else "LEAGUE",(rect.right-14,y),10,GOLD if i==1 else GREEN,True,anchor="topright")

    def _top_buys(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        Card(rect, "TOP BUYS", "MARKET WATCH").draw(surface)
        market = sorted(self.opponent_players, key=estimated_value, reverse=True)[:3]
        for i,player in enumerate(market):
            y=rect.y+51+i*24; text(surface,clipped_text(player["name"],rect.width-102,11),(rect.x+14,y),11,GOLD)
            text(surface, format_money(estimated_value(player), compact=True),(rect.right-14,y),11,WHITE,True,anchor="topright")

    def _news(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        Card(rect, "NEWS & CLUB INBOX", f"{sum(not m['read'] for m in self.messages)} UNREAD").draw(surface)
        col_w=(rect.width-30)//2
        for i,message in enumerate(self.messages[:4]):
            col,row=i%2,i//2; x=rect.x+15+col*col_w; y=rect.y+51+row*23
            symbol="!!!" if message["priority"]=="HIGH" else "!!" if message["priority"]=="MEDIUM" else "!"
            colour=RED if message["priority"]=="HIGH" else GOLD if message["priority"]=="MEDIUM" else MUTED
            text(surface,symbol,(x,y),10,colour,True); text(surface,clipped_text(message["title"],col_w-42,11),(x+31,y),11,WHITE,not message["read"])

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, f"Welcome back, {self.manager_name}  •  {self.context['team']['name']}  •  Division {self.context['team']['division']}")
        for button,_ in self.buttons: button.draw(surface)
        body=pygame.Rect(self.content_rect.x+18,self.content_rect.y+69,self.content_rect.width-36,self.content_rect.height-84)
        news_h=max(92,int(body.height*.17)); main=pygame.Rect(body.x,body.y,body.width,body.height-news_h-10); news=pygame.Rect(body.x,main.bottom+10,body.width,news_h)
        left,right=columns(main,(.60,.40),10)
        left_rows=rows(left,(.52,.24,.24),10); split=columns(left_rows[1],(.5,.5),10)
        right_rows=rows(right,(.48,.24,.28),8); right_bottom=columns(right_rows[2],(.5,.5),8)
        self._next_fixture(surface,left_rows[0]); self._recent_form(surface,split[0]); self._finance(surface,split[1]); self._objectives(surface,left_rows[2])
        self._standings(surface,right_rows[0]); self._squad(surface,right_rows[1]); self._upcoming(surface,right_bottom[0]); self._top_buys(surface,right_bottom[1]); self._news(surface,news)
        if self.context.get("toast"): text(surface,self.context.pop("toast"),(self.content_rect.right-20,self.content_rect.y+54),12,GREEN,True,anchor="topright")
