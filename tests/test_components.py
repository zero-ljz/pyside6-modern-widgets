from __future__ import annotations

import os
from dataclasses import replace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QContextMenuEvent, QFont, QIcon, QPalette, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QLabel,
    QMainWindow,
    QMenuBar,
    QStatusBar,
    QTabBar,
    QTabWidget,
    QToolButton,
    QWidget,
)

from pyside6_modern_widgets import (
    DARK_THEME,
    DEFAULT_METRICS,
    LIGHT_THEME,
    ModernWindow,
    NavigationPosition,
    NavigationSidebar,
    NavigationView,
    TabView,
    theme_manager,
)

_APP = QApplication.instance() or QApplication([])


def _application() -> QApplication:
    return _APP


def test_modern_window_preserves_base_window_api() -> None:
    _application()
    window = ModernWindow()
    assert isinstance(window, QWidget)
    assert not isinstance(window, QMainWindow)
    assert window.layout() is window.root_layout
    assert window.titleBar is not None
    assert window.titleBar.parent() is window.frame
    for icon_name in (
        "pin.png",
        "push-pin.png",
        "minimize.png",
        "maximize.png",
        "restore.png",
        "shutdown.png",
        "menu.png",
        "expand-arrow.png",
    ):
        icon = QIcon(f":/pyside6_modern_widgets/icons/{icon_name}")
        assert not icon.isNull()
    for attribute in (
        "frame",
        "chromeOverlay",
        "frameLayout",
        "toolbarLayout",
        "content",
        "titleBar",
        "cornerRadius",
    ):
        assert hasattr(window, attribute)
    for method in (
        "initWindow",
        "apply_window_style",
        "addTitleBarButton",
        "menuBar",
        "addToolBar",
        "statusBar",
        "setCentralWidget",
        "setCornerRadius",
        "showSystemWindowMenu",
        "hideTitleBar",
    ):
        assert callable(getattr(window, method))

    central = QLabel("content")
    window.setCentralWidget(central)
    assert window.content is central

    assert isinstance(window.menuBar(), QMenuBar)
    status_bar = window.statusBar()
    assert isinstance(status_bar, QStatusBar)
    assert "border: none" in status_bar.styleSheet()
    toolbar = window.addToolBar("Tools")
    assert window.toolbarLayout.indexOf(toolbar) >= 0


def test_title_bar_menu_button_and_native_context_menu(monkeypatch) -> None:
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()

    assert window.titleBar is not None
    title_bar = window.titleBar
    assert not title_bar.menuButton.icon().isNull()
    assert title_bar.main_layout.indexOf(title_bar.menuButton) < title_bar.main_layout.indexOf(
        title_bar.pinButton
    )
    assert "contextMenuEvent" in type(title_bar).__dict__
    assert [action.text() for action in title_bar.windowMenu.actions()] == ["退出程序"]

    QTest.mouseClick(title_bar.menuButton, Qt.MouseButton.LeftButton)
    _application().processEvents()
    assert title_bar.windowMenu.isVisible()
    title_bar.windowMenu.hide()

    observed: list[QPoint] = []
    monkeypatch.setattr(
        ModernWindow,
        "showSystemWindowMenu",
        lambda _window, position: observed.append(position),
    )
    local_position = QPoint(20, 10)
    global_position = title_bar.mapToGlobal(local_position)
    context_event = QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse,
        local_position,
        global_position,
    )
    QApplication.sendEvent(title_bar, context_event)
    assert observed == [global_position]


def test_title_bar_reserves_vertical_space_around_window_buttons() -> None:
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()

    assert window.titleBar is not None
    title_bar = window.titleBar
    assert title_bar.height() == DEFAULT_METRICS.title_bar_height
    for button in (
        title_bar.menuButton,
        title_bar.pinButton,
        title_bar.minimizeButton,
        title_bar.maximizeButton,
        title_bar.closeButton,
    ):
        assert button.geometry().top() >= 2
        assert button.geometry().bottom() <= title_bar.rect().bottom() - 2


def test_system_menu_has_cross_platform_qt_fallback(monkeypatch) -> None:
    from pyside6_modern_widgets import _system_menu

    monkeypatch.setattr(_system_menu, "show_native_system_menu", lambda *args, **kwargs: False)
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()

    window.showSystemWindowMenu(window.mapToGlobal(QPoint(20, 20)))
    _application().processEvents()

    menu = window._portable_system_menu
    assert menu.isVisible()
    assert [action.text() for action in menu.actions() if not action.isSeparator()] == [
        "还原",
        "最小化",
        "最大化",
        "关闭",
    ]
    menu.hide()


