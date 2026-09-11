"""A native QMenu with an acrylic surface and rounded backgrounds."""

from __future__ import annotations

import sys
from typing import Protocol, cast, overload

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QProxyStyle,
    QStyle,
    QStyleOptionMenuItem,
    QWidget,
)

from .theme import DEFAULT_METRICS, ModernMetrics

_FALLBACK_BASE_STYLE = "fusion"
_WINDOWS_ACRYLIC_TINT_ALPHA = 170
_ACRYLIC_INPUT_ALPHA = 1
_MENU_ITEM_EXTRA_HEIGHT = 4
_MENU_VERTICAL_MARGIN = 2
_OUTLINE_ALPHA = 30
_SEPARATOR_ALPHA = 20


class _MenuItemOption(Protocol):
    menuItemType: QStyleOptionMenuItem.MenuItemType
    palette: QPalette
    rect: QRect


def _soft_line_color(palette: QPalette, alpha: int) -> QColor:
    color = QColor(palette.color(QPalette.ColorRole.WindowText))
    color.setAlpha(alpha)
    return color


def _surface_color(palette: QPalette, widget: QWidget | None = None) -> QColor:
    color = QColor(palette.color(QPalette.ColorRole.Window))
    ancestor = widget.parentWidget() if widget is not None else None
    while color.alpha() == 0 and ancestor is not None:
        color = QColor(ancestor.palette().color(QPalette.ColorRole.Window))
        ancestor = ancestor.parentWidget()
    if color.alpha() == 0:
        color = QColor(QApplication.palette().color(QPalette.ColorRole.Window))
    return color


def _base_style_name(widget: QWidget) -> str:
    # Application style sheets wrap the base style in an anonymous QStyleSheetStyle.
    # Passing its empty name to QProxyStyle selects the platform default instead.
    return widget.style().name() or _FALLBACK_BASE_STYLE


def _supports_windows_acrylic() -> bool:
    if sys.platform != "win32" or QApplication.platformName() != "windows":
        return False
    get_windows_version = getattr(sys, "getwindowsversion", None)
    return get_windows_version is not None and get_windows_version().build >= 22000


def _enable_windows_rounded_corners(menu: QMenu, radius: int) -> bool:
    if radius <= 0 or sys.platform != "win32" or QApplication.platformName() != "windows":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        preference = ctypes.c_int(2)  # DWMWCP_ROUND
        set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        set_window_attribute.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        set_window_attribute.restype = ctypes.c_long
        return (
            set_window_attribute(
                wintypes.HWND(int(menu.winId())),
                33,  # DWMWA_WINDOW_CORNER_PREFERENCE
                ctypes.byref(preference),
                ctypes.sizeof(preference),
            )
            == 0
        )
    except (AttributeError, OSError, ValueError):
        return False


def _enable_windows_acrylic(menu: QMenu) -> bool:
    if not _supports_windows_acrylic():
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class AccentPolicy(ctypes.Structure):
            _fields_ = [
                ("state", ctypes.c_int),
                ("flags", ctypes.c_int),
                ("gradient_color", ctypes.c_uint),
                ("animation_id", ctypes.c_int),
            ]

        class WindowCompositionAttributeData(ctypes.Structure):
            _fields_ = [
                ("attribute", ctypes.c_int),
                ("data", ctypes.c_void_p),
                ("size", ctypes.c_size_t),
            ]

        tint = _surface_color(menu.palette(), menu)
        gradient_color = (
            (_WINDOWS_ACRYLIC_TINT_ALPHA << 24)
            | (tint.blue() << 16)
            | (tint.green() << 8)
            | tint.red()
        )
        accent = AccentPolicy(
            4,  # ACCENT_ENABLE_ACRYLICBLURBEHIND
            2,
            gradient_color,
            0,
        )
        data = WindowCompositionAttributeData(
            19,  # WCA_ACCENT_POLICY
            ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p),
            ctypes.sizeof(accent),
        )
        set_window_composition_attribute = ctypes.windll.user32.SetWindowCompositionAttribute
        set_window_composition_attribute.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(WindowCompositionAttributeData),
        ]
        set_window_composition_attribute.restype = wintypes.BOOL
        return bool(
            set_window_composition_attribute(
                wintypes.HWND(int(menu.winId())),
                ctypes.byref(data),
            )
        )
    except (AttributeError, OSError, ValueError):
        return False


