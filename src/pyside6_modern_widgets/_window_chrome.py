"""Shared visual building blocks for modern top-level widgets."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from math import ceil, floor
from typing import Generic, Literal, TypeVar

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QRect, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import (
    QBrush,
    QColor,
    QEnterEvent,
    QIcon,
    QIconEngine,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStyle,
    QStyleOptionButton,
    QStylePainter,
    QWidget,
)

from . import _resources  # noqa: F401
from ._macos_window import MACOS_TRAFFIC_LIGHT_INSET, perform_macos_title_bar_double_click
from ._windows_window import (
    HTTRANSPARENT,
    WM_DPICHANGED,
    WM_EXITSIZEMOVE,
    WM_GETDPISCALEDSIZE,
    WM_GETMINMAXINFO,
    WM_NCHITTEST,
    WM_WINDOWPOSCHANGING,
    WindowsMessage,
    constrain_window_position,
    read_message,
    set_size_constraints,
    set_window_corner_preference,
    window_dpi,
)
from .theme import ModernMetrics, ModernTheme, _chrome_palette, palette_for_theme, tinted_icon

WindowWidget = TypeVar("WindowWidget", bound=QWidget)


def _foreground_opacity(palette: QPalette, role: QPalette.ColorRole) -> float:
    if palette.currentColorGroup() != QPalette.ColorGroup.Inactive:
        return 1.0
    active_alpha = palette.color(QPalette.ColorGroup.Active, role).alphaF()
    if active_alpha == 0:
        return 1.0
    return min(1.0, palette.color(role).alphaF() / active_alpha)


class _OpacityIconEngine(QIconEngine):
    """Preserve icon modes, colors and DPR while adapting to the chrome palette."""

    def __init__(self, source: QIcon, opacity: float) -> None:
        super().__init__()
        self._source = QIcon(source)
        self._opacity = opacity

    def clone(self) -> QIconEngine:
        return _OpacityIconEngine(self._source, self._opacity)

    def paint(self, painter, rect, mode, state) -> None:
        painter.save()
        painter.setOpacity(painter.opacity() * self._opacity)
        self._source.paint(painter, rect, Qt.AlignmentFlag.AlignCenter, mode, state)
        painter.restore()

    def pixmap(self, size, mode, state) -> QPixmap:
        return self.scaledPixmap(size, mode, state, 1.0)

    def scaledPixmap(self, size, mode, state, scale) -> QPixmap:
        pixmap = self._source.pixmap(size, scale, mode, state)
        if pixmap.isNull():
            return pixmap
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.fillRect(pixmap.rect(), QColor(0, 0, 0, round(255 * self._opacity)))
        painter.end()
        return pixmap


class TitleBarButton(QPushButton):
    """Keep QStyle button rendering; adapt fixed icon pixels to its palette group."""

    def applyTheme(self, theme: ModernTheme, metrics: ModernMetrics) -> None:
        self.setStyleSheet(button_style(theme, metrics))
        # QSS can replace the inherited palette even without a foreground rule.
        self.setPalette(_chrome_palette(theme, self.palette()))

    def paintEvent(self, event) -> None:
        option = QStyleOptionButton()
        self.initStyleOption(option)
        opacity = _foreground_opacity(self.palette(), QPalette.ColorRole.ButtonText)
        if opacity < 1.0 and not self.icon().isNull():
            option.icon = QIcon(_OpacityIconEngine(self.icon(), opacity))  # type: ignore[attr-defined]
        painter = QStylePainter(self)
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)


class _TitleBarIconLabel(QLabel):
    def paintEvent(self, event) -> None:
        pixmap = self.pixmap()
        if pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setOpacity(_foreground_opacity(self.palette(), QPalette.ColorRole.WindowText))
        painter.drawPixmap(self.contentsRect(), pixmap)


class _TitleBarCloseButton(TitleBarButton):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._normal_icon = QIcon()
        self._hover_icon = QIcon()

    def setTheme(self, theme: ModernTheme) -> None:
        source_icon = QIcon(":/pyside6_modern_widgets/icons/close.svg")
        self._normal_icon = tinted_icon(source_icon, theme.text)
        self._hover_icon = tinted_icon(source_icon, theme.danger)
        self.setIcon(self._hover_icon if self.underMouse() else self._normal_icon)

    def enterEvent(self, event: QEnterEvent) -> None:
        self.setIcon(self._hover_icon)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.setIcon(self._normal_icon)
        super().leaveEvent(event)


def uses_windows_window_state() -> bool:
    return sys.platform == "win32" and QApplication.platformName() == "windows"


def _rounded_dpi_scale(dpi: int) -> float:
    """Match Qt's per-monitor scaling before its QScreen catches up with Windows."""
    scale = dpi / 96
    policy = QApplication.highDpiScaleFactorRoundingPolicy()
    if policy == Qt.HighDpiScaleFactorRoundingPolicy.Round:
        return max(1, floor(scale + 0.5))
    if policy == Qt.HighDpiScaleFactorRoundingPolicy.Ceil:
        return max(1, ceil(scale))
    if policy == Qt.HighDpiScaleFactorRoundingPolicy.Floor:
        return max(1, floor(scale))
    if policy == Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor:
        return max(1, floor(scale + 0.25))
    return scale


