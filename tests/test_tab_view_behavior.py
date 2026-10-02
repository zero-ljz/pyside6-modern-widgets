from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pyside6_modern_widgets import LIGHT_THEME, ModernTabWidget, TabView

_APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    "direction", [Qt.LayoutDirection.LeftToRight, Qt.LayoutDirection.RightToLeft]
)
@pytest.mark.parametrize("selected_index", [0, 3, 7])
def test_overflowed_tabs_remain_painted_in_both_layout_directions(direction, selected_index):
    view = TabView(theme=LIGHT_THEME)
    view.setLayoutDirection(direction)
    for index in range(8):
        view.addTab(QLabel(str(index)), f"Tab {index}")
    view.resize(500, 250)
    view.show()
    view.setCurrentIndex(selected_index)
    _APP.processEvents()
    try:
        bar = view.tabBar()
        scroll_buttons = [
            bar.findChild(QToolButton, name) for name in ("ScrollLeftButton", "ScrollRightButton")
        ]
        assert all(button is not None and button.isVisible() for button in scroll_buttons)
        selected_rect = bar.tabRect(selected_index)
        # Sample the selected surface above its label and away from the scroll controls.
        x, y = selected_rect.center().x(), selected_rect.top() + 5
        assert bar.rect().contains(x, y)
        assert all(not button.geometry().contains(x, y) for button in scroll_buttons)
        image = bar.grab().toImage()
        dpr = image.devicePixelRatio()
        assert image.pixelColor(round(x * dpr), round(y * dpr)) == QColor(LIGHT_THEME.tab_selected)
    finally:
        view.close()
        view.deleteLater()


@pytest.mark.parametrize("index", [-10, -1, 0, 1, 2, 10])
def test_insert_index_boundaries_match_qt(index):
    outcomes = []
    for view_class in (QTabWidget, ModernTabWidget, TabView):
        view = view_class()
        for label in ("A", "B"):
            view.addTab(QLabel(label), label)
        result = view.insertTab(index, QLabel("New"), "New")
        outcomes.append(
            (result, [view.tabText(i) for i in range(view.count())], view.currentWidget().text())
        )
        view.deleteLater()
    assert outcomes[0] == outcomes[1] == outcomes[2]


@pytest.mark.parametrize("by_widget", [False, True])
def test_programmatic_selection_of_disabled_tab_matches_qt(by_widget):
    outcomes = []
    for view_class in (QTabWidget, ModernTabWidget, TabView):
        view = view_class()
        for label in ("A", "B"):
            view.addTab(QLabel(label), label)
        view.setTabEnabled(1, False)
        changes = []
        view.currentChanged.connect(changes.append)
        for _ in range(2):
            if by_widget:
                view.setCurrentWidget(view.widget(1))
            else:
                view.setCurrentIndex(1)
        outcomes.append(
            (view.currentIndex(), view.currentWidget().text(), view.widget(1).isEnabled(), changes)
        )
        view.deleteLater()
    assert outcomes[0] == outcomes[1] == outcomes[2] == (1, "B", False, [1])


def test_relative_tab_navigation_still_skips_disabled_tabs():
    view = TabView()
    for label in ("A", "B", "C"):
        view.addTab(QLabel(label), label)
    view.setTabEnabled(1, False)
    view.nextTab()
    assert view.currentIndex() == 2
    view.previousTab()
    assert view.currentIndex() == 0
    view.deleteLater()


@pytest.mark.parametrize(
    "current,existing,target", [(0, 0, 3), (1, 0, 3), (2, 0, 1), (1, 1, 0), (1, 2, 0), (0, 0, 0)]
)
def test_reinserting_existing_page_matches_qt(current, existing, target):
    outcomes = []
    for view_class in (QTabWidget, TabView):
        view = view_class()
        pages = [QLabel(label) for label in ("A", "B", "C")]
        for page in pages:
            view.addTab(page, page.text())
        view.setCurrentIndex(current)
        result = view.insertTab(target, pages[existing], "Updated")
        assert view.tabBar().count() == view.count() == 3
        outcomes.append(
            (
                result,
                [view.tabText(i) for i in range(view.count())],
                [view.widget(i).text() for i in range(view.count())],
                view.currentWidget().text(),
            )
        )
        # The moved page must remain selectable under its new label.
        view.setCurrentIndex(result)
        assert view.currentWidget() is pages[existing]
        view.removeTab(result)
        assert view.count() == view.tabBar().count() == 2
        view.deleteLater()
    assert outcomes[0] == outcomes[1]


def test_repeated_add_of_only_page_does_not_duplicate_tab():
    view = TabView()
    page = QLabel("Page")
    for text in ("First", "Second", "Third"):
        assert view.addTab(page, text) == 0
        assert view.count() == view.tabBar().count() == 1
        assert view.currentWidget() is page
        assert view.tabText(0) == text
    view.deleteLater()


