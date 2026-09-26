from __future__ import annotations

import ctypes
from ctypes import wintypes
from types import SimpleNamespace

import pytest

from pyside6_modern_widgets import _windows_window


class _NativeFunction:
    def __init__(self, callback) -> None:
        self._callback = callback
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self._callback(*args)


@pytest.mark.parametrize("resize", [False, True])
def test_window_position_constraints_preserve_native_rounding_and_other_fields(resize):
    position = _windows_window._WindowPosition(123, 456, -100, 200, 415, 649, 0x0014)

    def constrain(size):
        assert size == (277, 433)
        return (300, 500) if resize else size

    assert _windows_window.constrain_window_position(ctypes.addressof(position), 1.5, constrain)
    assert (position.cx, position.cy) == ((450, 750) if resize else (415, 649))
    assert (position.hwnd, position.hwndInsertAfter, position.x, position.y) == (
        123,
        456,
        -100,
        200,
    )
    assert position.flags == 0x0114


def test_window_position_without_resize_does_not_run_layout_constraints():
    position = _windows_window._WindowPosition(123, 456, -100, 200, 0, 0, 0x0015)

    def unexpected_layout(_):
        pytest.fail("SWP_NOSIZE does not contain a proposed size")

    assert not _windows_window.constrain_window_position(
        ctypes.addressof(position), 1.25, unexpected_layout
    )
    assert (position.cx, position.cy, position.flags) == (0, 0, 0x0015)


@pytest.mark.parametrize("rounded", [False, True])
@pytest.mark.parametrize("result", [0, -1, "error"])
def test_shared_corner_preference_reports_dwm_success(monkeypatch, rounded, result):
    calls = []

    def set_attribute(hwnd, attribute, value, size):
        preference = ctypes.cast(value, ctypes.POINTER(ctypes.c_int)).contents.value
        calls.append((hwnd.value, attribute, preference, size))
        if result == "error":
            raise OSError("DWM unavailable")
        return result

    monkeypatch.setattr(
        ctypes,
        "windll",
        SimpleNamespace(
            dwmapi=SimpleNamespace(DwmSetWindowAttribute=_NativeFunction(set_attribute)),
        ),
        raising=False,
    )
    assert _windows_window.set_window_corner_preference(12345, rounded=rounded) == (result == 0)
    assert calls == [(12345, 33, 2 if rounded else 1, ctypes.sizeof(ctypes.c_int))]


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


def test_restore_native_window_uses_show_window_restore(monkeypatch) -> None:
    calls = []

    class User32:
        ShowWindow = _NativeFunction(lambda hwnd, command: calls.append((hwnd.value, command)))

    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: User32())

    _windows_window.restore_native_window(12345)

    assert calls == [(12345, 9)]


def test_hidden_native_restore_preserves_visibility_and_other_style_bits(monkeypatch) -> None:
    style = _windows_window.WS_MAXIMIZE | _windows_window.WS_CAPTION | 0x00080000
    calls = []

    class User32:
        GetWindowLongPtrW = _NativeFunction(lambda hwnd, index: style)
        SetWindowLongPtrW = _NativeFunction(
            lambda hwnd, index, updated: calls.append((hwnd.value, index, updated))
        )

    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: User32())
    _windows_window.restore_native_window(12345, visible=False)
    assert calls == [(12345, _windows_window.GWL_STYLE, style & ~_windows_window.WS_MAXIMIZE)]


@pytest.mark.parametrize("on_top", [True, False])
@pytest.mark.parametrize("succeeded", [True, False])
def test_topmost_changes_only_native_z_order(monkeypatch, on_top, succeeded) -> None:
    calls = []

    def set_position(hwnd, after, x, y, width, height, flags):
        calls.append((hwnd.value, after.value, x, y, width, height, flags))
        return succeeded

    class User32:
        SetWindowPos = _NativeFunction(set_position)

    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: User32())

    assert _windows_window.set_window_topmost(12345, on_top) is succeeded
    assert calls == [(12345, wintypes.HWND(-1 if on_top else -2).value, 0, 0, 0, 0, 0x13)]


