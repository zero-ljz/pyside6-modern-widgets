"""Integration coverage for the translated gallery launcher and its owned demo."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QLocale, QPoint, QTranslator
from PySide6.QtGui import QCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton
from shiboken6 import isValid

from examples.navigation_view_example import ExampleWindow
from pyside6_modern_widgets import DockSide

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
        demo.edge_buttons[0].click()
        QTest.qWait(300)
        assert demo.dock.dockSide() == DockSide.LEFT
        expected_status = (
            "停靠边缘：左侧 | 把手已隐藏" if language == "zh_CN" else "Edge: Left | Handle hidden"
        )
        assert demo.status.text() == expected_status
        demo.auto_hide_switch.setChecked(True)
        demo.dock.collapse()
        assert demo.dock.isCollapsed()
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
        demo.close()
        assert window.isVisible()
        assert not demo.floating_window.isVisible()
        launch.click()
        assert window.edge_dock_example is demo and demo.isVisible()
        demo.dock_to(DockSide.LEFT)
        QTest.qWait(300)
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
