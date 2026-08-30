"""Composite navigation component with a sidebar and page stack."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .navigation_sidebar import (
    NavigationPosition,
    NavigationSidebar,
    navigation_content_style,
)
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    palette_for_theme,
    theme_manager,
)


class NavigationView(QWidget):
    """Combine a ``NavigationSidebar`` with a synchronized page stack."""

    SIDEBAR_OVERLAY_ENTER_WIDTH = 900
    SIDEBAR_OVERLAY_EXIT_WIDTH = 1040

    currentChanged = Signal(int)

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
        self._sidebar_overlay = False
        self._auto_sidebar_overlay = True
        self._sidebar_user_prefers_expanded = True
        self._outside_click_filter_installed = False
        theme_manager().themeChanged.connect(self._on_global_theme_changed)
        self.setObjectName("ModernNavigationView")
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#ModernNavigationView { background-color: transparent; }")

        self._root_layout = QHBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        self.sidebar = NavigationSidebar(
            self,
            theme=self._theme,
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
        content_layout.addWidget(self.stackedWidget)

        self._root_layout.addWidget(self._sidebar_host)
        self._root_layout.addWidget(self.contentContainer, 1)

        self.sidebar.currentChanged.connect(self.stackedWidget.setCurrentIndex)
        self.sidebar.collapseIntentChanged.connect(
            self._on_sidebar_collapse_intent_changed
        )
        self.sidebar.collapsedChanged.connect(self._sync_outside_click_filter)
        self.stackedWidget.currentChanged.connect(self.stackedWidget.updateGeometry)
        self.stackedWidget.currentChanged.connect(self._on_current_changed)

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
            self._metrics.navigation_collapsed_width
            if overlay
            else self.sidebar.width()
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
        if self.width() <= self.SIDEBAR_OVERLAY_ENTER_WIDTH:
            self.setSidebarOverlay(True)
            if not self.sidebar.isCollapsed():
                self.sidebar.setCollapsed(True, animated=False)
        elif self.width() >= self.SIDEBAR_OVERLAY_EXIT_WIDTH:
            self.setSidebarOverlay(False)
            should_collapse = not self._sidebar_user_prefers_expanded
            if self.sidebar.isCollapsed() != should_collapse:
                self.sidebar.setCollapsed(should_collapse, animated=False)

    def _on_sidebar_collapse_intent_changed(self, collapsed: bool) -> None:
        self._sidebar_user_prefers_expanded = not collapsed

    def eventFilter(self, watched, event) -> bool:
        if watched is self.sidebar and event.type() == QEvent.Type.Resize:
            if not self._sidebar_overlay:
                self._sidebar_host.setFixedWidth(event.size().width())
            self._position_sidebar_layer()
        elif watched is self.sidebar and event.type() == QEvent.Type.LayoutRequest:
            self._sync_sidebar_minimum_height()
        elif (
            self._outside_click_filter_installed
            and event.type() == QEvent.Type.MouseButtonPress
        ):
            position = self.sidebar.mapFromGlobal(
                event.globalPosition().toPoint()
            )
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
        icon=None,
        position: NavigationPosition = NavigationPosition.TOP,
        selected: bool = False,
    ) -> int:
        page.setAutoFillBackground(False)
        page_index = self.stackedWidget.addWidget(page)
        item_index = self.sidebar.addItem(text, icon, position)
        self._sync_sidebar_minimum_height()
        if item_index != page_index:
            self.stackedWidget.removeWidget(page)
            self.sidebar.removeItem(item_index)
            raise RuntimeError("Navigation item and page indexes are out of sync")
        if selected or self.count() == 1:
            self.setCurrentIndex(page_index)
        return page_index

    def removePage(self, index: int) -> QWidget | None:
        page = self.widget(index)
        if page is None:
            return None
        was_current = index == self.currentIndex()
        self.stackedWidget.removeWidget(page)
        self.sidebar.removeItem(index)
        self._sync_sidebar_minimum_height()
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

    def theme(self) -> ModernTheme:
        return self._theme

    def setTheme(self, theme: ModernTheme | None) -> None:
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self.sidebar.setTheme(self._theme)
        self.contentContainer.setStyleSheet(navigation_content_style(self._theme))

    def _on_global_theme_changed(self, theme: ModernTheme) -> None:
        if self._uses_global_theme:
            self._theme = theme
            self.setPalette(palette_for_theme(theme, self.palette()))
            self.sidebar.setTheme(theme)
            self.contentContainer.setStyleSheet(navigation_content_style(theme))

    def _on_current_changed(self, index: int) -> None:
        if index >= 0 and self.sidebar.currentIndex() != index:
            self.sidebar.setCurrentIndex(index)
        self.currentChanged.emit(index)


class _CurrentPageStack(QStackedWidget):
    """Keep hidden pages from imposing their size hints on the active page."""

    def sizeHint(self) -> QSize:
        current = self.currentWidget()
        return current.sizeHint() if current is not None else super().sizeHint()

    def minimumSizeHint(self) -> QSize:
        current = self.currentWidget()
        return current.minimumSizeHint() if current is not None else super().minimumSizeHint()
