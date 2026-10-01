"""Themed spin editors with Qt-owned values, sections, and input handling."""

from __future__ import annotations

from typing import cast

from PySide6.QtCore import (
    QDate,
    QDateTime,
    QEvent,
    QObject,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QTime,
    Signal,
)
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QDateTimeEdit,
    QLineEdit,
    QProxyStyle,
    QSpinBox,
    QStyle,
    QStyleOptionComboBox,
    QStyleOptionSpinBox,
    QWidget,
)

from ._theme_binding import ThemeBinding
from .modern_line_edit import _CONTROL_FILLS_DARK, _CONTROL_FILLS_LIGHT, _draw_focus_underline
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    inherited_theme,
    palette_for_theme,
)


class _SpinOption(QStyleOptionSpinBox):
    # PySide6 6.8 stubs omit these public QStyleOption fields.
    frame: bool
    state: QStyle.StateFlag
    palette: QPalette
    rect: QRect
    direction: Qt.LayoutDirection
    buttonSymbols: QAbstractSpinBox.ButtonSymbols
    subControls: QStyle.SubControl
    activeSubControls: QStyle.SubControl
    stepEnabled: QAbstractSpinBox.StepEnabledFlag


class _ComboOption(QStyleOptionComboBox):
    rect: QRect
    palette: QPalette


