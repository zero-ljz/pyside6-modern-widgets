"""Exercise the gallery's notification handles and capacity feedback."""

from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from examples import navigation_view_example
from pyside6_modern_widgets import NotificationKind, NotificationManager

_APP = QApplication.instance() or QApplication([])


def test_download_can_restart_and_finish_through_its_handle(theme_manager_instance):
    window = navigation_view_example.ExampleWindow()
    manager = window.notification_managers[0]
    try:
        button = next(
            b for b in window.findChildren(QPushButton) if b.text() == "Simulate download"
        )
        button.click()
        first = manager.notifications()[0]
        button.click()
        assert first.isClosed()
        job = manager.notifications()[0]
        assert job is not first
        timer = next(t for t in window.findChildren(QTimer) if t.interval() == 120)
        for _ in range(50):
            timer.timeout.emit()
        assert not timer.isActive()
        assert job.snapshot().kind == NotificationKind.SUCCESS
        assert job.snapshot().progress is None
        assert job.snapshot().timeout_ms == 5000
        assert job.snapshot().actions[0].id == "open"
    finally:
        window.close()
        window.deleteLater()
        for _ in range(2):
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        _APP.processEvents()


def test_gallery_explains_full_capacity_without_discarding_notifications(
    theme_manager_instance, monkeypatch
):
    monkeypatch.setattr(
        navigation_view_example,
        "NotificationManager",
        lambda parent, **options: NotificationManager(parent, capacity=2, **options),
    )
    window = navigation_view_example.ExampleWindow()
    manager = window.notification_managers[0]
    try:
        manager.setDeliveryPaused(True)
        handles = tuple(manager.notify(str(index), timeout_ms=None) for index in range(2))
        button = next(
            b for b in window.findChildren(QPushButton) if b.text() == "Keep until dismissed"
        )
        button.click()
        assert manager.notifications() == handles
        assert any(
            label.text() == "Dismiss a notification before showing another."
            for label in window.findChildren(QLabel)
        )
    finally:
        window.close()
        window.deleteLater()
        for _ in range(2):
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        _APP.processEvents()
