"""Standalone frameless multi-tab window example."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from pyside6_modern_widgets import ModernWindow, TabView


class TabViewWindow(ModernWindow):
    """A multi-tab ModernWindow without a menu bar."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TabView Example")
        self.resize(800, 600)
        self.setMinimumSize(480, 320)

        self.tab_view = TabView(self)
        self.setCentralWidget(self.tab_view)

        self.tab_view.addTabClicked.connect(self.add_document)
        self.tab_view.tabCloseRequested.connect(self.close_tab)
        self.tab_view.currentChanged.connect(self.tab_changed)

        self.add_page("Home Page", "Home")
        self.add_page("Settings", "Settings")

    def add_page(self, content: str, title: str, *, select: bool = False) -> int:
        page = QLabel(content, self.tab_view)
        page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page.setStyleSheet("font-size: 20pt; color: #555555;")
        index = self.tab_view.addTab(page, title)
        if select:
            self.tab_view.setCurrentIndex(index)
        return index

    def add_document(self) -> None:
        number = self.tab_view.count() + 1
        self.add_page(
            f"New Content {number}",
            f"Document {number}",
            select=True,
        )

    def close_tab(self, index: int) -> None:
        page = self.tab_view.widget(index)
        self.tab_view.removeTab(index)
        if page is not None:
            page.deleteLater()
        if self.tab_view.count() == 0:
            self.close()

    def tab_changed(self, index: int) -> None:
        if index >= 0:
            print(f"Switched to tab {index}: {self.tab_view.tabText(index)}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("TabView Example")
    window = TabViewWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
