from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernSegmentedControl,
    ModernWindow,
    ThemeMode,
)

_APP = QApplication.instance() or QApplication([])


def test_exclusive_buttons_ids_signals_and_compact_layout(theme_manager_instance):
    control = ModernSegmentedControl(["All", "Open", "Closed"])
    selected = []
    control.itemActivated.connect(selected.append)
    try:
        assert control.count() == 3
        assert all(
            isinstance(button, QPushButton) and button.isCheckable()
            for button in [control.button(i) for i in range(control.count())]
        )
        assert control.currentIndex() == 0
        assert control.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Maximum
        assert control.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Fixed
        assert control.layout().contentsMargins().left() == 1
        assert control.layout().contentsMargins().top() == 1
        assert control.layout().spacing() == 0
        control.show()
        _APP.processEvents()
        assert control.button(0).minimumHeight() >= 26
        assert control.button(0).minimumWidth() >= 46
        QTest.mouseClick(control.button(2), Qt.MouseButton.LeftButton)
        assert control.currentIndex() == 2
        assert [
            button.isChecked() for button in [control.button(i) for i in range(control.count())]
        ] == [False, False, True]
        assert selected == [2]
        control.button(1).setChecked(True)
        assert control.currentIndex() == 1
        assert selected == [2]
        control.button(1).setEnabled(False)
        assert "color: #8A8A8A" in control.styleSheet()
    finally:
        control.close()
        control.deleteLater()


def test_empty_and_single_controls(theme_manager_instance):
    empty = ModernSegmentedControl([])
    single = ModernSegmentedControl(["Only"])
    try:
        assert empty.count() == 0
        assert empty.currentIndex() == -1
        assert single.currentIndex() == 0
    finally:
        empty.deleteLater()
        single.deleteLater()


def test_global_theme_override_and_inheritance_after_reparenting(theme_manager_instance):
    manager = theme_manager_instance
    window = ModernWindow(theme=DARK_THEME)
    container = QWidget(window)
    QVBoxLayout(window).addWidget(container)
    control = ModernSegmentedControl(["First", "Second"], container)
    try:
        window.show()
        _APP.processEvents()
        assert control.theme() == DARK_THEME
        assert DARK_THEME.tab_selected in control.styleSheet()
        window.setTheme(replace(DARK_THEME, tab_selected="#9155AB"))
        _APP.processEvents()
        assert "#9155AB" in control.styleSheet()
        control.setTheme(LIGHT_THEME)
        manager.setMode(ThemeMode.DARK)
        assert control.theme() == LIGHT_THEME
        assert LIGHT_THEME.tab_selected in control.styleSheet()
        control.setTheme(None)
        assert "#9155AB" in control.styleSheet()
        control.setParent(None)
        manager.setMode(ThemeMode.LIGHT)
        assert control.theme() == LIGHT_THEME
        assert LIGHT_THEME.tab_selected in control.styleSheet()
        manager.setMode(ThemeMode.DARK)
        assert control.theme() == DARK_THEME
        assert DARK_THEME.tab_selected in control.styleSheet()
        assert DARK_THEME.text_disabled in control.styleSheet()
        assert DARK_THEME.tab_hover in control.styleSheet()
    finally:
        control.close()
        control.deleteLater()
        window.close()
        window.deleteLater()


def test_inherited_token_only_change_while_hidden_and_ancestor_reparent(theme_manager_instance):
    first = ModernWindow(theme=DARK_THEME)
    second = ModernWindow(theme=LIGHT_THEME)
    container = QWidget(first)
    QVBoxLayout(first).addWidget(container)
    control = ModernSegmentedControl(["One", "Two"], container)
    try:
        first.setTheme(replace(DARK_THEME, tab_selected="#734CB2"))
        first.show()
        _APP.processEvents()
        assert "#734CB2" in control.styleSheet()
        container.setParent(second)
        QVBoxLayout(second).addWidget(container)
        assert control.theme() == LIGHT_THEME
        assert LIGHT_THEME.tab_selected in control.styleSheet()
        second.setTheme(replace(LIGHT_THEME, tab_hover="#B5D4ED"))
        second.show()
        _APP.processEvents()
        assert "#B5D4ED" in control.styleSheet()
    finally:
        first.close()
        first.deleteLater()
        second.close()
        second.deleteLater()
