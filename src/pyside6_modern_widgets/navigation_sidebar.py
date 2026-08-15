"""Collapsible navigation sidebar component."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import _resources  # noqa: F401


class NavigationStyle:
    """Colors and styles shared by the navigation component."""

    BACKGROUND = "transparent"
    PAGE_BACKGROUND = "#F0F0F0"
    HOVER = "rgba(0, 0, 0, 0.05)"
    PRESSED = "rgba(0, 0, 0, 0.15)"
    BORDER = "#E5E5E5"

    @classmethod
    def sidebarStyle(cls) -> str:
        return f"""
            QWidget#ModernNavigationSidebar {{
                background-color: {cls.BACKGROUND};
                border: none;
            }}
            QPushButton[class="NavigationItem"] {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: #000000;
                text-align: left;
                padding-left: 10px;
                font-size: 14px;
                margin-bottom: 4px;
            }}
            QPushButton[class="NavigationItem"]:hover {{ background-color: {cls.HOVER}; }}
            QPushButton[class="NavigationItem"]:pressed {{
                background-color: {cls.PRESSED};
                padding-left: 12px;
            }}
            QPushButton[class="NavigationItem"]:checked {{ background-color: {cls.PRESSED}; }}
            QPushButton#NavigationToggleButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                margin-bottom: 10px;
                text-align: left;
                padding-left: 9px;
                font-size: 20px;
            }}
            QPushButton#NavigationToggleButton:hover {{ background-color: {cls.HOVER}; }}
            QScrollArea {{ border: none; background-color: transparent; }}
            QWidget#NavigationScrollContent {{ background-color: transparent; }}
            QScrollBar:vertical {{ width: 4px; background: transparent; }}
            QScrollBar::handle:vertical {{
                background: #CCCCCC;
                min-height: 20px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #999999; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """

    @classmethod
    def contentStyle(cls, radius: int = 8) -> str:
        return f"""
            QFrame#NavigationContent {{
                background-color: {cls.PAGE_BACKGROUND};
                border: 1px solid {cls.BORDER};
                border-bottom: none;
                border-top-left-radius: {max(0, radius)}px;
            }}
        """


class NavigationPosition(Enum):
    TOP = 0
    BOTTOM = 1


class _NavigationItem(QPushButton):
    def __init__(self, text: str, icon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.fullText = text
        self.setProperty("class", "NavigationItem")
        self.setCheckable(True)
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(_coerce_icon(icon))
        self.setIconSize(QSize(18, 18))
        self.setCollapsed(False)

    def setCollapsed(self, collapsed: bool) -> None:
        self.setText("" if collapsed else f"   {self.fullText}")
        self.setToolTip(self.fullText if collapsed else "")


def _coerce_icon(icon) -> QIcon:
    if isinstance(icon, QIcon):
        return icon
    if icon is None:
        return QIcon()
    return QApplication.style().standardIcon(icon)


class NavigationSidebar(QWidget):
    """A standalone sidebar that emits an index when an item is selected."""

    currentChanged = Signal(int)
    itemActivated = Signal(int)
    collapsedChanged = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ModernNavigationSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(NavigationStyle.sidebarStyle())
        self._collapsed_width = 48
        self._expanded_width = 240
        self._collapsed = False
        self._items: list[_NavigationItem] = []
        self._current_index = -1
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._init_ui()
        self._init_animation()
        self.setFixedWidth(self._expanded_width)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(2)

        self.toggleButton = QPushButton(self)
        self.toggleButton.setObjectName("NavigationToggleButton")
        self.toggleButton.setIcon(
            QIcon(":/pyside6_modern_widgets/icons/menu.png")
        )
        self.toggleButton.setIconSize(QSize(20, 20))
        self.toggleButton.setFixedHeight(36)
        self.toggleButton.setToolTip("Toggle navigation")
        self.toggleButton.clicked.connect(self.toggle)
        layout.addWidget(self.toggleButton)

        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollContent = QWidget(self.scrollArea)
        self.scrollContent.setObjectName("NavigationScrollContent")
        self._top_layout = QVBoxLayout(self.scrollContent)
        self._top_layout.setContentsMargins(0, 0, 0, 0)
        self._top_layout.setSpacing(4)
        self._top_layout.addStretch()
        self.scrollArea.setWidget(self.scrollContent)
        layout.addWidget(self.scrollArea)

        self._bottom_layout = QVBoxLayout()
        self._bottom_layout.setSpacing(4)
        layout.addLayout(self._bottom_layout)

    def _init_animation(self) -> None:
        self._min_animation = QPropertyAnimation(self, b"minimumWidth", self)
        self._max_animation = QPropertyAnimation(self, b"maximumWidth", self)
        for animation in (self._min_animation, self._max_animation):
            animation.setDuration(250)
            animation.setEasingCurve(QEasingCurve.Type.OutQuint)

    def addItem(
        self,
        text: str,
        icon=None,
        position: NavigationPosition = NavigationPosition.TOP,
    ) -> int:
        button = _NavigationItem(text, icon, self)
        button.setCollapsed(self._collapsed)
        index = len(self._items)
        self._items.append(button)
        self._button_group.addButton(button, index)
        if position is NavigationPosition.TOP:
            self._top_layout.insertWidget(self._top_layout.count() - 1, button)
        else:
            self._bottom_layout.addWidget(button)
        button.clicked.connect(
            lambda _checked=False, target=button: self._activate_button(target)
        )
        return index

    def removeItem(self, index: int) -> QPushButton | None:
        if not 0 <= index < len(self._items):
            return None
        button = self._items.pop(index)
        self._button_group.removeButton(button)
        self._top_layout.removeWidget(button)
        self._bottom_layout.removeWidget(button)
        button.setParent(None)

        if not self._items:
            self._current_index = -1
            self.currentChanged.emit(-1)
        elif index < self._current_index:
            self._current_index -= 1
        elif index == self._current_index:
            self._current_index = -1
            self.setCurrentIndex(min(index, len(self._items) - 1))
        return button

    def count(self) -> int:
        return len(self._items)

    def button(self, index: int) -> QPushButton | None:
        return self._items[index] if 0 <= index < len(self._items) else None

    def currentIndex(self) -> int:
        return self._current_index

    def setCurrentIndex(self, index: int) -> None:
        if not 0 <= index < len(self._items):
            return
        changed = index != self._current_index
        self._current_index = index
        self._items[index].setChecked(True)
        self.itemActivated.emit(index)
        if changed:
            self.currentChanged.emit(index)

    def isCollapsed(self) -> bool:
        return self._collapsed

    def setCollapsed(self, collapsed: bool, *, animated: bool = True) -> None:
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        for item in self._items:
            item.setCollapsed(collapsed)
        self.scrollArea.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            if collapsed
            else Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        target = self._collapsed_width if collapsed else self._expanded_width
        if not animated:
            self.setFixedWidth(target)
        else:
            start = self.width()
            for animation in (self._min_animation, self._max_animation):
                animation.stop()
                animation.setStartValue(start)
                animation.setEndValue(target)
                animation.start()
        self.collapsedChanged.emit(collapsed)

    def toggle(self) -> None:
        self.setCollapsed(not self._collapsed)

    def _activate_button(self, button: _NavigationItem) -> None:
        try:
            index = self._items.index(button)
        except ValueError:
            return
        self.setCurrentIndex(index)
