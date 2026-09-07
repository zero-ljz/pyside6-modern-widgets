"""Small Win32 helpers for native frameless-window behavior."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

GWL_STYLE = -16

WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000

WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084
WM_NCMOUSEMOVE = 0x00A0
WM_NCLBUTTONDOWN = 0x00A1
WM_NCLBUTTONUP = 0x00A2
WM_NCLBUTTONDBLCLK = 0x00A3
WM_NCRBUTTONUP = 0x00A5
WM_MOUSEMOVE = 0x0200
WM_LBUTTONUP = 0x0202
WM_CAPTURECHANGED = 0x0215
WM_ENTERSIZEMOVE = 0x0231
WM_EXITSIZEMOVE = 0x0232
WM_NCMOUSELEAVE = 0x02A2

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

_RESIZE_COMMANDS = {
    HTLEFT: 1,
    HTRIGHT: 2,
    HTTOP: 3,
    HTTOPLEFT: 4,
    HTTOPRIGHT: 5,
    HTBOTTOM: 6,
    HTBOTTOMLEFT: 7,
    HTBOTTOMRIGHT: 8,
}


@dataclass(frozen=True)
class WindowsMessage:
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


class _Margins(ctypes.Structure):
    _fields_ = (
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    )


def read_message(address: int) -> WindowsMessage:
    message = ctypes.cast(address, ctypes.POINTER(wintypes.MSG)).contents
    return WindowsMessage(
        message=int(message.message),
        w_param=int(message.wParam),
        l_param=int(message.lParam),
    )


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


def start_system_move_or_resize(hwnd: int, hit_test: int) -> bool:
    """Enter the native Windows move/resize loop for a non-client hit target."""
    if hit_test == HTCAPTION:
        command = 0xF010 | HTCAPTION  # SC_MOVE
    elif hit_test in _RESIZE_COMMANDS:
        command = 0xF000 | _RESIZE_COMMANDS[hit_test]  # SC_SIZE
    else:
        return False

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.ReleaseCapture.argtypes = ()
        user32.ReleaseCapture.restype = wintypes.BOOL
        user32.PostMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        user32.PostMessageW.restype = wintypes.BOOL
        user32.ReleaseCapture()
        return bool(user32.PostMessageW(wintypes.HWND(hwnd), 0x0112, command, 0))
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
        parameters.rgrc[0] = monitor_info.rcWork
    except (AttributeError, OSError, TypeError, ValueError):
        return


def client_position_from_l_param(
    hwnd: int,
    l_param: int,
    logical_width: int,
    logical_height: int,
) -> tuple[float, float] | None:
    """Convert the physical screen position in LPARAM to Qt client coordinates."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    user32.GetClientRect.restype = wintypes.BOOL
    user32.ClientToScreen.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.POINT))
    user32.ClientToScreen.restype = wintypes.BOOL

    rect = wintypes.RECT()
    origin = wintypes.POINT()
    window_handle = wintypes.HWND(hwnd)
    if not user32.GetClientRect(window_handle, ctypes.byref(rect)) or not user32.ClientToScreen(
        window_handle, ctypes.byref(origin)
    ):
        return None

    physical_width = rect.right - rect.left
    physical_height = rect.bottom - rect.top
    if physical_width <= 0 or physical_height <= 0:
        return None

    screen_x = ctypes.c_short(l_param & 0xFFFF).value
    screen_y = ctypes.c_short((l_param >> 16) & 0xFFFF).value
    return (
        (screen_x - origin.x) * logical_width / physical_width,
        (screen_y - origin.y) * logical_height / physical_height,
    )


def set_native_frame(hwnd: int, enabled: bool) -> bool:
    """Expose standard resizable-window styles without drawing native chrome."""
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
        native_frame = WS_CAPTION | WS_THICKFRAME
        updated_style = style | native_frame if enabled else style & ~native_frame
        if updated_style == style:
            return True

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


def set_native_shadow(hwnd: int, enabled: bool) -> bool:
    """Ask DWM to render the standard shadow around a frameless window."""
    try:
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        dwmapi.DwmSetWindowAttribute.argtypes = (
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        )
        dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
        dwmapi.DwmExtendFrameIntoClientArea.argtypes = (
            wintypes.HWND,
            ctypes.POINTER(_Margins),
        )
        dwmapi.DwmExtendFrameIntoClientArea.restype = ctypes.c_long

        policy = ctypes.c_int(2 if enabled else 1)  # DWMNCRP_ENABLED / DWMNCRP_DISABLED
        policy_result = dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            2,  # DWMWA_NCRENDERING_POLICY
            ctypes.byref(policy),
            ctypes.sizeof(policy),
        )
        extent = 1 if enabled else 0
        margins = _Margins(extent, extent, extent, extent)
        frame_result = dwmapi.DwmExtendFrameIntoClientArea(
            wintypes.HWND(hwnd), ctypes.byref(margins)
        )
        return policy_result >= 0 and frame_result >= 0
    except (AttributeError, OSError, TypeError, ValueError):
        return False
