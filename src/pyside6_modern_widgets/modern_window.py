"""A QWidget-based frameless window with selected QMainWindow-compatible APIs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QCursor,
    QIcon,
    QPalette,
    QPixmap,
    QPlatformSurfaceEvent,
    QScreen,
    QWindow,
)
from PySide6.QtWidgets import (
    QApplication,
    QMenuBar,
    QPushButton,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import _resources, _system_menu  # noqa: F401
from ._window_chrome import (
    BackgroundFrame,
    WindowChromeOverlay,
    WindowSurfacePolicy,
    WindowTitleBar,
    button_style,
    current_window_surface_policy,
    manual_resize_geometry,
    uses_windows_window_state,
)
from ._windows_window import (
    HTBOTTOM,
    HTBOTTOMLEFT,
    HTBOTTOMRIGHT,
    HTCAPTION,
    HTCLIENT,
    HTLEFT,
    HTMAXBUTTON,
    HTRIGHT,
    HTTOP,
    HTTOPLEFT,
    HTTOPRIGHT,
    WM_CAPTURECHANGED,
    WM_DISPLAYCHANGE,
    WM_DPICHANGED,
    WM_ENTERSIZEMOVE,
    WM_EXITSIZEMOVE,
    WM_LBUTTONUP,
    WM_MOUSEMOVE,
    WM_NCCALCSIZE,
    WM_NCHITTEST,
    WM_NCLBUTTONDBLCLK,
    WM_NCLBUTTONDOWN,
    WM_NCLBUTTONUP,
    WM_NCMOUSELEAVE,
    WM_NCMOUSEMOVE,
    WM_NCRBUTTONUP,
    WM_SYSCOMMAND,
    client_position_from_l_param,
    constrain_maximized_client_area,
    read_message,
    redraw_native_window,
    screen_position_from_client,
    screen_position_from_l_param,
    set_mouse_capture,
    set_native_frame,
    start_system_move,
    track_non_client_mouse_leave,
)
from .modern_menu import ModernMenu
from .modern_menu_bar import ModernMenuBar
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    palette_for_theme,
    theme_manager,
    tinted_icon,
)

_DEFAULT_WINDOW_FLAGS = Qt.WindowType.Widget


def _resource_icon(name: str, theme: ModernTheme) -> QIcon:
    return tinted_icon(
        QIcon(f":/pyside6_modern_widgets/icons/{name}"),
        theme.text,
    )


class CustomTitleBar(WindowTitleBar["ModernWindow"]):
    """Title bar retained from the original BaseWindow implementation."""

    def __init__(
        self,
        parent: ModernWindow,
        *,
        theme: ModernTheme,
        metrics: ModernMetrics,
    ) -> None:
        super().__init__(
            parent,
            theme=theme,
            metrics=metrics,
            allows_maximize=True,
        )
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
        for button in (
            self.menuButton,
            self.pinButton,
            self.minimizeButton,
            self.maximizeButton,
        ):
            self.main_layout.insertWidget(self.main_layout.indexOf(self.closeButton), button)
        self.setTheme(self._theme)

    def _create_button(self, icon, tooltip, callback, *, checkable=False):
        button = QPushButton(self)
        button.setIcon(icon)
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        button.setFixedSize(
            self._metrics.title_button_size,
            self._metrics.title_button_size,
        )
        button.setStyleSheet(button_style(self._theme, self._metrics))
        button.clicked.connect(callback)
        return button

    def _create_window_menu(self) -> ModernMenu:
        menu = ModernMenu(self, metrics=self._metrics)
        self.quitAction = menu.addAction(
            _resource_icon("shutdown.png", self._theme),
            "退出程序",
        )

        def confirm_exit() -> None:
            from .modern_message_box import ModernMessageBox

            answer = ModernMessageBox.question(
                self,
                "确认退出",
                "确定要退出吗？",
                ModernMessageBox.StandardButton.Yes | ModernMessageBox.StandardButton.No,
            )
            if answer == ModernMessageBox.StandardButton.Yes:
                QApplication.quit()

        self.quitAction.triggered.connect(confirm_exit)
        return menu

    def showWindowMenu(self) -> None:
        position = self.menuButton.mapToGlobal(QPoint(0, self.menuButton.height()))
        self.windowMenu.popup(position)

    def contextMenuEvent(self, event) -> None:
        self.parent_window.showSystemWindowMenu(event.globalPos())
        event.accept()

    def syncWindowFlags(self, flags: Qt.WindowType) -> bool:
        window_type = flags & Qt.WindowType.WindowType_Mask
        title_bar_visible = window_type not in {
            Qt.WindowType.Popup,
            Qt.WindowType.ToolTip,
            Qt.WindowType.SplashScreen,
        }
        regular_window = window_type == Qt.WindowType.Window
        customized = bool(flags & Qt.WindowType.CustomizeWindowHint)

        self.menuButton.setVisible(
            regular_window and bool(flags & Qt.WindowType.WindowSystemMenuHint)
        )
        self.pinButton.setVisible(regular_window and not customized)
        self.minimizeButton.setVisible(
            regular_window and bool(flags & Qt.WindowType.WindowMinimizeButtonHint)
        )
        self.maximizeButton.setVisible(
            regular_window and bool(flags & Qt.WindowType.WindowMaximizeButtonHint)
        )
        self.closeButton.setVisible(bool(flags & Qt.WindowType.WindowCloseButtonHint))
        self._sync_pin_state(bool(flags & Qt.WindowType.WindowStaysOnTopHint))
        self.setVisible(title_bar_visible)
        return title_bar_visible

    def _sync_pin_state(self, on_top: bool) -> None:
        self.pinButton.setChecked(on_top)
        self.pinButton.setIcon(_resource_icon("push-pin.png" if on_top else "pin.png", self._theme))
        self.pinButton.setToolTip("取消置顶" if on_top else "置顶")

    def setTheme(self, theme: ModernTheme) -> None:
        super().setTheme(theme)
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
            button.setStyleSheet(button_style(theme, self._metrics))

    def toggleOnTop(self) -> None:
        was_visible = self.parent_window.isVisible()
        window_state = self.parent_window.windowState()
        on_top = self.pinButton.isChecked()
        self.parent_window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on_top)
        self.pinButton.setIcon(_resource_icon("push-pin.png" if on_top else "pin.png", self._theme))
        self.pinButton.setToolTip("取消置顶" if on_top else "置顶")
        self.parent_window.setWindowState(window_state)
        if was_visible:
            self.parent_window.show()
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
        elif self._can_maximize():
            self.parent_window.showMaximized()


class ModernWindow(QWidget):
    """Cross-platform frameless shell with themeable modern chrome."""

    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = _DEFAULT_WINDOW_FLAGS,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        flags = f
        if parent is not None and not flags & Qt.WindowType.WindowType_Mask:
            flags |= Qt.WindowType.Window
        super().__init__(parent, flags)
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self._metrics = metrics
        theme_manager().themeChanged.connect(self._on_global_theme_changed)
        QWidget.setWindowFlag(self, Qt.WindowType.FramelessWindowHint, True)
        self._surface_policy: WindowSurfacePolicy = current_window_surface_policy()
        self._surface_policy.apply_to(self)
        self.setMouseTracking(True)
        self._resize_cursor_active = False
        self._native_frame_enabled = False
        self._native_frame_refresh_pending = False
        self._native_maximize_button_pressed = False
        self._native_caption_press_position: QPoint | None = None
        self._native_caption_anchor_x = 0
        self._native_caption_anchor_from_right = False
        self._native_caption_anchor_y = 0
        self._native_caption_manual_move_offset: QPoint | None = None
        self._application_event_filter_installed = False
        self._screen_change_window: QWindow | None = None
        self._screen_metrics_screen: QScreen | None = None
        self._system_resize_active = False
        self._manual_resize_edges = Qt.Edge(0)
        self._manual_resize_start_position = QPoint()
        self._manual_resize_start_geometry = QRect()
        self._system_resize_watch_timer = QTimer(self)
        self._system_resize_watch_timer.setInterval(50)
        self._system_resize_watch_timer.timeout.connect(self._poll_system_resize_state)
        self._native_frame_sync_timer = QTimer(self)
        self._native_frame_sync_timer.setSingleShot(True)
        self._native_frame_sync_timer.timeout.connect(self._sync_windows_native_frame)
        self._surface_refresh_timer = QTimer(self)
        self._surface_refresh_timer.setSingleShot(True)
        self._surface_refresh_timer.timeout.connect(self._refresh_window_surface)
        self._surface_settle_timer = QTimer(self)
        self._surface_settle_timer.setSingleShot(True)
        self._surface_settle_timer.timeout.connect(self._refresh_window_surface)
        self.cornerRadius = metrics.corner_radius
        self._menu_bar: ModernMenuBar | None = None
        self._status_bar: QStatusBar | None = None
        self.root_layout: QVBoxLayout | None = None
        self.frameLayout: QVBoxLayout | None = None
        self.toolbarLayout: QVBoxLayout | None = None
        self._bottom_toolbar_layout: QVBoxLayout | None = None
        self.content: QWidget | None = None
        self._content_generation = 0
        self.titleBar: CustomTitleBar | None = None
        self.initWindow()
        self.apply_window_style()

    @staticmethod
    def _uses_windows_window_state() -> bool:
        return uses_windows_window_state()

    def setWindowFlags(self, flags: Qt.WindowType) -> None:
        QWidget.setWindowFlags(self, flags | Qt.WindowType.FramelessWindowHint)
        if hasattr(self, "titleBar"):
            self._sync_chrome_with_window_flags()

    def setWindowFlag(self, flag: Qt.WindowType, on: bool = True) -> None:
        QWidget.setWindowFlag(self, flag, on)
        QWidget.setWindowFlag(self, Qt.WindowType.FramelessWindowHint, True)
        if hasattr(self, "titleBar"):
            self._sync_chrome_with_window_flags()

    def _sync_window_state_style(self) -> None:
        is_maximized = self.isMaximized()
        if self.titleBar is not None:
            self.titleBar.updateMaximizeIcon(is_maximized)
            self.titleBar.maximizeButton.setEnabled(self._can_maximize())
        if not self.isMinimized():
            self.apply_window_style()

    def initWindow(self) -> None:
        self.frame = BackgroundFrame(
            self,
            theme=self._theme,
            corner_radius=self._surface_policy.paint_corner_radius(self.cornerRadius),
            opaque_surface=self._surface_policy.opaque_surface,
        )
        self.frame.setObjectName("backgroundFrame")
        self.frame.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        title_bar = CustomTitleBar(
            self,
            theme=self._theme,
            metrics=self._metrics,
        )
        self.titleBar = title_bar
        self.chromeOverlay = WindowChromeOverlay(
            self,
            theme=self._theme,
            corner_radius=self.cornerRadius,
        )
        self.chromeOverlay.setGeometry(self.rect())
        self.chromeOverlay.show()
        self.chromeOverlay.raise_()
        self._sync_chrome_with_window_flags()
        self._layout_chrome()
        self._install_resize_filters(self)

    def _set_application_event_filter_enabled(self, enabled: bool) -> None:
        if enabled == self._application_event_filter_installed:
            return
        application = QApplication.instance()
        if application is None:
            return
        if enabled:
            application.installEventFilter(self)
        else:
            application.removeEventFilter(self)
        self._application_event_filter_installed = enabled

    def _layout_chrome(self) -> None:
        self.frame.setGeometry(self.rect())
        self.frame.lower()
        self.chromeOverlay.setGeometry(self.rect())
        self.chromeOverlay.raise_()
        if self.titleBar is not None:
            self.titleBar.setGeometry(0, 0, self.width(), self.titleBar.height())
            self.titleBar.raise_()

    def _sync_chrome_with_window_flags(self) -> None:
        if self.titleBar is None:
            return
        title_bar_visible = self.titleBar.syncWindowFlags(self.windowFlags())
        self.titleBar.maximizeButton.setEnabled(self._can_maximize())
        top_margin = self.titleBar.height() if title_bar_visible else 0
        QWidget.setContentsMargins(self, 0, top_margin, 0, 0)
        self._layout_chrome()
        self._schedule_native_frame_sync()

    def _schedule_native_frame_sync(self, *, force_refresh: bool = False) -> None:
        if hasattr(self, "_native_frame_sync_timer"):
            self._native_frame_refresh_pending |= force_refresh
            self._native_frame_sync_timer.start(0)

    def _sync_windows_native_frame(self) -> None:
        force_refresh = self._native_frame_refresh_pending
        self._native_frame_refresh_pending = False
        if not self._uses_windows_window_state():
            self._native_frame_enabled = False
            return

        flags = self.windowFlags()
        window_type = flags & Qt.WindowType.WindowType_Mask
        enabled = window_type == Qt.WindowType.Window
        window_handle = self.windowHandle()
        if window_handle is None:
            self._native_frame_enabled = False
            return
        # Set this before SWP_FRAMECHANGED synchronously delivers WM_NCCALCSIZE.
        self._native_frame_enabled = enabled
        applied = set_native_frame(
            int(window_handle.winId()),
            enabled,
            resizable=self._is_resizable(),
            system_menu=bool(flags & Qt.WindowType.WindowSystemMenuHint),
            minimizable=bool(flags & Qt.WindowType.WindowMinimizeButtonHint),
            maximizable=self._can_maximize(),
            force_refresh=force_refresh,
        )
        self._native_frame_enabled = enabled and applied
        if self._native_frame_enabled and self._resize_cursor_active:
            self.unsetCursor()
            self._resize_cursor_active = False

    def _is_resizable(self) -> bool:
        return (
            self.minimumWidth() < self.maximumWidth() or self.minimumHeight() < self.maximumHeight()
        )

    def _can_maximize(self) -> bool:
        flags = self.windowFlags()
        return (
            bool(flags & Qt.WindowType.WindowMaximizeButtonHint)
            and self._size_allows_maximize()
            and not self.isFullScreen()
        )

    def _size_allows_maximize(self) -> bool:
        return (
            self.minimumWidth() < self.maximumWidth()
            and self.minimumHeight() < self.maximumHeight()
        )

    def showMaximized(self) -> None:
        if self._size_allows_maximize():
            QWidget.showMaximized(self)

    def _window_constraints_changed(self) -> None:
        if not hasattr(self, "_native_frame_sync_timer"):
            return
        if not self._size_allows_maximize() and self.isMaximized():
            self.showNormal()
        if self.titleBar is not None:
            self.titleBar.maximizeButton.setEnabled(self._can_maximize())
        self._schedule_native_frame_sync(force_refresh=True)

    def setMinimumSize(self, *args) -> None:
        QWidget.setMinimumSize(self, *args)
        self._window_constraints_changed()

    def setMaximumSize(self, *args) -> None:
        QWidget.setMaximumSize(self, *args)
        self._window_constraints_changed()

    def setFixedSize(self, *args) -> None:
        QWidget.setFixedSize(self, *args)
        self._window_constraints_changed()

    def setMinimumWidth(self, minw: int) -> None:
        QWidget.setMinimumWidth(self, minw)
        self._window_constraints_changed()

    def setMinimumHeight(self, minh: int) -> None:
        QWidget.setMinimumHeight(self, minh)
        self._window_constraints_changed()

    def setMaximumWidth(self, maxw: int) -> None:
        QWidget.setMaximumWidth(self, maxw)
        self._window_constraints_changed()

    def setMaximumHeight(self, maxh: int) -> None:
        QWidget.setMaximumHeight(self, maxh)
        self._window_constraints_changed()

    def setFixedWidth(self, w: int) -> None:
        QWidget.setFixedWidth(self, w)
        self._window_constraints_changed()

    def setFixedHeight(self, h: int) -> None:
        QWidget.setFixedHeight(self, h)
        self._window_constraints_changed()

    def apply_window_style(self) -> None:
        """Apply the same Qt-painted watercolor style on every platform."""
        corner_radius = (
            0 if self.isMaximized() or self.isFullScreen() else max(0, self.cornerRadius)
        )
        paint_corner_radius = self._surface_policy.paint_corner_radius(corner_radius)
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self.frame.setTheme(self._theme)
        self.frame.setCornerRadius(paint_corner_radius)
        if hasattr(self, "chromeOverlay"):
            self.chromeOverlay.setTheme(self._theme)
            self.chromeOverlay.setCornerRadius(paint_corner_radius)
        self._set_native_corner_preference(corner_radius > 0)
        if hasattr(self, "titleBar") and self.titleBar:
            self.titleBar.setTheme(self._theme)
            self.titleBar.raise_()
            self._sync_inactive_title_color()
        menu_bars: Iterable[ModernMenuBar] = self.findChildren(ModernMenuBar)
        for menu_bar in menu_bars:
            menu_bar._apply_theme()
        self.frame.update()
        self.update()

    def _set_native_corner_preference(self, rounded: bool) -> None:
        self._surface_policy.apply_native_corner_preference(self, rounded)

    def showSystemWindowMenu(self, position: QPoint) -> None:
        flags = self.windowFlags()
        if not flags & Qt.WindowType.WindowSystemMenuHint:
            return
        local_position = self.mapFromGlobal(position)
        native_position = screen_position_from_client(
            int(self.winId()),
            local_position.x(),
            local_position.y(),
            self.width(),
            self.height(),
        )
        if native_position is not None and self._show_native_system_menu(native_position):
            return
        self._show_portable_system_menu(position)

    def _show_native_system_menu(self, screen_position: tuple[int, int]) -> bool:
        flags = self.windowFlags()
        if not flags & Qt.WindowType.WindowSystemMenuHint:
            return False
        window_id = int(self.winId())
        move_position = None
        if self.titleBar is not None and self.titleBar.isVisible():
            title_center = QPoint(self.width() // 2, self.titleBar.geometry().center().y())
            move_position = screen_position_from_client(
                window_id,
                title_center.x(),
                title_center.y(),
                self.width(),
                self.height(),
            )
        return _system_menu.show_native_system_menu(
            window_id,
            screen_position,
            move_position=move_position,
            is_minimized=self.isMinimized(),
            is_maximized=self.isMaximized(),
            can_resize=self._is_resizable(),
            can_minimize=bool(flags & Qt.WindowType.WindowMinimizeButtonHint),
            can_maximize=self._can_maximize(),
            can_close=bool(flags & Qt.WindowType.WindowCloseButtonHint),
        )

    def _show_portable_system_menu(self, position: QPoint) -> None:
        flags = self.windowFlags()
        can_minimize = bool(flags & Qt.WindowType.WindowMinimizeButtonHint)
        can_maximize = self._can_maximize()
        can_close = bool(flags & Qt.WindowType.WindowCloseButtonHint)

        menu = ModernMenu(self, metrics=self._metrics)
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        restore_action = menu.addAction("还原", self.showNormal)
        minimize_action = menu.addAction("最小化", self.showMinimized)
        maximize_action = menu.addAction("最大化", self.showMaximized)
        menu.addSeparator()
        close_action = menu.addAction("关闭", self.close)

        is_normal = not self.isMinimized() and not self.isMaximized()
        restore_action.setEnabled(not is_normal)
        minimize_action.setEnabled(can_minimize and not self.isMinimized())
        maximize_action.setEnabled(can_maximize and not self.isMaximized())
        close_action.setEnabled(can_close)
        self._portable_system_menu = menu
        menu.popup(position)

    def theme(self) -> ModernTheme:
        return self._theme

    def setTheme(self, theme: ModernTheme | None) -> None:
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
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
        button.setStyleSheet(button_style(self._theme, self._metrics))
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

    def setTitleVisible(self, visible: bool) -> None:
        """Show or hide title text without changing the window title or icon visibility."""
        if self.titleBar is not None:
            self.titleBar.setTitleVisible(visible)

    def isTitleVisible(self) -> bool:
        """Return whether title text is enabled, even in a hidden window."""
        return self.titleBar is not None and self.titleBar.isTitleVisible()

    def setIconVisible(self, visible: bool) -> None:
        """Show or hide the title bar icon without changing the actual window icon."""
        if self.titleBar is not None:
            self.titleBar.setIconVisible(visible)

    def isIconVisible(self) -> bool:
        """Return the icon visibility setting, even in a hidden window or with no icon."""
        return self.titleBar is not None and self.titleBar.isIconVisible()

    def setTitleAlignment(self, alignment: Literal["left", "center"]) -> None:
        """Align title text left (default) or centered; the icon stays at the left."""
        if self.titleBar is not None:
            self.titleBar.setTitleAlignment(alignment)

    def titleAlignment(self) -> Literal["left", "center"]:
        """Return the configured alignment of the title text."""
        return self.titleBar.titleAlignment() if self.titleBar is not None else "left"

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._set_application_event_filter_enabled(True)
        self._connect_screen_change_signal()
        self._sync_chrome_with_window_flags()
        self._sync_windows_native_frame()
        if not event.spontaneous():
            self.apply_window_style()
        self._schedule_surface_refresh()

    def event(self, event) -> bool:
        handled = super().event(event)
        if event.type() == QEvent.Type.WinIdChange:
            self._schedule_native_frame_sync()
        elif event.type() == QEvent.Type.PlatformSurface and isinstance(
            event, QPlatformSurfaceEvent
        ):
            if event.surfaceEventType() == QPlatformSurfaceEvent.SurfaceEventType.SurfaceCreated:
                self._schedule_native_frame_sync()
            else:
                self._native_frame_enabled = False
        elif event.type() == QEvent.Type.DevicePixelRatioChange:
            self._schedule_native_frame_sync(force_refresh=True)
            self._schedule_surface_refresh()
        elif event.type() in (
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        ):
            self._sync_inactive_title_color()
        return handled

    def nativeEvent(self, event_type, message):
        if not self._uses_windows_window_state():
            return super().nativeEvent(event_type, message)

        try:
            native_message = read_message(int(message))
        except (TypeError, ValueError):
            return super().nativeEvent(event_type, message)

        if (
            native_message.message == WM_NCLBUTTONDBLCLK
            and native_message.w_param == HTCAPTION
            and self._native_frame_enabled
        ):
            self._cancel_native_caption_drag(native_message.hwnd)
            if self._can_maximize():
                QTimer.singleShot(0, self.showNormal if self.isMaximized() else self.showMaximized)
            return True, 0

        if native_message.message == WM_SYSCOMMAND and self._native_frame_enabled:
            # DefWindowProc's caption double-click and system menu must use the
            # same state path as our buttons. Native maximization of a Qt
            # frameless window otherwise loses Qt's saved normal geometry.
            command = native_message.w_param & 0xFFF0
            if command == _system_menu.SC_MAXIMIZE:
                if self._can_maximize():
                    QTimer.singleShot(0, self.showMaximized)
                return True, 0
            if command == _system_menu.SC_RESTORE:
                QTimer.singleShot(0, self._restore_from_native_command)
                return True, 0

        if native_message.message in (WM_DISPLAYCHANGE, WM_DPICHANGED):
            self._schedule_native_frame_sync(force_refresh=True)
            self._schedule_surface_refresh()
        if native_message.message == WM_NCCALCSIZE and self._native_frame_enabled:
            if native_message.w_param:
                constrain_maximized_client_area(native_message.hwnd, native_message.l_param)
            return True, 0
        if native_message.message == WM_NCHITTEST and self._native_frame_enabled:
            position = client_position_from_l_param(
                native_message.hwnd,
                native_message.l_param,
                self.width(),
                self.height(),
            )
            if position is not None:
                hit_test = self._native_hit_test_at(QPoint(round(position[0]), round(position[1])))
                if hit_test is not None:
                    return True, hit_test
        elif native_message.message == WM_NCMOUSEMOVE:
            hovered = native_message.w_param == HTMAXBUTTON
            self._set_native_maximize_button_hovered(hovered)
            if hovered:
                track_non_client_mouse_leave(native_message.hwnd)
        elif native_message.message == WM_NCMOUSELEAVE:
            self._set_native_maximize_button_hovered(False)
            self._cancel_native_maximize_button_press()
        elif native_message.message == WM_NCLBUTTONDOWN and native_message.w_param == HTMAXBUTTON:
            self._native_maximize_button_pressed = True
            self._set_native_maximize_button_down(True)
            return True, 0
        elif (
            native_message.message == WM_NCLBUTTONDOWN
            and native_message.w_param == HTCAPTION
            and self.isMaximized()
        ):
            self._begin_native_caption_drag(native_message.hwnd, native_message.l_param)
            return True, 0
        elif native_message.message == WM_NCRBUTTONUP and native_message.w_param == HTCAPTION:
            screen_position = screen_position_from_l_param(native_message.l_param)
            if self._show_native_system_menu(screen_position):
                return True, 0
        elif native_message.message == WM_NCLBUTTONUP:
            if self._native_caption_press_position is not None:
                self._cancel_native_caption_drag(native_message.hwnd)
                return True, 0
            pressed = self._native_maximize_button_pressed
            self._cancel_native_maximize_button_press()
            if native_message.w_param == HTMAXBUTTON or pressed:
                if pressed and native_message.w_param == HTMAXBUTTON and self.titleBar is not None:
                    QTimer.singleShot(0, self.titleBar.maximizeButton.click)
                return True, 0
        elif native_message.message == WM_MOUSEMOVE and (
            self._native_caption_press_position is not None
            or self._native_caption_manual_move_offset is not None
        ):
            self._continue_native_caption_drag(native_message.hwnd)
            return True, 0
        elif native_message.message == WM_LBUTTONUP and (
            self._native_caption_press_position is not None
            or self._native_caption_manual_move_offset is not None
        ):
            self._cancel_native_caption_drag(native_message.hwnd)
            return True, 0
        elif native_message.message == WM_CAPTURECHANGED:
            self._cancel_native_maximize_button_press()
            self._clear_native_caption_drag()
        elif native_message.message == WM_ENTERSIZEMOVE:
            self._begin_system_resize_tracking(poll_mouse_buttons=False)
        elif native_message.message == WM_EXITSIZEMOVE:
            self._finish_system_resize_tracking()
            self._sync_window_state_style()
        return super().nativeEvent(event_type, message)

    def _restore_from_native_command(self) -> None:
        if self.isMinimized():
            # Restoring a minimized maximized window keeps it maximized.
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
            self.show()
        else:
            self.showNormal()

    def _set_native_maximize_button_hovered(self, hovered: bool) -> None:
        if self.titleBar is None:
            return
        button = self.titleBar.maximizeButton
        if bool(button.property("nativeHover")) == hovered:
            return
        button.setProperty("nativeHover", hovered)
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()

    def _set_native_maximize_button_down(self, down: bool) -> None:
        if self.titleBar is not None:
            self.titleBar.maximizeButton.setDown(down)

    def _cancel_native_maximize_button_press(self) -> None:
        self._native_maximize_button_pressed = False
        self._set_native_maximize_button_down(False)

    def _begin_native_caption_drag(self, hwnd: int, l_param: int) -> None:
        # Use the press message, not a later cursor sample: the mouse may have
        # already moved by the time Qt delivers the non-client button press.
        client_position = client_position_from_l_param(hwnd, l_param, self.width(), self.height())
        if client_position is None:
            position = QCursor.pos()
            local_position = self.mapFromGlobal(position)
        else:
            local_position = QPoint(round(client_position[0]), round(client_position[1]))
            position = self.mapToGlobal(local_position)
        self._native_caption_press_position = position
        self._native_caption_anchor_from_right = local_position.x() > self.width() // 2
        self._native_caption_anchor_x = max(
            0,
            self.width() - local_position.x()
            if self._native_caption_anchor_from_right
            else local_position.x(),
        )
        title_height = self.titleBar.height() if self.titleBar is not None else 0
        self._native_caption_anchor_y = max(0, min(local_position.y(), title_height))
        self._native_caption_manual_move_offset = None
        set_mouse_capture(hwnd, True)

    def _continue_native_caption_drag(self, hwnd: int) -> None:
        position = QCursor.pos()
        if self._native_caption_manual_move_offset is not None:
            self.move(position - self._native_caption_manual_move_offset)
            return

        press_position = self._native_caption_press_position
        if press_position is None:
            return
        if (position - press_position).manhattanLength() < QApplication.startDragDistance():
            return

        normal_geometry = self.normalGeometry()
        if not normal_geometry.isValid():
            normal_geometry = self.geometry()
        restored_width = normal_geometry.width()
        restored_height = normal_geometry.height()
        # Preserve the distance from the nearest edge. Scaling the offset by
        # the window width shifts blank caption space onto fixed-width buttons.
        anchor_x = min(self._native_caption_anchor_x, restored_width // 2)
        if self._native_caption_anchor_from_right:
            anchor_x = restored_width - anchor_x
        restored_top_left = QPoint(
            position.x() - anchor_x,
            position.y() - self._native_caption_anchor_y,
        )

        self._native_caption_press_position = None
        self.showNormal()
        self.setGeometry(
            restored_top_left.x(),
            restored_top_left.y(),
            restored_width,
            restored_height,
        )

        set_mouse_capture(hwnd, False)
        if start_system_move(hwnd):
            return

        # Preserve dragging if the platform rejects the native move operation.
        self._native_caption_manual_move_offset = position - self.frameGeometry().topLeft()
        set_mouse_capture(hwnd, True)

    def _cancel_native_caption_drag(self, hwnd: int) -> None:
        self._clear_native_caption_drag()
        set_mouse_capture(hwnd, False)

    def _clear_native_caption_drag(self) -> None:
        self._native_caption_press_position = None
        self._native_caption_manual_move_offset = None

    def _native_hit_test_at(self, position: QPoint) -> int | None:
        if not self._native_frame_enabled:
            return None
        if self.isFullScreen():
            return HTCLIENT

        if not self.isMaximized():
            horizontal_resize = self.minimumWidth() < self.maximumWidth()
            vertical_resize = self.minimumHeight() < self.maximumHeight()
            left = horizontal_resize and position.x() < 8
            right = horizontal_resize and position.x() >= self.width() - 8
            top = vertical_resize and position.y() < 8
            bottom = vertical_resize and position.y() >= self.height() - 8
            if top and left:
                return HTTOPLEFT
            if top and right:
                return HTTOPRIGHT
            if bottom and left:
                return HTBOTTOMLEFT
            if bottom and right:
                return HTBOTTOMRIGHT
            if left:
                return HTLEFT
            if right:
                return HTRIGHT
            if top:
                return HTTOP
            if bottom:
                return HTBOTTOM

        title_bar = self.titleBar
        if (
            title_bar is None
            or not title_bar.isVisible()
            or not title_bar.geometry().contains(position)
        ):
            return None

        title_position = title_bar.mapFrom(self, position)
        if (
            self._can_maximize()
            and title_bar.maximizeButton.isVisible()
            and title_bar.maximizeButton.geometry().contains(title_position)
        ):
            return HTMAXBUTTON

        child = title_bar.childAt(title_position)
        if child is None or child in (title_bar.iconLabel, title_bar.titleLabel):
            return HTCAPTION
        return None

    def _connect_screen_change_signal(self) -> None:
        window_handle = self.windowHandle()
        if window_handle is None:
            return
        if window_handle is not self._screen_change_window:
            if self._screen_change_window is not None:
                try:
                    self._screen_change_window.screenChanged.disconnect(self._handle_screen_changed)
                except (RuntimeError, TypeError):
                    pass
            self._screen_change_window = window_handle
            window_handle.screenChanged.connect(self._handle_screen_changed)
        self._connect_screen_metric_signals(window_handle.screen())

    def _connect_screen_metric_signals(self, screen: QScreen | None) -> None:
        if screen is self._screen_metrics_screen:
            return
        old_screen = self._screen_metrics_screen
        if old_screen is not None:
            for signal_name in (
                "geometryChanged",
                "availableGeometryChanged",
                "logicalDotsPerInchChanged",
                "physicalDotsPerInchChanged",
            ):
                try:
                    signal = getattr(old_screen, signal_name)
                    signal.disconnect(self._handle_screen_metrics_changed)
                except (RuntimeError, TypeError):
                    pass
            try:
                old_screen.destroyed.disconnect(self._handle_screen_destroyed)
            except (RuntimeError, TypeError):
                pass
        self._screen_metrics_screen = screen
        if screen is not None:
            screen.geometryChanged.connect(self._handle_screen_metrics_changed)
            screen.availableGeometryChanged.connect(self._handle_screen_metrics_changed)
            screen.logicalDotsPerInchChanged.connect(self._handle_screen_metrics_changed)
            screen.physicalDotsPerInchChanged.connect(self._handle_screen_metrics_changed)
            screen.destroyed.connect(self._handle_screen_destroyed)

    def _handle_screen_destroyed(self, _object=None) -> None:
        self._screen_metrics_screen = None

    def _handle_screen_changed(self, screen: QScreen | None) -> None:
        self._connect_screen_metric_signals(screen)
        self._handle_screen_metrics_changed()

    def _handle_screen_metrics_changed(self, *_args) -> None:
        self._schedule_native_frame_sync(force_refresh=True)
        self._schedule_surface_refresh()

    def _disconnect_screen_change_signals(self) -> None:
        self._connect_screen_metric_signals(None)
        window_handle = self._screen_change_window
        self._screen_change_window = None
        if window_handle is not None:
            try:
                window_handle.screenChanged.disconnect(self._handle_screen_changed)
            except (RuntimeError, TypeError):
                pass

    def _schedule_surface_refresh(self) -> None:
        if not hasattr(self, "_surface_refresh_timer"):
            return
        self._surface_refresh_timer.start(0)
        self._surface_settle_timer.start(100)

    def _refresh_window_surface(self) -> None:
        if not self.isVisible() or self.isMinimized():
            return
        self.frame.invalidateSurfaceCache()
        self._layout_chrome()
        self.repaint()
        window_handle = self.windowHandle()
        if window_handle is not None:
            window_handle.requestUpdate()
            if self._uses_windows_window_state():
                redraw_native_window(int(window_handle.winId()))

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

    def _ensure_compatibility_layout(self) -> None:
        if self.root_layout is not None:
            return
        if self.layout() is not None:
            raise RuntimeError(
                "QMainWindow-compatible APIs cannot be mixed with a layout installed "
                "directly on ModernWindow"
            )

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        self.frameLayout = self.root_layout
        self.toolbarLayout = QVBoxLayout()
        self.toolbarLayout.setSpacing(0)
        self.root_layout.addLayout(self.toolbarLayout)
        self.content = QWidget(self)
        self.root_layout.addWidget(self.content)
        self._track_content(self.content)
        self._bottom_toolbar_layout = QVBoxLayout()
        self._bottom_toolbar_layout.setSpacing(0)
        self.root_layout.addLayout(self._bottom_toolbar_layout)

    def _clear_menu_bar(self, _object: object | None = None) -> None:
        self._menu_bar = None

    def _clear_status_bar(self, _object: object | None = None) -> None:
        self._status_bar = None

    def _track_content(self, widget: QWidget | None) -> None:
        self._content_generation += 1
        generation = self._content_generation
        self.content = widget
        if widget is not None:
            widget.destroyed.connect(
                lambda _object=None, generation=generation: self._clear_content(generation)
            )

    def _clear_content(self, generation: int) -> None:
        if generation == self._content_generation:
            self.content = None

    def menuBar(self) -> ModernMenuBar:
        if self._menu_bar is None:
            self._ensure_compatibility_layout()
            assert self.frameLayout is not None
            self._menu_bar = ModernMenuBar(self, metrics=self._metrics)
            self._menu_bar.destroyed.connect(self._clear_menu_bar)
            self.frameLayout.insertWidget(0, self._menu_bar)
            self._install_resize_filters(self._menu_bar)
            self._sync_inactive_title_color()
        return self._menu_bar

    def addToolBar(self, *args: object) -> QToolBar:
        area = Qt.ToolBarArea.TopToolBarArea
        if len(args) == 1 and isinstance(args[0], QToolBar):
            toolbar = args[0]
        elif len(args) == 1 and isinstance(args[0], str):
            toolbar = QToolBar(args[0], self)
        elif (
            len(args) == 2 and isinstance(args[0], Qt.ToolBarArea) and isinstance(args[1], QToolBar)
        ):
            area = args[0]
            toolbar = args[1]
        else:
            raise TypeError(
                "addToolBar() expects a QToolBar, a title, or a (Qt.ToolBarArea, QToolBar) pair"
            )

        if area not in (
            Qt.ToolBarArea.TopToolBarArea,
            Qt.ToolBarArea.BottomToolBarArea,
        ):
            raise TypeError("ModernWindow supports only top and bottom toolbar areas")

        self._ensure_compatibility_layout()
        assert self.toolbarLayout is not None
        toolbar.setStyleSheet("QToolBar { background: transparent; border: none; }")
        if area == Qt.ToolBarArea.TopToolBarArea:
            self.toolbarLayout.addWidget(toolbar)
        else:
            assert self._bottom_toolbar_layout is not None
            self._bottom_toolbar_layout.addWidget(toolbar)
        self._install_resize_filters(toolbar)
        return toolbar

    def statusBar(self) -> QStatusBar:
        if self._status_bar is None:
            self._ensure_compatibility_layout()
            assert self.frameLayout is not None
            self._status_bar = QStatusBar(self)
            self._status_bar.destroyed.connect(self._clear_status_bar)
            self._status_bar.setStyleSheet("QStatusBar { background: transparent; border: none; }")
            self._status_bar.setSizeGripEnabled(False)
            self.frameLayout.addWidget(self._status_bar)
            self._install_resize_filters(self._status_bar)
        return self._status_bar

    def setCentralWidget(self, widget: QWidget | None) -> None:
        if widget is not None and not isinstance(widget, QWidget):
            raise TypeError("setCentralWidget() expects a QWidget or None")
        self._ensure_compatibility_layout()
        assert self.frameLayout is not None
        if widget is self.content:
            return
        previous = self.content
        if previous is not None:
            self.frameLayout.removeWidget(previous)
        self._track_content(widget)
        if previous is not None:
            previous.deleteLater()
        if widget is None:
            return

        assert self._bottom_toolbar_layout is not None
        bottom_layout_index = next(
            index
            for index in range(self.frameLayout.count())
            if self.frameLayout.itemAt(index).layout() is self._bottom_toolbar_layout
        )
        self.frameLayout.insertWidget(bottom_layout_index, widget)
        self._install_resize_filters(widget)

    def setCornerRadius(self, radius: int) -> None:
        self.cornerRadius = radius
        self.apply_window_style()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMaximized() or self.isFullScreen():
                self._set_resize_cursor(Qt.Edge(0))
            self._sync_window_state_style()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "chromeOverlay"):
            self._layout_chrome()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        if hasattr(self, "_surface_settle_timer"):
            self._surface_settle_timer.start(100)

    @staticmethod
    def _has_pressed_mouse_buttons() -> bool:
        return QApplication.mouseButtons() != Qt.MouseButton.NoButton

    def _begin_system_resize_tracking(self, *, poll_mouse_buttons: bool = True) -> None:
        if self._system_resize_active:
            return
        self._system_resize_active = True
        self.frame.setLiveResize(True)
        if poll_mouse_buttons:
            self._system_resize_watch_timer.start()

    def _finish_system_resize_tracking(self) -> None:
        was_active = self._system_resize_active
        self._system_resize_active = False
        self._system_resize_watch_timer.stop()
        if was_active:
            self.frame.setLiveResize(False)

    def _poll_system_resize_state(self) -> None:
        if not self._has_pressed_mouse_buttons():
            self._finish_system_resize_tracking()

    def hideEvent(self, event) -> None:
        self._finish_manual_resize()
        self._finish_system_resize_tracking()
        self._disconnect_screen_change_signals()
        self._set_application_event_filter_enabled(False)
        super().hideEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if (
            isinstance(watched, QWidget)
            and watched.window() is self
            and not watched.hasMouseTracking()
        ):
            watched.setMouseTracking(True)

        if (
            not self._native_frame_enabled
            and isinstance(watched, QWidget)
            and watched.window() is self
        ):
            event_type = event.type()
            if event_type == QEvent.Type.MouseMove:
                if self._manual_resize_edges:
                    if event.buttons() & Qt.MouseButton.LeftButton:
                        self._update_manual_resize(event.globalPosition().toPoint())
                        return True
                    self._finish_manual_resize()
                position = watched.mapTo(self, event.position().toPoint())
                edges = self._resize_edges_at(position)
                self._set_resize_cursor(edges)
            elif event_type == QEvent.Type.MouseButtonPress:
                position = watched.mapTo(self, event.position().toPoint())
                edges = self._resize_edges_at(position)
                if event.button() == Qt.MouseButton.LeftButton and edges:
                    handle = self.windowHandle()
                    if handle is not None and handle.startSystemResize(edges):
                        self._begin_system_resize_tracking()
                        return True
                    if not QApplication.platformName().startswith("wayland"):
                        self._begin_manual_resize(edges, event.globalPosition().toPoint())
                        return True
            elif event_type == QEvent.Type.MouseButtonRelease:
                self._finish_manual_resize()
                self._finish_system_resize_tracking()
        return super().eventFilter(watched, event)

    def _begin_manual_resize(self, edges: Qt.Edge, global_position: QPoint) -> None:
        self._manual_resize_edges = edges
        self._manual_resize_start_position = global_position
        self._manual_resize_start_geometry = self.geometry()
        self._begin_system_resize_tracking()

    def _update_manual_resize(self, global_position: QPoint) -> None:
        delta = global_position - self._manual_resize_start_position
        self.setGeometry(
            manual_resize_geometry(
                self,
                self._manual_resize_start_geometry,
                self._manual_resize_edges,
                delta,
            )
        )

    def _finish_manual_resize(self) -> None:
        self._manual_resize_edges = Qt.Edge(0)

    def _install_resize_filters(self, widget: QWidget) -> None:
        widget.setMouseTracking(True)
        for child in widget.children():
            if isinstance(child, QWidget):
                self._install_resize_filters(child)

    def _resize_edges_at(self, position: QPoint) -> Qt.Edge:
        if self.isMaximized() or self.isFullScreen():
            return Qt.Edge(0)

        border_width = 8
        edges = Qt.Edge(0)
        if self.minimumWidth() < self.maximumWidth():
            if position.x() < border_width:
                edges |= Qt.Edge.LeftEdge
            elif position.x() >= self.width() - border_width:
                edges |= Qt.Edge.RightEdge
        if self.minimumHeight() < self.maximumHeight():
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
            self.titleBar.deleteLater()
            self.titleBar = None
            QWidget.setContentsMargins(self, 0, 0, 0, 0)
