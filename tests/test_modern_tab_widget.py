from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QLabel, QTabWidget

from pyside6_modern_widgets import DARK_THEME, LIGHT_THEME, ModernTabWidget, ThemeMode


def test_modern_tab_widget_preserves_native_fixed_tab_semantics():
    tabs = ModernTabWidget()
    first, second = QLabel("First"), QLabel("Second")
    changes = []
    tabs.currentChanged.connect(changes.append)
    try:
        assert isinstance(tabs, QTabWidget)
        assert tabs.documentMode()
        assert not tabs.tabBar().drawBase()
        assert not tabs.tabBar().expanding()
        assert not tabs.tabsClosable()
        assert not tabs.isMovable()

        assert tabs.addTab(first, "General") == 0
        assert tabs.addTab(second, "Advanced") == 1
        tabs.setCurrentIndex(1)
        assert tabs.currentWidget() is second
        assert changes[-1] == 1

        tab_rect = tabs.tabBar().tabRect(1)
        indicator = tabs.tabBar()._indicator_rect(1)
        assert indicator.left() == tab_rect.left() + 6
        assert indicator.right() == tab_rect.right() - 6
        assert indicator.height() == 2
    finally:
        tabs.deleteLater()


def test_modern_tab_widget_follows_global_theme_and_supports_override(
    theme_manager_instance,
):
    manager = theme_manager_instance
    following = ModernTabWidget()
    fixed = ModernTabWidget(theme=LIGHT_THEME)
    try:
        manager.setMode(ThemeMode.DARK)
        assert following.theme() == DARK_THEME
        assert fixed.theme() == LIGHT_THEME
        assert following.palette().color(QPalette.ColorRole.Text) == QColor(DARK_THEME.text)
        assert DARK_THEME.control_hover in following.tabBar().styleSheet()

        fixed.setTheme(None)
        assert fixed.theme() == DARK_THEME
    finally:
        following.deleteLater()
        fixed.deleteLater()
