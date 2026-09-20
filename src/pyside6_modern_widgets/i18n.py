"""Translation-catalog loading without changing application-global state."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QLocale, QObject, QTranslator

_CATALOG_NAME = "pyside6_modern_widgets"
_TRANSLATIONS_DIRECTORY = Path(__file__).with_name("translations")


def load_translator(
    locale: QLocale | str,
    parent: QObject | None = None,
) -> QTranslator | None:
    """Load the best bundled catalog for ``locale`` without installing it.

    The caller owns installation through ``QCoreApplication.installTranslator``.
    Passing the application as ``parent`` keeps the translator alive for the
    application lifetime.
    """

    resolved_locale = locale if isinstance(locale, QLocale) else QLocale(locale)
    translator = QTranslator(parent)
    if translator.load(
        resolved_locale,
        _CATALOG_NAME,
        "_",
        str(_TRANSLATIONS_DIRECTORY),
    ):
        return translator
    translator.deleteLater()
    return None
