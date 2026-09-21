"""Native macOS title-bar integration for ModernWindow."""

from __future__ import annotations

import ctypes
import platform
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


class _NSPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class _NSSize(ctypes.Structure):
    _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]


class _NSRect(ctypes.Structure):
    _fields_ = [("origin", _NSPoint), ("size", _NSSize)]


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
        self._send_id_integer = ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long
        )(address)
        self._send_bool = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(address)
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
        self._send_void_point = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, _NSPoint)(
            address
        )

        # Intel macOS returns NSRect through objc_msgSend_stret; Apple Silicon
        # uses the ordinary objc_msgSend ABI for the same structure.
        if platform.machine().lower() in {"x86_64", "amd64"}:
            stret_address = ctypes.cast(library.objc_msgSend_stret, ctypes.c_void_p).value
            if stret_address is None:
                raise OSError("objc_msgSend_stret is unavailable")
            self._send_rect = ctypes.CFUNCTYPE(
                None,
                ctypes.POINTER(_NSRect),
                ctypes.c_void_p,
                ctypes.c_void_p,
            )(stret_address)
            self._rect_uses_stret = True
        else:
            self._send_rect = ctypes.CFUNCTYPE(
                _NSRect,
                ctypes.c_void_p,
                ctypes.c_void_p,
            )(address)
            self._rect_uses_stret = False

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

    def send_id_integer(self, receiver: int, selector: str, value: int) -> int:
        return int(self._send_id_integer(receiver, self.selector(selector), value) or 0)

    def send_bool(self, receiver: int, selector: str) -> bool:
        return bool(self._send_bool(receiver, self.selector(selector)))

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

    def send_rect(self, receiver: int, selector: str) -> _NSRect:
        if self._rect_uses_stret:
            value = _NSRect()
            self._send_rect(ctypes.byref(value), receiver, self.selector(selector))
            return value
        return self._send_rect(receiver, self.selector(selector))

    def send_void_point(self, receiver: int, selector: str, value: _NSPoint) -> None:
        self._send_void_point(receiver, self.selector(selector), value)


@lru_cache(maxsize=1)
def _objc_bridge() -> _ObjCBridge:
    return _ObjCBridge()


def _native_window(widget: QWidget, bridge: _ObjCBridge) -> int:
    view = int(widget.winId())
    return bridge.send_id(view, "window") if view else 0


def _position_traffic_lights(
    window: int,
    bridge: _ObjCBridge,
    title_bar_height: int,
) -> None:
    buttons = [
        bridge.send_id_integer(window, "standardWindowButton:", button_type)
        for button_type in range(3)
    ]
    buttons = [button for button in buttons if button]
    if not buttons:
        return

    frames = [bridge.send_rect(button, "frame") for button in buttons]
    first_x = frames[0].origin.x
    first_padding = max(0.0, (title_bar_height - frames[0].size.height) / 2.0)
    for button, frame in zip(buttons, frames, strict=True):
        superview = bridge.send_id(button, "superview")
        if not superview:
            continue
        bounds = bridge.send_rect(superview, "bounds")
        vertical_padding = max(0.0, (title_bar_height - frame.size.height) / 2.0)
        if bridge.send_bool(superview, "isFlipped"):
            y = bounds.origin.y + vertical_padding
        else:
            y = bounds.origin.y + bounds.size.height - vertical_padding - frame.size.height
        x = bounds.origin.x + first_padding + frame.origin.x - first_x
        bridge.send_void_point(button, "setFrameOrigin:", _NSPoint(x, y))


def configure_macos_native_title_bar(widget: QWidget, *, title_bar_height: int = 0) -> bool:
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
        if title_bar_height > 0:
            _position_traffic_lights(window, bridge, title_bar_height)
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
