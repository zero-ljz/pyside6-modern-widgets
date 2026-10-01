from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QSlider

from pyside6_modern_widgets import DARK_THEME, ModernSlider

_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def slider(theme_manager_instance):
    widget = ModernSlider()
    widget.setRange(0, 100)
    widget.resize(widget.sizeHint())
    yield widget
    widget.close()
    widget.deleteLater()
    _APP.processEvents()


def test_native_slider_range_and_keyboard_behavior(slider):
    assert isinstance(slider, QSlider)
    assert slider.sizeHint() == QSize(84, 20)
    assert slider.minimumSizeHint() == QSize(22, 20)
    changed = []
    slider.valueChanged.connect(changed.append)
    slider.setValue(35)
    slider.show()
    _APP.processEvents()
    QTest.keyClick(slider, Qt.Key.Key_Right)
    assert slider.value() == 36
    assert changed == [35, 36]
    QTest.mouseClick(slider, Qt.MouseButton.LeftButton, pos=QPoint(slider.width() - 11, 10))
    assert slider.value() == 100
    slider.setEnabled(False)
    QTest.keyClick(slider, Qt.Key.Key_Right)
    assert slider.value() == 100


def test_theme_and_palette_update_paint(slider):
    slider.setValue(50)
    palette = QPalette()
    palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent, QColor("#197F64"))
    slider.setPalette(palette)
    image = slider.grab().toImage()
    assert image.pixelColor(42, 10) == QColor("#197F64")
    assert image.pixelColor(34, 2) != QColor("#197F64")
    slider.setTheme(replace(DARK_THEME, accent="#AE66DD"))
    assert slider.grab().toImage().pixelColor(42, 10) == QColor("#AE66DD")
    slider.setTheme(None)
    assert slider.grab().toImage().pixelColor(42, 10) == QColor("#197F64")
    slider.setOrientation(Qt.Orientation.Vertical)
    assert slider.sizeHint() == QSize(20, 84)
    assert slider.minimumSizeHint() == QSize(20, 22)
    slider.resize(slider.sizeHint())
    slider.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    assert slider._position_for_value(0) > slider._position_for_value(100)
    slider.setInvertedAppearance(True)
    assert slider._position_for_value(0) < slider._position_for_value(100)


def test_constructor_forms_and_theme_validation(slider):
    child = ModernSlider(slider)
    vertical = ModernSlider(Qt.Orientation.Vertical, slider)
    assert child.parentWidget() is slider
    assert child.orientation() == Qt.Orientation.Horizontal
    assert vertical.orientation() == Qt.Orientation.Vertical
    with pytest.raises(TypeError, match="parent specified twice"):
        ModernSlider(slider, slider)
    with pytest.raises(TypeError, match="theme must be"):
        slider.setTheme("dark")
