"""Small Win32 helpers for native frameless-window behavior."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

GWL_STYLE = -16

WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000

WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084
WM_NCMOUSEMOVE = 0x00A0
WM_NCLBUTTONDOWN = 0x00A1
WM_NCLBUTTONUP = 0x00A2
WM_NCLBUTTONDBLCLK = 0x00A3
WM_NCRBUTTONUP = 0x00A5
WM_SYSCOMMAND = 0x0112
WM_DISPLAYCHANGE = 0x007E
WM_DPICHANGED = 0x02E0
WM_GETMINMAXINFO = 0x0024
WM_MOUSEMOVE = 0x0200
WM_LBUTTONUP = 0x0202
WM_CAPTURECHANGED = 0x0215
WM_ENTERSIZEMOVE = 0x0231
WM_EXITSIZEMOVE = 0x0232
WM_NCMOUSELEAVE = 0x02A2

HTTRANSPARENT = -1
HTCLIENT = 1
HTCAPTION = 2
HTMAXBUTTON = 9
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17


@dataclass(frozen=True)
class WindowsMessage:
    hwnd: int
    message: int
    w_param: int
    l_param: int


class _TrackMouseEvent(ctypes.Structure):
    _fields_ = (
        ("cbSize", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("hwndTrack", wintypes.HWND),
        ("dwHoverTime", wintypes.DWORD),
    )


class _WindowPosition(ctypes.Structure):
    _fields_ = (
        ("hwnd", wintypes.HWND),
        ("hwndInsertAfter", wintypes.HWND),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("cx", ctypes.c_int),
        ("cy", ctypes.c_int),
        ("flags", wintypes.UINT),
    )


class _NcCalcSizeParams(ctypes.Structure):
    _fields_ = (("rgrc", wintypes.RECT * 3), ("lppos", ctypes.POINTER(_WindowPosition)))


class _MonitorInfo(ctypes.Structure):
    _fields_ = (
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    )


class _MinMaxInfo(ctypes.Structure):
    _fields_ = (
        ("ptReserved", wintypes.POINT),
        ("ptMaxSize", wintypes.POINT),
        ("ptMaxPosition", wintypes.POINT),
        ("ptMinTrackSize", wintypes.POINT),
        ("ptMaxTrackSize", wintypes.POINT),
    )


def window_dpi(hwnd: int) -> int | None:
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetDpiForWindow.argtypes = (wintypes.HWND,)
        user32.GetDpiForWindow.restype = wintypes.UINT
        return int(user32.GetDpiForWindow(wintypes.HWND(hwnd))) or None
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def set_size_constraints(
    l_param: int,
    minimum: tuple[int, int],
    maximum: tuple[int, int],
    scale: float,
) -> None:
    """Set frameless tracking bounds in physical pixels, preserving work-area fields."""
    info = ctypes.cast(l_param, ctypes.POINTER(_MinMaxInfo)).contents
    for axis, lower, upper in zip(("x", "y"), minimum, maximum):
        if lower > 0:
            setattr(info.ptMinTrackSize, axis, int(lower * scale + 0.5))
        if upper < 16777215:
            setattr(info.ptMaxTrackSize, axis, int(upper * scale + 0.5))


def read_message(address: int) -> WindowsMessage:
    message = ctypes.cast(address, ctypes.POINTER(wintypes.MSG)).contents
    return WindowsMessage(
        hwnd=int(message.hWnd or 0),
        message=int(message.message),
        w_param=int(message.wParam),
        l_param=int(message.lParam),
    )


def is_window_maximized(hwnd: int) -> bool:
    """Return the Win32 maximize state when Qt's state has not caught up yet."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.IsZoomed.argtypes = (wintypes.HWND,)
        user32.IsZoomed.restype = wintypes.BOOL
        return bool(user32.IsZoomed(wintypes.HWND(hwnd)))
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def track_non_client_mouse_leave(hwnd: int) -> None:
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.TrackMouseEvent.argtypes = (ctypes.POINTER(_TrackMouseEvent),)
        user32.TrackMouseEvent.restype = wintypes.BOOL
        request = _TrackMouseEvent(
            ctypes.sizeof(_TrackMouseEvent),
            0x00000002 | 0x00000010,  # TME_LEAVE | TME_NONCLIENT
            wintypes.HWND(hwnd),
            0,
        )
        user32.TrackMouseEvent(ctypes.byref(request))
    except (AttributeError, OSError, TypeError, ValueError):
        return


