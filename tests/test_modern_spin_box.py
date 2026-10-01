from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QDate, QDateTime, QPoint, Qt, QTime
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QDateTimeEdit,
    QSpinBox,
    QStyle,
    QStyleFactory,
    QStyleOptionSpinBox,
    QWidget,
)

from examples.navigation_view_example import ExampleWindow
from pyside6_modern_widgets import DARK_THEME, LIGHT_THEME, ModernDateTimeEdit, ModernSpinBox

_APP = QApplication.instance() or QApplication([])


def _native(widget_type):
    widget = widget_type()
    style = QStyleFactory.create("Fusion")
    style.setParent(widget)
    widget.setStyle(style)
    return widget


def _part(widget, part):
    option = QStyleOptionSpinBox()
    widget.initStyleOption(option)
    return widget.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, option, part, widget)


@pytest.mark.parametrize(
    "native_type,modern_type", [(QSpinBox, ModernSpinBox), (QDateTimeEdit, ModernDateTimeEdit)]
)
@pytest.mark.parametrize("point_size", [9, 12, 16])
def test_fusion_height_and_adjacent_buttons(
    theme_manager_instance, native_type, modern_type, point_size
):
    native, modern = _native(native_type), modern_type()
    try:
        for widget in (native, modern):
            font = widget.font()
            font.setPointSize(point_size)
            widget.setFont(font)
        assert modern.sizeHint().height() == native.sizeHint().height()
        assert modern.minimumSizeHint().height() == native.minimumSizeHint().height()
        assert modern.sizeHint().width() - native.sizeHint().width() == max(
            0, native.sizeHint().height() - 5
        )
        modern.resize(modern.sizeHint())
        up = _part(modern, QStyle.SubControl.SC_SpinBoxUp)
        down = _part(modern, QStyle.SubControl.SC_SpinBoxDown)
        field = _part(modern, QStyle.SubControl.SC_SpinBoxEditField)
        assert up.right() + 1 == down.left()
        assert up.top() == down.top() and up.height() == down.height()
        assert field.right() < up.left()
    finally:
        native.deleteLater()
        modern.deleteLater()


def test_native_number_editing_and_button_hit_testing(theme_manager_instance):
    widget = ModernSpinBox()
    widget.setRange(10, 12)
    widget.setValue(11)
    widget.resize(widget.sizeHint())
    widget.show()
    _APP.processEvents()
    changes = []
    widget.valueChanged.connect(changes.append)
    try:
        QTest.mouseClick(
            widget,
            Qt.MouseButton.LeftButton,
            pos=_part(widget, QStyle.SubControl.SC_SpinBoxUp).center(),
        )
        assert widget.value() == 12
        QTest.mouseClick(
            widget,
            Qt.MouseButton.LeftButton,
            pos=_part(widget, QStyle.SubControl.SC_SpinBoxUp).center(),
        )
        assert widget.value() == 12
        QTest.mouseClick(
            widget,
            Qt.MouseButton.LeftButton,
            pos=_part(widget, QStyle.SubControl.SC_SpinBoxDown).center(),
        )
        assert widget.value() == 11
        QTest.keyClick(widget, Qt.Key.Key_Down)
        assert widget.value() == 10
        assert changes == [12, 11, 10]
        widget.setWrapping(True)
        widget.stepDown()
        assert widget.value() == 12
        widget.setSuffix(" %")
        assert widget.text() == "12 %"
        widget.setReadOnly(True)
        assert widget.isReadOnly()
        widget.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        assert widget.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.NoButtons
        native = _native(QSpinBox)
        native.setRange(10, 12)
        native.setSuffix(" %")
        native.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        assert widget.sizeHint() == native.sizeHint()
        native.deleteLater()
        widget.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)
        widget.setReadOnly(False)
        widget.setValue(11)
        QTest.mouseClick(
            widget,
            Qt.MouseButton.LeftButton,
            pos=_part(widget, QStyle.SubControl.SC_SpinBoxUp).center(),
        )
        assert widget.value() == 12
        widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        assert (
            _part(widget, QStyle.SubControl.SC_SpinBoxUp).left()
            < _part(widget, QStyle.SubControl.SC_SpinBoxEditField).left()
        )
    finally:
        widget.close()


def test_frameless_mode_uses_fusion_button_geometry(theme_manager_instance):
    native, modern = _native(QSpinBox), ModernSpinBox()
    try:
        native.setFrame(False)
        modern.setFrame(False)
        assert modern.sizeHint() == native.sizeHint()
        modern.resize(modern.sizeHint())
        up = _part(modern, QStyle.SubControl.SC_SpinBoxUp)
        down = _part(modern, QStyle.SubControl.SC_SpinBoxDown)
        assert up.left() == down.left()
        assert up.bottom() < down.top()
    finally:
        native.deleteLater()
        modern.deleteLater()


