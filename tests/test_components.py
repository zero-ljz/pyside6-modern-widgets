from __future__ import annotations

import os
from dataclasses import replace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPalette
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
    ):
        icon = QIcon(f":/pyside6_modern_widgets/icons/{icon_name}")
        assert not icon.isNull()
    for attribute in (
        "effect_manager",
        "frame",
        "frameLayout",
        "toolbarLayout",
        "content",
        "titleBar",
        "cornerRadius",
    ):
        assert hasattr(window, attribute)
    for method in (
        "initWindow",
        "apply_window_effect",
        "addTitleBarButton",
        "menuBar",
        "addToolBar",
        "statusBar",
        "setCentralWidget",
        "setCornerRadius",
        "on_screen_changed",
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


def test_modern_window_does_not_overwrite_consumer_styles() -> None:
    window = ModernWindow()
    content = QLabel("content")
    content.setStyleSheet("QLabel { color: #123456; }")
    window.setCentralWidget(content)
    window.setStyleSheet("ModernWindow { background: #ABCDEF; }")

    window.apply_window_effect()

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
        theme.control_hover,
        theme.control_pressed,
        theme.surface_translucent,
        *(spot[0] for spot in theme.watercolor_spots),
    ):
        assert QColor(color).isValid(), color


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
