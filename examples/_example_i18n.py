"""Translation setup shared by the navigation and edge-dock examples."""

import argparse
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import load_translator


def example_locale() -> QLocale:
    parser = argparse.ArgumentParser(description="Modern widgets interactive example")
    parser.add_argument("--language", choices=("en", "zh_CN"), help="Override the system language")
    options, _qt_arguments = parser.parse_known_args()
    return QLocale(options.language) if options.language else QLocale.system()


def install_translators(app: QApplication, locale: QLocale) -> None:
    qt_translator = QTranslator(app)
    if qt_translator.load(
        locale, "qtbase", "_", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    ):
        app.installTranslator(qt_translator)
    widgets_translator = load_translator(locale, app)
    if widgets_translator is not None:
        app.installTranslator(widgets_translator)
    example_translator = QTranslator(app)
    if example_translator.load(
        locale, "examples", "_", str(Path(__file__).with_name("translations"))
    ):
        app.installTranslator(example_translator)
