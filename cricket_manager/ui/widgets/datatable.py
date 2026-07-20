"""Sortable, scrollable data table with striped rows and row selection."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
import pygame
from .common import BORDER, CARD, CARD_ALT, DIM, GOLD, GREEN, MUTED, PANEL, WHITE, clipped_text, text


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    width: float
    align: str = "left"
    formatter: Callable[[Any], str] | None = None


class DataTable:
    def __init__(self, rect: pygame.Rect, columns: list[Column | tuple], rows: list[dict[str, Any]],
                 row_height: int = 34, highlight_key: str | None = None, highlight_value: Any = None,
                 colour_func: Callable[[str, Any, dict], pygame.Color | None] | None = None):
        self.rect = pygame.Rect(rect)
        self.columns = [c if isinstance(c, Column) else Column(*c) for c in columns]
        self.rows, self.row_height = list(rows), row_height
        self.highlight_key, self.highlight_value = highlight_key, highlight_value
        self.colour_func = colour_func
        self.header_height, self.scroll = 36, 0
        self.sort_key, self.sort_reverse = None, False
        self.hovered_row, self.selected_row = None, None
        self.dragging_scrollbar = False

    @property
    def visible_count(self) -> int:
        return max(1, (self.rect.height - self.header_height) // self.row_height)

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        self.rows, self.scroll = list(rows), 0
        if self.sort_key:
            self._sort(self.sort_key, preserve_direction=True)

    def _column_rects(self) -> list[pygame.Rect]:
        total = sum(c.width for c in self.columns)
        x, result = self.rect.x, []
        for i, column in enumerate(self.columns):
            width = self.rect.width - (x - self.rect.x) if i == len(self.columns) - 1 else int(self.rect.width * column.width / total)
            result.append(pygame.Rect(x, self.rect.y, width, self.header_height)); x += width
        return result

    def _sort(self, key: str, preserve_direction: bool = False) -> None:
        if not preserve_direction:
            self.sort_reverse = not self.sort_reverse if self.sort_key == key else False
        self.sort_key = key
        self.rows.sort(key=lambda r: (r.get(key) is None, str(r.get(key, "")).lower()) if isinstance(r.get(key), str)
                       else (r.get(key) is None, r.get(key, 0)), reverse=self.sort_reverse)

    def process_event(self, event: pygame.event.Event) -> dict[str, Any] | None:
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            maximum = max(0, len(self.rows) - self.visible_count)
            self.scroll = max(0, min(maximum, self.scroll - event.y * 3))
        if event.type == pygame.MOUSEMOTION:
            self.hovered_row = self._row_at(event.pos)
            if self.dragging_scrollbar: self._scroll_from_y(event.pos[1])
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_scrollbar = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            if len(self.rows) > self.visible_count and self._scroll_track().inflate(8, 0).collidepoint(event.pos):
                self.dragging_scrollbar = True; self._scroll_from_y(event.pos[1]); return None
            if event.pos[1] < self.rect.y + self.header_height:
                for column, rect in zip(self.columns, self._column_rects()):
                    if rect.collidepoint(event.pos):
                        self._sort(column.key); return None
            index = self._row_at(event.pos)
            if index is not None:
                self.selected_row = index
                return self.rows[index]
        return None

    def _scroll_track(self) -> pygame.Rect:
        return pygame.Rect(self.rect.right - 5, self.rect.y + self.header_height + 2, 3,
                           self.rect.height - self.header_height - 4)

    def _scroll_from_y(self, y: int) -> None:
        maximum = max(0, len(self.rows) - self.visible_count)
        if not maximum: return
        track = self._scroll_track(); fraction = max(0, min(1, (y - track.y) / max(1, track.height)))
        self.scroll = round(fraction * maximum)

    def _row_at(self, pos: tuple[int, int]) -> int | None:
        if not self.rect.collidepoint(pos) or pos[1] < self.rect.y + self.header_height:
            return None
        index = self.scroll + (pos[1] - self.rect.y - self.header_height) // self.row_height
        return index if 0 <= index < len(self.rows) and index < self.scroll + self.visible_count else None

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, CARD, self.rect)
        pygame.draw.rect(surface, BORDER, self.rect, width=1)
        column_rects = self._column_rects()
        for column, rect in zip(self.columns, column_rects):
            pygame.draw.rect(surface, PANEL, rect)
            indicator = " ▲" if self.sort_key == column.key and not self.sort_reverse else " ▼" if self.sort_key == column.key else ""
            text(surface, column.label.upper() + indicator, (rect.x + 8, rect.y + 11), 11, MUTED, bold=True)
            pygame.draw.line(surface, BORDER, (rect.right - 1, rect.y + 6), (rect.right - 1, rect.bottom - 6))
        clip_before = surface.get_clip(); surface.set_clip(self.rect)
        visible = self.rows[self.scroll:self.scroll + self.visible_count]
        for local_index, row in enumerate(visible):
            absolute_index = self.scroll + local_index
            row_rect = pygame.Rect(self.rect.x, self.rect.y + self.header_height + local_index * self.row_height,
                                   self.rect.width, self.row_height)
            colour = CARD_ALT if absolute_index % 2 else CARD
            if self.highlight_key and row.get(self.highlight_key) == self.highlight_value:
                colour = CARD.lerp(GREEN, .32)
            if absolute_index == self.hovered_row:
                colour = colour.lerp(WHITE, .08)
            if absolute_index == self.selected_row:
                colour = colour.lerp(GREEN, .28)
            pygame.draw.rect(surface, colour, row_rect)
            pygame.draw.line(surface, BORDER, row_rect.bottomleft, row_rect.bottomright)
            for column, cell_rect in zip(self.columns, column_rects):
                value = row.get(column.key, "")
                shown = column.formatter(value) if column.formatter else str(value)
                colour_value = self.colour_func(column.key, value, row) if self.colour_func else None
                colour_value = colour_value or (WHITE if row.get("read", 1) else GOLD)
                label = clipped_text(shown, cell_rect.width - 14, 12, not row.get("read", 1))
                y = row_rect.y + (self.row_height - 14) // 2
                if column.align == "right":
                    text(surface, label, (cell_rect.right - 8, y), 12, colour_value,
                         bold=not row.get("read", 1), anchor="topright")
                else:
                    text(surface, label, (cell_rect.x + 8, y), 12, colour_value, bold=not row.get("read", 1))
        surface.set_clip(clip_before)
        if len(self.rows) > self.visible_count:
            track = self._scroll_track()
            pygame.draw.rect(surface, DIM, track)
            thumb_h = max(18, int(track.height * self.visible_count / len(self.rows)))
            max_scroll = len(self.rows) - self.visible_count
            thumb_y = track.y + int((track.height - thumb_h) * self.scroll / max_scroll)
            pygame.draw.rect(surface, GREEN, (track.x, thumb_y, track.width, thumb_h))
