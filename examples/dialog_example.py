"""Display a ModernDialog while using the standard QDialog API."""

import sys

from PySide6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from pyside6_modern_widgets import ModernDialog


def main() -> int:
    _application = QApplication(sys.argv)
    dialog = ModernDialog()
    dialog.setWindowTitle("Modern dialog")

    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel("ModernDialog keeps the standard QDialog API."))

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    return 0 if dialog.exec() == ModernDialog.DialogCode.Accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
