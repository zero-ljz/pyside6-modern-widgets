"""Verify Win11 acrylic in the desktop composite (requires an interactive desktop).

Run with: python tests/windows_appearance_smoke.py
Widget.grab() excludes DWM acrylic, so sample only our popup's desktop rectangle.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from pyside6_modern_widgets import ModernMenu, ModernWindow, ThemeMode, theme_manager
from pyside6_modern_widgets.modern_menu import _supports_windows_acrylic


class _Backdrop(QWidget):
    color = QColor("red")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.color)


def _sample_popup(menu):
    point = menu.mapToGlobal(QPoint(menu.width() - 50, menu.height() // 2))
    image = menu.screen().grabWindow(0, point.x(), point.y(), 16, 16).toImage()
    assert not image.isNull(), "Desktop capture is unavailable"
    pixels = [image.pixelColor(x, y) for y in range(image.height()) for x in range(image.width())]
    return tuple(
        sum(getattr(color, channel)() for color in pixels) / len(pixels)
        for channel in ("red", "green", "blue")
    )


def main(style="Fusion"):
    app = QApplication([])
    app.setStyle(style)
    if not _supports_windows_acrylic():
        print("Windows 11 acrylic verification skipped on this platform")
        return
    manager = theme_manager()
    manager.setWallpaperEnabled(False)
    window = ModernWindow()
    # Keep our sample backdrop above other applications during desktop capture.
    window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    backdrop = _Backdrop()
    window.setCentralWidget(backdrop)
    window.resize(600, 440)
    available = window.screen().availableGeometry()
    window.move(available.center() - QPoint(300, 220))
    window.show()
    window.activateWindow()
    QTest.qWait(250)
    menu = ModernMenu(window)
    menu.setFixedWidth(240)
    for index in range(7):
        menu.addAction(f"Action {index}")
    submenu = menu.addMenu("Submenu")
    submenu.setFixedWidth(240)
    for index in range(7):
        submenu.addAction(f"Child {index}")
    try:
        for popup in (menu, submenu):
            popup.popup(window.mapToGlobal(QPoint(150, 100)))
            # Switch an already open popup in both directions.
            for mode in (ThemeMode.LIGHT, ThemeMode.DARK, ThemeMode.LIGHT):
                manager.setMode(mode)
                assert popup._rounded_style._native_acrylic
                samples = []
                for color in ("red", "blue"):
                    backdrop.color = QColor(color)
                    backdrop.update()
                    QTest.qWait(350)
                    samples.append(_sample_popup(popup))
                red, blue = samples
                contrast = 24 if mode == ThemeMode.LIGHT else 10
                assert red[0] - blue[0] > contrast and blue[2] - red[2] > contrast, (
                    "The popup does not transmit backdrop colors",
                    mode,
                    samples,
                )
                print(f"{mode.value} {popup.title() or 'menu'} backdrop={samples}")
            popup.close()
    finally:
        menu.close()
        submenu.close()
        window.close()
    print("Windows 11 acrylic desktop verification passed")


if __name__ == "__main__":
    main()
