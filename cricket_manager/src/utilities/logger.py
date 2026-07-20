"""Rotating application logs and friendly last-resort crash reporting."""
from __future__ import annotations

import ctypes
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import threading
from types import TracebackType
from typing import Type


LOGGER_NAME = "stumped"


class GameLogFormatter(logging.Formatter):
    """Compact log format with the source location required for support."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        message = record.getMessage().replace("\n", " ")
        line = f"[{timestamp}] {record.levelname}: {message} | File: {Path(record.pathname).name} | Line: {record.lineno}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging(log_directory: str | Path, level: int = logging.INFO) -> tuple[logging.Logger, Path]:
    """Create ``logs/error.log`` with five 1 MB rotated backups."""
    directory = Path(log_directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "error.log"
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    # Reconfiguration is safe during tests and display recreation.
    for handler in list(logger.handlers):
        handler.close(); logger.removeHandler(handler)
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8", delay=True)
    handler.setLevel(level); handler.setFormatter(GameLogFormatter())
    logger.addHandler(handler)
    logger.info("Logging initialised")
    return logger, log_path


def install_exception_hooks(logger: logging.Logger, log_path: str | Path) -> None:
    """Capture exceptions escaping the main or a background thread."""
    previous_hook = sys.excepthook

    def exception_hook(exc_type: Type[BaseException], value: BaseException,
                       traceback: TracebackType | None) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            previous_hook(exc_type, value, traceback); return
        logger.critical("Unhandled application exception", exc_info=(exc_type, value, traceback))
        show_crash_dialog(value, log_path)

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        logger.critical(f"Unhandled exception in thread {args.thread.name if args.thread else 'unknown'}",
                        exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    sys.excepthook = exception_hook
    threading.excepthook = thread_hook


def show_crash_dialog(error: BaseException, log_path: str | Path) -> None:
    """Show a native Windows error box, falling back safely to stderr."""
    location = str(Path(log_path).resolve())
    message = ("Stumped! encountered an unexpected problem and needs to close.\n\n"
               "Your save data has not been deleted. Technical details were written to:\n"
               f"{location}\n\nError: {error}")
    try:
        if sys.platform == "win32":
            ctypes.windll.user32.MessageBoxW(None, message, "Stumped! — Error", 0x10)
            return
        from tkinter import messagebox
        messagebox.showerror("Stumped! — Error", message)
    except Exception:
        print(message, file=sys.stderr)
