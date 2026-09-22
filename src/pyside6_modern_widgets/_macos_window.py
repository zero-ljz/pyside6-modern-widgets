"""Native macOS title-bar integration for modern windows and dialogs."""

from __future__ import annotations

import ctypes
import logging
import platform
import sys
from collections.abc import Callable
from functools import lru_cache
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
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
        self._send_void = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)(address)
        self._send_void_point = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, _NSPoint)(
            address
        )
        self._send_void_size = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, _NSSize)(
            address
        )
        self._add_observer = ctypes.CFUNCTYPE(
            None,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )(address)
        self._notification_handlers: dict[int, Callable[[], None]] = {}
        self._observer_class = 0

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

    def send_void(self, receiver: int, selector: str) -> None:
        self._send_void(receiver, self.selector(selector))

    def send_rect(self, receiver: int, selector: str) -> _NSRect:
        if self._rect_uses_stret:
            value = _NSRect()
            self._send_rect(ctypes.byref(value), receiver, self.selector(selector))
            return value
        return self._send_rect(receiver, self.selector(selector))

    def send_void_point(self, receiver: int, selector: str, value: _NSPoint) -> None:
        self._send_void_point(receiver, self.selector(selector), value)

    def send_void_size(self, receiver: int, selector: str, value: _NSSize) -> None:
        self._send_void_size(receiver, self.selector(selector), value)

    def create_observer(self, callback: Callable[[], None]) -> int:
        """Own a small NSObject receiver; do not replace AppKit or Qt delegates."""
        if not self._observer_class:
            library = self._library
            library.objc_allocateClassPair.argtypes = (
                ctypes.c_void_p,
                ctypes.c_char_p,
                ctypes.c_size_t,
            )
            library.objc_allocateClassPair.restype = ctypes.c_void_p
            library.class_addMethod.argtypes = (
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_char_p,
            )
            library.class_addMethod.restype = ctypes.c_bool
            library.objc_registerClassPair.argtypes = (ctypes.c_void_p,)
            library.objc_registerClassPair.restype = None
            observer_class = library.objc_allocateClassPair(
                self.class_named("NSObject"), b"PMWTrafficLightObserver", 0
            )
            if not observer_class:
                raise OSError("Unable to register the traffic-light observer")

            @ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
            def receive(receiver, _selector, _notification):
                callback = self._notification_handlers.get(receiver)
                if callback is not None:
                    try:
                        callback()
                    except Exception:
                        # Never unwind a Python exception through AppKit.
                        logging.getLogger(__name__).exception("Traffic-light layout failed")

            self._notification_callback = receive  # Keep the IMP alive for the class lifetime.
            if not library.class_addMethod(
                observer_class, self.selector("frameChanged:"), receive, b"v@:@"
            ):
                raise OSError("Unable to install the traffic-light notification handler")
            library.objc_registerClassPair(observer_class)
            self._observer_class = int(observer_class)
        observer = self.send_id(self.send_id(self._observer_class, "alloc"), "init")
        if not observer:
            raise OSError("Unable to create the traffic-light observer")
        self._notification_handlers[observer] = callback
        return observer

    def observe(self, observer: int, name: str, obj: int) -> None:
        center = self.send_id(self.class_named("NSNotificationCenter"), "defaultCenter")
        notification_name = self.send_id_utf8(
            self.class_named("NSString"), "stringWithUTF8String:", name
        )
        self._add_observer(
            center,
            self.selector("addObserver:selector:name:object:"),
            observer,
            self.selector("frameChanged:"),
            notification_name,
            obj,
        )

    def remove_observer(self, observer: int) -> None:
        self._notification_handlers.pop(observer, None)
        center = self.send_id(self.class_named("NSNotificationCenter"), "defaultCenter")
        self.send_void_pointer(center, "removeObserver:", observer)
        self.send_void(observer, "release")


@lru_cache(maxsize=1)
def _objc_bridge() -> _ObjCBridge:
    return _ObjCBridge()


