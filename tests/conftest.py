"""Shared pytest configuration.

Forces Qt's offscreen platform plugin before PySide6 is ever imported,
so GUI-related tests can build real QGraphicsScene/QGraphicsItem
objects without a display server.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
