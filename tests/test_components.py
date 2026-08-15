from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenuBar,
    QStatusBar,
    QWidget,
)
from PySide6.QtGui import QIcon

from pyside6_modern_widgets import (
    ModernWindow,
    NavigationPosition,
    NavigationSidebar,
    NavigationView,
    TabView,
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


def test_tab_view_uses_qtabwidget_semantics() -> None:
    _application()
    tabs = TabView()
    first = QLabel("first")
    second = QLabel("second")
    assert tabs.addTab(first, "First") == 0
    assert tabs.insertTab(0, second, "Second") == 0
    assert tabs.widget(0) is second
    assert tabs.indexOf(first) == 1

    tabs.removeTab(0)
    assert tabs.count() == 1
    assert tabs.indexOf(first) == 0
    assert second.parent() is not None
