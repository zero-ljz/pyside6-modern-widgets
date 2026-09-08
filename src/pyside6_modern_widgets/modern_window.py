"""A QWidget-based frameless window with selected QMainWindow-compatible APIs."""

from __future__ import annotations

from typing import cast

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPalette, QPixmap, QWindow
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
    WM_NCCALCSIZE,
    WM_NCHITTEST,
    WM_NCLBUTTONDOWN,
    WM_NCLBUTTONUP,
    WM_NCMOUSELEAVE,
    WM_NCMOUSEMOVE,
    WM_NCRBUTTONUP,
    client_position_from_l_param,
    constrain_maximized_client_area,
    read_message,
    screen_position_from_client,
    screen_position_from_l_param,
    set_native_frame,
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
        else:
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
        self._screen_change_window: QWindow | None = None
        self._system_resize_active = False
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

    def _sync_window_state_style(self) -> None:
        is_maximized = self.isMaximized()
        if self.titleBar is not None:
            self.titleBar.updateMaximizeIcon(is_maximized)
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
        self._schedule_native_frame_sync()

    def _schedule_native_frame_sync(self) -> None:
        if hasattr(self, "_native_frame_sync_timer"):
            self._native_frame_sync_timer.start(0)

    def _sync_windows_native_frame(self) -> None:
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
            maximizable=bool(flags & Qt.WindowType.WindowMaximizeButtonHint),
        )
        self._native_frame_enabled = enabled and applied
        if self._native_frame_enabled and self._resize_cursor_active:
            self.unsetCursor()
            self._resize_cursor_active = False

    def _is_resizable(self) -> bool:
        return (
            self.minimumWidth() < self.maximumWidth() or self.minimumHeight() < self.maximumHeight()
        )

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
            can_maximize=bool(flags & Qt.WindowType.WindowMaximizeButtonHint),
            can_close=bool(flags & Qt.WindowType.WindowCloseButtonHint),
        )

    def _show_portable_system_menu(self, position: QPoint) -> None:
        flags = self.windowFlags()
        can_minimize = bool(flags & Qt.WindowType.WindowMinimizeButtonHint)
        can_maximize = bool(flags & Qt.WindowType.WindowMaximizeButtonHint)
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

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._connect_screen_change_signal()
        self._sync_chrome_with_window_flags()
        self._sync_windows_native_frame()
        if not event.spontaneous():
            self.apply_window_style()
        self._schedule_surface_refresh()

    def event(self, event) -> bool:
        handled = super().event(event)
        if event.type() in (
            QEvent.Type.WinIdChange,
            QEvent.Type.PlatformSurface,
        ):
            self._schedule_native_frame_sync()
        elif event.type() == QEvent.Type.DevicePixelRatioChange:
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
        elif native_message.message == WM_NCLBUTTONDOWN and native_message.w_param == HTMAXBUTTON:
            self._set_native_maximize_button_down(True)
        elif native_message.message == WM_NCRBUTTONUP and native_message.w_param == HTCAPTION:
            screen_position = screen_position_from_l_param(native_message.l_param)
            if self._show_native_system_menu(screen_position):
                return True, 0
        elif native_message.message in (WM_NCLBUTTONUP, WM_CAPTURECHANGED):
            self._set_native_maximize_button_down(False)
        elif native_message.message == WM_ENTERSIZEMOVE:
            self._begin_system_resize_tracking(poll_mouse_buttons=False)
        elif native_message.message == WM_EXITSIZEMOVE:
            self._finish_system_resize_tracking()
            self._sync_window_state_style()
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

    def _set_native_maximize_button_down(self, down: bool) -> None:
        if self.titleBar is not None:
            self.titleBar.maximizeButton.setDown(down)

    def _native_hit_test_at(self, position: QPoint) -> int | None:
        if not self._native_frame_enabled:
            return None

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
        flags = self.windowFlags()
        if (
            flags & Qt.WindowType.WindowMaximizeButtonHint
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
        if window_handle is None or window_handle is self._screen_change_window:
            return
        self._screen_change_window = window_handle
        window_handle.screenChanged.connect(self._handle_screen_changed)

    def _handle_screen_changed(self, _screen) -> None:
        self._schedule_surface_refresh()

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
            not self._native_frame_enabled
            and isinstance(watched, QWidget)
            and watched.window() is self
        ):
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
