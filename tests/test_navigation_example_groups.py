"""The gallery keeps comparison pages and custom controls in separate groups."""

from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QTranslator
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton, QTabWidget

from examples.navigation_view_example import ExampleWindow
from pyside6_modern_widgets import (
    ModernDialog,
    ModernMessageBox,
    ModernTabWidget,
    NavigationPosition,
)

_APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    ("language", "native_title", "custom_title"),
    [
        ("en", "PySide6 built-in widgets", "Custom widgets"),
        ("zh_CN", "PySide6 原生组件", "自定义组件"),
    ],
)
def test_gallery_navigation_groups(language, native_title, custom_title):
    translator = QTranslator()
    if language == "zh_CN":
        catalog = Path(__file__).parents[1] / "examples/translations/examples_zh_CN.qm"
        assert translator.load(str(catalog))
        assert _APP.installTranslator(translator)
    window = ExampleWindow()
    try:
        sidebar = window.navigation.sidebar
        assert window.navigation.count() == sidebar.count() == 18
        assert list(sidebar._groups) == [
            (NavigationPosition.TOP, native_title),
            (NavigationPosition.TOP, custom_title),
        ]
        native_group = sidebar._groups[(NavigationPosition.TOP, native_title)]
        custom_group = sidebar._groups[(NavigationPosition.TOP, custom_title)]
        assert all(
            sidebar._item_groups[sidebar.button(index)] is native_group
            for index in range(1, 12)
        )
        assert all(
            sidebar._item_groups[sidebar.button(index)] is custom_group
            for index in range(12, 17)
        )
        assert sidebar.button(0) not in sidebar._item_groups
        assert sidebar.button(17) not in sidebar._item_groups
        assert sidebar.currentIndex() == window.navigation.currentIndex() == 0
    finally:
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        if language == "zh_CN":
            assert _APP.removeTranslator(translator)


def test_gallery_native_comparison_pages_have_both_working_controls(monkeypatch):
    window = ExampleWindow()
    try:
        dialog_page = window.navigation.widget(1)
        dialog_buttons = dialog_page.findChildren(QPushButton)
        opened_dialogs = []
        monkeypatch.setattr(window, "_show_dialog", opened_dialogs.append)
        for button in dialog_buttons:
            button.click()
        assert opened_dialogs == [QDialog, ModernDialog]

        message_page = window.navigation.widget(2)
        message_buttons = message_page.findChildren(QPushButton)
        assert len(message_buttons) == 10
        opened_messages = []
        monkeypatch.setattr(
            QMessageBox,
            "information",
            lambda *args: opened_messages.append((QMessageBox, args)),
        )
        monkeypatch.setattr(
            ModernMessageBox,
            "information",
            lambda *args: opened_messages.append((ModernMessageBox, args)),
        )
        message_buttons[0].click()
        message_buttons[1].click()
        assert [box_type for box_type, _args in opened_messages] == [
            QMessageBox,
            ModernMessageBox,
        ]

        tab_page = window.navigation.widget(5)
        native_tabs = tab_page.findChildren(QTabWidget)
        assert any(type(tabs) is QTabWidget for tabs in native_tabs)
        assert any(type(tabs) is ModernTabWidget for tabs in native_tabs)
        assert [window.native_tab_widget.tabText(i) for i in range(2)] == [
            window.tab_widget.tabText(i) for i in range(2)
        ]
        assert window.native_tab_widget.count() == window.tab_widget.count() == 2
    finally:
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