def test_native_system_menu_rebuilds_stale_windows_menu(monkeypatch) -> None:
    import ctypes

    from pyside6_modern_widgets import _system_menu

    class StubFunction:
        def __init__(self, callback):
            self.callback = callback
            self.argtypes = None
            self.restype = None

        def __call__(self, *args):
            return self.callback(*args)

    class StubUser32:
        def __init__(self) -> None:
            self.get_system_menu_calls: list[bool] = []
            self.track_error = 0
            self.track_command = 0
            self.GetSystemMenu = StubFunction(self._get_system_menu)
            self.EnableMenuItem = StubFunction(lambda *_args: True)
            self.TrackPopupMenu = StubFunction(self._track_popup_menu)
            self.SetForegroundWindow = StubFunction(lambda *_args: True)
            self.GetDpiForWindow = StubFunction(lambda *_args: 144)
            self.ClientToScreen = StubFunction(self._client_to_screen)
            self.PostMessageW = StubFunction(self._post_message)
            self.posted_messages: list[tuple[int, int]] = []
            self.track_position: tuple[int, int] | None = None

        def _get_system_menu(self, _hwnd, revert) -> int:
            self.get_system_menu_calls.append(bool(revert))
            return 0 if revert else 123

        def _track_popup_menu(self, *_args) -> int:
            self.track_position = (_args[2], _args[3])
            ctypes.set_last_error(self.track_error)
            return self.track_command

        def _post_message(self, _hwnd, message, command, _lparam) -> bool:
            self.posted_messages.append((message, command))
            return True

        @staticmethod
        def _client_to_screen(_hwnd, point_pointer) -> bool:
            point_pointer._obj.x += 1000
            point_pointer._obj.y += 500
            return True

    user32 = StubUser32()
    monkeypatch.setattr(_system_menu.sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: user32)

    assert _system_menu.show_native_system_menu(
        100,
        QPoint(20, 20),
        is_minimized=False,
        is_maximized=False,
    )
    assert user32.get_system_menu_calls == [True, False]
    assert user32.track_position == (1030, 530)

    handled_commands: list[int] = []
    user32.track_command = _system_menu.SC_RESTORE
    assert _system_menu.show_native_system_menu(
        100,
        QPoint(20, 20),
        is_minimized=False,
        is_maximized=True,
        command_handler=lambda command: handled_commands.append(command) or True,
    )
    assert handled_commands == [_system_menu.SC_RESTORE]
    assert all(message != 0x0112 for message, _command in user32.posted_messages)

    user32.track_command = 0
    user32.track_error = 1401
    assert not _system_menu.show_native_system_menu(
        100,
        QPoint(20, 20),
        is_minimized=False,
        is_maximized=False,
    )


def test_native_system_menu_restore_uses_qt_window_state(monkeypatch) -> None:
    from pyside6_modern_widgets import _system_menu

    def choose_restore(*_args, command_handler, **_kwargs) -> bool:
        assert command_handler(_system_menu.SC_RESTORE)
        return True

    monkeypatch.setattr(_system_menu, "show_native_system_menu", choose_restore)
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()

    assert window.titleBar is not None
    title_bar = window.titleBar
    QTest.mouseDClick(
        title_bar,
        Qt.MouseButton.LeftButton,
        pos=title_bar.titleLabel.geometry().center(),
    )
    _application().processEvents()
    assert window.isMaximized()

    window.showSystemWindowMenu(window.mapToGlobal(QPoint(20, 20)))
    _application().processEvents()
    assert not window.isMaximized()

    QTest.mouseClick(title_bar.maximizeButton, Qt.MouseButton.LeftButton)
    _application().processEvents()
    assert window.isMaximized()

    window.showSystemWindowMenu(window.mapToGlobal(QPoint(20, 20)))
    _application().processEvents()
    assert not window.isMaximized()


def test_native_system_menu_maximize_can_be_restored_by_title_bar_button(monkeypatch) -> None:
    from pyside6_modern_widgets import _system_menu

    def choose_maximize(*_args, command_handler, **_kwargs) -> bool:
        assert command_handler(_system_menu.SC_MAXIMIZE)
        return True

    monkeypatch.setattr(_system_menu, "show_native_system_menu", choose_maximize)
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()

    assert window.titleBar is not None
    window.showSystemWindowMenu(window.mapToGlobal(QPoint(20, 20)))
    _application().processEvents()
    assert window.isMaximized()

    QTest.mouseClick(window.titleBar.maximizeButton, Qt.MouseButton.LeftButton)
    _application().processEvents()
    assert not window.isMaximized()


