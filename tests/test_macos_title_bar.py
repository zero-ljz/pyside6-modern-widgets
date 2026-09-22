from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QSize, Qt
from PySide6.QtGui import QIcon, QResizeEvent
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QMessageBox, QToolBar

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernDialog,
    ModernMessageBox,
    ModernWindow,
)
from pyside6_modern_widgets import _macos_window as macos_window
from pyside6_modern_widgets import modern_dialog as dialog_module
from pyside6_modern_widgets import modern_message_box as message_box_module
from pyside6_modern_widgets import modern_window as modern_window_module
from pyside6_modern_widgets.theme import ThemeMode

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


@pytest.mark.parametrize("configured", [True, False])
def test_dialog_uses_macos_chrome_and_native_resize(monkeypatch, configured):
    monkeypatch.setattr(dialog_module, "uses_macos_native_title_bar", lambda: True)
    monkeypatch.setattr(
        dialog_module, "configure_macos_native_title_bar", lambda *_args, **_kwargs: configured
    )
    dialog = ModernDialog()
    try:
        dialog.setWindowTitle("Preferences")
        dialog.show()
        _APP.processEvents()
        assert not dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
        assert dialog._surface_policy.opaque_surface
        assert not dialog.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert dialog._title_bar.titleAlignment() == "center"
        assert dialog._title_bar.titleLabel.text() == "Preferences"
        assert dialog._title_bar.closeButton.isHidden()
        assert dialog._title_bar.isVisible() == configured
        assert dialog.contentsMargins().top() == (dialog._title_bar.height() if configured else 0)
        assert dialog._chrome_overlay.isHidden()
        assert not dialog.showSystemWindowMenu(dialog.pos())
        resize_modes = []
        monkeypatch.setattr(
            dialog._resize_controller,
            "handle_event",
            lambda *_args, **kwargs: resize_modes.append(kwargs["enabled"]) or False,
        )
        dialog.eventFilter(dialog, QEvent(QEvent.Type.MouseMove))
        assert resize_modes == [False]
        dialog.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        assert not dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.FramelessWindowHint)
        assert not dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
    finally:
        _dispose(dialog)


@pytest.mark.parametrize(
    "module,widget_class", [(dialog_module, ModernDialog), (message_box_module, ModernMessageBox)]
)
def test_macos_dialog_appearance_tracks_explicit_and_global_themes(
    monkeypatch, theme_manager_instance, module, widget_class
):
    monkeypatch.setattr(module, "uses_macos_native_title_bar", lambda: True)
    appearances = []
    monkeypatch.setattr(
        module,
        "set_macos_window_appearance",
        lambda widget, *, dark: appearances.append(dark),
    )
    widget = widget_class(theme=DARK_THEME)
    try:
        widget.show()
        _APP.processEvents()
        assert appearances[-1] is True
        widget.setTheme(LIGHT_THEME)
        assert appearances[-1] is False
        widget.setTheme(DARK_THEME)
        assert appearances[-1] is True
        widget.setTheme(None)
        theme_manager_instance.setMode(ThemeMode.LIGHT)
        assert appearances[-1] is False
        theme_manager_instance.setMode(ThemeMode.DARK)
        assert appearances[-1] is True
        appearances.clear()
        widget.event(QEvent(QEvent.Type.WinIdChange))
        if isinstance(widget, ModernDialog):
            widget._sync_macos_native_title_bar()
        assert appearances[-1] is True
    finally:
        _dispose(widget)


@pytest.mark.parametrize("dark", [False, True])
def test_native_appearance_is_applied_to_the_window(monkeypatch, dark):
    calls = []

    class Bridge:
        def class_named(self, name):
            return {"NSString": 10, "NSAppearance": 20}[name]

        def send_id(self, receiver, selector):
            assert (receiver, selector) == (123, "window")
            return 456

        def send_id_utf8(self, receiver, selector, value):
            assert (receiver, selector) == (10, "stringWithUTF8String:")
            assert value == ("NSAppearanceNameDarkAqua" if dark else "NSAppearanceNameAqua")
            return 30

        def send_id_pointer(self, receiver, selector, value):
            assert (receiver, selector, value) == (20, "appearanceNamed:", 30)
            return 40

        def send_void_pointer(self, *args):
            calls.append(args)

    class Widget(_NativeWidget):
        def windowHandle(self):
            return object()

    monkeypatch.setattr(macos_window, "uses_macos_native_title_bar", lambda: True)
    monkeypatch.setattr(macos_window, "_objc_bridge", Bridge)
    assert macos_window.set_macos_window_appearance(Widget(), dark=dark)
    assert calls == [(456, "setAppearance:", 40)]


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


