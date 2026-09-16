"""Anchored, light-dismiss popups for arbitrary Qt widgets."""

from __future__ import annotations

import weakref
from enum import Enum

from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QApplication, QFrame, QScrollArea, QVBoxLayout, QWidget
from shiboken6 import isValid

from .modern_menu import (
    _enable_windows_acrylic,
    _enable_windows_rounded_corners,
    _soft_line_color,
    _surface_color,
)
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    inherited_theme,
    palette_for_theme,
    theme_manager,
)


class FlyoutPlacement(str, Enum):
    """Preferred side of an anchor; the opposite side is tried if needed."""

    BOTTOM = "bottom"
    TOP = "top"
    LEFT = "left"
    RIGHT = "right"


def _popup_geometry(
    anchor: QRect, size: QSize, available: QRect, placement: FlyoutPlacement, gap: int, rtl: bool
) -> QRect:
    """Choose a side, then clamp within the screen's logical available geometry."""
    x = anchor.right() - size.width() + 1 if rtl else anchor.left()
    y = anchor.center().y() - size.height() // 2
    candidates = {
        FlyoutPlacement.BOTTOM: QRect(QPoint(x, anchor.bottom() + 1 + gap), size),
        FlyoutPlacement.TOP: QRect(QPoint(x, anchor.top() - gap - size.height()), size),
        FlyoutPlacement.LEFT: QRect(QPoint(anchor.left() - gap - size.width(), y), size),
        FlyoutPlacement.RIGHT: QRect(QPoint(anchor.right() + 1 + gap, y), size),
    }
    opposite = {
        FlyoutPlacement.BOTTOM: FlyoutPlacement.TOP,
        FlyoutPlacement.TOP: FlyoutPlacement.BOTTOM,
        FlyoutPlacement.LEFT: FlyoutPlacement.RIGHT,
        FlyoutPlacement.RIGHT: FlyoutPlacement.LEFT,
    }
    order = [placement, opposite[placement]]
    order.extend(side for side in FlyoutPlacement if side not in order)
    rectangles = [candidates[side] for side in order]
    # Cross-axis clamping should not needlessly move a bottom popup to the top.
    for side, rect in zip(order, rectangles):
        if side in (FlyoutPlacement.TOP, FlyoutPlacement.BOTTOM):
            rect.moveLeft(
                max(available.left(), min(rect.left(), available.right() - size.width() + 1))
            )
        else:
            rect.moveTop(
                max(available.top(), min(rect.top(), available.bottom() - size.height() + 1))
            )
    result = next((rect for rect in rectangles if available.contains(rect)), None)
    if result is None:

        def visible_area(rect: QRect) -> int:
            intersection = rect.intersected(available)
            return intersection.width() * intersection.height()

        result = max(rectangles, key=visible_area)
    result.moveLeft(max(available.left(), min(result.left(), available.right() - size.width() + 1)))
    result.moveTop(max(available.top(), min(result.top(), available.bottom() - size.height() + 1)))
    return result