class _SpinBoxStyle(QProxyStyle):
    def __init__(self, editor: QAbstractSpinBox) -> None:
        super().__init__("Fusion")
        self.setParent(editor)
        self._editor = editor

    def sizeFromContents(self, contents_type, option, size, widget=None):
        result = super().sizeFromContents(contents_type, option, size, widget)
        if (
            contents_type == QStyle.ContentsType.CT_SpinBox
            and widget is self._editor
            and isinstance(option, QStyleOptionSpinBox)
            and cast(_SpinOption, option).frame
            and option.buttonSymbols != QAbstractSpinBox.ButtonSymbols.NoButtons
        ):
            # Fusion reserves one 14-DIP column; two adjacent buttons need two.
            result.setWidth(result.width() + max(0, result.height() - 5))
        return result

    def subControlRect(self, control, option, sub_control, widget=None):
        if (
            control != QStyle.ComplexControl.CC_SpinBox
            or widget is not self._editor
            or not isinstance(option, QStyleOptionSpinBox)
            or not cast(_SpinOption, option).frame
            or option.buttonSymbols == QAbstractSpinBox.ButtonSymbols.NoButtons
        ):
            return super().subControlRect(control, option, sub_control, widget)
        if sub_control not in (
            QStyle.SubControl.SC_SpinBoxUp,
            QStyle.SubControl.SC_SpinBoxDown,
            QStyle.SubControl.SC_SpinBoxEditField,
        ):
            return super().subControlRect(control, option, sub_control, widget)
        rect = option.rect
        button_width = max(16, rect.height() - 5)
        left = (
            rect.left() + 2
            if option.direction == Qt.LayoutDirection.RightToLeft
            else rect.right() - 2 * button_width + 1
        )
        up = QRect(left, rect.top() + 2, button_width, max(0, rect.height() - 4))
        down = QRect(left + button_width, up.top(), button_width, up.height())
        if sub_control == QStyle.SubControl.SC_SpinBoxUp:
            return up
        if sub_control == QStyle.SubControl.SC_SpinBoxDown:
            return down
        field = super().subControlRect(control, option, sub_control, widget)
        if option.direction == Qt.LayoutDirection.RightToLeft:
            field.setLeft(down.right() + 2)
        else:
            field.setRight(up.left() - 2)
        return field

    def drawComplexControl(self, control, option, painter, widget=None) -> None:
        if (
            control == QStyle.ComplexControl.CC_ComboBox
            and widget is self._editor
            and isinstance(option, QStyleOptionComboBox)
        ):
            combo_option = cast(_ComboOption, option)
            spin_option = cast(_SpinOption, QStyleOptionSpinBox())
            spin_option.initFrom(self._editor)
            spin_option.rect = combo_option.rect
            spin_option.frame = True
            spin_option.buttonSymbols = QAbstractSpinBox.ButtonSymbols.NoButtons
            spin_option.subControls = QStyle.SubControl.SC_SpinBoxFrame
            self.drawComplexControl(QStyle.ComplexControl.CC_SpinBox, spin_option, painter, widget)
            arrow = self.subControlRect(control, option, QStyle.SubControl.SC_ComboBoxArrow, widget)
            center = QPointF(arrow.center())
            path = QPainterPath(center + QPointF(-4, -2))
            path.lineTo(center + QPointF(0, 2))
            path.lineTo(center + QPointF(4, -2))
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(
                QPen(
                    combo_option.palette.color(QPalette.ColorRole.Text),
                    1.3,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.drawPath(path)
            painter.restore()
            return
        if (
            control != QStyle.ComplexControl.CC_SpinBox
            or widget is not self._editor
            or not isinstance(option, QStyleOptionSpinBox)
            or not cast(_SpinOption, option).frame
        ):
            super().drawComplexControl(control, option, painter, widget)
            return
        option = cast(_SpinOption, option)
        editor = cast(_SpinAppearance, self._editor)
        theme = editor.theme()
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        focused = enabled and bool(option.state & QStyle.StateFlag.State_HasFocus)
        fills = (
            _CONTROL_FILLS_DARK if QColor(theme.surface).lightness() < 128 else _CONTROL_FILLS_LIGHT
        )
        fill_index = (
            2 if not enabled or self._editor.isReadOnly() else 1 if hovered and not focused else 0
        )
        surface = QBrush(QColor(fills[fill_index]))
        if editor._palette_override.isBrushSet(
            option.palette.currentColorGroup(), QPalette.ColorRole.Base
        ):
            surface = option.palette.brush(QPalette.ColorRole.Base)
        rect = QRectF(option.rect).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = min(editor._metrics.control_radius, rect.width() / 2, rect.height() / 2)
        border = option.palette.color(QPalette.ColorRole.Mid)
        accent = (
            QColor(theme.accent)
            if theme.accent is not None
            else option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent)
        )
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(border, 1))
        painter.setBrush(surface)
        painter.drawRoundedRect(rect, radius, radius)
        if focused:
            _draw_focus_underline(
                painter, option.rect, radius, accent, self._editor.devicePixelRatioF()
            )

        if option.buttonSymbols != QAbstractSpinBox.ButtonSymbols.NoButtons:
            for sub_control, step_flag, upward in (
                (
                    QStyle.SubControl.SC_SpinBoxUp,
                    QAbstractSpinBox.StepEnabledFlag.StepUpEnabled,
                    True,
                ),
                (
                    QStyle.SubControl.SC_SpinBoxDown,
                    QAbstractSpinBox.StepEnabledFlag.StepDownEnabled,
                    False,
                ),
            ):
                if not option.subControls & sub_control:
                    continue
                button = self.subControlRect(control, option, sub_control, widget)
                active = option.activeSubControls & sub_control
                pressed = active and option.state & QStyle.StateFlag.State_Sunken
                if enabled and active and hovered:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(
                        QColor(theme.control_pressed if pressed else theme.control_hover)
                    )
                    painter.drawRoundedRect(QRectF(button).adjusted(1, 2, -1, -2), 3, 3)
                color = option.palette.color(QPalette.ColorRole.Text)
                if not enabled or not option.stepEnabled & step_flag:
                    color = option.palette.color(
                        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text
                    )
                center = QPointF(button.center()) + QPointF(0, 1 if pressed else 0)
                if option.buttonSymbols == QAbstractSpinBox.ButtonSymbols.PlusMinus:
                    path = QPainterPath(center + QPointF(-4, 0))
                    path.lineTo(center + QPointF(4, 0))
                    if upward:
                        path.moveTo(center + QPointF(0, -4))
                        path.lineTo(center + QPointF(0, 4))
                else:
                    direction = -1 if upward else 1
                    path = QPainterPath(center + QPointF(-4, -direction * 2))
                    path.lineTo(center + QPointF(0, direction * 2))
                    path.lineTo(center + QPointF(4, -direction * 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(
                    QPen(
                        color,
                        1.3,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin,
                    )
                )
                painter.drawPath(path)
        painter.restore()


class _SpinAppearance:
    _theme_override: ModernTheme | None
    _metrics: ModernMetrics
    _palette_override: QPalette
    _applying_theme: bool
    _styled_theme: ModernTheme | None
    _theme_binding: ThemeBinding
    _default_line_edit: QLineEdit | None
    _updating_editor_palette: bool

    def _init_appearance(self, theme: ModernTheme | None, metrics: ModernMetrics) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        owner = cast(QAbstractSpinBox, self)
        self._theme_override = theme
        self._metrics = metrics
        self._palette_override = QPalette()
        self._applying_theme = False
        self._styled_theme = None
        self._modern_style = _SpinBoxStyle(owner)
        owner.setStyle(self._modern_style)
        self._default_line_edit = owner.lineEdit()
        self._updating_editor_palette = False
        if self._default_line_edit is not None:
            self._default_line_edit.installEventFilter(owner)
        owner.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._apply_theme()
        self._theme_binding = ThemeBinding(owner, self.theme, self._apply_theme)
        self._theme_binding.changed.connect(
            cast(ModernSpinBox | ModernDateTimeEdit, owner).themeChanged.emit
        )

    def theme(self) -> ModernTheme:
        return (
            self._theme_override
            if self._theme_override is not None
            else inherited_theme(cast(QWidget, self))
        )

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override locally; None restores owner/ancestor/global inheritance."""
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def setPalette(self, palette: QPalette | Qt.GlobalColor | QColor) -> None:
        owner = cast(QAbstractSpinBox, self)
        if not hasattr(self, "_palette_override"):
            QAbstractSpinBox.setPalette(owner, palette)
            return
        self._palette_override = QPalette(palette)
        self._apply_theme()

    def _themed_palette(self, theme: ModernTheme) -> QPalette:
        owner = cast(QAbstractSpinBox, self)
        themed = palette_for_theme(theme, owner.palette())
        palette = self._palette_override.resolve(themed)
        palette.setResolveMask(self._palette_override.resolveMask() | themed.resolveMask())
        return palette

    def _apply_theme(self) -> None:
        if self._applying_theme:
            return
        self._applying_theme = True
        owner = cast(QAbstractSpinBox, self)
        try:
            self._styled_theme = self.theme()
            QAbstractSpinBox.setPalette(owner, self._themed_palette(self._styled_theme))
            self._refresh_editor_surface()
            owner.update()
        finally:
            self._applying_theme = False

    def _refresh_editor_surface(self) -> None:
        owner = cast(QAbstractSpinBox, self)
        editor = owner.lineEdit()
        if (
            editor is None
            or editor is not self._default_line_edit
            or self._updating_editor_palette
            or editor.palette().color(QPalette.ColorRole.Base).alpha() == 0
        ):
            return
        self._updating_editor_palette = True
        try:
            palette = editor.palette()
            palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
            editor.setPalette(palette)
        finally:
            self._updating_editor_palette = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        handled = super().eventFilter(watched, event)  # type: ignore[misc]
        if watched is getattr(self, "_default_line_edit", None) and event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        ):
            self._refresh_editor_surface()
        return handled

    def event(self, event: QEvent) -> bool:
        owner = cast(QAbstractSpinBox, self)
        handled = super().event(event)  # type: ignore[misc]
        if (
            event.type() == QEvent.Type.PaletteChange
            and getattr(self, "_styled_theme", None) is not None
            and not self._applying_theme
            and owner.palette() != self._themed_palette(self.theme())
        ):
            self._apply_theme()
        if event.type() in (QEvent.Type.Enter, QEvent.Type.Leave):
            owner.update()
        return handled


class ModernSpinBox(_SpinAppearance, QSpinBox):
    """A themed ``QSpinBox`` with native numeric editing and signals."""

    themeChanged = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        QSpinBox.__init__(self, parent)
        self._init_appearance(theme, metrics)


class ModernDateTimeEdit(_SpinAppearance, QDateTimeEdit):
    """A themed ``QDateTimeEdit`` with native date sections and calendar popup."""

    themeChanged = Signal(object)

    def __init__(
        self,
        value: QDateTime | QDate | QTime | QWidget | None = None,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        if isinstance(value, QWidget):
            if parent is not None:
                raise TypeError("parent specified twice")
            parent, value = value, None
        if value is None:
            QDateTimeEdit.__init__(self, parent)
        else:
            QDateTimeEdit.__init__(self, value, parent)
        self._init_appearance(theme, metrics)
