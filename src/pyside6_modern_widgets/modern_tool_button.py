"""Modern surfaces over QToolButton's native Fusion layout and interaction."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import (
    QProxyStyle,
    QStyle,
    QStyleOptionToolButton,
    QStylePainter,
    QToolButton,
    QWidget,
)

from ._theme_binding import ThemeBinding
from .theme import DEFAULT_METRICS, ModernMetrics, ModernTheme, inherited_theme


class _ToolButtonOption(QStyleOptionToolButton):
    # PySide6 6.8 stubs omit these public QStyleOption fields.
    state: QStyle.StateFlag
    palette: QPalette
    rect: QRect
    direction: Qt.LayoutDirection
    subControls: QStyle.SubControl
    activeSubControls: QStyle.SubControl


class _ToolButtonStyle(QProxyStyle):
    def __init__(self, button: ModernToolButton) -> None:
        # Never transfer ownership of the application's shared style.
        super().__init__("Fusion")
        self.setParent(button)
        self._button = button

    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if widget is self._button and element in (
            QStyle.PrimitiveElement.PE_PanelButtonTool,
            QStyle.PrimitiveElement.PE_PanelButtonCommand,
            QStyle.PrimitiveElement.PE_IndicatorButtonDropDown,
            QStyle.PrimitiveElement.PE_FrameFocusRect,
        ):
            # CC_ToolButton paints the whole rounded surface and focus outline.
            return
        super().drawPrimitive(element, option, painter, widget)

    def drawComplexControl(self, control, option, painter, widget=None) -> None:
        if control != QStyle.ComplexControl.CC_ToolButton or widget is not self._button:
            super().drawComplexControl(control, option, painter, widget)
            return
        modern = _ToolButtonOption(option)
        theme = self._button.theme()
        state = QStyle.StateFlag
        subcontrol = QStyle.SubControl
        enabled = bool(modern.state & state.State_Enabled)
        checked = bool(modern.state & state.State_On)
        hovered = enabled and bool(modern.state & state.State_MouseOver)
        pressed = enabled and bool(modern.state & state.State_Sunken)
        auto_raise = bool(modern.state & state.State_AutoRaise)
        split = bool(modern.subControls & subcontrol.SC_ToolButtonMenu)
        accent = (
            QColor(theme.accent)
            if theme.accent is not None
            else modern.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent)
        )
        foreground = QColor(theme.text)
        fill = QColor(theme.surface)
        border = QColor(theme.border)
        if checked:
            fill = border = accent
            foreground = (
                QColor(theme.on_accent)
                if theme.on_accent is not None
                else QColor("#FFFFFF" if accent.lightnessF() < 0.6 else "#202020")
            )
        if not enabled:
            fill = QColor(theme.border if checked else theme.surface_alternate)
            border = QColor(theme.border)
            foreground = QColor(theme.text_disabled)
        for group in (
            QPalette.ColorGroup.Active,
            QPalette.ColorGroup.Inactive,
            QPalette.ColorGroup.Disabled,
        ):
            modern.palette.setColor(group, QPalette.ColorRole.ButtonText, foreground)
            modern.palette.setColor(group, QPalette.ColorRole.WindowText, foreground)

        main_rect = self.subControlRect(control, modern, subcontrol.SC_ToolButton, widget)
        menu_rect = self.subControlRect(control, modern, subcontrol.SC_ToolButtonMenu, widget)
        rect = QRectF(modern.rect).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = max(
            0, min(self._button._metrics.control_radius, rect.width() / 2, rect.height() / 2)
        )
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        visible_panel = not auto_raise or checked or hovered or pressed
        if visible_panel:
            painter.setPen(QPen(border, 1))
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, radius, radius)
        if hovered or pressed:
            path = QPainterPath()
            path.addRoundedRect(rect, radius, radius)
            painter.save()
            painter.setClipPath(path, Qt.ClipOperation.IntersectClip)
            if hovered:
                painter.fillRect(modern.rect, QColor(theme.control_hover))
            if pressed:
                # Keep the split menu's pressed state out of the main action.
                pressed_rect = modern.rect
                if split:
                    pressed_rect = (
                        main_rect
                        if modern.activeSubControls & subcontrol.SC_ToolButton
                        else menu_rect
                    )
                painter.fillRect(pressed_rect, QColor(theme.control_pressed))
            painter.restore()
        if split and visible_panel:
            edge = (
                menu_rect.right() + 0.5
                if modern.direction == Qt.LayoutDirection.RightToLeft
                else menu_rect.left() - 0.5
            )
            painter.setPen(QPen(foreground if checked else border, 1))
            painter.drawLine(QPointF(edge, rect.top() + 3), QPointF(edge, rect.bottom() - 3))
        painter.restore()

        # Native painting retains all label modes, arrowType, icon modes/states,
        # QAction priority, elision, mnemonic visibility, and menu indicators.
        # Only the panel/focus primitives above are suppressed; geometry and
        # hitTestComplexControl remain entirely Fusion-owned.
        super().drawComplexControl(control, modern, painter, widget)

        if (
            enabled
            and modern.state & state.State_HasFocus
            and (modern.state & state.State_KeyboardFocusChange)
        ):
            # Derive from the actual main subcontrol so split focus mirrors in RTL.
            focus = QRectF(main_rect).adjusted(3.5, 3.5, -3.5, -3.5)
            if not focus.isEmpty():
                painter.save()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setPen(QPen(foreground if checked else accent, 1))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(focus, max(0, radius - 1), max(0, radius - 1))
                painter.restore()


class ModernToolButton(QToolButton):
    """A themed QToolButton with native Fusion sizing and input handling.

    Use the standard parent constructor and Qt keyword properties. All action,
    menu, popup-mode, auto-raise, arrow and tool-button-style APIs stay native.
    Theme/metrics affect painting only; checked buttons use the system accent.
    """

    themeChanged = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
        **kwargs,
    ) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        super().__init__(parent, **kwargs)
        self._theme_override = theme
        self._metrics = metrics
        self._modern_style = _ToolButtonStyle(self)
        self.setStyle(self._modern_style)
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
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        painter = QStylePainter(self)
        # QStyleSheetStyle routes arrow buttons through QWindowsStyle even when
        # only an unrelated ancestor has a stylesheet. Enter our painter directly
        # so that route cannot skip the modern surface and its themed palette.
        self._modern_style.drawComplexControl(
            QStyle.ComplexControl.CC_ToolButton, option, painter, self
        )
        painter.end()
