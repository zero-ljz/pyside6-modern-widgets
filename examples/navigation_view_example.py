"""ModernWindow and NavigationView example with empty pages."""

from __future__ import annotations

import sys

from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import QApplication, QStyle, QToolBar, QWidget

from pyside6_modern_widgets import ModernWindow, NavigationPosition, NavigationView


def standard_icon(name: QStyle.StandardPixmap) -> QIcon:
    return QApplication.style().standardIcon(name)


class ExampleWindow(ModernWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Modern Widgets Example")
        self.setWindowIcon(standard_icon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.resize(1000, 640)
        self.setMinimumSize(720, 460)

        self.navigation = NavigationView()
        self.setCentralWidget(self.navigation)
        self._page_names = ("Home", "Documents", "Activity", "Settings")

        self.navigation.addPage(
            QWidget(),
            "Home",
            standard_icon(QStyle.StandardPixmap.SP_DesktopIcon),
            selected=True,
        )
        self.navigation.addPage(
            QWidget(),
            "Documents",
            standard_icon(QStyle.StandardPixmap.SP_FileIcon),
        )
        self.navigation.addPage(
            QWidget(),
            "Activity",
            standard_icon(QStyle.StandardPixmap.SP_FileDialogListView),
        )
        self.navigation.addPage(
            QWidget(),
            "Settings",
            standard_icon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            position=NavigationPosition.BOTTOM,
        )

        self._create_actions()
        self._create_menu_bar()
        self._create_toolbar()
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

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Navigation", self)
        toolbar.setMovable(False)
        toolbar.addAction(
            standard_icon(QStyle.StandardPixmap.SP_ArrowBack),
            "Previous page",
            self.previous_page,
        )
        toolbar.addAction(
            standard_icon(QStyle.StandardPixmap.SP_ArrowForward),
            "Next page",
            self.next_page,
        )
        self.addToolBar(toolbar)

    def previous_page(self) -> None:
        index = (self.navigation.currentIndex() - 1) % self.navigation.count()
        self.navigation.setCurrentIndex(index)

    def next_page(self) -> None:
        index = (self.navigation.currentIndex() + 1) % self.navigation.count()
        self.navigation.setCurrentIndex(index)

    def _page_changed(self, index: int) -> None:
        if 0 <= index < len(self._page_names):
            self.statusBar().showMessage(self._page_names[index], 3000)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Modern Widgets Example")
    window = ExampleWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
