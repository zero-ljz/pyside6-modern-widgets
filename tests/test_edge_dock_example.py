"""Integration coverage for the translated gallery launcher and its owned demo."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QLocale, QPoint, QSize, QTranslator
from PySide6.QtGui import QCursor
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication, QPushButton
from shiboken6 import isValid

from examples.navigation_view_example import ExampleWindow
from pyside6_modern_widgets import DockHandleMode, DockSide, EdgeDockController

_APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize("language", ["en", "zh_CN"])
def test_gallery_launch_reuse_and_cleanup_in_both_languages(
    theme_manager_instance, monkeypatch, language
):
    translator = QTranslator()
    if language == "zh_CN":
        catalog = Path(__file__).parents[1] / "examples/translations/examples_zh_CN.qm"
        assert translator.load(str(catalog))
        assert _APP.installTranslator(translator)
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: QPoint(100000, 100000)))
    # Synthetic button clicks should not depend on the user's physical mouse
    # buttons when this integration test runs on the native Windows desktop.
    monkeypatch.setattr(
        EdgeDockController, "_buttons_pressed", staticmethod(lambda **_kwargs: False)
    )
    window = ExampleWindow()
    try:
        window.show()
        _APP.processEvents()
        launch_text = "打开边缘停靠演示" if language == "zh_CN" else "Open edge-docking demo"
        launch = next(b for b in window.findChildren(QPushButton) if b.text() == launch_text)
        assert window.edge_dock_example is None
        launch.click()
        demo = window.edge_dock_example
        assert demo is not None and demo.isWindow() and demo.isVisible()
        assert demo.parentWidget() is window
        assert demo.floating_window.isVisible()
        expected_title = (
            "屏幕边缘停靠控制" if language == "zh_CN" else "Screen-edge docking controls"
        )
        assert demo.windowTitle() == expected_title
        demo.auto_hide_switch.setChecked(False)
        finished = QSignalSpy(demo.dock._animation.finished)
        demo.edge_buttons[0].click()
        assert finished.wait(1000)
        assert demo.dock.dockSide() == DockSide.LEFT
        expected_status = (
            "停靠边缘：左侧 | 把手已隐藏" if language == "zh_CN" else "Edge: Left | Handle hidden"
        )
        assert demo.status.text() == expected_status
        demo.save_position_button.click()
        saved = demo.saved_placement
        assert saved is not None and saved.side == DockSide.LEFT
        demo.collapse_button.click()  # Explicit folding also works with auto-hide off.
        assert demo.dock.isCollapsed()
        demo.dock.setPlacement(None)
        demo.restore_position_button.click()
        assert demo.dock.placement() == saved
        demo.collapse_button.click()
        assert demo.dock.isCollapsed()
        demo.auto_hide_switch.setChecked(True)
        demo.handle_mode.setCurrentIndex(1)
        demo.handle_style.setCurrentIndex(1)
        demo.handle_icon_size.setValue(32)
        assert demo.dock.isCollapsed()
        assert demo.dock.handleMode() == DockHandleMode.CLICK
        assert demo.dock._handle.size() == QSize(44, 44)
        assert not demo.dock.handleIcon().isNull()
        assert demo.handle_style.currentText() == (
            "应用图标" if language == "zh_CN" else "Application icon"
        )
        assert demo.handle_mode.currentText() == ("仅点击" if language == "zh_CN" else "Click only")
        assert demo.dock.handleToolTip() == (
            "恢复悬浮工具" if language == "zh_CN" else "Restore floating tool"
        )
        demo.handle_mode.setCurrentIndex(2)
        assert demo.dock.handleMode() == DockHandleMode.DRAG_OR_CLICK
        assert demo.handle_mode.isEnabled()
        assert demo.handle_mode.currentText() == (
            "拖动或点击" if language == "zh_CN" else "Drag or click"
        )
        launch.click()
        assert window.edge_dock_example is demo
        assert demo.floating_window.isVisible()
        assert not demo.dock.isCollapsed()
        demo.replace_drag_strip()
        assert demo.drag_strip.text() == (
            "新的拖动区域 - 拖动此处" if language == "zh_CN" else "New drag strip - drag me"
        )
        demo.toggle_attachment()
        assert demo.attach_button.text() == (
            "绑定停靠" if language == "zh_CN" else "Attach docking"
        )
        demo.toggle_attachment()
        assert demo.dock.isEnabled()
        assert demo.dock.handleMode() == DockHandleMode.DRAG_OR_CLICK
        assert demo.dock.handleIconSize() == 32
        assert not demo.dock.handleIcon().isNull()
        assert demo.dock.handleMode() == DockHandleMode.DRAG_OR_CLICK
        demo.close()
        assert window.isVisible()
        assert not demo.floating_window.isVisible()
        launch.click()
        assert window.edge_dock_example is demo and demo.isVisible()
        finished = QSignalSpy(demo.dock._animation.finished)
        demo.dock_to(DockSide.LEFT)
        assert finished.wait(1000)
        demo.dock.collapse()
        assert demo.dock.isCollapsed()
        window.close()
        _APP.processEvents()
        assert not demo.isVisible()
        assert not demo.floating_window.isVisible()
        assert not demo.dock._handle.isVisible()
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        if language == "zh_CN":
            _APP.removeTranslator(translator)
    assert not isValid(demo)


def test_example_catalog_has_no_unfinished_messages():
    catalog = Path(__file__).parents[1] / "examples/translations/examples_zh_CN.ts"
    for message in ET.parse(catalog).iter("message"):
        translation = message.find("translation")
        assert translation is not None
        assert translation.get("type") != "unfinished", message.findtext("source")
        assert translation.text, message.findtext("source")


@pytest.mark.parametrize("language", ["en", "zh_CN"])
def test_example_language_override(monkeypatch, language):
    from examples._example_i18n import example_locale

    monkeypatch.setattr("sys.argv", ["example.py", "--language", language])
    assert example_locale() == QLocale(language)
