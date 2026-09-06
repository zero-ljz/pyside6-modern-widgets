"""Interactive example for the modern window, navigation, and dialogs."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from pyside6_modern_widgets import (
    ModernDialog,
    ModernMessageBox,
    ModernWindow,
    NavigationPosition,
    NavigationView,
)


def standard_icon(name: QStyle.StandardPixmap) -> QIcon:
    return QApplication.style().standardIcon(name)


class ExampleWindow(ModernWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Modern Widgets Example")
        self.setWindowIcon(QIcon(":/pyside6_modern_widgets/icons/application.png"))
        self.resize(1000, 640)

        self.navigation = NavigationView()
        self.setCentralWidget(self.navigation)
        self._page_names = ("Home", "Dialog", "Message boxes", "Settings")

        self.navigation.addPage(
            self._create_home_page(),
            "Home",
            standard_icon(QStyle.StandardPixmap.SP_DesktopIcon),
            selected=True,
        )
        self.navigation.addPage(
            self._create_dialog_page(),
            "Dialog",
            standard_icon(QStyle.StandardPixmap.SP_DialogApplyButton),
        )
        self.navigation.addPage(
            self._create_message_box_page(),
            "Message boxes",
            standard_icon(QStyle.StandardPixmap.SP_MessageBoxInformation),
        )
        self.navigation.addPage(
            self._create_settings_page(),
            "Settings",
            standard_icon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            position=NavigationPosition.BOTTOM,
        )

        self._create_actions()
        self._create_menu_bar()
        self.navigation.currentChanged.connect(self._page_changed)
        self.statusBar().showMessage("Ready")

    @staticmethod
    def _create_page(title: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(12)

        heading = QLabel(title)
        heading_font = heading.font()
        heading_font.setPointSize(heading_font.pointSize() + 6)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        layout.addWidget(heading)
        return page, layout

    def _create_home_page(self) -> QWidget:
        page, layout = self._create_page("Modern Widgets")
        layout.addWidget(QLabel("Window, navigation, dialog, and message box examples."))
        layout.addStretch()
        return page

    def _create_dialog_page(self) -> QWidget:
        page, layout = self._create_page("ModernDialog")
        open_button = QPushButton(
            standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton),
            "Open dialog",
        )
        open_button.setFixedWidth(220)
        open_button.clicked.connect(self._show_dialog)
        layout.addWidget(open_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return page

    def _create_message_box_page(self) -> QWidget:
        page, layout = self._create_page("ModernMessageBox")
        examples = (
            (
                "Information",
                QStyle.StandardPixmap.SP_MessageBoxInformation,
                self._show_information,
            ),
            (
                "Question",
                QStyle.StandardPixmap.SP_MessageBoxQuestion,
                self._show_question,
            ),
            (
                "Warning",
                QStyle.StandardPixmap.SP_MessageBoxWarning,
                self._show_warning,
            ),
            (
                "Critical",
                QStyle.StandardPixmap.SP_MessageBoxCritical,
                self._show_critical,
            ),
            (
                "Detailed message",
                QStyle.StandardPixmap.SP_FileDialogDetailedView,
                self._show_detailed_message,
            ),
        )
        for text, icon, callback in examples:
            button = QPushButton(standard_icon(icon), text)
            button.setFixedWidth(220)
            button.clicked.connect(callback)
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return page

    def _create_settings_page(self) -> QWidget:
        page, layout = self._create_page("Settings")
        layout.addStretch()
        return page

    def _show_dialog(self) -> None:
        dialog = ModernDialog(self)
        dialog.setWindowTitle("Save changes")

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("The document has unsaved changes."))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        result = dialog.exec()
        result_name = "Accepted" if result == ModernDialog.DialogCode.Accepted else "Rejected"
        self.statusBar().showMessage(f"Dialog: {result_name}", 3000)

    def _show_information(self) -> None:
        result = ModernMessageBox.information(
            self,
            "Update complete",
            "The application is up to date.",
        )
        self._show_message_result("Information", result)

    def _show_question(self) -> None:
        result = ModernMessageBox.question(
            self,
            "Replace file",
            "A file with this name already exists. Replace it?",
            ModernMessageBox.StandardButton.Yes | ModernMessageBox.StandardButton.No,
            ModernMessageBox.StandardButton.No,
        )
        self._show_message_result("Question", result)

    def _show_warning(self) -> None:
        result = ModernMessageBox.warning(
            self,
            "Unsaved changes",
            "Closing now will discard your changes.",
            ModernMessageBox.StandardButton.Save
            | ModernMessageBox.StandardButton.Discard
            | ModernMessageBox.StandardButton.Cancel,
            ModernMessageBox.StandardButton.Save,
        )
        self._show_message_result("Warning", result)

    def _show_critical(self) -> None:
        result = ModernMessageBox.critical(
            self,
            "Connection failed",
            "The server could not be reached.",
            ModernMessageBox.StandardButton.Retry | ModernMessageBox.StandardButton.Cancel,
            ModernMessageBox.StandardButton.Retry,
        )
        self._show_message_result("Critical", result)

    def _show_detailed_message(self) -> None:
        message_box = ModernMessageBox(
            ModernMessageBox.Icon.Warning,
            "Import completed with warnings",
            "Some records could not be imported.",
            ModernMessageBox.StandardButton.Ok,
            self,
        )
        message_box.setInformativeText("Open the details to review the skipped records.")
        message_box.setDetailedText(
            "Row 17: missing email address\n"
            "Row 24: duplicate identifier\n"
            "Row 31: unsupported date format"
        )
        message_box.setCheckBox(QCheckBox("Do not show import warnings again"))
        result = ModernMessageBox.StandardButton(message_box.exec())
        self._show_message_result("Detailed message", result)

    def _show_message_result(
        self,
        kind: str,
        result: QMessageBox.StandardButton,
    ) -> None:
        self.statusBar().showMessage(f"{kind}: {result.name}", 3000)

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
