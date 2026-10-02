"""Themed multiline editors retaining Qt's native document behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QEvent, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QProxyStyle,
    QStyle,
    QStyleOptionFrame,
    QTextEdit,
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


class _TextEditStyle(QProxyStyle):
    def __init__(self, editor: QWidget) -> None:
        super().__init__("Fusion")
        self.setParent(editor)
        self._editor = editor

    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if (
            element != QStyle.PrimitiveElement.PE_Frame
            or widget is not self._editor
            or not isinstance(option, QStyleOptionFrame)
        ):
            super().drawPrimitive(element, option, painter, widget)
            return
        option = cast(_TextOption, option)
        editor = cast(_TextAppearance, self._editor)
        theme = editor.theme()
        rect = QRectF(option.rect).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = min(editor._metrics.control_radius, rect.width() / 2, rect.height() / 2)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(option.palette.color(QPalette.ColorRole.Mid), 1))
        painter.setBrush(QBrush(option.palette.color(QPalette.ColorRole.Base)))
        painter.drawRoundedRect(rect, radius, radius)
        if (
            option.state & QStyle.StateFlag.State_HasFocus
            and option.state & QStyle.StateFlag.State_Enabled
        ):
            accent = (
                QColor(theme.accent)
                if theme.accent is not None
                else option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent)
            )
            _draw_focus_underline(
                painter, option.rect, radius, accent, self._editor.devicePixelRatioF()
            )
        painter.restore()


class _TextOption(QStyleOptionFrame):
    rect: QRect
    palette: QPalette
    state: QStyle.StateFlag


if TYPE_CHECKING:
    _TextBase = QWidget
else:
    _TextBase = object


class _TextAppearance(_TextBase):
    def _init_appearance(self, theme: ModernTheme | None, metrics: ModernMetrics) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        owner = cast(QTextEdit | QPlainTextEdit, self)
        self._theme_override = theme
        self._metrics = metrics
        self._palette_override = QPalette()
        self._applying_theme = False
        self._styled_theme: ModernTheme | None = None
        self._modern_style = _TextEditStyle(owner)
        owner.setStyle(self._modern_style)
        owner.setAttribute(Qt.WidgetAttribute.WA_Hover)
        owner.viewport().setAutoFillBackground(False)
        owner.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._apply_theme()
        self._theme_binding = ThemeBinding(owner, self.theme, self._apply_theme)
        self._theme_binding.changed.connect(
            cast(ModernPlainTextEdit | ModernTextEdit, owner).themeChanged.emit
        )

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def setPalette(self, palette: QPalette | Qt.GlobalColor | QColor) -> None:
        owner = cast(QTextEdit | QPlainTextEdit, self)
        if not hasattr(self, "_palette_override"):
            QWidget.setPalette(owner, palette)
            return
        self._palette_override = QPalette(palette)
        self._apply_theme()

    def _themed_palette(self, theme: ModernTheme) -> QPalette:
        owner = cast(QTextEdit | QPlainTextEdit, self)
        themed = palette_for_theme(theme, owner.palette())
        palette = self._palette_override.resolve(themed)
        palette.setResolveMask(self._palette_override.resolveMask() | themed.resolveMask())
        fills = (
            _CONTROL_FILLS_DARK if QColor(theme.surface).lightness() < 128 else _CONTROL_FILLS_LIGHT
        )
        if not self._palette_override.isBrushSet(
            QPalette.ColorGroup.Active, QPalette.ColorRole.Base
        ):
            fill_index = (
                2
                if not owner.isEnabled() or owner.isReadOnly()
                else 1
                if owner.underMouse() and not owner.hasFocus()
                else 0
            )
            palette.setColor(QPalette.ColorRole.Base, QColor(fills[fill_index]))
        return palette

    def setReadOnly(self, read_only: bool) -> None:
        super().setReadOnly(read_only)  # type: ignore[misc]
        if getattr(self, "_styled_theme", None) is not None:
            self._apply_theme()

    def _apply_theme(self) -> None:
        if self._applying_theme:
            return
        owner = cast(QTextEdit | QPlainTextEdit, self)
        self._applying_theme = True
        try:
            self._styled_theme = self.theme()
            QWidget.setPalette(owner, self._themed_palette(self._styled_theme))
            viewport = owner.viewport()
            viewport_palette = viewport.palette()
            viewport_palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
            viewport.setPalette(viewport_palette)
            viewport.update()
            owner.update()
        finally:
            self._applying_theme = False

    def event(self, event: QEvent) -> bool:
        handled = super().event(event)  # type: ignore[misc]
        owner = cast(QTextEdit | QPlainTextEdit, self)
        if (
            event.type() == QEvent.Type.PaletteChange
            and getattr(self, "_styled_theme", None) is not None
            and not self._applying_theme
            and owner.palette() != self._themed_palette(self.theme())
        ):
            self._apply_theme()
        if event.type() in (
            QEvent.Type.Enter,
            QEvent.Type.Leave,
            QEvent.Type.EnabledChange,
            QEvent.Type.FocusIn,
            QEvent.Type.FocusOut,
        ):
            self._apply_theme()
            owner.update()
        return handled


class ModernPlainTextEdit(_TextAppearance, QPlainTextEdit):
    """A themed ``QPlainTextEdit`` for large plain-text documents."""

    themeChanged = Signal(object)

    def __init__(
        self,
        text: str | QWidget | None = "",
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        if isinstance(text, QWidget):
            if parent is not None:
                raise TypeError("parent specified twice")
            parent, text = text, ""
        QPlainTextEdit.__init__(self, text or "", parent)
        self._init_appearance(theme, metrics)


class ModernTextEdit(_TextAppearance, QTextEdit):
    """A themed ``QTextEdit`` with native rich-text editing."""

    themeChanged = Signal(object)

    def __init__(
        self,
        text: str | QWidget | None = "",
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        if isinstance(text, QWidget):
            if parent is not None:
                raise TypeError("parent specified twice")
            parent, text = text, ""
        QTextEdit.__init__(self, text or "", parent)
        self._init_appearance(theme, metrics)
