from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QIcon
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QWidget
from shiboken6 import isValid

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    DockConfig,
    ModernComboBox,
    ModernDialog,
    ModernFlyout,
    ModernMessageBox,
    ModernMetrics,
    ModernNotification,
    ModernSegmentedControl,
    ModernSwitch,
    ModernTabWidget,
    ModernToolBar,
    ModernWindow,
    NavigationSidebar,
    NavigationView,
    NotificationManager,
    TabView,
    ThemeMode,
)


def flush_deletes():
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize(
    "factory",
    [
        ModernWindow,
        ModernDialog,
        ModernMessageBox,
        ModernTabWidget,
        NavigationView,
        NavigationSidebar,
        TabView,
        ModernComboBox,
        ModernSwitch,
        ModernToolBar,
        ModernFlyout,
        ModernNotification,
        NotificationManager,
        lambda **kwargs: ModernSegmentedControl(["First", "Second"], **kwargs),
    ],
)
def test_theme_inheritance_updates_hidden_children_and_tracks_reparenting(
    theme_manager_instance, factory
):
    theme_manager_instance.setMode(ThemeMode.LIGHT)
    first = ModernWindow(theme=DARK_THEME)
    second = ModernWindow(theme=LIGHT_THEME)
    container = QWidget(first)
    child = factory(parent=container)
    changes = []
    child.themeChanged.connect(changes.append)
    try:
        assert child.theme() == DARK_THEME
        # These tokens do not change the Qt palette. Hidden widgets still update.
        custom = replace(DARK_THEME, tab_selected="#735CA1", name="custom")
        first.setTheme(custom)
        assert child.theme() == custom
        assert changes == [custom]
        first.setTheme(custom)
        assert changes == [custom]
        child.setTheme(LIGHT_THEME)
        first.setTheme(DARK_THEME)
        assert child.theme() == LIGHT_THEME
        child.setTheme(None)
        assert child.theme() == DARK_THEME
        container.setParent(second)
        assert child.theme() == LIGHT_THEME
        changes.clear()
        first.setTheme(custom)
        assert not changes
        container.setParent(None)
        theme_manager_instance.setMode(ThemeMode.DARK)
        assert child.theme() == DARK_THEME
        assert changes == [DARK_THEME]
    finally:
        for widget in (container, first, second):
            widget.deleteLater()
        flush_deletes()


def test_navigation_sidebar_emits_shifted_index_after_state_is_committed():
    sidebar = NavigationSidebar()
    for label in ("A", "B", "C"):
        sidebar.addItem(label)
    sidebar.setCurrentIndex(2)
    snapshots = []
    sidebar.currentChanged.connect(
        lambda index: snapshots.append((index, sidebar.currentIndex(), sidebar.itemText(index)))
    )
    removed = sidebar.removeItem(0)
    assert snapshots == [(1, 1, "C")]
    removed.deleteLater()
    sidebar.deleteLater()
    flush_deletes()


def test_reentrant_theme_override_does_not_publish_stale_parent_tokens():
    window = ModernWindow(theme=LIGHT_THEME)
    child = ModernTabWidget(window)
    final_theme = replace(DARK_THEME, tab_selected="#9734B2", name="final")
    changes = []
    window.themeChanged.connect(changes.append)

    def override(theme):
        if theme == DARK_THEME:
            window.setTheme(final_theme)

    child.themeChanged.connect(override)
    window.setTheme(DARK_THEME)
    assert window.theme() == child.theme() == final_theme
    assert changes[-1] == final_theme
    window.deleteLater()
    flush_deletes()


def test_title_bar_visibility_is_reversible_and_survives_window_flag_changes():
    window = ModernWindow()
    title_bar = window.titleBar
    button = window.addTitleBarButton(QIcon(), tooltip="Custom")
    window.setTitleAlignment("center")
    window.setTitleBarVisible(False)
    window.show()
    QApplication.processEvents()
    window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    window.show()
    QApplication.processEvents()
    flush_deletes()
    assert not window.isTitleBarVisible()
    assert title_bar.isHidden()
    assert window.contentsMargins().top() == 0
    assert isValid(title_bar) and isValid(button)
    window.setTitleBarVisible(True)
    assert window.titleBar is title_bar
    assert window.contentsMargins().top() == title_bar.height()
    assert window.titleAlignment() == "center"
    assert button.toolTip() == "Custom"
    window.hide()
    assert window.isTitleBarVisible()
    window.deleteLater()
    flush_deletes()


