"""WinUI-inspired tabs with custom painting and QTabWidget-like APIs."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


THEME = {
    "tab_height": 38,
    "tab_max_width": 200,
    "tab_min_width": 80,
    "bar_bg": "#F3F3F3",
    "tab_hover": "#EAEAEA",
    "tab_selected": "#FFFFFF",
    "text_normal": "#454545",
    "text_selected": "#000000",
    "divider": "#D1D1D1",
    "border_selected": "#E5E5E5",
    "radius": 5,
    "font_family": "Segoe UI Variable Text, Segoe UI, Microsoft YaHei UI",
}


class _CloseButton(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self._hovered = False

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        background_rect = rect.adjusted(3, 3, -3, -3)

        if self._hovered:
            color = QColor("#D0D0D0" if self.isDown() else "#E0E0E0")
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(background_rect, 3, 3)

        pen = QPen(QColor("#111111"), 1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        center = rect.center()
        radius = 3.5
        painter.drawLine(
            QPointF(center.x() - radius, center.y() - radius),
            QPointF(center.x() + radius, center.y() + radius),
        )
        painter.drawLine(
            QPointF(center.x() + radius, center.y() - radius),
            QPointF(center.x() - radius, center.y() + radius),
        )


class _Tab(QWidget):
    clicked = Signal()
    closeRequested = Signal()
    dragMoved = Signal(QPoint)

    def __init__(
        self,
        text: str,
        icon: QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedHeight(THEME["tab_height"])
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setMouseTracking(True)

        self._selected = False
        self._hovered = False
        self._last_tab = False
        self._closable = True
        self._dragging = False
        self._text = text
        self._icon = icon or QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_FileIcon
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 2, 4)
        layout.setSpacing(6)

        self.iconLabel = QLabel(self)
        self.iconLabel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.iconLabel.setFixedSize(16, 16)
        layout.addWidget(self.iconLabel)

        self.textLabel = QLabel(self)
        self.textLabel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.textLabel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        layout.addWidget(self.textLabel)

        self.closeButton = _CloseButton(self)
        self.closeButton.clicked.connect(self.closeRequested.emit)
        layout.addWidget(self.closeButton)

        self.setText(text)
        self.setIcon(self._icon)
        self._update_ui_state()

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:  # noqa: N802
        self._text = text
        self.setToolTip(text)
        self.textLabel.setText(text)

    def icon(self) -> QIcon:
        return self._icon

    def setIcon(self, icon: QIcon | None) -> None:  # noqa: N802
        self._icon = icon or QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_FileIcon
        )
        self.iconLabel.setPixmap(self._icon.pixmap(QSize(16, 16)))

    def setSelected(self, selected: bool) -> None:  # noqa: N802
        self._selected = selected
        self._update_ui_state()
        self.update()

    def setLastTab(self, last: bool) -> None:  # noqa: N802
        self._last_tab = last
        self.update()

    def setClosable(self, closable: bool) -> None:  # noqa: N802
        self._closable = closable
        self._update_ui_state()

    def _update_ui_state(self) -> None:
        self.closeButton.setVisible(
            self._closable and (self._selected or self._hovered)
        )
        color = (
            THEME["text_selected"] if self._selected else THEME["text_normal"]
        )
        weight = 600 if self._selected else 400
        self.textLabel.setStyleSheet(
            f"color: {color}; font-family: '{THEME['font_family']}'; "
            f"font-size: 12px; font-weight: {weight};"
        )

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self._update_ui_state()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self._update_ui_state()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self.clicked.emit()
        elif event.button() == Qt.MouseButton.MiddleButton and self._closable:
            self.closeRequested.emit()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.dragMoved.emit(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._dragging = False
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        if self._selected:
            draw_rect = QRectF(rect).adjusted(0.5, 0.5, -0.5, 0)
            radius = THEME["radius"]
            path = QPainterPath()
            path.moveTo(draw_rect.bottomLeft())
            path.lineTo(draw_rect.topLeft() + QPointF(0, radius))
            path.quadTo(
                draw_rect.topLeft(),
                draw_rect.topLeft() + QPointF(radius, 0),
            )
            path.lineTo(draw_rect.topRight() - QPointF(radius, 0))
            path.quadTo(
                draw_rect.topRight(),
                draw_rect.topRight() + QPointF(0, radius),
            )
            path.lineTo(draw_rect.bottomRight())
            path.closeSubpath()

            painter.setBrush(QBrush(QColor(THEME["tab_selected"])))
            painter.setPen(QPen(QColor(THEME["border_selected"]), 1))
            painter.drawPath(path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(THEME["tab_selected"])))
            painter.drawRect(0, self.height() - 2, self.width(), 2)
        elif self._hovered:
            hover_rect = rect.adjusted(3, 3, -3, -3)
            painter.setBrush(QBrush(QColor(THEME["tab_hover"])))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(hover_rect, THEME["radius"], THEME["radius"])

        if not self._selected and not self._hovered and not self._last_tab:
            painter.setPen(QPen(QColor(THEME["divider"]), 1))
            painter.drawLine(
                self.width() - 1,
                10,
                self.width() - 1,
                self.height() - 10,
            )


class _ScrollButton(QToolButton):
    def __init__(self, direction: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._direction = direction
        self.setFixedSize(24, THEME["tab_height"])
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            "QToolButton { background: transparent; border: none; }"
            f"QToolButton:hover {{ background: {THEME['tab_hover']}; "
            "border-radius: 4px; }"
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#444444"), 1.2))
        center = QRectF(self.rect()).center()
        offset = 2
        if self._direction == "left":
            painter.drawLine(
                QPointF(center.x() + offset, center.y() - 4),
                QPointF(center.x() - offset, center.y()),
            )
            painter.drawLine(
                QPointF(center.x() - offset, center.y()),
                QPointF(center.x() + offset, center.y() + 4),
            )
        else:
            painter.drawLine(
                QPointF(center.x() - offset, center.y() - 4),
                QPointF(center.x() + offset, center.y()),
            )
            painter.drawLine(
                QPointF(center.x() + offset, center.y()),
                QPointF(center.x() - offset, center.y() + 4),
            )


class _TabBar(QWidget):
    tabClicked = Signal(int)
    tabCloseRequested = Signal(int)
    tabMoved = Signal(int, int)
    addClicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(THEME["tab_height"] + 2)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(THEME["bar_bg"]))
        self.setPalette(palette)

        self._tabs: list[_Tab] = []
        self._current_index = -1
        self._tabs_closable = True
        self._movable = True

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)

        self.leftButton = _ScrollButton("left", self)
        self.leftButton.clicked.connect(lambda: self._scroll_smooth(-200))
        layout.addWidget(self.leftButton)

        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scrollArea.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scrollArea.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.scrollArea.setStyleSheet("QScrollArea { background: transparent; }")

        self.tabsContainer = QWidget(self.scrollArea)
        self.tabsContainer.setStyleSheet("background: transparent;")
        self.tabsLayout = QHBoxLayout(self.tabsContainer)
        self.tabsLayout.setContentsMargins(0, 0, 0, 0)
        self.tabsLayout.setSpacing(0)
        self.tabsLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.tabsLayout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.scrollArea.setWidget(self.tabsContainer)
        layout.addWidget(self.scrollArea)

        self.rightButton = _ScrollButton("right", self)
        self.rightButton.clicked.connect(lambda: self._scroll_smooth(200))
        layout.addWidget(self.rightButton)

        self.addButton = QToolButton(self)
        self.addButton.setText("+")
        self.addButton.setToolTip("New tab")
        self.addButton.setFixedSize(34, 32)
        self.addButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.addButton.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.addButton.setStyleSheet(
            "QToolButton { border: none; border-radius: 4px; color: #444444; "
            "background: transparent; font-size: 18px; margin-left: 2px; "
            "margin-top: 1px; }"
            f"QToolButton:hover {{ background: {THEME['tab_hover']}; }}"
        )
        self.addButton.clicked.connect(self.addClicked.emit)
        layout.addWidget(self.addButton)

        self._scroll_animation = QPropertyAnimation(
            self.scrollArea.horizontalScrollBar(),
            b"value",
            self,
        )
        self._scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_animation.setDuration(300)

        scroll_bar = self.scrollArea.horizontalScrollBar()
        scroll_bar.rangeChanged.connect(self._update_scroll_buttons)
        scroll_bar.valueChanged.connect(self._update_scroll_buttons)
        self.leftButton.hide()
        self.rightButton.hide()

    def count(self) -> int:
        return len(self._tabs)

    def tabAt(self, position: QPoint) -> int:  # noqa: N802
        for index, tab in enumerate(self._tabs):
            top_left = tab.mapTo(self, QPoint(0, 0))
            if QRect(top_left, tab.size()).contains(position):
                return index
        return -1

    def tabText(self, index: int) -> str:  # noqa: N802
        tab = self._tab(index)
        return tab.text() if tab is not None else ""

    def setTabText(self, index: int, text: str) -> None:  # noqa: N802
        tab = self._tab(index)
        if tab is not None:
            tab.setText(text)

    def tabIcon(self, index: int) -> QIcon:  # noqa: N802
        tab = self._tab(index)
        return tab.icon() if tab is not None else QIcon()

    def setTabIcon(self, index: int, icon: QIcon) -> None:  # noqa: N802
        tab = self._tab(index)
        if tab is not None:
            tab.setIcon(icon)

    def tabToolTip(self, index: int) -> str:  # noqa: N802
        tab = self._tab(index)
        return tab.toolTip() if tab is not None else ""

    def setTabToolTip(self, index: int, tooltip: str) -> None:  # noqa: N802
        tab = self._tab(index)
        if tab is not None:
            tab.setToolTip(tooltip)

    def isTabEnabled(self, index: int) -> bool:  # noqa: N802
        tab = self._tab(index)
        return tab.isEnabled() if tab is not None else False

    def setTabEnabled(self, index: int, enabled: bool) -> None:  # noqa: N802
        tab = self._tab(index)
        if tab is not None:
            tab.setEnabled(enabled)

    def insertTab(  # noqa: N802
        self,
        index: int,
        text: str,
        icon: QIcon | None = None,
    ) -> int:
        index = max(0, min(index, self.count()))
        tab = _Tab(text, icon, self.tabsContainer)
        tab.setClosable(self._tabs_closable)
        self._tabs.insert(index, tab)
        self.tabsLayout.insertWidget(index, tab)
        tab.clicked.connect(lambda target=tab: self._activate_tab(target))
        tab.closeRequested.connect(lambda target=tab: self._request_close(target))
        tab.dragMoved.connect(lambda position, target=tab: self._move_dragged_tab(target, position))
        self._recalculate_tab_widths()
        QTimer.singleShot(0, self._recalculate_tab_widths)
        QTimer.singleShot(0, self._update_scroll_buttons)
        return index

    def removeTab(self, index: int) -> None:  # noqa: N802
        tab = self._tab(index)
        if tab is None:
            return
        self._tabs.pop(index)
        self.tabsLayout.removeWidget(tab)
        tab.deleteLater()
        if not self._tabs:
            self._current_index = -1
        elif index < self._current_index:
            self._current_index -= 1
        elif index == self._current_index:
            self._current_index = min(index, len(self._tabs) - 1)
        self._recalculate_tab_widths()
        self.setCurrentIndex(self._current_index)
        QTimer.singleShot(0, self._update_scroll_buttons)

    def currentIndex(self) -> int:  # noqa: N802
        return self._current_index

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        self._current_index = index if 0 <= index < self.count() else -1
        for tab_index, tab in enumerate(self._tabs):
            tab.setSelected(tab_index == self._current_index)
        if self._current_index >= 0:
            QTimer.singleShot(
                0,
                lambda: self._ensure_visible(self._tabs[self._current_index])
                if 0 <= self._current_index < self.count()
                else None,
            )

    def setTabsClosable(self, closable: bool) -> None:  # noqa: N802
        self._tabs_closable = closable
        for tab in self._tabs:
            tab.setClosable(closable)

    def tabsClosable(self) -> bool:  # noqa: N802
        return self._tabs_closable

    def setMovable(self, movable: bool) -> None:  # noqa: N802
        self._movable = movable

    def isMovable(self) -> bool:  # noqa: N802
        return self._movable

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._recalculate_tab_widths()
        QTimer.singleShot(0, self._recalculate_tab_widths)
        if 0 <= self._current_index < self.count():
            QTimer.singleShot(
                0,
                lambda: self._ensure_visible(self._tabs[self._current_index]),
            )

    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = event.angleDelta().y() or event.angleDelta().x()
        if delta:
            self._scroll_smooth(-delta)
            event.accept()
            return
        super().wheelEvent(event)

    def _tab(self, index: int) -> _Tab | None:
        return self._tabs[index] if 0 <= index < self.count() else None

    def _activate_tab(self, tab: _Tab) -> None:
        if tab in self._tabs and tab.isEnabled():
            self.tabClicked.emit(self._tabs.index(tab))

    def _request_close(self, tab: _Tab) -> None:
        if tab in self._tabs and self._tabs_closable:
            self.tabCloseRequested.emit(self._tabs.index(tab))

    def _move_dragged_tab(self, tab: _Tab, global_position: QPoint) -> None:
        if not self._movable or tab not in self._tabs:
            return
        old_index = self._tabs.index(tab)
        local_position = self.mapFromGlobal(global_position)
        new_index = self.tabAt(local_position)
        if new_index < 0 or new_index == old_index:
            return
        self._tabs.pop(old_index)
        self._tabs.insert(new_index, tab)
        self.tabsLayout.removeWidget(tab)
        self.tabsLayout.insertWidget(new_index, tab)
        self._current_index = new_index if self._current_index == old_index else self._current_index
        self._update_separators()
        self.tabMoved.emit(old_index, new_index)

    def _recalculate_tab_widths(self) -> None:
        if not self._tabs:
            return
        viewport_width = max(1, self.scrollArea.viewport().width())
        ideal_width = viewport_width // len(self._tabs)
        width = max(
            THEME["tab_min_width"],
            min(THEME["tab_max_width"], ideal_width),
        )
        for tab in self._tabs:
            tab.setFixedWidth(width)
        self.tabsContainer.adjustSize()
        self._update_separators()

    def _update_separators(self) -> None:
        for index, tab in enumerate(self._tabs):
            tab.setLastTab(index == self.count() - 1)

    def _update_scroll_buttons(self) -> None:
        scroll_bar = self.scrollArea.horizontalScrollBar()
        self.leftButton.setVisible(scroll_bar.value() > 0)
        self.rightButton.setVisible(
            scroll_bar.maximum() > 0
            and scroll_bar.value() < scroll_bar.maximum() - 2
        )

    def _scroll_smooth(self, delta: int) -> None:
        scroll_bar = self.scrollArea.horizontalScrollBar()
        self._scroll_animation.stop()
        self._scroll_animation.setStartValue(scroll_bar.value())
        self._scroll_animation.setEndValue(scroll_bar.value() + delta)
        self._scroll_animation.start()

    def _ensure_visible(self, tab: _Tab) -> None:
        scroll_bar = self.scrollArea.horizontalScrollBar()
        position = tab.pos().x()
        width = tab.width()
        viewport_width = self.scrollArea.viewport().width()
        value = scroll_bar.value()
        if position < value:
            self._scroll_smooth(position - value - 5)
        elif position + width > value + viewport_width:
            self._scroll_smooth(position + width - value - viewport_width + 10)


class TabView(QWidget):
    """A custom-painted tab view with selected QTabWidget-compatible APIs."""

    currentChanged = Signal(int)
    tabCloseRequested = Signal(int)
    tabMoved = Signal(int, int)
    addTabClicked = Signal()

    THEME = THEME

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._document_mode = True
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_bar = _TabBar(self)
        layout.addWidget(self._tab_bar)

        self._divider = QFrame(self)
        self._divider.setFixedHeight(1)
        self._divider.setStyleSheet(
            f"QFrame {{ background-color: {THEME['border_selected']}; border: none; }}"
        )
        layout.addWidget(self._divider)

        self._stack = QStackedWidget(self)
        self._stack.setStyleSheet("QStackedWidget { background: #FFFFFF; }")
        layout.addWidget(self._stack, 1)

        self._tab_bar.tabClicked.connect(self.setCurrentIndex)
        self._tab_bar.tabCloseRequested.connect(self.tabCloseRequested.emit)
        self._tab_bar.tabMoved.connect(self._move_page)
        self._tab_bar.tabMoved.connect(self.tabMoved.emit)
        self._tab_bar.addClicked.connect(self.addTabClicked.emit)
        self._stack.currentChanged.connect(self._stack_current_changed)
        self._setup_shortcuts()

    def addTab(self, widget: QWidget, *args) -> int:  # noqa: N802
        return self.insertTab(self.count(), widget, *args)

    def insertTab(self, index: int, widget: QWidget, *args) -> int:  # noqa: N802
        icon, text = self._parse_tab_arguments(args)
        index = max(0, min(index, self.count()))
        self._tab_bar.insertTab(index, text, icon)
        inserted_index = self._stack.insertWidget(index, widget)
        self._sync_current_state()
        return inserted_index

    def removeTab(self, index: int) -> None:  # noqa: N802
        page = self.widget(index)
        if page is None:
            return
        old_index = self.currentIndex()
        old_widget = self.currentWidget()
        self._syncing = True
        self._tab_bar.removeTab(index)
        self._stack.removeWidget(page)
        if old_widget is page and self.count():
            self._stack.setCurrentIndex(min(index, self.count() - 1))
        elif old_widget is not None:
            new_index = self._stack.indexOf(old_widget)
            if new_index >= 0:
                self._stack.setCurrentIndex(new_index)
        self._syncing = False
        current_changed = (
            old_index != self.currentIndex()
            or old_widget is not self.currentWidget()
        )
        self._sync_current_state(emit=current_changed)

    def clear(self) -> None:
        while self.count():
            self.removeTab(self.count() - 1)

    def count(self) -> int:
        return self._stack.count()

    def widget(self, index: int) -> QWidget | None:
        return self._stack.widget(index)

    def indexOf(self, widget: QWidget) -> int:  # noqa: N802
        return self._stack.indexOf(widget)

    def currentWidget(self) -> QWidget | None:  # noqa: N802
        return self._stack.currentWidget()

    def currentIndex(self) -> int:  # noqa: N802
        return self._stack.currentIndex()

    def setCurrentWidget(self, widget: QWidget) -> None:  # noqa: N802
        index = self.indexOf(widget)
        if index >= 0:
            self.setCurrentIndex(index)

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        if not 0 <= index < self.count() or not self.isTabEnabled(index):
            return
        self._stack.setCurrentIndex(index)
        self._sync_current_state()

    def tabBar(self) -> _TabBar:  # noqa: N802
        return self._tab_bar

    def tabText(self, index: int) -> str:  # noqa: N802
        return self._tab_bar.tabText(index)

    def setTabText(self, index: int, text: str) -> None:  # noqa: N802
        self._tab_bar.setTabText(index, text)

    def tabIcon(self, index: int) -> QIcon:  # noqa: N802
        return self._tab_bar.tabIcon(index)

    def setTabIcon(self, index: int, icon: QIcon) -> None:  # noqa: N802
        self._tab_bar.setTabIcon(index, icon)

    def tabToolTip(self, index: int) -> str:  # noqa: N802
        return self._tab_bar.tabToolTip(index)

    def setTabToolTip(self, index: int, tooltip: str) -> None:  # noqa: N802
        self._tab_bar.setTabToolTip(index, tooltip)

    def isTabEnabled(self, index: int) -> bool:  # noqa: N802
        return self._tab_bar.isTabEnabled(index)

    def setTabEnabled(self, index: int, enabled: bool) -> None:  # noqa: N802
        self._tab_bar.setTabEnabled(index, enabled)

    def setTabsClosable(self, closable: bool) -> None:  # noqa: N802
        self._tab_bar.setTabsClosable(closable)

    def tabsClosable(self) -> bool:  # noqa: N802
        return self._tab_bar.tabsClosable()

    def setMovable(self, movable: bool) -> None:  # noqa: N802
        self._tab_bar.setMovable(movable)

    def isMovable(self) -> bool:  # noqa: N802
        return self._tab_bar.isMovable()

    def setDocumentMode(self, enabled: bool) -> None:  # noqa: N802
        self._document_mode = enabled

    def documentMode(self) -> bool:  # noqa: N802
        return self._document_mode

    def nextTab(self) -> None:
        if self.count():
            self.setCurrentIndex((self.currentIndex() + 1) % self.count())

    def previousTab(self) -> None:
        if self.count():
            self.setCurrentIndex((self.currentIndex() - 1) % self.count())

    def prevTab(self) -> None:
        self.previousTab()

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+T"), self, self.addTabClicked.emit)
        QShortcut(QKeySequence("Ctrl+W"), self, self._request_current_close)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self.nextTab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self.previousTab)

    def _request_current_close(self) -> None:
        if self.currentIndex() >= 0 and self.tabsClosable():
            self.tabCloseRequested.emit(self.currentIndex())

    def _stack_current_changed(self, index: int) -> None:
        if self._syncing:
            return
        self._tab_bar.setCurrentIndex(index)
        self.currentChanged.emit(index)

    def _sync_current_state(self, *, emit: bool = False) -> None:
        index = self._stack.currentIndex()
        self._tab_bar.setCurrentIndex(index)
        if emit:
            self.currentChanged.emit(index)

    def _move_page(self, old_index: int, new_index: int) -> None:
        page = self.widget(old_index)
        current_page = self.currentWidget()
        if page is None:
            return
        self._syncing = True
        self._stack.removeWidget(page)
        self._stack.insertWidget(new_index, page)
        if current_page is not None:
            self._stack.setCurrentWidget(current_page)
        self._syncing = False
        self._sync_current_state()

    @staticmethod
    def _parse_tab_arguments(args: tuple) -> tuple[QIcon | None, str]:
        if len(args) == 1:
            return None, str(args[0])
        if len(args) == 2:
            first, second = args
            if isinstance(first, QIcon):
                return first, str(second)
            if isinstance(second, QIcon):
                return second, str(first)
        raise TypeError(
            "addTab/insertTab expects (widget, text), (widget, icon, text), "
            "or (widget, text, icon)"
        )
