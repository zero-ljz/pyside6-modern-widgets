from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import NavigationSidebar

_APP = QApplication.instance() or QApplication([])


def test_navigation_toggle_only_uses_hover_style_for_keyboard_focus() -> None:
    sidebar = NavigationSidebar()
    button = sidebar.toggleButton

    button.focusInEvent(QFocusEvent(QFocusEvent.Type.FocusIn, Qt.FocusReason.TabFocusReason))
    assert button._keyboard_focus_visible

    QTest.mousePress(button, Qt.MouseButton.LeftButton)
    assert not button._keyboard_focus_visible
    QTest.mouseRelease(button, Qt.MouseButton.LeftButton)

    sidebar.close()
