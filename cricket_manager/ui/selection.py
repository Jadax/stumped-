"""Interactive XI selection, batting order, roles, conditions, and tactics."""
from __future__ import annotations
import pygame
from database import (fetch_player_form, fetch_player_match_events,
                      fetch_player_records, save_game)
from .shared_components import BaseScreen
from .widgets import Button, ButtonStyle, Card, DataTable, PitchDisplay, Slider, WeatherDisplay
from .widgets.datatable import Column
from .widgets.common import CARD, CARD_ALT, GOLD, GREEN, MUTED, RED, WHITE, text, clipped_text
from .player_modals import PlayerComparisonModal, PlayerDetailModal


class SelectionScreen(BaseScreen):
    title = "Selection"
    PRESETS = ["Balanced", "Batting Heavy", "Bowling Heavy", "Aggressive", "Defensive"]
    BATTING_STYLES = ["Silly", "Blitz", "Build", "Rotate"]

    def build(self) -> None:
        self.players = self.context["players"]
        saved = self.context.get("selection", {})
        ids = saved.get("xi", [])
        self.xi = [next((p for p in self.players if p["id"] == pid), None) for pid in ids]
        self.xi = [p for p in self.xi if p]
        self.bowler_ids = set(saved.get("bowlers", [])); self.captain_id = saved.get("captain")
        self.keeper_id = saved.get("keeper"); self.preset_index = 0
        self.compare_ids: list[int] = []; self.modal = None
        self.batting_styles = {int(pid): style for pid, style in saved.get("batting_styles", {}).items()}
        self.batting_aggression = {int(pid): int(value) for pid, value in saved.get("batting_aggression", {}).items()}
        self.bowling_aggression = {int(pid): int(value) for pid, value in saved.get("bowling_aggression", {}).items()}
        self.default_style_index = self.BATTING_STYLES.index(saved.get("default_batting_style", "Build")) if saved.get("default_batting_style", "Build") in self.BATTING_STYLES else 2
        x, y, w = self.content_rect.x + 18, self.content_rect.y + 112, self.content_rect.width - 36
        self.left_w, self.mid_w, gap = int(w * .40), int(w * .35), 10
        self.right_x = x + self.left_w + self.mid_w + gap * 2
        self.table = DataTable(pygame.Rect(x, y, self.left_w, self.content_rect.bottom - y - 62),
                               [Column("name", "Squad", .34), Column("role", "Role", .20), Column("overall", "OVR", .09),
                                Column("form", "Form", .10), Column("fitness", "Fit", .13), Column("morale", "Mor", .14)],
                               [dict(p, fitness=p.get("physical",{}).get("fitness",p["mental"].get("fitness",50)), morale=p["mental"].get("morale",50)) for p in self.players], 31, colour_func=self._row_colour)
        bottom = self.content_rect.bottom - 44
        half = (self.left_w - 6) // 2
        self.auto_button = Button(pygame.Rect(x, bottom, half, 32), "AUTO-SELECT XI", ButtonStyle.SUCCESS)
        self.compare_button = Button(pygame.Rect(x + half + 6, bottom, self.left_w - half - 6, 32),
                                     "COMPARE LAST 2", ButtonStyle.SECONDARY, enabled=False)
        self.captain_button = Button(pygame.Rect(self.right_x, y + 225, w - self.left_w - self.mid_w - gap * 2, 29), "CAPTAIN: NOT SET")
        self.keeper_button = Button(pygame.Rect(self.right_x, y + 258, self.captain_button.rect.width, 29), "KEEPER: NOT SET")
        self.style_button = Button(pygame.Rect(self.right_x, y + 291, self.captain_button.rect.width, 29),
                                   f"DEFAULT STYLE: {self.BATTING_STYLES[self.default_style_index].upper()}", ButtonStyle.SUCCESS)
        self.preset_button = Button(pygame.Rect(self.right_x, y + 324, self.captain_button.rect.width, 29), "PRESET: BALANCED", ButtonStyle.PRIMARY)
        self.sliders = [Slider(pygame.Rect(self.right_x, y + 359 + i * 40, self.captain_button.rect.width, 38), label, 1, 10, 5)
                        for i, label in enumerate(("Batting aggression", "Bowling aggression", "Fielding aggression"))]
        self.confirm_button = Button(pygame.Rect(self.right_x, bottom, self.captain_button.rect.width, 32), "CONFIRM SELECTION", ButtonStyle.PRIMARY)

    def _row_colour(self, key, _value, row):
        if key == "name" and any(p["id"] == row["id"] for p in self.xi): return GREEN
        return None

    def _profile(self, player: dict) -> dict:
        profile = dict(player)
        profile["records"] = fetch_player_records(player["id"], self.context["database_path"])
        profile["form_history"] = fetch_player_form(player["id"], self.context["database_path"])
        profile["match_events"] = fetch_player_match_events(player["id"], self.context["database_path"])
        return profile

    def auto_select(self) -> None:
        def condition_score(player: dict) -> float:
            physical = player.get("physical", {})
            fitness = physical.get("fitness", player["mental"].get("fitness", 50))
            score = player["overall"] * .66 + player.get("form", 50) * .17
            score += fitness * .10 + player["mental"].get("morale", 50) * .07
            # The displayed green/overcast report rewards seam options while
            # still respecting current form and availability.
            if player["role"] in {"Bowler", "All-Rounder"}:
                score += player["bowling"].get("pace", 50) * .05
                score += player["bowling"].get("swing_or_spin", 50) * .04
            return score

        keepers = sorted((p for p in self.players if p["role"] == "Wicketkeeper"), key=condition_score, reverse=True)
        chosen = keepers[:1]
        chosen += [p for p in sorted(self.players, key=condition_score, reverse=True) if p not in chosen][:10]
        self.xi = chosen
        bowlers = [p for p in self.xi if p["role"] in ("Bowler", "All-Rounder")]
        bowlers.sort(key=lambda p: sum(p["bowling"].values()), reverse=True)
        if len(bowlers) < 5:
            bowlers += [p for p in self.xi if p not in bowlers]
        self.bowler_ids = {p["id"] for p in bowlers[:5]}
        for player in self.xi:
            if player["role"] == "Batsman" and player["batting"]["attack"] >= 75: style = "Blitz"
            elif player["role"] == "Bowler": style = "Rotate"
            else: style = "Build"
            self.batting_styles[player["id"]] = style
            self.batting_aggression[player["id"]] = 7 if style == "Blitz" else 4 if style == "Rotate" else 5
            self.bowling_aggression[player["id"]] = 6 if player["role"] in {"Bowler", "All-Rounder"} else 4
        self.keeper_id = chosen[0]["id"]
        self.captain_id = max(self.xi, key=lambda p: p["mental"]["experience"])["id"]
        self._update_role_buttons()

    def _update_role_buttons(self) -> None:
        def named(pid):
            player = next((p for p in self.xi if p["id"] == pid), None); return player["name"] if player else "NOT SET"
        self.captain_button.label = f"CAPTAIN: {named(self.captain_id)}"
        self.keeper_button.label = f"KEEPER: {named(self.keeper_id)}"

    def _cycle_role(self, current: int | None, keepers_only: bool = False) -> int | None:
        options = [p for p in self.xi if not keepers_only or p["role"] == "Wicketkeeper"]
        if not options: return None
        ids = [p["id"] for p in options]
        return ids[0] if current not in ids else ids[(ids.index(current) + 1) % len(ids)]

    def warnings(self) -> list[str]:
        warnings = []
        if len(self.xi) != 11: warnings.append(f"Need 11 players ({len(self.xi)} selected)")
        if self.keeper_id not in {p["id"] for p in self.xi}: warnings.append("No wicketkeeper!")
        if len(self.bowler_ids & {p["id"] for p in self.xi}) != 5: warnings.append(f"Only {len(self.bowler_ids)} bowlers designated!")
        if self.captain_id not in {p["id"] for p in self.xi}: warnings.append("Captain missing!")
        return warnings

    def process_event(self, event: pygame.event.Event) -> None:
        if self.modal:
            if self.modal.process_event(event): self.modal = None
            return
        selected = self.table.process_event(event)
        if selected:
            self.compare_ids = [pid for pid in self.compare_ids if pid != selected["id"]] + [selected["id"]]
            self.compare_ids = self.compare_ids[-2:]
            self.compare_button.enabled = len(self.compare_ids) == 2
            existing = next((p for p in self.xi if p["id"] == selected["id"]), None)
            if existing:
                self.xi.remove(existing); self.bowler_ids.discard(existing["id"])
                if self.captain_id == existing["id"]: self.captain_id = None
                if self.keeper_id == existing["id"]: self.keeper_id = None
            elif len(self.xi) < 11: self.xi.append(selected)
            self._update_role_buttons()
        if self.auto_button.process_event(event): self.auto_select()
        if self.compare_button.process_event(event) and len(self.compare_ids) == 2:
            players = [next(p for p in self.players if p["id"] == pid) for pid in self.compare_ids]
            self.modal = PlayerComparisonModal(self.content_rect, players[0], players[1])
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            index = self.table._row_at(event.pos)
            if index is not None:
                row = self.table.rows[index]
                player = next((p for p in self.players if p["id"] == row["id"]), row)
                self.modal = PlayerDetailModal(self.content_rect, self._profile(player))
        if self.captain_button.process_event(event): self.captain_id = self._cycle_role(self.captain_id); self._update_role_buttons()
        if self.keeper_button.process_event(event): self.keeper_id = self._cycle_role(self.keeper_id, True); self._update_role_buttons()
        if self.preset_button.process_event(event):
            self.preset_index = (self.preset_index + 1) % len(self.PRESETS); self.preset_button.label = f"PRESET: {self.PRESETS[self.preset_index].upper()}"
        if self.style_button.process_event(event):
            self.default_style_index = (self.default_style_index + 1) % len(self.BATTING_STYLES)
            style = self.BATTING_STYLES[self.default_style_index]
            self.style_button.label = f"DEFAULT STYLE: {style.upper()}"
            for player in self.xi:
                self.batting_styles[player["id"]] = style
                self.batting_aggression[player["id"]] = {"Silly": 10, "Blitz": 8, "Build": 5, "Rotate": 3}[style]
        for slider in self.sliders: slider.process_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mid_x = self.content_rect.x + 18 + self.left_w + 10
            start_y = self.content_rect.y + 157
            for i, player in enumerate(self.xi):
                row = pygame.Rect(mid_x, start_y + i * 33, self.mid_w, 29)
                if row.collidepoint(event.pos):
                    if event.pos[0] > row.right - 55:
                        if player["id"] in self.bowler_ids: self.bowler_ids.remove(player["id"])
                        elif len(self.bowler_ids) < 5: self.bowler_ids.add(player["id"])
                    elif event.pos[0] > row.right - 88:
                        self.bowling_aggression[player["id"]] = self.bowling_aggression.get(player["id"], 5) % 10 + 1
                    elif event.pos[0] > row.right - 121:
                        self.batting_aggression[player["id"]] = self.batting_aggression.get(player["id"], 5) % 10 + 1
                    elif event.pos[0] > row.right - 164:
                        current = self.batting_styles.get(player["id"], "Build")
                        self.batting_styles[player["id"]] = self.BATTING_STYLES[(self.BATTING_STYLES.index(current) + 1) % len(self.BATTING_STYLES)]
                    elif event.pos[0] > row.right - 188 and i < len(self.xi) - 1: self.xi[i], self.xi[i + 1] = self.xi[i + 1], self.xi[i]
                    elif event.pos[0] > row.right - 212 and i > 0: self.xi[i], self.xi[i - 1] = self.xi[i - 1], self.xi[i]
        self.confirm_button.enabled = not self.warnings()
        if self.confirm_button.process_event(event):
            self.context["selection"] = {"xi": [p["id"] for p in self.xi], "bowlers": list(self.bowler_ids),
                "captain": self.captain_id, "keeper": self.keeper_id, "preset": self.PRESETS[self.preset_index],
                "aggression": [s.value for s in self.sliders], "default_batting_style": self.BATTING_STYLES[self.default_style_index],
                "batting_styles": self.batting_styles, "batting_aggression": self.batting_aggression,
                "bowling_aggression": self.bowling_aggression}
            save_game({"selection": self.context["selection"]}, self.context["database_path"])
            if self.navigate: self.navigate("Pre-Match")

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Choose eleven • order the batting • assign five bowlers and leadership")
        x, y = self.content_rect.x + 18, self.content_rect.y + 76
        left = Card(pygame.Rect(x, y, self.left_w, self.content_rect.height - 90), "AVAILABLE SQUAD", f"{len(self.xi)}/11 SELECTED")
        mid = Card(pygame.Rect(x + self.left_w + 10, y, self.mid_w, self.content_rect.height - 90), "BATTING ORDER", "↑ ↓ / STYLE / BOWL")
        right = Card(pygame.Rect(self.right_x, y, self.content_rect.right - 18 - self.right_x, self.content_rect.height - 90),
                     "MATCH PLAN", "PACE FAVOURED")
        for card in (left, mid, right): card.draw(surface)
        self.table.draw(surface); self.auto_button.draw(surface); self.compare_button.draw(surface)
        start_y = self.content_rect.y + 157
        for i in range(11):
            row = pygame.Rect(mid.rect.x + 12, start_y + i * 33, mid.rect.width - 24, 29)
            pygame.draw.rect(surface, CARD_ALT if i % 2 else CARD, row)
            text(surface, i + 1, (row.x + 8, row.y + 7), 12, GOLD, bold=True)
            if i < len(self.xi):
                p = self.xi[i]; text(surface, clipped_text(p["name"], row.width - 225, 12), (row.x + 32, row.y + 7), 12)
                text(surface, "↑", (row.right - 207, row.y + 5), 15, MUTED); text(surface, "↓", (row.right - 183, row.y + 5), 15, MUTED)
                text(surface, self.batting_styles.get(p["id"], "Build")[:3].upper(), (row.right - 128, row.y + 7), 9, GOLD, bold=True, anchor="topright")
                text(surface, f"A{self.batting_aggression.get(p['id'], 5)}", (row.right - 91, row.y + 7), 9, WHITE, bold=True, anchor="topright")
                text(surface, f"B{self.bowling_aggression.get(p['id'], 5)}", (row.right - 59, row.y + 7), 9, GREEN, bold=True, anchor="topright")
                colour = GREEN if p["id"] in self.bowler_ids else MUTED
                text(surface, "BOWL", (row.right - 8, row.y + 7), 11, colour, bold=True, anchor="topright")
        rx = right.rect.x + 15
        PitchDisplay(pygame.Rect(rx, right.rect.y + 50, right.rect.width - 30, 42), "Green", 4).draw(surface)
        WeatherDisplay(pygame.Rect(rx, right.rect.y + 100, right.rect.width - 30, 62), "Overcast",
                       ["Overcast", "Cloudy", "Overcast", "Rain Threat", "Cloudy", "Sunny"]).draw(surface)
        warnings = self.warnings()
        text(surface, "SELECTION STATUS", (rx, right.rect.y + 173), 11, MUTED, bold=True)
        if warnings:
            for i, warning in enumerate(warnings[:3]): text(surface, f"! {warning}", (rx, right.rect.y + 195 + i * 20), 11, RED)
        else: text(surface, "✓ XI ready to confirm", (rx, right.rect.y + 195), 12, GREEN, bold=True)
        self.captain_button.draw(surface); self.keeper_button.draw(surface); self.style_button.draw(surface); self.preset_button.draw(surface)
        for slider in self.sliders: slider.draw(surface)
        self.confirm_button.enabled = not warnings; self.confirm_button.draw(surface)
        if self.modal: self.modal.draw(surface)
