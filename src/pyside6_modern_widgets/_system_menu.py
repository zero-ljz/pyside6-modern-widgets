"""Native system-window menu integration with a platform-safe fallback signal."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QPoint


def show_native_system_menu(
    hwnd: int,
    client_position: QPoint,
    *,
    is_minimized: bool,
    is_maximized: bool,
) -> bool:
    """Show the owning window's native system menu when the platform provides one."""
    if sys.platform != "win32":
        return False

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetSystemMenu.argtypes = (wintypes.HWND, wintypes.BOOL)
        user32.GetSystemMenu.restype = wintypes.HMENU
        user32.EnableMenuItem.argtypes = (wintypes.HMENU, wintypes.UINT, wintypes.UINT)
        user32.EnableMenuItem.restype = wintypes.BOOL
        user32.TrackPopupMenu.argtypes = (
            wintypes.HMENU,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            ctypes.c_void_p,
        )
        user32.TrackPopupMenu.restype = wintypes.UINT
        user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
        user32.SetForegroundWindow.restype = wintypes.BOOL
        user32.GetDpiForWindow.argtypes = (wintypes.HWND,)
        user32.GetDpiForWindow.restype = wintypes.UINT
        user32.ClientToScreen.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.POINT))
        user32.ClientToScreen.restype = wintypes.BOOL
        user32.PostMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        user32.PostMessageW.restype = wintypes.BOOL

        window_handle = wintypes.HWND(hwnd)
        # Qt can leave a stale system-menu handle after applying frameless/layered styles.
        # Reverting first asks Windows to create a fresh standard menu for this HWND.
        user32.GetSystemMenu(window_handle, True)
        menu_handle = user32.GetSystemMenu(window_handle, False)
        if not menu_handle:
            return False

        dpi = user32.GetDpiForWindow(window_handle) or 96
        scale = dpi / 96
        screen_position = wintypes.POINT(
            round(client_position.x() * scale),
            round(client_position.y() * scale),
        )
        if not user32.ClientToScreen(window_handle, ctypes.byref(screen_position)):
            return False

        mf_bycommand = 0x0000
        mf_enabled = 0x0000
        mf_grayed = 0x0001
        sc_size = 0xF000
        sc_move = 0xF010
        sc_minimize = 0xF020
        sc_maximize = 0xF030
        sc_restore = 0xF120

        def set_enabled(command: int, enabled: bool) -> None:
            state = mf_enabled if enabled else mf_grayed
            user32.EnableMenuItem(menu_handle, command, mf_bycommand | state)

        is_normal = not is_minimized and not is_maximized
        set_enabled(sc_restore, not is_normal)
        set_enabled(sc_move, is_normal)
        set_enabled(sc_size, is_normal)
        set_enabled(sc_minimize, not is_minimized)
        set_enabled(sc_maximize, not is_maximized)

        tpm_rightbutton = 0x0002
        tpm_returncmd = 0x0100
        wm_null = 0x0000
        wm_syscommand = 0x0112
        user32.SetForegroundWindow(window_handle)
        ctypes.set_last_error(0)
        command = user32.TrackPopupMenu(
            menu_handle,
            tpm_rightbutton | tpm_returncmd,
            screen_position.x,
            screen_position.y,
            0,
            window_handle,
            None,
        )
        if not command and ctypes.get_last_error():
            return False
        if command:
            user32.PostMessageW(window_handle, wm_syscommand, command, 0)
        user32.PostMessageW(window_handle, wm_null, 0, 0)
        return True
    except (AttributeError, OSError, TypeError, ValueError):
        return False
