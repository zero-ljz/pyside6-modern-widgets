"""Composite navigation component with a sidebar and page stack."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ._theme import colors_for_theme, resolve_application_theme
from .navigation_sidebar import (
    NavigationPosition,
    NavigationSidebar,
    NavigationStyle,
)
from .window_effect import ThemeMode


class NavigationView(QWidget):
    """Combine a ``NavigationSidebar`` with a synchronized page stack."""

    currentChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ModernNavigationView")
        self.setProperty("pyside6ModernThemeAware", True)
        self._theme_mode = ThemeMode.LIGHT
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "QWidget#ModernNavigationView { background-color: transparent; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = NavigationSidebar(self)
        self.contentContainer = QFrame(self)
        self.contentContainer.setObjectName("NavigationContent")
        self.contentContainer.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground,
            True,
        )
        self.contentContainer.setStyleSheet(NavigationStyle.contentStyle())

        content_layout = QVBoxLayout(self.contentContainer)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.stackedWidget = QStackedWidget(self.contentContainer)
        content_layout.addWidget(self.stackedWidget)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.contentContainer, 1)

        self.sidebar.currentChanged.connect(self.stackedWidget.setCurrentIndex)
        self.stackedWidget.currentChanged.connect(self._on_current_changed)

    def addPage(
        self,
        page: QWidget,
        text: str,
        icon=None,
        position: NavigationPosition = NavigationPosition.TOP,
        selected: bool = False,
    ) -> int:
        page.setAutoFillBackground(False)
        page_index = self.stackedWidget.addWidget(page)
        item_index = self.sidebar.addItem(text, icon, position)
        if item_index != page_index:
            self.stackedWidget.removeWidget(page)
            self.sidebar.removeItem(item_index)
            raise RuntimeError("Navigation item and page indexes are out of sync")
        if selected or self.count() == 1:
            self.setCurrentIndex(page_index)
        self.setThemeMode(self._theme_mode)
        return page_index

    def removePage(self, index: int) -> QWidget | None:
        page = self.widget(index)
        if page is None:
            return None
        was_current = index == self.currentIndex()
        self.stackedWidget.removeWidget(page)
        self.sidebar.removeItem(index)
        page.setParent(None)
        if self.count() and was_current:
            self.setCurrentIndex(min(index, self.count() - 1))
        return page

    def count(self) -> int:
        return self.stackedWidget.count()

    def widget(self, index: int) -> QWidget | None:
        return self.stackedWidget.widget(index)

    def currentWidget(self) -> QWidget | None:
        return self.stackedWidget.currentWidget()

    def currentIndex(self) -> int:
        return self.stackedWidget.currentIndex()

    def setCurrentIndex(self, index: int) -> None:
        if not 0 <= index < self.count():
            return
        self.sidebar.setCurrentIndex(index)
        self.stackedWidget.setCurrentIndex(index)

    def themeMode(self) -> ThemeMode:
        return self._theme_mode

    def resolvedThemeMode(self) -> ThemeMode:
        return resolve_application_theme(self._theme_mode)

    def setThemeMode(self, theme: ThemeMode | str) -> None:
        self._theme_mode = ThemeMode(theme)
        resolved = self.resolvedThemeMode()
        colors = colors_for_theme(resolved)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(colors.page))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors.text))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors.surface))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors.text))
        self.setPalette(palette)
        self.sidebar.setThemeMode(resolved)
        self.contentContainer.setStyleSheet(
            NavigationStyle.contentStyle(theme=resolved)
        )
        for index in range(self.count()):
            page = self.widget(index)
            if page is not None:
                for widget in (page, *page.findChildren(QWidget)):
                    widget.setPalette(palette)

    def _on_current_changed(self, index: int) -> None:
        if index >= 0 and self.sidebar.currentIndex() != index:
            self.sidebar.setCurrentIndex(index)
        self.currentChanged.emit(index)
