"""WinUI-inspired tabs built on Qt's native tab semantics."""

from __future__ import annotations

from typing import cast

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QHBoxLayout,
    QProxyStyle,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    palette_for_theme,
    theme_manager,
)


class _ModernTabBarStyle(QProxyStyle):
    def pixelMetric(self, metric, option=None, widget=None) -> int:
        if metric == QStyle.PixelMetric.PM_TabBarScrollButtonWidth:
            return 28
        return super().pixelMetric(metric, option, widget)


class _TabCloseButton(QAbstractButton):
    def __init__(
        self,
        theme: ModernTheme,
        metrics: ModernMetrics,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._metrics = metrics
        self.setFixedSize(24, 24)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setTheme(self, theme: ModernTheme) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        background_rect = rect.adjusted(3, 3, -3, -3)

        if self.isEnabled() and self.underMouse():
            painter.setBrush(
                QColor(self._theme.control_pressed if self.isDown() else self._theme.control_hover)
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(
                background_rect,
                self._metrics.control_radius,
                self._metrics.control_radius,
            )

        painter.setPen(
            QPen(
                QColor(self._theme.text if self.isEnabled() else self._theme.text_disabled),
                1.2,
            )
        )
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

        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(self._theme.focus), 1))
            painter.drawRoundedRect(
                rect.adjusted(1, 1, -1, -1),
                self._metrics.control_radius,
                self._metrics.control_radius,
            )


