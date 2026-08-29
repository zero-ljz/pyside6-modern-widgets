"""Composite navigation component with a sidebar and page stack."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter
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


class _SidebarOverlayShadow(QWidget):
    """A lightweight right-edge shadow for the overlay sidebar."""

    WIDTH = 14

    def __init__(self, parent: QWidget, theme: ModernTheme) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()

    def setTheme(self, theme: ModernTheme) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, _event) -> None:
        shadow_alpha = 72 if QColor(self._theme.watercolor_base).lightness() < 128 else 42
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(0, 0, 0, shadow_alpha))
        gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter = QPainter(self)
        painter.fillRect(self.rect(), QBrush(gradient))


class NavigationView(QWidget):
    """Combine a ``NavigationSidebar`` with a synchronized page stack."""

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
        self.contentContainer = QFrame(self)
        self.contentContainer.setObjectName("NavigationContent")
        self.contentContainer.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground,
            True,
        )
        self.contentContainer.setStyleSheet(navigation_content_style(self._theme))
        self._sidebar_shadow = _SidebarOverlayShadow(self, self._theme)

        content_layout = QVBoxLayout(self.contentContainer)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.stackedWidget = _CurrentPageStack(self.contentContainer)
        content_layout.addWidget(self.stackedWidget)

        self._root_layout.addWidget(self._sidebar_host)
        self._root_layout.addWidget(self.contentContainer, 1)

        self.sidebar.currentChanged.connect(self.stackedWidget.setCurrentIndex)
        self.sidebar.collapsedChanged.connect(self._sync_outside_click_filter)
        self.sidebar.collapsedChanged.connect(self._update_sidebar_shadow)
        self.stackedWidget.currentChanged.connect(self.stackedWidget.updateGeometry)
        self.stackedWidget.currentChanged.connect(self._on_current_changed)

    def isSidebarOverlay(self) -> bool:
        return self._sidebar_overlay

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
        self._update_sidebar_shadow()
        self._sync_outside_click_filter()
        self.updateGeometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_sidebar_layer()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.sidebar and event.type() == QEvent.Type.Resize:
            if not self._sidebar_overlay:
                self._sidebar_host.setFixedWidth(event.size().width())
            self._position_sidebar_layer()
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
            self._sidebar_shadow.setGeometry(
                self.sidebar.width(),
                0,
                _SidebarOverlayShadow.WIDTH,
                self.height(),
            )
            self._sidebar_shadow.raise_()

    def _update_sidebar_shadow(self, _collapsed: bool | None = None) -> None:
        visible = self._sidebar_overlay and not self.sidebar.isCollapsed()
        self._sidebar_shadow.setVisible(visible)
        if visible:
            self._sidebar_shadow.raise_()

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
        self._sidebar_shadow.setTheme(self._theme)
        self.contentContainer.setStyleSheet(navigation_content_style(self._theme))

    def _on_global_theme_changed(self, theme: ModernTheme) -> None:
        if self._uses_global_theme:
            self._theme = theme
            self.setPalette(palette_for_theme(theme, self.palette()))
            self.sidebar.setTheme(theme)
            self._sidebar_shadow.setTheme(theme)
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
