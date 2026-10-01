"""A themed line edit with Fusion geometry and native text interaction."""

from __future__ import annotations

from typing import cast

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QLineEdit, QProxyStyle, QStyle, QStyleOptionFrame, QWidget

from ._theme_binding import ThemeBinding
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    inherited_theme,
    palette_for_theme,
)

_CONTROL_FILLS_LIGHT = ("#B3FFFFFF", "#80F9F9F9", "#4DF9F9F9")
_CONTROL_FILLS_DARK = ("#0FFFFFFF", "#15FFFFFF", "#08FFFFFF")


def _draw_focus_underline(
    painter: QPainter, rect: QRect, radius: float, accent: QColor, scale: float
) -> None:
    scale = max(1.0, scale)
    width = round(rect.width() * scale)
    height = round(rect.height() * scale)
    inset = round(max(0.0, radius - 1.5) * scale)
    thickness = max(2, round(1.5 * scale))
    taper = thickness + 1
    left = round(rect.x() * scale) + inset
    top = round(rect.y() * scale) + height - thickness
    right = left + max(0, width - 2 * inset)
    bottom = top + thickness
    path = QPainterPath(QPointF((left - 1) / scale, top / scale))
    path.lineTo(QPointF((right + 1) / scale, top / scale))
    path.lineTo(QPointF((right - taper) / scale, bottom / scale))
    path.lineTo(QPointF((left + taper) / scale, bottom / scale))
    path.closeSubpath()
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(accent)
    painter.drawPath(path)
    painter.restore()


class _LineEditOption(QStyleOptionFrame):
    # PySide6 6.8 stubs omit these public QStyleOption fields.
    lineWidth: int
    state: QStyle.StateFlag
    palette: QPalette
    rect: QRect


class _LineEditStyle(QProxyStyle):
    def __init__(self, editor: ModernLineEdit) -> None:
        super().__init__("Fusion")
        self.setParent(editor)
        self._editor = editor

    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if (
            element != QStyle.PrimitiveElement.PE_PanelLineEdit
            or widget is not self._editor
            or not isinstance(option, QStyleOptionFrame)
            or not cast(_LineEditOption, option).lineWidth
        ):
            super().drawPrimitive(element, option, painter, widget)
            return

        option = cast(_LineEditOption, option)
        editor = self._editor
        theme = editor.theme()
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        focused = enabled and bool(option.state & QStyle.StateFlag.State_HasFocus)
        fills = (
            _CONTROL_FILLS_DARK if QColor(theme.surface).lightness() < 128 else _CONTROL_FILLS_LIGHT
        )
        fill_index = (
            2 if not enabled or editor.isReadOnly() else 1 if hovered and not focused else 0
        )
        surface = QBrush(QColor(fills[fill_index]))
        if editor._palette_override.isBrushSet(
            option.palette.currentColorGroup(), QPalette.ColorRole.Base
        ):
            surface = option.palette.brush(QPalette.ColorRole.Base)
        border = option.palette.color(QPalette.ColorRole.Mid)
        rect = QRectF(option.rect).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = min(editor._metrics.control_radius, rect.width() / 2, rect.height() / 2)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(border, 1))
        painter.setBrush(surface)
        painter.drawRoundedRect(rect, radius, radius)
        if focused:
            accent = (
                QColor(theme.accent)
                if theme.accent is not None
                else option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent)
            )
            _draw_focus_underline(painter, option.rect, radius, accent, editor.devicePixelRatioF())
        painter.restore()


class ModernLineEdit(QLineEdit):
    """QLineEdit text editing and signals with a theme-aware surface."""

    themeChanged = Signal(object)

    def __init__(
        self,
        text: str | QWidget | None = "",
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        if isinstance(text, QWidget):
            if parent is not None:
                raise TypeError("parent specified twice")
            parent, text = text, ""
        elif text is None:
            text = ""
        super().__init__(text, parent)
        self._theme_override = theme
        self._metrics = metrics
        self._palette_override = QPalette()
        self._applying_theme = False
        self._styled_theme: ModernTheme | None = None
        self._modern_style = _LineEditStyle(self)
        self.setStyle(self._modern_style)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._apply_theme()
        self._theme_binding = ThemeBinding(self, self.theme, self._apply_theme)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override locally; None restores owner/ancestor/global inheritance."""
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def setPalette(self, palette: QPalette | Qt.GlobalColor | QColor) -> None:
        if not hasattr(self, "_palette_override"):
            super().setPalette(palette)
            return
        self._palette_override = QPalette(palette)
        self._apply_theme()

    def _themed_palette(self, theme: ModernTheme) -> QPalette:
        themed = palette_for_theme(theme, self.palette())
        palette = self._palette_override.resolve(themed)
        palette.setResolveMask(self._palette_override.resolveMask() | themed.resolveMask())
        return palette

    def _apply_theme(self) -> None:
        if self._applying_theme:
            return
        self._applying_theme = True
        try:
            self._styled_theme = self.theme()
            super().setPalette(self._themed_palette(self._styled_theme))
            self.update()
        finally:
            self._applying_theme = False

    def event(self, event: QEvent) -> bool:
        handled = super().event(event)
        if (
            event.type() == QEvent.Type.PaletteChange
            and getattr(self, "_styled_theme", None) is not None
            and not self._applying_theme
            and self.palette() != self._themed_palette(self.theme())
        ):
            self._apply_theme()
        if event.type() in (QEvent.Type.Enter, QEvent.Type.Leave):
            self.update()
        return handled
