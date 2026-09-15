"""Compare native QComboBox behavior with the ModernComboBox appearance."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyside6_modern_widgets import ModernComboBox, ModernWindow, ThemeMode, theme_manager


class ComboBoxWindow(ModernWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ModernComboBox")
        self.resize(820, 610)
        content = QWidget()
        self.setCentralWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)
        title = QLabel("Modern ComboBox")
        title_font = title.font()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        layout.addWidget(QLabel("Rounded controls, familiar Qt interactions."))

        themes = QHBoxLayout()
        themes.addWidget(QLabel("Appearance"))
        for mode in ThemeMode:
            button = QPushButton(mode.value.title())
            button.clicked.connect(lambda _checked=False, mode=mode: theme_manager().setMode(mode))
            themes.addWidget(button)
        themes.addStretch()
        layout.addLayout(themes)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)
        grid.addWidget(QLabel("Native QComboBox"), 0, 1)
        grid.addWidget(QLabel("ModernComboBox"), 0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        layout.addLayout(grid)
        self.status = QLabel("Choose an item to see the native activated signal.")
        for row, label in enumerate(
            (
                "Standard",
                "Icons",
                "Placeholder",
                "Editable",
                "Disabled",
                "Long list",
                "Right to left",
            ),
            start=1,
        ):
            grid.addWidget(QLabel(label), row, 0)
            for column, widget_type in enumerate((QComboBox, ModernComboBox), start=1):
                combo = widget_type()
                combo.setMinimumWidth(230)
                combo.addItems(["Windows 11", "Windows 10", "Linux", "macOS"])
                if label == "Icons":
                    combo.setItemIcon(0, QIcon(":/pyside6_modern_widgets/icons/settings.png"))
                    combo.setItemIcon(1, QIcon(":/pyside6_modern_widgets/icons/application.png"))
                    combo.insertSeparator(2)
                elif label == "Placeholder":
                    combo.setPlaceholderText("Choose an operating system")
                    combo.setCurrentIndex(-1)
                elif label == "Editable":
                    combo.setEditable(True)
                    combo.setInsertPolicy(QComboBox.InsertPolicy.InsertAtBottom)
                elif label == "Disabled":
                    combo.setEnabled(False)
                elif label == "Long list":
                    combo.clear()
                    combo.addItems([f"Option {number:02d}" for number in range(1, 51)])
                    combo.setMaxVisibleItems(8)
                elif label == "Right to left":
                    combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                combo.activated.connect(
                    lambda index, combo=combo, label=label: self.status.setText(
                        f"{type(combo).__name__} / {label}: index={index}, text={combo.currentText()}"
                    )
                )
                grid.addWidget(combo, row, column)
        layout.addStretch()
        layout.addWidget(self.status)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ComboBoxWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
