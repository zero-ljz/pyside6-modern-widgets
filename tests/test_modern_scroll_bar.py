from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QAbstractAnimation, QPoint, QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QScrollArea,
    QScrollBar,
    QStyle,
    QStyleFactory,
    QStyleOptionSlider,
    QWidget,
)

from pyside6_modern_widgets import DARK_THEME, LIGHT_THEME, ModernScrollBar, NavigationSidebar

_APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize("orientation", [Qt.Orientation.Vertical, Qt.Orientation.Horizontal])
def test_native_range_and_fusion_geometry(orientation):
    bar = ModernScrollBar(orientation)
    native = QScrollBar(orientation)
    native.setStyle(QStyleFactory.create("Fusion"))
    bar.setRange(0, 100)
    bar.setPageStep(20)
    native.setRange(0, 100)
    native.setPageStep(20)
    bar.resize(14, 240) if orientation == Qt.Orientation.Vertical else bar.resize(240, 14)
    bar.show()
    _APP.processEvents()
    assert isinstance(bar, QScrollBar)
    assert bar.sizeHint() == native.sizeHint()
    changed = []
    bar.valueChanged.connect(changed.append)
    bar.setValue(50)
    native.setValue(50)
    key = Qt.Key.Key_Down if orientation == Qt.Orientation.Vertical else Qt.Key.Key_Right
    QTest.keyClick(bar, key)
    QTest.keyClick(native, key)
    assert bar.value() == native.value()
    assert changed == [50, native.value()]

    option = QStyleOptionSlider()
    bar.initStyleOption(option)
    handle = bar.style().subControlRect(
        QStyle.ComplexControl.CC_ScrollBar, option, QStyle.SubControl.SC_ScrollBarSlider, bar
    )
    QTest.mousePress(bar, Qt.MouseButton.LeftButton, pos=handle.center())
    assert bar.isSliderDown()
    QTest.mouseRelease(bar, Qt.MouseButton.LeftButton, pos=handle.center())
    assert not bar.isSliderDown()
    bar.close()
    native.close()


def test_theme_inheritance_hover_width_and_rtl():
    owner = NavigationSidebar(theme=DARK_THEME)
    bar = ModernScrollBar(Qt.Orientation.Horizontal, owner)
    bar.setRange(0, 100)
    bar.resize(240, 14)
    assert bar.theme() == DARK_THEME
    owner.setTheme(LIGHT_THEME)
    assert bar.theme() == LIGHT_THEME
    bar.setTheme(replace(DARK_THEME, scrollbar="#345678"))
    assert bar.theme().scrollbar == "#345678"
    bar.setTheme(None)
    assert bar.theme() == LIGHT_THEME
    bar.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    bar.setTheme(replace(LIGHT_THEME, scrollbar="#345678", scrollbar_hover="#9ABCDE"))

    owner.show()
    bar.show()
    _APP.processEvents()
    option = QStyleOptionSlider()
    bar.initStyleOption(option)
    handle = bar.style().subControlRect(
        QStyle.ComplexControl.CC_ScrollBar, option, QStyle.SubControl.SC_ScrollBarSlider, bar
    )
    sample_x = handle.center().x()
    idle = bar.grab().toImage()
    idle_width = sum(idle.pixelColor(sample_x, y) == QColor("#345678") for y in range(bar.height()))
    QTest.mouseMove(bar, QPoint(120, 7))
    QTest.qWait(150)
    for _ in range(50):
        if bar._hover_animation.state() == QAbstractAnimation.State.Stopped:
            break
        QTest.qWait(10)
    assert bar._hover_progress == pytest.approx(1.0)
    hovered = bar.grab().toImage()
    hover_width = sum(
        hovered.pixelColor(sample_x, y) == QColor("#9ABCDE") for y in range(bar.height())
    )
    assert hover_width > idle_width > 0
    bar.hide()
    assert bar._hover_progress == 0.0
    bar.show()
    QTest.mouseMove(bar, QPoint(-10, -10))
    QTest.qWait(150)
    for _ in range(50):
        if bar._hover_animation.state() == QAbstractAnimation.State.Stopped:
            break
        QTest.qWait(10)
    assert bar._hover_progress == pytest.approx(0.0)
    owner.close()


def test_scroll_area_can_install_both_orientations():
    area = QScrollArea()
    area.resize(120, 120)
    area.setWidget(QWidget())
    vertical = ModernScrollBar(Qt.Orientation.Vertical)
    horizontal = ModernScrollBar(Qt.Orientation.Horizontal)
    area.setVerticalScrollBar(vertical)
    area.setHorizontalScrollBar(horizontal)
    assert area.verticalScrollBar() is vertical
    assert area.horizontalScrollBar() is horizontal
    area.close()


@pytest.mark.parametrize("orientation", [Qt.Orientation.Vertical, Qt.Orientation.Horizontal])
@pytest.mark.parametrize(
    "direction", [Qt.LayoutDirection.LeftToRight, Qt.LayoutDirection.RightToLeft]
)
def test_arrow_glyphs_align_with_expanded_thumb(orientation, direction):
    bar = ModernScrollBar(
        orientation,
        theme=replace(
            LIGHT_THEME,
            scrollbar="#00B000",
            scrollbar_hover="#00B000",
            text_muted="#F00000",
        ),
    )
    bar.setLayoutDirection(direction)
    bar.setRange(0, 100)
    bar.setPageStep(20)
    bar.resize(QSize(72, 240) if orientation == Qt.Orientation.Vertical else QSize(240, 36))
    bar.show()
    _APP.processEvents()
    bar._set_hover_progress(1.0)
    image = bar.grab().toImage()
    horizontal = orientation == Qt.Orientation.Horizontal

    arrows = []
    thumb = []
    for x in range(image.width()):
        for y in range(image.height()):
            color = image.pixelColor(x, y)
            position = y if horizontal else x
            if color.red() > 160 and color.green() < 100 and color.blue() < 100:
                arrows.append(position)
            if color.green() > 120 and color.red() < 100 and color.blue() < 100:
                thumb.append(position)
    assert arrows and thumb
    assert abs(sum(arrows) / len(arrows) - sum(thumb) / len(thumb)) <= (
        1.5 * image.devicePixelRatio()
    )
    bar.close()
