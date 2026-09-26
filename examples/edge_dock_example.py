"""Drag the strip to a screen edge; leave the window to reveal its handle."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from pyside6_modern_widgets import EdgeDockController, ModernSwitch, ModernWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ModernWindow(None, Qt.WindowType.Tool)
    window.setWindowTitle("Screen-edge docking")
    window.resize(400, 240)
    content = QWidget()
    layout = QVBoxLayout(content)
    drag_strip = QLabel("Drag here to a screen edge")
    drag_strip.setMinimumHeight(48)
    layout.addWidget(drag_strip)
    layout.addWidget(QLineEdit("Text selection still works"))
    auto_hide = ModernSwitch("Hide when the pointer leaves")
    auto_hide.setChecked(True)
    layout.addWidget(auto_hide)
    close = QPushButton("Close")
    close.clicked.connect(window.close)
    layout.addWidget(close)
    window.setCentralWidget(content)
    dock = EdgeDockController(window, drag_widget=drag_strip)
    auto_hide.toggled.connect(dock.setAutoHide)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
