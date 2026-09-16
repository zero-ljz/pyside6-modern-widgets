"""Native focus, minimized-host, action, and animation checks for notifications.

Run with: python tests/notification_smoke.py
"""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QVBoxLayout, QWidget

from pyside6_modern_widgets import NotificationManager, NotificationPosition, theme_manager


def foreground():
    if sys.platform == "win32":
        get_foreground = ctypes.windll.user32.GetForegroundWindow
        get_foreground.restype = ctypes.c_void_p
        return get_foreground()
    return QApplication.activeWindow()


def main() -> None:
    app = QApplication([])
    app.setStyle("Fusion")
    theme_manager().setWallpaperEnabled(False)
    host, editor = QWidget(), QWidget()
    host.resize(600, 400)
    layout = QVBoxLayout(editor)
    field = QLineEdit()
    layout.addWidget(field)
    host.show()
    editor.show()
    editor.activateWindow()
    field.setFocus()
    QTest.qWait(200)
    previous = foreground()
    manager = NotificationManager(host)
    try:
        ids = [
            manager.notify(f"Update {i}", "Continue typing in the other window.", duration=0)
            for i in range(4)
        ]
        QTest.qWait(400)
        assert foreground() == previous
        assert field.hasFocus()
        assert QApplication.activePopupWidget() is None
        assert len(manager.visibleIds()) == 3
        assert len(manager.queuedIds()) == 1
        host.showMinimized()
        QTest.qWait(100)
        assert all(manager.notification(key).isVisible() for key in manager.visibleIds())
        assert foreground() == previous
        QTest.keyClicks(field, "Focus stayed here")
        assert field.text() == "Focus stayed here"
        manager.dismiss(ids[0])
        manager.setPosition(NotificationPosition.TOP_RIGHT)
        QTest.qWait(400)
        cards = [manager.notification(key) for key in manager.visibleIds()]
        assert len(cards) == 3
        assert all(card.screen().availableGeometry().contains(card.geometry()) for card in cards)
        assert all(
            not a.geometry().intersects(b.geometry())
            for i, a in enumerate(cards)
            for b in cards[i + 1 :]
        )
        assert foreground() == previous
        action_events = []
        manager.actionTriggered.connect(lambda key, action: action_events.append((key, action)))
        key = manager.visibleIds()[0]
        manager.updateNotification(key, actions={"open": "Open"})
        QTest.qWait(300)
        card = manager.notification(key)
        button = next(b for b in card.findChildren(QPushButton) if b.text() == "Open")
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert action_events == [(key, "open")]
        assert manager.notification(key) is None
    finally:
        manager.clear()
        host.close()
        editor.close()
        app.processEvents()
    print("Native notification focus, stacking, actions, and minimized-host checks passed")


if __name__ == "__main__":
    main()
