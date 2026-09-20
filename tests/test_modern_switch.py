from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)

from pyside6_modern_widgets import DARK_THEME, LIGHT_THEME, ModernSwitch, ModernWindow, ThemeMode

_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def switch(theme_manager_instance):
    widget = ModernSwitch()
    widget.resize(widget.sizeHint())
    yield widget
    widget.close()
    widget.deleteLater()
    _APP.processEvents()


def test_mouse_keyboard_and_programmatic_signals(switch):
    toggled, clicked = [], []
    switch.toggled.connect(toggled.append)
    switch.clicked.connect(lambda checked: clicked.append(checked))
    switch.setChecked(True)
    switch.setChecked(True)
    assert toggled == [True]
    assert clicked == []
    switch.show()
    _APP.processEvents()
    QTest.mouseClick(switch, Qt.MouseButton.LeftButton, pos=QPoint(switch.width() - 2, 10))
    QTest.keyClick(switch, Qt.Key.Key_Space)
    assert toggled == [True, False, True]
    assert clicked == [False, True]
    switch.setEnabled(False)
    QTest.mouseClick(switch, Qt.MouseButton.LeftButton)
    QTest.keyClick(switch, Qt.Key.Key_Space)
    assert toggled == [True, False, True]


def test_focus_ring_follows_keyboard_and_mouse_input(switch):
    window = QWidget()
    layout = QVBoxLayout(window)
    before, after = QPushButton("Before"), QPushButton("After")
    for widget in (before, switch, after):
        layout.addWidget(widget)
    window.show()
    _APP.processEvents()

    def focus_border():
        # Only the focus outline reaches the top row, so thumb animation and
        # hover/checked colors do not affect this comparison.
        return switch.grab().toImage().copy(0, 0, switch.width(), 1)

    try:
        before.setFocus()
        no_border = focus_border()
        QTest.mouseClick(switch, Qt.MouseButton.LeftButton)
        assert switch.hasFocus()
        assert focus_border() == no_border
        before.setFocus()
        QTest.keyClick(before, Qt.Key.Key_Tab)
        assert switch.hasFocus()
        keyboard_border = focus_border()
        assert keyboard_border != no_border
        # Clicking an already keyboard-focused switch must hide the ring too.
        QTest.mouseClick(switch, Qt.MouseButton.LeftButton)
        assert focus_border() == no_border
        QTest.keyClick(switch, Qt.Key.Key_Space)
        assert focus_border() == keyboard_border
        QTest.keyClick(switch, Qt.Key.Key_Tab)
        assert after.hasFocus()
        assert focus_border() == no_border
        QTest.keyClick(after, Qt.Key.Key_Backtab)
        assert switch.hasFocus()
        assert focus_border() == keyboard_border
    finally:
        switch.setParent(None)
        window.close()
        window.deleteLater()


@pytest.mark.parametrize("point_size", [9, 12, 20])
def test_track_stays_compact_and_large_labels_fit(switch, point_size):
    style = QStyleFactory.create("Fusion")
    style.setParent(switch)
    switch.setStyle(style)
    switch.setStyleSheet("QLineEdit { padding: 18px; }")
    font = switch.font()
    font.setPointSize(point_size)
    switch.setFont(font)
    assert switch.sizeHint().width() == 38
    assert switch.sizeHint().height() == 20
    switch.setText("Enable notifications")
    assert switch.sizeHint().height() >= switch.fontMetrics().height()
    assert switch.minimumSizeHint() == switch.sizeHint()
    switch.setTheme(replace(LIGHT_THEME, accent="#ff0000", on_accent="#ffffff"))
    switch.setChecked(True)
    switch.resize(switch.sizeHint())
    pixmap = switch.grab()
    image = pixmap.toImage()
    scale = pixmap.devicePixelRatio()
    pixels = [
        (x, y)
        for y in range(image.height())
        for x in range(round(38 * scale))
        if image.pixelColor(x, y) == QColor("#ff0000")
    ]
    width = (max(x for x, y in pixels) - min(x for x, y in pixels) + 1) / scale
    height = (max(y for x, y in pixels) - min(y for x, y in pixels) + 1) / scale
    assert 30 <= width <= 34
    assert 14 <= height <= 18


