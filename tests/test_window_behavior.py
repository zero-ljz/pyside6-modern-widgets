from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import ModernWindow
from pyside6_modern_widgets import modern_window as modern_window_module
from pyside6_modern_widgets._windows_window import (
    HTCAPTION,
    HTCLIENT,
    HTMAXBUTTON,
    WM_NCLBUTTONDOWN,
    WM_NCLBUTTONUP,
    WindowsMessage,
)

_APP = QApplication.instance() or QApplication([])


def test_fixed_window_cannot_maximize() -> None:
    window = ModernWindow()
    window.setFixedSize(500, 300)
    window.show()
    _APP.processEvents()

    window.showMaximized()
    _APP.processEvents()

    assert not window.isMaximized()
    assert window.size().toTuple() == (500, 300)
    assert not window._can_maximize()
    assert window.titleBar is not None
    assert not window.titleBar.maximizeButton.isEnabled()
    window.close()


def test_full_screen_surface_has_no_rounded_holes_or_resize_edges() -> None:
    window = ModernWindow()
    window.resize(400, 250)
    window.showFullScreen()
    _APP.processEvents()

    image = window.grab().toImage()
    assert window.frame._corner_radius == 0
    assert window.chromeOverlay._corner_radius == 0
    assert window._resize_edges_at(QPoint(0, 0)) == Qt.Edge(0)
    assert image.pixelColor(0, 0).alpha() == 255
    window.close()


def test_screen_metric_change_invalidates_surface_and_schedules_refresh() -> None:
    window = ModernWindow()
    window.resize(400, 250)
    window.show()
    _APP.processEvents()
    window.frame._ensure_watercolor_cache()
    cached_surface = window.frame._watercolor_cache
    assert cached_surface is not None

    window._handle_screen_metrics_changed()
    assert window._native_frame_sync_timer.isActive()
    assert window._surface_refresh_timer.isActive()
    assert window._surface_settle_timer.isActive()

    _APP.processEvents()
    assert window.frame._watercolor_cache is not cached_surface
    assert window.frame._watercolor_cache_signature is not None
    window._surface_settle_timer.stop()
    window.close()


def test_native_maximize_click_is_consumed_and_runs_custom_action(monkeypatch) -> None:
    window = ModernWindow()
    assert window.titleBar is not None
    calls: list[bool] = []
    message = [WindowsMessage(hwnd=1, message=WM_NCLBUTTONDOWN, w_param=HTMAXBUTTON, l_param=0)]
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: True)
    monkeypatch.setattr(modern_window_module, "read_message", lambda _message: message[0])
    monkeypatch.setattr(window, "showMaximized", lambda: calls.append(True))
    window._native_frame_enabled = True

    assert window.nativeEvent("windows_generic_MSG", 0) == (True, 0)
    assert window._native_maximize_button_pressed
    assert window.titleBar.maximizeButton.isDown()

    message[0] = WindowsMessage(hwnd=1, message=WM_NCLBUTTONUP, w_param=HTMAXBUTTON, l_param=0)
    assert window.nativeEvent("windows_generic_MSG", 0) == (True, 0)
    _APP.processEvents()
    assert calls == [True]
    assert not window._native_maximize_button_pressed
    assert not window.titleBar.maximizeButton.isDown()
    window.close()


def test_native_maximize_release_outside_only_cancels_press(monkeypatch) -> None:
    window = ModernWindow()
    assert window.titleBar is not None
    calls: list[bool] = []
    message = [WindowsMessage(hwnd=1, message=WM_NCLBUTTONDOWN, w_param=HTMAXBUTTON, l_param=0)]
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: True)
    monkeypatch.setattr(modern_window_module, "read_message", lambda _message: message[0])
    monkeypatch.setattr(window, "showMaximized", lambda: calls.append(True))
    window._native_frame_enabled = True

    window.nativeEvent("windows_generic_MSG", 0)
    message[0] = WindowsMessage(hwnd=1, message=WM_NCLBUTTONUP, w_param=HTCLIENT, l_param=0)
    assert window.nativeEvent("windows_generic_MSG", 0) == (True, 0)
    _APP.processEvents()
    assert calls == []
    assert not window.titleBar.maximizeButton.isDown()
    window.close()


def test_maximized_caption_press_starts_restore_drag(monkeypatch) -> None:
    window = ModernWindow()
    message = WindowsMessage(hwnd=1, message=WM_NCLBUTTONDOWN, w_param=HTCAPTION, l_param=0)
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: True)
    monkeypatch.setattr(modern_window_module, "read_message", lambda _message: message)
    monkeypatch.setattr(window, "isMaximized", lambda: True)
    monkeypatch.setattr(modern_window_module, "set_mouse_capture", lambda *_args: None)
    window._native_frame_enabled = True

    assert window.nativeEvent(b"windows_generic_MSG", 0) == (True, 0)
    assert window._native_caption_press_position is not None
    window.close()


def test_caption_restore_drag_keeps_cursor_anchor(monkeypatch) -> None:
    window = ModernWindow()
    positions = iter((QPoint(1200, 20), QPoint(1210, 30), QPoint(1230, 50)))
    capture_calls: list[tuple[int, bool]] = []
    monkeypatch.setattr(
        modern_window_module,
        "QCursor",
        type("CursorProbe", (), {"pos": staticmethod(lambda: next(positions))}),
    )
    monkeypatch.setattr(window, "mapFromGlobal", lambda _position: QPoint(1200, 20))
    monkeypatch.setattr(window, "width", lambda: 1600)
    monkeypatch.setattr(window, "normalGeometry", lambda: QRect(200, 100, 800, 600))
    monkeypatch.setattr(window, "showNormal", lambda: None)
    monkeypatch.setattr(
        window,
        "frameGeometry",
        lambda: QRect(window.geometry()),
    )
    monkeypatch.setattr(
        modern_window_module,
        "set_mouse_capture",
        lambda hwnd, captured: capture_calls.append((hwnd, captured)),
    )
    monkeypatch.setattr(modern_window_module, "start_system_move", lambda _hwnd: False)

    window._begin_native_caption_drag(1)
    window._continue_native_caption_drag(1)
    first_anchor = QPoint(1210, 30) - window.geometry().topLeft()
    window._continue_native_caption_drag(1)
    second_anchor = QPoint(1230, 50) - window.geometry().topLeft()

    assert first_anchor == QPoint(600, 20)
    assert second_anchor == first_anchor
    assert capture_calls == [(1, True), (1, False), (1, True)]
    window.close()


def test_manual_resize_fallback_respects_minimum_size() -> None:
    window = ModernWindow()
    window.setGeometry(100, 100, 320, 240)
    window.setMinimumSize(250, 180)

    window._begin_manual_resize(Qt.Edge.LeftEdge | Qt.Edge.TopEdge, QPoint(100, 100))
    window._update_manual_resize(QPoint(200, 200))

    assert window.geometry().getRect() == (170, 160, 250, 180)
    window._finish_manual_resize()
    window._finish_system_resize_tracking()
