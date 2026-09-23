"""Compact exclusive choices with inherited modern colors."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QSizePolicy, QWidget

from .theme import ModernTheme, inherited_theme, theme_manager


class ModernSegmentedControl(QWidget):
    """One exclusive choice among related views, filters, or form modes.

    ``group`` exposes Qt's button IDs (the label indices) and ``buttons`` exposes
    the ordinary checkable QPushButtons for signals, text, and enabled state.
    An empty sequence creates a control without a checked button.
    """

    def __init__(
        self,
        labels: Sequence[str],
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme_override = theme
        self._styled_theme: ModernTheme | None = None
        self._applying_theme = False
        self._theme_ancestors: list[QWidget] = []
        self.setObjectName("ModernSegmentedControl")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: list[QPushButton] = []
        for index, label in enumerate(labels):
            button = QPushButton(label, self)
            button.setObjectName("ModernSegmentButton")
            button.setCheckable(True)
            button.setAutoDefault(False)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(button, index)
            self.buttons.append(button)
            layout.addWidget(button)
        if self.buttons:
            self.buttons[0].setChecked(True)
        theme_manager().themeChanged.connect(self._on_theme_changed)
        self._watch_theme_ancestors()
        self._apply_theme()

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override colors locally, or pass None to restore theme inheritance."""
        self._theme_override = theme
        self._apply_theme()

    def _watch_theme_ancestors(self) -> None:
        for previous in self._theme_ancestors:
            previous.removeEventFilter(self)
        self._theme_ancestors.clear()
        ancestor: QWidget | None = self.parentWidget()
        while ancestor is not None:
            ancestor.installEventFilter(self)
            self._theme_ancestors.append(ancestor)
            ancestor = ancestor.parentWidget()

    def _on_theme_changed(self, _theme: ModernTheme) -> None:
        self._apply_theme()

    def eventFilter(self, watched, event) -> bool:
        if hasattr(self, "_theme_ancestors") and watched in self._theme_ancestors:
            if event.type() == QEvent.Type.ParentChange:
                self._watch_theme_ancestors()
                self._apply_theme()
            elif event.type() in (QEvent.Type.PaletteChange, QEvent.Type.UpdateRequest):
                # A theme-only token change can repaint an ancestor without changing its palette.
                self._apply_theme()
        return super().eventFilter(watched, event)

    def event(self, event) -> bool:
        result = super().event(event)
        if hasattr(self, "_theme_ancestors") and event.type() == QEvent.Type.ParentChange:
            self._watch_theme_ancestors()
            self._apply_theme()
        return result

    def _apply_theme(self) -> None:
        if self._applying_theme:
            return
        theme = self.theme()
        if theme == self._styled_theme:
            return
        self._applying_theme = True
        try:
            self.setStyleSheet(
                f"""
                QWidget#ModernSegmentedControl {{
                    background: {theme.surface_alternate};
                    border: 1px solid {theme.border};
                    border-radius: 4px;
                }}
                QWidget#ModernSegmentedControl > QPushButton#ModernSegmentButton {{
                    min-width: 46px;
                    min-height: 26px;
                    padding: 0 7px;
                    color: {theme.text};
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 4px;
                }}
                QWidget#ModernSegmentedControl > QPushButton#ModernSegmentButton:hover:!checked {{
                    background: {theme.tab_hover};
                }}
                QWidget#ModernSegmentedControl > QPushButton#ModernSegmentButton:checked {{
                    background: {theme.tab_selected};
                    border-color: {theme.tab_divider};
                }}
                QWidget#ModernSegmentedControl > QPushButton#ModernSegmentButton:disabled {{
                    color: {theme.text_disabled};
                }}
                """
            )
            self._styled_theme = theme
        finally:
            self._applying_theme = False
