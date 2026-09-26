"""Keep inherited themes current across hidden widgets and parent changes."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QMetaObject, QObject, Signal, Slot
from PySide6.QtWidgets import QWidget
from shiboken6 import isValid

from .theme import ModernTheme, theme_manager


class ThemeBinding(QObject):
    changed = Signal(object)

    def __init__(
        self,
        owner: QObject,
        resolve: Callable[[], ModernTheme],
        apply: Callable[[], None],
        *,
        source: Callable[[], QWidget | None] | None = None,
    ) -> None:
        super().__init__(owner)
        self._owner = owner
        self._resolve = resolve
        self._apply = apply
        self._source = source or self._parent_widget
        self._theme = resolve()
        self._ancestors: list[QWidget] = []
        self._connections: list[QMetaObject.Connection] = []
        self._active = True
        self._refreshing = False
        owner.installEventFilter(self)
        self._global_connection = theme_manager().themeChanged.connect(self.refresh)
        owner.destroyed.connect(self._dispose)
        self.rebind()

    def _parent_widget(self) -> QWidget | None:
        parent = self._owner.parent()
        return parent if isinstance(parent, QWidget) else None

    def rebind(self) -> None:
        if not self._active:
            return
        self._disconnect_ancestors()
        ancestor: QWidget | None = self._source()
        while ancestor is not None:
            ancestor.installEventFilter(self)
            self._ancestors.append(ancestor)
            signal = getattr(ancestor, "themeChanged", None)
            if signal is not None:
                self._connections.append(signal.connect(self.refresh))
            ancestor = ancestor.parentWidget()
        self.refresh()

    def _disconnect_ancestors(self) -> None:
        for connection in self._connections:
            if connection:
                QObject.disconnect(connection)
        self._connections.clear()
        for previous in self._ancestors:
            if isValid(previous):
                previous.removeEventFilter(self)
        self._ancestors.clear()

    @Slot()
    def _dispose(self) -> None:
        if not getattr(self, "_active", False):
            return
        self._active = False
        self._disconnect_ancestors()
        if self._global_connection:
            QObject.disconnect(self._global_connection)

    @Slot()
    @Slot(object)
    def refresh(self, *_args: object) -> None:
        if not getattr(self, "_active", False) or self._refreshing:
            return
        self._refreshing = True
        try:
            while self._active:
                theme = self._resolve()
                if theme == self._theme:
                    break
                # Palette changes can synchronously invoke application callbacks.
                # Finish one application before resolving any reentrant override.
                self._theme = theme
                self._apply()
                if not isValid(self) or not self._active:
                    return
                if self._resolve() == theme:
                    self.changed.emit(theme)
        finally:
            self._refreshing = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # Qt can still dispatch events while Python wrappers are being finalized.
        if not getattr(self, "_active", False):
            return False
        if event.type() == QEvent.Type.ParentChange:
            self.rebind()
        elif watched is not self._owner and event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.UpdateRequest,
        ):
            self.refresh()
        return False
