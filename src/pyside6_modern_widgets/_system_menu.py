"""Native system-window menu integration with a platform-safe fallback signal."""

from __future__ import annotations

import sys

SC_SIZE = 0xF000
SC_MOVE = 0xF010
SC_MINIMIZE = 0xF020
SC_MAXIMIZE = 0xF030
SC_CLOSE = 0xF060
SC_RESTORE = 0xF120


def show_native_system_menu(
    hwnd: int,
    screen_position: tuple[int, int],
    *,
    move_position: tuple[int, int] | None = None,
    is_minimized: bool,
    is_maximized: bool,
    can_resize: bool = True,
    can_minimize: bool = True,
    can_maximize: bool = True,
    can_close: bool = True,
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
        user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
        user32.SetCursorPos.restype = wintypes.BOOL
        user32.PostMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        user32.PostMessageW.restype = wintypes.BOOL

        window_handle = wintypes.HWND(hwnd)
        menu_handle = user32.GetSystemMenu(window_handle, False)
        if not menu_handle:
            return False

        mf_bycommand = 0x0000
        mf_enabled = 0x0000
        mf_grayed = 0x0001
        sc_size = SC_SIZE
        sc_move = SC_MOVE
        sc_minimize = SC_MINIMIZE
        sc_maximize = SC_MAXIMIZE
        sc_close = SC_CLOSE
        sc_restore = SC_RESTORE

        def set_enabled(command: int, enabled: bool) -> None:
            state = mf_enabled if enabled else mf_grayed
            user32.EnableMenuItem(menu_handle, command, mf_bycommand | state)

        is_normal = not is_minimized and not is_maximized
        set_enabled(sc_restore, not is_normal)
        set_enabled(sc_move, is_normal)
        set_enabled(sc_size, is_normal and can_resize)
        set_enabled(sc_minimize, can_minimize and not is_minimized)
        set_enabled(sc_maximize, can_maximize and not is_maximized)
        set_enabled(sc_close, can_close)

        tpm_rightbutton = 0x0002
        tpm_returncmd = 0x0100
        wm_null = 0x0000
        wm_syscommand = 0x0112
        user32.SetForegroundWindow(window_handle)
        ctypes.set_last_error(0)
        command = user32.TrackPopupMenu(
            menu_handle,
            tpm_rightbutton | tpm_returncmd,
            screen_position[0],
            screen_position[1],
            0,
            window_handle,
            None,
        )
        if not command and ctypes.get_last_error():
            return False
        if command:
            command_position = 0
            if command & 0xFFF0 == SC_MOVE and move_position is not None:
                user32.SetCursorPos(move_position[0], move_position[1])
                command |= 2  # HTCAPTION selects native mouse-driven movement.
                command_position = (move_position[0] & 0xFFFF) | ((move_position[1] & 0xFFFF) << 16)
            user32.PostMessageW(window_handle, wm_syscommand, command, command_position)
        user32.PostMessageW(window_handle, wm_null, 0, 0)
        return True
    except (AttributeError, OSError, TypeError, ValueError):
        return False