def test_windows_maximize_uses_native_state_when_qt_state_is_stale(monkeypatch) -> None:
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()

    native_state = {"maximized": False}
    commands: list[int] = []
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: True)
    monkeypatch.setattr(window, "_is_native_maximized", lambda: native_state["maximized"])

    def show_native_window(command: int) -> None:
        commands.append(command)
        native_state["maximized"] = command == 3

    monkeypatch.setattr(window, "_show_native_window", show_native_window)

    QWidget.showMaximized(window)
    _application().processEvents()
    assert QWidget.isMaximized(window)
    assert not window.isMaximized()

    assert window.titleBar is not None
    window.titleBar.changeMaximize()
    assert commands == [3]
    assert window.isMaximized()


def test_windows_native_restore_preserves_normal_geometry(monkeypatch) -> None:
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()
    normal_geometry = window.geometry()

    native_state = {"maximized": False}
    commands: list[int] = []
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: True)
    monkeypatch.setattr(window, "_is_native_maximized", lambda: native_state["maximized"])

    def show_native_window(command: int) -> None:
        commands.append(command)
        native_state["maximized"] = command == 3
        if native_state["maximized"]:
            window.setGeometry(0, 0, 1280, 720)

    monkeypatch.setattr(window, "_show_native_window", show_native_window)

    window.showMaximized()
    assert window.geometry() != normal_geometry
    window.showNormal()

    assert commands == [3, 9]
    assert not window.isMaximized()
    assert window.geometry() == normal_geometry


@pytest.mark.parametrize(
    ("show_method", "expected_command"),
    [("showNormal", 9), ("showMaximized", 3)],
)
def test_windows_native_show_restores_qt_visibility(
    monkeypatch, show_method: str, expected_command: int
) -> None:
    window = ModernWindow()
    commands: list[int] = []
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: True)
    monkeypatch.setattr(window, "_show_native_window", commands.append)

    assert window.isHidden()

    getattr(window, show_method)()
    _application().processEvents()

    assert window.isVisible()
    assert commands == [expected_command]
    window.close()


def test_non_windows_window_state_stays_managed_by_qt(monkeypatch) -> None:
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()
    normal_geometry = window.geometry()
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: False)

    window.showMaximized()
    _application().processEvents()

    assert window.isMaximized()
    assert window._normal_geometry_before_maximize is None

    window.showNormal()
    _application().processEvents()

    assert not window.isMaximized()
    assert window.geometry() == normal_geometry
    window.close()


def test_screen_change_preserves_stable_normal_size(monkeypatch) -> None:
    window = ModernWindow()
    window.resize(900, 600)
    window._normal_logical_size = QSize(900, 600)
    window._screen_device_pixel_ratio = 2.0
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: True)
    monkeypatch.setattr(window._screen_resize_correction_timer, "start", lambda _delay: None)

    class ScreenStub:
        @staticmethod
        def devicePixelRatio() -> float:
            return 1.0

    window._handle_screen_changed(ScreenStub())
    window.resize(1800, 1200)
    window._screen_device_pixel_ratio = 1.0

    class PrimaryScreenStub:
        @staticmethod
        def devicePixelRatio() -> float:
            return 2.0

    window._handle_screen_changed(PrimaryScreenStub())
    window.resize(450, 300)
    window._correct_screen_change_size()

    assert window.size() == QSize(900, 600)

    window._screen_device_pixel_ratio = 2.0
    window._system_resize_active = True
    window._handle_screen_changed(ScreenStub())
    window.resize(1200, 800)
    window._correct_screen_change_size()

    assert window.size() == QSize(1200, 800)


def test_non_windows_screen_change_does_not_force_cached_size(monkeypatch) -> None:
    window = ModernWindow()
    window.resize(900, 600)
    window._normal_logical_size = QSize(900, 600)
    window._screen_device_pixel_ratio = 2.0
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: False)

    class ScreenStub:
        @staticmethod
        def devicePixelRatio() -> float:
            return 1.0

    window._handle_screen_changed(ScreenStub())
    window.resize(1200, 800)
    window._correct_screen_change_size()

    assert not window._screen_change_in_progress
    assert window.size() == QSize(1200, 800)


