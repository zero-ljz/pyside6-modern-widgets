"""Exercise ModernWindow against the active Qt platform plugin."""

from __future__ import annotations

import sys

from PySide6.QtCore import QPoint, QSize
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import ModernWindow


def _wait(app: QApplication, milliseconds: int = 150) -> None:
    app.processEvents()
    QTest.qWait(milliseconds)
    app.processEvents()


def _center_on_screen(window: ModernWindow, screen) -> None:
    available = screen.availableGeometry()
    position = available.center() - QPoint(window.width() // 2, window.height() // 2)
    window.move(position)


def main() -> int:
    app = QApplication(sys.argv)
    window = ModernWindow()
    normal_size = QSize(900, 600)
    window.resize(normal_size)

    primary = app.primaryScreen()
    if primary is not None:
        _center_on_screen(window, primary)
    window.show()
    _wait(app)
    assert window.isVisible()
    assert window.titleBar is not None

    for screen in app.screens():
        _center_on_screen(window, screen)
        _wait(app, 400)
        assert window.size() == normal_size

    image = window.grab().toImage()
    assert not image.isNull()
    assert image.width() > 0 and image.height() > 0

    window.close()
    _wait(app, 50)
    print(f"platform={app.platformName()} screens={len(app.screens())} smoke=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
