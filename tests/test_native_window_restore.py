"""Real HWND regressions; run with QT_QPA_PLATFORM=windows."""

import ctypes
import sys
from ctypes import wintypes

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import ModernWindow

_APP = QApplication.instance()
pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or _APP.platformName() != "windows",
    reason="Requires real Windows HWNDs",
)


@pytest.mark.parametrize("maximized", [False, True])
@pytest.mark.parametrize("restore", ["state", "native", "show"])
def test_minimized_window_restores_native_state_and_geometry(maximized, restore):
    user32 = ctypes.windll.user32
    user32.IsIconic.argtypes = (wintypes.HWND,)
    user32.IsIconic.restype = wintypes.BOOL
    user32.IsZoomed.argtypes = (wintypes.HWND,)
    user32.IsZoomed.restype = wintypes.BOOL
    user32.GetForegroundWindow.restype = wintypes.HWND
    window = ModernWindow()
    window.setGeometry(100, 100, 800, 500)
    try:
        window.show()
        QTest.qWait(100)
        normal = window.geometry()
        hwnd = int(window.winId())
        for settle_ms in (0, 50, 0):
            if maximized:
                window.showMaximized()
            QTest.qWait(50)
            window.showMinimized()
            if settle_ms:
                QTest.qWait(settle_ms)
            assert user32.IsIconic(hwnd)
            if restore == "state":
                window.setWindowState(window.windowState() & ~Qt.WindowMinimized)
                window.show()
            elif restore == "native":
                window._restore_from_native_command()
            elif maximized:
                window.showMaximized()
            else:
                window.showNormal()
            window.raise_()
            window.activateWindow()
            QTest.qWait(150)
            assert window.isVisible()
            assert not window.isMinimized()
            assert not user32.IsIconic(hwnd)
            assert window.isMaximized() == maximized
            assert bool(user32.IsZoomed(hwnd)) == maximized
            assert user32.GetForegroundWindow() == hwnd
            window.showNormal()
            QTest.qWait(100)
            assert window.geometry() == normal
    finally:
        window.close()
