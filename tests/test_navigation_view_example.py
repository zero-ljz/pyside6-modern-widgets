from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from examples.navigation_view_example import ExampleWindow
from pyside6_modern_widgets import ModernTabWidget, ThemeMode, theme_manager

_APP = QApplication.instance() or QApplication([])


def test_title_bar_theme_button_replaces_home_and_search() -> None:
    manager = theme_manager()
    previous_mode = manager.mode()
    window = None
    try:
        manager.setMode(ThemeMode.LIGHT)
        window = ExampleWindow()
        title_bar = window.titleBar
        assert title_bar is not None
        assert title_bar.left_layout.count() == 1
        assert title_bar.right_layout.indexOf(window.theme_button) >= 0
        assert not any(
            isinstance(widget, QLineEdit) for widget in title_bar.findChildren(QLineEdit)
        )
        assert [
            widget for widget in title_bar.findChildren(QPushButton) if widget.text() == "Home"
        ] == []

        assert window.theme_button.text() == "Dark"
        window.theme_button.click()
        assert manager.mode() == ThemeMode.DARK
        assert window.theme_button.text() == "Light"
        window.theme_button.click()
        assert manager.mode() == ThemeMode.LIGHT
        assert window.theme_button.text() == "Dark"

        manager.setMode(ThemeMode.DARK)
        assert window.theme_button.text() == "Light"
    finally:
        if window is not None:
            window.close()
        manager.setMode(previous_mode)


def test_subpages_have_no_theme_button_rows() -> None:
    window = ExampleWindow()
    try:
        for index in (4, 5, 6, 7, 8, 9):
            page = window.navigation.stackedWidget.widget(index)
            labels = {button.text() for button in page.findChildren(QPushButton)}
            assert not labels.intersection({"System", "Light", "Dark"})
    finally:
        window.close()


def test_tab_widget_page_switches_fixed_sections_and_follows_theme() -> None:
    manager = theme_manager()
    previous_mode = manager.mode()
    window = None
    try:
        manager.setMode(ThemeMode.LIGHT)
        window = ExampleWindow()
        window.navigation.setCurrentIndex(5)
        page = window.navigation.stackedWidget.currentWidget()
        tabs = window.tab_widget
        assert isinstance(tabs, ModernTabWidget)
        assert page is not None and tabs.parent() is page
        assert tabs.count() == 2
        assert [tabs.tabText(index) for index in range(tabs.count())] == ["General", "Details"]
        assert not tabs.tabsClosable()
        assert not tabs.isMovable()

        first = tabs.currentWidget()
        tabs.tabBar().setCurrentIndex(1)
        assert tabs.currentIndex() == 1
        assert tabs.currentWidget() is not first
        assert tabs.count() == 2

        window.theme_button.click()
        assert manager.mode() == ThemeMode.DARK
        assert tabs.theme() == manager.theme()
    finally:
        if window is not None:
            window.close()
        manager.setMode(previous_mode)
