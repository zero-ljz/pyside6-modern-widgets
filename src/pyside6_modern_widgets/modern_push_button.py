"""Modern QPushButton painting with Fusion geometry and native interaction."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import QPushButton, QStyle, QStyleFactory, QStyleOptionButton

from ._theme_binding import ThemeBinding
from .theme import DEFAULT_METRICS, ModernMetrics, ModernTheme, inherited_theme


class _ButtonOption(QStyleOptionButton):
    # PySide6 6.8 stubs omit these public QStyleOption fields.
    state: QStyle.StateFlag
    features: QStyleOptionButton.ButtonFeature
    palette: QPalette
    rect: QRect
    direction: Qt.LayoutDirection


class ModernPushButton(QPushButton):
    """A QPushButton with rounded surfaces and native Fusion sizing.

    All QPushButton constructor forms and keyword properties are forwarded to Qt,
    including ``(parent)``, ``(text, parent)`` and ``(icon, text, parent)``.
    Checked and default buttons use the theme/system accent. Qt owns all input,
    signals, shortcuts, menu activation, auto-repeat and dialog default behavior.
    Dimensions are logical pixels; Qt handles display scaling and icon DPR.
    """

    themeChanged = Signal(object)

    def __init__(
        self,
        *args,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
        **kwargs,
    ) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        super().__init__(*args, **kwargs)
        self._theme_override = theme
        self._metrics = metrics
        # Own a separate style, never transfer ownership of QApplication.style().
        # Keep native size hints, content rectangles, mnemonics and icon layout.
        self._fusion_style = QStyleFactory.create("Fusion")
        self._fusion_style.setParent(self)
        self.setStyle(self._fusion_style)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._theme_binding = ThemeBinding(self, self.theme, self.update)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override locally; None restores ancestor/global theme inheritance."""
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def paintEvent(self, event) -> None:
        option = _ButtonOption()
        self.initStyleOption(option)
        theme = self.theme()
        state = QStyle.StateFlag
        feature = QStyleOptionButton.ButtonFeature
        enabled = bool(option.state & state.State_Enabled)
        pressed = bool(option.state & state.State_Sunken)
        hovered = bool(option.state & state.State_MouseOver)
        accented = bool(option.state & state.State_On or option.features & feature.DefaultButton)
        flat = bool(option.features & feature.Flat)
        accent = (
            QColor(theme.accent)
            if theme.accent is not None
            else option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent)
        )
        foreground = QColor(theme.text)
        fill = QColor(theme.surface)
        border = QColor(theme.border)
        if accented:
            fill = border = accent
            foreground = (
                QColor(theme.on_accent)
                if theme.on_accent is not None
                else QColor("#FFFFFF" if accent.lightnessF() < 0.6 else "#202020")
            )
        if not enabled:
            fill = QColor(theme.border if accented else theme.surface_alternate)
            border = QColor(theme.border)
            foreground = QColor(theme.text_disabled)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(option.rect).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = max(0, min(self._metrics.control_radius, rect.height() / 2, rect.width() / 2))
        if not flat or accented or pressed:
            painter.setPen(QPen(border, 1))
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, radius, radius)
        if enabled and (pressed or hovered):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.control_pressed if pressed else theme.control_hover))
            painter.drawRoundedRect(rect, radius, radius)

        # Delegate the complete label to Qt: icon modes/states, iconSize, mnemonic
        # visibility, RTL, and the menu-indicator space stay native.
        for group in (
            QPalette.ColorGroup.Active,
            QPalette.ColorGroup.Inactive,
            QPalette.ColorGroup.Disabled,
        ):
            option.palette.setColor(group, QPalette.ColorRole.ButtonText, foreground)
        label = _ButtonOption(option)
        label.rect = self.style().subElementRect(
            QStyle.SubElement.SE_PushButtonContents, option, self
        )
        self.style().drawControl(QStyle.ControlElement.CE_PushButtonLabel, label, painter, self)

        if option.features & feature.HasMenu:
            # QCommonStyle's push-button menu indicator rectangle (also used by
            # Fusion); only the glyph changes. QPushButton still opens the menu.
            mbi = self.style().pixelMetric(QStyle.PixelMetric.PM_MenuButtonIndicator, option, self)
            arrow = QRect(
                option.rect.right() - mbi - 2,
                option.rect.height() // 2 - mbi // 2 + 3,
                mbi - 6,
                mbi - 6,
            )
            arrow = QStyle.visualRect(option.direction, option.rect, arrow)
            center = QRectF(arrow).center()
            half_width = max(0, (arrow.width() - 1) / 2)
            painter.setPen(
                QPen(
                    foreground,
                    1.2,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.drawLine(center + QPointF(-half_width, -1), center + QPointF(0, 1.5))
            painter.drawLine(center + QPointF(0, 1.5), center + QPointF(half_width, -1))

        if (
            enabled
            and option.state & state.State_HasFocus
            and (option.state & state.State_KeyboardFocusChange)
        ):
            focus_rect = QRectF(
                self.style().subElementRect(QStyle.SubElement.SE_PushButtonFocusRect, option, self)
            ).adjusted(0.5, 0.5, -0.5, -0.5)
            painter.setPen(QPen(foreground if accented else accent, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(focus_rect, max(0, radius - 1), max(0, radius - 1))
        painter.end()
