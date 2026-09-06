from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QVBoxLayout

from pyside6_modern_widgets import LIGHT_THEME, ModernDialog

_APP = QApplication.instance() or QApplication([])


def _application() -> QApplication:
    return _APP


def test_modern_dialog_preserves_qdialog_api_and_direct_layouts() -> None:
    dialog = ModernDialog(theme=LIGHT_THEME)
    layout = QVBoxLayout(dialog)
    label = QLabel("content")
    layout.addWidget(label)

    assert isinstance(dialog, QDialog)
    assert dialog.layout() is layout
    assert dialog.windowFlags() & Qt.WindowType.Dialog
    assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert dialog.contentsMargins().top() == dialog._title_bar.height()
    assert dialog._title_bar.findChildren(QPushButton) == [dialog._title_bar.closeButton]
    assert not hasattr(dialog, "addTitleBarButton")
    assert not hasattr(dialog, "setCentralWidget")


def test_modern_dialog_keeps_exec_and_accept_result() -> None:
    dialog = ModernDialog(theme=LIGHT_THEME)
    QTimer.singleShot(0, dialog.accept)

    assert dialog.exec() == QDialog.DialogCode.Accepted
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_modern_dialog_close_button_rejects_dialog() -> None:
    dialog = ModernDialog(theme=LIGHT_THEME)
    rejected = QSignalSpy(dialog.rejected)
    dialog.show()
    _application().processEvents()

    QTest.mouseClick(dialog._title_bar.closeButton, Qt.MouseButton.LeftButton)
    _application().processEvents()

    assert rejected.count() == 1
    assert dialog.result() == QDialog.DialogCode.Rejected
    assert not dialog.isVisible()


def test_modern_dialog_synchronizes_title_icon_and_theme() -> None:
    dialog = ModernDialog(theme=LIGHT_THEME)
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor("red"))
    icon = QIcon(pixmap)

    dialog.setWindowTitle("Settings")
    dialog.setWindowIcon(icon)

    assert dialog.windowTitle() == "Settings"
    assert dialog._title_bar.titleLabel.text() == "Settings"
    assert not dialog._title_bar.iconLabel.pixmap().isNull()
    assert dialog.theme() == LIGHT_THEME


def test_modern_dialog_lays_out_chrome_around_user_content() -> None:
    dialog = ModernDialog(theme=LIGHT_THEME)
    layout = QVBoxLayout(dialog)
    label = QLabel("content")
    layout.addWidget(label)
    dialog.resize(420, 240)
    dialog.show()
    _application().processEvents()

    assert dialog._background_frame.geometry() == dialog.rect()
    assert dialog._chrome_overlay.geometry() == dialog.rect()
    assert dialog._title_bar.geometry().top() == 0
    assert dialog._title_bar.width() == dialog.width()
    assert label.geometry().top() >= dialog._title_bar.height()

    image = dialog.grab().toImage()
    assert image.pixelColor(1, 1).alpha() < 128


def test_modern_dialog_resize_edges_respect_fixed_dimensions() -> None:
    dialog = ModernDialog(theme=LIGHT_THEME)
    dialog.resize(420, 240)

    assert dialog._resize_edges_at(QPoint(0, 0)) == (Qt.Edge.TopEdge | Qt.Edge.LeftEdge)

    dialog.setFixedWidth(420)
    assert dialog._resize_edges_at(QPoint(0, 120)) == Qt.Edge(0)
    assert dialog._resize_edges_at(QPoint(210, 0)) == Qt.Edge.TopEdge