def test_macos_resize_defers_native_title_bar_until_appkit_finishes(monkeypatch) -> None:
    window = ModernWindow()
    monkeypatch.setattr(window, "_uses_native_macos_title_bar", True)
    try:
        window.resizeEvent(QResizeEvent(QSize(800, 500), QSize(700, 400)))

        assert window._macos_title_bar_resize_timer.isActive()
    finally:
        window._macos_title_bar_resize_timer.stop()
        _dispose(window)


def test_macos_title_bar_sync_waits_out_live_resize(monkeypatch) -> None:
    window = ModernWindow()
    native_syncs: list[bool] = []
    live_resize = [True]
    monkeypatch.setattr(window, "_uses_native_macos_title_bar", True)
    monkeypatch.setattr(
        modern_window_module,
        "macos_window_is_in_live_resize",
        lambda _widget: live_resize[0],
    )
    monkeypatch.setattr(
        window,
        "_sync_macos_native_title_bar",
        lambda: native_syncs.append(True),
    )
    try:
        window._sync_macos_title_bar_after_resize()
        assert window._macos_title_bar_resize_timer.isActive()
        assert native_syncs == []

        window._macos_title_bar_resize_timer.stop()
        live_resize[0] = False
        window._sync_macos_title_bar_after_resize()
        assert not window._macos_title_bar_resize_timer.isActive()
        assert native_syncs == [True]
    finally:
        window._macos_title_bar_resize_timer.stop()
        _dispose(window)


def test_macos_toolbar_visibility_reapplies_transparent_title_bar(monkeypatch) -> None:
    window = ModernWindow()
    toolbar = QToolBar(window)
    other_toolbar = QToolBar()
    syncs = []
    monkeypatch.setattr(window, "_uses_native_macos_title_bar", True)
    monkeypatch.setattr(window, "_sync_macos_native_title_bar", lambda: syncs.append(True))
    try:
        window._native_frame_sync_timer.stop()
        for event_type in (QEvent.Type.Show, QEvent.Type.Hide):
            assert not window.eventFilter(other_toolbar, QEvent(event_type))
            assert not window._native_frame_sync_timer.isActive()
            assert not window.eventFilter(toolbar, QEvent(event_type))
            assert window._native_frame_sync_timer.isActive()
            _APP.processEvents()
        assert syncs == [True, True]
    finally:
        _dispose(other_toolbar)
        _dispose(window)


class _NativeWidget:
    def isWindow(self) -> bool:
        return True

    def internalWinId(self) -> int:
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


class _LiveResizeBridgeProbe:
    def send_id(self, receiver: int, selector: str) -> int:
        assert (receiver, selector) == (123, "window")
        return 456

    def send_bool(self, receiver: int, selector: str) -> bool:
        assert (receiver, selector) == (456, "inLiveResize")
        return True


def test_native_bridge_preserves_style_and_enables_full_size_content(monkeypatch) -> None:
    bridge = _BridgeProbe()
    monkeypatch.setattr(macos_window, "uses_macos_native_title_bar", lambda: True)
    monkeypatch.setattr(macos_window, "_objc_bridge", lambda: bridge)
    layouts = []
    monkeypatch.setattr(
        macos_window,
        "_observe_traffic_lights",
        lambda widget, bridge, window, height: layouts.append((window, height)),
    )

    assert macos_window.configure_macos_native_title_bar(  # type: ignore[arg-type]
        _NativeWidget(),
        title_bar_height=34,
    )
    assert bridge.calls == [
        (456, "setStyleMask:", 7 | (1 << 15)),
        (456, "setTitlebarAppearsTransparent:", True),
        (456, "setTitleVisibility:", 1),
    ]
    assert layouts == [(456, 34)]


def test_traffic_lights_support_flipped_title_bar_coordinates() -> None:
    bridge = _FrameNotificationProbe(flipped=True)
    observer = macos_window._TrafficLightObserver(bridge, 456, 34)
    observer.layout()

    assert bridge.origins == [
        (100, 10.0, 10.0),
        (101, 30.0, 10.0),
        (102, 50.0, 10.0),
    ]
    observer.dispose()


