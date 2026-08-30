"""A QWidget-based frameless window with selected QMainWindow-compatible APIs."""

from __future__ import annotations

import sys
from typing import cast

from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QBrush,
    QColor,
    QCursor,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QRadialGradient,
    QWindow,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import _resources, _system_menu  # noqa: F401
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    WatercolorStyle,
    palette_for_theme,
    theme_manager,
    theme_with_watercolor_style,
    tinted_icon,
)


def _button_style(theme: ModernTheme, metrics: ModernMetrics) -> str:
    return f"""
    QPushButton {{ border: none; background-color: transparent; }}
    QPushButton:hover {{
        background-color: {theme.control_hover};
        border-radius: {metrics.control_radius}px;
    }}
    QPushButton:pressed {{ background-color: {theme.control_pressed}; }}
    """


def _menu_bar_style(theme: ModernTheme, metrics: ModernMetrics) -> str:
    return f"""
    QMenuBar {{ background: transparent; border: none; }}
    QMenuBar::item {{ background: transparent; }}
    QMenuBar::item:selected {{
        background: {theme.control_pressed};
        border-radius: {metrics.control_radius}px;
    }}
    """


def _resource_icon(name: str, theme: ModernTheme) -> QIcon:
    return tinted_icon(
        QIcon(f":/pyside6_modern_widgets/icons/{name}"),
        theme.text,
    )


