from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import (
    ModernDialog,
    ModernMessageBox,
    ModernWindow,
    _system_menu,
    modern_menu,
)

_APP = QApplication.instance() or QApplication([])


def _dispose(window) -> None:
    window.close()
    window.deleteLater()


@pytest.mark.parametrize("window_class", [ModernWindow, ModernDialog, ModernMessageBox])
def test_shared_title_bar_requests_the_host_system_menu(monkeypatch, window_class) -> None:
    window = window_class()
    title_bar = window.titleBar if isinstance(window, ModernWindow) else window._title_bar
    calls = []

    def show_system_menu(position):
        calls.append(position)
        return True

    monkeypatch.setattr(window._system_menu_controller, "show", show_system_menu)
    event = QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse,
        QPoint(100, title_bar.height() // 2),
        QPoint(300, 200),
    )
    try:
        title_bar.contextMenuEvent(event)
        assert calls == [QPoint(300, 200)]
        assert event.isAccepted()
    finally:
        _dispose(window)


def test_dialog_native_system_menu_follows_flags_and_size_constraints(monkeypatch) -> None:
    flags = (
        Qt.WindowType.Dialog
        | Qt.WindowType.WindowTitleHint
        | Qt.WindowType.WindowSystemMenuHint
        | Qt.WindowType.WindowMinimizeButtonHint
        | Qt.WindowType.WindowMaximizeButtonHint
        | Qt.WindowType.WindowCloseButtonHint
    )
    dialog = ModernDialog(f=flags)
    dialog.resize(400, 240)
    dialog.show()
    _APP.processEvents()
    calls = []
    monkeypatch.setattr(
        _system_menu,
        "screen_position_from_client",
        lambda _hwnd, x, y, _width, _height: (x, y),
    )
    monkeypatch.setattr(
        _system_menu,
        "show_native_system_menu",
        lambda *args, **kwargs: calls.append((args, kwargs)) or True,
    )
    try:
        assert dialog.showSystemWindowMenu(dialog.mapToGlobal(QPoint(80, 20)))
        native_options = calls[-1][1]
        assert native_options["move_position"] is not None
        assert native_options["can_resize"]
        assert native_options["can_minimize"]
        assert native_options["can_maximize"]
        assert native_options["can_close"]

        dialog.setFixedSize(dialog.size())
        assert dialog.showSystemWindowMenu(dialog.mapToGlobal(QPoint(80, 20)))
        native_options = calls[-1][1]
        assert not native_options["can_resize"]
        assert not native_options["can_maximize"]
    finally:
        _dispose(dialog)


def test_message_box_native_system_menu_is_fixed_and_close_only(monkeypatch) -> None:
    box = ModernMessageBox()
    box.show()
    _APP.processEvents()
    calls = []
    monkeypatch.setattr(
        _system_menu,
        "screen_position_from_client",
        lambda _hwnd, x, y, _width, _height: (x, y),
    )
    monkeypatch.setattr(
        _system_menu,
        "show_native_system_menu",
        lambda *args, **kwargs: calls.append((args, kwargs)) or True,
    )
    try:
        assert box.showSystemWindowMenu(box.mapToGlobal(QPoint(80, 20)))
        native_options = calls[-1][1]
        assert not native_options["can_resize"]
        assert not native_options["can_minimize"]
        assert not native_options["can_maximize"]
        assert native_options["can_close"]
    finally:
        _dispose(box)


def test_portable_system_menu_is_used_when_native_menu_is_unavailable(monkeypatch) -> None:
    dialog = ModernDialog()
    popup_positions = []
    monkeypatch.setattr(_system_menu, "screen_position_from_client", lambda *_args: (20, 20))
    monkeypatch.setattr(_system_menu, "show_native_system_menu", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        modern_menu.ModernMenu,
        "popup",
        lambda _menu, position: popup_positions.append(position),
    )
    position = QPoint(300, 200)
    try:
        assert dialog.showSystemWindowMenu(position)
        assert popup_positions == [position]
        actions = [
            action for action in dialog._portable_system_menu.actions() if not action.isSeparator()
        ]
        assert [action.text() for action in actions] == ["Restore", "Minimize", "Maximize", "Close"]
        assert [action.isEnabled() for action in actions] == [False, False, False, True]
    finally:
        _dispose(dialog)


def test_system_menu_hint_disables_title_bar_menu(monkeypatch) -> None:
    dialog = ModernDialog()
    dialog.setWindowFlag(Qt.WindowType.WindowSystemMenuHint, False)
    native_calls = []
    monkeypatch.setattr(
        _system_menu,
        "show_native_system_menu",
        lambda *_args, **_kwargs: native_calls.append(True) or True,
    )
    try:
        assert not dialog.showSystemWindowMenu(QPoint(100, 100))
        assert native_calls == []
    finally:
        _dispose(dialog)
