"""A QMenuBar that creates ModernMenu instances for its drop-down menus."""

from __future__ import annotations

from typing import overload

from PySide6.QtCore import QEvent
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import QMenu, QMenuBar, QToolButton, QWidget

from .modern_menu import ModernMenu
from .theme import DEFAULT_METRICS, ModernMetrics, ModernTheme, theme_manager


def _menu_bar_style(theme: ModernTheme, metrics: ModernMetrics) -> str:
    return f"""
    QMenuBar {{ background: transparent; border: none; }}
    QMenuBar::item {{ background: transparent; }}
    QMenuBar::item:selected {{
        background: {theme.control_pressed};
        border-radius: {metrics.control_radius}px;
    }}
    QToolButton#qt_menubar_ext_button {{ background: transparent; border: none; }}
    QToolButton#qt_menubar_ext_button:hover, QToolButton#qt_menubar_ext_button:pressed {{
        background: {theme.control_pressed};
        border-radius: {metrics.control_radius}px;
    }}
    """


class ModernMenuBar(QMenuBar):
    """A themed, transparent menu bar whose title-based menus use ``ModernMenu``."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        super().__init__(parent)
        self._metrics = metrics
        self._styled_theme: ModernTheme | None = None
        theme_manager().themeChanged.connect(self._on_theme_changed)
        self._apply_theme()
        # Qt fills this menu with overflow actions during layout. Supply the
        # modern menu before the first layout instead of letting Qt create QMenu.
        extension: QToolButton | None = self.findChild(QToolButton, "qt_menubar_ext_button")
        if extension is not None:
            extension.setMenu(ModernMenu(self, metrics=metrics))

    def _inherited_theme(self) -> ModernTheme:
        ancestor = self.parentWidget()
        while ancestor is not None:
            get_theme = getattr(ancestor, "theme", None)
            if callable(get_theme):
                theme = get_theme()
                if isinstance(theme, ModernTheme):
                    return theme
            ancestor = ancestor.parentWidget()
        return theme_manager().theme()

    def _apply_theme(self) -> None:
        theme = self._inherited_theme()
        if theme != self._styled_theme:
            # Cache before setting the style sheet, which can emit palette events.
            self._styled_theme = theme
            self.setStyleSheet(_menu_bar_style(theme, self._metrics))

    def _on_theme_changed(self, _theme: ModernTheme) -> None:
        self._apply_theme()

    def event(self, event) -> bool:
        handled = super().event(event)
        if event.type() in (QEvent.Type.ParentChange, QEvent.Type.PaletteChange) and hasattr(
            self, "_styled_theme"
        ):
            self._apply_theme()
        return handled

    @overload
    def addMenu(self, menu: QMenu, /) -> QAction: ...

    @overload
    def addMenu(self, title: str, /) -> ModernMenu: ...

    @overload
    def addMenu(self, icon: QIcon | QPixmap, title: str, /) -> ModernMenu: ...

    def addMenu(self, *args):
        owner = self.parentWidget() or self
        if len(args) == 1 and isinstance(args[0], str):
            menu = ModernMenu(args[0], owner, metrics=self._metrics)
            super().addMenu(menu)
            return menu
        if len(args) == 2 and isinstance(args[0], (QIcon, QPixmap)) and isinstance(args[1], str):
            menu = ModernMenu(args[1], owner, metrics=self._metrics)
            menu.setIcon(QIcon(args[0]))
            super().addMenu(menu)
            return menu
        return super().addMenu(*args)
