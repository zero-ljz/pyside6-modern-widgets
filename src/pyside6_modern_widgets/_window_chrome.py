"""Shared visual building blocks for modern top-level widgets."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QRect, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
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
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

from ._windows_window import HTTRANSPARENT, WM_NCHITTEST, read_message
from .theme import ModernMetrics, ModernTheme, palette_for_theme

WindowWidget = TypeVar("WindowWidget", bound=QWidget)


def uses_windows_window_state() -> bool:
    return sys.platform == "win32" and QApplication.platformName() == "windows"


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
        if not self.native_corners or widget.windowHandle() is None:
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
                wintypes.HWND(int(widget.winId())),
                33,  # DWMWA_WINDOW_CORNER_PREFERENCE
                ctypes.byref(preference),
                ctypes.sizeof(preference),
            )
        except (AttributeError, OSError):
            return


def current_window_surface_policy() -> WindowSurfacePolicy:
    native_windows = uses_windows_window_state()
    get_windows_version = getattr(sys, "getwindowsversion", None)
    native_corners = (
        native_windows and get_windows_version is not None and get_windows_version().build >= 22000
    )
    return WindowSurfacePolicy(
        opaque_surface=native_windows,
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
    ) -> None:
        super().__init__(parent)
        self.parent_window: WindowWidget = parent
        self._theme = theme
        self._metrics = metrics
        self._allows_maximize = allows_maximize
        self._title_alignment: Literal["left", "center"] = "left"
        self._title_visible = True
        self._icon_visible = True
        self._has_icon = False
        self._manual_move_offset: QPoint | None = None
        self.setObjectName("CustomTitleBar")
        self.setAutoFillBackground(False)
        self._init_ui()

    def _init_ui(self) -> None:
        vertical_padding = 2
        title_bar_height = max(
            self._metrics.title_bar_height,
            self._metrics.title_button_size + vertical_padding * 2,
        )
        self.setFixedHeight(title_bar_height)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, vertical_padding, 5, vertical_padding)
        self.main_layout.setSpacing(5)

        self.iconLabel = QLabel(self)
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

        self.closeButton = QPushButton("✕", self)
        self.closeButton.setToolTip("关闭")
        self.closeButton.setFixedSize(
            self._metrics.title_button_size,
            self._metrics.title_button_size,
        )
        self.closeButton.clicked.connect(self.parent_window.close)
        self.main_layout.addWidget(self.closeButton)
        WindowTitleBar.setTheme(self, self._theme)

    def event(self, event) -> bool:
        handled = super().event(event)
        if event.type() in (QEvent.Type.LayoutRequest, QEvent.Type.Resize) and hasattr(
            self, "_title_spacer"
        ):
            self.main_layout.activate()
            self._layout_title()
        return handled

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
        self.titleLabel.setGeometry(left, available.top(), width, available.height())

    def setTheme(self, theme: ModernTheme) -> None:
        self._theme = theme
        self.setPalette(palette_for_theme(theme, self.palette()))
        title_font = self.titleLabel.font()
        title_font.setPointSizeF(max(title_font.pointSizeF(), 10.5))
        self.titleLabel.setFont(title_font)
        self._layout_title()
        self.closeButton.setStyleSheet(
            button_style(theme, self._metrics)
            + f"QPushButton {{ color: {theme.text}; font-size: 18px; }}"
            + f"QPushButton:hover {{ color: {theme.danger}; }}"
        )

    def setInactiveTitleColor(self, color: QColor) -> None:
        palette = QPalette()
        palette.setColor(
            QPalette.ColorGroup.Inactive,
            QPalette.ColorRole.WindowText,
            color,
        )
        self.titleLabel.setPalette(palette)

    def setIcon(self, icon: QIcon) -> None:
        self._has_icon = not icon.isNull()
        self.iconLabel.setVisible(self._icon_visible and self._has_icon)
        if self._has_icon:
            self.iconLabel.setPixmap(icon.pixmap(20, 20))
        else:
            self.iconLabel.clear()
        self._layout_title()

    def addCustomWidget(self, widget: QWidget, align: str = "right") -> None:
        """Insert a vertically centered widget in the left or right control area."""
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
        self.iconLabel.setVisible(visible and self._has_icon)
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
            title_bar_visible and bool(flags & Qt.WindowType.WindowCloseButtonHint)
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