def test_bring_window_to_front_keeps_normal_z_order_band(monkeypatch) -> None:
    calls = []

    def set_position(hwnd, after, x, y, width, height, flags):
        calls.append((hwnd.value, after.value, x, y, width, height, flags))
        return True

    class User32:
        SetWindowPos = _NativeFunction(set_position)
        SetForegroundWindow = _NativeFunction(lambda hwnd: calls.append(("activate", hwnd.value)))
        GetForegroundWindow = _NativeFunction(lambda: 12345)
        IsWindow = _NativeFunction(lambda hwnd: True)

    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: User32())

    assert _windows_window.bring_window_to_front(12345)
    assert calls == [(12345, None, 0, 0, 0, 0, 0x13), ("activate", 12345)]


@pytest.mark.parametrize("fallback", ["success", "denied", "error", "attach_denied"])
def test_foreground_fallback_always_releases_shared_input_queue(monkeypatch, fallback):
    calls = []
    foreground = [67890]
    attached = [False]

    def activate(hwnd):
        calls.append(("activate", hwnd.value))
        if attached[0]:
            if fallback == "error":
                raise OSError("window closed during activation")
            if fallback == "success":
                foreground[0] = hwnd.value
        return foreground[0] == hwnd.value

    def attach(current, other, enabled):
        calls.append(("attach", current, other, enabled))
        if fallback == "attach_denied":
            return False
        attached[0] = enabled
        return True

    user32 = SimpleNamespace(
        IsWindow=_NativeFunction(lambda hwnd: True),
        SetWindowPos=_NativeFunction(lambda *args: True),
        SetForegroundWindow=_NativeFunction(activate),
        GetForegroundWindow=_NativeFunction(lambda: foreground[0]),
        GetWindowThreadProcessId=_NativeFunction(lambda *args: 20),
        AttachThreadInput=_NativeFunction(attach),
    )
    kernel32 = SimpleNamespace(GetCurrentThreadId=_NativeFunction(lambda: 10))
    monkeypatch.setattr(
        ctypes, "WinDLL", lambda name, **_: user32 if name == "user32" else kernel32
    )
    assert _windows_window.bring_window_to_front(12345) == (fallback == "success")
    assert not attached[0]
    assert calls[:2] == [("activate", 12345), ("attach", 10, 20, True)]
    if fallback != "attach_denied":
        assert calls[-1] == ("attach", 10, 20, False)


@pytest.mark.parametrize("hit_root", [12345, 67890])
def test_window_is_at_cursor_uses_native_hit_test(monkeypatch, hit_root) -> None:
    calls = []

    class User32:
        WindowFromPoint = _NativeFunction(lambda point: calls.append((point.x, point.y)) or 11111)
        GetAncestor = _NativeFunction(lambda hit, mode: hit_root)

    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: User32())
    monkeypatch.setattr(_windows_window, "_cursor_screen_position", lambda: (-500, 700))

    assert _windows_window.window_is_at_cursor(12345) is (hit_root == 12345)
    assert calls == [(-500, 700)]


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


@pytest.mark.parametrize("scale", [1.0, 1.25, 1.75, 2.0])
def test_dpi_constraints_scale_both_axes_and_preserve_monitor_bounds(scale) -> None:
    info = _windows_window._MinMaxInfo()
    info.ptMaxSize = wintypes.POINT(1920, 1032)
    info.ptMaxPosition = wintypes.POINT(-1920, 0)
    _windows_window.set_size_constraints(ctypes.addressof(info), (477, 165), (1000, 700), scale)

    assert (info.ptMinTrackSize.x, info.ptMinTrackSize.y) == (
        int(477 * scale + 0.5),
        int(165 * scale + 0.5),
    )
    assert (info.ptMaxTrackSize.x, info.ptMaxTrackSize.y) == (
        int(1000 * scale + 0.5),
        int(700 * scale + 0.5),
    )
    assert (info.ptMaxSize.x, info.ptMaxSize.y) == (1920, 1032)
    assert (info.ptMaxPosition.x, info.ptMaxPosition.y) == (-1920, 0)


def test_unconstrained_dimensions_keep_windows_defaults() -> None:
    info = _windows_window._MinMaxInfo()
    info.ptMinTrackSize = wintypes.POINT(120, 30)
    info.ptMaxTrackSize = wintypes.POINT(4480, 1600)
    _windows_window.set_size_constraints(ctypes.addressof(info), (0, 200), (16777215, 200), 1.75)
    assert (info.ptMinTrackSize.x, info.ptMinTrackSize.y) == (120, 350)
    assert (info.ptMaxTrackSize.x, info.ptMaxTrackSize.y) == (4480, 350)


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
