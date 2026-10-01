from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QRadioButton,
    QStyle,
    QStyleFactory,
    QStyleOptionButton,
    QWidget,
)

from examples.navigation_view_example import ExampleWindow
from pyside6_modern_widgets import DARK_THEME, ModernCheckBox, ModernRadioButton

_APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    ("native_type", "modern_type", "indicator", "contents"),
    [
        (
            QCheckBox,
            ModernCheckBox,
            QStyle.SubElement.SE_CheckBoxIndicator,
            QStyle.SubElement.SE_CheckBoxContents,
        ),
        (
            QRadioButton,
            ModernRadioButton,
            QStyle.SubElement.SE_RadioButtonIndicator,
            QStyle.SubElement.SE_RadioButtonContents,
        ),
    ],
)
@pytest.mark.parametrize("rtl", [False, True])
@pytest.mark.parametrize("text", ["", "&Option", "Long option label"])
@pytest.mark.parametrize("point_size", [9, 16])
def test_fusion_geometry_and_label_layout(
    theme_manager_instance, native_type, modern_type, indicator, contents, rtl, text, point_size
):
    native = native_type(text)
    modern = modern_type(text)
    fusion = QStyleFactory.create("Fusion")
    fusion.setParent(native)
    native.setStyle(fusion)
    try:
        for widget in (native, modern):
            font = widget.font()
            font.setPointSize(point_size)
            widget.setFont(font)
            widget.setLayoutDirection(
                Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
            )
            widget.resize(widget.sizeHint())
        assert modern.sizeHint() == native.sizeHint()
        assert modern.minimumSizeHint() == native.minimumSizeHint()
        assert modern.sizePolicy() == native.sizePolicy()
        for element in (indicator, contents):
            options = []
            for widget in (native, modern):
                option = QStyleOptionButton()
                widget.initStyleOption(option)
                options.append(widget.style().subElementRect(element, option, widget))
            assert options[1] == options[0]
    finally:
        native.deleteLater()
        modern.deleteLater()


def test_check_box_keeps_native_mouse_keyboard_and_tristate(theme_manager_instance):
    native = QCheckBox("&Option")
    modern = ModernCheckBox("&Option")
    try:
        for widget in (native, modern):
            widget.setTristate(True)
            widget.resize(widget.sizeHint())
            widget.show()
        _APP.processEvents()
        states = []
        for widget in (native, modern):
            spy = QSignalSpy(widget.checkStateChanged)
            sequence = []
            for _ in range(3):
                QTest.mouseClick(
                    widget,
                    Qt.MouseButton.LeftButton,
                    pos=QPoint(25, widget.height() // 2),
                )
                sequence.append(widget.checkState())
            QTest.keyClick(widget, Qt.Key.Key_Space)
            sequence.append(widget.checkState())
            assert spy.count() == 4
            states.append(sequence)
        assert states[1] == states[0]
        modern.setEnabled(False)
        before = modern.checkState()
        QTest.mouseClick(modern, Qt.MouseButton.LeftButton)
        assert modern.checkState() == before
    finally:
        native.close()
        modern.close()
        native.deleteLater()
        modern.deleteLater()


def test_radio_button_keeps_group_exclusivity_and_signals(theme_manager_instance):
    parent = QWidget()
    group = QButtonGroup(parent)
    first = ModernRadioButton("&First", parent)
    second = ModernRadioButton("&Second", parent)
    for button in (first, second):
        group.addButton(button)
        button.resize(button.sizeHint())
        button.show()
    first.setChecked(True)
    toggled = QSignalSpy(second.toggled)
    try:
        _APP.processEvents()
        QTest.mouseClick(second, Qt.MouseButton.LeftButton)
        assert second.isChecked() and not first.isChecked()
        assert toggled.count() == 1
        QTest.keyClick(first, Qt.Key.Key_Space)
        assert first.isChecked() and not second.isChecked()
    finally:
        parent.close()
        parent.deleteLater()


@pytest.mark.parametrize("modern_type", [ModernCheckBox, ModernRadioButton])
def test_system_accent_theme_override_and_disabled_state(theme_manager_instance, modern_type):
    widget = modern_type("Option")
    widget.resize(widget.sizeHint())
    widget.setChecked(True)
    palette = QPalette()
    palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent, QColor("#197F64"))
    widget.setPalette(palette)
    try:
        base = widget.grab().toImage()
        widget.setTheme(replace(DARK_THEME, accent="#AE66DD"))
        overridden = widget.grab().toImage()
        assert base != overridden
        widget.setTheme(None)
        assert widget.grab().toImage() == base
        widget.setEnabled(False)
        assert widget.grab().toImage() != base
    finally:
        widget.deleteLater()


def test_choice_gallery_page_contains_both_comparisons(theme_manager_instance):
    window = ExampleWindow()
    try:
        page = window._create_choice_page()
        assert len(page.findChildren(ModernCheckBox)) == 5
        assert len(page.findChildren(ModernRadioButton)) == 3
        assert any(check.isTristate() for check in page.findChildren(ModernCheckBox))
    finally:
        window.close()
        window.deleteLater()
