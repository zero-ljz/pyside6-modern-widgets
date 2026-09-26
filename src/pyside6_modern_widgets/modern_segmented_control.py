"""Compact exclusive choices with inherited modern colors."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QSizePolicy, QWidget

from ._theme_binding import ThemeBinding
from .theme import ModernTheme, inherited_theme


class ModernSegmentedControl(QWidget):
    """One exclusive choice among related views, filters, or form modes.

    Indices follow the input labels. Programmatic and user selection changes
    emit currentChanged; itemActivated reports clicks, including repeated ones.
    An empty control has currentIndex() == -1.
    """

    themeChanged = Signal(object)
    currentChanged = Signal(int)
    itemActivated = Signal(int)

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
        self.setObjectName("ModernSegmentedControl")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: list[QPushButton] = []
        for index, label in enumerate(labels):
            button = QPushButton(label, self)
            button.setObjectName("ModernSegmentButton")
            button.setCheckable(True)
            button.setAutoDefault(False)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self._group.addButton(button, index)
            self._buttons.append(button)
            layout.addWidget(button)
        if self._buttons:
            self._buttons[0].setChecked(True)
        self._group.idToggled.connect(self._on_toggled)
        self._group.idClicked.connect(self.itemActivated.emit)
        self._apply_theme()
        self._theme_binding: ThemeBinding = ThemeBinding(self, self.theme, self._apply_theme)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def count(self) -> int:
        return len(self._buttons)

    def currentIndex(self) -> int:
        return self._group.checkedId()

    def setCurrentIndex(self, index: int) -> None:
        """Select a valid index; invalid indices leave the selection unchanged."""
        button = self.button(index)
        if button is not None:
            button.setChecked(True)

    def button(self, index: int) -> QPushButton | None:
        """Return a borrowed button for advanced Qt customization."""
        return self._buttons[index] if 0 <= index < self.count() else None

    def itemText(self, index: int) -> str:
        button = self.button(index)
        return button.text() if button is not None else ""

    def setItemText(self, index: int, text: str) -> None:
        button = self.button(index)
        if button is not None:
            button.setText(text)

    def isItemEnabled(self, index: int) -> bool:
        button = self.button(index)
        return button.isEnabled() if button is not None else False

    def setItemEnabled(self, index: int, enabled: bool) -> None:
        button = self.button(index)
        if button is not None:
            button.setEnabled(enabled)

    def _on_toggled(self, index: int, checked: bool) -> None:
        if checked:
            self.currentChanged.emit(index)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override locally; None restores owner/ancestor/global inheritance."""
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

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
