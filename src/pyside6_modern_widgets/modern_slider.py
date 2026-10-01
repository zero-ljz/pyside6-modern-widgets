"""A compact, theme-aware slider with native Qt range semantics."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFocusEvent, QMouseEvent, QPainter, QPalette, QPen
from PySide6.QtWidgets import QSizePolicy, QSlider, QWidget

from ._theme_binding import ThemeBinding
from .theme import ModernTheme, inherited_theme


class ModernSlider(QSlider):
    """A QSlider with a compact track, accent fill, and keyboard focus ring."""

    themeChanged = Signal(object)

    def __init__(
        self,
        orientation: Qt.Orientation | QWidget = Qt.Orientation.Horizontal,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
    ) -> None:
        if isinstance(orientation, QWidget):
            if parent is not None:
                raise TypeError("parent specified twice")
            parent, orientation = orientation, Qt.Orientation.Horizontal
        super().__init__(orientation, parent)
        self._theme_override = theme
        self._keyboard_focus = False
        self._hovered = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._update_size_policy()
        self._theme_binding = ThemeBinding(self, self.theme, self.update)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override locally; None restores owner/ancestor/global inheritance."""
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def setOrientation(self, orientation: Qt.Orientation) -> None:
        super().setOrientation(orientation)
        self._update_size_policy()

    def _update_size_policy(self) -> None:
        if self.orientation() == Qt.Orientation.Horizontal:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def sizeHint(self) -> QSize:
        return QSize(84, 20) if self.orientation() == Qt.Orientation.Horizontal else QSize(20, 84)

    def minimumSizeHint(self) -> QSize:
        return QSize(22, 20) if self.orientation() == Qt.Orientation.Horizontal else QSize(20, 22)

    def _upside_down(self) -> bool:
        reversed_direction = self.orientation() == Qt.Orientation.Vertical or (
            self.layoutDirection() == Qt.LayoutDirection.RightToLeft
        )
        return reversed_direction != self.invertedAppearance()

    def _axis_bounds(self) -> tuple[float, float]:
        extent = self.width() if self.orientation() == Qt.Orientation.Horizontal else self.height()
        return 11.0, max(11.0, extent - 11.0)

    def _position_for_value(self, value: int) -> float:
        start, end = self._axis_bounds()
        span = self.maximum() - self.minimum()
        fraction = (value - self.minimum()) / span if span else 0.0
        return start + (1.0 - fraction if self._upside_down() else fraction) * (end - start)

    def _value_at(self, position: QPointF) -> int:
        start, end = self._axis_bounds()
        coordinate = (
            position.x() if self.orientation() == Qt.Orientation.Horizontal else position.y()
        )
        fraction = max(0.0, min(1.0, (coordinate - start) / max(1.0, end - start)))
        if self._upside_down():
            fraction = 1.0 - fraction
        return self.minimum() + round(fraction * (self.maximum() - self.minimum()))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self.minimum() == self.maximum():
            event.ignore()
            return
        self._keyboard_focus = False
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.setSliderDown(True)
        self.setSliderPosition(self._value_at(event.position()))
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._hovered = self.rect().contains(event.position().toPoint())
        if self.isSliderDown():
            self.setSliderPosition(self._value_at(event.position()))
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isSliderDown():
            self.setSliderPosition(self._value_at(event.position()))
            self.setSliderDown(False)
            self.update()
            event.accept()
        else:
            event.ignore()

    def event(self, event: QEvent) -> bool:
        if hasattr(self, "_keyboard_focus"):
            if event.type() == QEvent.Type.FocusIn and isinstance(event, QFocusEvent):
                self._keyboard_focus = event.reason() in (
                    Qt.FocusReason.TabFocusReason,
                    Qt.FocusReason.BacktabFocusReason,
                    Qt.FocusReason.ShortcutFocusReason,
                )
            elif event.type() == QEvent.Type.KeyPress:
                self._keyboard_focus = True
                self.update()
            elif event.type() == QEvent.Type.Leave:
                self._hovered = False
            elif event.type() == QEvent.Type.OrientationChange:
                self._update_size_policy()
                self.updateGeometry()
            if event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut, QEvent.Type.Leave):
                self.update()
        return super().event(event)

    def paintEvent(self, event: QEvent) -> None:
        theme = self.theme()
        enabled = self.isEnabled() and self.minimum() < self.maximum()
        accent = (
            QColor(theme.accent)
            if theme.accent
            else self.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent)
        )
        start, end = self._axis_bounds()
        position = self._position_for_value(self.sliderPosition())
        horizontal = self.orientation() == Qt.Orientation.Horizontal
        cross = self.height() / 2 if horizontal else self.width() / 2
        track = (
            QRectF(start, cross - 2, end - start, 4)
            if horizontal
            else QRectF(cross - 2, start, 4, end - start)
        )
        minimum_position = end if self._upside_down() else start
        fill = (
            QRectF(min(minimum_position, position), cross - 2, abs(position - minimum_position), 4)
            if horizontal
            else QRectF(
                cross - 2, min(minimum_position, position), 4, abs(position - minimum_position)
            )
        )
        center = QPointF(position, cross) if horizontal else QPointF(cross, position)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.border if enabled else theme.surface_alternate))
        painter.drawRoundedRect(track, 2, 2)
        if enabled and not fill.isEmpty():
            painter.setBrush(accent)
            painter.drawRoundedRect(fill, 2, 2)

        radius = 7 if self.isSliderDown() else (8 if self._hovered and enabled else 7.5)
        painter.setPen(QPen(QColor(theme.border), 1))
        painter.setBrush(QColor(theme.surface if enabled else theme.surface_alternate))
        painter.drawEllipse(center, radius, radius)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent if enabled else QColor(theme.text_disabled))
        painter.drawEllipse(center, 3.5, 3.5)
        if enabled and self.hasFocus() and self._keyboard_focus:
            painter.setPen(QPen(accent, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, 9, 9)
        painter.end()
