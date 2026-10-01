"""Theme-aware scroll bar using Fusion geometry and native Qt interaction."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QEnterEvent, QHideEvent, QPainter, QPen
from PySide6.QtWidgets import QProxyStyle, QScrollBar, QStyle, QStyleOptionSlider, QWidget

from ._theme_binding import ThemeBinding
from .theme import ModernTheme, inherited_theme


class _ScrollBarOption(QStyleOptionSlider):
    # PySide6 6.8 stubs omit these public QStyleOption fields.
    state: QStyle.StateFlag
    activeSubControls: QStyle.SubControl
    direction: Qt.LayoutDirection


class ModernScrollBar(QScrollBar):
    """A QScrollBar with modern painting and unchanged Qt range behavior."""

    themeChanged = Signal(object)

    def __init__(
        self,
        orientation: Qt.Orientation | QWidget = Qt.Orientation.Vertical,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
    ) -> None:
        if isinstance(orientation, QWidget):
            if parent is not None:
                raise TypeError("parent specified twice")
            parent, orientation = orientation, Qt.Orientation.Vertical
        super().__init__(orientation, parent)
        self._theme_override = theme
        # Fusion supplies the extent, slider length, subcontrol hit regions, and DPI scaling.
        style = QProxyStyle("Fusion")
        style.setParent(self)
        self.setStyle(style)
        self._hover_progress = 0.0
        self._hover_animation = QVariantAnimation(self)
        self._hover_animation.setDuration(120)
        self._hover_animation.valueChanged.connect(self._set_hover_progress)
        self._theme_binding = ThemeBinding(self, self.theme, self.update)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def _set_hover_progress(self, value: float) -> None:
        self._hover_progress = float(value)
        self.update()

    def _animate_hover(self, target: float) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(target)
        self._hover_animation.start()

    def enterEvent(self, event: QEnterEvent) -> None:
        super().enterEvent(event)
        self._animate_hover(1.0)

    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        self._animate_hover(0.0)

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)
        self._hover_animation.stop()
        self._set_hover_progress(0.0)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def paintEvent(self, event) -> None:
        option = _ScrollBarOption()
        self.initStyleOption(option)
        style = self.style()
        control = QStyle.ComplexControl.CC_ScrollBar
        part = QStyle.SubControl
        state = QStyle.StateFlag
        theme = self.theme()
        enabled = bool(option.state & state.State_Enabled)
        active = option.activeSubControls
        hovered = bool(option.state & state.State_MouseOver)
        pressed = bool(option.state & state.State_Sunken)
        horizontal = self.orientation() == Qt.Orientation.Horizontal

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        thumb_center: QPointF | None = None
        if self.maximum() > self.minimum():
            handle = style.subControlRect(control, option, part.SC_ScrollBarSlider, self)
            if handle.isValid():
                color = QColor(
                    theme.text_disabled
                    if not enabled
                    else theme.scrollbar_hover
                    if self._hover_progress > 0.5
                    else theme.scrollbar
                )
                if pressed and active == part.SC_ScrollBarSlider:
                    color = color.darker(115)
                hover_progress = self._hover_progress if enabled else 0.0
                bounds = QRectF(handle)
                extent = bounds.height() if horizontal else bounds.width()
                thin = min(3.0, max(1.0, extent - 4.0))
                expanded = min(8.0, max(thin, extent - 4.0))
                thickness = thin + (expanded - thin) * hover_progress
                if horizontal:
                    rect = QRectF(
                        bounds.left() + 2,
                        bounds.bottom() - 2 - thickness,
                        max(1.0, bounds.width() - 4),
                        thickness,
                    )
                else:
                    x = (
                        bounds.left() + 2
                        if option.direction == Qt.LayoutDirection.RightToLeft
                        else bounds.right() - 2 - thickness
                    )
                    rect = QRectF(x, bounds.top() + 2, thickness, max(1.0, bounds.height() - 4))
                painter.setBrush(color)
                painter.drawRoundedRect(
                    rect, min(rect.width(), rect.height()) / 2, min(rect.width(), rect.height()) / 2
                )
                thumb_center = rect.center()

        if not enabled or self.maximum() == self.minimum() or self._hover_progress <= 0:
            return
        for subcontrol, forward in (
            (part.SC_ScrollBarSubLine, False),
            (part.SC_ScrollBarAddLine, True),
        ):
            button_rect = style.subControlRect(control, option, subcontrol, self)
            if not button_rect.isValid():
                continue
            color = QColor(
                theme.scrollbar_hover if hovered and active == subcontrol else theme.text_muted
            )
            if pressed and active == subcontrol:
                color = color.darker(115)
            color.setAlphaF(self._hover_progress)
            painter.setPen(
                QPen(
                    color,
                    1.5,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            center = QRectF(button_rect).center()
            if thumb_center is not None:
                center = (
                    QPointF(center.x(), thumb_center.y())
                    if horizontal
                    else QPointF(thumb_center.x(), center.y())
                )
            direction = 1 if forward else -1
            if horizontal:
                if option.direction == Qt.LayoutDirection.RightToLeft:
                    direction *= -1
                points = (
                    QPointF(center.x() - direction * 2, center.y() - 3),
                    QPointF(center.x() + direction * 1, center.y()),
                    QPointF(center.x() - direction * 2, center.y() + 3),
                )
            else:
                points = (
                    QPointF(center.x() - 3, center.y() - direction * 2),
                    QPointF(center.x(), center.y() + direction * 1),
                    QPointF(center.x() + 3, center.y() - direction * 2),
                )
            painter.drawPolyline(points)
