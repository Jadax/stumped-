"""Production logging regression tests."""
from __future__ import annotations

import logging
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from src.utilities.logger import setup_logging


class LoggerTests(unittest.TestCase):
    def test_required_format_and_levels(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            logger, path = setup_logging(directory)
            logger.info("Game started")
            logger.warning("Example warning")
            logger.error("Example error")
            for handler in logger.handlers: handler.flush()
            lines = Path(path).read_text(encoding="utf-8").splitlines()
            self.assertTrue(any(" INFO: Game started | File:" in line for line in lines))
            self.assertTrue(any(" WARNING: Example warning | File:" in line for line in lines))
            self.assertTrue(any(" ERROR: Example error | File:" in line for line in lines))
            self.assertRegex(lines[-1], r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]")

    def test_rotating_handler_keeps_five_backups(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            logger, _ = setup_logging(directory)
            handler = next(h for h in logger.handlers if hasattr(h, "backupCount"))
            self.assertEqual(handler.backupCount, 5)
            self.assertEqual(handler.level, logging.INFO)


if __name__ == "__main__":
    unittest.main(verbosity=2)