class ModernFlyout(QWidget):
    """A reusable Qt.Popup containing a widget installed with setContentWidget().

    popup(anchor) opens without blocking. Outside clicks and Escape dismiss it;
    child menus and combo popups retain their own input handling. Oversized
    content scrolls inside the screen bounds. Closing hides rather than deletes
    the panel by default, so values survive subsequent opens.
    """

    opened = Signal()
    closed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self._theme_override = theme
        self._metrics = metrics
        self._native_acrylic = False
        self._applying_theme = False
        self._anchor: weakref.ReferenceType[QWidget] | None = None
        self._anchor_chain: list[QWidget] = []
        self._placement = FlyoutPlacement.BOTTOM
        self._gap = 8
        self._position_timer = QTimer(self)
        self._position_timer.setSingleShot(True)
        self._position_timer.timeout.connect(self._reposition)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_WindowPropagation)
        self.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._scroll = QScrollArea(self)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setAutoFillBackground(False)
        self._scroll.viewport().setAutoFillBackground(False)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self._scroll)
        theme_manager().themeChanged.connect(self._on_theme_changed)
        self._apply_theme()

    def contentWidget(self) -> QWidget | None:
        return self._scroll.widget()

    def setContentWidget(self, widget: QWidget) -> None:
        """Take ownership of widget, deleting any previous content like QScrollArea."""
        if widget is self.contentWidget():
            return
        if widget is self or widget.isAncestorOf(self) or widget is self._scroll:
            raise ValueError("content must not contain the flyout")
        auto_fill = widget.autoFillBackground()
        self._scroll.setWidget(widget)
        # QScrollArea forces a solid background; preserve the content's choice
        # so ordinary transparent containers do not cover the acrylic surface.
        widget.setAutoFillBackground(auto_fill)
        self.updateGeometry()
        if self.isVisible():
            self._position_timer.start(0)

    def takeContentWidget(self) -> QWidget | None:
        """Remove the content and transfer ownership back to the caller."""
        widget = self._scroll.takeWidget()
        self.updateGeometry()
        if self.isVisible():
            self._position_timer.start(0)
        return widget

    def anchorWidget(self) -> QWidget | None:
        anchor = self._anchor() if self._anchor is not None else None
        return anchor if anchor is not None and isValid(anchor) else None

    def theme(self) -> ModernTheme:
        if self._theme_override is not None:
            return self._theme_override
        anchor = self.anchorWidget()
        if anchor is not None:
            get_theme = getattr(anchor, "theme", None)
            if callable(get_theme):
                theme = get_theme()
                if isinstance(theme, ModernTheme):
                    return theme
            return inherited_theme(anchor)
        return inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override colors, or pass None to follow the anchor's theme."""
        self._theme_override = theme
        self._apply_theme()

    def _on_theme_changed(self, _theme: ModernTheme) -> None:
        self._apply_theme()

    def _apply_theme(self) -> None:
        if self._applying_theme:
            return
        self._applying_theme = True
        try:
            anchor = self.anchorWidget()
            base = anchor.palette() if anchor is not None else self.palette()
            palette = palette_for_theme(self.theme(), base)
            if palette != self.palette():
                self.setPalette(palette)
            self.update()
        finally:
            self._applying_theme = False

    def sizeHint(self) -> QSize:
        if not hasattr(self, "_scroll"):
            return super().sizeHint()
        content = self.contentWidget()
        if content is None:
            return QSize(160, 80)
        size = content.sizeHint().expandedTo(content.minimumSizeHint())
        if not size.isValid():
            size = content.size()
        size = size.expandedTo(content.minimumSize()).boundedTo(content.maximumSize())
        margins = self.contentsMargins()
        layout = self.layout()
        if layout is not None:
            margins += layout.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def popup(
        self,
        anchor: QWidget,
        placement: FlyoutPlacement | str = FlyoutPlacement.BOTTOM,
        *,
        gap: int = 8,
    ) -> None:
        """Open beside a visible anchor; top/bottom align to its leading edge.

        Geometry uses logical pixels and the anchor screen's available area.
        Moving the anchor repositions the popup; hiding or reparenting an anchor
        or its ancestors dismisses it. Negative gaps are rejected.
        """
        placement = FlyoutPlacement(placement)
        if gap < 0:
            raise ValueError("gap must be non-negative")
        if anchor is self or self.isAncestorOf(anchor) or not anchor.isVisible():
            raise ValueError("anchor must be a visible widget outside the flyout")
        if self.isVisible():
            self.hide()
        self._anchor = weakref.ref(anchor)
        self._placement, self._gap = placement, gap
        ancestor: QWidget | None = anchor
        while ancestor is not None:
            self._anchor_chain.append(ancestor)
            ancestor = ancestor.parentWidget()
        anchor.destroyed.connect(self._anchor_destroyed)
        self.setLayoutDirection(anchor.layoutDirection())
        self._apply_theme()
        self.ensurePolished()
        content = self.contentWidget()
        if content is not None:
            content.ensurePolished()
        self._reposition()
        self.show()
        self.setFocus(Qt.FocusReason.PopupFocusReason)
        self.focusNextChild()

    def _reposition(self) -> None:
        anchor = self.anchorWidget()
        if anchor is None:
            return
        rect = QRect(anchor.mapToGlobal(QPoint()), anchor.size())
        screen = QApplication.screenAt(rect.center()) or anchor.screen()
        if screen is None:
            return
        available = screen.availableGeometry().adjusted(8, 8, -8, -8)
        size = self.sizeHint().expandedTo(self.minimumSizeHint()).expandedTo(self.minimumSize())
        limit = self.maximumSize().boundedTo(available.size())
        # Reserve space for scrollbars so a tall form does not acquire an
        # unnecessary horizontal scrollbar when the vertical bar appears.
        if size.height() > limit.height():
            size.setWidth(size.width() + self._scroll.verticalScrollBar().sizeHint().width())
        if size.width() > limit.width():
            size.setHeight(size.height() + self._scroll.horizontalScrollBar().sizeHint().height())
        size = size.boundedTo(limit)
        geometry = _popup_geometry(
            rect,
            size,
            available,
            self._placement,
            self._gap,
            self.layoutDirection() == Qt.LayoutDirection.RightToLeft,
        )
        if geometry != self.geometry():
            self.setGeometry(geometry)

    def _anchor_destroyed(self) -> None:
        self._anchor = None
        self.close()

    def eventFilter(self, watched, event) -> bool:
        event_type = event.type()
        if watched in self._anchor_chain:
            if event_type in (QEvent.Type.Hide, QEvent.Type.ParentChange):
                self.close()
            elif event_type in (QEvent.Type.Move, QEvent.Type.Resize):
                self._position_timer.start(0)
            elif event_type == QEvent.Type.LayoutDirectionChange:
                anchor = self.anchorWidget()
                if anchor is not None:
                    self.setLayoutDirection(anchor.layoutDirection())
                    self._position_timer.start(0)
            elif event_type == QEvent.Type.PaletteChange:
                self._apply_theme()
        if (
            watched is self.contentWidget() or watched is self._scroll
        ) and event_type == QEvent.Type.LayoutRequest:
            self._position_timer.start(0)
        if (
            event_type == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Escape
            and QApplication.activePopupWidget() is self
        ):
            self.close()
            return True
        return super().eventFilter(watched, event)

    def _refresh_surface(self) -> None:
        self._native_acrylic = _enable_windows_rounded_corners(
            self, self._metrics.corner_radius
        ) and _enable_windows_acrylic(self)
        self.update()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if (
            hasattr(self, "_metrics")
            and self.isVisible()
            and event.type() == QEvent.Type.PaletteChange
        ):
            self._refresh_surface()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self._refresh_surface()
        self.opened.emit()

    def hideEvent(self, event) -> None:
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._position_timer.stop()
        anchor = self.anchorWidget()
        if anchor is not None and self._anchor_chain:
            anchor.destroyed.disconnect(self._anchor_destroyed)
        self._anchor_chain.clear()
        super().hideEvent(event)
        self.closed.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        surface = _surface_color(self.palette(), self)
        # Alpha 1 keeps the transparent Windows surface in native hit testing.
        surface.setAlpha(1 if self._native_acrylic else 255)
        painter.setBrush(surface)
        painter.setPen(QPen(_soft_line_color(self.palette(), 30), 1))
        radius = self._metrics.corner_radius
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
