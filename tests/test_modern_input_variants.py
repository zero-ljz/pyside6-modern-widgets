from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtGui import QColor, QFont, QKeySequence, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDateEdit,
    QDoubleSpinBox,
    QFontComboBox,
    QKeySequenceEdit,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QTimeEdit,
    QWidget,
)

from examples.navigation_view_example import ExampleWindow
from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernComboBox,
    ModernDateEdit,
    ModernDoubleSpinBox,
    ModernFontComboBox,
    ModernKeySequenceEdit,
    ModernLineEdit,
    ModernPlainTextEdit,
    ModernTextEdit,
    ModernTimeEdit,
    ThemeMode,
)

_APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    "native_type,modern_type",
    [
        (QDoubleSpinBox, ModernDoubleSpinBox),
        (QDateEdit, ModernDateEdit),
        (QTimeEdit, ModernTimeEdit),
        (QPlainTextEdit, ModernPlainTextEdit),
        (QTextEdit, ModernTextEdit),
        (QKeySequenceEdit, ModernKeySequenceEdit),
        (QFontComboBox, ModernFontComboBox),
    ],
)
def test_variants_keep_qt_types_and_theme_contract(
    theme_manager_instance, native_type, modern_type
):
    parent = QWidget()
    widget = modern_type(parent)
    try:
        assert isinstance(widget, native_type)
        assert widget.parent() is parent
        widget.setTheme(DARK_THEME)
        assert widget.theme() == DARK_THEME
        assert widget.palette().color(QPalette.ColorRole.Text) == QColor(DARK_THEME.text)
        changes = []
        widget.themeChanged.connect(changes.append)
        custom = replace(LIGHT_THEME, name="input-test")
        widget.setTheme(custom)
        assert changes == [custom]
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Text, QColor("#cc4477"))
        widget.setPalette(palette)
        widget.setTheme(DARK_THEME)
        assert widget.palette().color(QPalette.ColorRole.Text) == QColor("#cc4477")
        widget.setPalette(QPalette())
        assert widget.palette().color(QPalette.ColorRole.Text) == QColor(DARK_THEME.text)
    finally:
        parent.close()


def test_numeric_and_date_variants_preserve_values_and_signals(theme_manager_instance):
    number = ModernDoubleSpinBox()
    date = ModernDateEdit(QDate(2026, 10, 1))
    time = ModernTimeEdit(QTime(12, 21))
    try:
        number.setDecimals(3)
        number.setSingleStep(0.125)
        number.setValue(1.5)
        changes = []
        number.valueChanged.connect(changes.append)
        number.stepUp()
        assert number.value() == 1.625
        assert changes == [1.625]
        assert date.date() == QDate(2026, 10, 1)
        assert time.time() == QTime(12, 21)
        date.setCalendarPopup(True)
        assert date.calendarWidget() is not None
        assert date.displayFormat() != time.displayFormat()
    finally:
        for widget in (number, date, time):
            widget.close()


def test_multiline_editors_preserve_native_document_input(theme_manager_instance):
    plain = ModernPlainTextEdit("one")
    rich = ModernTextEdit("<b>bold</b>")
    try:
        plain.appendPlainText("two")
        assert plain.toPlainText() == "one\ntwo"
        assert rich.toPlainText() == "bold"
        assert rich.toHtml().find("font-weight:700") >= 0
        rich.setPlainText("plain")
        assert rich.toPlainText() == "plain"
        rich.setReadOnly(True)
        assert rich.isReadOnly()
    finally:
        plain.close()
        rich.close()


@pytest.mark.parametrize("editor_type", [ModernPlainTextEdit, ModernTextEdit])
@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
def test_multiline_editors_have_one_surface(theme_manager_instance, editor_type, theme):
    line_edit = ModernLineEdit(theme=theme)
    editor = editor_type(theme=theme)
    line_edit.resize(200, line_edit.sizeHint().height())
    editor.resize(200, 100)
    line_edit.show()
    editor.show()
    _APP.processEvents()
    try:
        assert editor.viewport().geometry().x() == 1
        assert editor.viewport().palette().color(QPalette.ColorRole.Base).alpha() == 0
        line_image = line_edit.grab().toImage()
        image = editor.grab().toImage()
        scale = editor.devicePixelRatioF()
        y = image.height() // 2
        assert image.pixelColor(round(3 * scale), y) == image.pixelColor(round(8 * scale), y)
        for x in range(round(5 * scale)):
            for corner_y in range(round(5 * scale)):
                assert image.pixelColor(x, corner_y) == line_image.pixelColor(x, corner_y)
    finally:
        line_edit.close()
        editor.close()


def test_shortcut_and_font_variants_keep_specialized_api(theme_manager_instance):
    shortcut = ModernKeySequenceEdit(QKeySequence("Ctrl+K"))
    fonts = ModernFontComboBox()
    native_fonts = QFontComboBox()
    try:
        assert shortcut.keySequence() == QKeySequence("Ctrl+K")
        assert fonts.count() == native_fonts.count()
        fonts.setCurrentFont(QFont("Arial"))
        native_fonts.setCurrentFont(QFont("Arial"))
        assert fonts.currentFont().family() == native_fonts.currentFont().family()
        if fonts.count():
            from PySide6.QtWidgets import QStyleOptionViewItem

            option = QStyleOptionViewItem()
            index = fonts.model().index(0, 0)
            fonts.itemDelegate().initStyleOption(option, index)
            assert option.font.family() == fonts.itemText(0)
        shortcut.show()
        shortcut.setFocus()
        _APP.processEvents()
        QTest.keyClick(shortcut, Qt.Key.Key_J, Qt.KeyboardModifier.ControlModifier)
        assert shortcut.keySequence() == QKeySequence("Ctrl+J")
    finally:
        shortcut.close()
        fonts.close()
        native_fonts.close()


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
def test_font_combo_default_editor_uses_the_same_surface_as_editable_combo(
    theme_manager_instance, theme
):
    combo = ModernComboBox(theme=theme)
    fonts = ModernFontComboBox(theme=theme)
    combo.setEditable(True)
    try:
        for widget in (combo, fonts):
            widget.setEditText("")
            widget.resize(200, 30)
            widget.show()
            widget.clearFocus()
        _APP.processEvents()
        images = [widget.grab().toImage() for widget in (combo, fonts)]
        for widget, image in zip((combo, fonts), images):
            scale = widget.devicePixelRatioF()
            editor = widget.lineEdit().geometry()
            y = round(editor.center().y() * scale)
            outside = image.pixelColor(round((editor.left() - 1) * scale), y)
            inside = image.pixelColor(round((editor.left() + 5) * scale), y)
            assert inside == outside
        assert images[0].pixelColor(10, 15) == images[1].pixelColor(10, 15)
    finally:
        combo.close()
        fonts.close()


def test_shortcut_editor_palette_tracks_gallery_theme_switch(theme_manager_instance):
    theme_manager_instance.setMode(ThemeMode.DARK)
    window = ExampleWindow()
    try:
        window.show()
        _APP.processEvents()
        shortcut = window.findChild(ModernKeySequenceEdit)
        assert shortcut is not None
        editor = shortcut.findChild(QLineEdit)
        assert editor is not None

        theme_manager_instance.setMode(ThemeMode.LIGHT)
        _APP.processEvents()
        assert shortcut.theme() == LIGHT_THEME
        assert editor.palette().color(QPalette.ColorRole.Text) == QColor(LIGHT_THEME.text)
        assert editor.palette().color(QPalette.ColorRole.Mid) == QColor(LIGHT_THEME.border)
    finally:
        window.close()