@dataclass
class WindowDpiState:
    """Shared native DPI tracking for frameless windows and dialogs."""

    dpi: int | None = None
    scale: float | None = None
    _changed: bool = False
    _pending_scale: float | None = None

    def reset(self, dpi: int | None = None, scale: float | None = None) -> None:
        """Synchronize once Qt and the native handle agree on the current screen."""
        self.dpi = dpi
        self.scale = scale
        self._changed = False
        self._pending_scale = None

    def handle_message(self, widget: QWidget, message: WindowsMessage) -> bool:
        if message.message == WM_GETDPISCALEDSIZE:
            # Windows can query minimum/maximum sizes while preparing the new
            # rectangle, before WM_DPICHANGED commits the monitor transition.
            # Leave Qt responsible for the suggested size and keep speculative
            # queries separate from the committed DPI (queries may be repeated
            # or cancelled at the monitor boundary).
            dpi = message.w_param
            self._pending_scale = None
            if dpi and self.dpi and self.scale is not None:
                self._pending_scale = (
                    self.scale * _rounded_dpi_scale(dpi) / _rounded_dpi_scale(self.dpi)
                )
        elif message.message == WM_EXITSIZEMOVE:
            self._pending_scale = None
        elif message.message == WM_DPICHANGED:
            self._pending_scale = None
            dpi = (message.w_param >> 16) & 0xFFFF
            if dpi and self.dpi and self.scale is not None:
                # Qt's screen may still have the old DPI, or may already have
                # the new DPI. Chain native changes independently, including
                # rapid reversals, while preserving Qt's global scale/rounding.
                self.scale *= _rounded_dpi_scale(dpi) / _rounded_dpi_scale(self.dpi)
                self.dpi = dpi
                self._changed = True
        elif message.message == WM_WINDOWPOSCHANGING:
            if (
                self._changed
                and self.scale is not None
                and abs(self.scale - widget.devicePixelRatioF()) > 1e-6
            ):
                # Qt 6.8's closestAcceptableGeometry() converts this target-DPI
                # rectangle using QWindow's still-old screen. Height-for-width
                # layouts then enlarge it before the native resize is applied.
                # Run the same layout constraints using the committed DPI here;
                # let Qt handle the ensuing screen/geometry notifications.
                def acceptable_size(size: tuple[int, int]) -> tuple[int, int]:
                    accepted = QLayout.closestAcceptableSize(widget, QSize(*size))
                    return accepted.width(), accepted.height()

                return constrain_window_position(message.l_param, self.scale, acceptable_size)
        elif message.message == WM_GETMINMAXINFO:
            if self._pending_scale is not None and self.scale is not None:
                # Qt still interprets native resize events using the source DPR
                # until WM_DPICHANGED. Keep speculative bounds permissive so a
                # target minimum cannot become a new logical window size.
                minimum_scale = min(self.scale, self._pending_scale)
                maximum_scale = max(self.scale, self._pending_scale)
            elif self._changed and self.scale is not None:
                minimum_scale = maximum_scale = self.scale
            else:
                return False
            set_size_constraints(
                message.l_param,
                (widget.minimumWidth(), widget.minimumHeight()),
                (widget.maximumWidth(), widget.maximumHeight()),
                minimum_scale,
                maximum_scale=maximum_scale,
            )
            return True
        return False

    def sync_window(self, widget: QWidget) -> None:
        self.reset()
        handle = widget.windowHandle()
        if uses_windows_window_state() and handle is not None:
            self.reset(window_dpi(int(handle.winId())), widget.devicePixelRatioF())

    def handle_native_event(self, widget: QWidget, message) -> bool:
        if not uses_windows_window_state():
            return False
        try:
            native = read_message(int(message))
        except (TypeError, ValueError):
            return False
        return self.handle_message(widget, native)