def test_system_resize_tracking_clears_after_native_mouse_loop(monkeypatch) -> None:
    window = ModernWindow()
    window._begin_system_resize_tracking()

    assert window._system_resize_active
    assert window._system_resize_watch_timer.isActive()

    monkeypatch.setattr(window, "_has_pressed_mouse_buttons", lambda: True)
    window._poll_system_resize_state()
    assert window._system_resize_active

    monkeypatch.setattr(window, "_has_pressed_mouse_buttons", lambda: False)
    window._poll_system_resize_state()
    assert not window._system_resize_active
    assert not window._system_resize_watch_timer.isActive()


def test_native_system_menu_move_and_size_use_qt_system_operations(monkeypatch) -> None:
    from pyside6_modern_widgets import _system_menu

    window = ModernWindow()
    window.setGeometry(100, 100, 640, 480)
    monkeypatch.setattr(window, "grabMouse", lambda: None)
    monkeypatch.setattr(window, "grabKeyboard", lambda: None)
    monkeypatch.setattr(window, "releaseMouse", lambda: None)
    monkeypatch.setattr(window, "releaseKeyboard", lambda: None)

    assert window._handle_native_system_menu_command(_system_menu.SC_MOVE)
    start_cursor = window._system_menu_start_cursor
    window._update_system_menu_operation(start_cursor + QPoint(40, 25))
    assert window.geometry() == QRect(140, 125, 640, 480)
    window._finish_system_menu_operation(cancel=False)

    assert window._handle_native_system_menu_command(_system_menu.SC_SIZE)
    start_cursor = window._system_menu_start_cursor
    window._update_system_menu_operation(start_cursor + QPoint(60, 35))
    assert window.geometry() == QRect(140, 125, 700, 515)
    window._finish_system_menu_operation(cancel=True)
    assert window.geometry() == QRect(140, 125, 640, 480)


def test_modern_window_does_not_overwrite_consumer_styles() -> None:
    window = ModernWindow()
    content = QLabel("content")
    content.setStyleSheet("QLabel { color: #123456; }")
    window.setCentralWidget(content)
    window.setStyleSheet("ModernWindow { background: #ABCDEF; }")

    window.apply_window_style()

    assert window.styleSheet() == "ModernWindow { background: #ABCDEF; }"
    assert content.styleSheet() == "QLabel { color: #123456; }"
    assert "QLabel" not in window.frame.styleSheet()


def test_navigation_sidebar_selection_and_collapse() -> None:
    _application()
    sidebar = NavigationSidebar()
    observed: list[int] = []
    sidebar.currentChanged.connect(observed.append)
    assert sidebar.addItem("First") == 0
    assert sidebar.addItem("Second") == 1

    sidebar.setCurrentIndex(1)
    assert sidebar.currentIndex() == 1
    assert observed == [1]
    sidebar.setCollapsed(True, animated=False)
    assert sidebar.isCollapsed()
    assert sidebar.width() == 48


def test_collapsed_navigation_ignores_application_button_padding() -> None:
    app = _application()
    previous_style = app.styleSheet()
    try:
        app.setStyleSheet("QPushButton { padding: 7px 16px; }")
        icon_color = QColor("#0088CC")
        pixmap = QPixmap(18, 18)
        pixmap.fill(icon_color)
        sidebar = NavigationSidebar()
        sidebar.addItem("Item", QIcon(pixmap))
        sidebar.setCurrentIndex(0)
        sidebar.setCollapsed(True, animated=False)
        sidebar.resize(DEFAULT_METRICS.navigation_collapsed_width, 240)
        sidebar.show()
        app.processEvents()

        button = sidebar.button(0)
        assert button is not None
        viewport_width = sidebar.scrollArea.viewport().width()
        assert sidebar.scrollContent.width() <= viewport_width
        assert button.width() <= viewport_width
        image = button.grab().toImage()
        icon_x_positions = [
            x
            for y in range(image.height())
            for x in range(image.width())
            if image.pixelColor(x, y) == icon_color
        ]
        assert min(icon_x_positions) == 9
        assert max(icon_x_positions) == 26
    finally:
        app.setStyleSheet(previous_style)


