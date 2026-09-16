"""Verify Win11 acrylic in the desktop composite (requires an interactive desktop).

Run with: python tests/windows_appearance_smoke.py
Widget.grab() excludes DWM acrylic, so sample only our popup's desktop rectangle.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from pyside6_modern_widgets import (
    ModernComboBox,
    ModernFlyout,
    ModernMenu,
    ModernNotification,
    ModernWindow,
    ThemeMode,
    theme_manager,
)
from pyside6_modern_widgets.modern_menu import _supports_windows_acrylic


class _Backdrop(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("blue"))
        painter.fillRect(0, 0, self.width() // 2, self.height(), QColor("red"))


def _sample_popup(menu, x):
    point = menu.mapToGlobal(QPoint(x, menu.height() // 2))
    image = menu.screen().grabWindow(0, point.x(), point.y(), 16, 16).toImage()
    assert not image.isNull(), "Desktop capture is unavailable"
    pixels = [image.pixelColor(x, y) for y in range(image.height()) for x in range(image.width())]
    return tuple(
        sum(getattr(color, channel)() for color in pixels) / len(pixels)
        for channel in ("red", "green", "blue")
    )


def _verify_editable_opening(combo):
    # Exercise the first and repeated opens, before the 150ms Qt animation
    # would finish. Checking only the settled popup misses the black flash.
    effect = Qt.UIEffect.UI_AnimateCombo
    previous = QApplication.isEffectEnabled(effect)
    QApplication.setEffectEnabled(effect, True)
    try:
        for _ in range(2):
            combo.showPopup()
            popup = combo.view().window()
            assert popup.isVisible() and combo._modern_style._native_acrylic
            assert QApplication.isEffectEnabled(effect)
            assert not any(
                widget.metaObject().className() == "QRollEffect" and widget.isVisible()
                for widget in QApplication.topLevelWidgets()
            )
            for delay in (0, 16, 32, 64):
                QTest.qWait(delay)
                for x in (80, popup.width() - 50):
                    sample = _sample_popup(popup, x)
                    assert sum(sample) > 60, ("Black opening frame", delay, sample)
            combo.hidePopup()
    finally:
        combo.hidePopup()
        QApplication.setEffectEnabled(effect, previous)


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
    combos = []
    for editable in (False, True):
        combo = ModernComboBox(backdrop)
        combo.setEditable(editable)
        combo.move(150, 100)
        combo.resize(240, 32)
        combo.addItems([f"Option {index}" for index in range(7)])
        combos.append(combo)
    anchor = QWidget(backdrop)
    anchor.setGeometry(150, 68, 240, 24)
    anchor.show()
    flyout = ModernFlyout(window)
    content = QWidget()
    content.setMinimumSize(216, 136)
    flyout.setContentWidget(content)
    notification = ModernNotification()
    notification._configure_desktop()
    notification.resize(240, 160)
    try:
        for control in (menu, submenu, *combos, flyout, notification):
            if isinstance(control, ModernNotification):
                control.move(window.mapToGlobal(QPoint(150, 100)))
                control.show()
                popup = control
                popup_style = control
                name = "notification"
            elif isinstance(control, ModernFlyout):
                control.popup(anchor)
                popup = control
                popup_style = control
                name = "flyout"
            elif isinstance(control, ModernComboBox):
                control.show()
                if control.isEditable():
                    _verify_editable_opening(control)
                control.showPopup()
                popup = control.view().window()
                popup_style = control._modern_style
                name = f"combo editable={control.isEditable()}"
            else:
                control.popup(window.mapToGlobal(QPoint(150, 100)))
                popup = control
                popup_style = control._rounded_style
                name = control.title() or "menu"
            # Switch an already open popup in both directions.
            for mode in (ThemeMode.LIGHT, ThemeMode.DARK, ThemeMode.LIGHT):
                manager.setMode(mode)
                # Sample both halves of a static backdrop. DWM may cache the
                # acrylic backdrop when the obscured widget repaints in place.
                QTest.qWait(600)
                assert popup_style._native_acrylic
                samples = [_sample_popup(popup, x) for x in (80, popup.width() - 50)]
                red, blue = samples
                contrast = 24 if mode == ThemeMode.LIGHT else 10
                assert red[0] - blue[0] > contrast and blue[2] - red[2] > contrast, (
                    "The popup does not transmit backdrop colors",
                    mode,
                    samples,
                )
                print(f"{mode.value} {name} backdrop={samples}")
            popup.close()
            if isinstance(control, ModernComboBox):
                control.hidePopup()
                control.hide()
    finally:
        notification.close()
        flyout.close()
        menu.close()
        submenu.close()
        window.close()
    print("Windows 11 acrylic desktop verification passed")


if __name__ == "__main__":
    main()
