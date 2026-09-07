from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QPalette, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMenuBar, QStyle, QWidget

from pyside6_modern_widgets import ModernMenu, ModernMenuBar, ModernWindow

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
    assert image.pixelColor(menu.width() - 8, first_item_y).alpha() == 255
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
    surface_color = palette.color(QPalette.ColorRole.Window)

    def color_distance(left: QColor, right: QColor) -> int:
        return sum(abs(a - b) for a, b in zip(left.getRgb()[:3], right.getRgb()[:3]))

    assert first_rect.top() == bottom_margin
    assert first_rect.top() > 0
    assert separator_color != palette.color(palette.ColorRole.Dark)
    assert color_distance(separator_color, surface_color) < color_distance(
        palette.color(QPalette.ColorRole.Dark), surface_color
    )
    assert separator_color.alpha() == 255
    menu.hide()


def test_modern_menu_uses_opaque_ancestor_surface_for_a_transparent_palette() -> None:
    parent = QWidget()
    parent_palette = QPalette(parent.palette())
    parent_palette.setColor(QPalette.ColorRole.Window, QColor("#e1e4e8"))
    parent.setPalette(parent_palette)
    menu = ModernMenu(parent)
    transparent_palette = QPalette(menu.palette())
    transparent_palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 0))
    menu.setPalette(transparent_palette)
    action = menu.addAction("Action")
    menu.show()
    _APP.processEvents()

    image = menu.grab().toImage()
    surface = image.pixelColor(menu.width() - 8, menu.actionGeometry(action).center().y())

    assert surface.name() == "#e1e4e8"
    assert surface.alpha() == 255
    menu.hide()


def test_windows_acrylic_requires_windows_11(monkeypatch) -> None:
    from pyside6_modern_widgets import modern_menu

    class WindowsVersion:
        build = 19045

    monkeypatch.setattr(modern_menu.sys, "platform", "win32")
    monkeypatch.setattr(modern_menu.QApplication, "platformName", lambda: "windows")
    monkeypatch.setattr(modern_menu.sys, "getwindowsversion", WindowsVersion, raising=False)

    assert not modern_menu._supports_windows_acrylic()

    WindowsVersion.build = 22000

    assert modern_menu._supports_windows_acrylic()


def test_modern_menu_requires_native_rounding_before_enabling_acrylic(monkeypatch) -> None:
    from pyside6_modern_widgets import modern_menu

    acrylic_attempts: list[ModernMenu] = []
    monkeypatch.setattr(modern_menu, "_enable_windows_rounded_corners", lambda *_args: False)
    monkeypatch.setattr(
        modern_menu,
        "_enable_windows_acrylic",
        lambda menu: acrylic_attempts.append(menu) or True,
    )
    menu = ModernMenu()
    menu.addAction("Action")
    menu.show()
    _APP.processEvents()

    assert acrylic_attempts == []
    assert not menu._rounded_style._native_acrylic
    menu.hide()


def test_modern_menu_accepts_pixmap_submenu_icons() -> None:
    menu = ModernMenu()
    pixmap = QPixmap(16, 16)

    submenu = menu.addMenu(pixmap, "Pixmap submenu")

    assert isinstance(submenu, ModernMenu)
    assert not submenu.icon().isNull()


def test_modern_menu_bar_creates_modern_menus_and_preserves_supplied_menus() -> None:
    parent = QWidget()
    menu_bar = ModernMenuBar(parent)
    icon = QIcon(QPixmap(16, 16))
    pixmap = QPixmap(16, 16)

    file_menu = menu_bar.addMenu("&File")
    view_menu = menu_bar.addMenu(icon, "&View")
    help_menu = menu_bar.addMenu(pixmap, "&Help")
    native_menu = QMenu("Native", menu_bar)
    native_action = menu_bar.addMenu(native_menu)

    assert isinstance(menu_bar, QMenuBar)
    assert menu_bar.parent() is parent
    assert isinstance(file_menu, ModernMenu)
    assert file_menu.parent() is parent
    recent_menu = file_menu.addMenu("Recent")
    assert isinstance(recent_menu, ModernMenu)
    assert isinstance(view_menu, ModernMenu)
    assert view_menu.icon().cacheKey() == icon.cacheKey()
    assert isinstance(help_menu, ModernMenu)
    assert not help_menu.icon().isNull()
    assert native_action is native_menu.menuAction()
    assert native_menu.menuAction() in menu_bar.actions()

    menu_bar.setStyleSheet("QMenuBar { background: transparent; }")
    file_menu.show()
    _APP.processEvents()
    assert file_menu.style() is file_menu._rounded_style
    file_menu.hide()


def test_modern_window_uses_modern_menus() -> None:
    window = ModernWindow()
    menu_bar = window.menuBar()

    assert isinstance(menu_bar, ModernMenuBar)
    assert isinstance(menu_bar.addMenu("File"), ModernMenu)
    assert window.titleBar is not None
    assert isinstance(window.titleBar.windowMenu, ModernMenu)