class _ModernTabBar(QTabBar):
    def __init__(
        self,
        theme: ModernTheme,
        metrics: ModernMetrics,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._metrics = metrics
        self._hovered_index = -1
        self._keyboard_focus_visible = False
        self._modern_style = _ModernTabBarStyle()
        self.setStyle(self._modern_style)
        self.setObjectName("ModernTabBar")
        self.setAccessibleName("Document tabs")
        self.setDrawBase(False)
        self.setDocumentMode(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setExpanding(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMovable(True)
        self.setMouseTracking(True)
        self.setTabsClosable(True)
        self.setUsesScrollButtons(True)
        self.setMinimumHeight(self._tab_height() + 2)
        self._configure_scroll_buttons()
        self.currentChanged.connect(self._update_close_buttons)

    def setTheme(self, theme: ModernTheme) -> None:
        self._theme = theme
        self._configure_scroll_buttons()
        for index in range(self.count()):
            button = self._close_button(index)
            if button is not None:
                button.setTheme(theme)
        self.update()

    def _configure_scroll_buttons(self) -> None:
        labels = {
            "ScrollLeftButton": "Previous tabs",
            "ScrollRightButton": "Next tabs",
        }
        for object_name, label in labels.items():
            button = self.findChild(QToolButton, object_name)
            if button is not None:
                button.installEventFilter(self)
                button.setAccessibleName(label)
                button.setToolTip(label)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                button.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
                button.update()

    def eventFilter(self, watched, event) -> bool:
        if (
            event.type() == QEvent.Type.Paint
            and isinstance(watched, QToolButton)
            and watched.objectName() in ("ScrollLeftButton", "ScrollRightButton")
        ):
            self._paint_scroll_button(watched)
            return True
        return super().eventFilter(watched, event)

    def _paint_scroll_button(self, button: QToolButton) -> None:
        painter = QPainter(button)
        rect = QRectF(button.rect())
        painter.fillRect(button.rect(), QColor(self._theme.tab_bar))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if button.isEnabled() and button.underMouse():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(
                QColor(
                    self._theme.control_pressed if button.isDown() else self._theme.control_hover
                )
            )
            painter.drawRoundedRect(
                rect.adjusted(3, 5, -3, -5),
                self._metrics.control_radius,
                self._metrics.control_radius,
            )

        color = self._theme.text if button.isEnabled() else self._theme.text_disabled
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(
            QPen(
                QColor(color),
                1.5,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        center = rect.center()
        direction = -1 if button.objectName() == "ScrollLeftButton" else 1
        path = QPainterPath()
        path.moveTo(center.x() - direction * 2, center.y() - 4)
        path.lineTo(center.x() + direction * 2, center.y())
        path.lineTo(center.x() - direction * 2, center.y() + 4)
        painter.drawPath(path)

    def tabSizeHint(self, index: int) -> QSize:
        count = max(1, self.count())
        ideal_width = self.width() // count
        width = max(
            self._metrics.tab_min_width,
            min(self._metrics.tab_max_width, ideal_width),
        )
        return QSize(width, self._tab_height())

    def minimumTabSizeHint(self, index: int) -> QSize:
        return QSize(self._metrics.tab_min_width, self._tab_height())

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:
            self.setMinimumHeight(self._tab_height() + 2)
            self.updateGeometry()

    def _tab_height(self) -> int:
        return max(self._metrics.tab_height, self.fontMetrics().height() + 12)

    def setTabsClosable(self, closable: bool) -> None:
        if closable == self.tabsClosable():
            return
        super().setTabsClosable(closable)
        for index in range(self.count()):
            self._install_close_button(index) if closable else self._remove_close_button(index)
        self._update_close_buttons()

    def tabInserted(self, index: int) -> None:
        super().tabInserted(index)
        if self.tabsClosable():
            self._install_close_button(index)
        self._update_accessible_names()
        self._update_close_buttons()

    def tabRemoved(self, index: int) -> None:
        super().tabRemoved(index)
        self._update_accessible_names()
        self._update_close_buttons()

    def mouseMoveEvent(self, event) -> None:
        hovered_index = self.tabAt(event.position().toPoint())
        if hovered_index != self._hovered_index:
            self._hovered_index = hovered_index
            self._update_close_buttons()
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        self._keyboard_focus_visible = False
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton and self.tabsClosable():
            index = self.tabAt(event.position().toPoint())
            if index >= 0:
                self.tabCloseRequested.emit(index)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        self._keyboard_focus_visible = True
        self.update()
        super().keyPressEvent(event)

    def focusInEvent(self, event) -> None:
        self._keyboard_focus_visible = event.reason() in (
            Qt.FocusReason.TabFocusReason,
            Qt.FocusReason.BacktabFocusReason,
            Qt.FocusReason.ShortcutFocusReason,
        )
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._keyboard_focus_visible = False
        self.update()
        super().focusOutEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered_index = -1
        self._update_close_buttons()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(self._theme.tab_bar))

        scroll_buttons = [
            button
            for object_name in ("ScrollLeftButton", "ScrollRightButton")
            if (button := self.findChild(QToolButton, object_name)) is not None
        ]
        overflowed = self.count() > 0 and (
            self.tabRect(0).left() < 0 or self.tabRect(self.count() - 1).right() >= self.width()
        )
        painter.save()
        if scroll_buttons and (overflowed or any(button.isVisible() for button in scroll_buttons)):
            controls_left = min(button.geometry().left() for button in scroll_buttons)
            painter.setClipRect(
                QRectF(0, 0, controls_left, self.height()),
                Qt.ClipOperation.IntersectClip,
            )

        for index in range(self.count()):
            rect = self.tabRect(index)
            selected = index == self.currentIndex()
            hovered = index == self._hovered_index
            enabled = self.isTabEnabled(index)

            if selected:
                draw_rect = QRectF(rect).adjusted(0.5, 0.5, -0.5, 0)
                radius = self._metrics.control_radius + 1
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
                painter.setBrush(QColor(self._theme.tab_selected))
                painter.setPen(QPen(QColor(self._theme.border), 1))
                painter.drawPath(path)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(rect.left(), self.height() - 2, rect.width(), 2)
            elif hovered and enabled:
                painter.setBrush(QColor(self._theme.tab_hover))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(
                    rect.adjusted(3, 3, -3, -3),
                    self._metrics.control_radius + 1,
                    self._metrics.control_radius + 1,
                )
            elif index < self.count() - 1:
                painter.setPen(QPen(QColor(self._theme.tab_divider), 1))
                painter.drawLine(
                    rect.right(),
                    rect.top() + 10,
                    rect.right(),
                    rect.bottom() - 10,
                )

            self._paint_tab_label(painter, index, rect, selected, enabled)
            if self.hasFocus() and self._keyboard_focus_visible and selected:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(self._theme.focus), 1))
                painter.drawRoundedRect(
                    rect.adjusted(2, 2, -2, -2),
                    self._metrics.control_radius,
                    self._metrics.control_radius,
                )
        painter.restore()

    def _paint_tab_label(
        self,
        painter: QPainter,
        index: int,
        rect,
        selected: bool,
        enabled: bool,
    ) -> None:
        close_button = self._close_button(index)
        close_width = 26 if close_button is not None and close_button.isVisible() else 2
        logical_rect = rect.adjusted(8, 4, -close_width, -4)
        content_rect = self.style().visualRect(
            self.layoutDirection(),
            rect,
            logical_rect,
        )
        icon = self.tabIcon(index)
        icon_size = QSize(16, 16)
        if not icon.isNull():
            icon_rect = QRectF(
                content_rect.left(),
                content_rect.center().y() - 8,
                16,
                16,
            )
            mode = QIcon.Mode.Normal if enabled else QIcon.Mode.Disabled
            painter.drawPixmap(icon_rect.toRect(), icon.pixmap(icon_size, mode))
            content_rect.adjust(22, 0, 0, 0)

        font = QFont(self.font())
        font.setWeight(QFont.Weight.DemiBold if selected else QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(
            QColor(
                self._theme.text_disabled
                if not enabled
                else self._theme.text
                if selected
                else self._theme.text_muted
            )
        )
        text = painter.fontMetrics().elidedText(
            self.tabText(index),
            Qt.TextElideMode.ElideRight,
            max(0, content_rect.width()),
        )
        painter.drawText(
            content_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            text,
        )

    def _install_close_button(self, index: int) -> None:
        self._remove_close_button(index)
        button = _TabCloseButton(self._theme, self._metrics, self)
        button.setAccessibleName(f"Close {self.tabText(index)}")
        button.clicked.connect(lambda _checked=False, target=button: self._request_close(target))
        self.setTabButton(index, QTabBar.ButtonPosition.RightSide, button)

    def _remove_close_button(self, index: int) -> None:
        button = self._close_button(index)
        if button is not None:
            self.setTabButton(
                index,
                QTabBar.ButtonPosition.RightSide,
                cast(QWidget, None),
            )
            button.deleteLater()

    def _close_button(self, index: int) -> _TabCloseButton | None:
        button = self.tabButton(index, QTabBar.ButtonPosition.RightSide)
        return button if isinstance(button, _TabCloseButton) else None

    def _request_close(self, button: _TabCloseButton) -> None:
        for index in range(self.count()):
            if self._close_button(index) is button:
                self.tabCloseRequested.emit(index)
                return

    def _update_accessible_names(self) -> None:
        for index in range(self.count()):
            button = self._close_button(index)
            if button is not None:
                button.setAccessibleName(f"Close {self.tabText(index)}")

    def _update_close_buttons(self, *_args) -> None:
        for index in range(self.count()):
            button = self._close_button(index)
            if button is not None:
                button.setVisible(
                    self.tabsClosable()
                    and (index == self.currentIndex() or index == self._hovered_index)
                )


class TabView(QWidget):
    """A themeable tab view backed by ``QTabBar`` and ``QStackedWidget``."""

    currentChanged = Signal(int)
    tabCloseRequested = Signal(int)
    tabMoved = Signal(int, int)
    addTabClicked = Signal()

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
        self._syncing = False
        theme_manager().themeChanged.connect(self._on_global_theme_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_row = QWidget(self)
        self._tab_row.setObjectName("ModernTabRow")
        tab_layout = QHBoxLayout(self._tab_row)
        tab_layout.setContentsMargins(4, 0, 4, 0)
        tab_layout.setSpacing(0)

        self._tab_bar = _ModernTabBar(self._theme, self._metrics, self._tab_row)
        tab_layout.addWidget(self._tab_bar, 1)

        self._add_button = QToolButton(self._tab_row)
        self._add_button.setObjectName("ModernTabAddButton")
        self._add_button.setText("+")
        self._add_button.setToolTip("New tab")
        self._add_button.setAccessibleName("New tab")
        self._add_button.setFixedSize(34, 32)
        self._add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._add_button.clicked.connect(self.addTabClicked.emit)
        tab_layout.addWidget(self._add_button)
        layout.addWidget(self._tab_row)

        self._stack = QStackedWidget(self)
        self._stack.setObjectName("ModernTabStack")
        layout.addWidget(self._stack, 1)

        self._tab_bar.currentChanged.connect(self._tab_current_changed)
        self._tab_bar.tabCloseRequested.connect(self.tabCloseRequested.emit)
        self._tab_bar.tabMoved.connect(self._move_page)
        self._tab_bar.tabMoved.connect(self.tabMoved.emit)
        self._stack.currentChanged.connect(self._stack_current_changed)
        self._setup_shortcuts()
        self._apply_theme()

    def addTab(
        self,
        widget: QWidget,
        icon_or_text: QIcon | str,
        text: str | None = None,
    ) -> int:
        return self.insertTab(self.count(), widget, icon_or_text, text)

    def insertTab(
        self,
        index: int,
        widget: QWidget,
        icon_or_text: QIcon | str,
        text: str | None = None,
    ) -> int:
        icon, label = self._parse_tab_arguments(icon_or_text, text)
        index = max(0, min(index, self.count()))
        old_widget = self.currentWidget()
        self._syncing = True
        page_index = self._stack.insertWidget(index, widget)
        tab_index = self._tab_bar.insertTab(index, icon, label)
        self._tab_bar.setTabToolTip(tab_index, label)
        if old_widget is not None:
            self._stack.setCurrentWidget(old_widget)
            self._tab_bar.setCurrentIndex(self._stack.currentIndex())
        else:
            self._stack.setCurrentIndex(tab_index)
            self._tab_bar.setCurrentIndex(tab_index)
        self._syncing = False
        return page_index

    def removeTab(self, index: int) -> None:
        page = self.widget(index)
        if page is None:
            return
        old_index = self.currentIndex()
        old_widget = self.currentWidget()
        self._syncing = True
        self._tab_bar.removeTab(index)
        self._stack.removeWidget(page)
        new_index = self._tab_bar.currentIndex()
        self._stack.setCurrentIndex(new_index)
        self._syncing = False
        if old_index != new_index or old_widget is not self.currentWidget():
            self.currentChanged.emit(new_index)

    def clear(self) -> None:
        while self.count():
            self.removeTab(self.count() - 1)

    def count(self) -> int:
        return self._stack.count()

    def widget(self, index: int) -> QWidget | None:
        return self._stack.widget(index)

    def indexOf(self, widget: QWidget) -> int:
        return self._stack.indexOf(widget)

    def currentWidget(self) -> QWidget | None:
        return self._stack.currentWidget()

    def currentIndex(self) -> int:
        return self._stack.currentIndex()

    def setCurrentWidget(self, widget: QWidget) -> None:
        index = self.indexOf(widget)
        if index >= 0:
            self.setCurrentIndex(index)

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < self.count() and self.isTabEnabled(index):
            self._tab_bar.setCurrentIndex(index)

    def tabBar(self) -> QTabBar:
        return self._tab_bar

    def tabText(self, index: int) -> str:
        return self._tab_bar.tabText(index)

    def setTabText(self, index: int, text: str) -> None:
        self._tab_bar.setTabText(index, text)
        self._tab_bar._update_accessible_names()

    def tabIcon(self, index: int) -> QIcon:
        return self._tab_bar.tabIcon(index)

    def setTabIcon(self, index: int, icon: QIcon) -> None:
        self._tab_bar.setTabIcon(index, icon)

    def tabToolTip(self, index: int) -> str:
        return self._tab_bar.tabToolTip(index)

    def setTabToolTip(self, index: int, tooltip: str) -> None:
        self._tab_bar.setTabToolTip(index, tooltip)

    def isTabEnabled(self, index: int) -> bool:
        return self._tab_bar.isTabEnabled(index)

    def setTabEnabled(self, index: int, enabled: bool) -> None:
        self._tab_bar.setTabEnabled(index, enabled)

    def setTabsClosable(self, closable: bool) -> None:
        self._tab_bar.setTabsClosable(closable)

    def tabsClosable(self) -> bool:
        return self._tab_bar.tabsClosable()

    def setMovable(self, movable: bool) -> None:
        self._tab_bar.setMovable(movable)

    def isMovable(self) -> bool:
        return self._tab_bar.isMovable()

    def setDocumentMode(self, enabled: bool) -> None:
        self._tab_bar.setDocumentMode(enabled)

    def documentMode(self) -> bool:
        return self._tab_bar.documentMode()

    def theme(self) -> ModernTheme:
        return self._theme

    def setTheme(self, theme: ModernTheme | None) -> None:
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self._apply_theme()

    def nextTab(self) -> None:
        self._select_relative_tab(1)

    def previousTab(self) -> None:
        self._select_relative_tab(-1)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence.StandardKey.AddTab, self, self.addTabClicked.emit)
        QShortcut(QKeySequence.StandardKey.Close, self, self._request_current_close)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self.nextTab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self.previousTab)

    def _request_current_close(self) -> None:
        if self.currentIndex() >= 0 and self.tabsClosable():
            self.tabCloseRequested.emit(self.currentIndex())

    def _select_relative_tab(self, direction: int) -> None:
        count = self.count()
        if not count:
            return
        start = self.currentIndex()
        for offset in range(1, count + 1):
            index = (start + direction * offset) % count
            if self.isTabEnabled(index):
                self.setCurrentIndex(index)
                return

    def _tab_current_changed(self, index: int) -> None:
        if self._syncing:
            return
        self._syncing = True
        self._stack.setCurrentIndex(index)
        self._syncing = False
        self.currentChanged.emit(index)

    def _stack_current_changed(self, index: int) -> None:
        if self._syncing:
            return
        self._tab_bar.setCurrentIndex(index)

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

    def _on_global_theme_changed(self, theme: ModernTheme) -> None:
        if self._uses_global_theme:
            self._theme = theme
            self._apply_theme()

    def _apply_theme(self) -> None:
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self._tab_bar.setTheme(self._theme)
        self._tab_row.setStyleSheet(
            f"QWidget#ModernTabRow {{ background: {self._theme.tab_bar}; }}"
        )
        self._add_button.setStyleSheet(
            f"""
            QToolButton#ModernTabAddButton {{
                border: none;
                border-radius: {self._metrics.control_radius}px;
                color: {self._theme.text_muted};
                background: transparent;
                font-size: 18px;
            }}
            QToolButton#ModernTabAddButton:hover {{
                background: {self._theme.tab_hover};
            }}
            QToolButton#ModernTabAddButton:focus {{
                border: 1px solid {self._theme.focus};
            }}
            """
        )
        self._stack.setStyleSheet(
            f"QStackedWidget#ModernTabStack {{ background: {self._theme.surface}; }}"
        )

    @staticmethod
    def _parse_tab_arguments(
        icon_or_text: QIcon | str,
        text: str | None,
    ) -> tuple[QIcon, str]:
        if isinstance(icon_or_text, QIcon):
            if text is None:
                raise TypeError("addTab/insertTab requires text after an icon")
            return icon_or_text, text
        if text is not None:
            raise TypeError("addTab/insertTab accepts (widget, text) or (widget, icon, text)")
        icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        return icon, str(icon_or_text)
