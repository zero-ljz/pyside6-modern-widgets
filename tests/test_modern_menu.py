from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QAction, QKeySequence, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QWidget

from pyside6_modern_widgets import ModernMenu

_APP = QApplication.instance() or QApplication([])


def test_modern_menu_preserves_qmenu_constructors_and_actions() -> None:
    parent = QWidget()
    menu = ModernMenu("&File", parent)
    parent_only_menu = ModernMenu(parent)
    action = QAction("Open", menu)

    menu.addAction(action)
    menu.addSeparator()
    submenu = menu.addMenu("Recent")

    assert isinstance(menu, QMenu)
    assert menu.title() == "&File"
    assert menu.parent() is parent
    assert parent_only_menu.parent() is parent
    assert menu.actions()[0] is action
    assert submenu.menuAction() in menu.actions()
    assert isinstance(submenu, ModernMenu)


def test_modern_menu_preserves_native_width_and_action_icons() -> None:
    native = QMenu()
    modern = ModernMenu()
    icon = _APP.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)

    for menu in (native, modern):
        menu.addAction(icon, "Open file")
        toggle = menu.addAction("Checkable toggle")
        toggle.setCheckable(True)
        toggle.setChecked(True)
        menu.addSeparator()
        shortcut = menu.addAction("Combined shortcut")
        shortcut.setShortcut(QKeySequence("Ctrl+Shift+S"))
        menu.addMenu("Nested menu")
        menu.ensurePolished()

    assert modern.sizeHint().width() == native.sizeHint().width()
    assert modern.sizeHint().height() == native.sizeHint().height() + 4 * 4 + 4
    assert modern.actions()[0].icon().cacheKey() == icon.cacheKey()
    assert modern.styleSheet() == ""


def test_modern_menu_clips_only_the_outer_corners() -> None:
    menu = ModernMenu()
    menu.addAction("First action")
    menu.addAction("Second action")
    menu.show()
    _APP.processEvents()

    image = menu.grab().toImage()
    first_item_y = menu.actionGeometry(menu.actions()[0]).center().y()

    assert menu.mask().isEmpty()
    assert image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0
    assert 0 < image.pixelColor(menu.width() - 8, first_item_y).alpha() < 255
    menu.hide()


def test_modern_menu_has_even_vertical_margins_and_soft_lines() -> None:
    menu = ModernMenu()
    action = menu.addAction("Only action")
    separator = menu.addSeparator()
    menu.addAction("Last action")
    menu.show()
    _APP.processEvents()

    first_rect = menu.actionGeometry(action)
    last_rect = menu.actionGeometry(menu.actions()[-1])
    image = menu.grab().toImage()
    palette = menu.palette()
    bottom_margin = menu.height() - last_rect.bottom() - 1
    separator_center = menu.actionGeometry(separator).center()
    separator_color = image.pixelColor(separator_center)

    assert first_rect.top() == bottom_margin
    assert first_rect.top() > 0
    assert separator_color != palette.color(palette.ColorRole.Dark)
    assert separator_color.alpha() < palette.color(palette.ColorRole.Dark).alpha()
    menu.hide()


def test_modern_menu_accepts_pixmap_submenu_icons() -> None:
    menu = ModernMenu()
    pixmap = QPixmap(16, 16)

    submenu = menu.addMenu(pixmap, "Pixmap submenu")

    assert isinstance(submenu, ModernMenu)
    assert not submenu.icon().isNull()
