from __future__ import annotations

import ctypes
from ctypes import wintypes

import pytest

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


@pytest.mark.parametrize("zoomed", [False, True])
def test_native_maximize_state(monkeypatch, zoomed) -> None:
    class User32:
        IsZoomed = _NativeFunction(lambda hwnd: int(hwnd.value == 12345 and zoomed))

    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: User32())

    assert _windows_window.is_window_maximized(12345) is zoomed


def test_l_param_coordinates_use_full_width_cursor_position_when_available(monkeypatch) -> None:
    x, y = 70_000, -40_000
    l_param = (x & 0xFFFF) | ((y & 0xFFFF) << 16)
    monkeypatch.setattr(_windows_window, "_cursor_screen_position", lambda: (x, y))

    assert _windows_window.screen_position_from_l_param(l_param) == (x, y)


def test_l_param_coordinates_keep_packed_position_for_synthetic_messages(monkeypatch) -> None:
    monkeypatch.setattr(_windows_window, "_cursor_screen_position", lambda: (100, 100))

    assert _windows_window.screen_position_from_l_param((20 & 0xFFFF) | (30 << 16)) == (20, 30)


@pytest.mark.parametrize("position", [(1815, 45), (-1200, 80), (1200, -300), (0, 0)])
def test_system_move_is_posted_with_cursor_position_after_capture_is_released(
    monkeypatch, position
) -> None:
    user32 = _MoveUser32()
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: user32)
    monkeypatch.setattr(_windows_window, "_cursor_screen_position", lambda: position)

    assert _windows_window.start_system_move(12345)
    l_param = (position[0] & 0xFFFF) | ((position[1] & 0xFFFF) << 16)
    assert user32.calls == [
        ("activate", (12345,)),
        ("release", ()),
        ("post", (12345, 0x0112, 0xF012, l_param)),
    ]
    assert ctypes.c_short(l_param & 0xFFFF).value == position[0]
    assert ctypes.c_short((l_param >> 16) & 0xFFFF).value == position[1]


def test_system_move_falls_back_when_cursor_position_is_unavailable(monkeypatch) -> None:
    user32 = _MoveUser32()
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: user32)
    monkeypatch.setattr(_windows_window, "_cursor_screen_position", lambda: None)

    assert not _windows_window.start_system_move(12345)
    assert user32.calls == []


@pytest.mark.parametrize(
    ("proposed", "expected"),
    [
        ((-12, -12, 2572, 1528), (0, 0, 2560, 1516)),
        ((0, 0, 1167, 369), (0, 0, 1167, 369)),
        ((406, 198, 2156, 1318), (406, 198, 2156, 1318)),
        ((-200, -100, 1000, 800), (-200, -100, 1000, 800)),
    ],
)
def test_maximized_client_area_never_expands_restore_rectangle(
    monkeypatch, proposed, expected
) -> None:
    class User32:
        IsZoomed = _NativeFunction(lambda _hwnd: True)
        MonitorFromWindow = _NativeFunction(lambda *_args: 1)

        @staticmethod
        def monitor_info(_monitor, pointer):
            info = ctypes.cast(pointer, ctypes.POINTER(_windows_window._MonitorInfo)).contents
            info.rcWork = wintypes.RECT(0, 0, 2560, 1516)
            return True

        GetMonitorInfoW = _NativeFunction(monitor_info)

    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: User32())
    parameters = _windows_window._NcCalcSizeParams()
    parameters.rgrc[0] = wintypes.RECT(*proposed)
    _windows_window.constrain_maximized_client_area(1, ctypes.addressof(parameters))

    rect = parameters.rgrc[0]
    assert (rect.left, rect.top, rect.right, rect.bottom) == expected
