"""Interactive gallery for modern windows, navigation, menus, dialogs, and controls."""

from __future__ import annotations

import sys

from PySide6.QtCore import QSize, Qt, QTimer
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
    QSlider,
    QStyle,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from pyside6_modern_widgets import (
    FlyoutPlacement,
    ModernComboBox,
    ModernDialog,
    ModernFlyout,
    ModernMenu,
    ModernMenuBar,
    ModernMessageBox,
    ModernSwitch,
    ModernToolBar,
    ModernWindow,
    NavigationPosition,
    NavigationView,
    NotificationKind,
    NotificationManager,
    NotificationPosition,
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
            self._create_toolbar_page(),
            "Toolbar",
            standard_icon(QStyle.StandardPixmap.SP_FileDialogContentsView),
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
            self._create_flyout_page(),
            "Flyout",
            standard_icon(QStyle.StandardPixmap.SP_TitleBarShadeButton),
        )
        self.navigation.addPage(
            self._create_notification_page(),
            "Notifications",
            standard_icon(QStyle.StandardPixmap.SP_MessageBoxInformation),
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
            "Modern windows, navigation, menus, dialogs, controls, flyouts, and desktop notifications."
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

    def _create_flyout_page(self) -> QWidget:
        page, layout = self._create_page("ModernFlyout")
        description = QLabel(
            "Open quick settings beside a button. Click outside or press Escape to close. "
            "Move the window near a screen edge to try automatic placement."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addLayout(self._create_appearance_controls())
        status = QLabel("Settings are kept when the panel closes.")
        status.setWordWrap(True)

        self.flyout = ModernFlyout(self)
        self.flyout.setAccessibleName("Quick settings")
        content = QWidget()
        content.setMinimumWidth(280)
        form = QFormLayout(content)
        form.setContentsMargins(4, 4, 4, 4)
        heading = QLabel("Quick settings")
        font = heading.font()
        font.setBold(True)
        heading.setFont(font)
        form.addRow(heading)
        name = QLineEdit()
        name.setPlaceholderText("Workspace name")
        form.addRow("Name", name)
        mode = ModernComboBox()
        mode.addItems(["Balanced", "Performance", "Quiet"])
        form.addRow("Mode", mode)
        notifications = ModernSwitch("Enable notifications")
        notifications.setChecked(True)
        form.addRow(notifications)
        appearance = ModernComboBox()
        for theme_mode in ThemeMode:
            appearance.addItem(theme_mode.value.title(), theme_mode)
        appearance.setCurrentIndex(appearance.findData(theme_manager().mode()))
        appearance.activated.connect(
            lambda _index: theme_manager().setMode(appearance.currentData())
        )
        form.addRow("Appearance", appearance)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(
            lambda: status.setText(f"{name.text() or 'Workspace'}: {mode.currentText()}")
        )
        apply_button.clicked.connect(self.flyout.close)
        form.addRow(apply_button)
        self.flyout.setContentWidget(content)

        buttons = QHBoxLayout()
        for placement in FlyoutPlacement:
            button = QPushButton(placement.value.title())
            button.clicked.connect(
                lambda _checked=False, anchor=button, side=placement: self.flyout.popup(
                    anchor, side
                )
            )
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)
        layout.addWidget(status)

        self.long_flyout = ModernFlyout(self)
        long_content = QWidget()
        long_layout = QVBoxLayout(long_content)
        for index in range(40):
            long_layout.addWidget(ModernSwitch(f"Option {index + 1}"))
        self.long_flyout.setContentWidget(long_content)
        long_button = QPushButton("Open scrollable panel")
        long_button.clicked.connect(lambda: self.long_flyout.popup(long_button))
        layout.addWidget(long_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return page

    def _create_notification_page(self) -> QWidget:
        page, layout = self._create_page("Notifications")
        description = QLabel(
            "Show a quiet update without interrupting your work. Hover to keep a notification "
            "open, or dismiss it to make room for the next one."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addLayout(self._create_appearance_controls())
        desktop_manager = NotificationManager(self)
        page_manager = NotificationManager(page, desktop=False)
        self.notification_managers = (desktop_manager, page_manager)

        options = QFormLayout()
        delivery = ModernComboBox()
        delivery.addItems(
            [
                "Desktop" if desktop_manager.isDesktop() else "Window (automatic)",
                "Inside this page",
            ]
        )
        placement = ModernComboBox()
        for position in NotificationPosition:
            placement.addItem(position.value.replace("-", " ").title(), position)
        placement.setCurrentIndex(3)
        screens = ModernComboBox()
        screens.addItem("Follow this window", None)
        for screen in QApplication.screens():
            screens.addItem(screen.name(), screen)
        options.addRow("Show on", delivery)
        options.addRow("Corner", placement)
        options.addRow("Screen", screens)
        layout.addLayout(options)

        def current_manager() -> NotificationManager:
            return self.notification_managers[delivery.currentIndex()]

        placement.currentIndexChanged.connect(
            lambda _index: [
                manager.setPosition(placement.currentData())
                for manager in self.notification_managers
            ]
        )
        screens.currentIndexChanged.connect(
            lambda _index: desktop_manager.setScreen(screens.currentData())
        )
        paused = ModernSwitch("Pause notifications")
        paused.toggled.connect(
            lambda checked: [
                manager.setEnabled(not checked) for manager in self.notification_managers
            ]
        )
        layout.addWidget(paused)
        status = QLabel()
        status.setWordWrap(True)

        def update_counts(*_args) -> None:
            manager = current_manager()
            status.setText(
                f"{len(manager.visibleIds())} showing · {len(manager.queuedIds())} waiting"
            )

        activity = QLabel("Action results appear here.")
        activity.setWordWrap(True)
        for manager in self.notification_managers:
            manager.countChanged.connect(update_counts)
            manager.actionTriggered.connect(
                lambda _key, action: activity.setText(f"Action: {action}")
            )
            manager.notificationActivated.connect(
                lambda _key: activity.setText("Notification selected.")
            )
        delivery.currentIndexChanged.connect(update_counts)
        delivery.currentIndexChanged.connect(lambda index: screens.setEnabled(index == 0))
        update_counts()

        examples = (
            (
                "Information",
                NotificationKind.INFO,
                "A new version is available",
                "You can install it when you are ready.",
            ),
            (
                "Success",
                NotificationKind.SUCCESS,
                "Export complete",
                "Your report is ready to open.",
            ),
            (
                "Warning",
                NotificationKind.WARNING,
                "Connection interrupted",
                "Your changes are saved. We will retry shortly.",
            ),
            (
                "Error",
                NotificationKind.ERROR,
                "Upload failed",
                "Check your connection and try again.",
            ),
        )
        buttons = QHBoxLayout()
        for text, kind, title, message in examples:
            button = QPushButton(text)
            button.clicked.connect(
                lambda _checked=False, kind=kind, title=title, message=message: (
                    current_manager().notify(
                        title,
                        message,
                        kind=kind,
                        actions={"open": "View details"},
                    )
                )
            )
            buttons.addWidget(button)
        layout.addLayout(buttons)

        more = QHBoxLayout()
        burst = QPushButton("Queue 8 updates")
        burst.clicked.connect(
            lambda: [
                current_manager().notify(
                    f"Task {i + 1} complete", "The next update appears when there is room."
                )
                for i in range(8)
            ]
        )
        persistent = QPushButton("Keep until dismissed")
        persistent.clicked.connect(
            lambda: current_manager().notify(
                "Waiting for your review",
                "This notification stays until you dismiss it.",
                duration=0,
                actions={"review": "Review"},
            )
        )
        long_text = QPushButton("Long message")
        long_text.clicked.connect(
            lambda: current_manager().notify(
                "Import summary",
                "Imported records successfully. Review the following details.\n\n" * 25,
                duration=0,
                actions={"done": "Done"},
            )
        )
        for button in (burst, persistent, long_text):
            more.addWidget(button)
        layout.addLayout(more)

        progress_timer = QTimer(self)
        progress_timer.setInterval(120)
        progress_state: dict = {}

        def advance_download() -> None:
            manager, key = progress_state["manager"], progress_state["key"]
            if manager.notification(key) is None:
                progress_timer.stop()
                return
            progress_state["value"] += 2
            value = progress_state["value"]
            if value >= 100:
                progress_timer.stop()
                manager.updateNotification(
                    key,
                    title="Download complete",
                    message="Your file is ready.",
                    kind=NotificationKind.SUCCESS,
                    progress=None,
                    actions={"open": "Open file"},
                    duration=5000,
                )
            else:
                manager.updateNotification(key, message=f"Downloading… {value}%", progress=value)

        def start_download() -> None:
            if progress_state:
                progress_state["manager"].dismiss(progress_state["key"])
            manager = current_manager()
            key = manager.notify(
                "Downloading", "Starting…", duration=0, progress=0, actions={"cancel": "Cancel"}
            )
            progress_state.update(manager=manager, key=key, value=0)
            progress_timer.start()

        progress_timer.timeout.connect(advance_download)
        bottom = QHBoxLayout()
        progress = QPushButton("Simulate download")
        progress.clicked.connect(start_download)
        minimized = QPushButton("Notify after minimizing")
        minimized.setEnabled(desktop_manager.isDesktop())

        def notify_minimized() -> None:
            self.showMinimized()
            QTimer.singleShot(
                700,
                lambda: desktop_manager.notify(
                    "Background task complete",
                    "Notifications remain available while the window is minimized.",
                    kind=NotificationKind.SUCCESS,
                ),
            )

        minimized.clicked.connect(notify_minimized)
        clear = QPushButton("Clear all")
        clear.clicked.connect(lambda: [manager.clear() for manager in self.notification_managers])
        for button in (progress, minimized, clear):
            bottom.addWidget(button)
        layout.addLayout(bottom)
        layout.addWidget(status)
        layout.addWidget(activity)
        layout.addStretch()
        return page

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        if event.isAccepted():
            for manager in self.notification_managers:
                manager.clear()

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

    def _create_toolbar_page(self) -> QWidget:
        page, layout = self._create_page("Toolbars")
        hint = QLabel(
            "Compare the same actions in native and modern toolbars. "
            "Narrow both to compare overflow, or hover and click to compare button states."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addLayout(self._create_appearance_controls())
        comparison = QGridLayout()
        comparison.setHorizontalSpacing(24)
        comparison.setVerticalSpacing(8)
        layout.addLayout(comparison)
        status = QLabel("Choose an action")
        status.setWordWrap(True)
        toolbars = []
        for column, (label, toolbar_type, menu_type) in enumerate(
            (("Native QToolBar", QToolBar, QMenu), ("ModernToolBar", ModernToolBar, ModernMenu))
        ):
            comparison.addWidget(QLabel(label), 0, column)
            toolbar = toolbar_type("Editing", page)
            toolbar.setMovable(False)
            toolbar.setFloatable(False)
            toolbar.setIconSize(QSize(18, 18))
            toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            toolbar.setFixedWidth(260)
            for text, icon in (
                ("Open", QStyle.StandardPixmap.SP_DialogOpenButton),
                ("Save", QStyle.StandardPixmap.SP_DialogSaveButton),
                ("Back", QStyle.StandardPixmap.SP_ArrowBack),
                ("Forward", QStyle.StandardPixmap.SP_ArrowForward),
            ):
                toolbar.addAction(standard_icon(icon), text)
            toolbar.addSeparator()
            toggle = toolbar.addAction(
                standard_icon(QStyle.StandardPixmap.SP_FileDialogListView), "Panel"
            )
            toggle.setCheckable(True)
            toggle.setChecked(True)
            toolbar.addAction(
                standard_icon(QStyle.StandardPixmap.SP_DialogCancelButton), "Unavailable"
            ).setEnabled(False)
            more = menu_type("More", page)
            more.addAction("Details")
            more.setIcon(standard_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
            toolbar.addAction(more.menuAction())
            toolbar.actionTriggered.connect(
                lambda action, label=label: status.setText(f"{label}: {action.text()}")
            )
            more.triggered.connect(
                lambda action, label=label: status.setText(f"{label}: {action.text()}")
            )
            comparison.addWidget(toolbar, 1, column, Qt.AlignmentFlag.AlignLeft)
            comparison.setColumnMinimumWidth(column, 320)
            comparison.setColumnStretch(column, 1)
            toolbars.append(toolbar)
        width_label = QLabel("Width of each toolbar: 260 px")
        layout.addWidget(width_label)
        width = QSlider(Qt.Orientation.Horizontal)
        width.setRange(100, 320)
        width.setValue(260)
        width.valueChanged.connect(
            lambda value: width_label.setText(f"Width of each toolbar: {value} px")
        )
        layout.addWidget(width)
        text = QCheckBox("Show text beside icons")
        layout.addWidget(text)
        rtl = QCheckBox("Right-to-left layout")
        for toolbar in toolbars:
            width.valueChanged.connect(toolbar.setFixedWidth)
            text.toggled.connect(
                lambda checked, toolbar=toolbar: toolbar.setToolButtonStyle(
                    Qt.ToolButtonStyle.ToolButtonTextBesideIcon
                    if checked
                    else Qt.ToolButtonStyle.ToolButtonIconOnly
                )
            )
            rtl.toggled.connect(
                lambda checked, toolbar=toolbar: toolbar.setLayoutDirection(
                    Qt.LayoutDirection.RightToLeft if checked else Qt.LayoutDirection.LeftToRight
                )
            )
        layout.addWidget(rtl)
        layout.addWidget(status)
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
