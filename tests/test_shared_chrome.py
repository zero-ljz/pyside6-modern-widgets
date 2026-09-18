"""Behavior checks across the Qt classes that share chrome and resizing."""

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPalette
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernComboBox,
    ModernDialog,
    ModernMenuBar,
    ModernMessageBox,
    ModernWindow,
)

_APP = QApplication.instance() or QApplication([])


def dispose(widget):
    widget.close()
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(widget, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("window_class", [ModernDialog, ModernWindow])
def test_child_edge_drag_fallback_constrains_geometry_and_finishes(monkeypatch, window_class):
    window = window_class()
    window.setGeometry(100, 100, 320, 240)
    window.setMinimumSize(250, 180)
    child = QLabel("Child edge", window)
    child.setGeometry(0, 40, 100, 30)
    window.show()
    _APP.processEvents()
    monkeypatch.setattr(window.windowHandle(), "startSystemResize", lambda _: False)
    start = child.mapToGlobal(QPoint(2, 10))
    try:
        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(2, 10),
            QPointF(start),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        assert window.eventFilter(child, press)
        move = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(202, 10),
            QPointF(start + QPoint(200, 0)),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        assert window.eventFilter(child, move)
        assert window.geometry().getRect() == (170, 100, 250, 240)
        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(202, 10),
            QPointF(start + QPoint(200, 0)),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        window.eventFilter(child, release)
        assert window._resize_controller.edges == Qt.Edge(0)
        if isinstance(window, ModernWindow):
            assert not window._system_resize_active
    finally:
        dispose(window)


@pytest.mark.parametrize("window_class", [ModernDialog, ModernWindow])
def test_resize_edges_honor_fixed_axes_and_clear_cursor(window_class):
    window = window_class()
    window.resize(320, 240)
    try:
        edges = window._resize_edges_at(QPoint(1, 1))
        assert edges == Qt.Edge.TopEdge | Qt.Edge.LeftEdge
        window._set_resize_cursor(edges)
        assert window.cursor().shape() == Qt.CursorShape.SizeFDiagCursor
        window.setFixedWidth(320)
        assert window._resize_edges_at(QPoint(1, 1)) == Qt.Edge.TopEdge
        window.setFixedHeight(240)
        assert window._resize_edges_at(QPoint(1, 1)) == Qt.Edge(0)
        window._set_resize_cursor(Qt.Edge(0))
        assert window.cursor().shape() == Qt.CursorShape.ArrowCursor
        assert not window._resize_controller.cursor_active
    finally:
        dispose(window)


@pytest.mark.parametrize("window_class", [ModernDialog, ModernWindow, ModernMessageBox])
def test_shared_chrome_tracks_theme_geometry_and_window_state(window_class):
    window = window_class()
    window.show()
    _APP.processEvents()
    try:
        for theme in (DARK_THEME, LIGHT_THEME):
            window.setTheme(theme)
            window.resize(450, 300)
            _APP.processEvents()
            chrome = window._chrome
            assert chrome.background.geometry() == window.rect()
            assert chrome.overlay.geometry() == window.rect()
            assert chrome.title_bar.width() == window.width()
            expected_surface = (
                theme.surface_alternate if isinstance(window, ModernMessageBox) else theme.surface
            )
            assert window.palette().color(QPalette.ColorRole.Window) == QColor(expected_surface)
            assert chrome.background._theme == chrome.overlay._theme == theme
        window.setCornerRadius(12)
        window.showFullScreen()
        _APP.processEvents()
        assert chrome.background._corner_radius == chrome.overlay._corner_radius == 0
        window.showNormal()
        _APP.processEvents()
        assert chrome.background._corner_radius == chrome.policy.paint_corner_radius(12)
    finally:
        dispose(window)


def test_menu_bar_and_combo_follow_nearest_theme_after_reparenting():
    first = ModernDialog(theme=DARK_THEME)
    second = ModernDialog(theme=LIGHT_THEME)
    container = QWidget(first)
    menu_bar = ModernMenuBar(container)
    combo = ModernComboBox(container)
    try:
        assert menu_bar._inherited_theme() == combo.theme() == DARK_THEME
        container.setParent(second)
        _APP.processEvents()
        assert menu_bar._inherited_theme() == combo.theme() == LIGHT_THEME
        combo.setTheme(DARK_THEME)
        assert menu_bar._inherited_theme() == LIGHT_THEME
        assert combo.theme() == DARK_THEME
        combo.setTheme(None)
        assert combo.theme() == LIGHT_THEME
    finally:
        dispose(first)
        dispose(second)
