"""Fusion-sized check and radio controls with themed indicators."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QRadioButton,
    QStyle,
    QStyleFactory,
    QStyleOptionButton,
)

from ._theme_binding import ThemeBinding
from .theme import ModernTheme, inherited_theme


class _ChoiceOption(QStyleOptionButton):
    # PySide6 6.8 stubs omit these public QStyleOption fields.
    state: QStyle.StateFlag
    palette: QPalette
    rect: QRect


def _paint_choice(
    button: QAbstractButton, option: _ChoiceOption, theme: ModernTheme, *, radio: bool
) -> None:
    style = button.style()
    state = QStyle.StateFlag
    enabled = bool(option.state & state.State_Enabled)
    hovered = bool(option.state & state.State_MouseOver)
    pressed = bool(option.state & state.State_Sunken)
    partial = (
        isinstance(button, QCheckBox) and button.checkState() == Qt.CheckState.PartiallyChecked
    )
    selected = button.isChecked() or partial
    accent = (
        QColor(theme.accent)
        if theme.accent is not None
        else option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent)
    )
    on_accent = (
        QColor(theme.on_accent)
        if theme.on_accent is not None
        else QColor("#FFFFFF" if accent.lightnessF() < 0.6 else "#202020")
    )
    fill = accent if selected else QColor(theme.surface)
    border = accent if selected or hovered else QColor(theme.text_muted)
    mark = on_accent
    if not enabled:
        fill = QColor(theme.border if selected else theme.surface_alternate)
        border = QColor(theme.border)
        mark = QColor(theme.text_disabled)

    indicator_element = (
        QStyle.SubElement.SE_RadioButtonIndicator
        if radio
        else QStyle.SubElement.SE_CheckBoxIndicator
    )
    label_element = (
        QStyle.ControlElement.CE_RadioButtonLabel
        if radio
        else QStyle.ControlElement.CE_CheckBoxLabel
    )
    contents_element = (
        QStyle.SubElement.SE_RadioButtonContents if radio else QStyle.SubElement.SE_CheckBoxContents
    )
    indicator = QRectF(style.subElementRect(indicator_element, option, button)).adjusted(
        0.5, 0.5, -0.5, -0.5
    )
    painter = QPainter(button)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(border, 1))
    painter.setBrush(fill)
    if radio:
        painter.drawEllipse(indicator)
    else:
        painter.drawRoundedRect(indicator, 3, 3)
    if enabled and (hovered or pressed):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.control_pressed if pressed else theme.control_hover))
        if radio:
            painter.drawEllipse(indicator)
        else:
            painter.drawRoundedRect(indicator, 3, 3)

    if selected:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(mark)
        if radio:
            painter.drawEllipse(indicator.center(), 2.5, 2.5)
        elif partial:
            painter.drawRoundedRect(
                QRectF(indicator.left() + 3, indicator.center().y() - 1, indicator.width() - 6, 2),
                1,
                1,
            )
        else:
            check = QPainterPath()
            check.moveTo(QPointF(indicator.left() + 3, indicator.center().y()))
            check.lineTo(QPointF(indicator.left() + 5.5, indicator.bottom() - 3))
            check.lineTo(QPointF(indicator.right() - 2.5, indicator.top() + 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(
                QPen(
                    mark,
                    1.8,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.drawPath(check)

    foreground = QColor(theme.text if enabled else theme.text_disabled)
    for group in (
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
        QPalette.ColorGroup.Disabled,
    ):
        option.palette.setColor(group, QPalette.ColorRole.WindowText, foreground)
        option.palette.setColor(group, QPalette.ColorRole.ButtonText, foreground)
    label = _ChoiceOption(option)
    label.rect = style.subElementRect(contents_element, option, button)
    style.drawControl(label_element, label, painter, button)

    if (
        enabled
        and option.state & state.State_HasFocus
        and option.state & state.State_KeyboardFocusChange
    ):
        focus_element = (
            QStyle.SubElement.SE_RadioButtonFocusRect
            if radio
            else QStyle.SubElement.SE_CheckBoxFocusRect
        )
        focus = QRectF(style.subElementRect(focus_element, option, button)).adjusted(
            0.5, 0.5, -0.5, -0.5
        )
        painter.setPen(QPen(accent, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(focus, 2, 2)
    painter.end()


class ModernCheckBox(QCheckBox):
    """A QCheckBox with Fusion geometry and a themed, three-state indicator."""

    themeChanged = Signal(object)

    def __init__(self, *args, theme: ModernTheme | None = None, **kwargs) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        super().__init__(*args, **kwargs)
        self._theme_override = theme
        self._fusion_style = QStyleFactory.create("Fusion")
        self._fusion_style.setParent(self)
        self.setStyle(self._fusion_style)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._theme_binding = ThemeBinding(self, self.theme, self.update)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def paintEvent(self, event) -> None:
        option = _ChoiceOption()
        self.initStyleOption(option)
        _paint_choice(self, option, self.theme(), radio=False)


class ModernRadioButton(QRadioButton):
    """A QRadioButton with Fusion geometry and a themed circular indicator."""

    themeChanged = Signal(object)

    def __init__(self, *args, theme: ModernTheme | None = None, **kwargs) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        super().__init__(*args, **kwargs)
        self._theme_override = theme
        self._fusion_style = QStyleFactory.create("Fusion")
        self._fusion_style.setParent(self)
        self.setStyle(self._fusion_style)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._theme_binding = ThemeBinding(self, self.theme, self.update)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def paintEvent(self, event) -> None:
        option = _ChoiceOption()
        self.initStyleOption(option)
        _paint_choice(self, option, self.theme(), radio=True)
