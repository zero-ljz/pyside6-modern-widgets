"""Compact themed tabs for fixed application sections."""

from __future__ import annotations

from PySide6.QtCore import QRect, Signal
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import QTabBar, QTabWidget, QWidget

from ._theme_binding import ThemeBinding
from .theme import ModernTheme, inherited_theme, palette_for_theme


class _ModernSectionTabBar(QTabBar):
    _INDICATOR_INSET = 6
    _INDICATOR_HEIGHT = 2

    def __init__(self, theme: ModernTheme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme

    def setTheme(self, theme: ModernTheme) -> None:
        self._theme = theme
        self.update()

    def _indicator_rect(self, index: int) -> QRect:
        tab_rect = self.tabRect(index)
        inset = min(self._INDICATOR_INSET, max(0, (tab_rect.width() - 1) // 2))
        return QRect(
            tab_rect.left() + inset,
            tab_rect.bottom() - self._INDICATOR_HEIGHT + 1,
            max(0, tab_rect.width() - inset * 2),
            self._INDICATOR_HEIGHT,
        )

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        index = self.currentIndex()
        if index < 0 or not self.isTabVisible(index):
            return
        indicator = self._indicator_rect(index)
        if indicator.isEmpty():
            return
        painter = QPainter(self)
        painter.fillRect(indicator, QColor(self._theme.accent or self._theme.focus))


class ModernTabWidget(QTabWidget):
    """A compact ``QTabWidget`` for fixed pages such as settings sections.

    The widget preserves Qt's native page, signal, and keyboard semantics. Unlike
    :class:`TabView`, it does not add document-tab behaviors such as adding,
    closing, or moving tabs.
    """

    themeChanged = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme_override = theme
        self._theme = theme if theme is not None else inherited_theme(self)

        self._tab_bar = _ModernSectionTabBar(self._theme, self)
        self.setTabBar(self._tab_bar)
        self.setDocumentMode(True)
        self._tab_bar.setDrawBase(False)
        self._tab_bar.setExpanding(False)
        self._tab_bar.setObjectName("ModernTabWidgetBar")

        self._apply_theme()
        self._theme_binding: ThemeBinding = ThemeBinding(self, self.theme, self._apply_theme)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def takeTab(self, index: int) -> QWidget | None:
        """Remove and hide a page, transferring ownership to the caller."""
        page = self.widget(index)
        if page is None:
            return None
        self.removeTab(index)
        page.hide()
        page.setParent(None)
        return page

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override locally; None restores ancestor/global theme inheritance."""
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def _apply_theme(self) -> None:
        self._theme = self.theme()
        theme = self._theme
        self.setPalette(palette_for_theme(theme, QPalette()))
        self._tab_bar.setTheme(theme)
        self._tab_bar.setStyleSheet(
            f"""
            QTabBar#ModernTabWidgetBar::tab {{
                background: transparent;
                color: {theme.text};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 5px 10px;
            }}
            QTabBar#ModernTabWidgetBar::tab:hover {{
                background: {theme.control_hover};
            }}
            QTabBar#ModernTabWidgetBar::tab:disabled {{
                color: {theme.text_disabled};
            }}
            """
        )
