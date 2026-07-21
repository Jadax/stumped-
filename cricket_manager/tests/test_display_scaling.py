"""Fullscreen logical-canvas selection: crisp integer scaling (v0.21.0).

The previous implementation always targeted a ~1920x1080 logical canvas,
which produces a *non-integer* SDL_SCALED stretch on very common monitors
(2560x1440 -> 1.33x) and visibly blurs every glyph in the game. This checks
that the common desktop resolutions all resolve to an exact integer scale.
"""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


class FullscreenLogicalSizeTests(unittest.TestCase):
    def _scale(self, desktop: tuple[int, int]) -> tuple[float, float]:
        import main
        logical = main.CricketManagerApp._fullscreen_logical_size(desktop)
        return desktop[0] / logical[0], desktop[1] / logical[1]

    def test_native_1080p_is_unscaled(self) -> None:
        import main
        self.assertEqual(main.CricketManagerApp._fullscreen_logical_size((1920, 1080)), (1920, 1080))

    def test_1440p_scales_by_an_exact_integer(self) -> None:
        sx, sy = self._scale((2560, 1440))
        self.assertEqual(sx, sy)
        self.assertEqual(sx, round(sx))

    def test_4k_scales_by_an_exact_integer_and_keeps_1080_canvas(self) -> None:
        import main
        logical = main.CricketManagerApp._fullscreen_logical_size((3840, 2160))
        self.assertEqual(logical, (1920, 1080))
        sx, sy = self._scale((3840, 2160))
        self.assertEqual(sx, sy)
        self.assertEqual(sx, round(sx))

    def test_ultrawide_1440_scales_by_an_exact_integer(self) -> None:
        sx, sy = self._scale((3440, 1440))
        self.assertEqual(sx, sy)
        self.assertEqual(sx, round(sx))

    def test_logical_canvas_never_falls_below_minimum_resolution(self) -> None:
        import main
        for desktop in [(1920, 1080), (2560, 1440), (3840, 2160), (3440, 1440),
                        (5120, 2880), (2560, 1080), (2560, 1600)]:
            logical = main.CricketManagerApp._fullscreen_logical_size(desktop)
            self.assertGreaterEqual(logical[0], 1280)
            self.assertGreaterEqual(logical[1], 720)


if __name__ == "__main__":
    unittest.main()
