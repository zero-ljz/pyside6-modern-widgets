from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QCursor, QHelpEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QToolTip, QVBoxLayout, QWidget
from shiboken6 import isValid

from pyside6_modern_widgets import DARK_THEME, LIGHT_THEME, ModernToolTip, ModernWindow

_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def tips(theme_manager_instance):
    window = ModernWindow(theme=LIGHT_THEME)
    content = QWidget()
    layout = QVBoxLayout(content)
    first = QPushButton("First")
    second = QPushButton("Second")
    first.setToolTip("Save changes")
    second.setToolTip("Another action")
    layout.addWidget(first)
    layout.addWidget(second)
    window.setCentralWidget(content)
    window.setGeometry(100, 100, 400, 240)
    window.show()
    window.activateWindow()
    first.setFocus()
    _APP.processEvents()
    QCursor.setPos(5, 5)
    manager = ModernToolTip.install(delay_ms=40, reshow_delay_ms=10, max_width=240)
    yield manager, window, first, second
    ModernToolTip.uninstall()
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def hover(widget):
    QTest.mouseMove(widget, widget.rect().center())
    _APP.processEvents()


def wait_visible(manager):
    for _ in range(50):
        if manager._popup.isVisible():
            return
        QTest.qWait(10)
    assert manager._popup.isVisible()


def test_install_reconfigure_and_uninstall_preserve_style_and_text(tips):
    manager, _, first, _ = tips
    style = _APP.style()
    original_hover = first.testAttribute(Qt.WidgetAttribute.WA_Hover)
    assert ModernToolTip.install(delay_ms=20) is manager
    hover(first)
    wait_visible(manager)
    assert _APP.style() is style
    assert first.toolTip() == "Save changes"
    ModernToolTip.uninstall()
    assert not manager._popup.isVisible()
    assert first.testAttribute(Qt.WidgetAttribute.WA_Hover) == original_hover
    assert _APP.style() is style
    assert first.toolTip() == "Save changes"
    ModernToolTip.uninstall()


def test_first_and_repeat_delay_and_no_focus_or_native_popup(tips):
    manager, window, first, second = tips
    hover(first)
    assert manager._timer.interval() == 40
    assert not manager._popup.isVisible()
    wait_visible(manager)
    assert _APP.activeWindow() is window
    assert _APP.focusWidget() is first
    assert manager._popup.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert not QToolTip.isVisible()
    hover(second)
    assert not manager._popup.isVisible()
    assert manager._timer.interval() == 10
    wait_visible(manager)
    assert manager._popup.accessibleName() == second.toolTip()


def test_theme_updates_and_opaque_rounded_fallback(tips):
    manager, window, first, _ = tips
    hover(first)
    wait_visible(manager)
    popup = manager._popup
    assert popup.theme() == LIGHT_THEME
    window.setTheme(replace(DARK_THEME, tooltip_surface="#304050"))
    assert popup.theme().tooltip_surface == "#304050"
    assert not popup._native_acrylic
    pixmap = popup.grab()
    image = pixmap.toImage()
    assert image.pixelColor(0, 0).alpha() == 0
    scale = pixmap.devicePixelRatio()
    color = image.pixelColor(round(12 * scale), round(4 * scale))
    assert color == QColor("#304050")


@pytest.mark.parametrize("kind", [QEvent.Type.WindowDeactivate, QEvent.Type.ApplicationDeactivate])
def test_deactivation_cancels_pending_and_visible_tips(tips, kind):
    manager, window, first, _ = tips
    hover(first)
    _APP.sendEvent(window if kind == QEvent.Type.WindowDeactivate else _APP, QEvent(kind))
    QTest.qWait(70)
    assert not manager._popup.isVisible()
    QTest.mouseMove(first, QPoint(3, 3))
    wait_visible(manager)
    _APP.sendEvent(window if kind == QEvent.Type.WindowDeactivate else _APP, QEvent(kind))
    assert not manager._popup.isVisible()


def test_click_and_escape_dismiss_without_swallowing_input(tips):
    manager, _, first, _ = tips
    clicks = []
    first.clicked.connect(lambda: clicks.append(True))
    hover(first)
    wait_visible(manager)
    QTest.mouseClick(first, Qt.MouseButton.LeftButton)
    assert clicks == [True]
    assert not manager._popup.isVisible()
    QTest.mouseMove(first, QPoint(4, 4))
    wait_visible(manager)
    QTest.keyClick(first, Qt.Key.Key_Escape)
    assert not manager._popup.isVisible()


