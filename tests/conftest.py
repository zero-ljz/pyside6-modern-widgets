from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt, Signal
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import ThemeManager
from pyside6_modern_widgets import theme as theme_module

_APP = QApplication.instance() or QApplication([])
if sys.platform == "darwin" and QApplication.platformName() == "offscreen":
    _APP.setStyle("Fusion")
_ORIGINAL_THEME_MANAGER = theme_module.theme_manager()
# Component tests use isolated managers; avoid querying the host wallpaper between tests.
_ORIGINAL_THEME_MANAGER.setWallpaperEnabled(False)


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
    _ORIGINAL_THEME_MANAGER.theme()
    appearance = SystemAppearance()
    with monkeypatch.context() as appearance_patch:
        appearance_patch.setattr(_APP, "styleHints", lambda: appearance)
        yield appearance


@pytest.fixture
def theme_manager_instance(monkeypatch, system_appearance):
    palette = _APP.palette()
    manager = ThemeManager()
    with monkeypatch.context() as manager_patch:
        manager_patch.setattr(theme_module, "_THEME_MANAGER", manager)
        manager.setWallpaperEnabled(False)
        try:
            yield manager
        finally:
            manager.setWallpaperEnabled(False)
    manager.deleteLater()
    QCoreApplication.sendPostedEvents(manager, QEvent.Type.DeferredDelete)
    _APP.setPalette(palette)
