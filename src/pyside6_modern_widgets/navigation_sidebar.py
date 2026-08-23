"""Collapsible navigation sidebar component."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QByteArray, QEasingCurve, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QPushButton,
    QScrollArea,
    QStyle,
    QStyleOptionButton,
    QStylePainter,
    QVBoxLayout,
    QWidget,
)

from . import _resources  # noqa: F401
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    palette_for_theme,
    theme_manager,
    tinted_icon,
)


def _sidebar_style(theme: ModernTheme, metrics: ModernMetrics) -> str:
    compact_content_width = max(0, metrics.navigation_collapsed_width - 12)
    item_icon_padding = max(0, (compact_content_width - 18) // 2)
    toggle_icon_padding = max(0, (compact_content_width - 20) // 2)
    return f"""
            QWidget#ModernNavigationSidebar {{
                background-color: {theme.navigation_background};
                border: none;
            }}
            QPushButton[class="NavigationItem"] {{
                background-color: transparent;
                border: none;
                border-radius: {metrics.control_radius}px;
                color: {theme.text};
                text-align: left;
                padding-left: {item_icon_padding}px;
                margin-bottom: 4px;
            }}
            QPushButton[class="NavigationItem"]:hover {{
                background-color: {theme.control_hover};
            }}
            QPushButton[class="NavigationItem"]:pressed {{
                background-color: {theme.control_pressed};
                padding-left: 12px;
            }}
            QPushButton[class="NavigationItem"]:checked {{
                background-color: {theme.control_pressed};
            }}
            QPushButton[class="NavigationItem"]:disabled {{
                color: {theme.text_disabled};
            }}
            QPushButton#NavigationToggleButton {{
                background-color: transparent;
                border: none;
                border-radius: {metrics.control_radius}px;
                margin-bottom: 10px;
                text-align: left;
                padding-left: {toggle_icon_padding}px;
            }}
            QPushButton#NavigationToggleButton:hover {{
                background-color: {theme.control_hover};
            }}
            QScrollArea {{ border: none; background-color: transparent; }}
            QWidget#NavigationScrollContent {{ background-color: transparent; }}
            QScrollBar:vertical {{ width: 4px; background: transparent; }}
            QScrollBar::handle:vertical {{
                background: {theme.scrollbar};
                min-height: 20px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {theme.scrollbar_hover}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """


def navigation_content_style(theme: ModernTheme, radius: int = 8) -> str:
    return f"""
        QFrame#NavigationContent {{
            background-color: {theme.navigation_content};
            border: 1px solid {theme.border};
            border-bottom: none;
            border-top-left-radius: {max(0, radius)}px;
        }}
    """


class NavigationPosition(Enum):
    TOP = 0
    BOTTOM = 1


class _NavigationButton(QPushButton):
    def paintEvent(self, _event) -> None:
        option = QStyleOptionButton()
        self.initStyleOption(option)
        state = option.state  # type: ignore[attr-defined]
        if state & QStyle.StateFlag.State_HasFocus:
            state &= ~QStyle.StateFlag.State_HasFocus
            state |= QStyle.StateFlag.State_MouseOver
            option.state = state  # type: ignore[attr-defined]
        painter = QStylePainter(self)
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)


class _NavigationItem(_NavigationButton):
    def __init__(
        self,
        text: str,
        icon,
        metrics: ModernMetrics,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.fullText = text
        self.setProperty("class", "NavigationItem")
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(metrics.navigation_item_height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(_coerce_icon(icon))
        self.setIconSize(QSize(18, 18))
        self.setCollapsed(False)

    def setCollapsed(self, collapsed: bool) -> None:
        self.setText("" if collapsed else self.fullText)
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

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        super().__init__(parent)
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self._metrics = metrics
        theme_manager().themeChanged.connect(self._on_global_theme_changed)
        self.setObjectName("ModernNavigationSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_sidebar_style(self._theme, self._metrics))
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self._collapsed_width = metrics.navigation_collapsed_width
        self._expanded_width = metrics.navigation_expanded_width
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

        self.toggleButton = _NavigationButton(self)
        self.toggleButton.setObjectName("NavigationToggleButton")
        self.toggleButton.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.toggleButton.setIcon(
            tinted_icon(
                QIcon(":/pyside6_modern_widgets/icons/menu.png"),
                self._theme.text,
            )
        )
        self.toggleButton.setIconSize(QSize(20, 20))
        self.toggleButton.setFixedWidth(
            max(
                1,
                self._collapsed_width
                - layout.contentsMargins().left()
                - layout.contentsMargins().right(),
            )
        )
        self.toggleButton.setMinimumHeight(self._metrics.navigation_item_height)
        self.toggleButton.setToolTip("Toggle navigation")
        self.toggleButton.clicked.connect(self.toggle)
        layout.addWidget(self.toggleButton, alignment=Qt.AlignmentFlag.AlignLeft)

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
        self._min_animation = QPropertyAnimation(
            self,
            QByteArray(b"minimumWidth"),
            self,
        )
        self._max_animation = QPropertyAnimation(
            self,
            QByteArray(b"maximumWidth"),
            self,
        )
        for animation in (self._min_animation, self._max_animation):
            animation.setDuration(self._metrics.animation_duration)
            animation.setEasingCurve(QEasingCurve.Type.OutQuint)

    def addItem(
        self,
        text: str,
        icon=None,
        position: NavigationPosition = NavigationPosition.TOP,
    ) -> int:
        button = _NavigationItem(text, icon, self._metrics, self)
        button.setCollapsed(self._collapsed)
        index = len(self._items)
        self._items.append(button)
        self._button_group.addButton(button, index)
        if position is NavigationPosition.TOP:
            self._top_layout.insertWidget(self._top_layout.count() - 1, button)
        else:
            self._bottom_layout.addWidget(button)
        button.clicked.connect(lambda _checked=False, target=button: self._activate_button(target))
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

    def theme(self) -> ModernTheme:
        return self._theme

    def setTheme(self, theme: ModernTheme | None) -> None:
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self._apply_theme()

    def _on_global_theme_changed(self, theme: ModernTheme) -> None:
        if self._uses_global_theme:
            self._theme = theme
            self._apply_theme()

    def _apply_theme(self) -> None:
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self.setStyleSheet(_sidebar_style(self._theme, self._metrics))
        self.toggleButton.setIcon(
            tinted_icon(
                QIcon(":/pyside6_modern_widgets/icons/menu.png"),
                self._theme.text,
            )
        )

    def _activate_button(self, button: _NavigationItem) -> None:
        try:
            index = self._items.index(button)
        except ValueError:
            return
        self.setCurrentIndex(index)