@dataclass(frozen=True)
class WindowSurfacePolicy:
    opaque_surface: bool
    native_corners: bool

    def apply_to(self, widget: QWidget) -> None:
        widget.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, not self.opaque_surface)
        widget.setAutoFillBackground(self.opaque_surface)

    def paint_corner_radius(self, radius: int) -> int:
        return 0 if self.opaque_surface else max(0, radius)

    def apply_native_corner_preference(self, widget: QWidget, rounded: bool) -> None:
        if self.native_corners and widget.windowHandle() is not None:
            set_window_corner_preference(int(widget.winId()), rounded=rounded)


def current_window_surface_policy(*, native_macos_title_bar: bool = False) -> WindowSurfacePolicy:
    native_windows = uses_windows_window_state()
    get_windows_version = getattr(sys, "getwindowsversion", None)
    native_corners = (
        native_windows and get_windows_version is not None and get_windows_version().build >= 22000
    )
    return WindowSurfacePolicy(
        opaque_surface=native_windows or native_macos_title_bar,
        native_corners=native_corners,
    )


def button_style(theme: ModernTheme, metrics: ModernMetrics) -> str:
    return f"""
    QPushButton {{ border: none; background-color: transparent; }}
    QPushButton:hover, QPushButton[nativeHover="true"] {{
        background-color: {theme.control_hover};
        border-radius: {metrics.control_radius}px;
    }}
    QPushButton:pressed {{ background-color: {theme.control_pressed}; }}
    """


def manual_resize_geometry(
    widget: QWidget,
    start_geometry: QRect,
    edges: Qt.Edge,
    delta: QPoint,
) -> QRect:
    """Return constrained geometry for a client-side resize fallback."""
    geometry = QRect(start_geometry)
    if edges & Qt.Edge.LeftEdge:
        width = max(widget.minimumWidth(), min(widget.maximumWidth(), geometry.width() - delta.x()))
        geometry.setX(geometry.x() + geometry.width() - width)
        geometry.setWidth(width)
    elif edges & Qt.Edge.RightEdge:
        geometry.setWidth(
            max(widget.minimumWidth(), min(widget.maximumWidth(), geometry.width() + delta.x()))
        )
    if edges & Qt.Edge.TopEdge:
        height = max(
            widget.minimumHeight(), min(widget.maximumHeight(), geometry.height() - delta.y())
        )
        geometry.setY(geometry.y() + geometry.height() - height)
        geometry.setHeight(height)
    elif edges & Qt.Edge.BottomEdge:
        geometry.setHeight(
            max(widget.minimumHeight(), min(widget.maximumHeight(), geometry.height() + delta.y()))
        )
    return geometry


