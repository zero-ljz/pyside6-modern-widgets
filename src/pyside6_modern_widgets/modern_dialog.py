"""A QDialog with the same frameless chrome as ModernWindow."""

from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QColor, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QMenuBar, QWidget

from ._window_chrome import BackgroundFrame, WindowChromeOverlay, WindowTitleBar
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    palette_for_theme,
    theme_manager,
)


class ModernDialog(QDialog):
    """A native QDialog whose client-side chrome follows the modern theme."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        super().__init__(parent)
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self._metrics = metrics
        self._corner_radius = metrics.corner_radius
        self._resize_cursor_active = False
        self._native_opaque_surface = self._supports_native_window_corners()

        theme_manager().themeChanged.connect(self._on_global_theme_changed)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        if self._native_opaque_surface:
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        paint_radius = 0 if self._native_opaque_surface else self._corner_radius
        self._background_frame = BackgroundFrame(
            self,
            theme=self._theme,
            corner_radius=paint_radius,
            opaque_surface=self._native_opaque_surface,
        )
        self._background_frame.setObjectName("backgroundFrame")
        self._background_frame.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._title_bar = WindowTitleBar(
            self,
            theme=self._theme,
            metrics=self._metrics,
        )
        self._title_bar.setIcon(self.windowIcon())
        self.setContentsMargins(0, self._title_bar.height(), 0, 0)

        self._chrome_overlay = WindowChromeOverlay(
            self,
            theme=self._theme,
            corner_radius=paint_radius,
        )
        self._chrome_overlay.show()
        self._layout_chrome()
        self._install_resize_filters(self)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)
        self.apply_window_style()

    @staticmethod
    def _uses_windows_window_state() -> bool:
        return sys.platform == "win32" and QApplication.platformName() == "windows"

    @classmethod
    def _supports_native_window_corners(cls) -> bool:
        if not cls._uses_windows_window_state():
            return False
        get_windows_version = getattr(sys, "getwindowsversion", None)
        return get_windows_version is not None and get_windows_version().build >= 22000

    def theme(self) -> ModernTheme:
        return self._theme

    def setTheme(self, theme: ModernTheme | None) -> None:
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self.apply_window_style()

    def setCornerRadius(self, radius: int) -> None:
        self._corner_radius = max(0, radius)
        self.apply_window_style()

    def apply_window_style(self) -> None:
        """Apply the current theme without changing QDialog behavior."""
        radius = 0 if self.isMaximized() else self._corner_radius
        paint_radius = 0 if self._native_opaque_surface else radius
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self._background_frame.setTheme(self._theme)
        self._background_frame.setCornerRadius(paint_radius)
        self._title_bar.setTheme(self._theme)
        self._chrome_overlay.setTheme(self._theme)
        self._chrome_overlay.setCornerRadius(paint_radius)
        self._set_native_corner_preference(radius > 0)
        self._sync_inactive_title_color()
        self._raise_chrome()
        self.update()

    def setWindowIcon(self, icon: QIcon | QPixmap) -> None:
        window_icon = icon if isinstance(icon, QIcon) else QIcon(icon)
        super().setWindowIcon(window_icon)
        if hasattr(self, "_title_bar"):
            self._title_bar.setIcon(window_icon)

    def setWindowTitle(self, title: str) -> None:
        super().setWindowTitle(title)
        if hasattr(self, "_title_bar"):
            self._title_bar.setTitle(title)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not event.spontaneous():
            self.apply_window_style()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self.apply_window_style()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_chrome()

    def event(self, event) -> bool:
        handled = super().event(event)
        if event.type() in (
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        ):
            self._sync_inactive_title_color()
        return handled

    def eventFilter(self, watched, event) -> bool:
        if isinstance(watched, QWidget) and watched.window() is self:
            if not watched.hasMouseTracking():
                watched.setMouseTracking(True)
            event_type = event.type()
            if event_type == QEvent.Type.MouseMove:
                position = watched.mapTo(self, event.position().toPoint())
                self._set_resize_cursor(self._resize_edges_at(position))
            elif event_type == QEvent.Type.MouseButtonPress:
                position = watched.mapTo(self, event.position().toPoint())
                edges = self._resize_edges_at(position)
                if event.button() == Qt.MouseButton.LeftButton and edges:
                    handle = self.windowHandle()
                    if handle is not None and handle.startSystemResize(edges):
                        return True
        return super().eventFilter(watched, event)

    def _on_global_theme_changed(self, theme: ModernTheme) -> None:
        if self._uses_global_theme:
            self._theme = theme
            self.apply_window_style()

    def _layout_chrome(self) -> None:
        rect = self.rect()
        self._background_frame.setGeometry(rect)
        self._background_frame.lower()
        self._title_bar.setGeometry(0, 0, self.width(), self._title_bar.height())
        self._chrome_overlay.setGeometry(rect)
        self._raise_chrome()

    def _raise_chrome(self) -> None:
        self._title_bar.raise_()
        self._chrome_overlay.raise_()

    def _sync_inactive_title_color(self) -> None:
        probe = QMenuBar()
        probe.ensurePolished()
        color = QColor(
            probe.palette().color(
                QPalette.ColorGroup.Inactive,
                QPalette.ColorRole.ButtonText,
            )
        )
        self._title_bar.setInactiveTitleColor(color)
        probe.deleteLater()

    def _set_native_corner_preference(self, rounded: bool) -> None:
        if not self._native_opaque_surface or self.windowHandle() is None:
            return
        try:
            import ctypes
            from ctypes import wintypes

            preference = ctypes.c_int(2 if rounded else 1)
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            set_window_attribute.argtypes = [
                wintypes.HWND,
                wintypes.DWORD,
                ctypes.c_void_p,
                wintypes.DWORD,
            ]
            set_window_attribute.restype = ctypes.c_long
            set_window_attribute(
                wintypes.HWND(int(self.winId())),
                33,
                ctypes.byref(preference),
                ctypes.sizeof(preference),
            )
        except (AttributeError, OSError):
            return

    def _install_resize_filters(self, widget: QWidget) -> None:
        widget.setMouseTracking(True)
        for child in widget.children():
            if isinstance(child, QWidget):
                self._install_resize_filters(child)

    def _resize_edges_at(self, position: QPoint) -> Qt.Edge:
        if self.isMaximized():
            return Qt.Edge(0)

        edges = Qt.Edge(0)
        horizontally_resizable = self.minimumWidth() < self.maximumWidth()
        vertically_resizable = self.minimumHeight() < self.maximumHeight()
        if horizontally_resizable:
            if position.x() < 8:
                edges |= Qt.Edge.LeftEdge
            elif position.x() >= self.width() - 8:
                edges |= Qt.Edge.RightEdge
        if vertically_resizable:
            if position.y() < 8:
                edges |= Qt.Edge.TopEdge
            elif position.y() >= self.height() - 8:
                edges |= Qt.Edge.BottomEdge
        return edges

    def _set_resize_cursor(self, edges: Qt.Edge) -> None:
        if not edges:
            if self._resize_cursor_active:
                self.unsetCursor()
                self._resize_cursor_active = False
            return

        if edges in (
            Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
            Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
        ):
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif edges in (
            Qt.Edge.TopEdge | Qt.Edge.RightEdge,
            Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
        ):
            cursor = Qt.CursorShape.SizeBDiagCursor
        elif edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge):
            cursor = Qt.CursorShape.SizeHorCursor
        else:
            cursor = Qt.CursorShape.SizeVerCursor
        self.setCursor(cursor)
        self._resize_cursor_active = True