def set_mouse_capture(hwnd: int, captured: bool) -> None:
    """Capture or release mouse input for a custom non-client interaction."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        if captured:
            user32.SetCapture.argtypes = (wintypes.HWND,)
            user32.SetCapture.restype = wintypes.HWND
            user32.SetCapture(wintypes.HWND(hwnd))
        else:
            user32.ReleaseCapture.argtypes = ()
            user32.ReleaseCapture.restype = wintypes.BOOL
            user32.ReleaseCapture()
    except (AttributeError, OSError, TypeError, ValueError):
        return


def start_system_move(hwnd: int) -> bool:
    """Start a Win32 caption move after the current native message returns."""
    position = _cursor_screen_position()
    if position is None:
        return False
    # SC_MOVE | HTCAPTION is a mouse-initiated move. Its LPARAM must carry
    # physical screen coordinates, just like WM_NCLBUTTONDOWN. A zero value
    # can make Windows reposition the cursor when it takes over the drag.
    l_param = (position[0] & 0xFFFF) | ((position[1] & 0xFFFF) << 16)
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
        user32.SetForegroundWindow.restype = wintypes.BOOL
        user32.ReleaseCapture.argtypes = ()
        user32.ReleaseCapture.restype = wintypes.BOOL
        user32.PostMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        user32.PostMessageW.restype = wintypes.BOOL

        window_handle = wintypes.HWND(hwnd)
        user32.SetForegroundWindow(window_handle)
        user32.ReleaseCapture()
        return bool(user32.PostMessageW(window_handle, 0x0112, 0xF010 | HTCAPTION, l_param))
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def constrain_maximized_client_area(hwnd: int, l_param: int) -> None:
    """Keep a borderless maximized client area inside the monitor work area."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.IsZoomed.argtypes = (wintypes.HWND,)
        user32.IsZoomed.restype = wintypes.BOOL
        if not user32.IsZoomed(wintypes.HWND(hwnd)):
            return

        user32.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
        user32.MonitorFromWindow.restype = wintypes.HMONITOR
        user32.GetMonitorInfoW.argtypes = (wintypes.HMONITOR, ctypes.POINTER(_MonitorInfo))
        user32.GetMonitorInfoW.restype = wintypes.BOOL
        monitor = user32.MonitorFromWindow(wintypes.HWND(hwnd), 0x00000002)
        monitor_info = _MonitorInfo(cbSize=ctypes.sizeof(_MonitorInfo))
        if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info)):
            return

        parameters = ctypes.cast(l_param, ctypes.POINTER(_NcCalcSizeParams)).contents
        proposed = parameters.rgrc[0]
        work = monitor_info.rcWork
        # IsZoomed can still describe the old state during a restore. Only trim
        # an actual maximized frame; never expand a smaller proposed client area.
        if (
            proposed.left <= work.left
            and proposed.top <= work.top
            and proposed.right >= work.right
            and proposed.bottom >= work.bottom
        ):
            parameters.rgrc[0] = work
    except (AttributeError, OSError, TypeError, ValueError):
        return


def client_position_from_l_param(
    hwnd: int,
    l_param: int,
    logical_width: int,
    logical_height: int,
) -> tuple[float, float] | None:
    """Convert the physical screen position in LPARAM to Qt client coordinates."""
    screen_position = screen_position_from_l_param(l_param)
    client_metrics = _client_metrics(hwnd)
    if client_metrics is None:
        return None
    origin_x, origin_y, physical_width, physical_height = client_metrics
    if physical_width <= 0 or physical_height <= 0:
        return None
    return (
        (screen_position[0] - origin_x) * logical_width / physical_width,
        (screen_position[1] - origin_y) * logical_height / physical_height,
    )


def screen_position_from_l_param(l_param: int) -> tuple[int, int]:
    """Extract signed physical screen coordinates from a native LPARAM."""
    packed_position = (
        ctypes.c_short(l_param & 0xFFFF).value,
        ctypes.c_short((l_param >> 16) & 0xFFFF).value,
    )
    cursor_position = _cursor_screen_position()
    if cursor_position is not None and (
        cursor_position[0] & 0xFFFF == l_param & 0xFFFF
        and cursor_position[1] & 0xFFFF == (l_param >> 16) & 0xFFFF
    ):
        return cursor_position
    return packed_position


