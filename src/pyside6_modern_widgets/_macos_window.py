"""Native macOS title-bar integration for ModernWindow."""

from __future__ import annotations

import sys
from functools import lru_cache
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


MACOS_TRAFFIC_LIGHT_INSET = 78

_NS_WINDOW_STYLE_MASK_FULL_SIZE_CONTENT_VIEW = 1 << 15
_NS_WINDOW_TITLE_HIDDEN = 1


def uses_macos_native_title_bar() -> bool:
    """Return whether the active Qt backend can expose native macOS chrome."""
    return sys.platform == "darwin" and QApplication.platformName() == "cocoa"


def window_flags_with_chrome(
    flags: Qt.WindowType,
    *,
    native_macos_title_bar: bool | None = None,
) -> Qt.WindowType:
    """Select the native macOS frame or the portable frameless frame."""
    if native_macos_title_bar is None:
        native_macos_title_bar = uses_macos_native_title_bar()
    if native_macos_title_bar:
        return Qt.WindowType(int(flags) & ~int(Qt.WindowType.FramelessWindowHint))
    return flags | Qt.WindowType.FramelessWindowHint


class _ObjCBridge:
    def __init__(self) -> None:
        import ctypes
        import ctypes.util

        library_name = ctypes.util.find_library("objc") or "/usr/lib/libobjc.A.dylib"
        library = ctypes.CDLL(library_name)
        library.sel_registerName.argtypes = (ctypes.c_char_p,)
        library.sel_registerName.restype = ctypes.c_void_p
        library.objc_getClass.argtypes = (ctypes.c_char_p,)
        library.objc_getClass.restype = ctypes.c_void_p

        address = ctypes.cast(library.objc_msgSend, ctypes.c_void_p).value
        if address is None:
            raise OSError("objc_msgSend is unavailable")

        self._library = library
        self._send_id = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
        self._send_id_pointer = ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )(address)
        self._send_id_utf8 = ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p
        )(address)
        self._send_integer = ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p)(
            address
        )
        self._send_utf8 = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p)(
            address
        )
        self._send_void_bool = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool
        )(address)
        self._send_void_integer = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong
        )(address)
        self._send_void_pointer = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )(address)

    def selector(self, name: str) -> int:
        return int(self._library.sel_registerName(name.encode("ascii")))

    def class_named(self, name: str) -> int:
        return int(self._library.objc_getClass(name.encode("ascii")))

    def send_id(self, receiver: int, selector: str) -> int:
        return int(self._send_id(receiver, self.selector(selector)) or 0)

    def send_id_pointer(self, receiver: int, selector: str, value: int) -> int:
        return int(self._send_id_pointer(receiver, self.selector(selector), value) or 0)

    def send_id_utf8(self, receiver: int, selector: str, value: str) -> int:
        return int(
            self._send_id_utf8(receiver, self.selector(selector), value.encode("utf-8")) or 0
        )

    def send_integer(self, receiver: int, selector: str) -> int:
        return int(self._send_integer(receiver, self.selector(selector)))

    def send_utf8(self, receiver: int, selector: str) -> str | None:
        value = self._send_utf8(receiver, self.selector(selector))
        return value.decode("utf-8") if value else None

    def send_void_bool(self, receiver: int, selector: str, value: bool) -> None:
        self._send_void_bool(receiver, self.selector(selector), value)

    def send_void_integer(self, receiver: int, selector: str, value: int) -> None:
        self._send_void_integer(receiver, self.selector(selector), value)

    def send_void_pointer(self, receiver: int, selector: str, value: int = 0) -> None:
        self._send_void_pointer(receiver, self.selector(selector), value)


@lru_cache(maxsize=1)
def _objc_bridge() -> _ObjCBridge:
    return _ObjCBridge()


def _native_window(widget: QWidget, bridge: _ObjCBridge) -> int:
    view = int(widget.winId())
    return bridge.send_id(view, "window") if view else 0


def configure_macos_native_title_bar(widget: QWidget) -> bool:
    """Make a native title bar transparent while retaining its traffic lights."""
    if not uses_macos_native_title_bar() or not widget.isWindow():
        return False
    try:
        bridge = _objc_bridge()
        window = _native_window(widget, bridge)
        if not window:
            return False
        style_mask = bridge.send_integer(window, "styleMask")
        bridge.send_void_integer(
            window,
            "setStyleMask:",
            style_mask | _NS_WINDOW_STYLE_MASK_FULL_SIZE_CONTENT_VIEW,
        )
        bridge.send_void_bool(window, "setTitlebarAppearsTransparent:", True)
        bridge.send_void_integer(window, "setTitleVisibility:", _NS_WINDOW_TITLE_HIDDEN)
        return True
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def perform_macos_title_bar_double_click(widget: QWidget) -> bool:
    """Apply the user's macOS title-bar double-click preference."""
    if not uses_macos_native_title_bar() or not widget.isWindow():
        return False
    try:
        bridge = _objc_bridge()
        window = _native_window(widget, bridge)
        if not window:
            return False

        defaults_class = bridge.class_named("NSUserDefaults")
        string_class = bridge.class_named("NSString")
        defaults = bridge.send_id(defaults_class, "standardUserDefaults")
        key = bridge.send_id_utf8(string_class, "stringWithUTF8String:", "AppleActionOnDoubleClick")
        value = bridge.send_id_pointer(defaults, "stringForKey:", key)
        action = bridge.send_utf8(value, "UTF8String") if value else None
        action = (action or "Maximize").casefold()

        flags = widget.windowFlags()
        if action == "minimize":
            if flags & Qt.WindowType.WindowMinimizeButtonHint:
                bridge.send_void_pointer(window, "miniaturize:")
        elif (
            action not in {"none", "do nothing"} and flags & Qt.WindowType.WindowMaximizeButtonHint
        ):
            bridge.send_void_pointer(window, "performZoom:")
        return True
    except (AttributeError, OSError, TypeError, ValueError):
        return False
