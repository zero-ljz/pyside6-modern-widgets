"""A QMenuBar that creates ModernMenu instances for its drop-down menus."""

from __future__ import annotations

from typing import overload

from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import QMenu, QMenuBar, QWidget

from .modern_menu import ModernMenu
from .theme import DEFAULT_METRICS, ModernMetrics


class ModernMenuBar(QMenuBar):
    """A ``QMenuBar`` whose title-based menus use ``ModernMenu``."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        super().__init__(parent)
        self._metrics = metrics

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