def _cursor_screen_position() -> tuple[int, int] | None:
    """Return full-width cursor coordinates when Win32 is available."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetCursorPos.argtypes = (ctypes.POINTER(wintypes.POINT),)
        user32.GetCursorPos.restype = wintypes.BOOL
        position = wintypes.POINT()
        if user32.GetCursorPos(ctypes.byref(position)):
            return position.x, position.y
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    return None


def screen_position_from_client(
    hwnd: int,
    logical_x: float,
    logical_y: float,
    logical_width: int,
    logical_height: int,
) -> tuple[int, int] | None:
    """Map Qt client coordinates to Win32 physical screen coordinates."""
    client_metrics = _client_metrics(hwnd)
    if client_metrics is None or logical_width <= 0 or logical_height <= 0:
        return None
    origin_x, origin_y, physical_width, physical_height = client_metrics
    return (
        origin_x + round(logical_x * physical_width / logical_width),
        origin_y + round(logical_y * physical_height / logical_height),
    )


def _client_metrics(hwnd: int) -> tuple[int, int, int, int] | None:
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
        user32.GetClientRect.restype = wintypes.BOOL
        user32.ClientToScreen.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.POINT))
        user32.ClientToScreen.restype = wintypes.BOOL

        rect = wintypes.RECT()
        origin = wintypes.POINT()
        window_handle = wintypes.HWND(hwnd)
        if not user32.GetClientRect(window_handle, ctypes.byref(rect)):
            return None
        if not user32.ClientToScreen(window_handle, ctypes.byref(origin)):
            return None
        return (
            origin.x,
            origin.y,
            rect.right - rect.left,
            rect.bottom - rect.top,
        )
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def set_native_frame(
    hwnd: int,
    enabled: bool,
    *,
    resizable: bool = True,
    system_menu: bool = True,
    minimizable: bool = True,
    maximizable: bool = True,
    force_refresh: bool = False,
) -> bool:
    """Synchronize the native frame styles that drive Windows window behavior."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int)
        user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.SetWindowLongPtrW.argtypes = (
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_ssize_t,
        )
        user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.SetWindowPos.argtypes = (
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        )
        user32.SetWindowPos.restype = wintypes.BOOL

        window_handle = wintypes.HWND(hwnd)
        style = int(user32.GetWindowLongPtrW(window_handle, GWL_STYLE))
        if enabled:
            updated_style = style | WS_CAPTION
            capabilities = (
                (WS_THICKFRAME, resizable),
                (WS_SYSMENU, system_menu),
                (WS_MINIMIZEBOX, minimizable),
                (WS_MAXIMIZEBOX, maximizable),
            )
            for style_bit, active in capabilities:
                if active:
                    updated_style |= style_bit
                else:
                    updated_style &= ~style_bit
        else:
            updated_style = style & ~(
                WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX
            )
        if updated_style == style and not force_refresh:
            return True

        if updated_style != style:
            ctypes.set_last_error(0)
            previous_style = user32.SetWindowLongPtrW(window_handle, GWL_STYLE, updated_style)
            if not previous_style and ctypes.get_last_error():
                return False

        swp_nomove = 0x0002
        swp_nosize = 0x0001
        swp_nozorder = 0x0004
        swp_noactivate = 0x0010
        swp_framechanged = 0x0020
        return bool(
            user32.SetWindowPos(
                window_handle,
                wintypes.HWND(),
                0,
                0,
                0,
                0,
                swp_nomove | swp_nosize | swp_nozorder | swp_noactivate | swp_framechanged,
            )
        )
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def redraw_native_window(hwnd: int) -> None:
    """Invalidate a complete Win32 window after DPI or display metric changes."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.RedrawWindow.argtypes = (
            wintypes.HWND,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.UINT,
        )
        user32.RedrawWindow.restype = wintypes.BOOL
        rdw_invalidate = 0x0001
        rdw_erase = 0x0004
        rdw_allchildren = 0x0080
        rdw_updatenow = 0x0100
        rdw_erasenow = 0x0200
        rdw_frame = 0x0400
        user32.RedrawWindow(
            wintypes.HWND(hwnd),
            None,
            None,
            rdw_invalidate | rdw_erase | rdw_allchildren | rdw_updatenow | rdw_erasenow | rdw_frame,
        )
    except (AttributeError, OSError, TypeError, ValueError):
        return
