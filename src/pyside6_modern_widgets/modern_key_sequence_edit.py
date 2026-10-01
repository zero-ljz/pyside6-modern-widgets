"""A themed shortcut editor retaining QKeySequenceEdit's capture behavior."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPalette
from PySide6.QtWidgets import QKeySequenceEdit, QLineEdit, QWidget

from ._theme_binding import ThemeBinding
from .modern_line_edit import _LineEditStyle
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    inherited_theme,
    palette_for_theme,
)


class ModernKeySequenceEdit(QKeySequenceEdit):
    """A modern ``QKeySequenceEdit`` with Qt-owned shortcut capture and signals."""

    themeChanged = Signal(object)

    def __init__(
        self,
        sequence: QKeySequence | QWidget | None = None,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        if isinstance(sequence, QWidget):
            if parent is not None:
                raise TypeError("parent specified twice")
            parent, sequence = sequence, None
        if sequence is None:
            super().__init__(parent)
        else:
            super().__init__(sequence, parent)
        self._theme_override = theme
        self._metrics = metrics
        self._palette_override = QPalette()
        self._applying_theme = False
        self._styled_theme: ModernTheme | None = None
        editor = self.findChild(QLineEdit, "qt_keysequenceedit_lineedit")
        if editor is None:
            raise RuntimeError("QKeySequenceEdit has no internal line edit")
        self._editor: QLineEdit = editor
        self._modern_style = _LineEditStyle(self._editor, self)
        self._editor.setStyle(self._modern_style)
        self._editor.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._editor.installEventFilter(self)
        self._apply_theme()
        self._theme_binding: ThemeBinding = ThemeBinding(self, self.theme, self._apply_theme)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
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
            palette = self._themed_palette(self._styled_theme)
            super().setPalette(palette)
            self._editor.setPalette(palette)
            self._editor.update()
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
        return handled

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # Qt can reset the internal editor after the owner applies a new theme.
        if (
            watched is getattr(self, "_editor", None)
            and event.type() == QEvent.Type.PaletteChange
            and not self._applying_theme
            and self._editor.palette() != self.palette()
        ):
            self._editor.setPalette(self.palette())
        return super().eventFilter(watched, event)
