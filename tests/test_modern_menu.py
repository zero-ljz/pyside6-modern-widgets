from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QActionGroup, QColor, QIcon, QImage, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QApplication, QStyle, QStyleOption, QStyleOptionMenuItem

from pyside6_modern_widgets import DARK_THEME, LIGHT_THEME, ModernMenu, palette_for_theme
from pyside6_modern_widgets.modern_menu import _ACRYLIC_INPUT_ALPHA, _windows_acrylic_tint

_APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    "surface, tint",
    [
        ("#FFFFFF", "#F0F0F0"),
        ("#F0F0F0", "#F0F0F0"),
        ("#2B2B2B", "#2B2B2B"),
        ("#204060", "#204060"),
    ],
)
def test_native_acrylic_tint_preserves_backdrop_without_changing_palette(surface, tint):
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(surface))
    assert _windows_acrylic_tint(palette).toRgb() == QColor(tint)
    assert palette.color(QPalette.ColorRole.Window) == QColor(surface)


def test_unsupported_acrylic_keeps_opaque_menu_surface():
    menu = ModernMenu()
    menu.addAction("Action")
    menu.setFixedWidth(220)
    menu.show()
    _APP.processEvents()
    try:
        assert not menu._rounded_style._native_acrylic
        assert _pixel_at_logical_position(menu, QPoint(180, 15)).alpha() == 255
    finally:
        menu.close()


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


@pytest.mark.parametrize(
    ("element", "tip_offset"),
    [
        (QStyle.PrimitiveElement.PE_IndicatorArrowRight, 2),
        (QStyle.PrimitiveElement.PE_IndicatorArrowLeft, -2),
    ],
)
def test_submenu_indicator_is_an_outlined_chevron(element, tip_offset):
    menu = ModernMenu()
    option = QStyleOption()
    option.initFrom(menu)
    option.rect = QRect(0, 0, 20, 20)
    image = QImage(20, 20, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    menu.style().drawPrimitive(element, option, painter, menu)
    painter.end()

    center = option.rect.center()
    assert image.pixelColor(center.x() + tip_offset, center.y()).alpha() > 0
    assert image.pixelColor(center.x() - tip_offset, center.y()).alpha() == 0


@pytest.mark.parametrize("sunken", [False, True])
def test_exclusive_menu_indicator_checked_is_a_check_mark(sunken: bool):
    menu = ModernMenu()
    group = QActionGroup(menu)
    group.setExclusive(True)
    action = menu.addAction("Choice")
    action.setCheckable(True)
    action.setChecked(True)
    group.addAction(action)
    option = QStyleOptionMenuItem()
    menu.initStyleOption(option, action)
    option.rect = QRect(0, 0, 100, 24)
    option.text = ""
    if sunken:
        option.state |= QStyle.StateFlag.State_Sunken
    image = QImage(100, 24, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    menu.style().drawControl(QStyle.ControlElement.CE_MenuItem, option, painter, menu)
    painter.end()

    assert option.checkType == QStyleOptionMenuItem.CheckType.Exclusive
    assert image.pixelColor(12, 12).alpha() > 0
    assert image.pixelColor(18, 10).alpha() > 0
    assert image.pixelColor(12, 9).alpha() == 0


@pytest.mark.parametrize("sunken", [False, True])
@pytest.mark.parametrize("selected", [False, True])
def test_exclusive_menu_indicator_unchecked_has_no_dot(sunken: bool, selected: bool):
    menu = ModernMenu()
    group = QActionGroup(menu)
    group.setExclusive(True)
    action = menu.addAction("Choice")
    action.setCheckable(True)
    action.setChecked(False)
    group.addAction(action)
    option = QStyleOptionMenuItem()
    menu.initStyleOption(option, action)
    option.rect = QRect(0, 0, 100, 24)
    option.text = ""
    if sunken:
        option.state |= QStyle.StateFlag.State_Sunken
    if selected:
        option.state |= QStyle.StateFlag.State_Selected
    image = QImage(100, 24, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    menu.style().drawControl(QStyle.ControlElement.CE_MenuItem, option, painter, menu)
    painter.end()

    assert option.checkType == QStyleOptionMenuItem.CheckType.Exclusive
    # An unchecked exclusive item must never render a native bullet, even when pressed or selected
    assert image.pixelColor(15, 12).alpha() < 50
    assert image.pixelColor(12, 12).alpha() < 50


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
@pytest.mark.parametrize("selected", [False, True])
def test_fusion_checked_icon_has_translucent_backdrop_on_acrylic(theme, selected, monkeypatch):
    # Exercise the Fusion checked-icon panel used by the application's theme,
    # independently of the test host's default native style.
    monkeypatch.setattr("pyside6_modern_widgets.modern_menu._base_style_name", lambda _: "fusion")
    menu = ModernMenu()
    menu.setPalette(palette_for_theme(theme))
    # A transparent icon exposes the entire checked panel drawn by the base style.
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    action = menu.addAction(QIcon(pixmap), "Checked action")
    action.setCheckable(True)
    action.setChecked(True)
    menu.show()
    _APP.processEvents()
    try:
        menu._rounded_style.setNativeAcrylic(True)
        if selected:
            menu.setActiveAction(action)
        rect = menu.actionGeometry(action)
        rendered = menu.grab()
        scale = rendered.devicePixelRatio()
        image = rendered.toImage()
        pixels = [
            image.pixelColor(round(x * scale), round(y * scale))
            for x in range(8, 20)
            for y in range(rect.center().y() - 4, rect.center().y() + 5)
        ]
        assert all(0 < pixel.alpha() < 60 for pixel in pixels)
        assert action.isChecked()
        action.trigger()
        assert not action.isChecked()
    finally:
        menu.close()
