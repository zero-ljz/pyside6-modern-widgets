"""ModernWindow and NavigationView example with empty pages."""

from __future__ import annotations

import sys

from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import QApplication, QWidget

from pyside6_modern_widgets import (
    ModernWindow,
    NavigationPosition,
    NavigationView,
)


def resource_icon(name: str) -> QIcon:
    return QIcon(f":/pyside6_modern_widgets/icons/{name}")


class ExampleWindow(ModernWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Modern Widgets Example")
        self.setWindowIcon(resource_icon("application.png"))
        self.resize(1000, 640)
        self.setMinimumSize(720, 460)

        self.navigation = NavigationView()
        self.setCentralWidget(self.navigation)
        self._page_names = ("Home", "Search", "Account", "Settings")

        self.navigation.addPage(
            QWidget(),
            "Home",
            resource_icon("home.png"),
            selected=True,
        )
        self.navigation.addPage(
            QWidget(),
            "Search",
            resource_icon("search.png"),
        )
        self.navigation.addPage(
            QWidget(),
            "Account",
            resource_icon("account.png"),
            position=NavigationPosition.BOTTOM,
        )
        self.navigation.addPage(
            QWidget(),
            "Settings",
            resource_icon("settings.png"),
            position=NavigationPosition.BOTTOM,
        )

        self._create_actions()
        self._create_menu_bar()
        self.navigation.currentChanged.connect(self._page_changed)
        self.statusBar().showMessage("Ready")

    def _create_actions(self) -> None:
        self.compact_action = QAction("Compact navigation", self)
        self.compact_action.setCheckable(True)
        self.compact_action.toggled.connect(self.navigation.sidebar.setCollapsed)
        self.navigation.sidebar.collapsedChanged.connect(self.compact_action.setChecked)

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self.exit_action.triggered.connect(self.close)

    def _create_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.exit_action)
        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.compact_action)

    def _page_changed(self, index: int) -> None:
        if 0 <= index < len(self._page_names):
            self.statusBar().showMessage(self._page_names[index], 3000)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Modern Widgets Example")
    window = ExampleWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