@pytest.mark.parametrize("view_type", [NavigationView, TabView, ModernTabWidget])
@pytest.mark.parametrize("take", [False, True])
def test_page_remove_retains_ownership_and_take_transfers_it(view_type, take):
    view = view_type()
    page = QLabel("Page")
    if isinstance(view, NavigationView):
        view.addPage(page, "Page")
        operation = view.takePage if take else view.removePage
    else:
        view.addTab(page, "Page")
        operation = view.takeTab if take else view.removeTab
    original_parent = page.parent()
    result = operation(0)
    assert view.count() == 0
    assert page.isHidden()
    assert operation(100) is None
    if take:
        assert result is page
        assert page.parent() is None
    else:
        assert result is None
        assert page.parent() is original_parent
    view.deleteLater()
    flush_deletes()
    assert isValid(page) == take
    if take:
        assert page.text() == "Page"
        page.deleteLater()
        flush_deletes()


def test_central_widget_take_survives_replacement_and_owner_destruction():
    window = ModernWindow()
    assert window.centralWidget() is None
    assert window.takeCentralWidget() is None
    page = QLabel("Keep me")
    window.setCentralWidget(page)
    assert window.centralWidget() is page
    assert window.takeCentralWidget() is page
    assert window.centralWidget() is None
    assert page.parent() is None
    replacement = QLabel("Replacement")
    window.setCentralWidget(replacement)
    window.deleteLater()
    flush_deletes()
    assert isValid(page)
    assert not isValid(replacement)
    page.deleteLater()
    flush_deletes()


def test_segmented_selection_signals_cover_programmatic_and_user_changes():
    control = ModernSegmentedControl(["A", "B", "C"])
    changes, activations = [], []
    control.currentChanged.connect(changes.append)
    control.itemActivated.connect(activations.append)
    control.setCurrentIndex(1)
    control.setCurrentIndex(1)
    control.setCurrentIndex(-1)
    control.setCurrentIndex(100)
    assert changes == [1]
    assert not activations
    control.button(2).setChecked(True)
    assert changes == [1, 2]
    QTest.mouseClick(control.button(2), Qt.MouseButton.LeftButton)
    QTest.mouseClick(control.button(0), Qt.MouseButton.LeftButton)
    assert changes == [1, 2, 0]
    assert activations == [2, 0]
    control.setItemText(0, "Updated")
    assert control.itemText(0) == "Updated"
    control.setItemEnabled(1, False)
    assert not control.isItemEnabled(1)
    assert control.button(-1) is None
    assert control.itemText(100) == ""
    assert not control.isItemEnabled(100)
    control.deleteLater()
    flush_deletes()


def test_window_creates_toolbar_and_overflow_with_its_metrics():
    metrics = ModernMetrics(control_radius=13, animation_duration_ms=0)
    window = ModernWindow(metrics=metrics)
    toolbar = window.addToolBar("Tools")
    assert isinstance(toolbar, ModernToolBar)
    assert toolbar._metrics == metrics
    assert toolbar.overflowMenu()._metrics == metrics
    assert window.menuBar()._metrics == metrics
    window.deleteLater()
    flush_deletes()


def test_removed_api_names_are_not_kept_as_aliases():
    window = ModernWindow()
    segments = ModernSegmentedControl(["A"])
    for name in ("hideTitleBar", "content", "initWindow", "apply_window_style"):
        assert not hasattr(window, name)
    assert not hasattr(segments, "group")
    assert not hasattr(segments, "buttons")
    for options in ({"anim_duration": 0}, {"hide_delay": 0}):
        with pytest.raises(TypeError):
            DockConfig(**options)
    with pytest.raises(TypeError):
        ModernMetrics(animation_duration=0)
    window.deleteLater()
    segments.deleteLater()
    flush_deletes()
