from __future__ import annotations

import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionMenuItem, QToolButton

from pyside6_modern_widgets import ModernMenu, ModernMenuBar, ModernWindow
from pyside6_modern_widgets.theme import LIGHT_THEME, theme_manager

_APP = QApplication.instance() or QApplication([])


def _selected_background(menu_bar: ModernMenuBar) -> QColor:
    menu_bar.ensurePolished()
    option = QStyleOptionMenuItem()
    menu_bar.initStyleOption(option, menu_bar.actions()[0])
    option.rect = QRect(0, 0, 100, 30)
    option.text = ""
    option.state |= QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_Sunken
    pixels = QPixmap(option.rect.size())
    pixels.fill(QColor("white"))
    painter = QPainter(pixels)
    menu_bar.style().drawControl(QStyle.ControlElement.CE_MenuBarItem, option, painter, menu_bar)
    painter.end()
    image = pixels.toImage()
    assert image.pixelColor(0, 0) != image.pixelColor(50, 15)  # Rounded corner.
    return image.pixelColor(50, 15)


@pytest.mark.parametrize("manual", [True, False])
def test_menu_bar_selection_uses_window_theme_in_either_location(manual) -> None:
    theme = replace(LIGHT_THEME, control_pressed="#FF123456")
    window = ModernWindow(theme=theme)
    menu_bar = ModernMenuBar(window) if manual else window.menuBar()
    menu = menu_bar.addMenu("File")
    assert isinstance(menu, ModernMenu)
    assert isinstance(menu.addMenu("Recent"), ModernMenu)
    if manual:
        window.titleBar.addCustomWidget(menu_bar, align="left")
    window.show()
    _APP.processEvents()
    assert _selected_background(menu_bar) == QColor("#123456")

    # Changing only a control color need not emit a Qt palette change.
    window.setTheme(replace(theme, control_pressed="#FF654321"))
    _APP.processEvents()
    assert _selected_background(menu_bar) == QColor("#654321")
    window.close()


def test_manual_menu_bar_updates_theme_when_moved_between_windows() -> None:
    first = ModernWindow(theme=replace(LIGHT_THEME, control_pressed="#FF123456"))
    second = ModernWindow(theme=replace(LIGHT_THEME, control_pressed="#FF654321"))
    menu_bar = ModernMenuBar(first)
    menu_bar.addMenu("File")
    first.titleBar.addCustomWidget(menu_bar, align="left")
    assert _selected_background(menu_bar) == QColor("#123456")
    second.titleBar.addCustomWidget(menu_bar, align="left")
    assert _selected_background(menu_bar) == QColor("#654321")
    first.close()
    second.close()


def test_standalone_menu_bar_follows_global_theme() -> None:
    manager = theme_manager()
    original = manager.theme()
    menu_bar = ModernMenuBar()
    menu_bar.addMenu("File")
    try:
        manager.setTheme(replace(original, control_pressed="#FF123456"))
        assert _selected_background(menu_bar) == QColor("#123456")
        manager.setTheme(replace(original, control_pressed="#FF654321"))
        assert _selected_background(menu_bar) == QColor("#654321")
    finally:
        menu_bar.close()
        manager.setTheme(original)


def test_overflow_uses_modern_menu_and_keeps_qt_action_updates() -> None:
    window = ModernWindow()
    menu_bar = ModernMenuBar(window)
    menu_bar.setNativeMenuBar(False)
    menus = [
        menu_bar.addMenu(title) for title in ("File", "Edit", "View", "Navigate", "Tools", "Help")
    ]
    for menu in menus:
        menu.addAction("Item")
    window.titleBar.addCustomWidget(menu_bar, align="left")
    menu_bar.setFixedWidth(180)
    window.resize(800, 400)
    window.show()
    _APP.processEvents()
    extension = menu_bar.findChild(QToolButton, "qt_menubar_ext_button")
    assert extension is not None and extension.isVisible()
    overflow = extension.menu()
    assert isinstance(overflow, ModernMenu)
    original_actions = overflow.actions()
    assert original_actions
    assert all(action in menu_bar.actions() for action in original_actions)
    assert all(isinstance(action.menu(), ModernMenu) for action in original_actions)

    opened = []

    def inspect_popup() -> None:
        opened.append(QApplication.activePopupWidget() is overflow and overflow.isVisible())
        overflow.close()

    QTimer.singleShot(30, inspect_popup)
    QTest.mouseClick(extension, Qt.MouseButton.LeftButton)
    QTest.qWait(40)
    assert opened == [True]

    menu_bar.setFixedWidth(260)
    _APP.processEvents()
    assert extension.menu() is overflow
    assert len(overflow.actions()) < len(original_actions)
    assert overflow.actions()[-1] is menus[-1].menuAction()
    menus[-1].setEnabled(False)
    assert not overflow.actions()[-1].isEnabled()
    menu_bar.removeAction(menus[-1].menuAction())
    _APP.processEvents()
    assert menus[-1].menuAction() not in overflow.actions()

    menu_bar.setFixedWidth(800)
    _APP.processEvents()
    assert not extension.isVisible()
    menu_bar.setFixedWidth(180)
    _APP.processEvents()
    assert extension.isVisible()
    assert extension.menu() is overflow
    window.close()
