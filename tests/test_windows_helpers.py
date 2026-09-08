from __future__ import annotations

import ctypes

from pyside6_modern_widgets import _windows_window


class _NativeFunction:
    def __init__(self, callback) -> None:
        self._callback = callback
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self._callback(*args)


class _MoveUser32:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[int, ...]]] = []
        self.SetForegroundWindow = _NativeFunction(
            lambda hwnd: self._record("activate", int(hwnd.value))
        )
        self.ReleaseCapture = _NativeFunction(lambda: self._record("release"))
        self.PostMessageW = _NativeFunction(
            lambda hwnd, message, command, l_param: self._record(
                "post", int(hwnd.value), message, command, l_param
            )
        )

    def _record(self, name: str, *args: int) -> bool:
        self.calls.append((name, args))
        return True


def test_l_param_coordinates_use_full_width_cursor_position_when_available(monkeypatch) -> None:
    x, y = 70_000, -40_000
    l_param = (x & 0xFFFF) | ((y & 0xFFFF) << 16)
    monkeypatch.setattr(_windows_window, "_cursor_screen_position", lambda: (x, y))

    assert _windows_window.screen_position_from_l_param(l_param) == (x, y)


def test_l_param_coordinates_keep_packed_position_for_synthetic_messages(monkeypatch) -> None:
    monkeypatch.setattr(_windows_window, "_cursor_screen_position", lambda: (100, 100))

    assert _windows_window.screen_position_from_l_param((20 & 0xFFFF) | (30 << 16)) == (20, 30)


def test_system_move_is_posted_after_capture_is_released(monkeypatch) -> None:
    user32 = _MoveUser32()
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: user32)

    assert _windows_window.start_system_move(12345)
    assert user32.calls == [
        ("activate", (12345,)),
        ("release", ()),
        ("post", (12345, 0x0112, 0xF012, 0)),
    ]
