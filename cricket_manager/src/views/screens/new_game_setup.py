"""Manager identity, mode, difficulty, and active-league setup."""
from __future__ import annotations

import pygame
import pygame_gui

from src.models.manager import Manager, VALID_BACKGROUNDS
from ui.shared_components import BaseScreen
from ui.widgets import Button, ButtonStyle, Card
from ui.widgets.common import BG, BORDER, CARD_ALT, GOLD, GREEN, MUTED, RED, WHITE, text, wrap_text


class NewGameSetupScreen(BaseScreen):
    """First new-career setup page for professional manager details."""

    title = "New Game Setup"

    def build(self) -> None:
        controller = self.context["game_controller"]
        self.countries = [country for country in controller.countries if country["domestic_leagues"]]
        prior = self.context.get("new_game_setup", {})
        prior_manager = prior.get("manager", {})
        self.mode = prior.get("mode", "Career")
        self.difficulty = prior.get("difficulty", "Normal")
        self.background = prior_manager.get("background", "Coach")
        self.nationality = prior_manager.get("nationality", "England")
        self.enabled = set(prior.get("enabled_countries", ["england", "australia", "india"]))
        self.primary_country = prior.get("primary_country", next(iter(self.enabled), None))
        self.message = ""
        self.saved = False
        self._layout()
        self.name_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=self.name_entry_rect,
            manager=self.manager,
            object_id="#setup_text_entry",
        )
        self.name_entry.set_text(prior_manager.get("name", "Alex Morgan"))
        country_names = [country["name"] for country in self.countries]
        self.nationality_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=country_names,
            starting_option=self.nationality if self.nationality in country_names else country_names[0],
            relative_rect=self.nationality_rect,
            manager=self.manager,
            object_id="#setup_dropdown",
        )

    def _layout(self) -> None:
        r = self.content_rect
        s = max(1.0, min(r.width / 1280, r.height / 720, 1.55))
        margin, gap = int(28 * s), int(14 * s)
        header_h, footer_h = int(92 * s), int(72 * s)
        body_y = r.y + header_h
        body_h = r.height - header_h - footer_h
        left_w, middle_w = int(330 * s), int(335 * s)
        right_w = r.width - margin * 2 - gap * 2 - left_w - middle_w
        self.profile_card = Card(pygame.Rect(r.x + margin, body_y, left_w, body_h), "Manager Profile", "IDENTITY")
        self.game_card = Card(pygame.Rect(self.profile_card.rect.right + gap, body_y, middle_w, body_h), "Game Setup", "MODE & DIFFICULTY")
        self.league_card = Card(pygame.Rect(self.game_card.rect.right + gap, body_y, right_w, body_h), "Starting League", "CHOOSE WHERE YOUR CAREER BEGINS")

        px = self.profile_card.content_rect.x
        pw = self.profile_card.content_rect.width
        self.name_entry_rect = pygame.Rect(px, self.profile_card.content_rect.y + int(36 * s), pw, int(38 * s))
        self.nationality_rect = pygame.Rect(px, self.profile_card.content_rect.y + int(126 * s), pw, int(38 * s))
        self.background_buttons = {}
        by = self.profile_card.content_rect.y + int(224 * s)
        bh = int(40 * s)
        for index, background in enumerate(VALID_BACKGROUNDS):
            self.background_buttons[background] = Button(
                pygame.Rect(px, by + index * (bh + int(9 * s)), pw, bh), background.upper(),
                ButtonStyle.PRIMARY, selected=background == self.background,
            )

        gx, gw = self.game_card.content_rect.x, self.game_card.content_rect.width
        self.mode_buttons = {}
        my = self.game_card.content_rect.y + int(36 * s)
        for index, mode in enumerate(("Career", "World Cup", "Tournament")):
            self.mode_buttons[mode] = Button(
                pygame.Rect(gx, my + index * int(57 * s), gw, int(45 * s)), mode.upper(),
                ButtonStyle.PRIMARY, selected=mode == self.mode,
            )
        self.difficulty_buttons = {}
        dy = self.game_card.content_rect.y + int(264 * s)
        dw = (gw - int(16 * s)) // 3
        for index, difficulty in enumerate(("Easy", "Normal", "Hard")):
            self.difficulty_buttons[difficulty] = Button(
                pygame.Rect(gx + index * (dw + int(8 * s)), dy, dw, int(42 * s)), difficulty.upper(),
                ButtonStyle.SUCCESS if difficulty == "Normal" else ButtonStyle.SECONDARY,
                selected=difficulty == self.difficulty,
            )

        lx, lw = self.league_card.content_rect.x, self.league_card.content_rect.width
        self.league_buttons = {}
        cols = 2 if lw >= 330 else 1
        bw = (lw - int(10 * s) * (cols - 1)) // cols
        bh = int(39 * s)
        for index, country in enumerate(self.countries):
            col, row = index % cols, index // cols
            label = f"{country['flag']} {country['name']}"
            self.league_buttons[country["id"]] = Button(
                pygame.Rect(lx + col * (bw + int(10 * s)), self.league_card.content_rect.y + row * int(48 * s), bw, bh),
                label, ButtonStyle.SUCCESS if country["id"] == self.primary_country else ButtonStyle.SECONDARY,
                selected=country["id"] == self.primary_country,
            )

        self.back_button = Button(pygame.Rect(r.x + margin, r.bottom - int(54 * s), int(150 * s), int(40 * s)), "BACK", ButtonStyle.SECONDARY)
        self.continue_button = Button(pygame.Rect(r.right - margin - int(220 * s), r.bottom - int(54 * s), int(220 * s), int(40 * s)), "SAVE & CONTINUE", ButtonStyle.SUCCESS)

    def process_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED and event.ui_element == self.nationality_dropdown:
            self.nationality = event.text
            self.mark_dirty()
        if self.back_button.process_event(event):
            self.navigate("Main Menu")
            return
        for name, button in self.background_buttons.items():
            if button.process_event(event):
                self.background = name
                self._sync_selection(self.background_buttons, name)
        for name, button in self.mode_buttons.items():
            if button.process_event(event):
                self.mode = name
                self._sync_selection(self.mode_buttons, name)
        for name, button in self.difficulty_buttons.items():
            if button.process_event(event):
                self.difficulty = name
                self._sync_selection(self.difficulty_buttons, name)
        for country_id, button in self.league_buttons.items():
            if button.process_event(event):
                self.primary_country = country_id
                self.enabled.add(country_id)
                for cid, candidate in self.league_buttons.items():
                    candidate.selected = cid == country_id
                    candidate.style = ButtonStyle.SUCCESS if candidate.selected else ButtonStyle.SECONDARY
                self.mark_dirty()
        if self.continue_button.process_event(event):
            try:
                draft = self.context["game_controller"].save_new_game_setup(
                    Manager(self.name_entry.get_text(), self.nationality, self.background),
                    self.mode, self.difficulty, sorted(self.enabled), self.primary_country,
                )
                self.saved = True
                self.message = f"Setup saved: {len(draft['enabled_leagues'])} competitions enabled. Team selection is next."
                self.context["game_controller"].continue_from_setup(draft)
            except ValueError as exc:
                self.saved = False
                self.message = str(exc)
            self.mark_dirty()

    def _sync_selection(self, buttons: dict[str, Button], selected: str) -> None:
        for name, button in buttons.items():
            button.selected = name == selected
        self.mark_dirty()

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, BG, self.content_rect)
        s = max(1.0, min(self.content_rect.width / 1280, self.content_rect.height / 720, 1.55))
        text(surface, "CREATE YOUR MANAGER", (self.content_rect.x + int(30 * s), self.content_rect.y + int(20 * s)), int(28 * s), WHITE, True)
        text(surface, "Build the world you want to manage. You set strategy; your players execute it.",
             (self.content_rect.x + int(31 * s), self.content_rect.y + int(57 * s)), int(14 * s), MUTED)
        for card in (self.profile_card, self.game_card, self.league_card):
            card.draw(surface)
        self._draw_profile_labels(surface, s)
        self._draw_game_copy(surface, s)
        for group in (self.background_buttons, self.mode_buttons, self.difficulty_buttons, self.league_buttons):
            for button in group.values():
                button.draw(surface)
        self._draw_league_detail(surface, s)
        self.back_button.draw(surface)
        self.continue_button.draw(surface)
        if self.message:
            colour = GREEN if self.saved else RED
            text(surface, self.message, (self.content_rect.centerx, self.content_rect.bottom - int(35 * s)),
                 int(13 * s), colour, True, anchor="center")

    def _draw_profile_labels(self, surface: pygame.Surface, scale: float) -> None:
        x, y = self.profile_card.content_rect.x, self.profile_card.content_rect.y
        text(surface, "MANAGER NAME", (x, y), int(12 * scale), MUTED, True)
        text(surface, "NATIONALITY", (x, y + int(90 * scale)), int(12 * scale), MUTED, True)
        text(surface, "PROFESSIONAL BACKGROUND", (x, y + int(188 * scale)), int(12 * scale), MUTED, True)
        text(surface, "Background provides narrative context for your management career.",
             (x, self.profile_card.content_rect.bottom - int(48 * scale)), int(11 * scale), MUTED)

    def _draw_game_copy(self, surface: pygame.Surface, scale: float) -> None:
        x, y = self.game_card.content_rect.x, self.game_card.content_rect.y
        text(surface, "GAME MODE", (x, y), int(12 * scale), MUTED, True)
        text(surface, "DIFFICULTY", (x, y + int(228 * scale)), int(12 * scale), MUTED, True)
        descriptions = {
            "Career": "Manage a domestic club and build a long-term career.",
            "World Cup": "Choose a qualified nation for a focused global campaign.",
            "Tournament": "Configure a custom competition and invited teams.",
        }
        yy = y + int(339 * scale)
        pygame.draw.line(surface, BORDER, (x, yy - int(12 * scale)), (self.game_card.content_rect.right, yy - int(12 * scale)))
        for line in wrap_text(descriptions[self.mode], self.game_card.content_rect.width, int(13 * scale)):
            text(surface, line, (x, yy), int(13 * scale), GOLD)
            yy += int(21 * scale)

    def _draw_league_detail(self, surface: pygame.Surface, scale: float) -> None:
        country = next((item for item in self.countries if item["id"] == self.primary_country), None)
        if not country:
            return
        leagues = [league for league in self.context["game_controller"].leagues if league["country"] == country["id"]]
        x = self.league_card.content_rect.x
        y = self.league_card.content_rect.bottom - int(142 * scale)
        pygame.draw.line(surface, BORDER, (x, y - 10), (self.league_card.content_rect.right, y - 10))
        text(surface, f"{country['name'].upper()} CAREER", (x, y), int(13 * scale), GOLD, True)
        text(surface, f"{len(leagues)} competitions  •  {max((l['teams'] for l in leagues), default=0)} clubs in the largest competition",
             (x, y + int(25 * scale)), int(11 * scale), WHITE)
        reputation = "Elite" if country["id"] in {"england", "india", "australia"} else "Established"
        prize = "High" if reputation == "Elite" else "Competitive"
        text(surface, f"Reputation: {reputation}   •   Prize money: {prize}", (x, y + int(48 * scale)), int(11 * scale), GREEN)
        names = "  •  ".join(league["name"] for league in leagues[:3])
        for index, line in enumerate(wrap_text(names, self.league_card.content_rect.width, int(10 * scale))[:2]):
            text(surface, line, (x, y + int((74 + index * 18) * scale)), int(10 * scale), MUTED)

    def kill(self) -> None:
        self.name_entry.kill()
        self.nationality_dropdown.kill()
        super().kill()
