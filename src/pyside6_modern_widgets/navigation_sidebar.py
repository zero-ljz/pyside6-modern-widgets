"""Collapsible navigation sidebar component."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QByteArray, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QProxyStyle,
    QPushButton,
    QScrollArea,
    QSizePolicy,
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

_COLLAPSED_TOOLTIP_WAKE_UP_DELAY_MS = 250
_SIDEBAR_SCROLLBAR_WIDTH = 4


class _CollapsedNavigationToolTipStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None) -> int:
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return _COLLAPSED_TOOLTIP_WAKE_UP_DELAY_MS
        return super().styleHint(hint, option, widget, returnData)


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
                padding-top: 0px;
                padding-right: 0px;
                padding-bottom: 0px;
                padding-left: {item_icon_padding}px;
                margin-top: 0px;
                margin-right: 0px;
                margin-bottom: 4px;
                margin-left: 0px;
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
                padding-top: 0px;
                padding-right: 0px;
                padding-bottom: 0px;
                margin-top: 0px;
                margin-right: 0px;
                margin-bottom: 4px;
                margin-left: 0px;
                text-align: left;
                padding-left: {toggle_icon_padding}px;
            }}
            QPushButton#NavigationToggleButton:hover {{
                background-color: {theme.control_hover};
            }}
            QScrollArea {{ border: none; background-color: transparent; }}
            QWidget#NavigationScrollContent {{ background-color: transparent; }}
            QScrollBar:vertical {{
                width: {_SIDEBAR_SCROLLBAR_WIDTH}px;
                background: transparent;
            }}
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
        self.setFixedHeight(metrics.navigation_item_height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(_coerce_icon(icon))
        self.setIconSize(QSize(18, 18))
        self._tooltip_style = _CollapsedNavigationToolTipStyle()
        self.setStyle(self._tooltip_style)
        self._collapsed = False
        self._unconstrained_minimum_width = self.minimumWidth()
        self._unconstrained_maximum_width = self.maximumWidth()
        self.setCollapsed(False)

    def setText(self, text: str) -> None:
        self.fullText = text
        super().setText("" if self._collapsed else text)
        self.setToolTip(text if self._collapsed else "")

    def setCollapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        super().setText("" if collapsed else self.fullText)
        self.setToolTip(self.fullText if collapsed else "")

    def _set_compact_width(self, width: int | None) -> None:
        if width is None:
            self.setMinimumWidth(self._unconstrained_minimum_width)
            self.setMaximumWidth(self._unconstrained_maximum_width)
        else:
            self.setFixedWidth(width)


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
    collapseIntentChanged = Signal(bool)

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
        self._overlay_surface = False
        self._compact_item_width = max(1, self._collapsed_width - 12)
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
        layout.setContentsMargins(6, 8, 6, 4)
        layout.setSpacing(4)

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
        self.toggleButton.setFixedHeight(self._metrics.navigation_item_height)
        self.toggleButton.setToolTip("Toggle navigation")
        self.toggleButton.clicked.connect(self.toggle)
        layout.addWidget(self.toggleButton, alignment=Qt.AlignmentFlag.AlignLeft)

        self.scrollArea = QScrollArea(self)
        self.scrollArea.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Ignored,
        )
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scrollContent = QWidget(self.scrollArea)
        self.scrollContent.setObjectName("NavigationScrollContent")
        self._top_layout = QVBoxLayout(self.scrollContent)
        self._top_layout.setContentsMargins(0, 0, 0, 0)
        self._top_layout.setSpacing(4)
        self._top_layout.addStretch()
        self.scrollArea.setWidget(self.scrollContent)
        layout.addWidget(self.scrollArea)

        self._bottom_container = QWidget(self)
        self._bottom_container.setFixedHeight(0)
        self._bottom_container.hide()
        self._bottom_layout = QVBoxLayout(self._bottom_container)
        self._bottom_layout.setContentsMargins(0, 0, 0, 0)
        self._bottom_layout.setSpacing(4)
        layout.addWidget(self._bottom_container)

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
        button._set_compact_width(self._compact_item_width if self._collapsed else None)
        index = len(self._items)
        self._items.append(button)
        self._button_group.addButton(button, index)
        if position is NavigationPosition.TOP:
            self._top_layout.insertWidget(self._top_layout.count() - 1, button)
        else:
            self._bottom_layout.addWidget(button)
            self._sync_bottom_container_height()
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
        self._sync_bottom_container_height()

        if not self._items:
            self._current_index = -1
            self.currentChanged.emit(-1)
        elif index < self._current_index:
            self._current_index -= 1
        elif index == self._current_index:
            self._current_index = -1
            self.setCurrentIndex(min(index, len(self._items) - 1))
        return button

    def _sync_bottom_container_height(self) -> None:
        has_items = self._bottom_layout.count() > 0
        self._bottom_container.setFixedHeight(
            self._bottom_layout.sizeHint().height() if has_items else 0
        )
        self._bottom_container.setVisible(has_items)

    def count(self) -> int:
        return len(self._items)

    def button(self, index: int) -> QPushButton | None:
        return self._items[index] if 0 <= index < len(self._items) else None

    def itemText(self, index: int) -> str:
        return self._items[index].fullText if 0 <= index < len(self._items) else ""

    def setItemText(self, index: int, text: str) -> None:
        if 0 <= index < len(self._items):
            self._items[index].setText(text)

    def itemIcon(self, index: int) -> QIcon:
        return self._items[index].icon() if 0 <= index < len(self._items) else QIcon()

    def setItemIcon(self, index: int, icon) -> None:
        if 0 <= index < len(self._items):
            self._items[index].setIcon(_coerce_icon(icon))

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

    def setOverlaySurface(self, overlay: bool) -> None:
        if self._overlay_surface == overlay:
            return
        self._overlay_surface = overlay
        self.setProperty("overlay", overlay)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, overlay)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _overlay_surface_path(self) -> QPainterPath:
        surface_rect = QRectF(self.rect())
        surface_path = QPainterPath()
        if self._collapsed or self._metrics.corner_radius <= 0:
            surface_path.addRect(surface_rect)
            return surface_path

        radius = min(
            float(self._metrics.corner_radius),
            surface_rect.width(),
            surface_rect.height() / 2,
        )
        surface_path.moveTo(surface_rect.left(), surface_rect.top())
        surface_path.lineTo(surface_rect.right() - radius, surface_rect.top())
        surface_path.quadTo(
            surface_rect.right(),
            surface_rect.top(),
            surface_rect.right(),
            surface_rect.top() + radius,
        )
        surface_path.lineTo(surface_rect.right(), surface_rect.bottom() - radius)
        surface_path.quadTo(
            surface_rect.right(),
            surface_rect.bottom(),
            surface_rect.right() - radius,
            surface_rect.bottom(),
        )
        surface_path.lineTo(surface_rect.left(), surface_rect.bottom())
        surface_path.closeSubpath()
        return surface_path

    def paintEvent(self, event) -> None:
        if not self._overlay_surface:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setClipPath(self._overlay_surface_path())

        painter.fillRect(self.rect(), QColor(self._theme.watercolor_base))
        parent = self.parentWidget()
        surface_width = parent.width() if parent is not None else self.width()
        for color, x, y, radius in self._theme.watercolor_spots:
            gradient = QRadialGradient(
                surface_width * x,
                self.height() * y,
                surface_width * radius,
            )
            gradient.setColorAt(0, QColor(color))
            gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self.rect())

        if not self._collapsed:
            border_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            radius = min(
                max(0.0, float(self._metrics.corner_radius) - 0.5),
                border_rect.width(),
                border_rect.height() / 2,
            )
            border_path = QPainterPath()
            border_path.moveTo(border_rect.left(), border_rect.top())
            border_path.lineTo(border_rect.right() - radius, border_rect.top())
            border_path.quadTo(
                border_rect.right(),
                border_rect.top(),
                border_rect.right(),
                border_rect.top() + radius,
            )
            border_path.lineTo(border_rect.right(), border_rect.bottom() - radius)
            border_path.quadTo(
                border_rect.right(),
                border_rect.bottom(),
                border_rect.right() - radius,
                border_rect.bottom(),
            )
            border_path.lineTo(border_rect.left(), border_rect.bottom())
            painter.setClipping(False)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(self._theme.border), 1))
            painter.drawPath(border_path)

    def setCollapsed(self, collapsed: bool, *, animated: bool = True) -> None:
        target = self._collapsed_width if collapsed else self._expanded_width
        animations = (self._min_animation, self._max_animation)
        if collapsed == self._collapsed:
            if not animated:
                for animation in animations:
                    animation.stop()
                self.setFixedWidth(target)
            return
        self._collapsed = collapsed
        self.scrollArea.setViewportMargins(
            0,
            0,
            -_SIDEBAR_SCROLLBAR_WIDTH if collapsed else 0,
            0,
        )
        for item in self._items:
            item.setCollapsed(collapsed)
            item._set_compact_width(self._compact_item_width if collapsed else None)
        if not animated:
            for animation in animations:
                animation.stop()
            self.setFixedWidth(target)
        else:
            start = self.width()
            for animation in animations:
                animation.stop()
                animation.setStartValue(start)
                animation.setEndValue(target)
                animation.start()
        self.collapsedChanged.emit(collapsed)

    def toggle(self) -> None:
        collapsed = not self._collapsed
        self.collapseIntentChanged.emit(collapsed)
        self.setCollapsed(collapsed)

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