def _track_color(switch):
    # The top-middle of the capsule is clear of the thumb at both endpoints.
    height = switch.sizeHint().height() - 4
    x = 3 + height
    if switch.layoutDirection() == Qt.LayoutDirection.RightToLeft:
        x = switch.width() - x
    return switch.grab().toImage().pixelColor(x, 4)


def test_system_accent_and_runtime_palette_changes(switch):
    switch.setChecked(True)
    for color in ("#CD3377", "#197F64"):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Accent, QColor(color))
        switch.setPalette(palette)
        assert _track_color(switch) == QColor(color)
    switch.setTheme(replace(DARK_THEME, accent="#AE66DD"))
    assert _track_color(switch) == QColor("#AE66DD")
    switch.setTheme(None)
    assert _track_color(switch) == QColor("#197F64")
    switch.setEnabled(False)
    assert _track_color(switch) != QColor("#197F64")


def test_checked_colors_survive_window_deactivation(switch):
    palette = QPalette()
    accent = QColor("#197F64")
    palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent, accent)
    palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Accent, QColor("#f0f0f0"))
    switch.setPalette(palette)
    switch.setChecked(True)
    other = QWidget()
    try:
        switch.show()
        other.show()
        _APP.setActiveWindow(switch)
        _APP.processEvents()
        switch.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
        assert _track_color(switch) == accent
        _APP.setActiveWindow(other)
        _APP.processEvents()
        switch.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
        assert not switch.isActiveWindow()
        assert switch.palette().currentColorGroup() == QPalette.ColorGroup.Inactive
        assert switch.isChecked()
        assert _track_color(switch) == accent
        pixmap = switch.grab()
        scale = pixmap.devicePixelRatio()
        assert pixmap.toImage().pixelColor(round(27 * scale), round(10 * scale)) == QColor(
            "#ffffff"
        )
        switch.setEnabled(False)
        assert _track_color(switch) != accent
    finally:
        other.close()
        other.deleteLater()


def test_theme_inheritance_and_reparenting(switch, theme_manager_instance):
    window = ModernWindow(theme=DARK_THEME)
    container = QWidget(window)
    switch.setParent(container)
    assert switch.theme() == DARK_THEME
    switch.setTheme(LIGHT_THEME)
    window.setTheme(replace(DARK_THEME, accent="#AD4499"))
    assert switch.theme() == LIGHT_THEME
    switch.setTheme(None)
    assert switch.theme().accent == "#AD4499"
    switch.setParent(None)
    theme_manager_instance.setMode(ThemeMode.LIGHT)
    assert switch.theme() == LIGHT_THEME
    theme_manager_instance.setMode(ThemeMode.DARK)
    assert switch.theme() == DARK_THEME
    window.deleteLater()


def test_animation_reverses_and_blocked_signals_still_update(switch):
    switch.show()
    _APP.processEvents()
    switch.setChecked(True)
    QTest.qWait(90)
    assert 0 < switch._position < 1
    switch.setChecked(False)
    QTest.qWait(300)
    assert switch._position == 0
    switch.blockSignals(True)
    switch.setChecked(True)
    QTest.qWait(300)
    assert switch._position == 1
    switch.hide()
    switch.setChecked(False)
    assert switch._position == 0


def test_rtl_mirrors_track_and_thumb(switch):
    switch.setChecked(True)
    switch.clearFocus()
    left = switch.grab().toImage()
    switch.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    right = switch.grab().toImage()
    # Compare interior pixels, avoiding antialiasing at the outer boundaries.
    for x in range(6, switch.width() - 6):
        first = left.pixelColor(x, 10).getRgb()
        mirrored = right.pixelColor(switch.width() - x - 1, 10).getRgb()
        assert all(abs(a - b) <= 1 for a, b in zip(first, mirrored))


def test_parent_and_text_constructors(switch):
    child = ModernSwitch(switch)
    assert child.parentWidget() is switch
    assert not child.text()
    labeled = ModernSwitch("&Notifications", switch)
    assert labeled.parentWidget() is switch
    assert labeled.sizeHint().width() > child.sizeHint().width()
    assert not labeled.shortcut().isEmpty()
