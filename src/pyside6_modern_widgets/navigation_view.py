"""Composite navigation component with a sidebar and page stack."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSignalBlocker, QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
    QWidgetItem,
)

from ._theme_binding import ThemeBinding
from .navigation_sidebar import (
    NavigationPosition,
    NavigationSidebar,
    navigation_content_style,
)
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    inherited_theme,
    palette_for_theme,
)


class NavigationView(QWidget):
    """Combine a ``NavigationSidebar`` with a synchronized page stack."""

    themeChanged = Signal(object)

    SIDEBAR_OVERLAY_HYSTERESIS = 48

    currentChanged = Signal(int)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        super().__init__(parent)
        self._theme_override = theme
        self._theme = theme if theme is not None else inherited_theme(self)
        self._metrics = metrics
        self._sidebar_overlay = False
        self._auto_sidebar_overlay = True
        self._sidebar_user_prefers_expanded = True
        self._outside_click_filter_installed = False
        self.setObjectName("ModernNavigationView")
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#ModernNavigationView { background-color: transparent; }")

        self._root_layout = QHBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        self.sidebar = NavigationSidebar(
            self,
            metrics=self._metrics,
        )
        self.sidebar.installEventFilter(self)
        self._sidebar_host = QWidget(self)
        self._sidebar_host.setFixedWidth(self.sidebar.width())
        self._sync_sidebar_minimum_height()
        self.contentContainer = QFrame(self)
        self.contentContainer.setObjectName("NavigationContent")
        self.contentContainer.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground,
            True,
        )
        self.contentContainer.setStyleSheet(navigation_content_style(self._theme))

        content_layout = QVBoxLayout(self.contentContainer)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.stackedWidget = _CurrentPageStack(self.contentContainer)
        self.stackedWidget.installEventFilter(self)
        # QWidgetItem normally bypasses QWidget.heightForWidth and queries its
        # layout directly, which would bring hidden QStackedLayout pages back.
        content_layout.addItem(_CurrentPageStackItem(self.stackedWidget))

        self._root_layout.addWidget(self._sidebar_host)
        self._root_layout.addWidget(self.contentContainer, 1)

        self.sidebar.currentChanged.connect(self.stackedWidget.setCurrentIndex)
        self.sidebar.collapseIntentChanged.connect(self._on_sidebar_collapse_intent_changed)
        self.sidebar.collapsedChanged.connect(self._sync_outside_click_filter)
        self.stackedWidget.currentChanged.connect(self.stackedWidget.updateGeometry)
        self.stackedWidget.currentChanged.connect(self._on_current_changed)
        self.stackedWidget.widgetRemoved.connect(self._on_page_removed)
        self._theme_binding: ThemeBinding = ThemeBinding(self, self.theme, self._apply_theme)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def isSidebarOverlay(self) -> bool:
        return self._sidebar_overlay

    def isAutoSidebarOverlay(self) -> bool:
        return self._auto_sidebar_overlay

    def setAutoSidebarOverlay(self, enabled: bool) -> None:
        if enabled == self._auto_sidebar_overlay:
            return
        self._auto_sidebar_overlay = enabled
        if enabled:
            self._update_automatic_sidebar_overlay()

    def setSidebarOverlay(self, overlay: bool) -> None:
        if overlay == self._sidebar_overlay:
            return
        self._sidebar_overlay = overlay
        self._sidebar_host.setFixedWidth(
            self._metrics.navigation_collapsed_width if overlay else self.sidebar.width()
        )
        self.sidebar.setOverlaySurface(overlay)
        self._position_sidebar_layer()
        self.sidebar.show()
        self._sync_outside_click_filter()
        self.updateGeometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_automatic_sidebar_overlay()
        self._position_sidebar_layer()

    def _update_automatic_sidebar_overlay(self) -> None:
        if not self._auto_sidebar_overlay:
            return
        required_width = self._metrics.navigation_expanded_width + self._minimum_content_width()
        if self.width() <= required_width:
            self.setSidebarOverlay(True)
            if not self.sidebar.isCollapsed():
                self.sidebar.setCollapsed(True, animated=False)
        elif self.width() >= required_width + self.SIDEBAR_OVERLAY_HYSTERESIS:
            self.setSidebarOverlay(False)
            should_collapse = not self._sidebar_user_prefers_expanded
            if self.sidebar.isCollapsed() != should_collapse:
                self.sidebar.setCollapsed(should_collapse, animated=False)

    def _minimum_content_width(self) -> int:
        return max(
            0,
            self.contentContainer.minimumWidth(),
            self.contentContainer.minimumSizeHint().width(),
        )

    def _on_sidebar_collapse_intent_changed(self, collapsed: bool) -> None:
        self._sidebar_user_prefers_expanded = not collapsed

    def eventFilter(self, watched, event) -> bool:
        if watched is self.sidebar and event.type() == QEvent.Type.Resize:
            if not self._sidebar_overlay:
                self._sidebar_host.setFixedWidth(event.size().width())
            self._position_sidebar_layer()
        elif watched is self.sidebar and event.type() == QEvent.Type.LayoutRequest:
            self._sync_sidebar_minimum_height()
        elif watched is self.stackedWidget and event.type() == QEvent.Type.LayoutRequest:
            self._update_automatic_sidebar_overlay()
        elif self._outside_click_filter_installed and event.type() == QEvent.Type.MouseButtonPress:
            position = self.sidebar.mapFromGlobal(event.globalPosition().toPoint())
            if not self.sidebar.rect().contains(position):
                self.sidebar.setCollapsed(True)
        return super().eventFilter(watched, event)

    def _position_sidebar_layer(self) -> None:
        if hasattr(self, "sidebar"):
            self.sidebar.setGeometry(
                0,
                0,
                self.sidebar.width(),
                self.height(),
            )
            self.sidebar.raise_()

    def _sync_sidebar_minimum_height(self) -> None:
        self._sidebar_host.setMinimumHeight(self.sidebar.minimumSizeHint().height())
        self.updateGeometry()

    def _sync_outside_click_filter(self, _collapsed: bool | None = None) -> None:
        application = QApplication.instance()
        if application is None:
            return
        should_install = self._sidebar_overlay and not self.sidebar.isCollapsed()
        if should_install and not self._outside_click_filter_installed:
            application.installEventFilter(self)
            self._outside_click_filter_installed = True
        elif not should_install and self._outside_click_filter_installed:
            application.removeEventFilter(self)
            self._outside_click_filter_installed = False

    def addPage(
        self,
        page: QWidget,
        text: str,
        icon: QIcon | QStyle.StandardPixmap | None = None,
        position: NavigationPosition = NavigationPosition.TOP,
        selected: bool = False,
    ) -> int:
        page_index = self.stackedWidget.addWidget(page)
        item_index = self.sidebar.addItem(text, icon, position)
        self._sync_sidebar_minimum_height()
        if item_index != page_index:
            self.stackedWidget.removeWidget(page)
            self.sidebar.removeItem(item_index)
            raise RuntimeError("Navigation item and page indexes are out of sync")
        if selected or self.count() == 1:
            self.setCurrentIndex(page_index)
        if self.count() == 1:
            self._on_current_changed(self.currentIndex())
        return page_index

    def removePage(self, index: int) -> None:
        """Remove a page without deleting it or changing its Qt parent."""
        page = self.widget(index)
        if page is not None:
            self.stackedWidget.removeWidget(page)
            page.hide()

    def takePage(self, index: int) -> QWidget | None:
        """Remove and hide a page, transferring ownership to the caller."""
        page = self.widget(index)
        if page is None:
            return None
        self.removePage(index)
        page.setParent(None)
        return page

    def _on_page_removed(self, index: int) -> None:
        old_index = self.sidebar.currentIndex()
        new_index = min(index, self.count() - 1) if old_index == index else self.currentIndex()
        with QSignalBlocker(self.sidebar), QSignalBlocker(self.stackedWidget):
            button = self.sidebar.removeItem(index)
            if button is not None:
                button.deleteLater()
            self.sidebar.setCurrentIndex(new_index)
            self.stackedWidget.setCurrentIndex(new_index)
        self._sync_sidebar_minimum_height()
        self.stackedWidget.updateGeometry()
        if old_index != new_index or old_index == index:
            self._on_current_changed(new_index)
        else:
            self._update_automatic_sidebar_overlay()

    def count(self) -> int:
        return self.stackedWidget.count()

    def widget(self, index: int) -> QWidget | None:
        return self.stackedWidget.widget(index)

    def currentWidget(self) -> QWidget | None:
        return self.stackedWidget.currentWidget()

    def indexOf(self, page: QWidget) -> int:
        return self.stackedWidget.indexOf(page)

    def setCurrentWidget(self, page: QWidget) -> None:
        self.setCurrentIndex(self.indexOf(page))

    def currentIndex(self) -> int:
        return self.stackedWidget.currentIndex()

    def setCurrentIndex(self, index: int) -> None:
        if not 0 <= index < self.count():
            return
        self.sidebar.setCurrentIndex(index)
        self.stackedWidget.setCurrentIndex(index)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override locally; None restores ancestor/global theme inheritance."""
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def _apply_theme(self) -> None:
        self._theme = self.theme()
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self.contentContainer.setStyleSheet(navigation_content_style(self._theme))

    def _on_current_changed(self, index: int) -> None:
        # QStackedWidget announces selection changes before widgetRemoved.
        # Wait until the navigation entries have caught up before publishing.
        if self.sidebar.count() != self.count():
            return
        if index >= 0 and self.sidebar.currentIndex() != index:
            self.sidebar.setCurrentIndex(index)
        self._update_automatic_sidebar_overlay()
        self.currentChanged.emit(index)


class _CurrentPageStack(QStackedWidget):
    """Keep hidden pages from imposing their size hints on the active page."""

    def hasHeightForWidth(self) -> bool:
        current = self.currentWidget()
        return current.hasHeightForWidth() if current is not None else False

    def heightForWidth(self, width: int) -> int:
        # QStackedLayout otherwise takes the tallest of *all* pages. Windows
        # consults this during a DPI resize, even when minimumSizeHint is small.
        current = self.currentWidget()
        return current.heightForWidth(width) if current is not None else -1

    def sizeHint(self) -> QSize:
        current = self.currentWidget()
        return current.sizeHint() if current is not None else super().sizeHint()

    def minimumSizeHint(self) -> QSize:
        current = self.currentWidget()
        if current is None:
            return super().minimumSizeHint()
        return current.minimumSizeHint().expandedTo(current.minimumSize())


class _CurrentPageStackItem(QWidgetItem):
    def heightForWidth(self, width: int) -> int:
        stack = self.widget()
        return max(stack.minimumHeight(), min(stack.maximumHeight(), stack.heightForWidth(width)))

    def minimumHeightForWidth(self, width: int) -> int:
        return self.heightForWidth(width)
