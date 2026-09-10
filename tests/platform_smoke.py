"""Exercise ModernWindow against the active Qt platform plugin."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QPoint, QSize
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import ModernWindow
from pyside6_modern_widgets._windows_window import (
    HTCAPTION,
    HTMAXBUTTON,
    WM_NCLBUTTONDBLCLK,
    WM_NCLBUTTONDOWN,
    WM_NCLBUTTONUP,
    WM_SYSCOMMAND,
    WS_MAXIMIZEBOX,
    WS_THICKFRAME,
    _client_metrics,
)


def _wait(app: QApplication, milliseconds: int = 100) -> None:
    app.processEvents()
    QTest.qWait(milliseconds)
    app.processEvents()


def main() -> int:
    app = QApplication(sys.argv)
    window = ModernWindow()
    normal_size = QSize(900, 600)
    window.resize(normal_size)
    screen = app.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        window.move(available.center() - QPoint(window.width() // 2, window.height() // 2))
    window.show()
    _wait(app)

    assert window.isVisible()
    assert window.titleBar is not None
    assert not window.grab().isNull()

    if sys.platform == "win32" and app.platformName() == "windows":
        get_style = ctypes.windll.user32.GetWindowLongPtrW
        get_style.argtypes = (wintypes.HWND, ctypes.c_int)
        get_style.restype = ctypes.c_ssize_t
        send_message = ctypes.windll.user32.SendMessageW
        send_message.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        send_message.restype = ctypes.c_ssize_t
        hwnd = int(window.winId())

        assert send_message(hwnd, WM_NCLBUTTONDOWN, HTMAXBUTTON, 0) == 0
        assert window.titleBar.maximizeButton.isDown()
        assert send_message(hwnd, WM_NCLBUTTONUP, HTMAXBUTTON, 0) == 0
        _wait(app)
        assert window.isMaximized()
        assert send_message(hwnd, WM_NCLBUTTONDOWN, HTMAXBUTTON, 0) == 0
        assert send_message(hwnd, WM_NCLBUTTONUP, HTMAXBUTTON, 0) == 0
        _wait(app)
        assert not window.isMaximized()

        normal_geometry = window.geometry()
        normal_client = _client_metrics(hwnd)
        assert normal_client is not None
        # A native caption double-click used to lose the normal geometry;
        # following it with the Qt restore button then clipped the client area.
        for maximize_message, restore_message in (
            ((WM_NCLBUTTONDBLCLK, HTCAPTION), None),
            ((WM_SYSCOMMAND, 0xF030), (WM_NCLBUTTONDBLCLK, HTCAPTION)),
            ((WM_NCLBUTTONDBLCLK, HTCAPTION), (WM_SYSCOMMAND, 0xF120)),
        ):
            send_message(hwnd, *maximize_message, 0)
            _wait(app)
            assert window.isMaximized()
            assert window.normalGeometry() == normal_geometry
            if restore_message is None:
                send_message(hwnd, WM_NCLBUTTONDOWN, HTMAXBUTTON, 0)
                send_message(hwnd, WM_NCLBUTTONUP, HTMAXBUTTON, 0)
            else:
                send_message(hwnd, *restore_message, 0)
            _wait(app)
            assert not window.isMaximized()
            assert window.geometry() == normal_geometry
            assert _client_metrics(hwnd) == normal_client

        window.setFixedSize(normal_size)
        _wait(app)
        fixed_style = int(get_style(hwnd, -16))
        assert not fixed_style & WS_THICKFRAME
        assert not fixed_style & WS_MAXIMIZEBOX
        window.showMaximized()
        _wait(app)
        assert not window.isMaximized()
        assert window.size() == normal_size

        window.setMinimumSize(0, 0)
        window.setMaximumSize(16777215, 16777215)
        _wait(app)
        resizable_style = int(get_style(hwnd, -16))
        assert resizable_style & WS_THICKFRAME
        assert resizable_style & WS_MAXIMIZEBOX

    window._handle_screen_metrics_changed()
    _wait(app, 150)
    assert not window.grab().isNull()
    window.close()
    _wait(app, 20)
    print(f"platform={app.platformName()} screens={len(app.screens())} smoke=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
