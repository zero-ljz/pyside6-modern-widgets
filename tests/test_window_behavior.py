from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import ModernWindow
from pyside6_modern_widgets import modern_window as modern_window_module
from pyside6_modern_widgets._windows_window import (
    HTCAPTION,
    HTCLIENT,
    HTMAXBUTTON,
    WM_NCLBUTTONDBLCLK,
    WM_NCLBUTTONDOWN,
    WM_NCLBUTTONUP,
    WM_SYSCOMMAND,
    WindowsMessage,
)

_APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    ("message_id", "command"),
    [(WM_NCLBUTTONDBLCLK, HTCAPTION), (WM_SYSCOMMAND, 0xF032)],
)
def test_native_maximize_then_button_restore_preserves_geometry(
    monkeypatch, message_id, command
) -> None:
    window = ModernWindow()
    window.setGeometry(100, 100, 500, 300)
    window.show()
    _APP.processEvents()
    normal = window.geometry()
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: True)
    monkeypatch.setattr(modern_window_module, "set_mouse_capture", lambda *_args: None)
    message = WindowsMessage(hwnd=1, message=message_id, w_param=command, l_param=0)
    monkeypatch.setattr(modern_window_module, "read_message", lambda _address: message)
    window._native_frame_enabled = True

    assert window.nativeEvent(b"windows_generic_MSG", 0) == (True, 0)
    _APP.processEvents()
    assert window.isMaximized()
    assert window.normalGeometry() == normal
    window.titleBar.maximizeButton.click()
    _APP.processEvents()
    assert not window.isMaximized()
    assert window.geometry() == normal
    window.close()


@pytest.mark.parametrize(
    "message_id,command", [(WM_NCLBUTTONDBLCLK, HTCAPTION), (WM_SYSCOMMAND, 0xF120)]
)
def test_button_maximize_then_native_restore_preserves_geometry(
    monkeypatch, message_id, command
) -> None:
    window = ModernWindow()
    window.setGeometry(100, 100, 500, 300)
    window.show()
    _APP.processEvents()
    normal = window.geometry()
    window.titleBar.maximizeButton.click()
    _APP.processEvents()
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: True)
    monkeypatch.setattr(modern_window_module, "set_mouse_capture", lambda *_args: None)
    message = WindowsMessage(hwnd=1, message=message_id, w_param=command, l_param=0)
    monkeypatch.setattr(modern_window_module, "read_message", lambda _address: message)
    window._native_frame_enabled = True

    assert window.nativeEvent(b"windows_generic_MSG", 0) == (True, 0)
    _APP.processEvents()
    assert not window.isMaximized()
    assert window.geometry() == normal
    window.close()


@pytest.mark.parametrize("maximized", [False, True])
def test_native_restore_from_minimized_preserves_previous_state(maximized) -> None:
    window = ModernWindow()
    window.show()
    if maximized:
        window.showMaximized()
    window.showMinimized()
    _APP.processEvents()
    window._restore_from_native_command()
    _APP.processEvents()

    assert not window.isMinimized()
    assert window.isMaximized() == maximized
    window.close()


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


@pytest.mark.parametrize("native_move_started", [False, True])
@pytest.mark.parametrize(
    ("press_x", "anchor_x"),
    [(150, 150), (650, 400), (800, 400), (950, 400), (1200, 400), (1390, 590)],
)
def test_caption_restore_drag_keeps_cursor_anchor(
    monkeypatch, native_move_started, press_x, anchor_x
) -> None:
    window = ModernWindow()
    positions = iter((QPoint(press_x, 20), QPoint(press_x + 10, 30), QPoint(press_x + 30, 50)))
    capture_calls: list[tuple[int, bool]] = []
    monkeypatch.setattr(
        modern_window_module,
        "QCursor",
        type("CursorProbe", (), {"pos": staticmethod(lambda: next(positions))}),
    )
    monkeypatch.setattr(window, "mapFromGlobal", lambda _position: QPoint(press_x, 20))
    monkeypatch.setattr(modern_window_module, "client_position_from_l_param", lambda *_args: None)
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

    def start_move(hwnd: int) -> bool:
        assert hwnd == 1
        assert window.geometry() == QRect(press_x + 10 - anchor_x, 10, 800, 600)
        assert window._native_caption_press_position is None
        return native_move_started

    monkeypatch.setattr(modern_window_module, "start_system_move", start_move)

    window._begin_native_caption_drag(1, 0)
    window._continue_native_caption_drag(1)
    first_anchor = QPoint(press_x + 10, 30) - window.geometry().topLeft()
    assert first_anchor == QPoint(anchor_x, 20)
    if native_move_started:
        assert window._native_caption_manual_move_offset is None
        assert capture_calls == [(1, True), (1, False)]
    else:
        window._continue_native_caption_drag(1)
        second_anchor = QPoint(press_x + 30, 50) - window.geometry().topLeft()
        assert second_anchor == first_anchor
        assert capture_calls == [(1, True), (1, False), (1, True)]
    window.close()


def test_caption_press_uses_message_position_when_cursor_has_already_moved(monkeypatch) -> None:
    window = ModernWindow()
    window.setGeometry(100, 100, 1600, 900)
    monkeypatch.setattr(modern_window_module, "set_mouse_capture", lambda *_args: None)
    monkeypatch.setattr(
        modern_window_module,
        "QCursor",
        type("CursorProbe", (), {"pos": staticmethod(lambda: QPoint(1510, 180))}),
    )

    def client_position(hwnd, l_param, width, height):
        assert (hwnd, l_param, width, height) == (1, 123, 1600, 900)
        return 1390.0, 12.0

    monkeypatch.setattr(modern_window_module, "client_position_from_l_param", client_position)
    window._begin_native_caption_drag(1, 123)

    assert window._native_caption_press_position == window.mapToGlobal(QPoint(1390, 12))
    assert window._native_caption_anchor_y == 12
    assert window._native_caption_anchor_x == 210
    assert window._native_caption_anchor_from_right
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
