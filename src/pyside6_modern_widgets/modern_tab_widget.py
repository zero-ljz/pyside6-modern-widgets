"""Compact themed tabs for fixed application sections."""

from __future__ import annotations

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QTabWidget, QWidget

from .theme import ModernTheme, palette_for_theme, theme_manager


class ModernTabWidget(QTabWidget):
    """A compact ``QTabWidget`` for fixed pages such as settings sections.

    The widget preserves Qt's native page, signal, and keyboard semantics. Unlike
    :class:`TabView`, it does not add document-tab behaviors such as adding,
    closing, or moving tabs.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
    ) -> None:
        super().__init__(parent)
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()

        self.setDocumentMode(True)
        self.tabBar().setDrawBase(False)
        self.tabBar().setExpanding(False)
        self.tabBar().setObjectName("ModernTabWidgetBar")

        theme_manager().themeChanged.connect(self._on_global_theme_changed)
        self._apply_theme()

    def theme(self) -> ModernTheme:
        return self._theme

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override the theme locally, or pass ``None`` to follow the global theme."""
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self._apply_theme()

    def _on_global_theme_changed(self, theme: ModernTheme) -> None:
        if self._uses_global_theme:
            self._theme = theme
            self._apply_theme()

    def _apply_theme(self) -> None:
        theme = self._theme
        self.setPalette(palette_for_theme(theme, QPalette()))
        self.tabBar().setStyleSheet(
            f"""
            QTabBar#ModernTabWidgetBar::tab {{
                background: transparent;
                color: {theme.text};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 5px 10px;
            }}
            QTabBar#ModernTabWidgetBar::tab:selected {{
                border-bottom-color: {theme.accent or theme.focus};
            }}
            QTabBar#ModernTabWidgetBar::tab:hover {{
                background: {theme.control_hover};
            }}
            QTabBar#ModernTabWidgetBar::tab:disabled {{
                color: {theme.text_disabled};
            }}
            """
        )
