from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel
from shiboken6 import isValid

from pyside6_modern_widgets import NavigationPosition, NavigationSidebar, NavigationView

_APP = QApplication.instance() or QApplication([])


def _flush_deletes():
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_borrowed_button_selection_updates_navigation_and_activation_signals():
    view = NavigationView()
    for label in ("A", "B", "C"):
        view.addPage(QLabel(label), label)
    sidebar = view.sidebar
    changes, activations, pages = [], [], []
    sidebar.currentChanged.connect(
        lambda index: changes.append(
            (index, sidebar.currentIndex(), sidebar.button(index).isChecked())
        )
    )
    sidebar.itemActivated.connect(activations.append)
    view.currentChanged.connect(lambda index: pages.append((index, view.currentWidget().text())))
    sidebar.button(1).setChecked(True)
    sidebar.button(1).setChecked(True)
    sidebar.setCurrentIndex(2)
    sidebar.setCurrentIndex(2)
    sidebar.button(2).click()
    sidebar.button(0).click()
    assert changes == [(1, 1, True), (2, 2, True), (0, 0, True)]
    assert pages == [(1, "B"), (2, "C"), (0, "A")]
    assert activations == [2, 0]
    view.deleteLater()
    _flush_deletes()


@pytest.mark.parametrize("take", [False, True])
@pytest.mark.parametrize("position", list(NavigationPosition))
def test_item_removal_ownership_and_detached_selection(take, position):
    sidebar = NavigationSidebar()
    sidebar.addItem("A", position=position)
    sidebar.addItem("B", position=position)
    sidebar.setCurrentIndex(0)
    button = sidebar.button(0)
    original_parent = button.parent()
    changes, activations = [], []
    sidebar.currentChanged.connect(
        lambda index: changes.append(
            (index, sidebar.itemText(index), sidebar.button(index).isChecked())
        )
    )
    sidebar.itemActivated.connect(activations.append)
    operation = sidebar.takeItem if take else sidebar.removeItem
    result = operation(0)
    assert sidebar.count() == 1
    assert changes == [(0, "B", True)]
    assert button.isHidden()
    assert result is (button if take else None)
    assert button.parent() is (None if take else original_parent)
    assert operation(-1) is None
    assert operation(100) is None
    # A removed button no longer participates, even when the caller retains it.
    button.setChecked(False)
    button.setChecked(True)
    button.click()
    assert changes == [(0, "B", True)]
    assert activations == []
    sidebar.addItem("C")
    sidebar.button(1).setChecked(True)
    assert changes[-1] == (1, "C", True)
    sidebar.deleteLater()
    _flush_deletes()
    assert isValid(button) == take
    if take:
        assert button.text() == "A"
        button.deleteLater()
        _flush_deletes()


def test_removal_before_selection_keeps_button_indices_current():
    sidebar = NavigationSidebar()
    for label in ("A", "B", "C"):
        sidebar.addItem(label)
    sidebar.setCurrentIndex(2)
    sidebar.removeItem(0)
    changes = []
    sidebar.currentChanged.connect(changes.append)
    sidebar.button(0).setChecked(True)
    sidebar.button(1).setChecked(True)
    assert changes == [0, 1]
    sidebar.deleteLater()
    _flush_deletes()


def test_grouped_pages_keep_page_indices_and_selection_in_sync():
    view = NavigationView()
    view.addPage(QLabel("Home"), "Home")
    view.addPage(QLabel("One"), "One", group="Tools")
    view.addPage(QLabel("Settings"), "Settings", position=NavigationPosition.BOTTOM, group="Tools")
    view.addPage(QLabel("Two"), "Two", group="Tools")
    sidebar = view.sidebar
    top = sidebar._groups[(NavigationPosition.TOP, "Tools")]
    bottom = sidebar._groups[(NavigationPosition.BOTTOM, "Tools")]

    assert view.count() == sidebar.count() == 4
    assert [top.itemLayout.itemAt(i).widget() for i in (1, 2)] == [
        sidebar.button(1), sidebar.button(3)
    ]
    assert top.header.text() == bottom.header.text() == "Tools"
    sidebar.button(3).click()
    assert view.currentIndex() == sidebar.currentIndex() == 3
    assert view.currentWidget().text() == "Two"

    sidebar.setCollapsed(True, animated=False)
    assert top.header.isHidden() and bottom.header.isHidden()
    sidebar.setCollapsed(False, animated=False)
    assert not top.header.isHidden() and not bottom.header.isHidden()

    view.removePage(1)
    _flush_deletes()
    assert view.count() == sidebar.count() == 3
    assert view.currentIndex() == sidebar.currentIndex() == 2
    assert not top.isHidden()
    view.removePage(2)
    _flush_deletes()
    assert top.isHidden()
    assert not bottom.isHidden()
    view.deleteLater()
    _flush_deletes()


def test_empty_bottom_group_hides_and_can_be_reused():
    sidebar = NavigationSidebar()
    index = sidebar.addItem("Settings", position=NavigationPosition.BOTTOM, group="More")
    group = sidebar._groups[(NavigationPosition.BOTTOM, "More")]
    assert not group.isHidden()
    assert not sidebar._bottom_container.isHidden()

    button = sidebar.button(index)
    sidebar.removeItem(index)
    assert group.isHidden()
    assert sidebar._bottom_container.isHidden()
    assert button.parent() is group
    assert sidebar.addItem("About", position=NavigationPosition.BOTTOM, group="More") == 0
    assert sidebar._groups[(NavigationPosition.BOTTOM, "More")] is group
    assert not group.isHidden()
    assert not sidebar._bottom_container.isHidden()
    sidebar.deleteLater()
    _flush_deletes()


def test_invalid_group_does_not_add_page_or_item():
    view = NavigationView()
    page = QLabel("Page")
    with pytest.raises(ValueError):
        view.addPage(page, "Page", group=" ")
    with pytest.raises(ValueError):
        view.sidebar.addItem("Item", group="")
    assert view.count() == view.sidebar.count() == 0
    assert page.parent() is None
    view.deleteLater()
    page.deleteLater()
    _flush_deletes()


def test_navigation_toggle_only_uses_hover_style_for_keyboard_focus() -> None:
    sidebar = NavigationSidebar()
    button = sidebar.toggleButton

    button.focusInEvent(QFocusEvent(QFocusEvent.Type.FocusIn, Qt.FocusReason.TabFocusReason))
    assert button._keyboard_focus_visible

    QTest.mousePress(button, Qt.MouseButton.LeftButton)
    assert not button._keyboard_focus_visible
    QTest.mouseRelease(button, Qt.MouseButton.LeftButton)

    sidebar.close()
