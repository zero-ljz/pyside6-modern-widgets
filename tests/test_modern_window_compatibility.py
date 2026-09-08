from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QLabel, QToolBar
from shiboken6 import isValid

from pyside6_modern_widgets import ModernWindow


@pytest.fixture(scope="module")
def application() -> QApplication:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    return app


def _destroy_deferred_objects(application: QApplication) -> None:
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()


def test_cached_compatibility_widgets_can_be_recreated_after_destruction(
    application: QApplication,
) -> None:
    window = ModernWindow()
    menu_bar = window.menuBar()
    status_bar = window.statusBar()

    menu_bar.deleteLater()
    status_bar.deleteLater()
    _destroy_deferred_objects(application)

    assert window._menu_bar is None
    assert window._status_bar is None
    assert not isValid(menu_bar)
    assert not isValid(status_bar)
    assert isValid(window.menuBar())
    assert isValid(window.statusBar())
    window.close()


def test_central_widget_destruction_and_none_leave_window_reusable(
    application: QApplication,
) -> None:
    window = ModernWindow()
    first = QLabel("first")
    window.setCentralWidget(first)
    replacement = QLabel("replacement")
    window.setCentralWidget(replacement)
    _destroy_deferred_objects(application)

    assert not isValid(first)
    assert window.content is replacement

    replacement.deleteLater()
    _destroy_deferred_objects(application)

    assert window.content is None
    second = QLabel("second")
    window.setCentralWidget(second)
    assert window.content is second

    window.setCentralWidget(None)
    assert window.content is None
    _destroy_deferred_objects(application)
    assert not isValid(second)

    third = QLabel("third")
    window.setCentralWidget(third)
    assert window.content is third
    assert window.frameLayout is not None
    assert window.frameLayout.indexOf(third) >= 0
    window.close()


def test_add_toolbar_honors_supported_areas_and_rejects_invalid_signatures(
    application: QApplication,
) -> None:
    window = ModernWindow()
    top = QToolBar()
    bottom = QToolBar()

    assert window.addToolBar(Qt.ToolBarArea.TopToolBarArea, top) is top
    assert window.addToolBar(Qt.ToolBarArea.BottomToolBarArea, bottom) is bottom
    assert window.toolbarLayout is not None
    assert window._bottom_toolbar_layout is not None
    assert window.toolbarLayout.indexOf(top) >= 0
    assert window._bottom_toolbar_layout.indexOf(bottom) >= 0

    with pytest.raises(TypeError, match="top and bottom"):
        window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, QToolBar())
    with pytest.raises(TypeError, match="expects"):
        window.addToolBar()
    with pytest.raises(TypeError, match="expects"):
        window.addToolBar(Qt.ToolBarArea.TopToolBarArea, "not a toolbar")
    with pytest.raises(TypeError, match="expects"):
        window.addToolBar(object())
    window.close()


def test_application_event_filter_is_active_only_while_visible(
    application: QApplication,
) -> None:
    window = ModernWindow()
    assert not window._application_event_filter_installed

    window.show()
    application.processEvents()
    assert window._application_event_filter_installed
    visible_child = QLabel(window)
    assert visible_child.hasMouseTracking()

    window.hide()
    application.processEvents()
    assert not window._application_event_filter_installed
    hidden_child = QLabel(window)
    assert not hidden_child.hasMouseTracking()
    QApplication.sendEvent(hidden_child, QEvent(QEvent.Type.User))
    assert not hidden_child.hasMouseTracking()

    window.show()
    application.processEvents()
    assert window._application_event_filter_installed
    QApplication.sendEvent(hidden_child, QEvent(QEvent.Type.User))
    assert hidden_child.hasMouseTracking()

    window.close()
    application.processEvents()
    assert not window._application_event_filter_installed