class _RoundedMenuStyle(QProxyStyle):
    """Clip only the native selected-item rendering to a rounded rectangle."""

    def __init__(self, radius: int, base_style_name: str) -> None:
        super().__init__(base_style_name)
        self._radius = max(0, radius)
        self._native_acrylic = False

    def setNativeAcrylic(self, enabled: bool) -> None:
        self._native_acrylic = enabled

    def sizeFromContents(self, content_type, option, size, widget=None):
        result = super().sizeFromContents(content_type, option, size, widget)
        if content_type == QStyle.ContentsType.CT_MenuItem and isinstance(
            option, QStyleOptionMenuItem
        ):
            menu_option = cast(_MenuItemOption, option)
            if menu_option.menuItemType != QStyleOptionMenuItem.MenuItemType.Separator:
                result.setHeight(result.height() + _MENU_ITEM_EXTRA_HEIGHT)
        return result

    def pixelMetric(self, metric, option=None, widget=None) -> int:
        if metric == QStyle.PixelMetric.PM_MenuVMargin:
            return _MENU_VERTICAL_MARGIN
        return super().pixelMetric(metric, option, widget)

    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if element == QStyle.PrimitiveElement.PE_PanelMenu:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            surface = _surface_color(
                option.palette,
                widget if isinstance(widget, QWidget) else None,
            )
            # Fully transparent pixels in a layered Windows popup are omitted
            # from native hit testing. Keep the acrylic surface visually clear
            # while ensuring blank menu-item space still receives mouse input.
            surface.setAlpha(_ACRYLIC_INPUT_ALPHA if self._native_acrylic else 255)
            painter.setBrush(surface)
            painter.setPen(QPen(_soft_line_color(option.palette, _OUTLINE_ALPHA), 1))
            rect = QRectF(option.rect).adjusted(0.5, 0.5, -0.5, -0.5)
            painter.drawRoundedRect(rect, self._radius, self._radius)
            painter.restore()
            return
        super().drawPrimitive(element, option, painter, widget)

    def drawControl(self, element, option, painter, widget=None) -> None:
        if element == QStyle.ControlElement.CE_MenuItem and isinstance(
            option, QStyleOptionMenuItem
        ):
            menu_option = cast(_MenuItemOption, option)
        else:
            menu_option = None
        if (
            menu_option is not None
            and menu_option.menuItemType == QStyleOptionMenuItem.MenuItemType.Separator
        ):
            painter.save()
            painter.setPen(QPen(_soft_line_color(menu_option.palette, _SEPARATOR_ALPHA), 1))
            y = menu_option.rect.center().y()
            painter.drawLine(
                menu_option.rect.left() + 12,
                y,
                menu_option.rect.right() - 12,
                y,
            )
            painter.restore()
            return
        if (
            element == QStyle.ControlElement.CE_MenuItem
            and option.state & QStyle.StateFlag.State_Selected
            and self._radius > 0
        ):
            rect = QRectF(option.rect).adjusted(4, 2, -4, -2)
            window_color = _surface_color(
                option.palette,
                widget if isinstance(widget, QWidget) else None,
            )
            hover = (
                QColor(255, 255, 255, 20) if window_color.lightness() < 128 else QColor(0, 0, 0, 13)
            )
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(hover)
            painter.drawRoundedRect(rect, self._radius, self._radius)
            painter.restore()

            native_option = QStyleOptionMenuItem(option)
            native_option.state &= ~QStyle.StateFlag.State_Selected  # type: ignore[attr-defined]
            super().drawControl(element, native_option, painter, widget)
            return
        super().drawControl(element, option, painter, widget)


class ModernMenu(QMenu):
    """A native ``QMenu`` with acrylic and rounded selection geometry."""

    def __init__(
        self,
        title: str | QWidget | None = None,
        parent: QWidget | None = None,
        *,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        if isinstance(title, QWidget):
            if parent is not None:
                raise TypeError("parent specified twice")
            parent = title
            title = None
        elif title is not None and not isinstance(title, str):
            raise TypeError("title must be a string or QWidget parent")

        if title is None:
            super().__init__(parent)
        else:
            super().__init__(title, parent)

        self._metrics = metrics
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._rounded_style = _RoundedMenuStyle(metrics.control_radius, _base_style_name(self))
        self.setStyle(self._rounded_style)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        has_native_corners = _enable_windows_rounded_corners(
            self,
            self._metrics.control_radius,
        )
        self._rounded_style.setNativeAcrylic(has_native_corners and _enable_windows_acrylic(self))
        self.update()

    @overload
    def addMenu(self, menu: QMenu, /) -> QAction: ...

    @overload
    def addMenu(self, title: str, /) -> ModernMenu: ...

    @overload
    def addMenu(self, icon: QIcon | QPixmap, title: str, /) -> ModernMenu: ...

    def addMenu(self, *args):
        if len(args) == 1 and isinstance(args[0], str):
            submenu = self._create_submenu(args[0])
            super().addMenu(submenu)
            return submenu
        if len(args) == 2 and isinstance(args[0], (QIcon, QPixmap)) and isinstance(args[1], str):
            submenu = self._create_submenu(args[1])
            submenu.setIcon(QIcon(args[0]))
            super().addMenu(submenu)
            return submenu
        return super().addMenu(*args)

    def _create_submenu(self, title: str) -> ModernMenu:
        return ModernMenu(title, self, metrics=self._metrics)