class _FrameNotificationProbe(_BridgeProbe):
    def __init__(self, *, flipped=False):
        super().__init__(flipped=flipped)
        self.frames = {
            button: super(_FrameNotificationProbe, self).send_rect(button, "frame")
            for button in (100, 101, 102)
        }
        self.refs = {}
        self.posts = dict.fromkeys((100, 101, 102, 200), False)
        self.notifications = []
        self.callback = None
        self.full_screen = False
        self.parent = 200

    def send_id(self, receiver, selector):
        if selector == "retain":
            self.refs[receiver] = self.refs.get(receiver, 0) + 1
            return receiver
        if selector == "superview":
            return self.parent
        return super().send_id(receiver, selector)

    def send_void(self, receiver, selector):
        assert selector == "release"
        self.refs[receiver] -= 1

    def create_observer(self, callback):
        self.callback = callback
        return 999

    def observe(self, observer, name, obj):
        assert observer == 999
        self.notifications.append((name, obj))

    def remove_observer(self, observer):
        assert observer == 999
        self.callback = None
        self.notifications.clear()

    def notify(self, name, obj):
        if self.callback and (name, obj) in self.notifications:
            self.callback()

    def send_integer(self, receiver, selector):
        return (1 << 14) if self.full_screen else super().send_integer(receiver, selector)

    def send_bool(self, receiver, selector):
        if selector == "postsFrameChangedNotifications":
            return self.posts.get(receiver, False)
        if selector == "isFlipped":
            return self.flipped
        return super().send_bool(receiver, selector)

    def send_void_bool(self, receiver, selector, value):
        if selector == "setPostsFrameChangedNotifications:":
            self.posts[receiver] = value
        else:
            super().send_void_bool(receiver, selector, value)

    def send_rect(self, receiver, selector):
        if selector == "frame":
            frame = self.frames[receiver]
            return macos_window._NSRect.from_buffer_copy(frame)
        return super().send_rect(200 if selector == "bounds" else receiver, selector)

    def send_void_point(self, receiver, selector, value):
        super().send_void_point(receiver, selector, value)
        self.frames[receiver].origin = value
        if self.callback and self.posts[receiver]:
            self.callback()


def test_native_frame_resets_are_corrected_synchronously_without_spacing_drift():
    bridge = _FrameNotificationProbe()
    observer = macos_window._TrafficLightObserver(bridge, 456, 34)
    try:
        observer.layout()
        # AppKit lays out one button at a time during live resize. Correction
        # must finish within each notification, without waiting for a Qt timer.
        for _ in range(3):
            for button in (100, 101, 102):
                bridge.frames[button].origin = macos_window._NSPoint(14 + (button - 100) * 20, 7)
                bridge.callback()
                for other in (100, 101, 102):
                    assert bridge.frames[other].origin.x == 10 + (other - 100) * 20
                    assert bridge.frames[other].origin.y == 4
        assert len(bridge.origins) == 12  # No recursive notification loop.
        bridge.full_screen = True
        bridge.frames[100].origin.y = 7
        bridge.callback()
        assert bridge.frames[100].origin.y == 7
        bridge.full_screen = False
        bridge.callback()
        assert bridge.frames[100].origin.y == 4
    finally:
        observer.dispose()
    observer.dispose()  # Surface teardown followed by QObject destruction.
    assert bridge.callback is None
    assert not bridge.notifications
    assert not any(bridge.refs.values())
    assert not any(bridge.posts.values())


@pytest.mark.parametrize(
    "notification",
    ["NSWindowDidResizeNotification", "NSWindowDidEndLiveResizeNotification"],
)
def test_window_resize_corrects_green_button_after_silent_appkit_layout(notification):
    bridge = _FrameNotificationProbe()
    observer = macos_window._TrafficLightObserver(bridge, 456, 34)
    try:
        observer.layout()
        for _ in range(3):
            # The last AppKit layout pass moves only the green button without
            # a view-frame notification. Window notifications must correct it
            # before returning to the native resize loop, without a Qt timer.
            bridge.frames[102].origin = macos_window._NSPoint(46, 7)
            bridge.notify(notification, 789)  # A different window is unrelated.
            assert bridge.frames[102].origin.x == 46
            bridge.notify(notification, 456)
            for button in (100, 101, 102):
                assert bridge.frames[button].origin.x == 10 + (button - 100) * 20
                assert bridge.frames[button].origin.y == 4
        assert len(bridge.origins) == 6  # Only the green button needs correction.

        bridge.full_screen = True
        bridge.frames[102].origin = macos_window._NSPoint(46, 7)
        bridge.notify(notification, 456)
        assert bridge.frames[102].origin.x == 46
        assert bridge.frames[102].origin.y == 7
    finally:
        observer.dispose()
    bridge.notify(notification, 456)
    assert not bridge.notifications
    assert not any(bridge.refs.values())


