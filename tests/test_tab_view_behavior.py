from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QTabWidget, QVBoxLayout, QWidget

from pyside6_modern_widgets import TabView

_APP = QApplication.instance() or QApplication([])


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
