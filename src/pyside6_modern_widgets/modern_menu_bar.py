"""A QMenuBar that creates ModernMenu instances for its drop-down menus."""

from __future__ import annotations

from typing import overload

from PySide6.QtCore import QEvent
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
from PySide6.QtWidgets import QMenu, QMenuBar, QToolButton, QWidget

from ._window_chrome import INACTIVE_TITLE_OPACITY, WindowTitleBar
from .modern_menu import ModernMenu
from .theme import DEFAULT_METRICS, ModernMetrics, ModernTheme, theme_manager


def _menu_bar_style(
    theme: ModernTheme, metrics: ModernMetrics, in_title_bar: bool = False, active: bool = True
) -> str:
    style = f"""
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
    if in_title_bar:
        color = QColor(theme.text)
        if not active:
            color.setAlphaF(color.alphaF() * INACTIVE_TITLE_OPACITY)
        style += f"""
        QMenuBar::item {{
            color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()});
        }}
        """
    return style


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
        self._styled_in_title_bar = False
        self._styled_active = True
        self._observed_window: QWidget | None = None
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
        window = self.window()
        if window is not self._observed_window:
            if self._observed_window is not None:
                self._observed_window.removeEventFilter(self)
            self._observed_window = window
            window.installEventFilter(self)
        theme = self._inherited_theme()
        in_title_bar = self._in_title_bar()
        active = window.isActiveWindow()
        if (
            theme != self._styled_theme
            or in_title_bar != self._styled_in_title_bar
            or (in_title_bar and active != self._styled_active)
        ):
            # Cache before setting the style sheet, which can emit palette events.
            self._styled_theme = theme
            self._styled_in_title_bar = in_title_bar
            self._styled_active = active
            self.setStyleSheet(_menu_bar_style(theme, self._metrics, in_title_bar, active))
            # Re-polishing QMenuBar can temporarily expand it to the window width.
            # Restore the title-bar layout before hit testing or painting resumes.
            parent = self.parentWidget()
            layout = parent.layout() if parent is not None else None
            if in_title_bar and layout is not None:
                layout.activate()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.ActivationChange and watched is getattr(
            self, "_observed_window", None
        ):
            self._apply_theme()
        return super().eventFilter(watched, event)

    def _in_title_bar(self) -> bool:
        ancestor = self.parentWidget()
        while ancestor is not None:
            if isinstance(ancestor, WindowTitleBar):
                return True
            ancestor = ancestor.parentWidget()
        return False

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
        owner = self.window() if self._in_title_bar() else self.parentWidget() or self
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