def _native_window(widget: QWidget, bridge: _ObjCBridge) -> int:
    # winId() creates a native window. During WinIdChange on teardown that can
    # resurrect a modal dialog and leave its parent blocked by an invisible window.
    view = int(widget.internalWinId())
    return bridge.send_id(view, "window") if view else 0


def set_macos_window_appearance(widget: QWidget, *, dark: bool) -> bool:
    """Match native chrome to the widget theme without changing the application."""
    if not uses_macos_native_title_bar() or not widget.isWindow() or widget.windowHandle() is None:
        return False
    try:
        bridge = _objc_bridge()
        window = _native_window(widget, bridge)
        if not window:
            return False
        name = bridge.send_id_utf8(
            bridge.class_named("NSString"),
            "stringWithUTF8String:",
            "NSAppearanceNameDarkAqua" if dark else "NSAppearanceNameAqua",
        )
        appearance = bridge.send_id_pointer(
            bridge.class_named("NSAppearance"), "appearanceNamed:", name
        )
        if not appearance:
            return False
        bridge.send_void_pointer(window, "setAppearance:", appearance)
        # An appearance change can relayout (or reparent) native buttons without
        # emitting frame notifications for the zoom button. Correct it after
        # AppKit finishes applying the appearance, including theme changes.
        observer = getattr(widget, "_macos_traffic_light_observer", None)
        if observer is not None:
            _observe_traffic_lights(widget, bridge, window, observer.height)
        return True
    except (AttributeError, OSError, TypeError, ValueError):
        return False


class _TrafficLightObserver:
    """Correct native frames synchronously, before AppKit can display a reset.

    Frame notifications are synchronous even inside the native live-resize loop.
    Cache native horizontal offsets once: other buttons may already have been
    repositioned when AppKit updates one button at a time.
    """

    def __init__(self, bridge: _ObjCBridge, window: int, height: int) -> None:
        self.bridge = bridge
        self.window = window
        self.height = height
        self.busy = False
        self.observer = 0
        self.views: dict[int, bool] = {}
        self.buttons: list[tuple[int, int, float]] = []
        self.bridge.send_id(window, "retain")
        try:
            self.observer = bridge.create_observer(self.layout)
            first_x = None
            for kind in range(3):
                button = bridge.send_id_integer(window, "standardWindowButton:", kind)
                if not button:
                    continue
                parent = bridge.send_id(button, "superview")
                if not parent:
                    continue
                frame = bridge.send_rect(button, "frame")
                if first_x is None:
                    first_x = frame.origin.x
                self.buttons.append((button, parent, frame.origin.x - first_x))
                for view in (button, parent):
                    if view not in self.views:
                        bridge.send_id(view, "retain")
                        self.views[view] = bridge.send_bool(view, "postsFrameChangedNotifications")
                        bridge.send_void_bool(view, "setPostsFrameChangedNotifications:", True)
                        bridge.observe(self.observer, "NSViewFrameDidChangeNotification", view)
            # AppKit's final layout can silently reset the zoom button after a
            # resize, appearance change, or modal activation. Also observe the
            # completed window update: opening a dialog need not resize it again.
            for name in (
                "NSWindowDidResizeNotification",
                "NSWindowDidEndLiveResizeNotification",
                "NSWindowDidExitFullScreenNotification",
                "NSWindowDidBecomeKeyNotification",
                "NSWindowDidUpdateNotification",
            ):
                bridge.observe(self.observer, name, window)
        except Exception:
            self.dispose()
            raise

    def layout(self) -> None:
        if self.busy or not self.observer or not self.buttons:
            return
        # AppKit owns the automatically revealed full-screen title bar.
        if self.bridge.send_integer(self.window, "styleMask") & (1 << 14):
            return
        self.busy = True
        try:
            bridge = self.bridge
            first = bridge.send_rect(self.buttons[0][0], "frame")
            padding = max(0.0, (self.height - first.size.height) / 2)
            for button, parent, offset in self.buttons:
                # Full-screen transitions can reparent native controls. The next
                # window-state sync rebinds the observer to the new hierarchy.
                if bridge.send_id(button, "superview") != parent:
                    continue
                frame = bridge.send_rect(button, "frame")
                bounds = bridge.send_rect(parent, "bounds")
                top = max(0.0, (self.height - frame.size.height) / 2)
                y = bounds.origin.y + (
                    top
                    if bridge.send_bool(parent, "isFlipped")
                    else bounds.size.height - top - frame.size.height
                )
                x = bounds.origin.x + padding + offset
                if abs(frame.origin.x - x) > 0.01 or abs(frame.origin.y - y) > 0.01:
                    bridge.send_void_point(button, "setFrameOrigin:", _NSPoint(x, y))
        finally:
            self.busy = False

    def matches_window(self, window: int) -> bool:
        if self.window != window:
            return False
        current = []
        for kind in range(3):
            button = self.bridge.send_id_integer(window, "standardWindowButton:", kind)
            parent = self.bridge.send_id(button, "superview") if button else 0
            if parent:
                current.append((button, parent))
        return current == [(button, parent) for button, parent, _offset in self.buttons]

    def dispose(self, *_args) -> None:
        if self.observer:
            self.bridge.remove_observer(self.observer)
            self.observer = 0
        for view, previous in self.views.items():
            self.bridge.send_void_bool(view, "setPostsFrameChangedNotifications:", previous)
            self.bridge.send_void(view, "release")
        self.views.clear()
        self.buttons.clear()
        if self.window:
            self.bridge.send_void(self.window, "release")
            self.window = 0