def test_traffic_light_observer_rebinds_after_native_reparenting():
    widget = QObject()
    bridge = _FrameNotificationProbe()
    try:
        macos_window._observe_traffic_lights(widget, bridge, 456, 34)
        previous = widget._macos_traffic_light_observer
        bridge.parent = 201
        macos_window._observe_traffic_lights(widget, bridge, 456, 34)
        replacement = widget._macos_traffic_light_observer
        assert replacement is not previous
        assert previous.observer == 0
        assert replacement.matches_window(456)
        assert bridge.refs[200] == 0
        assert not bridge.posts[200]
        assert bridge.refs[201] == 1
        assert ("NSViewFrameDidChangeNotification", 201) in bridge.notifications
        macos_window._observe_traffic_lights(widget, bridge, 456, 34)
        assert widget._macos_traffic_light_observer is replacement
        macos_window.release_macos_title_bar(widget)
        assert not any(bridge.refs.values())
        assert not any(bridge.posts.values())
        # A released native surface can be recreated on the same Qt object.
        macos_window._observe_traffic_lights(widget, bridge, 456, 34)
    finally:
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert bridge.callback is None
    assert not any(bridge.refs.values())


def test_macos_message_box_keeps_native_margins_and_titled_frame(monkeypatch):
    monkeypatch.setattr(message_box_module, "uses_macos_native_title_bar", lambda: True)
    box = ModernMessageBox(
        QMessageBox.Icon.Information, "Information", "Latest version", QMessageBox.StandardButton.Ok
    )
    try:
        # Qt/macOS supplies these widget margins; the offscreen backend does not.
        box.setContentsMargins(24, 15, 24, 20)
        box.setInformativeText("Additional context")
        box.setDetailedText("Details")
        check_box = QCheckBox("Remember", box)
        box.setCheckBox(check_box)
        box.show()
        _APP.processEvents()
        assert box.contentsMargins().left() == 24
        assert box.contentsMargins().top() == 15
        assert box.contentsMargins().right() == 24
        assert box.contentsMargins().bottom() == 20
        assert not box.windowFlags() & Qt.WindowType.FramelessWindowHint
        assert box.windowFlags() & Qt.WindowType.WindowTitleHint
        assert box.windowTitle() == "Information"
        assert not box.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert box._title_bar.isHidden()
        assert box._chrome_overlay.isHidden()
        assert box.autoFillBackground()
        for child in [
            box.button(QMessageBox.StandardButton.Ok),
            box.checkBox(),
            box.findChild(QLabel, "qt_msgbox_label"),
        ]:
            assert box.rect().contains(child.mapTo(box, child.rect().bottomRight()))
        box.setWindowFlags(box.windowFlags() | Qt.WindowType.FramelessWindowHint)
        assert not box.windowFlags() & Qt.WindowType.FramelessWindowHint
        box.setWindowTitle("Changed")
        assert box.windowTitle() == "Changed"
        box.button(QMessageBox.StandardButton.Ok).click()
        assert box.result() == QMessageBox.StandardButton.Ok
    finally:
        _dispose(box)


def test_native_bridge_reports_live_resize(monkeypatch) -> None:
    monkeypatch.setattr(macos_window, "uses_macos_native_title_bar", lambda: True)
    monkeypatch.setattr(macos_window, "_objc_bridge", _LiveResizeBridgeProbe)

    assert macos_window.macos_window_is_in_live_resize(  # type: ignore[arg-type]
        _NativeWidget()
    )


def test_title_bar_double_click_follows_macos_preference(monkeypatch) -> None:
    bridge = _DoubleClickBridgeProbe()
    monkeypatch.setattr(macos_window, "uses_macos_native_title_bar", lambda: True)
    monkeypatch.setattr(macos_window, "_objc_bridge", lambda: bridge)

    assert macos_window.perform_macos_title_bar_double_click(  # type: ignore[arg-type]
        _NativeWidget()
    )
    assert bridge.calls == [(456, "miniaturize:", 0)]
