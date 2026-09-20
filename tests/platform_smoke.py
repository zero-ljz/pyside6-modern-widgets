"""Exercise ModernWindow against the active Qt platform plugin."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from unittest.mock import patch

from PySide6.QtCore import QEvent, QObject, QPoint, QSize, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QWidget

from pyside6_modern_widgets import ModernMessageBox, ModernWindow
from pyside6_modern_widgets import modern_window as modern_window_module
from pyside6_modern_widgets._windows_window import (
    HTCAPTION,
    HTCLIENT,
    HTMAXBUTTON,
    HTTRANSPARENT,
    WM_MOUSEMOVE,
    WM_NCHITTEST,
    WM_NCLBUTTONDBLCLK,
    WM_NCLBUTTONDOWN,
    WM_NCLBUTTONUP,
    WM_SYSCOMMAND,
    WS_MAXIMIZEBOX,
    WS_THICKFRAME,
    _client_metrics,
    is_window_maximized,
    screen_position_from_client,
)


def _wait(app: QApplication, milliseconds: int = 100) -> None:
    app.processEvents()
    QTest.qWait(milliseconds)
    app.processEvents()


class _LifecycleProbe(QObject):
    def __init__(self, window: ModernWindow) -> None:
        super().__init__(window)
        self.events: list[QEvent.Type] = []
        window.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if event.type() in (
            QEvent.Type.Hide,
            QEvent.Type.Show,
            QEvent.Type.WinIdChange,
            QEvent.Type.PlatformSurface,
        ):
            self.events.append(event.type())
        return False


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
        assert is_window_maximized(hwnd)
        assert window.titleBar.maximizeButton.toolTip() == "Restore"
        assert send_message(hwnd, WM_NCLBUTTONDOWN, HTMAXBUTTON, 0) == 0
        assert send_message(hwnd, WM_NCLBUTTONUP, HTMAXBUTTON, 0) == 0
        _wait(app)
        assert not window.isMaximized()
        assert not is_window_maximized(hwnd)
        assert window.titleBar.maximizeButton.toolTip() == "Maximize"

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

        # Re-showing a frameless maximized window can set WS_MAXIMIZE and
        # overwrite Qt's normalGeometry with the maximized client rectangle.
        for transition in ("direct", "minimize", "hide", "minimized"):
            for restore in ("drag", "button", "state", "hidden_state"):
                if transition == "minimized" and restore in ("drag", "button"):
                    continue  # Caption controls are unavailable while minimized.
                window.setGeometry(normal_geometry)
                window.showMaximized()
                _wait(app)
                if transition in ("minimize", "minimized"):
                    window.showMinimized()
                    _wait(app)
                    if transition == "minimize":
                        send_message(hwnd, WM_SYSCOMMAND, 0xF120, 0)
                elif transition == "hide":
                    window.hide()
                    window.show()
                _wait(app)
                assert window.isMaximized()

                if restore == "hidden_state":
                    window.hide()
                    window.setWindowState(Qt.WindowState.WindowNoState)
                    assert not window.isVisible()
                    assert not get_style(hwnd, -16) & 0x10000000  # WS_VISIBLE
                    _wait(app)
                    assert not window.isVisible()
                    assert not get_style(hwnd, -16) & 0x10000000
                    window.show()
                elif restore == "state":
                    window.setWindowState(Qt.WindowState.WindowNoState)
                elif restore == "button":
                    window.titleBar.maximizeButton.click()
                else:
                    press = QPoint(300, 20)
                    physical = screen_position_from_client(
                        hwnd, press.x(), press.y(), window.width(), window.height()
                    )
                    assert physical is not None
                    l_param = (physical[0] & 0xFFFF) | ((physical[1] & 0xFFFF) << 16)
                    cursor = window.mapToGlobal(press) + QPoint(30, 20)
                    send_message(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, l_param)
                    assert window._native_caption_press_position is not None
                    with (
                        patch.object(modern_window_module.QCursor, "pos", return_value=cursor),
                        patch.object(
                            modern_window_module, "start_system_move", return_value=True
                        ) as start_move,
                    ):
                        send_message(hwnd, WM_MOUSEMOVE, 1, 0)
                        start_move.assert_called_once_with(hwnd)
                    # Check the handoff as well as queued native state changes.
                    assert not is_window_maximized(hwnd), (transition, restore)
                    assert window.size() == normal_geometry.size(), (transition, restore)
                _wait(app)
                assert not window.isMaximized(), (transition, restore)
                assert not is_window_maximized(hwnd), (transition, restore)
                assert window.size() == normal_geometry.size(), (transition, restore)
                if restore != "drag":
                    assert window.geometry() == normal_geometry, (transition, restore)

        lifecycle = _LifecycleProbe(window)
        for maximized in (False, True):
            window.setGeometry(normal_geometry)
            if maximized:
                window.showMaximized()
            _wait(app)
            geometry = window.geometry()
            restore_geometry = window.normalGeometry()
            style = int(get_style(hwnd, -16))
            native_maximized = is_window_maximized(hwnd)
            lifecycle.events.clear()
            for on_top in (True, False, True, False):
                window.titleBar.pinButton.click()
                _wait(app)
                assert not lifecycle.events, lifecycle.events
                assert int(window.winId()) == hwnd
                assert window.isVisible()
                assert window.isMaximized() == maximized
                assert is_window_maximized(hwnd) == native_maximized
                assert window.geometry() == geometry
                assert window.normalGeometry() == restore_geometry
                assert int(get_style(hwnd, -16)) == style
                assert bool(get_style(hwnd, -20) & 0x00000008) == on_top  # WS_EX_TOPMOST
                assert bool(window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint) == on_top
                assert window.titleBar.pinButton.isChecked() == on_top
            window.showNormal()
            _wait(app)
            assert window.geometry() == normal_geometry

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

        # Calling winId() on a descendant (including via accessibility) can
        # promote the title bar and content to native sibling HWNDs at runtime.
        content = QWidget()
        window.setCentralWidget(content)
        status = window.statusBar()
        button = QPushButton("Custom")
        window.titleBar.addCustomWidget(button)
        content.winId()
        window.titleBar.winId()
        status.winId()
        button.winId()
        _wait(app)

        def child_hit(child, position):
            screen_position = screen_position_from_client(
                hwnd, position.x(), position.y(), window.width(), window.height()
            )
            assert screen_position is not None
            x, y = screen_position
            return send_message(
                int(child.winId()), WM_NCHITTEST, 0, (x & 0xFFFF) | ((y & 0xFFFF) << 16)
            )

        caption = QPoint(200, window.titleBar.height() // 2)
        corner = QPoint(window.width() - 2, window.height() - 2)
        button_center = button.mapTo(window, button.rect().center())
        maximize_center = window.titleBar.maximizeButton.mapTo(
            window, window.titleBar.maximizeButton.rect().center()
        )
        assert child_hit(window.titleBar, caption) == HTTRANSPARENT
        assert child_hit(status, corner) == HTTRANSPARENT
        assert child_hit(content, QPoint(2, window.height() // 2)) == HTTRANSPARENT
        assert child_hit(window.titleBar, maximize_center) == HTTRANSPARENT
        assert child_hit(button, button_center) == HTCLIENT
        assert child_hit(content, QPoint(window.width() // 2, window.height() // 2)) == HTCLIENT
        assert child_hit(window, caption) == HTCAPTION

        window.setFixedSize(window.size())
        _wait(app)
        assert child_hit(status, corner) == HTCLIENT
        assert child_hit(window.titleBar, caption) == HTTRANSPARENT
        window.hide()
        window.show()
        _wait(app)
        assert child_hit(window.titleBar, caption) == HTTRANSPARENT

    window._handle_screen_metrics_changed()
    _wait(app, 150)
    assert not window.grab().isNull()
    window.close()
    _wait(app, 20)

    # Check native-platform focus too: title-bar buttons must not capture Enter.
    outcomes = []
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        box.setText("Continue?")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.show()
        box.activateWindow()
        _wait(app)
        focus = app.focusWidget()
        assert focus in box.buttons()
        QTest.keyClick(focus, Qt.Key.Key_Return)
        outcomes.append((box.isVisible(), box.result()))
        box.deleteLater()
    assert outcomes[0] == outcomes[1]

    print(f"platform={app.platformName()} screens={len(app.screens())} smoke=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