def release_macos_title_bar(widget: QWidget) -> None:
    observer = getattr(widget, "_macos_traffic_light_observer", None)
    if observer is not None:
        observer.dispose()
        widget.destroyed.disconnect(observer.dispose)
        widget._macos_traffic_light_observer = None  # type: ignore[attr-defined]


def _observe_traffic_lights(widget: QWidget, bridge: _ObjCBridge, window: int, height: int) -> None:
    observer = getattr(widget, "_macos_traffic_light_observer", None)
    if observer is not None and not observer.matches_window(window):
        release_macos_title_bar(widget)
        observer = None
    if observer is None:
        observer = _TrafficLightObserver(bridge, window, height)
        widget._macos_traffic_light_observer = observer  # type: ignore[attr-defined]
        widget.destroyed.connect(observer.dispose)
    observer.height = height
    observer.layout()


def configure_macos_native_title_bar(
    widget: QWidget, *, title_bar_height: int = 0, content_size: QSize | None = None
) -> bool:
    """Make a native title bar transparent while retaining its traffic lights."""
    if not uses_macos_native_title_bar() or not widget.isWindow():
        return False
    try:
        bridge = _objc_bridge()
        window = _native_window(widget, bridge)
        if not window:
            return False
        style_mask = bridge.send_integer(window, "styleMask")
        if not style_mask & _NS_WINDOW_STYLE_MASK_FULL_SIZE_CONTENT_VIEW:
            bridge.send_void_integer(
                window,
                "setStyleMask:",
                style_mask | _NS_WINDOW_STYLE_MASK_FULL_SIZE_CONTENT_VIEW,
            )
        bridge.send_void_bool(window, "setTitlebarAppearsTransparent:", True)
        bridge.send_void_integer(window, "setTitleVisibility:", _NS_WINDOW_TITLE_HIDDEN)
        if content_size is not None and content_size.isValid():
            # Switching to full-size content can leave AppKit's initial content
            # frame stale. Reapply Qt's resolved size without a synthetic drag.
            bridge.send_void_size(
                window, "setContentSize:", _NSSize(content_size.width(), content_size.height())
            )
        if title_bar_height > 0:
            _observe_traffic_lights(widget, bridge, window, title_bar_height)
        return True
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def macos_window_is_in_live_resize(widget: QWidget) -> bool:
    """Return whether AppKit is currently running an interactive window resize."""
    if not uses_macos_native_title_bar() or not widget.isWindow():
        return False
    try:
        bridge = _objc_bridge()
        window = _native_window(widget, bridge)
        return bool(window and bridge.send_bool(window, "inLiveResize"))
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
