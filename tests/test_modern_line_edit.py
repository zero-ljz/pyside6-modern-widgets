from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QIntValidator, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QStyleFactory, QToolButton, QWidget

from pyside6_modern_widgets import DARK_THEME, DEFAULT_METRICS, LIGHT_THEME, ModernLineEdit

_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def editor(theme_manager_instance):
    widget = ModernLineEdit()
    widget.resize(widget.sizeHint())
    yield widget
    widget.close()
    widget.deleteLater()
    _APP.processEvents()


@pytest.mark.parametrize("point_size", [9, 12, 16])
def test_fusion_geometry_tracks_font_and_clear_button(editor, point_size):
    native = QLineEdit()
    style = QStyleFactory.create("Fusion")
    style.setParent(native)
    native.setStyle(style)
    try:
        for widget in (native, editor):
            font = widget.font()
            font.setPointSize(point_size)
            widget.setFont(font)
            widget.setText("Workspace name")
            widget.setClearButtonEnabled(True)
        assert editor.sizeHint() == native.sizeHint()
        assert editor.minimumSizeHint() == native.minimumSizeHint()
    finally:
        native.deleteLater()


def test_native_editing_signals_validator_and_clear_button(editor):
    changed, edited = [], []
    editor.textChanged.connect(changed.append)
    editor.textEdited.connect(edited.append)
    editor.setValidator(QIntValidator(0, 999, editor))
    editor.setClearButtonEnabled(True)
    editor.show()
    _APP.processEvents()
    QTest.keyClicks(editor, "12a3")
    assert editor.text() == "123"
    assert changed == edited == ["1", "12", "123"]
    editor.undo()
    assert editor.text() == ""
    editor.redo()
    assert editor.text() == "123"
    clear = editor.findChild(QToolButton)
    assert clear is not None
    QTest.mouseClick(clear, Qt.MouseButton.LeftButton)
    assert editor.text() == ""


def test_theme_palette_focus_and_frameless_surface(editor):
    assert isinstance(editor, QLineEdit)
    editor.setTheme(replace(DARK_THEME, accent="#A24477"))
    assert editor.palette().color(QPalette.ColorRole.Text) == QColor(DARK_THEME.text)
    editor.show()
    editor.setFocus()
    _APP.processEvents()
    assert editor.grab().toImage().pixelColor(editor.width() // 2, editor.height() - 1) == QColor(
        "#A24477"
    )
    editor.setTheme(LIGHT_THEME)
    assert editor.palette().color(QPalette.ColorRole.Text) == QColor(LIGHT_THEME.text)
    editor.setTheme(None)
    editor.setFrame(False)
    assert editor.hasFrame() is False


def test_system_accent_updates_focused_border(editor):
    editor.show()
    editor.setFocus()
    _APP.processEvents()
    for value in ("#c83764", "#258067"):
        palette = QPalette(_APP.palette())
        palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent, QColor(value))
        _APP.setPalette(palette)
        _APP.processEvents()
        assert editor.grab().toImage().pixelColor(
            editor.width() // 2, editor.height() - 1
        ) == QColor(value)


def test_focus_underline_has_equal_end_insets(editor):
    editor.setTheme(replace(LIGHT_THEME, accent="#008080"))
    editor.resize(240, editor.sizeHint().height())
    editor.show()
    editor.setFocus()
    _APP.processEvents()
    image = editor.grab().toImage()
    bottom = image.height() - 1
    accent = QColor("#008080")
    pixels = [x for x in range(image.width()) if image.pixelColor(x, bottom) == accent]
    upper = [x for x in range(image.width()) if image.pixelColor(x, bottom - 1) == accent]
    assert pixels
    assert pixels[0] == image.width() - 1 - pixels[-1]
    assert pixels[0] - upper[0] >= 2
    assert upper[-1] - pixels[-1] >= 2
    assert upper[0] <= round(DEFAULT_METRICS.control_radius * editor.devicePixelRatioF())


def test_focused_editor_stays_same_color_on_hover(theme_manager_instance):
    parent = QWidget()
    parent.resize(300, 80)
    editor = ModernLineEdit(parent, theme=LIGHT_THEME)
    editor.move(10, 10)
    editor.resize(240, editor.sizeHint().height())
    parent.show()
    editor.setFocus()
    try:
        QTest.mouseMove(parent, QPoint(280, 70))
        _APP.processEvents()
        before = editor.grab().toImage().pixelColor(100, 5)
        QTest.mouseMove(editor, QPoint(100, editor.height() // 2))
        _APP.processEvents()
        assert editor.hasFocus()
        assert editor.grab().toImage().pixelColor(100, 5) == before
    finally:
        parent.close()


def test_constructor_and_explicit_palette_override(editor):
    parent = ModernLineEdit(editor)
    assert parent.parentWidget() is editor
    assert parent.text() == ""
    assert ModernLineEdit("Sample", editor).text() == "Sample"
    with pytest.raises(TypeError, match="parent specified twice"):
        ModernLineEdit(editor, editor)
    with pytest.raises(TypeError, match="theme must be"):
        editor.setTheme("dark")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Text, QColor("#cc4477"))
    editor.setPalette(palette)
    editor.setTheme(DARK_THEME)
    assert editor.palette().color(QPalette.ColorRole.Text) == QColor("#cc4477")
    editor.setPalette(QPalette())
    assert editor.palette().color(QPalette.ColorRole.Text) == QColor(DARK_THEME.text)


def test_password_read_only_and_rtl_keep_qt_behavior(editor):
    editor.setPlaceholderText("Enter a name")
    assert editor.placeholderText() == "Enter a name"
    editor.setText("secret")
    editor.setEchoMode(QLineEdit.EchoMode.Password)
    assert editor.displayText() != editor.text()
    editor.setReadOnly(True)
    editor.show()
    _APP.processEvents()
    QTest.keyClicks(editor, "more")
    assert editor.text() == "secret"
    editor.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    assert editor.layoutDirection() == Qt.LayoutDirection.RightToLeft
