from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import ModernMenu
from pyside6_modern_widgets.modern_menu import _ACRYLIC_INPUT_ALPHA

_APP = QApplication.instance() or QApplication([])


def _pixel_at_logical_position(menu: ModernMenu, point: QPoint) -> QColor:
    pixmap = menu.grab()
    scale = pixmap.devicePixelRatio()
    return pixmap.toImage().pixelColor(
        round(point.x() * scale),
        round(point.y() * scale),
    )


def test_acrylic_menu_keeps_blank_action_space_in_the_input_surface() -> None:
    menu = ModernMenu()
    action = menu.addAction("Action")
    menu.setFixedWidth(220)
    menu.show()
    _APP.processEvents()

    menu._rounded_style.setNativeAcrylic(True)
    menu.update()
    _APP.processEvents()

    action_rect = menu.actionGeometry(action)
    blank_point = QPoint(action_rect.right() - 8, action_rect.center().y())

    assert menu.actionAt(blank_point) is action
    assert _pixel_at_logical_position(menu, blank_point).alpha() == _ACRYLIC_INPUT_ALPHA
    assert _pixel_at_logical_position(menu, QPoint(0, 0)).alpha() == 0
    menu.hide()
