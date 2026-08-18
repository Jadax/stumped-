"""Club finance ledger, cash projection, ticket pricing, and sponsorships."""
from __future__ import annotations
from collections import defaultdict
import pygame
from src.models.currency import format_money
from database import (add_financial_transaction, connect, create_inbox_message, fetch_financial_log, get_team_summary,
                      renew_sponsorship, set_ticket_price)
from .shared_components import BaseScreen
from .widgets import Button, ButtonStyle, Card, Slider
from .widgets.common import BORDER, GOLD, GREEN, MUTED, RED, WHITE, text


class FinancesScreen(BaseScreen):
    title = "Finances"

    def build(self) -> None:
        self.team_id, self.db = self.context["team"]["id"], self.context["database_path"]
        self.refresh()
        x, y, w = self.content_rect.x + 18, self.content_rect.y + 77, self.content_rect.width - 36
        self.x, self.y, self.w = x, y, w
        self.ticket_slider = Slider(pygame.Rect(x + int(w * .67) + 24, self.content_rect.bottom - 125, int(w * .33) - 48, 38),
                                    "Ticket price", 5, 80, self.team.get("ticket_price", 24), 1, lambda v: format_money(int(v)))
        self.sponsor_button = Button(pygame.Rect(x + int(w * .67) + 14, self.content_rect.bottom - 75, int(w * .33) - 28, 27),
                                     "RENEW SPONSORSHIP", ButtonStyle.SUCCESS)
        self.revenue_button = Button(pygame.Rect(x + int(w * .67) + 14, self.content_rect.bottom - 42, int(w * .33) - 28, 27),
                                     "RECORD NEXT MATCHDAY", ButtonStyle.PRIMARY)

    def refresh(self) -> None:
        self.team = get_team_summary(self.team_id, self.db); self.context["team"] = self.team
        self.ledger = fetch_financial_log(self.team_id, self.db)
        self.income, self.expenses = defaultdict(int), defaultdict(int)
        for row in self.ledger:
            (self.income if row["kind"] == "INCOME" else self.expenses)[row["category"]] += row["amount"]
        self.total_income, self.total_expense = sum(self.income.values()), sum(self.expenses.values())
        with connect(self.db) as connection:
            self.wages = connection.execute("SELECT COALESCE(SUM(wage),0) FROM players WHERE team_id=?", (self.team_id,)).fetchone()[0]
            sponsor = connection.execute("SELECT * FROM sponsorships WHERE team_id=? AND status='ACTIVE' ORDER BY id DESC LIMIT 1", (self.team_id,)).fetchone()
            self.sponsor = dict(sponsor) if sponsor else None

    def process_event(self, event: pygame.event.Event) -> None:
        if self.ticket_slider.process_event(event):
            set_ticket_price(self.team_id, int(self.ticket_slider.value), self.db); self.team["ticket_price"] = int(self.ticket_slider.value)
        if self.sponsor_button.process_event(event):
            self.sponsor = renew_sponsorship(self.team_id, self.db); self.context["toast"] = "Boundary Bank sponsorship renewed"
            create_inbox_message("MEDIUM", "Sponsorship renewed",
                                 f"Boundary Bank will pay {format_money(self.sponsor['monthly_value'])} per month through {self.sponsor['end_date']}.",
                                 timestamp=f"{self.context.get('current_date','2026-04-01')} 11:00", database_path=self.db)
            self.context["refresh_inbox"] = True
        if self.revenue_button.process_event(event):
            atmosphere = (self.team.get("stadium_level", 1) - 1) * .025
            from src.models.fan_sentiment import demand_modifier
            fan_mod = demand_modifier(int(self.team.get("fan_morale", 50)))
            demand = max(.48, min(.99, 1.12 - (self.ticket_slider.value - 20) * .012 + atmosphere + fan_mod))
            attendance = int(self.team["stadium_capacity"] * demand)
            revenue = int(attendance * self.ticket_slider.value)
            add_financial_transaction(self.team_id, self.context.get("current_date", "2026-04-01"), "Matchday Revenue", "INCOME",
                                      revenue, f"Gate receipts: {attendance:,} attendance", self.db)
            self.context["toast"] = f"Matchday revenue {format_money(revenue)}"; self.refresh()

    def _draw_summary(self, surface: pygame.Surface) -> None:
        gap, width = 10, (self.w - 20) // 3
        cards = [Card(pygame.Rect(self.x + i * (width + gap), self.y, width, 91), title)
                 for i, title in enumerate(("CASH BALANCE", "WAGE BUDGET", "SEASON PROJECTION"))]
        for card in cards: card.draw(surface)
        text(surface, format_money(self.team['cash']), (cards[0].rect.x + 15, cards[0].rect.y + 57), 19, GREEN, bold=True)
        budget = 230_000; text(surface, f"{format_money(self.wages)} / {format_money(budget)}", (cards[1].rect.x + 15, cards[1].rect.y + 57), 16, GOLD if self.wages > budget else WHITE, bold=True)
        projection = self.team["cash"] + (self.total_income - self.total_expense) // 6
        text(surface, format_money(projection), (cards[2].rect.x + 15, cards[2].rect.y + 57), 18, GREEN if projection >= 0 else RED, bold=True)

    @staticmethod
    def _draw_breakdown(surface: pygame.Surface, card: Card, values: dict, colour) -> None:
        card.draw(surface); total = sum(values.values()); y = card.rect.y + 52
        for category, amount in sorted(values.items(), key=lambda item: item[1], reverse=True)[:6]:
            text(surface, category, (card.rect.x + 14, y), 10, MUTED)
            text(surface, format_money(amount), (card.rect.right - 14, y), 10, colour, bold=True, anchor="topright"); y += 22
        text(surface, "TOTAL", (card.rect.x + 14, card.rect.bottom - 24), 10, WHITE, bold=True)
        text(surface, format_money(total), (card.rect.right - 14, card.rect.bottom - 24), 11, colour, bold=True, anchor="topright")

    def _draw_chart(self, surface: pygame.Surface, card: Card) -> None:
        card.draw(surface); rect = card.content_rect.inflate(-12, -14)
        monthly = defaultdict(int)
        for row in self.ledger:
            monthly[row["date"][:7]] += row["amount"] if row["kind"] == "INCOME" else -row["amount"]
        keys = sorted(monthly)[-12:]; values = []; balance = self.team["cash"] - sum(monthly[key] for key in keys)
        for key in keys: balance += monthly[key]; values.append(balance)
        if not values: values = [self.team["cash"]]
        low, high = min(values), max(values); span = max(1, high - low)
        for i in range(4):
            yy = rect.y + int(i * rect.height / 3); pygame.draw.line(surface, BORDER, (rect.x, yy), (rect.right, yy))
        points = [(rect.x + int(i * rect.width / max(1, len(values)-1)), rect.bottom - int((value-low)*rect.height/span)) for i, value in enumerate(values)]
        if len(points)>1: pygame.draw.lines(surface, GREEN, False, points, 3)
        for point in points: pygame.draw.aacircle(surface, GOLD, point, 4)
        text(surface, "12-MONTH CASH TREND", (rect.x + 5, rect.y + 5), 9, MUTED, bold=True)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Income, expenditure, pricing, sponsorship, and end-of-season projection")
        self._draw_summary(surface)
        mid_y = self.y + 101; mid_h = 198; col_w = (int(self.w * .67) - 10) // 2
        income_card = Card(pygame.Rect(self.x, mid_y, col_w, mid_h), "INCOME BREAKDOWN")
        expense_card = Card(pygame.Rect(self.x + col_w + 10, mid_y, col_w, mid_h), "EXPENDITURE BREAKDOWN")
        self._draw_breakdown(surface, income_card, self.income, GREEN); self._draw_breakdown(surface, expense_card, self.expenses, RED)
        chart = Card(pygame.Rect(self.x, mid_y + mid_h + 10, int(self.w * .67), self.content_rect.bottom - 16 - (mid_y + mid_h + 10)), "CASH TREND")
        self._draw_chart(surface, chart)
        controls = Card(pygame.Rect(self.x + int(self.w * .67) + 10, mid_y, self.w - int(self.w * .67) - 10,
                                    self.content_rect.bottom - 16 - mid_y), "COMMERCIAL CONTROLS")
        controls.draw(surface)
        text(surface, self.sponsor["sponsor_name"] if self.sponsor else "No active sponsor", (controls.rect.x + 15, controls.rect.y + 57), 14, GOLD, bold=True)
        if self.sponsor:
            text(surface, f"{format_money(self.sponsor['monthly_value'])} / month", (controls.rect.x + 15, controls.rect.y + 82), 11, GREEN)
            text(surface, f"Expires {self.sponsor['end_date']}", (controls.rect.x + 15, controls.rect.y + 103), 10, MUTED)
        atmosphere = (self.team.get("stadium_level", 1) - 1) * .025
        attendance = int(self.team["stadium_capacity"] * max(.48, min(.99, 1.12 - (self.ticket_slider.value - 20) * .012 + atmosphere)))
        text(surface, f"Projected attendance: {attendance:,}", (controls.rect.x + 15, controls.rect.y + 139), 11, WHITE)
        text(surface, f"Projected gate: {format_money(int(attendance*self.ticket_slider.value))}", (controls.rect.x + 15, controls.rect.y + 162), 11, GREEN, bold=True)
        self.ticket_slider.draw(surface); self.sponsor_button.draw(surface); self.revenue_button.draw(surface)
        if self.context.get("toast"): text(surface, self.context.pop("toast"), (self.content_rect.right - 20, self.content_rect.y + 52), 11, GREEN, anchor="topright")
