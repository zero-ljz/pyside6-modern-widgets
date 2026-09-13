from __future__ import annotations

import pytest
from PySide6.QtGui import QColor, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernDialog,
    ModernMenuBar,
    ModernMessageBox,
    ModernWindow,
)
from pyside6_modern_widgets._window_chrome import TitleBarButton, WindowTitleBar

_APP = QApplication.instance()


def _activate(window):
    window.activateWindow()
    _APP.processEvents()
    assert window.isActiveWindow()


@pytest.mark.parametrize("window_type", [ModernWindow, ModernDialog, ModernMessageBox])
@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME], ids=["light", "dark"])
def test_inactive_title_foregrounds_keep_color_at_half_opacity(window_type, theme):
    window = window_type(theme=theme)
    other = QWidget()
    icon = QPixmap(20, 20)
    icon.fill(QColor("red"))
    window.setWindowIcon(QIcon(icon))
    window.setWindowTitle("Foreground")
    try:
        window.show()
        other.show()
        title_bar = window.findChild(WindowTitleBar)
        for _ in range(2):
            _activate(window)
            assert title_bar.iconLabel.graphicsEffect().opacity() == 1.0
            assert title_bar.titleLabel.palette().color(QPalette.ColorRole.WindowText) == QColor(
                theme.text
            )
            _activate(other)
            color = title_bar.titleLabel.palette().color(QPalette.ColorRole.WindowText)
            assert color.alphaF() == pytest.approx(0.5, abs=0.01)
            color.setAlpha(255)
            assert color == QColor(theme.text)
            assert title_bar.iconLabel.graphicsEffect().opacity() == 0.5
        next_theme = DARK_THEME if theme == LIGHT_THEME else LIGHT_THEME
        window.setTheme(next_theme)
        color = title_bar.titleLabel.palette().color(QPalette.ColorRole.WindowText)
        assert color.alphaF() == pytest.approx(0.5, abs=0.01)
        color.setAlpha(255)
        assert color == QColor(next_theme.text)
    finally:
        window.close()
        other.close()
        window.deleteLater()
        other.deleteLater()


def test_title_bar_menu_text_fades_without_fading_popup_contents():
    window, other = ModernWindow(theme=DARK_THEME), QWidget()
    menu_bar = ModernMenuBar(window)
    window.titleBar.addCustomWidget(menu_bar, align="left")
    popup = menu_bar.addMenu("File")
    popup.addAction("Open")
    try:
        window.show()
        other.show()
        _activate(window)
        active = menu_bar.grab().toImage()
        _activate(other)
        inactive = menu_bar.grab().toImage()
        active_peak = max(
            active.pixelColor(x, y).red() * active.pixelColor(x, y).alphaF()
            for x in range(active.width())
            for y in range(active.height())
        )
        inactive_peak = max(
            inactive.pixelColor(x, y).red() * inactive.pixelColor(x, y).alphaF()
            for x in range(inactive.width())
            for y in range(inactive.height())
        )
        assert active_peak > 240
        assert inactive_peak < 190
        assert popup.palette().color(QPalette.ColorRole.WindowText).alpha() == 255
    finally:
        window.close()
        other.close()
        window.deleteLater()
        other.deleteLater()


def test_title_button_only_fades_foreground_pixels():
    window, other = QWidget(), QWidget()
    button = TitleBarButton(window)
    button.setGeometry(0, 0, 40, 40)
    button.setStyleSheet("background: #204060; border: none;")
    icon = QPixmap(16, 16)
    icon.fill(QColor("red"))
    button.setIcon(QIcon(icon))
    try:
        window.show()
        other.show()
        _activate(window)
        active = button.grab().toImage()
        _activate(other)
        inactive = button.grab().toImage()
        assert active.pixelColor(2, 2) == inactive.pixelColor(2, 2) == QColor("#204060")
        assert active.pixelColor(20, 20) == QColor("red")
        color = inactive.pixelColor(20, 20)
        assert color.red() == pytest.approx((255 + 32) / 2, abs=1)
        assert color.green() == pytest.approx(64 / 2, abs=1)
        assert color.blue() == pytest.approx(96 / 2, abs=1)
    finally:
        window.close()
        other.close()
        window.deleteLater()
        other.deleteLater()
