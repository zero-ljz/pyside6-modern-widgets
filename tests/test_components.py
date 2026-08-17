from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenuBar,
    QStatusBar,
    QStyleFactory,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyside6_modern_widgets import (
    ModernWindow,
    NavigationPosition,
    NavigationSidebar,
    NavigationView,
    TabView,
    ThemeMode,
    WindowMaterial,
)

_APP = QApplication.instance() or QApplication([])


def _application() -> QApplication:
    return _APP


def test_modern_window_preserves_base_window_api() -> None:
    _application()
    window = ModernWindow()
    assert isinstance(window, QWidget)
    assert not isinstance(window, QMainWindow)
    for icon_name in (
        "pin.png",
        "push-pin.png",
        "minimize.png",
        "maximize.png",
        "restore.png",
        "shutdown.png",
        "menu.png",
        "account.png",
        "application.png",
        "home.png",
        "search.png",
        "settings.png",
        "sun.png",
        "night.png",
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
        "addTitleBarButton",
        "menuBar",
        "addToolBar",
        "statusBar",
        "setCentralWidget",
        "setCornerRadius",
        "on_screen_changed",
        "hideTitleBar",
        "setWindowEffectsEnabled",
        "setWindowMaterial",
        "setThemeMode",
        "windowEffectsEnabled",
        "windowMaterial",
        "themeMode",
        "resolvedThemeMode",
        "toggleThemeMode",
    ):
        assert callable(getattr(window, method))

    assert window.windowEffectsEnabled()
    assert window.windowMaterial() is WindowMaterial.AUTO
    assert window.themeMode() is ThemeMode.LIGHT
    assert not window.titleBar.themeButton.icon().isNull()

    central = QLabel("content")
    window.setCentralWidget(central)
    assert window.content is central

    assert isinstance(window.menuBar(), QMenuBar)
    status_bar = window.statusBar()
    assert isinstance(status_bar, QStatusBar)
    assert "border: none" in status_bar.styleSheet()
    toolbar = window.addToolBar("Tools")
    assert window.toolbarLayout.indexOf(toolbar) >= 0


def test_supported_qt_styles_preserve_component_layout() -> None:
    app = _application()
    original_style = app.style().objectName()
    supported_styles = {"fusion", "windows11", "windowsvista", "windows"}
    qt_styles = QStyleFactory.keys()
    available_styles = [
        name for name in qt_styles if name.casefold() in supported_styles
    ]

    try:
        for style_name in available_styles:
            app.setStyle(style_name)
            window = ModernWindow()
            navigation = NavigationView(window)
            tabs = TabView(window)
            tabs.addTab(QLabel("content"), "Tab")
            window.setCentralWidget(navigation)
            window.resize(640, 480)
            window.show()
            app.processEvents()

            title_buttons = (
                window.titleBar.pinButton,
                window.titleBar.minimizeButton,
                window.titleBar.maximizeButton,
                window.titleBar.closeButton,
            )
            assert window.titleBar.height() >= max(
                button.height() for button in title_buttons
            ), style_name
            assert navigation.sidebar.width() == 240, style_name
            assert tabs.tabBar().height() > 0, style_name

            window.close()
            window.deleteLater()
            app.processEvents()
    finally:
        app.setStyle(original_style)


def test_window_effect_configuration_persists_across_reapplication() -> None:
    window = ModernWindow(effects_enabled=False)
    calls: list[tuple[WindowMaterial, ThemeMode]] = []
    window.effect_manager.apply = (
        lambda _hwnd, material, theme: calls.append((material, theme)) or True
    )

    window.setWindowMaterial(WindowMaterial.ACRYLIC)
    window.setThemeMode(ThemeMode.DARK)
    window.setWindowEffectsEnabled(True)
    window.setCornerRadius(window.cornerRadius)

    assert window.windowEffectsEnabled()
    assert window.windowMaterial() is WindowMaterial.ACRYLIC
    assert window.themeMode() is ThemeMode.DARK
    assert calls == [
        (WindowMaterial.NONE, ThemeMode.LIGHT),
        (WindowMaterial.NONE, ThemeMode.DARK),
        (WindowMaterial.ACRYLIC, ThemeMode.DARK),
        (WindowMaterial.ACRYLIC, ThemeMode.DARK),
    ]


def test_modern_window_theme_updates_nested_components() -> None:
    window = ModernWindow(effects_enabled=False)
    navigation = NavigationView()
    page = QWidget()
    page_layout = QVBoxLayout(page)
    page_label = QLabel("Page")
    tabs = TabView()
    tab_label = QLabel("Tab")
    tabs.addTab(tab_label, "Tab")
    page_layout.addWidget(page_label)
    page_layout.addWidget(tabs)
    navigation.addPage(page, "Home")
    window.setCentralWidget(navigation)
    window.setStyleSheet("QWidget { selection-color: red; }")
    observed: list[ThemeMode] = []
    window.themeChanged.connect(observed.append)

    window.toggleThemeMode()

    assert window.themeMode() is ThemeMode.DARK
    assert window.resolvedThemeMode() is ThemeMode.DARK
    assert window.frame.use_watercolor
    assert window.frame.themeMode() is ThemeMode.DARK
    assert navigation.themeMode() is ThemeMode.DARK
    assert navigation.sidebar.themeMode() is ThemeMode.DARK
    assert tabs.themeMode() is ThemeMode.DARK
    assert observed == [ThemeMode.DARK]
    assert window.styleSheet() == "QWidget { selection-color: red; }"
    assert "rgb(32, 32, 32)" in window.frame.styleSheet()
    assert "#F5F5F5" in window.titleBar.titleLabel.styleSheet()
    assert window.titleBar.themeButton.toolTip() == "切换到浅色模式"
    assert (
        page_label.palette().color(QPalette.ColorRole.WindowText).name().upper()
        == "#F5F5F5"
    )
    assert (
        tab_label.palette().color(QPalette.ColorRole.WindowText).name().upper()
        == "#F5F5F5"
    )
    _application().processEvents()
    window.close()
    window.deleteLater()
    _application().processEvents()


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
    assert view.addPage(
        second,
        "Second",
        position=NavigationPosition.BOTTOM,
    ) == 1
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


def test_tab_view_preserves_custom_ui_and_qtabwidget_compatible_api() -> None:
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
    assert tabs.tabBar().count() == 2
    assert tabs.tabBar().addButton.text() == "+"

    tabs.setTabText(0, "Updated")
    tabs.setTabToolTip(0, "Updated tab")
    assert tabs.tabText(0) == "Updated"
    assert tabs.tabToolTip(0) == "Updated tab"

    tabs.setCurrentIndex(0)
    tabs.resize(600, 400)
    tabs.show()
    _application().processEvents()
    assert tabs.tabBar()._tabs[0].width() > 80
    assert tabs.tabBar()._tabs[0].closeButton.isVisible()
    assert not tabs.tabBar()._tabs[1].closeButton.isVisible()

    observed: list[int] = []
    tabs.currentChanged.connect(observed.append)
    tabs.setCurrentIndex(0)
    assert tabs.currentWidget() is second

    tabs.removeTab(0)
    assert tabs.count() == 1
    assert tabs.indexOf(first) == 0
    assert second.parent() is not None
    assert observed[-1] == 0
