from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernDialog,
    ModernMessageBox,
    ModernWindow,
    NavigationView,
)
from pyside6_modern_widgets._window_chrome import BackgroundFrame, SurfaceActivationTransition

_APP = QApplication.instance() or QApplication([])


class _PaintCounter(QObject):
    def __init__(self, widget: QWidget) -> None:
        super().__init__(widget)
        self.count = 0
        widget.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Paint:
            self.count += 1
        return False


def _activate(window: QWidget, *, settle: bool = True) -> None:
    window.activateWindow()
    _APP.processEvents()
    if settle:
        QTest.qWait(SurfaceActivationTransition.DURATION_MS + 30)
    _APP.processEvents()
    assert window.isActiveWindow()


def _surface_colors(widget: QWidget) -> tuple[QColor, QColor]:
    image = widget.grab().toImage()
    return (
        image.pixelColor(image.width() // 3, image.height() // 2),
        image.pixelColor(image.width() * 2 // 3, image.height() // 2),
    )


@pytest.mark.parametrize("window_type", [ModernWindow, ModernDialog, ModernMessageBox])
@pytest.mark.parametrize(
    "theme, inactive_color",
    [(LIGHT_THEME, "#F3F3F3"), (DARK_THEME, "#2B2B2B")],
    ids=["light", "dark"],
)
def test_window_background_tracks_activation_and_inactive_theme_changes(
    window_type, theme, inactive_color
) -> None:
    window = window_type(theme=theme)
    other = QWidget()
    try:
        window.resize(480, 320)
        window.show()
        other.show()
        frame = window.findChild(BackgroundFrame)
        assert frame is not None
        paints = _PaintCounter(frame)

        _activate(window)
        active_colors = _surface_colors(frame)
        assert active_colors[0] != active_colors[1]
        paint_count = paints.count

        _activate(other)
        assert not window.isActiveWindow()
        assert paints.count > paint_count
        assert _surface_colors(frame) == (QColor(inactive_color),) * 2

        _activate(window)
        assert _surface_colors(frame) == active_colors

        _activate(other)
        new_theme = DARK_THEME if theme is LIGHT_THEME else LIGHT_THEME
        window.setTheme(new_theme)
        window.resize(520, 360)
        _APP.processEvents()
        new_inactive_color = "#2B2B2B" if theme is LIGHT_THEME else "#F3F3F3"
        assert _surface_colors(frame) == (QColor(new_inactive_color),) * 2

        _activate(window)
        restored_colors = _surface_colors(frame)
        assert restored_colors[0] != restored_colors[1]
        assert restored_colors != active_colors
    finally:
        window.close()
        other.close()


@pytest.mark.parametrize("overlay", [False, True], ids=["window", "sidebar"])
@pytest.mark.parametrize(
    "theme, inactive_color",
    [(LIGHT_THEME, "#F3F3F3"), (DARK_THEME, "#2B2B2B")],
    ids=["light", "dark"],
)
def test_background_fade_blends_pixels_and_reverses_without_a_jump(
    overlay, theme, inactive_color
) -> None:
    window = ModernWindow(theme=theme)
    other = QWidget()
    try:
        surface = window.frame
        if overlay:
            navigation = NavigationView(theme=theme)
            navigation.setAutoSidebarOverlay(False)
            window.setCentralWidget(navigation)
            navigation.setSidebarOverlay(True)
            navigation.sidebar.setCollapsed(False, animated=False)
            surface = navigation.sidebar
        window.resize(480, 320)
        window.show()
        other.show()
        _activate(window)
        active_colors = _surface_colors(surface)

        _activate(other, settle=False)
        transition = surface._activation_transition
        transition.pause()
        inactive = QColor(inactive_color)
        for elapsed_ms in (50, 125, 200):
            transition.setCurrentTime(elapsed_ms)
            middle_colors = _surface_colors(surface)
            progress = elapsed_ms / 250
            for active, middle in zip(active_colors, middle_colors):
                assert middle != active
                assert middle != inactive
                assert middle.alpha() == 255
                for channel in (QColor.red, QColor.green, QColor.blue):
                    expected = channel(active) * (1 - progress) + channel(inactive) * progress
                    assert abs(channel(middle) - expected) <= 2

        _activate(window, settle=False)
        assert _surface_colors(surface) == middle_colors
        QTest.qWait(SurfaceActivationTransition.DURATION_MS + 30)
        assert _surface_colors(surface) == active_colors
    finally:
        window.close()
        other.close()


@pytest.mark.parametrize(
    "theme, inactive_color",
    [(LIGHT_THEME, "#F3F3F3"), (DARK_THEME, "#2B2B2B")],
    ids=["light", "dark"],
)
def test_navigation_overlay_background_tracks_window_activation(theme, inactive_color) -> None:
    window = ModernWindow(theme=theme)
    other = QWidget()
    try:
        navigation = NavigationView(theme=theme)
        navigation.setAutoSidebarOverlay(False)
        window.setCentralWidget(navigation)
        window.resize(480, 320)
        navigation.setSidebarOverlay(True)
        navigation.sidebar.setCollapsed(False, animated=False)
        window.show()
        other.show()
        paints = _PaintCounter(navigation.sidebar)

        _activate(window)
        active_colors = _surface_colors(navigation.sidebar)
        assert active_colors[0] != active_colors[1]
        paint_count = paints.count

        _activate(other)
        assert paints.count > paint_count
        assert _surface_colors(navigation.sidebar) == (QColor(inactive_color),) * 2

        _activate(window)
        assert _surface_colors(navigation.sidebar) == active_colors
    finally:
        window.close()
        other.close()