def test_expiry_native_wakeup_does_not_revive_tip_and_uninstall_restores_delivery(tips):
    manager, _, first, _ = tips
    first.setToolTipDuration(30)
    hover(first)
    wait_visible(manager)
    QTest.qWait(60)
    assert not manager._popup.isVisible()
    event = QHelpEvent(QEvent.Type.ToolTip, first.rect().center(), QCursor.pos())
    _APP.sendEvent(first, event)
    QTest.qWait(60)
    assert not manager._popup.isVisible()
    assert not QToolTip.isVisible()
    ModernToolTip.uninstall()
    _APP.sendEvent(first, QHelpEvent(QEvent.Type.ToolTip, first.rect().center(), QCursor.pos()))
    assert QToolTip.isVisible()
    QToolTip.hideText()


def test_text_changes_rich_text_and_long_word_wrapping(tips):
    manager, _, first, _ = tips
    first.setToolTip("<b>Help</b><br>" + "x" * 160)
    hover(first)
    wait_visible(manager)
    assert "<b>" not in manager._popup.accessibleName()
    assert manager._popup.width() <= 240
    assert manager._popup.height() > 40
    first.setToolTip("Updated")
    assert manager._popup.accessibleName() == "Updated"
    first.setToolTip("")
    assert not manager._popup.isVisible()


@pytest.mark.parametrize("origin", [QPoint(0, 0), QPoint(-800, -600)])
def test_cursor_screen_edges_and_negative_coordinates(tips, monkeypatch, origin):
    manager, _, first, _ = tips
    screen = first.screen()
    area = QRect(origin.x(), origin.y(), 800, 600)
    monkeypatch.setattr(screen, "availableGeometry", lambda: area)
    monkeypatch.setattr(QApplication, "screenAt", staticmethod(lambda _: screen))
    first.setToolTip("Long content " * 50)
    for point in (area.topLeft(), area.topRight(), area.bottomLeft(), area.bottomRight()):
        manager._popup.present(first, point, 240)
        assert area.contains(manager._popup.geometry())
        assert manager._popup.width() <= 240
    manager._popup.hide()


def test_parent_tooltip_and_temporary_hover_attribute_restoration(tips):
    manager, _, first, _ = tips
    label = QLabel("Child", first)
    label.setGeometry(10, 2, 80, 18)
    label.show()
    original = label.testAttribute(Qt.WidgetAttribute.WA_Hover)
    hover(label)
    wait_visible(manager)
    assert manager._popup.owner() is first
    assert label.testAttribute(Qt.WidgetAttribute.WA_Hover)
    ModernToolTip.uninstall()
    assert label.testAttribute(Qt.WidgetAttribute.WA_Hover) == original


@pytest.mark.parametrize("visible", [False, True])
def test_destroying_target_cancels_delivery(tips, visible):
    manager, _, first, _ = tips
    hover(first)
    if visible:
        wait_visible(manager)
    first.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QTest.qWait(60)
    assert not isValid(first)
    assert not manager._popup.isVisible()
    assert not manager._timer.isActive()


def test_hiding_or_moving_owner_cancels_tooltip(tips):
    manager, window, first, _ = tips
    hover(first)
    wait_visible(manager)
    window.move(window.pos() + QPoint(10, 10))
    assert not manager._popup.isVisible()
    hover(first)
    wait_visible(manager)
    window.hide()
    assert not manager._popup.isVisible()


def test_custom_help_events_without_widget_text_keep_native_delivery(tips):
    _, window, _, _ = tips

    class ItemHelp(QWidget):
        requested = False

        def event(self, event):
            if event.type() == QEvent.Type.ToolTip:
                self.requested = True
                return True
            return super().event(event)

    item = ItemHelp(window)
    _APP.sendEvent(item, QHelpEvent(QEvent.Type.ToolTip, QPoint(), QPoint()))
    assert item.requested


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"delay_ms": -1}, ValueError),
        ({"reshow_delay_ms": -1}, ValueError),
        ({"delay_ms": 1.5}, TypeError),
        ({"delay_ms": True}, TypeError),
        ({"max_width": 20}, ValueError),
        ({"delay_ms": 2**31}, ValueError),
    ],
)
def test_invalid_configuration_is_atomic(tips, kwargs, error):
    manager, _, _, _ = tips
    with pytest.raises(error):
        ModernToolTip.install(**kwargs)
    assert ModernToolTip._instance is manager
    assert manager._delay == 40
