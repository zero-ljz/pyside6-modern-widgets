"""A QDialog with the same platform-aware chrome as ModernWindow."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap, QPlatformSurfaceEvent
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from . import _system_menu
from ._macos_window import (
    configure_macos_native_title_bar,
    macos_window_is_in_live_resize,
    release_macos_title_bar,
    set_macos_window_appearance,
    uses_macos_native_title_bar,
    window_flags_with_chrome,
)
from ._theme_binding import ThemeBinding
from ._window_chrome import (
    BackgroundFrame,
    WindowChrome,
    WindowChromeOverlay,
    WindowDpiState,
    WindowResizeController,
    WindowSurfacePolicy,
    WindowTitleBar,
    current_window_surface_policy,
)
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    inherited_theme,
)

_DEFAULT_DIALOG_FLAGS = (
    Qt.WindowType.Dialog
    | Qt.WindowType.WindowTitleHint
    | Qt.WindowType.WindowSystemMenuHint
    | Qt.WindowType.WindowCloseButtonHint
)


class ModernDialog(QDialog):
    """A native QDialog whose client-side chrome follows the modern theme."""

    themeChanged = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = _DEFAULT_DIALOG_FLAGS,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        self._uses_native_macos_title_bar = uses_macos_native_title_bar()
        self._macos_title_bar_configured: bool | None = None
        self._macos_title_bar_syncing = False
        self._native_dpi = WindowDpiState()
        QDialog.__init__(
            self,
            parent,
            window_flags_with_chrome(f, native_macos_title_bar=self._uses_native_macos_title_bar),
        )
        self._macos_title_bar_resize_timer = QTimer(self)
        self._macos_title_bar_resize_timer.setInterval(50)
        self._macos_title_bar_resize_timer.setSingleShot(True)
        self._macos_title_bar_resize_timer.timeout.connect(self._sync_macos_native_title_bar)
        self._theme_override = theme
        self._theme = theme if theme is not None else inherited_theme(self)
        self._metrics = metrics
        self._corner_radius = metrics.corner_radius
        self._resize_controller = WindowResizeController(self)
        self._application_event_filter_installed = False
        self._surface_policy: WindowSurfacePolicy = current_window_surface_policy(
            native_macos_title_bar=self._uses_native_macos_title_bar
        )

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
            native_macos_title_bar=self._uses_native_macos_title_bar,
        )
        self._title_bar.setIcon(self.windowIcon())
        self._system_menu_controller = _system_menu.SystemMenuController(
            self, self._title_bar, self._metrics
        )

        self._chrome_overlay = WindowChromeOverlay(
            self,
            theme=self._theme,
            corner_radius=paint_radius,
        )
        self._chrome = WindowChrome(
            self,
            self._background_frame,
            self._chrome_overlay,
            self._title_bar,
            self._surface_policy,
        )
        self._chrome_overlay.show()
        self._sync_chrome_with_window_flags()
        self._layout_chrome()
        self._install_resize_filters(self)
        self._apply_window_style()
        self._theme_binding: ThemeBinding = ThemeBinding(self, self.theme, self._apply_window_style)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setWindowFlags(self, flags: Qt.WindowType) -> None:
        QDialog.setWindowFlags(
            self,
            window_flags_with_chrome(
                flags, native_macos_title_bar=self._uses_native_macos_title_bar
            ),
        )
        if hasattr(self, "_title_bar"):
            self._sync_chrome_with_window_flags()

    def setWindowFlag(self, flag: Qt.WindowType, on: bool = True) -> None:
        QDialog.setWindowFlag(self, flag, on)
        QDialog.setWindowFlag(
            self, Qt.WindowType.FramelessWindowHint, not self._uses_native_macos_title_bar
        )
        if hasattr(self, "_title_bar"):
            self._sync_chrome_with_window_flags()

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override locally; None restores ancestor/global theme inheritance."""
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def cornerRadius(self) -> int:
        return self._corner_radius

    def setCornerRadius(self, radius: int) -> None:
        self._corner_radius = max(0, radius)
        self._apply_window_style()

    def showSystemWindowMenu(self, position: QPoint) -> bool:
        if self._uses_native_macos_title_bar:
            return False
        return self._system_menu_controller.show(position)

    def _apply_window_style(self) -> None:
        self._theme = self.theme()
        self._chrome.apply(self._theme, self._corner_radius)
        if self._uses_native_macos_title_bar:
            self._chrome_overlay.hide()
            set_macos_window_appearance(self, dark=QColor(self._theme.surface).lightness() < 128)

    def _sync_macos_native_title_bar(self) -> None:
        if (
            not self._uses_native_macos_title_bar
            or not self.isVisible()
            or not self.internalWinId()
            or self._macos_title_bar_syncing
        ):
            return
        if macos_window_is_in_live_resize(self):
            self._macos_title_bar_resize_timer.start(50)
            return
        self._macos_title_bar_syncing = True
        try:
            layout = self.layout()
            if layout is not None:
                layout.activate()
            content_size = None
            if not self._macos_title_bar_configured:
                content_size = self.size().expandedTo(self.minimumSizeHint())
                if not self.testAttribute(Qt.WidgetAttribute.WA_Resized):
                    content_size = content_size.expandedTo(self.sizeHint())
                content_size = content_size.boundedTo(self.maximumSize())
            # Appearance changes can trigger AppKit's own traffic-light layout.
            # Apply them before the final title-bar configuration and alignment.
            set_macos_window_appearance(self, dark=QColor(self._theme.surface).lightness() < 128)
            self._macos_title_bar_configured = configure_macos_native_title_bar(
                self, title_bar_height=self._title_bar.height(), content_size=content_size
            )
            self._sync_chrome_with_window_flags()
            if content_size is not None:
                self.resize(content_size)
            if layout is not None:
                layout.invalidate()
                layout.activate()
            self._layout_chrome()
        finally:
            self._macos_title_bar_syncing = False

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
        self._sync_windows_dpi()
        if self._uses_native_macos_title_bar:
            # QDialog must finish its initial size/layout and modal show before
            # AppKit's full-size-content style is applied.
            self._macos_title_bar_resize_timer.start(0)
        self._set_application_event_filter_enabled(True)
        if not event.spontaneous():
            self._apply_window_style()

    def hideEvent(self, event) -> None:
        self._macos_title_bar_resize_timer.stop()
        self._finish_manual_resize()
        self._set_application_event_filter_enabled(False)
        super().hideEvent(event)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._set_resize_cursor(Qt.Edge(0))
            self._apply_window_style()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_chrome"):
            self._layout_chrome()
            if self._uses_native_macos_title_bar and not self._macos_title_bar_syncing:
                self._macos_title_bar_resize_timer.start(50)

    def event(self, event) -> bool:
        if (
            event.type() == QEvent.Type.PlatformSurface
            and isinstance(event, QPlatformSurfaceEvent)
            and event.surfaceEventType()
            == QPlatformSurfaceEvent.SurfaceEventType.SurfaceAboutToBeDestroyed
        ):
            self._macos_title_bar_resize_timer.stop()
            self._macos_title_bar_configured = None
            release_macos_title_bar(self)
        handled = super().event(event)
        if event.type() == QEvent.Type.WinIdChange:
            self._sync_windows_dpi()
            if (
                self._uses_native_macos_title_bar
                and hasattr(self, "_chrome")
                and self.isVisible()
                and self.internalWinId()
            ):
                self._macos_title_bar_resize_timer.start(0)
        return handled

    def _sync_windows_dpi(self) -> None:
        self._native_dpi.sync_window(self)

    def nativeEvent(self, event_type, message):
        if self._native_dpi.handle_native_event(self, message):
            return True, 0
        return super().nativeEvent(event_type, message)

    def eventFilter(self, watched, event) -> bool:
        if self._resize_controller.handle_event(
            watched, event, enabled=not self._uses_native_macos_title_bar
        ):
            return True
        return super().eventFilter(watched, event)

    def _begin_manual_resize(self, edges: Qt.Edge, global_position: QPoint) -> None:
        self._resize_controller.begin(edges, global_position)

    def _update_manual_resize(self, global_position: QPoint) -> None:
        self._resize_controller.update(global_position)

    def _finish_manual_resize(self) -> None:
        self._resize_controller.finish()

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
        self._chrome.layout()

    def _sync_chrome_with_window_flags(self) -> None:
        title_bar_visible = self._title_bar.syncWindowFlags(self.windowFlags())
        if self._uses_native_macos_title_bar and self._macos_title_bar_configured is False:
            self._title_bar.hide()
            title_bar_visible = False
        top_margin = self._title_bar.height() if title_bar_visible else 0
        QDialog.setContentsMargins(self, 0, top_margin, 0, 0)
        self._layout_chrome()

    def _install_resize_filters(self, widget: QWidget) -> None:
        self._resize_controller.install_tracking(widget)

    def _resize_edges_at(self, position: QPoint) -> Qt.Edge:
        return self._resize_controller.edges_at(position)

    def _set_resize_cursor(self, edges: Qt.Edge) -> None:
        self._resize_controller.set_cursor(edges)
