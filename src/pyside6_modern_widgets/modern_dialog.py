"""A QDialog with the same frameless chrome as ModernWindow."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QMenuBar, QWidget

from ._window_chrome import (
    BackgroundFrame,
    WindowChromeOverlay,
    WindowSurfacePolicy,
    WindowTitleBar,
    current_window_surface_policy,
    manual_resize_geometry,
)
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    palette_for_theme,
    theme_manager,
)

_DEFAULT_DIALOG_FLAGS = (
    Qt.WindowType.Dialog
    | Qt.WindowType.WindowTitleHint
    | Qt.WindowType.WindowSystemMenuHint
    | Qt.WindowType.WindowCloseButtonHint
)


class ModernDialog(QDialog):
    """A native QDialog whose client-side chrome follows the modern theme."""

    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = _DEFAULT_DIALOG_FLAGS,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        QDialog.__init__(self, parent, f | Qt.WindowType.FramelessWindowHint)
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self._metrics = metrics
        self._corner_radius = metrics.corner_radius
        self._resize_cursor_active = False
        self._manual_resize_edges = Qt.Edge(0)
        self._manual_resize_start_position = QPoint()
        self._manual_resize_start_geometry = QRect()
        self._application_event_filter_installed = False
        self._surface_policy: WindowSurfacePolicy = current_window_surface_policy()

        theme_manager().themeChanged.connect(self._on_global_theme_changed)
        self._surface_policy.apply_to(self)
        self.setMouseTracking(True)

        paint_radius = self._surface_policy.paint_corner_radius(self._corner_radius)
        self._background_frame = BackgroundFrame(
            self,
            theme=self._theme,
            corner_radius=paint_radius,
            opaque_surface=self._surface_policy.opaque_surface,
        )
        self._background_frame.setObjectName("backgroundFrame")
        self._background_frame.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._title_bar = WindowTitleBar(
            self,
            theme=self._theme,
            metrics=self._metrics,
        )
        self._title_bar.setIcon(self.windowIcon())

        self._chrome_overlay = WindowChromeOverlay(
            self,
            theme=self._theme,
            corner_radius=paint_radius,
        )
        self._chrome_overlay.show()
        self._sync_chrome_with_window_flags()
        self._layout_chrome()
        self._install_resize_filters(self)
        self.apply_window_style()

    def theme(self) -> ModernTheme:
        return self._theme

    def setWindowFlags(self, flags: Qt.WindowType) -> None:
        QDialog.setWindowFlags(self, flags | Qt.WindowType.FramelessWindowHint)
        if hasattr(self, "_title_bar"):
            self._sync_chrome_with_window_flags()

    def setWindowFlag(self, flag: Qt.WindowType, on: bool = True) -> None:
        QDialog.setWindowFlag(self, flag, on)
        QDialog.setWindowFlag(self, Qt.WindowType.FramelessWindowHint, True)
        if hasattr(self, "_title_bar"):
            self._sync_chrome_with_window_flags()

    def setTheme(self, theme: ModernTheme | None) -> None:
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self.apply_window_style()

    def setCornerRadius(self, radius: int) -> None:
        self._corner_radius = max(0, radius)
        self.apply_window_style()

    def apply_window_style(self) -> None:
        """Apply the current theme without changing QDialog behavior."""
        radius = 0 if self.isMaximized() or self.isFullScreen() else self._corner_radius
        paint_radius = self._surface_policy.paint_corner_radius(radius)
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
        self._set_application_event_filter_enabled(True)
        if not event.spontaneous():
            self.apply_window_style()

    def hideEvent(self, event) -> None:
        self._finish_manual_resize()
        self._set_application_event_filter_enabled(False)
        super().hideEvent(event)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._set_resize_cursor(Qt.Edge(0))
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
                if self._manual_resize_edges:
                    if event.buttons() & Qt.MouseButton.LeftButton:
                        self._update_manual_resize(event.globalPosition().toPoint())
                        return True
                    self._finish_manual_resize()
                position = watched.mapTo(self, event.position().toPoint())
                self._set_resize_cursor(self._resize_edges_at(position))
            elif event_type == QEvent.Type.MouseButtonPress:
                position = watched.mapTo(self, event.position().toPoint())
                edges = self._resize_edges_at(position)
                if event.button() == Qt.MouseButton.LeftButton and edges:
                    handle = self.windowHandle()
                    if handle is not None and handle.startSystemResize(edges):
                        return True
                    if not QApplication.platformName().startswith("wayland"):
                        self._begin_manual_resize(edges, event.globalPosition().toPoint())
                        return True
            elif event_type == QEvent.Type.MouseButtonRelease and self._manual_resize_edges:
                self._finish_manual_resize()
                return True
        return super().eventFilter(watched, event)

    def _begin_manual_resize(self, edges: Qt.Edge, global_position: QPoint) -> None:
        self._manual_resize_edges = edges
        self._manual_resize_start_position = global_position
        self._manual_resize_start_geometry = self.geometry()

    def _update_manual_resize(self, global_position: QPoint) -> None:
        delta = global_position - self._manual_resize_start_position
        self.setGeometry(
            manual_resize_geometry(
                self,
                self._manual_resize_start_geometry,
                self._manual_resize_edges,
                delta,
            )
        )

    def _finish_manual_resize(self) -> None:
        self._manual_resize_edges = Qt.Edge(0)

    def _on_global_theme_changed(self, theme: ModernTheme) -> None:
        if self._uses_global_theme:
            self._theme = theme
            self.apply_window_style()

    def _set_application_event_filter_enabled(self, enabled: bool) -> None:
        if enabled == self._application_event_filter_installed:
            return
        application = QApplication.instance()
        if application is None:
            return
        if enabled:
            application.installEventFilter(self)
        else:
            application.removeEventFilter(self)
        self._application_event_filter_installed = enabled

    def _layout_chrome(self) -> None:
        rect = self.rect()
        self._background_frame.setGeometry(rect)
        self._background_frame.lower()
        self._title_bar.setGeometry(0, 0, self.width(), self._title_bar.height())
        self._chrome_overlay.setGeometry(rect)
        self._raise_chrome()

    def _sync_chrome_with_window_flags(self) -> None:
        title_bar_visible = self._title_bar.syncWindowFlags(self.windowFlags())
        top_margin = self._title_bar.height() if title_bar_visible else 0
        QDialog.setContentsMargins(self, 0, top_margin, 0, 0)
        self._layout_chrome()

    def _raise_chrome(self) -> None:
        self._chrome_overlay.raise_()
        self._title_bar.raise_()

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
        self._surface_policy.apply_native_corner_preference(self, rounded)

    def _install_resize_filters(self, widget: QWidget) -> None:
        widget.setMouseTracking(True)
        for child in widget.children():
            if isinstance(child, QWidget):
                self._install_resize_filters(child)

    def _resize_edges_at(self, position: QPoint) -> Qt.Edge:
        if self.isMaximized() or self.isFullScreen():
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
