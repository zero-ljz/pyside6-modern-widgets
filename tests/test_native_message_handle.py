from __future__ import annotations

import ctypes
from ctypes import wintypes

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import ModernWindow
from pyside6_modern_widgets._windows_window import WM_NCCALCSIZE, WM_NCHITTEST


def test_native_frame_calculation_does_not_recreate_the_window_handle(monkeypatch) -> None:
    from pyside6_modern_widgets import modern_window

    app = QApplication.instance() or QApplication([])
    window = ModernWindow()
    observed = []
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: True)
    window._native_frame_enabled = True

    def unexpected_win_id():
        raise AssertionError("winId() can recursively recreate a window during WM_NCCALCSIZE")

    monkeypatch.setattr(window, "winId", unexpected_win_id)
    monkeypatch.setattr(
        modern_window,
        "constrain_maximized_client_area",
        lambda hwnd, l_param: observed.append((hwnd, l_param)),
    )
    message = wintypes.MSG()
    message.hWnd = 12345
    message.message = WM_NCCALCSIZE
    message.wParam = 1
    message.lParam = 67890

    assert window.nativeEvent(b"windows_generic_MSG", ctypes.addressof(message)) == (True, 0)
    assert observed == [(12345, 67890)]
    window.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("surface_name", ["chromeOverlay", "frame"])
def test_native_decorative_surface_passes_mouse_hit_testing(monkeypatch, surface_name) -> None:
    from pyside6_modern_widgets import _window_chrome

    app = QApplication.instance() or QApplication([])
    window = ModernWindow()
    surface = getattr(window, surface_name)
    surface.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
    assert surface.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    monkeypatch.setattr(_window_chrome, "uses_windows_window_state", lambda: True)
    message = wintypes.MSG()
    message.hWnd = int(surface.winId())
    message.message = WM_NCHITTEST

    assert surface.nativeEvent(b"windows_generic_MSG", ctypes.addressof(message)) == (True, -1)
    window.deleteLater()
    app.processEvents()