class BackgroundFrame(QFrame):
    """Cross-platform watercolor surface used by the frameless window."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme,
        corner_radius: int,
        opaque_surface: bool = False,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._corner_radius = corner_radius
        self._opaque_surface = opaque_surface
        self._watercolor_cache: QPixmap | None = None
        self._watercolor_cache_signature: tuple[int, int, float, ModernTheme] | None = None
        self._live_resize = False
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, not opaque_surface)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, opaque_surface)

    def setTheme(self, theme: ModernTheme) -> None:
        self._theme = theme
        self._invalidate_watercolor_cache()
        self.update()

    def setCornerRadius(self, radius: int) -> None:
        self._corner_radius = radius
        self.update()

    def setLiveResize(self, active: bool) -> None:
        if active == self._live_resize:
            return
        if active:
            self._ensure_watercolor_cache()
        self._live_resize = active
        if not active:
            self._invalidate_watercolor_cache()
        self.update()

    def _invalidate_watercolor_cache(self) -> None:
        self._watercolor_cache = None
        self._watercolor_cache_signature = None

    def _ensure_watercolor_cache(self) -> QPixmap:
        dpr = self.devicePixelRatioF()
        signature = (self.width(), self.height(), dpr, self._theme)
        if self._watercolor_cache is not None and (
            self._live_resize or signature == self._watercolor_cache_signature
        ):
            return self._watercolor_cache

        logical_size = self.size().expandedTo(QSize(1, 1))
        pixel_size = QSize(
            max(1, round(logical_size.width() * dpr)),
            max(1, round(logical_size.height() * dpr)),
        )
        pixmap = QPixmap(pixel_size)
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        logical_rect = QRectF(0, 0, logical_size.width(), logical_size.height())
        painter.fillRect(logical_rect, QColor(self._theme.watercolor_base))
        for color, x, y, radius in self._theme.watercolor_spots:
            gradient = QRadialGradient(
                logical_size.width() * x,
                logical_size.height() * y,
                logical_size.width() * radius,
            )
            gradient.setColorAt(0, QColor(color))
            gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(logical_rect)
        painter.end()
        self._watercolor_cache = pixmap
        self._watercolor_cache_signature = signature
        return pixmap

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._opaque_surface:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        border_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(border_rect, self._corner_radius, self._corner_radius)
        painter.setClipPath(path)
        painter.drawPixmap(self.rect(), self._ensure_watercolor_cache())

        painter.setClipping(False)


class WindowChromeOverlay(QWidget):
    """Anti-aliased corner clipping and border rendered above window content."""

    def __init__(
        self,
        parent: QWidget,
        *,
        theme: ModernTheme,
        corner_radius: int,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._corner_radius = corner_radius
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def setTheme(self, theme: ModernTheme) -> None:
        self._theme = theme
        self.update()

    def setCornerRadius(self, radius: int) -> None:
        self._corner_radius = radius
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        border_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        border_path = QPainterPath()
        border_path.addRoundedRect(
            border_rect,
            self._corner_radius,
            self._corner_radius,
        )

        if self._corner_radius > 0:
            outside_path = QPainterPath()
            outside_path.addRect(QRectF(self.rect()))
            outside_path = outside_path.subtracted(border_path)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillPath(outside_path, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        painter.setPen(QPen(QColor(self._theme.border), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(border_path)


class _LiveResizeOverlay(QWidget):
    """Freeze window content at its original size during translucent resizing."""

    def __init__(self, parent: QWidget, theme: ModernTheme, corner_radius: int) -> None:
        super().__init__(parent)
        self._theme = theme
        self._corner_radius = corner_radius
        self._snapshot: QPixmap | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hide()

    def begin(self, snapshot: QPixmap, theme: ModernTheme, corner_radius: int) -> None:
        self._snapshot = snapshot
        self._theme = theme
        self._corner_radius = corner_radius
        self.show()
        self.raise_()
        self.update()

    def finish(self) -> None:
        self.hide()
        self._snapshot = None

    def setCornerRadius(self, corner_radius: int) -> None:
        self._corner_radius = corner_radius
        self.update()

    def paintEvent(self, _event) -> None:
        if self._snapshot is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        border_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(border_rect, self._corner_radius, self._corner_radius)
        painter.setClipPath(path)
        painter.fillPath(path, QColor(self._theme.watercolor_base))
        painter.drawPixmap(0, 0, self._snapshot)
        painter.setClipping(False)
        painter.setPen(QPen(QColor(self._theme.border), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


class CustomTitleBar(QWidget):
    """Title bar retained from the original BaseWindow implementation."""

    def __init__(
        self,
        parent: ModernWindow,
        *,
        theme: ModernTheme,
        metrics: ModernMetrics,
    ) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self._theme = theme
        self._metrics = metrics
        self.setObjectName("CustomTitleBar")
        self.setAutoFillBackground(False)
        self.drag_start_pos: QPoint | None = None
        self.m_is_pressed = False
        self.m_start_pos: QPoint | None = None
        self.m_window_pos: QPoint | None = None
        self.initUI()

    def initUI(self) -> None:
        vertical_padding = 2
        title_bar_height = max(
            self._metrics.title_bar_height,
            self._metrics.title_button_size + vertical_padding * 2,
        )
        self.setFixedHeight(title_bar_height)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, vertical_padding, 5, vertical_padding)
        self.main_layout.setSpacing(5)

        self.left_layout = QHBoxLayout()
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(1)
        self.main_layout.addLayout(self.left_layout)

        self.iconLabel = QLabel(self)
        self.iconLabel.setFixedSize(20, 20)
        self.iconLabel.setScaledContents(True)
        self.iconLabel.hide()
        self.main_layout.addWidget(self.iconLabel)

        title = self.parent_window.windowTitle() if self.parent_window is not None else ""
        self.titleLabel = QLabel(title, self)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.titleLabel.setObjectName("ModernWindowTitle")
        self.main_layout.addWidget(self.titleLabel)
        self.main_layout.addSpacerItem(
            QSpacerItem(
                40,
                20,
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum,
            )
        )

        self.right_layout = QHBoxLayout()
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(1)
        self.main_layout.addLayout(self.right_layout)

        self.windowMenu = self._create_window_menu()
        self.menuButton = self._create_button(
            _resource_icon("expand-arrow.png", self._theme),
            "窗口菜单",
            self.showWindowMenu,
        )
        self.pinButton = self._create_button(
            _resource_icon("pin.png", self._theme),
            "置顶",
            self.toggleOnTop,
            checkable=True,
        )
        self.minimizeButton = self._create_button(
            _resource_icon("minimize.png", self._theme),
            "最小化",
            self.parent_window.showMinimized,
        )
        self.maximizeButton = self._create_button(
            _resource_icon("maximize.png", self._theme),
            "最大化",
            self.changeMaximize,
        )
        self.closeButton = QPushButton("✕", self)
        self.closeButton.setToolTip("关闭")
        self.closeButton.setFixedSize(
            self._metrics.title_button_size,
            self._metrics.title_button_size,
        )
        self.closeButton.clicked.connect(self.parent_window.close)
        self.setTheme(self._theme)
        for button in (
            self.menuButton,
            self.pinButton,
            self.minimizeButton,
            self.maximizeButton,
            self.closeButton,
        ):
            self.main_layout.addWidget(button)

    def _create_button(self, icon, tooltip, callback, *, checkable=False):
        button = QPushButton(self)
        button.setIcon(icon)
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        button.setFixedSize(
            self._metrics.title_button_size,
            self._metrics.title_button_size,
        )
        button.setStyleSheet(_button_style(self._theme, self._metrics))
        button.clicked.connect(callback)
        return button

    def _create_window_menu(self) -> QMenu:
        menu = QMenu(self)
        self.watercolorMenu = menu.addMenu("主题风格")
        self.watercolorActionGroup = QActionGroup(self)
        self.watercolorActionGroup.setExclusive(True)
        self.standardWatercolorAction = self.watercolorMenu.addAction("标准")
        self.modernWatercolorAction = self.watercolorMenu.addAction("现代")
        self.originalWatercolorAction = self.watercolorMenu.addAction("经典")
        for action, style in (
            (self.standardWatercolorAction, WatercolorStyle.STANDARD),
            (self.modernWatercolorAction, WatercolorStyle.MODERN),
            (self.originalWatercolorAction, WatercolorStyle.ORIGINAL),
        ):
            action.setCheckable(True)
            action.setData(style)
            self.watercolorActionGroup.addAction(action)
        self.watercolorActionGroup.triggered.connect(self._select_watercolor_style)
        menu.addSeparator()
        self.quitAction = menu.addAction(
            _resource_icon("shutdown.png", self._theme),
            "退出程序",
        )

        def confirm_exit() -> None:
            answer = QMessageBox.question(
                self,
                "确认退出",
                "确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                QApplication.quit()

        self.quitAction.triggered.connect(confirm_exit)
        return menu

    def _select_watercolor_style(self, action: QAction) -> None:
        style = action.data()
        if isinstance(style, WatercolorStyle):
            self.parent_window.setWatercolorStyle(style)

    def showWindowMenu(self) -> None:
        position = self.menuButton.mapToGlobal(QPoint(0, self.menuButton.height()))
        self.windowMenu.popup(position)

    def contextMenuEvent(self, event) -> None:
        self.parent_window.showSystemWindowMenu(event.globalPos())
        event.accept()

    def setTheme(self, theme: ModernTheme) -> None:
        self._theme = theme
        self.standardWatercolorAction.setChecked(
            theme.watercolor_style is WatercolorStyle.STANDARD
        )
        self.modernWatercolorAction.setChecked(theme.watercolor_style is WatercolorStyle.MODERN)
        self.originalWatercolorAction.setChecked(theme.watercolor_style is WatercolorStyle.ORIGINAL)
        self.setPalette(palette_for_theme(theme, self.palette()))
        title_font = self.titleLabel.font()
        title_font.setPointSizeF(max(title_font.pointSizeF(), 10.5))
        self.titleLabel.setFont(title_font)
        self.pinButton.setIcon(
            _resource_icon(
                "push-pin.png" if self.pinButton.isChecked() else "pin.png",
                theme,
            )
        )
        self.menuButton.setIcon(_resource_icon("expand-arrow.png", theme))
        self.quitAction.setIcon(_resource_icon("shutdown.png", theme))
        self.minimizeButton.setIcon(_resource_icon("minimize.png", theme))
        self.updateMaximizeIcon(self.parent_window.isMaximized())
        for button in (
            self.menuButton,
            self.pinButton,
            self.minimizeButton,
            self.maximizeButton,
        ):
            button.setStyleSheet(_button_style(theme, self._metrics))
        self.closeButton.setStyleSheet(
            _button_style(theme, self._metrics)
            + f"QPushButton {{ color: {theme.text}; font-size: 18px; }}"
            + f"QPushButton:hover {{ color: {theme.danger}; }}"
        )

    def setInactiveTitleColor(self, color: QColor) -> None:
        palette = QPalette()
        palette.setColor(
            QPalette.ColorGroup.Inactive,
            QPalette.ColorRole.WindowText,
            color,
        )
        self.titleLabel.setPalette(palette)

    def setIcon(self, icon: QIcon) -> None:
        self.iconLabel.setVisible(not icon.isNull())
        if not icon.isNull():
            self.iconLabel.setPixmap(icon.pixmap(20, 20))

    def addCustomWidget(self, widget: QWidget, align: str = "right") -> None:
        if align == "left":
            self.left_layout.addWidget(widget)
        else:
            self.right_layout.addWidget(widget)

    def setTitle(self, title: str) -> None:
        self.titleLabel.setText(title)

    def toggleOnTop(self) -> None:
        was_maximized = self.parent_window.isMaximized()
        stored_rect = self.parent_window.normalGeometry()
        on_top = self.pinButton.isChecked()
        self.parent_window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on_top)
        self.pinButton.setIcon(_resource_icon("push-pin.png" if on_top else "pin.png", self._theme))
        self.pinButton.setToolTip("取消置顶" if on_top else "置顶")
        if was_maximized:
            self.parent_window.showNormal()
            self.parent_window.setGeometry(stored_rect)
            self.parent_window.showMaximized()
        else:
            self.parent_window.showNormal()
        self.parent_window.apply_window_style()

    def updateMaximizeIcon(self, isMaximized: bool) -> None:
        self.maximizeButton.setIcon(
            _resource_icon(
                "restore.png" if isMaximized else "maximize.png",
                self._theme,
            )
        )
        self.maximizeButton.setToolTip("向下还原" if isMaximized else "最大化")

    def changeMaximize(self) -> None:
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if isinstance(child, QPushButton):
                super().mousePressEvent(event)
                return
            self.drag_start_pos = event.globalPosition().toPoint()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            current_pos = event.globalPosition().toPoint()
            if self.parent_window.isMaximized() and self.drag_start_pos:
                delta = current_pos - self.drag_start_pos
                if delta.manhattanLength() > 5:
                    local_x = event.position().x()
                    local_y = event.position().y()
                    percent_x = local_x / max(1, self.parent_window.width())
                    width_after = self.parent_window.normalGeometry().width()
                    self.parent_window.showNormal()
                    new_x = current_pos.x() - int(width_after * percent_x)
                    new_y = current_pos.y() - int(local_y)
                    self.parent_window.move(new_x, new_y)
                    self.m_is_pressed = True
                    self.m_start_pos = current_pos
                    self.m_window_pos = QPoint(new_x, new_y)
                    self.drag_start_pos = None
            elif self.m_is_pressed and self.m_start_pos and self.m_window_pos:
                self.parent_window.move(self.m_window_pos + current_pos - self.m_start_pos)
                event.accept()
            elif self.drag_start_pos:
                delta = current_pos - self.drag_start_pos
                if delta.manhattanLength() > 5:
                    handle = self.parent_window.windowHandle()
                    if handle:
                        handle.startSystemMove()
                        self.drag_start_pos = None
                        QTimer.singleShot(
                            100,
                            lambda: self.updateMaximizeIcon(self.parent_window.isMaximized()),
                        )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.m_is_pressed = False
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if not isinstance(child, QPushButton):
                self.changeMaximize()
                event.accept()


class ModernWindow(QWidget):
    """Cross-platform frameless shell with themeable modern chrome."""

    DEFERRED_RESIZE_SYNC_INTERVAL_MS = 120

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
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self._native_opaque_surface = self._supports_native_window_corners()
        self._deferred_live_resize = (
            self._uses_windows_window_state() and not self._native_opaque_surface
        )
        if self._native_opaque_surface:
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setWindowTitle("基础窗体")
        self._resize_cursor_active = False
        self._system_menu_operation: str | None = None
        self._system_menu_start_cursor = QPoint()
        self._system_menu_start_geometry = QRect()
        self._normal_geometry_before_maximize: QRect | None = None
        self._screen_change_window: QWindow | None = None
        self._screen_device_pixel_ratio: float | None = None
        self._normal_logical_size = QSize(self.size())
        self._screen_change_in_progress = False
        self._system_resize_active = False
        self._system_resize_edges = Qt.Edge(0)
        self._hover_resize_edges = Qt.Edge(0)
        self._system_resize_previous_width: int | None = None
        self._pending_resize_snapshot: QPixmap | None = None
        self._system_resize_watch_timer = QTimer(self)
        self._system_resize_watch_timer.setInterval(50)
        self._system_resize_watch_timer.timeout.connect(self._poll_system_resize_state)
        self._deferred_resize_sync_timer = QTimer(self)
        self._deferred_resize_sync_timer.setInterval(
            self.DEFERRED_RESIZE_SYNC_INTERVAL_MS
        )
        self._deferred_resize_sync_timer.timeout.connect(
            self._refresh_deferred_resize_snapshot
        )
        self._resize_snapshot_prepare_timer = QTimer(self)
        self._resize_snapshot_prepare_timer.setSingleShot(True)
        self._resize_snapshot_prepare_timer.timeout.connect(
            self._prepare_deferred_resize_snapshot
        )
        self._screen_resize_correction_timer = QTimer(self)
        self._screen_resize_correction_timer.setSingleShot(True)
        self._screen_resize_correction_timer.timeout.connect(self._correct_screen_change_size)
        self._surface_refresh_timer = QTimer(self)
        self._surface_refresh_timer.setSingleShot(True)
        self._surface_refresh_timer.timeout.connect(self._refresh_window_surface)
        self._surface_settle_timer = QTimer(self)
        self._surface_settle_timer.setSingleShot(True)
        self._surface_settle_timer.timeout.connect(self._refresh_window_surface)
        self._window_state_settle_timer = QTimer(self)
        self._window_state_settle_timer.setSingleShot(True)
        self._window_state_settle_timer.timeout.connect(self._sync_window_state_style)

        self.cornerRadius = metrics.corner_radius
        self._menu_bar: QMenuBar | None = None
        self._status_bar: QStatusBar | None = None
        self.titleBar: CustomTitleBar | None = None
        self.initWindow()
        self.apply_window_style()

    @staticmethod
    def _uses_windows_window_state() -> bool:
        return sys.platform == "win32" and QApplication.platformName() == "windows"

    @staticmethod
    def _supports_native_window_corners() -> bool:
        if not ModernWindow._uses_windows_window_state():
            return False
        get_windows_version = getattr(sys, "getwindowsversion", None)
        if get_windows_version is None:
            return False
        return get_windows_version().build >= 22000

    def isMaximized(self) -> bool:
        qt_maximized = QWidget.isMaximized(self)
        if not self._uses_windows_window_state():
            return qt_maximized
        if QWidget.isMinimized(self):
            return qt_maximized or self._is_native_maximized()
        return self._is_native_maximized()

    def showMaximized(self) -> None:
        if not self._uses_windows_window_state():
            QWidget.showMaximized(self)
            return
        if self._normal_geometry_before_maximize is None and not self.isMaximized():
            normal_geometry = self.geometry()
            if normal_geometry.isValid():
                self._normal_geometry_before_maximize = QRect(normal_geometry)
        if self.isHidden():
            QWidget.show(self)
        self._show_native_window(3)  # SW_MAXIMIZE
        self._schedule_window_state_style_sync()

    def showNormal(self) -> None:
        if not self._uses_windows_window_state():
            self._normal_geometry_before_maximize = None
            QWidget.showNormal(self)
            return
        normal_geometry = self._normal_geometry_before_maximize
        qt_state = QWidget.windowState(self)
        if normal_geometry is None and qt_state & Qt.WindowState.WindowMaximized:
            normal_geometry = QRect(self.normalGeometry())
        if self.isHidden():
            QWidget.show(self)
        self._show_native_window(9)  # SW_RESTORE
        if normal_geometry is not None and normal_geometry.isValid():
            self.setGeometry(normal_geometry)
        self._normal_geometry_before_maximize = None
        self._schedule_window_state_style_sync()

    def _show_native_window(self, command: int) -> None:
        import ctypes
        from ctypes import wintypes

        show_window = ctypes.windll.user32.ShowWindow
        show_window.argtypes = [wintypes.HWND, ctypes.c_int]
        show_window.restype = wintypes.BOOL
        show_window(wintypes.HWND(int(self.winId())), command)
        if self.titleBar is not None:
            self.titleBar.updateMaximizeIcon(self.isMaximized())

    def _schedule_window_state_style_sync(self) -> None:
        self._sync_window_state_style()
        self._window_state_settle_timer.start(50)

    def _sync_window_state_style(self) -> None:
        is_maximized = self.isMaximized()
        if self.titleBar is not None:
            self.titleBar.updateMaximizeIcon(is_maximized)
        if not self.isMinimized():
            self.apply_window_style()

    def _is_native_maximized(self) -> bool:
        import ctypes
        from ctypes import wintypes

        is_zoomed = ctypes.windll.user32.IsZoomed
        is_zoomed.argtypes = [wintypes.HWND]
        is_zoomed.restype = wintypes.BOOL
        return bool(is_zoomed(wintypes.HWND(int(self.winId()))))

    def initWindow(self) -> None:
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)

        self.frame = BackgroundFrame(
            self,
            theme=self._theme,
            corner_radius=0 if self._native_opaque_surface else self.cornerRadius,
            opaque_surface=self._native_opaque_surface,
        )
        self.frame.setObjectName("backgroundFrame")
        self.apply_window_style()
        self.root_layout.addWidget(self.frame)

        self.frameLayout = QVBoxLayout(self.frame)
        self.frameLayout.setContentsMargins(0, 0, 0, 0)
        self.frameLayout.setSpacing(0)

        title_bar = CustomTitleBar(
            self,
            theme=self._theme,
            metrics=self._metrics,
        )
        self.titleBar = title_bar
        self.frameLayout.addWidget(title_bar)

        self.toolbarLayout = QVBoxLayout()
        self.toolbarLayout.setSpacing(0)
        self.frameLayout.addLayout(self.toolbarLayout)

        self.content = QWidget(self)
        self.frameLayout.addWidget(self.content)
        self.chromeOverlay = WindowChromeOverlay(
            self,
            theme=self._theme,
            corner_radius=self.cornerRadius,
        )
        self.chromeOverlay.setGeometry(self.rect())
        self.chromeOverlay.show()
        self.chromeOverlay.raise_()
        self._live_resize_overlay = _LiveResizeOverlay(
            self,
            self._theme,
            self.cornerRadius,
        )
        self._live_resize_overlay.setGeometry(self.rect())
        self._install_resize_filters(self)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def apply_window_style(self) -> None:
        """Apply the same Qt-painted watercolor style on every platform."""
        corner_radius = 0 if self.isMaximized() else max(0, self.cornerRadius)
        paint_corner_radius = 0 if self._native_opaque_surface else corner_radius
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self.frame.setTheme(self._theme)
        self.frame.setCornerRadius(paint_corner_radius)
        if hasattr(self, "chromeOverlay"):
            self.chromeOverlay.setTheme(self._theme)
            self.chromeOverlay.setCornerRadius(paint_corner_radius)
            self.chromeOverlay.raise_()
        self._set_native_corner_preference(corner_radius > 0)
        if hasattr(self, "_live_resize_overlay"):
            self._live_resize_overlay.setCornerRadius(corner_radius)
            if self._live_resize_overlay.isVisible():
                self._live_resize_overlay.raise_()
        if hasattr(self, "titleBar") and self.titleBar:
            self.titleBar.setTheme(self._theme)
            self._sync_inactive_title_color()
        if self._menu_bar is not None:
            self._menu_bar.setStyleSheet(_menu_bar_style(self._theme, self._metrics))
        self.frame.update()
        self.update()

    def _set_native_corner_preference(self, rounded: bool) -> None:
        if not self._native_opaque_surface or self.windowHandle() is None:
            return
        try:
            import ctypes
            from ctypes import wintypes

            preference = ctypes.c_int(2 if rounded else 1)
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            set_window_attribute.argtypes = [
                wintypes.HWND,
                wintypes.DWORD,
                ctypes.c_void_p,
                wintypes.DWORD,
            ]
            set_window_attribute.restype = ctypes.c_long
            set_window_attribute(
                wintypes.HWND(int(self.winId())),
                33,  # DWMWA_WINDOW_CORNER_PREFERENCE
                ctypes.byref(preference),
                ctypes.sizeof(preference),
            )
        except (AttributeError, OSError):
            return

    def showSystemWindowMenu(self, position: QPoint) -> None:
        if _system_menu.show_native_system_menu(
            int(self.winId()),
            self.mapFromGlobal(position),
            is_minimized=self.isMinimized(),
            is_maximized=self.isMaximized(),
            command_handler=self._handle_native_system_menu_command,
        ):
            return

        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        restore_action = menu.addAction("还原", self.showNormal)
        minimize_action = menu.addAction("最小化", self.showMinimized)
        maximize_action = menu.addAction("最大化", self.showMaximized)
        menu.addSeparator()
        menu.addAction("关闭", self.close)

        is_normal = not self.isMinimized() and not self.isMaximized()
        restore_action.setEnabled(not is_normal)
        minimize_action.setEnabled(not self.isMinimized())
        maximize_action.setEnabled(not self.isMaximized())
        self._portable_system_menu = menu
        menu.popup(position)

    def _handle_native_system_menu_command(self, command: int) -> bool:
        command &= 0xFFF0
        if command == _system_menu.SC_MOVE:
            return self._start_system_menu_operation("move")
        if command == _system_menu.SC_SIZE:
            return self._start_system_menu_operation("size")

        handlers = {
            _system_menu.SC_MINIMIZE: self.showMinimized,
            _system_menu.SC_MAXIMIZE: self.showMaximized,
            _system_menu.SC_RESTORE: self.showNormal,
        }
        handler = handlers.get(command)
        if handler is None:
            return False
        handler()
        return True

    def _start_system_menu_operation(self, operation: str) -> bool:
        if self.isMaximized() or operation not in {"move", "size"}:
            return False
        self._system_menu_operation = operation
        self._system_menu_start_cursor = QCursor.pos()
        self._system_menu_start_geometry = self.geometry()
        cursor = (
            Qt.CursorShape.SizeAllCursor if operation == "move" else Qt.CursorShape.SizeFDiagCursor
        )
        self.setCursor(cursor)
        self.grabMouse()
        self.grabKeyboard()
        return True

    def _update_system_menu_operation(self, global_position: QPoint) -> None:
        delta = global_position - self._system_menu_start_cursor
        geometry = QRect(self._system_menu_start_geometry)
        if self._system_menu_operation == "move":
            geometry.translate(delta)
        elif self._system_menu_operation == "size":
            geometry.setWidth(
                max(self.minimumWidth(), min(self.maximumWidth(), geometry.width() + delta.x()))
            )
            geometry.setHeight(
                max(
                    self.minimumHeight(),
                    min(self.maximumHeight(), geometry.height() + delta.y()),
                )
            )
        self.setGeometry(geometry)

    def _finish_system_menu_operation(self, *, cancel: bool) -> None:
        if self._system_menu_operation is None:
            return
        if cancel:
            self.setGeometry(self._system_menu_start_geometry)
        self._system_menu_operation = None
        self.releaseMouse()
        self.releaseKeyboard()
        self.unsetCursor()

    def theme(self) -> ModernTheme:
        return self._theme

    def setTheme(self, theme: ModernTheme | None) -> None:
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self.apply_window_style()

    def watercolorStyle(self) -> WatercolorStyle:
        return self._theme.watercolor_style

    def setWatercolorStyle(self, style: WatercolorStyle) -> None:
        theme = theme_with_watercolor_style(self._theme, style)
        if theme is self._theme:
            return
        if self._uses_global_theme:
            theme_manager().setWatercolorStyle(style)
        else:
            self._theme = theme
            self.apply_window_style()

    def _on_global_theme_changed(self, theme: ModernTheme) -> None:
        if self._uses_global_theme:
            self._theme = theme
            self.apply_window_style()

    def addTitleBarButton(
        self,
        icon,
        callback=None,
        tooltip: str = "",
        align: str = "right",
    ) -> QPushButton | None:
        if not hasattr(self, "titleBar") or self.titleBar is None:
            return None
        button = QPushButton(self.titleBar)
        if isinstance(icon, str):
            button.setIcon(QIcon(icon))
        elif isinstance(icon, QIcon):
            button.setIcon(icon)
        button.setFixedSize(
            self._metrics.title_button_size,
            self._metrics.title_button_size,
        )
        button.setStyleSheet(_button_style(self._theme, self._metrics))
        if tooltip:
            button.setToolTip(tooltip)
        if callback:
            button.clicked.connect(callback)
        self.titleBar.addCustomWidget(button, align=align)
        self._install_resize_filters(button)
        return button

    def setWindowIcon(self, icon: QIcon | QPixmap) -> None:
        super().setWindowIcon(icon)
        if hasattr(self, "titleBar") and self.titleBar:
            self.titleBar.setIcon(icon if isinstance(icon, QIcon) else QIcon(icon))

    def setWindowTitle(self, title: str) -> None:
        super().setWindowTitle(title)
        if hasattr(self, "titleBar") and self.titleBar is not None:
            self.titleBar.setTitle(title)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._connect_screen_change_signal()
        if not event.spontaneous():
            self.apply_window_style()
        self._schedule_surface_refresh()

    def event(self, event) -> bool:
        handled = super().event(event)
        if event.type() == QEvent.Type.DevicePixelRatioChange:
            self._schedule_surface_refresh()
        elif event.type() in (
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        ):
            self._sync_inactive_title_color()
        return handled

    def _connect_screen_change_signal(self) -> None:
        window_handle = self.windowHandle()
        if window_handle is None or window_handle is self._screen_change_window:
            return
        self._screen_change_window = window_handle
        screen = window_handle.screen()
        self._screen_device_pixel_ratio = screen.devicePixelRatio() if screen else None
        window_handle.screenChanged.connect(self._handle_screen_changed)

    def _handle_screen_changed(self, screen) -> None:
        previous_dpr = self._screen_device_pixel_ratio
        current_dpr = screen.devicePixelRatio()
        self._screen_device_pixel_ratio = current_dpr
        if (
            self._uses_windows_window_state()
            and previous_dpr
            and current_dpr
            and previous_dpr != current_dpr
            and not self.isMaximized()
            and not self.isMinimized()
            and not self._system_resize_active
        ):
            self._screen_change_in_progress = True
            self._screen_resize_correction_timer.start(250)
        self._schedule_surface_refresh()

    def _correct_screen_change_size(self) -> None:
        if not self._screen_change_in_progress:
            return
        self._screen_change_in_progress = False
        if (
            not self._uses_windows_window_state()
            or self.isMaximized()
            or self.isMinimized()
            or self._system_resize_active
        ):
            return
        if self.size() != self._normal_logical_size:
            self.resize(self._normal_logical_size)

    def _schedule_surface_refresh(self) -> None:
        if not hasattr(self, "_surface_refresh_timer"):
            return
        self._surface_refresh_timer.start(0)
        self._surface_settle_timer.start(100)

    def _refresh_window_surface(self) -> None:
        if not self.isVisible() or self.isMinimized():
            return
        if hasattr(self, "chromeOverlay"):
            self.chromeOverlay.setGeometry(self.rect())
            self.chromeOverlay.raise_()
        self.update()
        widgets = cast(list[QWidget], self.findChildren(QWidget))
        for widget in widgets:
            if widget.isVisible():
                QWidget.update(widget)
        window_handle = self.windowHandle()
        if window_handle is not None:
            window_handle.requestUpdate()

    def _sync_inactive_title_color(self) -> None:
        title_bar = getattr(self, "titleBar", None)
        if title_bar is None:
            return
        menu_bar = getattr(self, "_menu_bar", None)
        owns_probe = menu_bar is None
        if menu_bar is None:
            menu_bar = QMenuBar()
        menu_bar.ensurePolished()
        color = QColor(
            menu_bar.palette().color(
                QPalette.ColorGroup.Inactive,
                QPalette.ColorRole.ButtonText,
            )
        )
        title_bar.setInactiveTitleColor(color)
        if owns_probe:
            menu_bar.deleteLater()

    def menuBar(self) -> QMenuBar:
        if self._menu_bar is None:
            self._menu_bar = QMenuBar(self)
            self._menu_bar.setStyleSheet(_menu_bar_style(self._theme, self._metrics))
            self.frameLayout.insertWidget(1, self._menu_bar)
            self._install_resize_filters(self._menu_bar)
            self._sync_inactive_title_color()
        return self._menu_bar

    def addToolBar(self, *args) -> QToolBar:
        toolbar = next((arg for arg in args if isinstance(arg, QToolBar)), None)
        if toolbar is None:
            title = next((arg for arg in args if isinstance(arg, str)), "")
            toolbar = QToolBar(title, self) if title else QToolBar(self)
        toolbar.setStyleSheet("QToolBar { background: transparent; border: none; }")
        self.toolbarLayout.addWidget(toolbar)
        self._install_resize_filters(toolbar)
        return toolbar

    def statusBar(self) -> QStatusBar:
        if self._status_bar is None:
            self._status_bar = QStatusBar(self)
            self._status_bar.setStyleSheet("QStatusBar { background: transparent; border: none; }")
            self._status_bar.setSizeGripEnabled(False)
            self.frameLayout.addWidget(self._status_bar)
            self._install_resize_filters(self._status_bar)
        return self._status_bar

    def setCentralWidget(self, widget: QWidget) -> None:
        self.frameLayout.removeWidget(self.content)
        self.content.deleteLater()
        self.content = widget
        if self._status_bar:
            index = self.frameLayout.indexOf(self._status_bar)
            self.frameLayout.insertWidget(index, self.content)
        else:
            self.frameLayout.addWidget(self.content)
        self._install_resize_filters(self.content)

    def setCornerRadius(self, radius: int) -> None:
        self.cornerRadius = radius
        self.apply_window_style()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._schedule_window_state_style_sync()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if (
            not self._screen_change_in_progress
            and not self.isMaximized()
            and not self.isMinimized()
        ):
            self._normal_logical_size = QSize(event.size())
        if hasattr(self, "chromeOverlay"):
            self.chromeOverlay.setGeometry(self.rect())
            self.chromeOverlay.raise_()
        if hasattr(self, "_live_resize_overlay"):
            self._live_resize_overlay.setGeometry(self.rect())
            if self._live_resize_overlay.isVisible():
                self._live_resize_overlay.raise_()
        if self._system_resize_active and self._deferred_live_resize:
            self._update_deferred_resize_state(event.size().width())

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        if hasattr(self, "_surface_settle_timer"):
            self._surface_settle_timer.start(100)

    @staticmethod
    def _has_pressed_mouse_buttons() -> bool:
        return QApplication.mouseButtons() != Qt.MouseButton.NoButton

    @staticmethod
    def _has_horizontal_resize_edge(edges: Qt.Edge) -> bool:
        return bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))

    def _queue_deferred_resize_snapshot(self, edges: Qt.Edge) -> None:
        if not self._deferred_live_resize or self._system_resize_active:
            return
        self._hover_resize_edges = edges
        if self._has_horizontal_resize_edge(edges):
            if self._pending_resize_snapshot is None:
                self._resize_snapshot_prepare_timer.start(0)
        else:
            self._resize_snapshot_prepare_timer.stop()
            self._pending_resize_snapshot = None

    def _prepare_deferred_resize_snapshot(self) -> None:
        if (
            self._system_resize_active
            or not self._deferred_live_resize
            or not self._has_horizontal_resize_edge(self._hover_resize_edges)
        ):
            return
        self._pending_resize_snapshot = self.frame.grab()

    def _begin_system_resize_tracking(self, edges: Qt.Edge | None = None) -> None:
        if self._system_resize_active:
            return
        self._system_resize_active = True
        self._system_resize_edges = edges if edges is not None else Qt.Edge(0)
        self._system_resize_previous_width = self.width()
        self.frame.setLiveResize(True)
        self._resize_snapshot_prepare_timer.stop()
        if not self._has_horizontal_resize_edge(self._system_resize_edges):
            self._pending_resize_snapshot = None
        self._system_resize_watch_timer.start()

    def _update_deferred_resize_state(self, width: int) -> None:
        previous_width = self._system_resize_previous_width
        self._system_resize_previous_width = width
        if previous_width is None:
            return
        if not self._has_horizontal_resize_edge(self._system_resize_edges):
            self._pending_resize_snapshot = None
            if self._live_resize_overlay.isVisible():
                self._stop_deferred_resize_overlay()
            return
        if width < previous_width:
            self._start_deferred_resize_overlay()
        elif width > previous_width:
            self._pending_resize_snapshot = None
            if self._live_resize_overlay.isVisible():
                self._stop_deferred_resize_overlay()
        elif not self._live_resize_overlay.isVisible():
            self._pending_resize_snapshot = None

    def _start_deferred_resize_overlay(self) -> None:
        if self._live_resize_overlay.isVisible():
            return
        snapshot = self._pending_resize_snapshot or self.frame.grab()
        self._pending_resize_snapshot = None
        self._live_resize_overlay.setGeometry(self.rect())
        self._live_resize_overlay.begin(snapshot, self._theme, self.cornerRadius)
        self.frame.setUpdatesEnabled(False)
        self._deferred_resize_sync_timer.start()

    def _stop_deferred_resize_overlay(self) -> None:
        if not self._live_resize_overlay.isVisible():
            return
        self._deferred_resize_sync_timer.stop()
        self.frame.setUpdatesEnabled(True)
        self.frame.update()
        self._live_resize_overlay.finish()
        self._schedule_surface_refresh()

    def _refresh_deferred_resize_snapshot(self) -> None:
        if (
            not self._system_resize_active
            or not self._deferred_live_resize
            or not self._live_resize_overlay.isVisible()
        ):
            return

        self.frame.setUpdatesEnabled(True)
        snapshot = self.frame.grab()
        self.frame.setUpdatesEnabled(False)
        self._live_resize_overlay.begin(snapshot, self._theme, self.cornerRadius)

    def _finish_system_resize_tracking(self) -> None:
        was_active = self._system_resize_active
        self._system_resize_active = False
        self._system_resize_edges = Qt.Edge(0)
        self._system_resize_previous_width = None
        self._pending_resize_snapshot = None
        self._system_resize_watch_timer.stop()
        self._deferred_resize_sync_timer.stop()
        if was_active:
            self.frame.setLiveResize(False)
            if self._deferred_live_resize:
                self._stop_deferred_resize_overlay()

    def _poll_system_resize_state(self) -> None:
        if not self._has_pressed_mouse_buttons():
            self._finish_system_resize_tracking()

    def hideEvent(self, event) -> None:
        self._finish_system_resize_tracking()
        super().hideEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if (
            isinstance(watched, QWidget)
            and watched.window() is self
            and not watched.hasMouseTracking()
        ):
            watched.setMouseTracking(True)

        if (
            self._system_menu_operation is not None
            and isinstance(watched, QWidget)
            and watched.window() is self
        ):
            event_type = event.type()
            if event_type == QEvent.Type.MouseMove:
                self._update_system_menu_operation(event.globalPosition().toPoint())
                return True
            if event_type == QEvent.Type.MouseButtonPress:
                cancel = event.button() != Qt.MouseButton.LeftButton
                self._finish_system_menu_operation(cancel=cancel)
                return True
            if event_type == QEvent.Type.KeyPress and event.key() in (
                Qt.Key.Key_Escape,
                Qt.Key.Key_Enter,
                Qt.Key.Key_Return,
            ):
                self._finish_system_menu_operation(cancel=event.key() == Qt.Key.Key_Escape)
                return True

        if isinstance(watched, QWidget) and watched.window() is self:
            event_type = event.type()
            if event_type == QEvent.Type.MouseMove:
                position = watched.mapTo(self, event.position().toPoint())
                edges = self._resize_edges_at(position)
                self._queue_deferred_resize_snapshot(edges)
                self._set_resize_cursor(edges)
            elif event_type == QEvent.Type.MouseButtonPress:
                position = watched.mapTo(self, event.position().toPoint())
                edges = self._resize_edges_at(position)
                if event.button() == Qt.MouseButton.LeftButton and edges:
                    handle = self.windowHandle()
                    if handle is not None and handle.startSystemResize(edges):
                        self._begin_system_resize_tracking(edges)
                        self._screen_change_in_progress = False
                        self._screen_resize_correction_timer.stop()
                        return True
            elif event_type == QEvent.Type.MouseButtonRelease:
                self._finish_system_resize_tracking()
        return super().eventFilter(watched, event)

    def _install_resize_filters(self, widget: QWidget) -> None:
        widget.setMouseTracking(True)
        for child in widget.children():
            if isinstance(child, QWidget):
                self._install_resize_filters(child)

    def _resize_edges_at(self, position: QPoint) -> Qt.Edge:
        if self.isMaximized():
            return Qt.Edge(0)

        border_width = 8
        edges = Qt.Edge(0)
        if position.x() < border_width:
            edges |= Qt.Edge.LeftEdge
        elif position.x() >= self.width() - border_width:
            edges |= Qt.Edge.RightEdge
        if position.y() < border_width:
            edges |= Qt.Edge.TopEdge
        elif position.y() >= self.height() - border_width:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _set_resize_cursor(self, edges: Qt.Edge) -> None:
        if not edges:
            if self._resize_cursor_active:
                self.unsetCursor()
                self._resize_cursor_active = False
            return

        if edges in (
            Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
            Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
        ):
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif edges in (
            Qt.Edge.TopEdge | Qt.Edge.RightEdge,
            Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
        ):
            cursor = Qt.CursorShape.SizeBDiagCursor
        elif edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge):
            cursor = Qt.CursorShape.SizeHorCursor
        else:
            cursor = Qt.CursorShape.SizeVerCursor
        self.setCursor(cursor)
        self._resize_cursor_active = True

    def hideTitleBar(self) -> None:
        if hasattr(self, "titleBar") and self.titleBar:
            self.titleBar.hide()
            self.frameLayout.removeWidget(self.titleBar)
            self.titleBar.deleteLater()
            self.titleBar = None