class WindowResizeController:
    """Shared client-side resizing; native frame and live-paint policy stay with the host."""

    def __init__(
        self,
        widget: QWidget,
        *,
        on_start: Callable[[], None] | None = None,
        on_finish: Callable[[], None] | None = None,
    ) -> None:
        self.widget = widget
        self.on_start = on_start
        self.on_finish = on_finish
        self.edges = Qt.Edge(0)
        self.start_position = QPoint()
        self.start_geometry = QRect()
        self.cursor_active = False

    def install_tracking(self, widget: QWidget) -> None:
        widget.setMouseTracking(True)
        for child in widget.children():
            if isinstance(child, QWidget):
                self.install_tracking(child)

    def edges_at(self, position: QPoint) -> Qt.Edge:
        widget = self.widget
        if widget.isMaximized() or widget.isFullScreen():
            return Qt.Edge(0)
        edges = Qt.Edge(0)
        if widget.minimumWidth() < widget.maximumWidth():
            if position.x() < 8:
                edges |= Qt.Edge.LeftEdge
            elif position.x() >= widget.width() - 8:
                edges |= Qt.Edge.RightEdge
        if widget.minimumHeight() < widget.maximumHeight():
            if position.y() < 8:
                edges |= Qt.Edge.TopEdge
            elif position.y() >= widget.height() - 8:
                edges |= Qt.Edge.BottomEdge
        return edges

    def set_cursor(self, edges: Qt.Edge) -> None:
        if not edges:
            if self.cursor_active:
                self.widget.unsetCursor()
                self.cursor_active = False
            return
        if edges in (Qt.Edge.TopEdge | Qt.Edge.LeftEdge, Qt.Edge.BottomEdge | Qt.Edge.RightEdge):
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif edges in (Qt.Edge.TopEdge | Qt.Edge.RightEdge, Qt.Edge.BottomEdge | Qt.Edge.LeftEdge):
            cursor = Qt.CursorShape.SizeBDiagCursor
        elif edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge):
            cursor = Qt.CursorShape.SizeHorCursor
        else:
            cursor = Qt.CursorShape.SizeVerCursor
        self.widget.setCursor(cursor)
        self.cursor_active = True

    def begin(self, edges: Qt.Edge, position: QPoint) -> None:
        self.edges = edges
        self.start_position = position
        self.start_geometry = self.widget.geometry()
        if self.on_start is not None:
            self.on_start()

    def update(self, position: QPoint) -> None:
        self.widget.setGeometry(
            manual_resize_geometry(
                self.widget,
                self.start_geometry,
                self.edges,
                position - self.start_position,
            )
        )

    def finish(self) -> None:
        self.edges = Qt.Edge(0)

    def handle_event(self, watched, event, *, enabled=True, consume_manual_release=True) -> bool:
        if not isinstance(watched, QWidget) or watched.window() is not self.widget:
            return False
        if not watched.hasMouseTracking():
            watched.setMouseTracking(True)
        if not enabled:
            return False
        if event.type() == QEvent.Type.MouseMove:
            if self.edges:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    self.update(event.globalPosition().toPoint())
                    return True
                self.finish()
            self.set_cursor(self.edges_at(watched.mapTo(self.widget, event.position().toPoint())))
        elif event.type() == QEvent.Type.MouseButtonPress:
            edges = self.edges_at(watched.mapTo(self.widget, event.position().toPoint()))
            if event.button() == Qt.MouseButton.LeftButton and edges:
                handle = self.widget.windowHandle()
                if handle is not None and handle.startSystemResize(edges):
                    if self.on_start is not None:
                        self.on_start()
                    return True
                if not QApplication.platformName().startswith("wayland"):
                    self.begin(edges, event.globalPosition().toPoint())
                    return True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            was_manual = bool(self.edges)
            self.finish()
            if self.on_finish is not None:
                self.on_finish()
            return was_manual and consume_manual_release
        return False


@dataclass
class WindowChrome:
    """Apply surface styling and stacking consistently without owning dialog behavior."""

    widget: QWidget
    background: BackgroundFrame
    overlay: WindowChromeOverlay
    title_bar: WindowTitleBar | None
    policy: WindowSurfacePolicy

    def raise_layers(self) -> None:
        self.overlay.raise_()
        if self.title_bar is not None:
            self.title_bar.raise_()

    def layout(self) -> None:
        self.background.setGeometry(self.widget.rect())
        self.background.lower()
        self.overlay.setGeometry(self.widget.rect())
        if self.title_bar is not None:
            self.title_bar.setGeometry(0, 0, self.widget.width(), self.title_bar.height())
        self.raise_layers()

    def apply(self, theme: ModernTheme, corner_radius: int) -> None:
        radius = (
            0 if self.widget.isMaximized() or self.widget.isFullScreen() else max(0, corner_radius)
        )
        paint_radius = self.policy.paint_corner_radius(radius)
        self.widget.setPalette(palette_for_theme(theme, self.widget.palette()))
        self.background.setTheme(theme)
        self.background.setCornerRadius(paint_radius)
        self.overlay.setTheme(theme)
        self.overlay.setCornerRadius(paint_radius)
        if self.title_bar is not None:
            self.title_bar.setTheme(theme)
        self.policy.apply_native_corner_preference(self.widget, radius > 0)
        self.layout()
        self.widget.update()