def test_renaming_tab_updates_generated_tooltip_but_preserves_custom_tooltip():
    view = TabView()
    view.addTab(QLabel("First"), "First")
    view.addTab(QLabel("Second"), "Second")
    view.setTabToolTip(1, "Details about the second tab")

    view.setTabText(0, "Renamed")
    view.setTabText(1, "Changed")

    assert view.tabToolTip(0) == "Renamed"
    assert view.tabToolTip(1) == "Details about the second tab"
    view.deleteLater()


def test_disabled_tabs_disable_pages_and_reenable_them_like_qt():
    outcomes = []
    for view_class in (QTabWidget, TabView):
        view = view_class()
        pages = [QLineEdit("A"), QLineEdit("B")]
        for page in pages:
            view.addTab(page, page.text())
        states = []
        for index, enabled in ((0, False), (1, False), (0, True), (1, True)):
            view.setTabEnabled(index, enabled)
            states.append(
                (
                    view.currentIndex(),
                    [view.isTabEnabled(i) for i in range(view.count())],
                    [page.isEnabled() for page in pages],
                )
            )
        outcomes.append(states)
        view.deleteLater()
    assert outcomes[0] == outcomes[1]


def test_shortcuts_apply_only_to_the_focused_tab_view():
    window = QWidget()
    layout = QVBoxLayout(window)
    views = [TabView(), TabView()]
    adds = []
    closes = []
    for number, view in enumerate(views):
        layout.addWidget(view)
        for label in ("A", "B"):
            view.addTab(QLineEdit(label), label)
        view.addTabClicked.connect(lambda n=number: adds.append(n))
        view.tabCloseRequested.connect(lambda index, n=number: closes.append((n, index)))
    outside = QLineEdit("Outside")
    layout.addWidget(outside)
    window.show()
    window.activateWindow()
    QTest.qWait(50)
    add_keys = QKeySequence.keyBindings(QKeySequence.StandardKey.AddTab)
    close_keys = QKeySequence.keyBindings(QKeySequence.StandardKey.Close)
    try:
        for number, view in enumerate(views):
            view.currentWidget().setFocus()
            _APP.processEvents()
            assert _APP.focusWidget() is view.currentWidget()
            QTest.keySequence(view.currentWidget(), QKeySequence("Ctrl+Tab"))
            assert view.currentIndex() == 1
            assert views[1 - number].currentIndex() == 0
            QTest.keySequence(view.currentWidget(), QKeySequence("Ctrl+Shift+Tab"))
            assert view.currentIndex() == 0
            for key in add_keys + close_keys:
                QTest.keySequence(view.currentWidget(), key)
        assert adds == [0] * len(add_keys) + [1] * len(add_keys)
        assert closes == [(0, 0)] * len(close_keys) + [(1, 0)] * len(close_keys)
        outside.setFocus()
        _APP.processEvents()
        for key in add_keys + close_keys:
            QTest.keySequence(outside, key)
        assert adds == [0] * len(add_keys) + [1] * len(add_keys)
        assert closes == [(0, 0)] * len(close_keys) + [(1, 0)] * len(close_keys)
    finally:
        window.close()
        window.deleteLater()


def test_nested_tab_shortcuts_follow_the_nearest_view_as_focus_moves():
    outer = TabView()
    inner = TabView()
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(inner)
    outside_inner = QLineEdit("Outer page")
    layout.addWidget(outside_inner)
    outer.addTab(page, "Nested")
    outer.addTab(QLineEdit("Other outer page"), "Other")
    for label in ("A", "B"):
        inner.addTab(QLineEdit(label), label)
    adds = []
    closes = []
    for name, view in (("outer", outer), ("inner", inner)):
        view.addTabClicked.connect(lambda n=name: adds.append(n))
        view.tabCloseRequested.connect(lambda index, n=name: closes.append((n, index)))
    outer.show()
    outer.activateWindow()
    QTest.qWait(50)
    try:
        # Moving back into the nested view must reactivate its shortcuts.
        for name, view, focus in (
            ("inner", inner, inner.currentWidget()),
            ("outer", outer, outside_inner),
            ("inner", inner, inner.tabBar()),
            ("outer", outer, outer.tabBar()),
        ):
            focus.setFocus()
            _APP.processEvents()
            assert _APP.focusWidget() is focus
            for key in QKeySequence.keyBindings(QKeySequence.StandardKey.AddTab):
                QTest.keySequence(focus, key)
                assert adds == [name]
                adds.clear()
            for key in QKeySequence.keyBindings(QKeySequence.StandardKey.Close):
                QTest.keySequence(focus, key)
                assert closes == [(name, 0)]
                closes.clear()
            QTest.keySequence(focus, QKeySequence("Ctrl+Tab"))
            assert view.currentIndex() == 1
            assert (outer if view is inner else inner).currentIndex() == 0
            QTest.keySequence(_APP.focusWidget(), QKeySequence("Ctrl+Shift+Tab"))
            assert view.currentIndex() == 0
    finally:
        outer.close()
        outer.deleteLater()
