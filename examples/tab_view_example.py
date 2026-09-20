"""Standalone frameless multi-tab window example."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, Qt, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QLabel

from pyside6_modern_widgets import ModernWindow, TabView, load_translator


class TabViewWindow(ModernWindow):
    """A multi-tab ModernWindow without a menu bar."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(self.tr("TabView Example"))
        self.setWindowIcon(QIcon(":/pyside6_modern_widgets/icons/application.png"))
        self.resize(800, 600)
        self.setMinimumSize(480, 320)

        self.tab_view = TabView(self)
        self.setCentralWidget(self.tab_view)

        self.tab_view.addTabClicked.connect(self.add_document)
        self.tab_view.tabCloseRequested.connect(self.close_tab)
        self.tab_view.currentChanged.connect(self.tab_changed)

        self.add_page(self.tr("Home Page"), self.tr("Home"))
        self.add_page(self.tr("Settings"), self.tr("Settings"))

    def add_page(self, content: str, title: str, *, select: bool = False) -> int:
        page = QLabel(content, self.tab_view)
        page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page.setStyleSheet("font-size: 20pt;")
        index = self.tab_view.addTab(page, title)
        if select:
            self.tab_view.setCurrentIndex(index)
        return index

    def add_document(self) -> None:
        number = self.tab_view.count() + 1
        self.add_page(
            self.tr("New Content %1").replace("%1", str(number)),
            self.tr("Document %1").replace("%1", str(number)),
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
            print(
                self.tr("Switched to tab %1: %2")
                .replace("%1", str(index))
                .replace("%2", self.tab_view.tabText(index))
            )


def _install_translators(app: QApplication, locale: QLocale) -> None:
    qt_translator = QTranslator(app)
    if qt_translator.load(
        locale,
        "qtbase",
        "_",
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath),
    ):
        app.installTranslator(qt_translator)

    widgets_translator = load_translator(locale, app)
    if widgets_translator is not None:
        app.installTranslator(widgets_translator)

    example_translator = QTranslator(app)
    if example_translator.load(
        locale,
        "examples",
        "_",
        str(Path(__file__).with_name("translations")),
    ):
        app.installTranslator(example_translator)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    locale = QLocale.system()
    _install_translators(app, locale)
    app.setApplicationName(QCoreApplication.translate("TabViewWindow", "TabView Example"))
    window = TabViewWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
