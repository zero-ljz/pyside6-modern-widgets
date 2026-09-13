from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap, QRegion
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernDialog,
    ModernMenuBar,
    ModernMessageBox,
    ModernMetrics,
    ModernWindow,
    ThemeMode,
)
from pyside6_modern_widgets._window_chrome import WindowTitleBar

_APP = QApplication.instance()


@pytest.fixture(params=[False, True], ids=["no-qss", "global-qss"])
def application_stylesheet(request):
    original = _APP.styleSheet()
    # A selector for unrelated labels is enough to change QLabel inheritance.
    stylesheet = 'QLabel[typographyRole="pageTitle"] { font-weight: 700; }'
    _APP.setStyleSheet(stylesheet if request.param else "")
    try:
        yield
    finally:
        _APP.setStyleSheet(original)


def _activate(window):
    window.activateWindow()
    _APP.processEvents()
    for _ in range(20):
        if window.isActiveWindow():
            break
        QTest.qWait(10)
    assert window.isActiveWindow()


def _foreground_alpha(widget):
    """Render actual widget paint output without the parent's opaque background."""
    pixmap = QPixmap(widget.size() * widget.devicePixelRatioF())
    pixmap.setDevicePixelRatio(widget.devicePixelRatioF())
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    widget.render(painter, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
    painter.end()
    image = pixmap.toImage()
    return sum(
        image.pixelColor(x, y).alpha() for y in range(image.height()) for x in range(image.width())
    )


@pytest.mark.parametrize("window_type", [ModernWindow, ModernDialog, ModernMessageBox])
@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME], ids=["light", "dark"])
def test_actual_chrome_foregrounds_fade_and_restore(window_type, theme, application_stylesheet):
    # Native Windows 11 menu items need more height than Fusion menu items.
    window = window_type(theme=theme, metrics=ModernMetrics(title_bar_height=40))
    other = QWidget()
    window.setWindowModality(Qt.WindowModality.NonModal)
    window.setWindowTitle("Foreground")
    if isinstance(window, ModernMessageBox):
        window.setText("A message with enough space to show the title, menu and close button.")
    icon = QPixmap(20, 20)
    icon.fill(QColor("red"))
    window.setWindowIcon(QIcon(icon))
    title_bar = window.findChild(WindowTitleBar)
    menu = ModernMenuBar(window)
    menu.addAction("File")
    title_bar.addCustomWidget(menu, align="left")
    if isinstance(window, ModernWindow):
        window.addTitleBarButton(QIcon(icon), tooltip="Custom icon")
    window.resize(800, 300)
    try:
        window.show()
        other.show()
        widgets = [title_bar.titleLabel, title_bar.iconLabel, menu]
        widgets += title_bar.findChildren(QPushButton)
        widgets = [widget for widget in widgets if not widget.isHidden()]
        snapshots = []
        for target in (window, other, window):
            _activate(target)
            for widget in widgets:
                widget.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
            snapshots.append([_foreground_alpha(widget) for widget in widgets])
        for widget, active, inactive, restored in zip(widgets, *snapshots):
            assert active > 0, type(widget).__name__
            assert 0.47 < inactive / active < 0.53, (type(widget).__name__, active, inactive)
            assert restored == active, type(widget).__name__
            assert widget.graphicsEffect() is None
        assert title_bar.iconLabel.pixmap().toImage().pixelColor(10, 10) == QColor("red")
    finally:
        window.close()
        other.close()
        window.deleteLater()
        other.deleteLater()


def test_chrome_palette_survives_live_mode_changes(theme_manager_instance):
    window, other = ModernWindow(), QWidget()
    menu = ModernMenuBar(window)
    menu.addAction("File")
    window.titleBar.addCustomWidget(menu, align="left")
    try:
        window.show()
        other.show()
        for mode, theme in ((ThemeMode.DARK, DARK_THEME), (ThemeMode.LIGHT, LIGHT_THEME)):
            theme_manager_instance.setMode(mode)
            for target in (window, other):
                _activate(target)
                expected = QColor(theme.text)
                if target is other:
                    expected.setAlphaF(0.5)
                widgets = [menu, window.titleBar.titleLabel, window.titleBar.iconLabel]
                widgets += window.titleBar.findChildren(QPushButton)
                for widget in widgets:
                    if widget.isHidden():
                        continue
                    assert widget.palette().color(QPalette.ColorRole.WindowText) == expected
                # Page content keeps normal contrast in an inactive window.
                assert window.palette().color(QPalette.ColorRole.Text) == QColor(theme.text)
    finally:
        window.close()
        other.close()
        window.deleteLater()
        other.deleteLater()


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME], ids=["light", "dark"])
def test_title_button_keeps_native_hover_pressed_and_disabled_rendering(theme):
    window = ModernWindow(theme=theme)
    actual = window.titleBar.closeButton
    reference = QPushButton(window.titleBar)
    reference.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    reference.setAutoDefault(False)
    reference.setFixedSize(actual.size())
    try:
        window.show()
        _activate(window)
        for enabled, hover, pressed in (
            (True, False, False),
            (True, True, False),
            (True, True, True),
            (False, False, False),
        ):
            for button in (actual, reference):
                button.setEnabled(enabled)
                button.setDown(pressed)
                button.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, hover)
            reference.setStyleSheet(actual.styleSheet())
            reference.setPalette(actual.palette())
            reference.setIcon(actual.icon())
            reference.setIconSize(actual.iconSize())
            assert actual.grab().toImage() == reference.grab().toImage()
    finally:
        window.close()
        window.deleteLater()
