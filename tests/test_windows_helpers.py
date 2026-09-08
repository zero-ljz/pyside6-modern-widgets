from __future__ import annotations

from pyside6_modern_widgets import _windows_window


def test_l_param_coordinates_use_full_width_cursor_position_when_available(monkeypatch) -> None:
    x, y = 70_000, -40_000
    l_param = (x & 0xFFFF) | ((y & 0xFFFF) << 16)
    monkeypatch.setattr(_windows_window, "_cursor_screen_position", lambda: (x, y))

    assert _windows_window.screen_position_from_l_param(l_param) == (x, y)


def test_l_param_coordinates_keep_packed_position_for_synthetic_messages(monkeypatch) -> None:
    monkeypatch.setattr(_windows_window, "_cursor_screen_position", lambda: (100, 100))

    assert _windows_window.screen_position_from_l_param((20 & 0xFFFF) | (30 << 16)) == (20, 30)
