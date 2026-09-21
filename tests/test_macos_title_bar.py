from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import ModernWindow
from pyside6_modern_widgets import _macos_window as macos_window
from pyside6_modern_widgets import modern_window as modern_window_module

_APP = QApplication.instance() or QApplication([])


def _dispose(window: ModernWindow) -> None:
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    _APP.processEvents()


def test_chrome_flags_select_native_macos_frame() -> None:
    flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint

    native = macos_window.window_flags_with_chrome(flags, native_macos_title_bar=True)
    portable = macos_window.window_flags_with_chrome(flags, native_macos_title_bar=False)

    assert not native & Qt.WindowType.FramelessWindowHint
    assert portable & Qt.WindowType.FramelessWindowHint


def test_modern_window_uses_native_macos_title_bar_layout(monkeypatch) -> None:
    monkeypatch.setattr(modern_window_module, "uses_macos_native_title_bar", lambda: True)
    monkeypatch.setattr(
        modern_window_module,
        "configure_macos_native_title_bar",
        lambda _widget, **_kwargs: True,
    )

    window = ModernWindow()
    try:
        title_bar = window.titleBar
        assert title_bar is not None
        assert not window.windowFlags() & Qt.WindowType.FramelessWindowHint
        assert window._surface_policy.opaque_surface
        assert title_bar.titleAlignment() == "center"
        assert title_bar.main_layout.indexOf(title_bar.titleLabel) == -1
        assert (
            title_bar.main_layout.contentsMargins().left() == macos_window.MACOS_TRAFFIC_LIGHT_INSET
        )
        assert all(
            button.isHidden()
            for button in (
                title_bar.pinButton,
                title_bar.minimizeButton,
                title_bar.maximizeButton,
                title_bar.closeButton,
            )
        )

        window.setWindowIcon(QIcon(":/pyside6_modern_widgets/icons/application.png"))
        assert title_bar.iconLabel.isHidden()

        window._sync_macos_native_title_bar()
        assert window._macos_title_bar_configured
        assert window.contentsMargins().top() == title_bar.height()
    finally:
        _dispose(window)


def test_failed_macos_bridge_falls_back_to_plain_native_title_bar(monkeypatch) -> None:
    monkeypatch.setattr(modern_window_module, "uses_macos_native_title_bar", lambda: True)
    monkeypatch.setattr(
        modern_window_module,
        "configure_macos_native_title_bar",
        lambda _widget, **_kwargs: False,
    )

    window = ModernWindow()
    try:
        window._sync_macos_native_title_bar()

        assert window._macos_title_bar_configured is False
        assert window.titleBar is not None
        assert window.titleBar.isHidden()
        assert window.contentsMargins().top() == 0
        assert not window.windowFlags() & Qt.WindowType.FramelessWindowHint
    finally:
        _dispose(window)


class _NativeWidget:
    def isWindow(self) -> bool:
        return True

    def winId(self) -> int:
        return 123

    def windowFlags(self) -> Qt.WindowType:
        return Qt.WindowType.Window | Qt.WindowType.WindowMinimizeButtonHint


class _BridgeProbe:
    def __init__(self, *, flipped: bool = False) -> None:
        self.calls: list[tuple] = []
        self.origins: list[tuple[int, float, float]] = []
        self.flipped = flipped

    def send_id(self, receiver: int, selector: str) -> int:
        if (receiver, selector) == (123, "window"):
            return 456
        assert selector == "superview" and receiver in {100, 101, 102}
        return 200

    def send_id_integer(self, receiver: int, selector: str, value: int) -> int:
        assert (receiver, selector) == (456, "standardWindowButton:")
        return 100 + value

    def send_integer(self, receiver: int, selector: str) -> int:
        assert (receiver, selector) == (456, "styleMask")
        return 7

    def send_void_integer(self, receiver: int, selector: str, value: int) -> None:
        self.calls.append((receiver, selector, value))

    def send_void_bool(self, receiver: int, selector: str, value: bool) -> None:
        self.calls.append((receiver, selector, value))

    def send_rect(self, receiver: int, selector: str) -> macos_window._NSRect:
        if selector == "bounds":
            assert receiver == 200
            return macos_window._NSRect(
                macos_window._NSPoint(0, 0),
                macos_window._NSSize(800, 28),
            )
        assert selector == "frame" and receiver in {100, 101, 102}
        return macos_window._NSRect(
            macos_window._NSPoint(14 + (receiver - 100) * 20, 7),
            macos_window._NSSize(14, 14),
        )

    def send_bool(self, receiver: int, selector: str) -> bool:
        assert (receiver, selector) == (200, "isFlipped")
        return self.flipped

    def send_void_point(
        self,
        receiver: int,
        selector: str,
        value: macos_window._NSPoint,
    ) -> None:
        assert selector == "setFrameOrigin:"
        self.origins.append((receiver, value.x, value.y))


class _DoubleClickBridgeProbe:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str, int]] = []

    def send_id(self, receiver: int, selector: str) -> int:
        if (receiver, selector) == (123, "window"):
            return 456
        assert (receiver, selector) == (10, "standardUserDefaults")
        return 20

    def class_named(self, name: str) -> int:
        return {"NSUserDefaults": 10, "NSString": 11}[name]

    def send_id_utf8(self, receiver: int, selector: str, value: str) -> int:
        assert (receiver, selector, value) == (
            11,
            "stringWithUTF8String:",
            "AppleActionOnDoubleClick",
        )
        return 30

    def send_id_pointer(self, receiver: int, selector: str, value: int) -> int:
        assert (receiver, selector, value) == (20, "stringForKey:", 30)
        return 40

    def send_utf8(self, receiver: int, selector: str) -> str:
        assert (receiver, selector) == (40, "UTF8String")
        return "Minimize"

    def send_void_pointer(self, receiver: int, selector: str, value: int = 0) -> None:
        self.calls.append((receiver, selector, value))


def test_native_bridge_preserves_style_and_enables_full_size_content(monkeypatch) -> None:
    bridge = _BridgeProbe()
    monkeypatch.setattr(macos_window, "uses_macos_native_title_bar", lambda: True)
    monkeypatch.setattr(macos_window, "_objc_bridge", lambda: bridge)

    assert macos_window.configure_macos_native_title_bar(  # type: ignore[arg-type]
        _NativeWidget(),
        title_bar_height=34,
    )
    assert bridge.calls == [
        (456, "setStyleMask:", 7 | (1 << 15)),
        (456, "setTitlebarAppearsTransparent:", True),
        (456, "setTitleVisibility:", 1),
    ]
    assert bridge.origins == [
        (100, 10.0, 4.0),
        (101, 30.0, 4.0),
        (102, 50.0, 4.0),
    ]


def test_traffic_lights_support_flipped_title_bar_coordinates() -> None:
    bridge = _BridgeProbe(flipped=True)

    macos_window._position_traffic_lights(456, bridge, 34)  # type: ignore[arg-type]

    assert bridge.origins == [
        (100, 10.0, 10.0),
        (101, 30.0, 10.0),
        (102, 50.0, 10.0),
    ]


def test_title_bar_double_click_follows_macos_preference(monkeypatch) -> None:
    bridge = _DoubleClickBridgeProbe()
    monkeypatch.setattr(macos_window, "uses_macos_native_title_bar", lambda: True)
    monkeypatch.setattr(macos_window, "_objc_bridge", lambda: bridge)

    assert macos_window.perform_macos_title_bar_double_click(  # type: ignore[arg-type]
        _NativeWidget()
    )
    assert bridge.calls == [(456, "miniaturize:", 0)]
