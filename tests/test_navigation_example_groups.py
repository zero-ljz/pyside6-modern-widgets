"""The gallery keeps comparison pages and custom controls in separate groups."""

from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QTranslator
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox, QPushButton, QTabWidget

from examples import navigation_view_example
from examples.navigation_view_example import ExampleWindow
from pyside6_modern_widgets import (
    ModernComboBox,
    ModernDialog,
    ModernFlyout,
    ModernMenu,
    ModernMenuBar,
    ModernMessageBox,
    ModernSegmentedControl,
    ModernSwitch,
    ModernTabWidget,
    ModernToolBar,
    NavigationPosition,
    NotificationManager,
)

_APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    ("language", "native_title", "custom_title", "segmented_title"),
    [
        ("en", "PySide6 built-in widgets", "Custom widgets", "Segmented control"),
        ("zh_CN", "PySide6 原生组件", "自定义组件", "分段控件"),
    ],
)
def test_gallery_navigation_groups(language, native_title, custom_title, segmented_title):
    translator = QTranslator()
    if language == "zh_CN":
        catalog = Path(__file__).parents[1] / "examples/translations/examples_zh_CN.qm"
        assert translator.load(str(catalog))
        assert _APP.installTranslator(translator)
    window = ExampleWindow()
    try:
        sidebar = window.navigation.sidebar
        assert window.navigation.count() == sidebar.count() == 20
        assert list(sidebar._groups) == [
            (NavigationPosition.TOP, native_title),
            (NavigationPosition.TOP, custom_title),
        ]
        native_group = sidebar._groups[(NavigationPosition.TOP, native_title)]
        custom_group = sidebar._groups[(NavigationPosition.TOP, custom_title)]
        assert all(
            sidebar._item_groups[sidebar.button(index)] is native_group for index in range(1, 13)
        )
        assert all(
            sidebar._item_groups[sidebar.button(index)] is custom_group for index in range(13, 19)
        )
        assert sidebar.button(0) not in sidebar._item_groups
        assert sidebar.button(19) not in sidebar._item_groups
        assert sidebar.button(14).text() == segmented_title
        assert sidebar.currentIndex() == window.navigation.currentIndex() == 0
        assert window.acrylic_switch.text() == (
            "启用亚克力背景" if language == "zh_CN" else "Enable acrylic background"
        )
        assert window.watercolor_switch.text() == (
            "启用水彩背景" if language == "zh_CN" else "Enable watercolor background"
        )
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

        segmented_page = window.navigation.widget(14)
        segments = segmented_page.findChildren(ModernSegmentedControl)
        assert len(segments) == 2
        assert not segments[1].isItemEnabled(1)
        window.segmented_control.setCurrentIndex(1)
        assert any(
            label.text() == "More details in a separate section."
            for label in segmented_page.findChildren(QLabel)
        )
    finally:
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_settings_acrylic_switch_updates_gallery_components():
    window = ExampleWindow()
    try:
        components = [
            *window.findChildren(ModernMenu),
            *window.findChildren(ModernMenuBar),
            *window.findChildren(ModernToolBar),
            *window.findChildren(ModernComboBox),
            *window.findChildren(ModernFlyout),
            *window.findChildren(NotificationManager),
        ]
        assert components
        assert window.acrylic_switch.isChecked()
        window.acrylic_switch.setChecked(False)
        assert all(not component.isAcrylicEnabled() for component in components)
        window.acrylic_switch.setChecked(True)
        assert all(component.isAcrylicEnabled() for component in components)
    finally:
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("supported", [False, True])
def test_settings_acrylic_switch_is_only_shown_on_windows_11(monkeypatch, supported):
    monkeypatch.setattr(navigation_view_example, "_supports_windows_acrylic", lambda: supported)
    window = ExampleWindow()
    try:
        assert window.acrylic_switch.isHidden() is not supported
    finally:
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_settings_watercolor_switch_updates_window_and_navigation_overlay():
    window = ExampleWindow()
    try:
        settings_layout = window.navigation.widget(19).layout()
        assert settings_layout.indexOf(window.watercolor_switch) < settings_layout.indexOf(
            window.wallpaper_switch
        )
        assert window.watercolor_switch.isChecked()
        assert isinstance(window.wallpaper_switch, ModernSwitch)
        assert window.wallpaper_switch.isEnabled()
        wallpaper_selected = window.wallpaper_switch.isChecked()
        window.watercolor_switch.setChecked(False)
        assert not window.isWatercolorEnabled()
        assert not window.navigation.sidebar.isWatercolorEnabled()
        assert not window.wallpaper_switch.isEnabled()
        window.wallpaper_switch.click()
        assert window.wallpaper_switch.isChecked() == wallpaper_selected
        window.watercolor_switch.setChecked(True)
        assert window.isWatercolorEnabled()
        assert window.navigation.sidebar.isWatercolorEnabled()
        assert window.wallpaper_switch.isEnabled()
        assert window.wallpaper_switch.isChecked() == wallpaper_selected
    finally:
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