def test_navigation_icons_stay_fixed_when_collapse_changes() -> None:
    icon_color = QColor("#0088CC")
    pixmap = QPixmap(18, 18)
    pixmap.fill(icon_color)
    toggle_color = QColor("#CC4400")
    toggle_pixmap = QPixmap(20, 20)
    toggle_pixmap.fill(toggle_color)

    sidebar = NavigationSidebar()
    sidebar.addItem("Item", QIcon(pixmap))
    sidebar.toggleButton.setIcon(QIcon(toggle_pixmap))
    sidebar.setCurrentIndex(0)
    sidebar.setCollapsed(True, animated=False)
    sidebar.resize(48, 240)
    sidebar.show()
    _application().processEvents()

    button = sidebar.button(0)
    assert button is not None

    def icon_bounds(widget: QWidget, color: QColor) -> tuple[int, int]:
        image = widget.grab().toImage()
        x_positions = [
            x
            for y in range(image.height())
            for x in range(image.width())
            if image.pixelColor(x, y) == color
        ]
        assert x_positions
        return min(x_positions), max(x_positions)

    collapsed_item_bounds = icon_bounds(button, icon_color)
    collapsed_toggle_bounds = icon_bounds(sidebar.toggleButton, toggle_color)
    assert sum(collapsed_item_bounds) / 2 == (button.width() - 1) / 2
    assert sum(collapsed_toggle_bounds) / 2 == (sidebar.toggleButton.width() - 1) / 2

    sidebar.setCollapsed(False, animated=False)
    _application().processEvents()

    assert icon_bounds(button, icon_color) == collapsed_item_bounds
    assert icon_bounds(sidebar.toggleButton, toggle_color) == collapsed_toggle_bounds


