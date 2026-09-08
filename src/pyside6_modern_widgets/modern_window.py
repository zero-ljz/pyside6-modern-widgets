"""A QWidget-based frameless window with selected QMainWindow-compatible APIs."""

from __future__ import annotations

from typing import cast

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QIcon, QPalette, QPixmap, QWindow
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
    uses_windows_window_state,
)
from ._windows_window import (
    HTBOTTOM,
    HTBOTTOMLEFT,
    HTBOTTOMRIGHT,
    HTCAPTION,
    HTLEFT,
    HTMAXBUTTON,
    HTRIGHT,
    HTTOP,
    HTTOPLEFT,
    HTTOPRIGHT,
    WM_CAPTURECHANGED,
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
    client_position_from_l_param,
    constrain_maximized_client_area,
    read_message,
    set_mouse_capture,
    set_native_frame,
    start_system_move_or_resize,
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
        self.setVisible(title_bar_visible)
        return title_bar_visible

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

    def _sync_maximize_icon(self) -> None:
        self.updateMaximizeIcon(self.parent_window.isMaximized())


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
        self._native_maximize_button_pressed = False
        self._normal_geometry_before_maximize: QRect | None = None
        self._screen_change_window: QWindow | None = None
        self._screen_device_pixel_ratio: float | None = None
        self._normal_logical_size = QSize(self.size())
        self._screen_change_in_progress = False
        self._system_move_active = False
        self._system_resize_active = False
        self._system_resize_watch_timer = QTimer(self)
        self._system_resize_watch_timer.setInterval(50)
        self._system_resize_watch_timer.timeout.connect(self._poll_system_resize_state)
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
        self._menu_bar: ModernMenuBar | None = None
        self._status_bar: QStatusBar | None = None
        self.root_layout: QVBoxLayout | None = None
        self.frameLayout: QVBoxLayout | None = None
        self.toolbarLayout: QVBoxLayout | None = None
        self.content: QWidget | None = None
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
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def _layout_chrome(self) -> None:
        self.frame.setGeometry(self.rect())
        self.frame.lower()
        if self.titleBar is not None:
            self.titleBar.setGeometry(0, 0, self.width(), self.titleBar.height())
            self.titleBar.raise_()
        self.chromeOverlay.setGeometry(self.rect())
        self.chromeOverlay.raise_()

    def _sync_chrome_with_window_flags(self) -> None:
        if self.titleBar is None:
            return
        title_bar_visible = self.titleBar.syncWindowFlags(self.windowFlags())
        top_margin = self.titleBar.height() if title_bar_visible else 0
        QWidget.setContentsMargins(self, 0, top_margin, 0, 0)
        self._layout_chrome()
        self._sync_windows_native_frame()

    def _sync_windows_native_frame(self) -> None:
        if not self._uses_windows_window_state():
            self._native_frame_enabled = False
            return

        flags = self.windowFlags()
        window_type = flags & Qt.WindowType.WindowType_Mask
        enabled = (
            window_type == Qt.WindowType.Window
            and bool(flags & Qt.WindowType.WindowSystemMenuHint)
            and bool(flags & Qt.WindowType.WindowMaximizeButtonHint)
        )
        self._native_frame_enabled = enabled
        if not set_native_frame(int(self.winId()), enabled):
            self._native_frame_enabled = False

    def apply_window_style(self) -> None:
        """Apply the same Qt-painted watercolor style on every platform."""
        corner_radius = 0 if self.isMaximized() else max(0, self.cornerRadius)
        paint_corner_radius = self._surface_policy.paint_corner_radius(corner_radius)
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self.frame.setTheme(self._theme)
        self.frame.setCornerRadius(paint_corner_radius)
        if hasattr(self, "chromeOverlay"):
            self.chromeOverlay.setTheme(self._theme)
            self.chromeOverlay.setCornerRadius(paint_corner_radius)
            self.chromeOverlay.raise_()
        self._set_native_corner_preference(corner_radius > 0)
        if hasattr(self, "titleBar") and self.titleBar:
            self.titleBar.setTheme(self._theme)
            self._sync_inactive_title_color()
        if self._menu_bar is not None:
            self._menu_bar.setStyleSheet(_menu_bar_style(self._theme, self._metrics))
        self.frame.update()
        self.update()

    def _set_native_corner_preference(self, rounded: bool) -> None:
        self._surface_policy.apply_native_corner_preference(self, rounded)

    def showSystemWindowMenu(self, position: QPoint) -> None:
        if _system_menu.show_native_system_menu(
            int(self.winId()),
            self.mapFromGlobal(position),
            is_minimized=self.isMinimized(),
            is_maximized=self.isMaximized(),
            command_handler=self._handle_native_system_menu_command,
        ):
            return

        menu = ModernMenu(self, metrics=self._metrics)
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

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._connect_screen_change_signal()
        self._sync_chrome_with_window_flags()
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

    def nativeEvent(self, event_type, message):
        if not self._uses_windows_window_state():
            return super().nativeEvent(event_type, message)

        try:
            native_message = read_message(int(message))
        except (TypeError, ValueError):
            return super().nativeEvent(event_type, message)

        if (
            native_message.message == WM_NCCALCSIZE
            and getattr(self, "_native_frame_enabled", False)
            and native_message.w_param
        ):
            constrain_maximized_client_area(int(self.winId()), native_message.l_param)
            return True, 0
        if native_message.message == WM_NCHITTEST and self._native_frame_enabled:
            position = client_position_from_l_param(
                int(self.winId()),
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
                track_non_client_mouse_leave(int(self.winId()))
        elif native_message.message == WM_NCMOUSELEAVE:
            self._set_native_maximize_button_hovered(False)
        elif native_message.message == WM_NCLBUTTONDOWN and native_message.w_param == HTMAXBUTTON:
            self._native_maximize_button_pressed = True
            if self.titleBar is not None:
                self.titleBar.maximizeButton.setDown(True)
            set_mouse_capture(int(self.winId()), True)
            return True, 0
        elif native_message.message == WM_NCLBUTTONDOWN:
            if start_system_move_or_resize(int(self.winId()), native_message.w_param):
                self._system_move_active = native_message.w_param == HTCAPTION
                if self._system_move_active:
                    self._normal_logical_size = QSize(self.size())
                return True, 0
        elif native_message.message == WM_NCLBUTTONDBLCLK and native_message.w_param == HTCAPTION:
            if self.titleBar is not None:
                QTimer.singleShot(0, self.titleBar.changeMaximize)
            return True, 0
        elif native_message.message == WM_NCRBUTTONUP and native_message.w_param == HTCAPTION:
            QTimer.singleShot(0, lambda: self.showSystemWindowMenu(QCursor.pos()))
            return True, 0
        elif native_message.message == WM_NCLBUTTONUP and self._native_maximize_button_pressed:
            self._finish_native_maximize_button_press(native_message.w_param == HTMAXBUTTON)
            return True, 0
        elif native_message.message == WM_MOUSEMOVE and self._native_maximize_button_pressed:
            if self.titleBar is not None:
                self.titleBar.maximizeButton.setDown(
                    self._native_hit_test_at(self.mapFromGlobal(QCursor.pos())) == HTMAXBUTTON
                )
        elif native_message.message == WM_LBUTTONUP and self._native_maximize_button_pressed:
            self._finish_native_maximize_button_press(
                self._native_hit_test_at(self.mapFromGlobal(QCursor.pos())) == HTMAXBUTTON
            )
            return True, 0
        elif native_message.message == WM_CAPTURECHANGED and self._native_maximize_button_pressed:
            self._finish_native_maximize_button_press(False, release_capture=False)
        elif native_message.message == WM_ENTERSIZEMOVE:
            if not self._system_move_active:
                self._begin_system_resize_tracking(poll_mouse_buttons=False)
        elif native_message.message == WM_EXITSIZEMOVE:
            self._system_move_active = False
            self._finish_system_resize_tracking()
            self._schedule_window_state_style_sync()
        return super().nativeEvent(event_type, message)

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

    def _finish_native_maximize_button_press(
        self, activate: bool, *, release_capture: bool = True
    ) -> None:
        self._native_maximize_button_pressed = False
        if self.titleBar is not None:
            self.titleBar.maximizeButton.setDown(False)
            if activate:
                QTimer.singleShot(0, self.titleBar.changeMaximize)
        if release_capture:
            set_mouse_capture(int(self.winId()), False)

    def _native_hit_test_at(self, position: QPoint) -> int | None:
        if not self._native_frame_enabled:
            return None

        if not self.isMaximized():
            left = position.x() < 8
            right = position.x() >= self.width() - 8
            top = position.y() < 8
            bottom = position.y() >= self.height() - 8
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
        if title_bar.maximizeButton.isVisible() and title_bar.maximizeButton.geometry().contains(
            title_position
        ):
            return HTMAXBUTTON

        child = title_bar.childAt(title_position)
        if child is None or child in (title_bar.iconLabel, title_bar.titleLabel):
            return HTCAPTION
        return None

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

    def menuBar(self) -> ModernMenuBar:
        if self._menu_bar is None:
            self._ensure_compatibility_layout()
            assert self.frameLayout is not None
            self._menu_bar = ModernMenuBar(self, metrics=self._metrics)
            self._menu_bar.setStyleSheet(_menu_bar_style(self._theme, self._metrics))
            self.frameLayout.insertWidget(0, self._menu_bar)
            self._install_resize_filters(self._menu_bar)
            self._sync_inactive_title_color()
        return self._menu_bar

    def addToolBar(self, *args) -> QToolBar:
        self._ensure_compatibility_layout()
        assert self.toolbarLayout is not None
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
            self._ensure_compatibility_layout()
            assert self.frameLayout is not None
            self._status_bar = QStatusBar(self)
            self._status_bar.setStyleSheet("QStatusBar { background: transparent; border: none; }")
            self._status_bar.setSizeGripEnabled(False)
            self.frameLayout.addWidget(self._status_bar)
            self._install_resize_filters(self._status_bar)
        return self._status_bar

    def setCentralWidget(self, widget: QWidget) -> None:
        self._ensure_compatibility_layout()
        assert self.frameLayout is not None
        assert self.content is not None
        if widget is self.content:
            return
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
            and not self._system_move_active
            and not self.isMaximized()
            and not self.isMinimized()
        ):
            self._normal_logical_size = QSize(event.size())
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
        self._system_move_active = False
        self._finish_system_resize_tracking()
        super().hideEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if (
            isinstance(watched, QWidget)
            and watched.window() is self
            and not watched.hasMouseTracking()
        ):
            watched.setMouseTracking(True)

        if isinstance(watched, QWidget) and watched.window() is self:
            event_type = event.type()
            if event_type == QEvent.Type.MouseMove:
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
            self.titleBar.deleteLater()
            self.titleBar = None
            QWidget.setContentsMargins(self, 0, 0, 0, 0)