def paint_watercolor(
    painter: QPainter, rect: QRectF, theme: ModernTheme, surface_width: int
) -> None:
    painter.fillRect(rect, QColor(theme.watercolor_base))
    for color, x, y, radius in theme.watercolor_spots:
        gradient = QRadialGradient(surface_width * x, rect.height() * y, surface_width * radius)
        gradient.setColorAt(0, QColor(color))
        gradient.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(rect)


def inactive_surface_color(theme: ModernTheme) -> QColor:
    """Use a neutral light background while retaining dark theme surfaces."""
    surface = QColor(theme.surface)
    return surface if surface.lightness() < 128 else QColor("#F3F3F3")


class SurfaceActivationTransition(QVariantAnimation):
    """Fade the background effect without changing content or window opacity."""

    DURATION_MS = 250

    def __init__(self, widget: QWidget) -> None:
        super().__init__(widget)
        self._widget = widget
        self.opacity = float(widget.isActiveWindow())
        self.setEasingCurve(QEasingCurve.Type.Linear)
        self.valueChanged.connect(self._set_opacity)
        widget.installEventFilter(self)

    def _set_opacity(self, value: float) -> None:
        self.opacity = value
        self._widget.update()

    def eventFilter(self, watched, event) -> bool:
        event_type = event.type()
        if event_type in (
            QEvent.Type.WindowActivate,
            QEvent.Type.WindowDeactivate,
            QEvent.Type.Show,
            QEvent.Type.Hide,
        ):
            target = float(self._widget.isActiveWindow())
            self.stop()
            if event_type in (QEvent.Type.Show, QEvent.Type.Hide) or not self._widget.isVisible():
                self._set_opacity(target)
            elif self.opacity != target:
                # Changing duration can emit valueChanged using the previous endpoints.
                current_opacity = self.opacity
                self.setDuration(max(1, round(self.DURATION_MS * abs(target - current_opacity))))
                self.setStartValue(current_opacity)
                self.setEndValue(target)
                self.start()
        return super().eventFilter(watched, event)


