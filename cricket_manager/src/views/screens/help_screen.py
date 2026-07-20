"""Searchable, scrollable in-game manual for cricket managers."""
from __future__ import annotations

import json
from pathlib import Path
import pygame

from src.utilities.graphics import draw_cricket_icon
from ui.shared_components import BaseScreen
from ui.widgets import Button, ButtonStyle, Card
from ui.widgets.common import (ACCENT, BG, BORDER, CARD, CARD_ALT, GOLD, GREEN,
                               MUTED, PANEL, WHITE, clipped_text, text, wrap_text)


class HelpScreen(BaseScreen):
    title = "Help & Guide"

    def build(self) -> None:
        data_root = Path(__file__).resolve().parents[2] / "data"
        self.sections = json.loads((data_root / "help_content.json").read_text(encoding="utf-8"))["sections"]
        faq = json.loads((data_root / "match_engine_faq.json").read_text(encoding="utf-8"))
        self.sections.append({"id": "engine_faq", "title": "Engine FAQ",
                              "articles": [{"title": item["question"], "body": item["answer"]}
                                           for item in faq["questions"]]})
        self.active = self.expanded = 0
        self.search, self.search_active, self.scroll = "", False, 0
        self._layout()

    def _layout(self) -> None:
        r = self.content_rect; margin, gap = 24, 14
        top = r.y + 88; bottom = r.bottom - 62
        nav_w = min(265, max(220, int(r.width * .22)))
        self.nav_card = Card(pygame.Rect(r.x + margin, top, nav_w, bottom - top), "Guide", "TOPICS")
        self.article_card = Card(pygame.Rect(self.nav_card.rect.right + gap, top,
                                             r.right - margin - self.nav_card.rect.right - gap,
                                             bottom - top), "", "")
        self.search_rect = pygame.Rect(r.x + 285, r.y + 26, min(390, r.width - 540), 38)
        self.topic_buttons = []
        y = self.nav_card.content_rect.y
        for index, section in enumerate(self.sections):
            self.topic_buttons.append(Button(
                pygame.Rect(self.nav_card.content_rect.x, y, self.nav_card.content_rect.width, 34),
                clipped_text(section["title"], self.nav_card.content_rect.width - 24, 12).upper(),
                ButtonStyle.PRIMARY if index == 0 else ButtonStyle.SECONDARY, selected=index == 0))
            y += 39
        self.back_button = Button(pygame.Rect(r.x + margin, r.bottom - 49, 140, 34), "BACK TO GAME", ButtonStyle.SECONDARY)

    def _articles(self) -> list[dict]:
        articles = self.sections[self.active]["articles"]
        query = self.search.strip().lower()
        if not query:
            return articles
        return [article for article in articles if query in article["title"].lower() or query in article["body"].lower()]

    def process_event(self, event: pygame.event.Event) -> None:
        if self.back_button.process_event(event):
            self.navigate(self.context.pop("help_return", "Dashboard")); return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.search_active = self.search_rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.search_active:
            if event.key == pygame.K_BACKSPACE: self.search = self.search[:-1]
            elif event.key == pygame.K_ESCAPE: self.search_active = False
            elif event.unicode and event.unicode.isprintable() and len(self.search) < 48: self.search += event.unicode
            self.expanded = 0; self.scroll = 0; self.mark_dirty()
        for index, button in enumerate(self.topic_buttons):
            if button.process_event(event):
                self.active, self.expanded, self.scroll = index, 0, 0
                for i, other in enumerate(self.topic_buttons): other.selected = i == index
                self.mark_dirty(); return
        if event.type == pygame.MOUSEWHEEL and self.article_card.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, self.scroll - event.y * 38); self.mark_dirty()
        y = self.article_card.content_rect.y + 62 - self.scroll
        for index, article in enumerate(self._articles()):
            header = pygame.Rect(self.article_card.content_rect.x, y, self.article_card.content_rect.width, 38)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and header.collidepoint(event.pos):
                self.expanded = index if self.expanded != index else -1; self.mark_dirty(); return
            y += 46
            if index == self.expanded:
                y += len(wrap_text(article["body"], self.article_card.content_rect.width - 32, 14)) * 22 + 22

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, BG, self.content_rect)
        text(surface, "HELP & GUIDE", (self.content_rect.x + 26, self.content_rect.y + 20), 28, WHITE, True)
        pygame.draw.rect(surface, PANEL, self.search_rect, border_radius=4)
        pygame.draw.rect(surface, ACCENT if self.search_active else BORDER, self.search_rect, 1, border_radius=4)
        text(surface, self.search or "Search rules, tactics, finance…", (self.search_rect.x + 12, self.search_rect.y + 10),
             13, WHITE if self.search else MUTED)
        self.nav_card.draw(surface); self.article_card.draw(surface)
        for button in self.topic_buttons: button.draw(surface)
        self.back_button.draw(surface)
        section, articles = self.sections[self.active], self._articles(); c = self.article_card.content_rect
        draw_cricket_icon(surface, "stumps", pygame.Rect(c.x, c.y - 2, 42, 42), GOLD)
        text(surface, section["title"], (c.x + 55, c.y + 2), 24, WHITE, True)
        text(surface, f"{len(articles)} ARTICLES", (c.right, c.y + 8), 11, ACCENT, True, anchor="topright")
        clip = surface.get_clip(); surface.set_clip(pygame.Rect(c.x, c.y + 54, c.width, c.height - 54))
        y = c.y + 62 - self.scroll
        for index, article in enumerate(articles):
            header = pygame.Rect(c.x, y, c.width, 38)
            pygame.draw.rect(surface, CARD.lerp(GREEN, .18) if index == self.expanded else CARD_ALT, header, border_radius=4)
            pygame.draw.rect(surface, GREEN if index == self.expanded else BORDER, header, 1, border_radius=4)
            text(surface, clipped_text(article["title"], header.width - 55, 14, True), (header.x + 14, header.y + 10), 14, WHITE, True)
            text(surface, "−" if index == self.expanded else "+", (header.right - 16, header.y + 7), 18, GOLD, True, anchor="topright")
            y += 46
            if index == self.expanded:
                for line in wrap_text(article["body"], c.width - 32, 14):
                    text(surface, line, (c.x + 16, y), 14, WHITE); y += 22
                y += 22
        surface.set_clip(clip)
        content_height = max(0, y - (c.y + 62 - self.scroll))
        self.scroll = min(self.scroll, max(0, content_height - (c.height - 60)))
