from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import ThemeManager
from pyside6_modern_widgets import theme as theme_module

_APP = QApplication.instance() or QApplication([])


class SystemAppearance(QObject):
    colorSchemeChanged = Signal(object)

    def __init__(self):
        super().__init__()
        self.scheme = Qt.ColorScheme.Light

    def colorScheme(self):
        return self.scheme

    def setScheme(self, scheme):
        self.scheme = scheme
        self.colorSchemeChanged.emit(scheme)


@pytest.fixture
def system_appearance(monkeypatch):
    theme_module.theme_manager().theme()
    appearance = SystemAppearance()
    monkeypatch.setattr(_APP, "styleHints", lambda: appearance)
    return appearance


@pytest.fixture
def theme_manager_instance(monkeypatch, system_appearance):
    original = theme_module.theme_manager()
    wallpaper_enabled = original.wallpaperEnabled()
    original.setWallpaperEnabled(False)
    deadline = time.monotonic() + 3
    while original._wallpaper_future is not None and time.monotonic() < deadline:
        QTest.qWait(10)
    assert original._wallpaper_future is None
    palette = _APP.palette()
    manager = ThemeManager()
    monkeypatch.setattr(theme_module, "_THEME_MANAGER", manager)
    manager.setWallpaperEnabled(False)
    try:
        yield manager
    finally:
        manager.setWallpaperEnabled(False)
        manager.deleteLater()
        QCoreApplication.sendPostedEvents(manager, QEvent.Type.DeferredDelete)
        monkeypatch.undo()
        original.setWallpaperEnabled(wallpaper_enabled)
        _APP.setPalette(palette)
