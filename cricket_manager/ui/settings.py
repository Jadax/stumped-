"""Persistent game speed, audio, display, and autosave configuration."""
from __future__ import annotations
import pygame
from database import update_user_settings
from src.models.currency import CURRENCIES, currency_options, set_active_currency
from .shared_components import BaseScreen
from .widgets import Button, ButtonStyle, Card, Slider
from .widgets.common import GOLD, GREEN, MUTED, WHITE, text


class SettingsScreen(BaseScreen):
    title = "Settings"
    SPEEDS = ["Normal", "Fast", "Instant"]
    RESOLUTIONS = ["1280x720", "1600x900", "1920x1080", "Fullscreen"]
    AUTOSAVES = ["Never", "Monthly", "Seasonal"]
    CURRENCY_CODES = currency_options()

    def build(self) -> None:
        user = self.context.get("user_settings", {})
        self.speed = user.get("game_speed", "Normal")
        self.sound = bool(user.get("sound_on", 1))
        self.volume = int(user.get("master_volume", 70))
        self.resolution = user.get("resolution", "1280x720")
        self.autosave = user.get("auto_save_frequency", "Monthly")
        self.currency = user.get("currency", "GBP")
        self.reduced_motion = bool(user.get("reduced_motion", 0))
        self.colour_blind = bool(user.get("colour_blind_mode", 1))
        self.ui_scale = float(user.get("ui_scale", 1.0) or 1.0)
        x, y, w = self.content_rect.x + 18, self.content_rect.y + 82, self.content_rect.width - 36
        self.card = pygame.Rect(x, y, w, self.content_rect.height - 108)
        bx, bw = self.card.right - 300, 250
        ys = [self.card.y + 52 + index * 54 for index in range(9)]
        self.speed_button = Button(pygame.Rect(bx, ys[0], bw, 34), f"GAME SPEED: {self.speed.upper()}", ButtonStyle.PRIMARY)
        self.sound_button = Button(pygame.Rect(bx, ys[1], bw, 34), f"SOUND: {'ON' if self.sound else 'OFF'}", ButtonStyle.SECONDARY)
        self.volume_slider = Slider(pygame.Rect(bx, ys[2] - 4, bw, 40), "MASTER VOLUME", 0, 100, self.volume, 5,
                                    lambda value: f"{int(value)}%")
        self.resolution_button = Button(pygame.Rect(bx, ys[3], bw, 34), f"DISPLAY: {self.resolution.upper()}", ButtonStyle.SECONDARY)
        self.currency_button = Button(pygame.Rect(bx, ys[4], bw, 34), f"CURRENCY: {self.currency}", ButtonStyle.SUCCESS)
        self.autosave_button = Button(pygame.Rect(bx, ys[5], bw, 34), f"AUTOSAVE: {self.autosave.upper()}", ButtonStyle.SUCCESS)
        self.motion_button = Button(pygame.Rect(bx, ys[6], bw, 34),
                                    f"REDUCED MOTION: {'ON' if self.reduced_motion else 'OFF'}", ButtonStyle.SECONDARY)
        self.colour_blind_button = Button(pygame.Rect(bx, ys[7], bw, 34),
                                          f"COLOUR-BLIND GLYPHS: {'ON' if self.colour_blind else 'OFF'}", ButtonStyle.SECONDARY)
        self.scale_button = Button(pygame.Rect(bx, ys[8], bw, 34),
                                   f"UI SCALE: {int(self.ui_scale * 100)}%", ButtonStyle.SECONDARY)
        self.save_button = Button(pygame.Rect(bx, self.card.bottom - 57, bw, 34), "SAVE SETTINGS", ButtonStyle.SUCCESS)

    @staticmethod
    def _next(current, options): return options[(options.index(current) + 1) % len(options)] if current in options else options[0]

    def process_event(self, event: pygame.event.Event) -> None:
        if self.speed_button.process_event(event):
            self.speed = self._next(self.speed, self.SPEEDS); self.speed_button.label = f"GAME SPEED: {self.speed.upper()}"
        if self.sound_button.process_event(event):
            self.sound = not self.sound; self.sound_button.label = f"SOUND: {'ON' if self.sound else 'OFF'}"
            audio = self.context.get("audio_manager")
            if audio:
                audio.set_muted(not self.sound)
        if self.volume_slider.process_event(event):
            self.volume = int(self.volume_slider.value)
            audio = self.context.get("audio_manager")
            if audio: audio.set_volume(self.volume)
        if self.resolution_button.process_event(event):
            self.resolution = self._next(self.resolution, self.RESOLUTIONS); self.resolution_button.label = f"DISPLAY: {self.resolution.upper()}"
        if self.autosave_button.process_event(event):
            self.autosave = self._next(self.autosave, self.AUTOSAVES); self.autosave_button.label = f"AUTOSAVE: {self.autosave.upper()}"
        if self.currency_button.process_event(event):
            self.currency = self._next(self.currency, self.CURRENCY_CODES)
            self.currency_button.label = f"CURRENCY: {self.currency}"
        from src.views.theme import PREFS, set_ui_scale
        if self.motion_button.process_event(event):
            self.reduced_motion = not self.reduced_motion
            self.motion_button.label = f"REDUCED MOTION: {'ON' if self.reduced_motion else 'OFF'}"
            PREFS["reduced_motion"] = self.reduced_motion
        if self.colour_blind_button.process_event(event):
            self.colour_blind = not self.colour_blind
            self.colour_blind_button.label = f"COLOUR-BLIND GLYPHS: {'ON' if self.colour_blind else 'OFF'}"
            PREFS["colour_blind"] = self.colour_blind
        if self.scale_button.process_event(event):
            self.ui_scale = {1.0: 1.1, 1.1: 1.2, 1.2: 1.0}.get(round(self.ui_scale, 1), 1.0)
            self.scale_button.label = f"UI SCALE: {int(self.ui_scale * 100)}%"
            set_ui_scale(self.ui_scale)
        if self.save_button.process_event(event):
            values = {"game_speed": self.speed, "sound_on": int(self.sound), "master_volume": self.volume,
                      "resolution": self.resolution, "currency": self.currency,
                      "auto_save_frequency": self.autosave,
                      "reduced_motion": int(self.reduced_motion),
                      "colour_blind_mode": int(self.colour_blind), "ui_scale": self.ui_scale}
            update_user_settings(values, self.context["database_path"]); self.context["user_settings"].update(values)
            set_active_currency(self.currency)
            self.context["toast"] = "Settings saved"
            callback = self.context.get("apply_resolution")
            if callback: callback(self.resolution)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Configure simulation pacing, match crowd effects, display mode, and campaign saves")
        Card(self.card, "GAME PREFERENCES", "PERSISTED TO SAVE DATABASE").draw(surface)
        x, y = self.card.x + 42, self.card.y + 52
        rows = [("Game Speed", "Controls the delay between simulated deliveries and calendar events."),
                ("Crowd Sound", "Mutes or enables optional match-day crowd effects."),
                ("Crowd Volume", "Controls match effects from 0% to 100%. No background music is used."),
                ("Resolution", "Windowed resolutions or borderless fullscreen. Minimum 1280×720."),
                ("Currency", f"Display club finances in {CURRENCIES[self.currency]['name']}. Save values stay stable."),
                ("Auto-save", "Never, after every simulated month, or at the end of each season."),
                ("Reduced Motion", "Disables flashes and hover growth for a calmer interface."),
                ("Colour-blind Glyphs", "Always pairs colours with glyphs on beads and status displays."),
                ("UI Scale", "Enlarges all interface text: 100%, 110%, or 120%.")]
        for label, description in rows:
            text(surface, label, (x, y), 13, WHITE, bold=True); text(surface, description, (x, y + 19), 10, MUTED); y += 54
        for button in (self.speed_button, self.sound_button, self.resolution_button, self.currency_button,
                       self.autosave_button, self.motion_button, self.colour_blind_button, self.scale_button,
                       self.save_button): button.draw(surface)
        self.volume_slider.draw(surface)
        text(surface, "F11 toggles fullscreen • Escape returns to windowed mode or exits", (self.card.x + 42, self.card.bottom - 45), 11, GOLD)
        if self.context.get("toast"): text(surface, self.context.pop("toast"), (self.content_rect.right - 20, self.content_rect.y + 54), 11, GREEN, anchor="topright")
