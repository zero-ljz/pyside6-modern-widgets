from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QLocale, QPoint, QTranslator
from PySide6.QtWidgets import QApplication, QLabel, QTabBar

from pyside6_modern_widgets import (
    ModernDialog,
    ModernNotification,
    ModernToolBar,
    ModernWindow,
    NavigationSidebar,
    TabView,
    load_translator,
    modern_menu,
)

_APP = QApplication.instance() or QApplication([])


def test_load_translator_uses_bundled_locale_fallbacks() -> None:
    assert load_translator("zh_CN") is not None
    assert load_translator(QLocale("zh-CN")) is not None
    assert load_translator("ja_JP") is None


def test_example_catalog_is_complete_and_loadable() -> None:
    catalog = Path(__file__).parents[1] / "examples" / "translations" / "examples_zh_CN.qm"
    translator = QTranslator()
    assert translator.load(str(catalog))
    assert _APP.installTranslator(translator)
    try:
        assert QCoreApplication.translate("ExampleWindow", "Home") == "主页"
        assert QCoreApplication.translate("ExampleWindow", "Open dialog") == "打开对话框"
        assert QCoreApplication.translate("TabViewWindow", "Document %1") == "文档 %1"
    finally:
        assert _APP.removeTranslator(translator)


def test_language_change_retranslates_existing_widgets_and_portable_menu(monkeypatch) -> None:
    window = ModernWindow()
    notification = ModernNotification("Build", kind="success")
    notification.setProgress(-1)
    toolbar = ModernToolBar()
    sidebar = NavigationSidebar()
    tabs = TabView()
    tabs.addTab(QLabel("Contents"), "README")
    dialog = ModernDialog()
    widgets = [window, notification, toolbar, sidebar, tabs, dialog]
    close_button = tabs.tabBar().tabButton(0, QTabBar.ButtonPosition.RightSide)
    assert close_button is not None
    assert window.titleBar.closeButton.toolTip() == "Close"
    assert window.titleBar.pinButton.toolTip() == "Pin"
    assert notification.closeButton.toolTip() == "Dismiss"
    assert toolbar.overflowButton().toolTip() == "More actions"
    assert sidebar.toggleButton.toolTip() == "Toggle navigation"
    assert tabs._add_button.toolTip() == "New tab"
    assert close_button.accessibleName() == "Close README"

    translator = load_translator("zh_CN", _APP)
    assert translator is not None
    assert _APP.installTranslator(translator)
    _APP.processEvents()
    try:
        assert window.titleBar.closeButton.toolTip() == "关闭"
        assert window.titleBar.pinButton.toolTip() == "置顶"
        assert notification.closeButton.toolTip() == "关闭"
        assert notification._progress_bar.toolTip() == "正在处理…"
        assert notification.accessibleName() == "成功：Build"
        assert toolbar.overflowButton().toolTip() == "更多操作"
        assert sidebar.toggleButton.toolTip() == "切换导航栏"
        assert tabs._add_button.toolTip() == "新建标签页"
        assert close_button.accessibleName() == "关闭 README"

        monkeypatch.setattr(modern_menu.ModernMenu, "popup", lambda *_args: None)
        dialog._system_menu_controller.show_portable(QPoint())
        actions = [
            action for action in dialog._portable_system_menu.actions() if not action.isSeparator()
        ]
        assert [action.text() for action in actions] == ["还原", "最小化", "最大化", "关闭"]
    finally:
        assert _APP.removeTranslator(translator)
        _APP.processEvents()
        for widget in widgets:
            widget.close()
            widget.deleteLater()

    assert window.titleBar.closeButton.toolTip() == "Close"
    assert window.titleBar.pinButton.toolTip() == "Pin"
    assert notification.closeButton.toolTip() == "Dismiss"
    assert toolbar.overflowButton().toolTip() == "More actions"
    assert sidebar.toggleButton.toolTip() == "Toggle navigation"
    assert tabs._add_button.toolTip() == "New tab"
    assert close_button.accessibleName() == "Close README"