def test_navigation_focus_is_borderless_and_keeps_toggle_icon_centered() -> None:
    focus_background = "#FF4FA3"
    focus_color = QColor("#00FF00")
    theme = replace(
        LIGHT_THEME,
        control_hover=focus_background,
        focus=focus_color.name(),
    )
    sidebar = NavigationSidebar(theme=theme)
    sidebar.addItem("Item")
    toggle_color = QColor("#CC4400")
    toggle_pixmap = QPixmap(20, 20)
    toggle_pixmap.fill(toggle_color)
    sidebar.toggleButton.setIcon(QIcon(toggle_pixmap))
    sidebar.resize(240, 240)
    sidebar.show()
    _application().processEvents()

    button = sidebar.button(0)
    assert button is not None
    assert button.focusPolicy() == Qt.FocusPolicy.StrongFocus

    button.setFocus(Qt.FocusReason.TabFocusReason)
    _application().processEvents()
    focused_image = button.grab().toImage()
    assert focused_image.pixelColor(button.width() // 2, 0) == QColor(focus_background)
    assert all(
        focused_image.pixelColor(x, y) != focus_color
        for y in range(focused_image.height())
        for x in range(focused_image.width())
    )

    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    _application().processEvents()
    assert button.hasFocus()
    selected_image = button.grab().toImage()
    assert selected_image.pixelColor(button.width() // 2, 0) == QColor(theme.control_pressed)
    assert all(
        selected_image.pixelColor(x, y) != focus_color
        for y in range(selected_image.height())
        for x in range(selected_image.width())
    )

    button.clearFocus()
    sidebar.toggleButton.setFocus(Qt.FocusReason.BacktabFocusReason)
    _application().processEvents()
    assert sidebar.toggleButton.width() == DEFAULT_METRICS.navigation_collapsed_width - 12
    assert sidebar.toggleButton.grab().toImage().pixelColor(
        sidebar.toggleButton.width() // 2, 0
    ) == QColor(focus_background)

    QTest.mouseClick(sidebar.toggleButton, Qt.MouseButton.LeftButton)
    QTest.qWait(DEFAULT_METRICS.animation_duration + 20)
    image = sidebar.toggleButton.grab().toImage()
    assert image.pixelColor(sidebar.toggleButton.width() // 2, 0) == QColor(focus_background)
    icon_x_positions = [
        x
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y) == toggle_color
    ]
    assert icon_x_positions
    assert (min(icon_x_positions) + max(icon_x_positions)) / 2 == (
        sidebar.toggleButton.width() - 1
    ) / 2


def test_navigation_view_manages_pages_and_selection() -> None:
    _application()
    view = NavigationView()
    first = QLabel("first")
    second = QLabel("second")

    assert view.addPage(first, "First") == 0
    assert (
        view.addPage(
            second,
            "Second",
            position=NavigationPosition.BOTTOM,
        )
        == 1
    )
    assert view.count() == 2
    assert view.currentWidget() is first
    assert view.sidebar.count() == 2
    assert "border-bottom: none" in view.contentContainer.styleSheet()

    view.setCurrentIndex(1)
    assert view.currentIndex() == 1
    assert view.sidebar.currentIndex() == 1

    removed = view.removePage(0)
    assert removed is first
    assert removed.parent() is None
    assert view.count() == 1
    assert view.widget(0) is second
    assert view.sidebar.count() == 1


def test_tab_view_uses_native_tab_semantics_and_qtabwidget_api() -> None:
    _application()
    tabs = TabView()
    assert isinstance(tabs, QWidget)
    assert not isinstance(tabs, QTabWidget)
    first = QLabel("first")
    second = QLabel("second")
    assert tabs.addTab(first, "First") == 0
    assert tabs.insertTab(0, second, "Second") == 0
    assert tabs.widget(0) is second
    assert tabs.indexOf(first) == 1
    assert not tabs.tabIcon(0).isNull()
    tab_bar = tabs.tabBar()
    assert isinstance(tab_bar, QTabBar)
    assert tab_bar.count() == 2
    assert tab_bar.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert tab_bar.accessibleName() == "Document tabs"

    tabs.setTabText(0, "Updated")
    tabs.setTabToolTip(0, "Updated tab")
    assert tabs.tabText(0) == "Updated"
    assert tabs.tabToolTip(0) == "Updated tab"

    tabs.setCurrentIndex(0)
    tabs.resize(600, 400)
    tabs.show()
    _application().processEvents()
    assert tab_bar.tabRect(0).width() > 80
    close_buttons = tab_bar.findChildren(QAbstractButton)
    assert any(button.accessibleName() == "Close Updated" for button in close_buttons)

    observed: list[int] = []
    tabs.currentChanged.connect(observed.append)
    tabs.setCurrentIndex(0)
    assert tabs.currentWidget() is second

    tabs.removeTab(0)
    assert tabs.count() == 1
    assert tabs.indexOf(first) == 0
    assert second.parent() is not None
    assert observed[-1] == 0


def test_tab_view_keyboard_disabled_state_and_page_moves() -> None:
    tabs = TabView()
    pages = [QLabel(str(index)) for index in range(3)]
    for index, page in enumerate(pages):
        tabs.addTab(page, f"Tab {index}")
    tabs.setTabEnabled(1, False)
    tabs.resize(600, 300)
    tabs.show()
    tabs.tabBar().setFocus()
    tabs.setCurrentIndex(0)
    assert not tabs.tabBar()._keyboard_focus_visible

    QTest.keyClick(tabs.tabBar(), Qt.Key.Key_Right)
    assert tabs.tabBar()._keyboard_focus_visible
    assert tabs.currentIndex() == 2
    assert tabs.currentWidget() is pages[2]

    QTest.mouseClick(
        tabs.tabBar(),
        Qt.MouseButton.LeftButton,
        pos=tabs.tabBar().tabRect(0).center(),
    )
    assert not tabs.tabBar()._keyboard_focus_visible
    current_page = tabs.currentWidget()

    tabs.tabBar().moveTab(2, 0)
    assert tabs.widget(0) is pages[2]
    assert tabs.currentWidget() is current_page


def test_tab_view_middle_click_requests_tab_close() -> None:
    tabs = TabView()
    tabs.addTab(QLabel("first"), "First")
    tabs.addTab(QLabel("second"), "Second")
    tabs.resize(600, 300)
    tabs.show()
    _application().processEvents()
    observed: list[int] = []
    tabs.tabCloseRequested.connect(observed.append)

    QTest.mouseClick(
        tabs.tabBar(),
        Qt.MouseButton.MiddleButton,
        pos=tabs.tabBar().tabRect(1).center(),
    )

    assert observed == [1]


def test_tab_view_overflow_buttons_use_modern_scroll_controls() -> None:
    tabs = TabView(theme=LIGHT_THEME)
    for index in range(8):
        tabs.addTab(QLabel(str(index)), f"Document {index + 1}")
    tabs.resize(460, 300)
    tabs.show()
    _application().processEvents()

    tab_bar = tabs.tabBar()
    left = tab_bar.findChild(QToolButton, "ScrollLeftButton")
    right = tab_bar.findChild(QToolButton, "ScrollRightButton")

    assert left is not None
    assert right is not None
    assert left.isVisible()
    assert right.isVisible()
    assert left.width() == 28
    assert right.width() == 28
    assert left.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert right.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert left.accessibleName() == "Previous tabs"
    assert right.accessibleName() == "Next tabs"
    assert left.grab().toImage().pixelColor(0, 0) == QColor(LIGHT_THEME.tab_bar)
    right_image = right.grab().toImage()
    assert right_image.pixelColor(0, 0) == QColor(LIGHT_THEME.tab_bar)
    assert all(
        right_image.pixelColor(right_image.width() - 1, y) == QColor(LIGHT_THEME.tab_bar)
        for y in range(right_image.height())
    )

    right.hide()
    tab_bar.update()
    _application().processEvents()
    assert tab_bar.grab().toImage().pixelColor(
        tab_bar.width() - 1, tab_bar.height() // 2
    ) == QColor(LIGHT_THEME.tab_bar)
    right.show()

    assert not left.isEnabled()
    assert right.isEnabled()
    QTest.mouseClick(right, Qt.MouseButton.LeftButton)
    _application().processEvents()
    assert left.isEnabled()
    assert not right.hasFocus()


def test_tab_view_has_no_divider_below_tab_row() -> None:
    tabs = TabView(theme=LIGHT_THEME)
    tabs.addTab(QLabel("first"), "First")
    tabs.addTab(QLabel("second"), "Second")
    tabs.resize(600, 300)
    tabs.show()
    _application().processEvents()

    tab_bar = tabs.tabBar()
    image = tab_bar.grab().toImage()
    bottom = tab_bar.height() - 1

    assert tabs.findChild(QWidget, "ModernTabDivider") is None
    assert image.pixelColor(tab_bar.tabRect(0).center().x(), bottom) == QColor(
        LIGHT_THEME.tab_selected
    )
    assert image.pixelColor(tab_bar.tabRect(1).center().x(), bottom) == QColor(LIGHT_THEME.tab_bar)


def test_tab_view_rejects_removed_reverse_icon_signature() -> None:
    tabs = TabView()
    with pytest.raises(TypeError):
        tabs.addTab(QLabel("page"), "Title", QIcon())


def test_runtime_theme_updates_and_local_overrides() -> None:
    manager = theme_manager()
    manager.setTheme(LIGHT_THEME)
    tabs = TabView()
    navigation = NavigationView()
    local_tabs = TabView(theme=LIGHT_THEME)

    try:
        manager.setTheme(DARK_THEME)
        assert tabs.theme() is DARK_THEME
        assert navigation.theme() is DARK_THEME
        assert local_tabs.theme() is LIGHT_THEME
        assert DARK_THEME.surface in tabs._stack.styleSheet()
        assert DARK_THEME.navigation_content in navigation.contentContainer.styleSheet()
        page = QLabel("dark page")
        tabs.addTab(page, "Dark")
        assert page.palette().color(QPalette.ColorRole.WindowText) == QColor(DARK_THEME.text)
    finally:
        manager.setTheme(LIGHT_THEME)


def test_custom_metrics_scale_fixed_format_controls() -> None:
    metrics = replace(
        DEFAULT_METRICS,
        tab_height=48,
        navigation_item_height=44,
        navigation_collapsed_width=56,
    )
    tabs = TabView(metrics=metrics)
    navigation = NavigationSidebar(metrics=metrics)
    navigation.addItem("Item")

    assert tabs.tabBar().height() == 50
    assert navigation.button(0).height() == 44
    navigation.setCollapsed(True, animated=False)
    assert navigation.width() == 56


def test_tab_height_expands_for_accessibility_fonts() -> None:
    tabs = TabView()
    font = QFont(tabs.font())
    font.setPointSize(24)
    tabs.setFont(font)
    tabs.addTab(QLabel("page"), "Large text")
    tabs.show()
    _application().processEvents()

    assert tabs.tabBar().tabRect(0).height() >= tabs.tabBar().fontMetrics().height() + 12


def test_theme_manager_can_follow_application_palette() -> None:
    manager = theme_manager()
    manager.setTheme(LIGHT_THEME)
    manager.setFollowsSystemTheme(True)
    palette = QPalette(_application().palette())
    palette.setColor(QPalette.ColorRole.Window, QColor("#202020"))

    try:
        _application().setPalette(palette)
        _application().processEvents()
        assert manager.theme() is DARK_THEME
    finally:
        manager.setTheme(LIGHT_THEME)


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
def test_theme_painter_colors_are_valid(theme) -> None:
    for color in (
        theme.text,
        theme.text_disabled,
        theme.surface,
        theme.control_hover,
        theme.control_pressed,
        theme.watercolor_base,
        *(spot[0] for spot in theme.watercolor_spots),
    ):
        assert QColor(color).isValid(), color


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
def test_modern_window_uses_cross_platform_watercolor(theme) -> None:
    window = ModernWindow(theme=theme)
    window.resize(640, 480)
    window.apply_window_style()

    assert window.frame._theme is theme
    assert QColor(theme.watercolor_base).alpha() == 255
    assert window.titleBar is not None
    assert not window.titleBar.autoFillBackground()


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
def test_modern_window_watercolor_covers_title_bar_and_preserves_round_corners(theme) -> None:
    window = ModernWindow(theme=theme)
    window.resize(640, 480)
    window.show()
    _application().processEvents()

    image = window.grab().toImage()
    assert image.pixelColor(1, 1).alpha() < 128
    assert image.pixelColor(window.width() - 2, 1).alpha() < 128
    assert window.titleBar is not None
    title_center = window.titleBar.geometry().center()
    assert image.pixelColor(title_center) != QColor(theme.surface)


def test_opaque_tab_view_preserves_window_bottom_corners_and_border() -> None:
    window = ModernWindow(theme=LIGHT_THEME)
    tabs = TabView(theme=LIGHT_THEME)
    tabs.addTab(QLabel("page"), "Tab")
    window.setCentralWidget(tabs)
    window.resize(640, 480)
    window.show()
    _application().processEvents()

    image = window.grab().toImage()
    assert image.pixelColor(0, window.height() - 1).alpha() == 0
    assert image.pixelColor(window.width() - 1, window.height() - 1).alpha() == 0
    assert image.pixelColor(window.width() // 2, window.height() - 1) == QColor(LIGHT_THEME.border)
    assert image.pixelColor(0, window.height() // 2) == QColor(LIGHT_THEME.border)

    assert window.frame.mask().isEmpty()
    corner_alphas = {
        image.pixelColor(x, window.height() - y - 1).alpha()
        for x in range(window.cornerRadius + 2)
        for y in range(window.cornerRadius + 2)
    }
    assert any(0 < alpha < 255 for alpha in corner_alphas)


def test_modern_window_resize_edges_are_platform_independent() -> None:
    window = ModernWindow()
    window.resize(640, 480)

    assert window._resize_edges_at(window.rect().topLeft()) == (Qt.Edge.TopEdge | Qt.Edge.LeftEdge)
    assert window._resize_edges_at(window.rect().center()) == Qt.Edge(0)
    assert window._resize_edges_at(window.rect().bottomRight()) == (
        Qt.Edge.BottomEdge | Qt.Edge.RightEdge
    )


def test_modern_window_refreshes_entire_surface_after_screen_change() -> None:
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()

    assert window._screen_change_window is window.windowHandle()
    window.chromeOverlay.setGeometry(0, 0, 1, 1)
    window._handle_screen_changed(window.windowHandle().screen())
    assert window._surface_refresh_timer.isActive()
    assert window._surface_settle_timer.isActive()

    _application().processEvents()
    assert window.chromeOverlay.geometry() == window.rect()
    window._surface_settle_timer.stop()


def test_modern_window_surface_refresh_is_asynchronous(monkeypatch) -> None:
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()
    repaint_calls: list[bool] = []
    monkeypatch.setattr(window, "repaint", lambda: repaint_calls.append(True))

    window._refresh_window_surface()

    assert repaint_calls == []


def test_modern_window_refreshes_surface_after_device_pixel_ratio_change() -> None:
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()

    window._surface_refresh_timer.stop()
    window._surface_settle_timer.stop()
    QApplication.sendEvent(window, QEvent(QEvent.Type.DevicePixelRatioChange))

    assert window._surface_refresh_timer.isActive()
    assert window._surface_settle_timer.isActive()
    window._surface_refresh_timer.stop()
    window._surface_settle_timer.stop()


def test_modern_window_refreshes_surface_after_moving_stops() -> None:
    window = ModernWindow()
    window.resize(640, 480)
    window.show()
    _application().processEvents()

    window._surface_settle_timer.stop()
    window.move(window.pos() + QPoint(20, 20))
    _application().processEvents()

    assert window._surface_settle_timer.isActive()
    window._surface_settle_timer.stop()


def test_tab_view_default_visual_colors() -> None:
    tabs = TabView(theme=LIGHT_THEME)
    tabs.addTab(QLabel("first"), "First")
    tabs.addTab(QLabel("second"), "Second")
    tabs.resize(600, 300)
    tabs.show()
    _application().processEvents()

    image = tabs.grab().toImage()
    selected = image.pixelColor(100, 30)
    bar = image.pixelColor(500, 30)
    assert selected == QColor(LIGHT_THEME.tab_selected)
    assert bar == QColor(LIGHT_THEME.tab_bar)
