"""Interactive gallery for modern windows, navigation, menus, dialogs, and controls."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from pyside6_modern_widgets import (
    ModernComboBox,
    ModernDialog,
    ModernMenu,
    ModernMenuBar,
    ModernMessageBox,
    ModernSwitch,
    ModernWindow,
    NavigationPosition,
    NavigationView,
    ThemeMode,
    theme_manager,
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
            self._create_combo_box_page(),
            "Combo box",
            standard_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
        )
        self.navigation.addPage(
            self._create_switch_page(),
            "Switch",
            standard_icon(QStyle.StandardPixmap.SP_DialogYesButton),
        )
        self.navigation.addPage(
            self._create_settings_page(),
            "Settings",
            QIcon(":/pyside6_modern_widgets/icons/settings.png"),
            position=NavigationPosition.BOTTOM,
        )

        self._create_actions()
        self._create_menu_bar()

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
        description = QLabel(
            "Window, navigation, menu, dialog, message box, combo box, and switch examples."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
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

    @staticmethod
    def _create_appearance_controls() -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Appearance"))
        for mode in ThemeMode:
            button = QPushButton(mode.value.title())
            button.clicked.connect(lambda _checked=False, mode=mode: theme_manager().setMode(mode))
            layout.addWidget(button)
        layout.addStretch()
        return layout

    def _create_combo_box_page(self) -> QWidget:
        page, layout = self._create_page("ModernComboBox")
        layout.addWidget(QLabel("Rounded controls, familiar Qt interactions."))
        layout.addLayout(self._create_appearance_controls())
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)
        grid.addWidget(QLabel("Native QComboBox"), 0, 1)
        grid.addWidget(QLabel("ModernComboBox"), 0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        layout.addLayout(grid)
        status = QLabel("Choose an item to see the native activated signal.")
        status.setWordWrap(True)
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
                    lambda index, combo=combo, label=label: status.setText(
                        f"{type(combo).__name__} / {label}: index={index}, text={combo.currentText()}"
                    )
                )
                grid.addWidget(combo, row, column)
        layout.addStretch()
        layout.addWidget(status)
        return page

    def _create_switch_page(self) -> QWidget:
        page, layout = self._create_page("ModernSwitch")
        hint = QLabel("Click to toggle. Use Tab and Space to try the keyboard focus indicator.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addLayout(self._create_appearance_controls())
        form = QFormLayout()
        form.setVerticalSpacing(14)
        form.addRow("QLineEdit", QLineEdit("Native text field"))
        for widget_type in (QComboBox, ModernComboBox):
            combo = widget_type()
            combo.addItems(["Default size", "No fixed height"])
            form.addRow(widget_type.__name__, combo)
        switch = ModernSwitch("Enable notifications")
        switch.setChecked(True)
        form.addRow("ModernSwitch", switch)
        states = QHBoxLayout()
        for checked in (False, True):
            disabled = ModernSwitch("Disabled")
            disabled.setChecked(checked)
            disabled.setEnabled(False)
            states.addWidget(disabled)
        form.addRow("Disabled states", states)
        rtl = ModernSwitch("Right to left")
        rtl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        rtl.setChecked(True)
        form.addRow("RTL", rtl)
        layout.addLayout(form)
        status = QLabel("Notifications: on")
        switch.toggled.connect(
            lambda checked: status.setText(f"Notifications: {'on' if checked else 'off'}")
        )
        layout.addWidget(status)
        layout.addStretch()
        return page

    def _create_settings_page(self) -> QWidget:
        page, layout = self._create_page("Settings")
        manager = theme_manager()
        layout.addWidget(QLabel("Appearance"))
        self.theme_mode_combo = QComboBox()
        for label, mode in (
            ("Follow system", ThemeMode.SYSTEM),
            ("Light", ThemeMode.LIGHT),
            ("Dark", ThemeMode.DARK),
        ):
            self.theme_mode_combo.addItem(label, mode.value)
        self._sync_theme_mode(manager.mode())
        self.theme_mode_combo.currentIndexChanged.connect(self._set_theme_mode)
        manager.modeChanged.connect(self._sync_theme_mode)
        layout.addWidget(self.theme_mode_combo)

        self.wallpaper_checkbox = QCheckBox("Use desktop wallpaper colors")
        self.wallpaper_checkbox.setChecked(manager.wallpaperEnabled())
        self.wallpaper_checkbox.toggled.connect(manager.setWallpaperEnabled)
        manager.wallpaperEnabledChanged.connect(self.wallpaper_checkbox.setChecked)
        layout.addWidget(self.wallpaper_checkbox)
        layout.addStretch()
        return page

    def _set_theme_mode(self, _index: int) -> None:
        theme_manager().setMode(ThemeMode(self.theme_mode_combo.currentData()))

    def _sync_theme_mode(self, mode: ThemeMode) -> None:
        self.theme_mode_combo.blockSignals(True)
        self.theme_mode_combo.setCurrentIndex(self.theme_mode_combo.findData(mode.value))
        self.theme_mode_combo.blockSignals(False)

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

        self.native_menu = QMenu("Native actions", self)
        self._populate_example_menu(self.native_menu)
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

        dialog.exec()

    def _show_information(self) -> None:
        ModernMessageBox.information(
            self,
            "Update complete",
            "The application is up to date.",
        )

    def _show_question(self) -> None:
        ModernMessageBox.question(
            self,
            "Replace file",
            "A file with this name already exists. Replace it?",
            ModernMessageBox.StandardButton.Yes | ModernMessageBox.StandardButton.No,
            ModernMessageBox.StandardButton.No,
        )

    def _show_warning(self) -> None:
        ModernMessageBox.warning(
            self,
            "Unsaved changes",
            "Closing now will discard your changes.",
            ModernMessageBox.StandardButton.Save
            | ModernMessageBox.StandardButton.Discard
            | ModernMessageBox.StandardButton.Cancel,
            ModernMessageBox.StandardButton.Save,
        )

    def _show_critical(self) -> None:
        ModernMessageBox.critical(
            self,
            "Connection failed",
            "The server could not be reached.",
            ModernMessageBox.StandardButton.Retry | ModernMessageBox.StandardButton.Cancel,
            ModernMessageBox.StandardButton.Retry,
        )

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
        message_box.exec()

    def _create_actions(self) -> None:
        self.compact_action = QAction("Compact Navigation", self)
        self.compact_action.setCheckable(True)
        self.compact_action.toggled.connect(self.navigation.sidebar.setCollapsed)
        self.navigation.sidebar.collapsedChanged.connect(self.compact_action.setChecked)

        self.quit_action = QAction("Quit", self)
        self.quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self.quit_action.triggered.connect(QApplication.quit)

        self.full_screen_action = QAction("Toggle Full Screen", self)
        self.full_screen_action.setCheckable(True)
        self.full_screen_action.setShortcut(QKeySequence("F11"))
        self.full_screen_action.toggled.connect(self._toggle_full_screen)

    def _create_menu_bar(self) -> None:
        menu_bar = ModernMenuBar(self)
        menu_bar.setNativeMenuBar(False)

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.quit_action)

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.compact_action)
        view_menu.addSeparator()
        view_menu.addAction(self.full_screen_action)

        window_menu = menu_bar.addMenu("&Window")
        window_menu.addAction("Minimize", self.showMinimized)
        window_menu.addAction("Maximize / Restore", self._toggle_maximized)
        window_menu.addSeparator()
        close_action = window_menu.addAction("Close", self.close)
        close_action.setShortcut(QKeySequence.StandardKey.Close)

        assert self.titleBar is not None
        self.titleBar.addCustomWidget(menu_bar, align="left")

    def _toggle_full_screen(self, enabled: bool) -> None:
        if enabled:
            self.showFullScreen()
        else:
            self.showNormal()

    def _toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Modern Widgets Example")
    window = ExampleWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