class BackgroundFrame(QFrame):
    """Watercolor for active windows, with a solid inactive surface."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme,
        corner_radius: int,
        opaque_surface: bool = False,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._corner_radius = corner_radius
        self._opaque_surface = opaque_surface
        self._watercolor_cache: QPixmap | None = None
        self._watercolor_cache_signature: tuple[int, int, float, ModernTheme] | None = None
        self._live_resize = False
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, not opaque_surface)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, opaque_surface)
        self._activation_transition = SurfaceActivationTransition(self)

    def nativeEvent(self, event_type, message):
        if (
            uses_windows_window_state()
            and self.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            and read_message(int(message)).message == WM_NCHITTEST
        ):
            return True, HTTRANSPARENT
        return super().nativeEvent(event_type, message)

    def setTheme(self, theme: ModernTheme) -> None:
        self._theme = theme
        self._invalidate_watercolor_cache()
        self.update()

    def setCornerRadius(self, radius: int) -> None:
        self._corner_radius = radius
        self.update()

    def setLiveResize(self, active: bool) -> None:
        if active == self._live_resize:
            return
        if active and self.isActiveWindow():
            self._ensure_watercolor_cache()
        self._live_resize = active
        if not active:
            self._invalidate_watercolor_cache()
        self.update()

    def _invalidate_watercolor_cache(self) -> None:
        self._watercolor_cache = None
        self._watercolor_cache_signature = None

    def invalidateSurfaceCache(self) -> None:
        """Discard device-dependent pixels after a screen metric change."""
        self._invalidate_watercolor_cache()
        self.update()

    def _ensure_watercolor_cache(self) -> QPixmap:
        dpr = self.devicePixelRatioF()
        signature = (self.width(), self.height(), dpr, self._theme)
        if self._watercolor_cache is not None and (
            self._live_resize or signature == self._watercolor_cache_signature
        ):
            return self._watercolor_cache

        logical_size = self.size().expandedTo(QSize(1, 1))
        pixel_size = QSize(
            max(1, round(logical_size.width() * dpr)),
            max(1, round(logical_size.height() * dpr)),
        )
        pixmap = QPixmap(pixel_size)
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        logical_rect = QRectF(0, 0, logical_size.width(), logical_size.height())
        paint_watercolor(painter, logical_rect, self._theme, logical_size.width())
        painter.end()
        self._watercolor_cache = pixmap
        self._watercolor_cache_signature = signature
        return pixmap

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._opaque_surface:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        if self._corner_radius > 0:
            border_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            path = QPainterPath()
            path.addRoundedRect(border_rect, self._corner_radius, self._corner_radius)
            painter.setClipPath(path)
        opacity = self._activation_transition.opacity
        if opacity > 0:
            painter.drawPixmap(self.rect(), self._ensure_watercolor_cache())
        if opacity < 1:
            painter.setOpacity(1 - opacity)
            painter.fillRect(self.rect(), inactive_surface_color(self._theme))


class WindowChromeOverlay(QWidget):
    """Anti-aliased corner clipping and border rendered above window content."""

    def __init__(
        self,
        parent: QWidget,
        *,
        theme: ModernTheme,
        corner_radius: int,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._corner_radius = corner_radius
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def nativeEvent(self, event_type, message):
        # Native siblings can give this overlay an HWND. Qt's mouse attribute alone
        # does not make Windows pass input through that native child window.
        if uses_windows_window_state() and read_message(int(message)).message == WM_NCHITTEST:
            return True, HTTRANSPARENT
        return super().nativeEvent(event_type, message)

    def setTheme(self, theme: ModernTheme) -> None:
        self._theme = theme
        self.update()

    def setCornerRadius(self, radius: int) -> None:
        self._corner_radius = radius
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        border_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        border_path = QPainterPath()
        border_path.addRoundedRect(border_rect, self._corner_radius, self._corner_radius)

        if self._corner_radius > 0:
            outside_path = QPainterPath()
            outside_path.addRect(QRectF(self.rect()))
            outside_path = outside_path.subtracted(border_path)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillPath(outside_path, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        painter.setPen(QPen(QColor(self._theme.border), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(border_path)


class WindowTitleBar(QWidget, Generic[WindowWidget]):
    """Shared title, icon, close button, and native window dragging."""

    def __init__(
        self,
        parent: WindowWidget,
        *,
        theme: ModernTheme,
        metrics: ModernMetrics,
        allows_maximize: bool = False,
        native_macos_title_bar: bool = False,
    ) -> None:
        super().__init__(parent)
        self.parent_window: WindowWidget = parent
        self._theme = theme
        self._metrics = metrics
        self._allows_maximize = allows_maximize
        self._native_macos_title_bar = native_macos_title_bar
        self._title_alignment: Literal["left", "center"] = "left"
        self._title_visible = True
        self._icon_visible = True
        self._has_icon = False
        self._manual_move_offset: QPoint | None = None
        self.setObjectName("CustomTitleBar")
        self.setAutoFillBackground(False)
        if self._native_macos_title_bar:
            self.setAttribute(Qt.WidgetAttribute.WA_LayoutOnEntireRect, True)
        self._init_ui()
        if self._native_macos_title_bar:
            self.setTitleAlignment("center")

    def _init_ui(self) -> None:
        padding = 5
        title_bar_height = max(
            self._metrics.title_bar_height,
            self._metrics.title_button_size + padding * 2,
        )
        self.setFixedHeight(title_bar_height)

        self.main_layout = QHBoxLayout(self)
        left_margin = MACOS_TRAFFIC_LIGHT_INSET if self._native_macos_title_bar else padding
        self.main_layout.setContentsMargins(left_margin, padding, padding, padding)
        self.main_layout.setSpacing(5)

        self.iconLabel = _TitleBarIconLabel(self)
        self.iconLabel.setFixedSize(20, 20)
        self.iconLabel.setScaledContents(True)
        self.iconLabel.hide()
        self.main_layout.addWidget(self.iconLabel)

        self.left_layout = QHBoxLayout()
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(1)
        self.main_layout.addLayout(self.left_layout)

        self.titleLabel = QLabel(self.parent_window.windowTitle(), self)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.titleLabel.setObjectName("ModernWindowTitle")
        self.titleLabel.setMinimumWidth(0)
        self.main_layout.insertWidget(1, self.titleLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self._title_spacer = QSpacerItem(
            0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.main_layout.addSpacerItem(self._title_spacer)
        self.main_layout.setStretch(self.main_layout.count() - 1, 1)

        self.right_layout = QHBoxLayout()
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(1)
        self.main_layout.addLayout(self.right_layout)

        self.closeButton = _TitleBarCloseButton(self)
        # Window controls must not enter the content's tab order or become a
        # dialog's default button.
        self.closeButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.closeButton.setAutoDefault(False)
        self.closeButton.setFixedSize(
            self._metrics.title_button_size,
            self._metrics.title_button_size,
        )
        self.closeButton.clicked.connect(self.parent_window.close)
        self.main_layout.addWidget(self.closeButton)
        WindowTitleBar._retranslate_ui(self)
        WindowTitleBar.setTheme(self, self._theme)

    def _retranslate_ui(self) -> None:
        self.closeButton.setToolTip(self.tr("Close"))

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()

    def event(self, event) -> bool:
        handled = super().event(event)
        if event.type() in (QEvent.Type.LayoutRequest, QEvent.Type.Resize) and hasattr(
            self, "_title_spacer"
        ):
            self.main_layout.activate()
            self._layout_title()
        return handled

    def contextMenuEvent(self, event) -> None:
        if self._native_macos_title_bar:
            super().contextMenuEvent(event)
            return
        show_system_menu = getattr(self.parent_window, "showSystemWindowMenu", None)
        if show_system_menu is not None and show_system_menu(event.globalPos()):
            event.accept()
            return
        super().contextMenuEvent(event)

    def _layout_title(self) -> None:
        if self._title_alignment == "left":
            return
        # Center the text on the window, without covering the icon or controls.
        available = self._title_spacer.geometry()
        width = min(self.titleLabel.sizeHint().width(), max(0, available.width()))
        left = max(
            available.left(),
            min((self.width() - width) // 2, available.right() + 1 - width),
        )
        margins = self.main_layout.contentsMargins()
        top = margins.top()
        height = max(0, self.height() - top - margins.bottom())
        self.titleLabel.setGeometry(left, top, width, height)

    def setTheme(self, theme: ModernTheme) -> None:
        self._theme = theme
        self.setPalette(_chrome_palette(theme, self.palette()))
        title_font = self.titleLabel.font()
        title_font.setPointSizeF(max(title_font.pointSizeF(), 10.5))
        self.titleLabel.setFont(title_font)
        # Global QSS can stop QLabel from inheriting its parent's palette even
        # when its selectors only target unrelated labels (for example page titles).
        self.titleLabel.setPalette(self.palette())
        self.iconLabel.setPalette(self.palette())
        self._layout_title()
        buttons: Iterable[TitleBarButton] = self.findChildren(TitleBarButton)
        for button in buttons:
            button.applyTheme(theme, self._metrics)
        self.closeButton.setTheme(theme)

    def setIcon(self, icon: QIcon) -> None:
        self._has_icon = not icon.isNull()
        self.iconLabel.setVisible(
            self._icon_visible and self._has_icon and not self._native_macos_title_bar
        )
        if self._has_icon:
            self.iconLabel.setPixmap(icon.pixmap(20, 20))
        else:
            self.iconLabel.clear()
        self._layout_title()

    def addCustomWidget(self, widget: QWidget, align: Literal["left", "right"] = "right") -> None:
        """Insert a vertically centered widget in the left or right control area."""
        if align not in ("left", "right"):
            raise ValueError("align must be left or right")
        if self._native_macos_title_bar:
            widget.setAttribute(Qt.WidgetAttribute.WA_ContentsMarginsRespectsSafeArea, False)
        if align == "left":
            self.left_layout.addWidget(
                widget, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        else:
            self.right_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)

    def setTitle(self, title: str) -> None:
        self.titleLabel.setText(title)
        self._layout_title()

    def setTitleVisible(self, visible: bool) -> None:
        """Show or hide title text without changing the window title or icon visibility."""
        self._title_visible = visible
        self.titleLabel.setVisible(visible)
        self._layout_title()

    def isTitleVisible(self) -> bool:
        """Return whether title text is enabled, even in a hidden window."""
        return self._title_visible

    def setIconVisible(self, visible: bool) -> None:
        """Show or hide the title bar icon independently of title text."""
        self._icon_visible = visible
        self.iconLabel.setVisible(visible and self._has_icon and not self._native_macos_title_bar)
        self._layout_title()

    def isIconVisible(self) -> bool:
        """Return the icon visibility setting, even in a hidden window or with no icon."""
        return self._icon_visible

    def setTitleAlignment(self, alignment: Literal["left", "center"]) -> None:
        """Align title text left (default) or to the window center; keep the icon left."""
        if alignment not in ("left", "center"):
            raise ValueError("title alignment must be 'left' or 'center'")
        if alignment == self._title_alignment:
            return
        self._title_alignment = alignment
        if alignment == "left":
            self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.main_layout.insertWidget(1, self.titleLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.main_layout.removeWidget(self.titleLabel)
        self.main_layout.activate()
        self._layout_title()

    def titleAlignment(self) -> Literal["left", "center"]:
        """Return the configured alignment of the title text."""
        return self._title_alignment

    def syncWindowFlags(self, flags: Qt.WindowType) -> bool:
        """Synchronize the controls shared by simple frameless windows."""
        window_type = flags & Qt.WindowType.WindowType_Mask
        title_bar_visible = window_type not in {
            Qt.WindowType.Popup,
            Qt.WindowType.ToolTip,
            Qt.WindowType.SplashScreen,
        }
        self.closeButton.setVisible(
            title_bar_visible
            and not self._native_macos_title_bar
            and bool(flags & Qt.WindowType.WindowCloseButtonHint)
        )
        self.setVisible(title_bar_visible)
        return title_bar_visible

    def _can_maximize(self) -> bool:
        flags = self.parent_window.windowFlags()
        return (
            self._allows_maximize
            and bool(flags & Qt.WindowType.WindowMaximizeButtonHint)
            and not self.parent_window.isFullScreen()
            and self.parent_window.minimumWidth() < self.parent_window.maximumWidth()
            and self.parent_window.minimumHeight() < self.parent_window.maximumHeight()
        )

    def _toggle_maximize(self) -> None:
        if not self._can_maximize():
            return
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if isinstance(child, QPushButton):
                super().mousePressEvent(event)
                return
            if not bool(getattr(self.parent_window, "_native_frame_enabled", False)):
                handle = self.parent_window.windowHandle()
                if handle is not None and handle.startSystemMove():
                    self._manual_move_offset = None
                    event.accept()
                    return
                if (
                    not QApplication.platformName().startswith("wayland")
                    and not self.parent_window.isMaximized()
                    and not self.parent_window.isFullScreen()
                ):
                    self._manual_move_offset = (
                        event.globalPosition().toPoint()
                        - self.parent_window.frameGeometry().topLeft()
                    )
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._manual_move_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.parent_window.move(event.globalPosition().toPoint() - self._manual_move_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._manual_move_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self._native_macos_title_bar and event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if not isinstance(child, QPushButton):
                perform_macos_title_bar_double_click(self.parent_window)
                event.accept()
                return
        if (
            self._can_maximize()
            and not bool(getattr(self.parent_window, "_native_frame_enabled", False))
            and event.button() == Qt.MouseButton.LeftButton
        ):
            child = self.childAt(event.position().toPoint())
            if not isinstance(child, QPushButton):
                self._toggle_maximize()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)