@pytest.mark.parametrize("widget_type", [ModernSpinBox, ModernDateTimeEdit])
@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
def test_idle_step_buttons_share_field_background(theme_manager_instance, widget_type, theme):
    widget = widget_type(theme=theme)
    if isinstance(widget, QDateTimeEdit):
        widget.setDisplayFormat("yyyy")
    widget.resize(240, widget.sizeHint().height())
    widget.show()
    widget.setFocus()
    _APP.processEvents()
    try:
        up = _part(widget, QStyle.SubControl.SC_SpinBoxUp)
        down = _part(widget, QStyle.SubControl.SC_SpinBoxDown)
        QTest.mouseMove(widget, _part(widget, QStyle.SubControl.SC_SpinBoxEditField).center())
        _APP.processEvents()
        image = widget.grab().toImage()
        scale = widget.devicePixelRatioF()
        y = round((up.top() + 3) * scale)
        field = image.pixelColor(round(80 * scale), y)
        assert image.pixelColor(round((up.left() + 3) * scale), y) == field
        assert image.pixelColor(round((down.left() + 3) * scale), y) == field
        for button in (up, down):
            QTest.mouseMove(widget, button.center())
            _APP.processEvents()
            hovered = widget.grab().toImage()
            assert hovered.pixelColor(round(80 * scale), y) == field
            assert hovered.pixelColor(round(80 * scale), y) != hovered.pixelColor(
                round((button.left() + 3) * scale), y
            )
        QTest.mouseMove(widget, _part(widget, QStyle.SubControl.SC_SpinBoxEditField).center())
        _APP.processEvents()
        restored = widget.grab().toImage()
        assert restored.pixelColor(round(80 * scale), y) == restored.pixelColor(
            round((up.left() + 3) * scale), y
        )
    finally:
        widget.close()


def test_gallery_keeps_editor_and_buttons_on_one_surface(theme_manager_instance):
    window = ExampleWindow()
    try:
        window.navigation.setCurrentIndex(10)
        window.show()
        _APP.processEvents()
        image = window.grab().toImage()
        scale = window.devicePixelRatioF()
        for widget_type in (ModernSpinBox, ModernDateTimeEdit):
            editor = next(
                widget for widget in window.findChildren(widget_type) if widget.isVisible()
            )
            assert editor.lineEdit().palette().color(QPalette.ColorRole.Base).alpha() == 0
            origin = editor.mapTo(window, QPoint(0, 0))
            up = _part(editor, QStyle.SubControl.SC_SpinBoxUp)
            y = round((origin.y() + up.top() + 3) * scale)
            field = image.pixelColor(round((origin.x() + 180) * scale), y)
            button = image.pixelColor(round((origin.x() + up.left() + 3) * scale), y)
            assert field == button
    finally:
        window.close()


def test_datetime_constructors_sections_and_popup(theme_manager_instance):
    parent = QWidget()
    value = QDateTime(QDate(2026, 10, 1), QTime(12, 21))
    widgets = [
        ModernDateTimeEdit(parent),
        ModernDateTimeEdit(value, parent),
        ModernDateTimeEdit(value.date(), parent),
        ModernDateTimeEdit(value.time(), parent),
    ]
    try:
        assert all(isinstance(widget, QDateTimeEdit) for widget in widgets)
        assert widgets[1].dateTime() == value
        assert widgets[2].date() == value.date()
        assert widgets[3].time().hour() == value.time().hour()
        editor = widgets[1]
        editor.setDisplayFormat("yyyy/M/d HH:mm")
        editor.setCurrentSection(QDateTimeEdit.Section.YearSection)
        changes = []
        editor.dateTimeChanged.connect(changes.append)
        editor.stepBy(1)
        assert editor.date().year() == 2027
        assert changes[-1] == editor.dateTime()
        editor.setCalendarPopup(True)
        assert editor.calendarPopup()
        assert editor.calendarWidget() is not None
        editor.resize(editor.sizeHint())
        parent.show()
        _APP.processEvents()
        QTest.mouseClick(
            editor,
            Qt.MouseButton.LeftButton,
            pos=_part(editor, QStyle.SubControl.SC_SpinBoxDown).center(),
        )
        _APP.processEvents()
        assert editor.calendarWidget().isVisible()
        editor.calendarWidget().window().hide()
        with pytest.raises(TypeError, match="parent specified twice"):
            ModernDateTimeEdit(parent, parent)
    finally:
        parent.close()


@pytest.mark.parametrize("widget_type", [ModernSpinBox, ModernDateTimeEdit])
def test_theme_palette_and_accent(theme_manager_instance, widget_type):
    widget = widget_type()
    try:
        widget.setTheme(replace(DARK_THEME, accent="#A24477"))
        assert widget.palette().color(QPalette.ColorRole.Text) == QColor(DARK_THEME.text)
        assert widget.lineEdit().palette().color(QPalette.ColorRole.Base).alpha() == 0
        widget.resize(widget.sizeHint())
        widget.show()
        widget.setFocus()
        _APP.processEvents()
        image = widget.grab().toImage()
        assert image.pixelColor(widget.width() // 2, widget.height() - 1) == QColor("#A24477")
        widget.setTheme(LIGHT_THEME)
        assert widget.palette().color(QPalette.ColorRole.Text) == QColor(LIGHT_THEME.text)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Text, QColor("#cc4477"))
        widget.setPalette(palette)
        widget.setTheme(DARK_THEME)
        assert widget.palette().color(QPalette.ColorRole.Text) == QColor("#cc4477")
        widget.setPalette(QPalette())
        assert widget.palette().color(QPalette.ColorRole.Text) == QColor(DARK_THEME.text)
        with pytest.raises(TypeError, match="theme must be"):
            widget.setTheme("dark")
    finally:
        widget.close()


@pytest.mark.parametrize("widget_type", [ModernSpinBox, ModernDateTimeEdit])
def test_system_accent_updates_focused_underline(theme_manager_instance, widget_type):
    widget = widget_type()
    widget.resize(widget.sizeHint())
    widget.show()
    widget.setFocus()
    _APP.processEvents()
    try:
        for value in ("#c83764", "#258067"):
            palette = QPalette(_APP.palette())
            palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent, QColor(value))
            _APP.setPalette(palette)
            _APP.processEvents()
            image = widget.grab().toImage()
            assert image.pixelColor(widget.width() // 2, widget.height() - 1) == QColor(value)
    finally:
        widget.close()
