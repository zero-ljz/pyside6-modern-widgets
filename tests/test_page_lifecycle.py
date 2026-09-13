from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel

from pyside6_modern_widgets import NavigationView, TabView

_APP = QApplication.instance() or QApplication([])


def _flush_deletes() -> None:
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    _APP.processEvents()


def _add(view, page) -> None:
    if isinstance(view, TabView):
        view.addTab(page, page.text())
    else:
        view.addPage(page, page.text())


def _assert_synced(view) -> None:
    if isinstance(view, TabView):
        assert view.tabBar().count() == view.count()
        assert view.tabBar().currentIndex() == view.currentIndex()
        labels = [view.tabText(i) for i in range(view.count())]
    else:
        assert view.sidebar.count() == view.count()
        assert view.sidebar.currentIndex() == view.currentIndex()
        labels = [view.sidebar.itemText(i) for i in range(view.count())]
    assert labels == [view.widget(i).text() for i in range(view.count())]


@pytest.mark.parametrize("view_class", [TabView, NavigationView])
@pytest.mark.parametrize("removed_index", [0, 1, 2])
@pytest.mark.parametrize("method", ["delete", "reparent", "remove"])
def test_page_removal_keeps_entries_and_selection_in_sync(view_class, removed_index, method):
    view = view_class()
    pages = [QLabel(label) for label in ("A", "B", "C")]
    for page in pages:
        _add(view, page)
    view.setCurrentIndex(1)
    notifications = []

    def changed(index):
        _assert_synced(view)
        notifications.append(index)

    view.currentChanged.connect(changed)
    removed = pages[removed_index]
    if method == "delete":
        removed.deleteLater()
    elif method == "reparent":
        removed.setParent(None)
    elif isinstance(view, TabView):
        view.removeTab(removed_index)
    else:
        assert view.removePage(removed_index) is removed
    _flush_deletes()
    assert view.count() == 2
    _assert_synced(view)
    assert view.currentWidget() is not removed
    assert len(notifications) == (0 if removed_index == 2 else 1)

    # Removing a page and later destroying it must not remove another entry.
    if method != "delete":
        removed.deleteLater()
        _flush_deletes()
        assert view.count() == 2
        _assert_synced(view)
    for index in range(view.count()):
        view.setCurrentIndex(index)
        _assert_synced(view)
    view.deleteLater()
    _flush_deletes()


@pytest.mark.parametrize("view_class", [TabView, NavigationView])
def test_last_page_destruction_and_replacement_publish_complete_state(view_class):
    view = view_class()
    notifications = []

    def changed(index):
        _assert_synced(view)
        notifications.append(index)

    view.currentChanged.connect(changed)
    page = QLabel("First")
    _add(view, page)
    assert notifications == [0]
    page.deleteLater()
    _flush_deletes()
    assert view.count() == 0
    assert view.currentIndex() == -1
    _assert_synced(view)
    assert notifications == [0, -1]
    _add(view, QLabel("Replacement"))
    assert notifications == [0, -1, 0]
    _assert_synced(view)
    view.deleteLater()
    _flush_deletes()


@pytest.mark.parametrize("insert_index", [0, 10])
def test_first_tab_insertion_emits_once_after_page_and_label_are_ready(insert_index):
    view = TabView()
    snapshots = []
    view.currentChanged.connect(
        lambda index: snapshots.append((index, view.tabText(index), view.currentWidget().text()))
    )
    first = QLabel("First")
    view.insertTab(insert_index, first, "First")
    assert snapshots == [(0, "First", "First")]
    view.insertTab(0, QLabel("Before"), "Before")
    view.addTab(QLabel("After"), "After")
    assert view.currentWidget() is first
    assert len(snapshots) == 1
    view.tabBar().moveTab(0, 2)
    _assert_synced(view)
    view.widget(2).deleteLater()
    _flush_deletes()
    _assert_synced(view)
    view.deleteLater()
    _flush_deletes()
