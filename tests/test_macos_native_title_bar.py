"""Real AppKit regressions; run on macOS with QT_QPA_PLATFORM=cocoa."""

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QToolBar

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernDialog,
    ModernMessageBox,
    ModernWindow,
)
from pyside6_modern_widgets import _macos_window as native

pytestmark = pytest.mark.skipif(
    not native.uses_macos_native_title_bar(), reason="Requires real macOS AppKit windows"
)


def _dispose(widget):
    widget.close()
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("widget_class", [ModernDialog, ModernMessageBox])
def test_appkit_dialog_appearance_follows_widget_theme(widget_class):
    widget = widget_class(theme=DARK_THEME)
    try:
        widget.setWindowTitle("Appearance")
        widget.show()
        QTest.qWait(100)
        bridge = native._objc_bridge()
        nswindow = native._native_window(widget, bridge)
        for theme, expected in (
            (DARK_THEME, "NSAppearanceNameDarkAqua"),
            (LIGHT_THEME, "NSAppearanceNameAqua"),
            (DARK_THEME, "NSAppearanceNameDarkAqua"),
        ):
            widget.setTheme(theme)
            QApplication.processEvents()
            appearance = bridge.send_id(nswindow, "effectiveAppearance")
            name = bridge.send_id(appearance, "name")
            assert bridge.send_utf8(name, "UTF8String") == expected
        if isinstance(widget, ModernDialog):
            assert widget._macos_title_bar_configured
            assert bridge.send_bool(nswindow, "titlebarAppearsTransparent")
            assert widget._title_bar.isVisible()
            assert widget._title_bar.closeButton.isHidden()
            assert widget.contentsMargins().top() == widget._title_bar.height()
    finally:
        _dispose(widget)


def test_appkit_frame_notifications_correct_buttons_before_returning():
    window = ModernWindow()
    try:
        window.show()
        QTest.qWait(100)
        assert window._macos_title_bar_configured
        observer = window._macos_traffic_light_observer
        bridge = observer.bridge
        for width, height in ((800, 500), (900, 600), (750, 450)):
            window.resize(width, height)
            QApplication.processEvents()
            for button, parent, offset in observer.buttons:
                expected = bridge.send_rect(button, "frame")
                bounds = bridge.send_rect(parent, "bounds")
                first = bridge.send_rect(observer.buttons[0][0], "frame")
                padding = max(0.0, (observer.height - first.size.height) / 2)
                top = max(0.0, (observer.height - expected.size.height) / 2)
                assert expected.origin.x == pytest.approx(bounds.origin.x + padding + offset)
                assert expected.origin.y == pytest.approx(
                    bounds.origin.y
                    + (
                        top
                        if bridge.send_bool(parent, "isFlipped")
                        else bounds.size.height - top - expected.size.height
                    )
                )
                bridge.send_void_point(
                    button,
                    "setFrameOrigin:",
                    native._NSPoint(expected.origin.x, expected.origin.y + 5),
                )
                # No Qt event processing here: the Objective-C callback must
                # restore the position before setFrameOrigin: returns.
                actual = bridge.send_rect(button, "frame")
                assert actual.origin.x == pytest.approx(expected.origin.x)
                assert actual.origin.y == pytest.approx(expected.origin.y)
    finally:
        _dispose(window)
    assert observer.observer == 0
    assert observer.window == 0


def test_appkit_toolbar_visibility_preserves_transparent_title_bar():
    window = ModernWindow()
    toolbar = QToolBar(window)
    window.addToolBar(toolbar)
    try:
        window.show()
        QTest.qWait(100)
        bridge = native._objc_bridge()
        nswindow = native._native_window(window, bridge)
        for visible in (False, True, False, True):
            toolbar.setVisible(visible)
            QTest.qWait(100)
            assert bridge.send_bool(nswindow, "titlebarAppearsTransparent")
    finally:
        _dispose(window)


def test_appkit_message_box_preserves_layout_and_movable_native_frame():
    reference = QMessageBox()
    box = ModernMessageBox(
        QMessageBox.Icon.Information, "Information", "Latest version", QMessageBox.StandardButton.Ok
    )
    try:
        box.setInformativeText("Additional context")
        box.setDetailedText("Details")
        box.show()
        QTest.qWait(100)
        assert box.contentsMargins() == reference.contentsMargins()
        assert not box.windowFlags() & Qt.WindowType.FramelessWindowHint
        assert box._title_bar.isHidden()
        bridge = native._objc_bridge()
        nswindow = native._native_window(box, bridge)
        assert bridge.send_bool(nswindow, "isMovable")
        assert bridge.send_integer(nswindow, "styleMask") & 1  # NSWindowStyleMaskTitled
        assert box.windowTitle() == "Information"
        for child in (
            box.button(QMessageBox.StandardButton.Ok),
            box.findChild(QLabel, "qt_msgbox_label"),
        ):
            assert box.rect().contains(child.mapTo(box, child.rect().bottomRight()))
        box.button(QMessageBox.StandardButton.Ok).click()
        assert box.result() == QMessageBox.StandardButton.Ok
    finally:
        _dispose(box)
        _dispose(reference)
