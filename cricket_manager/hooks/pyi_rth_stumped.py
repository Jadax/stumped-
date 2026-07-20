"""Runtime environment adjustments executed before the packaged game."""
import multiprocessing
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
multiprocessing.freeze_support()
