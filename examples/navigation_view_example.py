"""Interactive example for the modern window, navigation, menus, and dialogs."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialogButtonBox,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from pyside6_modern_widgets import (
    ModernDialog,
    ModernMenu,
    ModernMenuBar,
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
        self.setTitleVisible(False)
        self.setTitleAlignment("center")
        self.setWindowIcon(QIcon(":/pyside6_modern_widgets/icons/application.png"))
        self.resize(1000, 640)

        self.navigation = NavigationView()
        self.setCentralWidget(self.navigation)
        self._page_names = ("Home", "Dialog", "Message boxes", "Menu", "Settings")

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
            self._create_menu_page(),
            "Menu",
            standard_icon(QStyle.StandardPixmap.SP_FileDialogListView),
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
        layout.addWidget(QLabel("Window, navigation, menu, dialog, and message box examples."))
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

    def _create_menu_page(self) -> QWidget:
        page, layout = self._create_page("Menus")
        self.menu_button = QPushButton(
            standard_icon(QStyle.StandardPixmap.SP_TitleBarMenuButton),
            "Open ModernMenu",
        )
        self.menu_button.setFixedWidth(220)
        self.menu_button.clicked.connect(self._show_menu)
        layout.addWidget(self.menu_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.native_menu_button = QPushButton(
            standard_icon(QStyle.StandardPixmap.SP_TitleBarMenuButton),
            "Open native QMenu",
        )
        self.native_menu_button.setFixedWidth(220)
        self.native_menu_button.clicked.connect(self._show_native_menu)
        layout.addWidget(self.native_menu_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.choice_groups: list[QActionGroup] = []
        self.example_menu = ModernMenu("Actions", self)
        self._populate_example_menu(self.example_menu)
        self.example_menu.triggered.connect(self._menu_action_triggered)

        self.native_menu = QMenu("Native actions", self)
        self._populate_example_menu(self.native_menu)
        self.native_menu.triggered.connect(self._menu_action_triggered)
        layout.addStretch()
        return page

    def _populate_example_menu(self, menu: QMenu) -> None:
        default_action = menu.addAction("Default action")
        menu.setDefaultAction(default_action)
        menu.addAction(
            standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton),
            "Qt standard icon",
        )
        menu.addAction(
            QIcon(":/pyside6_modern_widgets/icons/application.png"),
            "Custom icon",
        )
        menu.addSeparator()

        toggle_action = menu.addAction("Checkable toggle")
        toggle_action.setCheckable(True)
        toggle_action.setChecked(True)

        choice_menu = menu.addMenu("Single choice")
        choice_group = QActionGroup(choice_menu)
        choice_group.setExclusive(True)
        self.choice_groups.append(choice_group)
        for text in ("Compact", "Comfortable", "Spacious"):
            action = choice_menu.addAction(text)
            action.setCheckable(True)
            choice_group.addAction(action)
            if text == "Comfortable":
                action.setChecked(True)

        menu.addSeparator()
        combined_shortcut = menu.addAction("Combined shortcut")
        combined_shortcut.setShortcut(QKeySequence("Ctrl+Shift+S"))
        combined_shortcut.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        alt_shortcut = menu.addAction("Alt shortcut")
        alt_shortcut.setShortcut(QKeySequence("Alt+M"))
        alt_shortcut.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        menu.addAction("&Keyboard mnemonic")

        nested_menu = menu.addMenu("Nested menus")
        level_two_menu = nested_menu.addMenu("Level 2")
        level_three_menu = level_two_menu.addMenu("Level 3")
        level_three_menu.addAction("Deep action")

        menu.addSeparator()
        unavailable_action = menu.addAction("Unavailable action")
        unavailable_action.setEnabled(False)

    def _show_menu(self) -> None:
        position = self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft())
        self.example_menu.popup(position)

    def _show_native_menu(self) -> None:
        position = self.native_menu_button.mapToGlobal(self.native_menu_button.rect().bottomLeft())
        self.native_menu.popup(position)

    def _menu_action_triggered(self, action: QAction) -> None:
        self.statusBar().showMessage(f"Menu: {action.text()}", 3000)

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

        self.new_window_action = QAction("New window", self)
        self.new_window_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_window_action.triggered.connect(lambda: self._show_action_message("New window"))

        self.open_action = QAction("Open...", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(lambda: self._show_action_message("Open"))

        self.preferences_action = QAction("Preferences...", self)
        self.preferences_action.triggered.connect(lambda: self.navigation.setCurrentIndex(4))

        self.about_action = QAction("About Modern Widgets", self)
        self.about_action.triggered.connect(
            lambda: self._show_action_message("Modern Widgets Example")
        )

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self.exit_action.triggered.connect(self.close)

    def _create_menu_bar(self) -> None:
        menu_bar = ModernMenuBar(self)
        menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.new_window_action)
        file_menu.addAction(self.open_action)
        recent_menu = file_menu.addMenu("Open recent")
        recent_menu.addAction(
            "project-notes.md", lambda: self._show_action_message("project-notes.md")
        )
        recent_menu.addAction(
            "theme-preview.py", lambda: self._show_action_message("theme-preview.py")
        )
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        edit_menu = menu_bar.addMenu("&Edit")
        undo_action = edit_menu.addAction("Undo")
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.setEnabled(False)
        redo_action = edit_menu.addAction("Redo")
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.setEnabled(False)
        edit_menu.addSeparator()
        for text, shortcut in (
            ("Cut", QKeySequence.StandardKey.Cut),
            ("Copy", QKeySequence.StandardKey.Copy),
            ("Paste", QKeySequence.StandardKey.Paste),
        ):
            action = edit_menu.addAction(text)
            action.setShortcut(shortcut)
            action.triggered.connect(
                lambda _checked=False, name=text: self._show_action_message(name)
            )

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.compact_action)
        navigate_menu = menu_bar.addMenu("&Navigate")
        for index, page_name in enumerate(self._page_names):
            action = navigate_menu.addAction(page_name)
            action.triggered.connect(
                lambda _checked=False, target=index: self.navigation.setCurrentIndex(target)
            )

        tools_menu = menu_bar.addMenu("&Tools")
        tools_menu.addAction(self.preferences_action)
        tools_menu.addSeparator()
        tools_menu.addAction("Check for updates", lambda: self._show_action_message("Up to date"))

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction("Documentation", lambda: self._show_action_message("Documentation"))
        help_menu.addAction(self.about_action)
        assert self.titleBar is not None
        self.titleBar.addCustomWidget(menu_bar, align="left")

    def _show_action_message(self, message: str) -> None:
        self.statusBar().showMessage(message, 3000)

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
