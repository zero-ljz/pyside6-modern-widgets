"""Interactive gallery for modern windows, navigation, menus, dialogs, and controls."""

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, QDate, QDateTime, QSize, Qt, QTime, QTimer
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFontComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QStyle,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pyside6_modern_widgets import (
    FlyoutPlacement,
    ModernCheckBox,
    ModernComboBox,
    ModernDateEdit,
    ModernDateTimeEdit,
    ModernDialog,
    ModernDoubleSpinBox,
    ModernFlyout,
    ModernFontComboBox,
    ModernKeySequenceEdit,
    ModernLineEdit,
    ModernMenu,
    ModernMenuBar,
    ModernMessageBox,
    ModernPlainTextEdit,
    ModernPushButton,
    ModernRadioButton,
    ModernScrollBar,
    ModernSegmentedControl,
    ModernSlider,
    ModernSpinBox,
    ModernSwitch,
    ModernTabWidget,
    ModernTextEdit,
    ModernTimeEdit,
    ModernToolBar,
    ModernToolButton,
    ModernToolTip,
    ModernWindow,
    NavigationPosition,
    NavigationView,
    NotificationAction,
    NotificationKind,
    NotificationManager,
    NotificationPosition,
    NotificationState,
    ThemeMode,
    theme_manager,
)

if __package__:
    from ._example_i18n import example_locale, install_translators
    from .edge_dock_example import EdgeDockExample
else:
    from _example_i18n import example_locale, install_translators
    from edge_dock_example import EdgeDockExample


def standard_icon(name: QStyle.StandardPixmap) -> QIcon:
    return QApplication.style().standardIcon(name)


class ExampleWindow(ModernWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(self.tr("Modern Widgets Example"))
        self.setTitleVisible(True)
        self.setTitleAlignment("center")
        self.setWindowIcon(QIcon(":/pyside6_modern_widgets/icons/application.png"))
        self.resize(1000, 640)
        self.edge_dock_example: EdgeDockExample | None = None

        self.navigation = NavigationView()
        self.setCentralWidget(self.navigation)
        native_group = self.tr("PySide6 built-in widgets")
        custom_group = self.tr("Custom widgets")

        self.navigation.addPage(
            self._create_home_page(),
            self.tr("Home"),
            standard_icon(QStyle.StandardPixmap.SP_DesktopIcon),
            selected=True,
        )
        self.navigation.addPage(
            self._create_dialog_page(),
            self.tr("Dialog"),
            standard_icon(QStyle.StandardPixmap.SP_DialogApplyButton),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_message_box_page(),
            self.tr("Message boxes"),
            standard_icon(QStyle.StandardPixmap.SP_MessageBoxInformation),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_menu_page(),
            self.tr("Menu"),
            standard_icon(QStyle.StandardPixmap.SP_FileDialogListView),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_toolbar_page(),
            self.tr("Toolbar"),
            standard_icon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_tab_widget_page(),
            self.tr("Tab widget"),
            standard_icon(QStyle.StandardPixmap.SP_FileDialogListView),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_button_page(),
            self.tr("Buttons"),
            standard_icon(QStyle.StandardPixmap.SP_DialogOkButton),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_tool_button_page(),
            self.tr("Tool buttons"),
            standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_choice_page(),
            self.tr("Choice controls"),
            standard_icon(QStyle.StandardPixmap.SP_DialogYesButton),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_combo_box_page(),
            self.tr("Combo box"),
            standard_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_line_edit_page(),
            self.tr("Line edit"),
            standard_icon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_spin_editors_page(),
            self.tr("Spin editors"),
            standard_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_more_inputs_page(),
            self.tr("More inputs"),
            standard_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
            group=native_group,
        )
        self.navigation.addPage(
            self._create_switch_page(),
            self.tr("Switch"),
            standard_icon(QStyle.StandardPixmap.SP_DialogYesButton),
            group=custom_group,
        )
        self.navigation.addPage(
            self._create_scroll_bar_page(),
            self.tr("Scroll bars"),
            standard_icon(QStyle.StandardPixmap.SP_FileDialogListView),
            group=custom_group,
        )
        self.navigation.addPage(
            self._create_flyout_page(),
            self.tr("Flyout"),
            standard_icon(QStyle.StandardPixmap.SP_TitleBarShadeButton),
            group=custom_group,
        )
        self.navigation.addPage(
            self._create_tooltip_page(),
            self.tr("Tooltips"),
            standard_icon(QStyle.StandardPixmap.SP_MessageBoxInformation),
            group=custom_group,
        )
        self.navigation.addPage(
            self._create_notification_page(),
            self.tr("Notifications"),
            standard_icon(QStyle.StandardPixmap.SP_MessageBoxInformation),
            group=custom_group,
        )
        self.navigation.addPage(
            self._create_edge_dock_page(),
            self.tr("Edge docking"),
            standard_icon(QStyle.StandardPixmap.SP_TitleBarNormalButton),
            group=custom_group,
        )
        self.navigation.addPage(
            self._create_settings_page(),
            self.tr("Settings"),
            QIcon(":/pyside6_modern_widgets/icons/settings.png"),
            position=NavigationPosition.BOTTOM,
        )

        self._create_actions()
        self._create_menu_bar()

    def _create_tool_button_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("Tool buttons"))
        hint = QLabel(
            self.tr(
                "Compare tool button layouts and states. In Menus, try a short click, "
                "a long press, or the separate menu arrow. Tab and Space use native keyboard behavior."
            )
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        tabs = ModernTabWidget(page)
        layout.addWidget(tabs)
        status = QLabel(self.tr("Choose an action"))
        status.setWordWrap(True)
        panels = []
        groups = (
            (
                self.tr("Styles and states"),
                (
                    ("icon", self.tr("Icon only")),
                    ("text", self.tr("Text only")),
                    ("beside", self.tr("Text beside icon")),
                    ("under", self.tr("Text under icon")),
                    ("follow", self.tr("Follow style")),
                    ("auto_raise", self.tr("Auto raise")),
                    ("checked", self.tr("Checkable button")),
                    ("arrow", self.tr("Arrow button")),
                    ("disabled", self.tr("Unavailable")),
                ),
            ),
            (
                self.tr("Menus"),
                (
                    ("delayed", "DelayedPopup"),
                    ("split", "MenuButtonPopup"),
                    ("instant", "InstantPopup"),
                ),
            ),
        )
        for title, rows in groups:
            panel = QWidget(tabs)
            panels.append(panel)
            grid = QGridLayout(panel)
            grid.setContentsMargins(12, 12, 12, 12)
            grid.setHorizontalSpacing(24)
            grid.setVerticalSpacing(8)
            for row, (_kind, label) in enumerate(rows, 1):
                grid.addWidget(QLabel(label), row, 0)
            for column, (heading, button_type, menu_type) in enumerate(
                (
                    (self.tr("Native QToolButton"), QToolButton, QMenu),
                    ("ModernToolButton", ModernToolButton, ModernMenu),
                ),
                1,
            ):
                grid.addWidget(QLabel(heading), 0, column)
                grid.setColumnStretch(column, 1)
                for row, (kind, _label) in enumerate(rows, 1):
                    button = button_type(panel)
                    action = QAction(
                        standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton),
                        self.tr("Open"),
                        button,
                    )
                    button.setDefaultAction(action)
                    button.setToolButtonStyle(
                        {
                            "text": Qt.ToolButtonStyle.ToolButtonTextOnly,
                            "beside": Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
                            "under": Qt.ToolButtonStyle.ToolButtonTextUnderIcon,
                            "follow": Qt.ToolButtonStyle.ToolButtonFollowStyle,
                        }.get(kind, Qt.ToolButtonStyle.ToolButtonIconOnly)
                    )
                    button.setAutoRaise(kind == "auto_raise")
                    if kind == "checked":
                        action.setCheckable(True)
                        action.setChecked(True)
                    elif kind == "disabled":
                        action.setEnabled(False)
                    elif kind == "arrow":
                        button.setArrowType(Qt.ArrowType.DownArrow)
                    elif kind in ("delayed", "split", "instant"):
                        menu = menu_type(button)
                        menu.addAction(self.tr("Details"))
                        menu.addAction(self.tr("Unavailable")).setEnabled(False)
                        button.setMenu(menu)
                        button.setPopupMode(
                            {
                                "delayed": QToolButton.ToolButtonPopupMode.DelayedPopup,
                                "split": QToolButton.ToolButtonPopupMode.MenuButtonPopup,
                                "instant": QToolButton.ToolButtonPopupMode.InstantPopup,
                            }[kind]
                        )
                    button.triggered.connect(
                        lambda action, heading=heading: status.setText(
                            self.tr("%1: %2").replace("%1", heading).replace("%2", action.text())
                        )
                    )
                    grid.addWidget(button, row, column, Qt.AlignmentFlag.AlignLeft)
            grid.setRowStretch(len(rows) + 1, 1)
            tabs.addTab(panel, title)

        arrows = QWidget(tabs)
        panels.append(arrows)
        arrow_grid = QGridLayout(arrows)
        arrow_grid.setContentsMargins(12, 12, 12, 12)
        arrow_grid.setHorizontalSpacing(20)
        arrow_grid.setVerticalSpacing(12)
        directions = (
            (self.tr("Up"), Qt.ArrowType.UpArrow),
            (self.tr("Down"), Qt.ArrowType.DownArrow),
            (self.tr("Left"), Qt.ArrowType.LeftArrow),
            (self.tr("Right"), Qt.ArrowType.RightArrow),
        )
        for column, (label, _arrow) in enumerate(directions, 2):
            arrow_grid.addWidget(QLabel(label), 0, column, Qt.AlignmentFlag.AlignHCenter)
            arrow_grid.setColumnStretch(column, 1)
        for state_index, (kind, label) in enumerate(
            (
                ("normal", self.tr("Normal")),
                ("checked", self.tr("Checked")),
                ("disabled", self.tr("Disabled")),
            )
        ):
            row = state_index * 2 + 1
            arrow_grid.addWidget(QLabel(label), row, 0, 2, 1)
            for offset, (heading, button_type) in enumerate(
                (
                    (self.tr("Native QToolButton"), QToolButton),
                    ("ModernToolButton", ModernToolButton),
                )
            ):
                arrow_grid.addWidget(QLabel(heading), row + offset, 1)
                for column, (direction, arrow) in enumerate(directions, 2):
                    button = button_type(arrows)
                    action = QAction(direction, button)
                    action.setCheckable(kind == "checked")
                    action.setChecked(kind == "checked")
                    action.setEnabled(kind != "disabled")
                    button.setDefaultAction(action)
                    button.setArrowType(arrow)
                    button.setAccessibleName(direction)
                    button.triggered.connect(
                        lambda action, heading=heading: status.setText(
                            self.tr("%1: %2").replace("%1", heading).replace("%2", action.text())
                        )
                    )
                    arrow_grid.addWidget(
                        button, row + offset, column, Qt.AlignmentFlag.AlignHCenter
                    )
        arrow_grid.setRowStretch(7, 1)
        tabs.insertTab(1, arrows, self.tr("Arrows"))
        rtl = QCheckBox(self.tr("Right-to-left layout"))
        for panel in panels:
            rtl.toggled.connect(
                lambda checked, panel=panel: panel.setLayoutDirection(
                    Qt.LayoutDirection.RightToLeft if checked else Qt.LayoutDirection.LeftToRight
                )
            )
        layout.addWidget(rtl)
        layout.addWidget(status)
        return page

    def _create_button_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("Buttons"))
        hint = QLabel(
            self.tr(
                "Compare native and modern buttons. Use Tab and Space to try keyboard focus, "
                "or hover and press to compare states."
            )
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        panel = QWidget(page)
        comparison = QGridLayout(panel)
        comparison.setContentsMargins(0, 0, 0, 0)
        comparison.setHorizontalSpacing(24)
        comparison.setVerticalSpacing(10)
        layout.addWidget(panel)
        status = QLabel(self.tr("Choose an action"))
        status.setWordWrap(True)
        for column, (heading, button_type, menu_type) in enumerate(
            (
                (self.tr("Native QPushButton"), QPushButton, QMenu),
                ("ModernPushButton", ModernPushButton, ModernMenu),
            )
        ):
            comparison.addWidget(QLabel(heading), 0, column)
            comparison.setColumnStretch(column, 1)
            for row, (kind, text) in enumerate(
                (
                    ("normal", self.tr("&Save")),
                    ("icon", self.tr("Open")),
                    ("icon_only", ""),
                    ("checked", self.tr("Checkable button")),
                    ("default", self.tr("Default button")),
                    ("flat", self.tr("Flat button")),
                    ("menu", self.tr("More actions")),
                    ("disabled", self.tr("Unavailable")),
                ),
                start=1,
            ):
                button = button_type(text, panel)
                if kind in ("icon", "icon_only"):
                    button.setIcon(standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton))
                if kind == "icon_only":
                    button.setToolTip(self.tr("Open"))
                    button.setAccessibleName(self.tr("Open"))
                elif kind == "checked":
                    button.setCheckable(True)
                    button.setChecked(True)
                elif kind == "default":
                    button.setDefault(True)
                elif kind == "flat":
                    button.setFlat(True)
                elif kind == "disabled":
                    button.setEnabled(False)
                elif kind == "menu":
                    menu = menu_type(button)
                    menu.addAction(self.tr("Open"))
                    menu.addAction(self.tr("Details"))
                    menu.triggered.connect(
                        lambda action, heading=heading: status.setText(
                            self.tr("%1: %2").replace("%1", heading).replace("%2", action.text())
                        )
                    )
                    button.setMenu(menu)
                button.clicked.connect(
                    lambda checked=False, button=button, heading=heading: status.setText(
                        self.tr("%1: %2")
                        .replace("%1", heading)
                        .replace("%2", button.text() or button.accessibleName())
                        + (f" ({checked})" if button.isCheckable() else "")
                    )
                )
                comparison.addWidget(button, row, column, Qt.AlignmentFlag.AlignLeft)
        rtl = QCheckBox(self.tr("Right-to-left layout"))
        rtl.toggled.connect(
            lambda checked: panel.setLayoutDirection(
                Qt.LayoutDirection.RightToLeft if checked else Qt.LayoutDirection.LeftToRight
            )
        )
        layout.addWidget(rtl)
        layout.addWidget(status)
        layout.addStretch()
        return page

    def _create_choice_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("Choice controls"))
        checks = QGridLayout()
        checks.setHorizontalSpacing(32)
        checks.setVerticalSpacing(10)
        for column, (heading, widget_type) in enumerate(
            (("QCheckBox", QCheckBox), ("ModernCheckBox", ModernCheckBox))
        ):
            checks.addWidget(QLabel(heading), 0, column)
            for row, text in enumerate(
                (
                    self.tr("General"),
                    self.tr("Details"),
                    self.tr("Partially checked"),
                    self.tr("Disabled"),
                    self.tr("Right to left"),
                ),
                start=1,
            ):
                check = widget_type(text, page)
                if row == 2 or row >= 4:
                    check.setChecked(True)
                if row == 3:
                    check.setTristate(True)
                    check.setCheckState(Qt.CheckState.PartiallyChecked)
                if row == 4:
                    check.setEnabled(False)
                if row == 5:
                    check.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                checks.addWidget(check, row, column, Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(checks)

        radios = QGridLayout()
        radios.setHorizontalSpacing(32)
        radios.setVerticalSpacing(10)
        for column, (heading, widget_type) in enumerate(
            (("QRadioButton", QRadioButton), ("ModernRadioButton", ModernRadioButton))
        ):
            radios.addWidget(QLabel(heading), 0, column)
            group = QButtonGroup(page)
            for row, text in enumerate(
                (self.tr("General"), self.tr("Details"), self.tr("Disabled")), start=1
            ):
                radio = widget_type(text, page)
                group.addButton(radio)
                if row == 2:
                    radio.setChecked(True)
                if row == 3:
                    radio.setEnabled(False)
                radios.addWidget(radio, row, column, Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(radios)
        layout.addStretch()
        return page

    def _create_tooltip_page(self) -> QWidget:
        page, layout = self._create_page("ModernToolTip")
        description = QLabel(
            self.tr("Hover over the buttons, then move between them to compare delays.")
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        row = QHBoxLayout()
        for title, text in (
            (self.tr("Short tip"), self.tr("Save your changes")),
            (
                self.tr("Long tip"),
                self.tr(
                    "Long tooltips wrap automatically and stay within the screen. Move the window near an edge to try it."
                ),
            ),
            (
                self.tr("Formatted tip"),
                self.tr("<b>Quick help</b><br>Tooltips follow the owner's theme."),
            ),
        ):
            button = QPushButton(title)
            button.setToolTip(text)
            row.addWidget(button)
        layout.addLayout(row)
        form = QFormLayout()
        first = ModernSlider(Qt.Orientation.Horizontal)
        first.setRange(0, 1000)
        first.setValue(300)
        repeat = ModernSlider(Qt.Orientation.Horizontal)
        repeat.setRange(0, 500)
        repeat.setValue(100)
        form.addRow(self.tr("First delay (ms)"), first)
        form.addRow(self.tr("Repeat delay (ms)"), repeat)
        layout.addLayout(form)
        status = QLabel()
        layout.addWidget(status)

        def update_delays() -> None:
            ModernToolTip.install(delay_ms=first.value(), reshow_delay_ms=repeat.value())
            status.setText(f"{first.value()} ms / {repeat.value()} ms")

        first.valueChanged.connect(update_delays)
        repeat.valueChanged.connect(update_delays)
        status.setText("300 ms / 100 ms")
        layout.addStretch()
        return page

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
        page, layout = self._create_page(self.tr("Modern Widgets"))
        description = QLabel(
            self.tr(
                "Modern windows, navigation, menus, dialogs, controls, flyouts, and desktop notifications."
            )
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addStretch()
        return page

    def _create_scroll_bar_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("Scroll bars"))
        scroll = QScrollArea(page)
        scroll.setObjectName("ScrollBarExampleArea")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea#ScrollBarExampleArea, "
            "QScrollArea#ScrollBarExampleArea > QWidget, "
            "QWidget#ScrollBarExampleContent { background: transparent; border: none; }"
        )
        scroll.setWidgetResizable(False)
        scroll.setFixedHeight(250)
        scroll.setVerticalScrollBar(ModernScrollBar(Qt.Orientation.Vertical))
        scroll.setHorizontalScrollBar(ModernScrollBar(Qt.Orientation.Horizontal))
        scroll.setCornerWidget(QWidget(scroll))
        content = QWidget()
        content.setObjectName("ScrollBarExampleContent")
        content.setFixedSize(1100, 720)
        content_layout = QVBoxLayout(content)
        for index in range(24):
            row = QWidget(content)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(QLabel(self.tr("Document %1").replace("%1", str(index + 1))))
            row_layout.addStretch()
            row_layout.addWidget(QLabel(self.tr("Ready")))
            content_layout.addWidget(row)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        rtl = QCheckBox(self.tr("Right-to-left layout"))
        rtl.toggled.connect(
            lambda checked: scroll.setLayoutDirection(
                Qt.LayoutDirection.RightToLeft if checked else Qt.LayoutDirection.LeftToRight
            )
        )
        layout.addWidget(rtl)
        layout.addStretch()
        return page

    def _create_edge_dock_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("Edge docking"))
        description = QLabel(
            self.tr(
                "Open a floating tool and its controls to try screen-edge docking. "
                "Drag between displays, hide and restore the tool, replace its drag strip, "
                "or detach and reattach docking."
            )
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        launch = QPushButton(self.tr("Open edge-docking demo"))
        launch.clicked.connect(self._show_edge_dock_example)
        layout.addWidget(launch, 0, Qt.AlignmentFlag.AlignLeft)
        note = QLabel(self.tr("Opening again reuses the same demo and restores the floating tool."))
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        return page

    def _show_edge_dock_example(self) -> None:
        if self.edge_dock_example is None:
            self.edge_dock_example = EdgeDockExample(self)
        self.edge_dock_example.showNormal()
        self.edge_dock_example.raise_()
        self.edge_dock_example.activateWindow()
        self.edge_dock_example.show_floating()

    def _create_dialog_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("Dialog"))
        comparison = QGridLayout()
        comparison.setHorizontalSpacing(24)
        for column, (heading, dialog_type) in enumerate(
            (("QDialog", QDialog), ("ModernDialog", ModernDialog))
        ):
            comparison.addWidget(QLabel(heading), 0, column)
            comparison.setColumnStretch(column, 1)
            open_button = QPushButton(
                standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton),
                self.tr("Open dialog"),
            )
            open_button.setFixedWidth(220)
            open_button.clicked.connect(
                lambda _checked=False, widget_type=dialog_type: self._show_dialog(widget_type)
            )
            comparison.addWidget(open_button, 1, column, Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(comparison)
        layout.addStretch()
        return page

    def _create_flyout_page(self) -> QWidget:
        page, layout = self._create_page("ModernFlyout")
        description = QLabel(
            self.tr(
                "Open quick settings beside a button. Click outside or press Escape to close. "
                "Move the window near a screen edge to try automatic placement."
            )
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        status = QLabel(self.tr("Settings are kept when the panel closes."))
        status.setWordWrap(True)

        self.flyout = ModernFlyout(self)
        self.flyout.setAccessibleName(self.tr("Quick settings"))
        content = QWidget()
        content.setMinimumWidth(280)
        form = QFormLayout(content)
        form.setContentsMargins(4, 4, 4, 4)
        heading = QLabel(self.tr("Quick settings"))
        font = heading.font()
        font.setBold(True)
        heading.setFont(font)
        form.addRow(heading)
        name = QLineEdit()
        name.setPlaceholderText(self.tr("Workspace name"))
        form.addRow(self.tr("Name"), name)
        mode = ModernComboBox()
        mode.addItems([self.tr("Balanced"), self.tr("Performance"), self.tr("Quiet")])
        form.addRow(self.tr("Mode"), mode)
        notifications = ModernSwitch(self.tr("Enable notifications"))
        notifications.setChecked(True)
        form.addRow(notifications)
        appearance = ModernComboBox()
        for label, theme_mode in (
            (self.tr("System"), ThemeMode.SYSTEM),
            (self.tr("Light"), ThemeMode.LIGHT),
            (self.tr("Dark"), ThemeMode.DARK),
        ):
            appearance.addItem(label, theme_mode)
        appearance.setCurrentIndex(appearance.findData(theme_manager().mode()))
        appearance.activated.connect(
            lambda _index: theme_manager().setMode(appearance.currentData())
        )
        form.addRow(self.tr("Appearance"), appearance)
        apply_button = QPushButton(self.tr("Apply"))
        apply_button.clicked.connect(
            lambda: status.setText(
                self.tr("%1: %2")
                .replace("%1", name.text() or self.tr("Workspace"))
                .replace("%2", mode.currentText())
            )
        )
        apply_button.clicked.connect(self.flyout.close)
        form.addRow(apply_button)
        self.flyout.setContentWidget(content)

        buttons = QHBoxLayout()
        for label, placement in (
            (self.tr("Top"), FlyoutPlacement.TOP),
            (self.tr("Right"), FlyoutPlacement.RIGHT),
            (self.tr("Bottom"), FlyoutPlacement.BOTTOM),
            (self.tr("Left"), FlyoutPlacement.LEFT),
        ):
            button = QPushButton(label)
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
            long_layout.addWidget(ModernSwitch(self.tr("Option %1").replace("%1", str(index + 1))))
        self.long_flyout.setContentWidget(long_content)
        long_button = QPushButton(self.tr("Open scrollable panel"))
        long_button.clicked.connect(lambda: self.long_flyout.popup(long_button))
        layout.addWidget(long_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return page

    def _create_notification_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("Notifications"))
        description = QLabel(
            self.tr(
                "Show a quiet update without interrupting your work. Hover to keep a notification "
                "open, or dismiss it to make room for the next one."
            )
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        desktop_manager = NotificationManager(self)
        page_manager = NotificationManager(page, desktop=False)
        self.notification_managers = (desktop_manager, page_manager)

        options = QFormLayout()
        delivery = ModernComboBox()
        delivery.addItems(
            [
                self.tr("Desktop")
                if desktop_manager.isDesktop()
                else self.tr("Window (automatic)"),
                self.tr("Inside this page"),
            ]
        )
        placement = ModernComboBox()
        for label, position in (
            (self.tr("Top left"), NotificationPosition.TOP_LEFT),
            (self.tr("Top right"), NotificationPosition.TOP_RIGHT),
            (self.tr("Bottom left"), NotificationPosition.BOTTOM_LEFT),
            (self.tr("Bottom right"), NotificationPosition.BOTTOM_RIGHT),
        ):
            placement.addItem(label, position)
        placement.setCurrentIndex(3)
        screens = ModernComboBox()
        screens.addItem(self.tr("Follow this window"), None)
        for screen in QApplication.screens():
            screens.addItem(screen.name(), screen)
        options.addRow(self.tr("Show on"), delivery)
        options.addRow(self.tr("Corner"), placement)
        options.addRow(self.tr("Screen"), screens)
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
        paused = ModernSwitch(self.tr("Pause notifications"))
        paused.toggled.connect(
            lambda checked: [
                manager.setDeliveryPaused(checked) for manager in self.notification_managers
            ]
        )
        layout.addWidget(paused)
        status = QLabel()
        status.setWordWrap(True)

        def update_counts(*_args) -> None:
            manager = current_manager()
            visible = len(manager.notifications(NotificationState.VISIBLE))
            status.setText(
                self.tr("%1 showing · %2 waiting")
                .replace("%1", str(visible))
                .replace("%2", str(len(manager.notifications()) - visible))
            )

        activity = QLabel(self.tr("Action results appear here."))
        activity.setWordWrap(True)

        def notify(title, message="", *, manager=None, **options):
            manager = manager if manager is not None else current_manager()
            try:
                return manager.notify(title, message, **options)
            except OverflowError:
                activity.setText(self.tr("Dismiss a notification before showing another."))
                return None

        for manager in self.notification_managers:
            manager.countChanged.connect(update_counts)
            manager.actionTriggered.connect(
                lambda _key, action: activity.setText(self.tr("Action: %1").replace("%1", action))
            )
            manager.notificationActivated.connect(
                lambda _key: activity.setText(self.tr("Notification selected."))
            )
        delivery.currentIndexChanged.connect(update_counts)
        delivery.currentIndexChanged.connect(lambda index: screens.setEnabled(index == 0))
        update_counts()

        examples = (
            (
                self.tr("Information"),
                NotificationKind.INFO,
                self.tr("A new version is available"),
                self.tr("You can install it when you are ready."),
            ),
            (
                self.tr("Success"),
                NotificationKind.SUCCESS,
                self.tr("Export complete"),
                self.tr("Your report is ready to open."),
            ),
            (
                self.tr("Warning"),
                NotificationKind.WARNING,
                self.tr("Connection interrupted"),
                self.tr("Your changes are saved. We will retry shortly."),
            ),
            (
                self.tr("Error"),
                NotificationKind.ERROR,
                self.tr("Upload failed"),
                self.tr("Check your connection and try again."),
            ),
        )
        buttons = QHBoxLayout()
        for text, kind, title, message in examples:
            button = QPushButton(text)
            button.clicked.connect(
                lambda _checked=False, kind=kind, title=title, message=message: notify(
                    title,
                    message,
                    kind=kind,
                    actions=[NotificationAction("open", self.tr("View details"))],
                )
            )
            buttons.addWidget(button)
        layout.addLayout(buttons)

        more = QHBoxLayout()
        burst = QPushButton(self.tr("Queue 8 updates"))
        burst.clicked.connect(
            lambda: [
                notify(
                    self.tr("Task %1 complete").replace("%1", str(i + 1)),
                    self.tr("The next update appears when there is room."),
                )
                for i in range(8)
            ]
        )
        persistent = QPushButton(self.tr("Keep until dismissed"))
        persistent.clicked.connect(
            lambda: notify(
                self.tr("Waiting for your review"),
                self.tr("This notification stays until you dismiss it."),
                timeout_ms=None,
                actions=[NotificationAction("review", self.tr("Review"))],
            )
        )
        long_text = QPushButton(self.tr("Long message"))
        long_text.clicked.connect(
            lambda: notify(
                self.tr("Import summary"),
                self.tr("Imported records successfully. Review the following details.\n\n") * 25,
                timeout_ms=None,
                actions=[NotificationAction("done", self.tr("Done"))],
            )
        )
        for button in (burst, persistent, long_text):
            more.addWidget(button)
        layout.addLayout(more)

        progress_timer = QTimer(self)
        progress_timer.setInterval(120)
        progress_state: dict = {}

        def advance_download() -> None:
            job = progress_state["handle"]
            if job.isClosed():
                progress_timer.stop()
                return
            progress_state["value"] += 2
            value = progress_state["value"]
            if value >= 100:
                progress_timer.stop()
                job.update(
                    title=self.tr("Download complete"),
                    message=self.tr("Your file is ready."),
                    kind=NotificationKind.SUCCESS,
                    progress=None,
                    actions=[NotificationAction("open", self.tr("Open file"))],
                    timeout_ms=5000,
                )
            else:
                job.update(
                    message=self.tr("Downloading… %1%").replace("%1", str(value)), progress=value
                )

        def start_download() -> None:
            if progress_state:
                progress_state["handle"].dismiss()
            job = notify(
                self.tr("Downloading"),
                self.tr("Starting…"),
                timeout_ms=None,
                progress=0,
                actions=[NotificationAction("cancel", self.tr("Cancel"))],
            )
            if job is not None:
                progress_state.update(handle=job, value=0)
                progress_timer.start()

        progress_timer.timeout.connect(advance_download)
        bottom = QHBoxLayout()
        progress = QPushButton(self.tr("Simulate download"))
        progress.clicked.connect(start_download)
        minimized = QPushButton(self.tr("Notify after minimizing"))
        minimized.setEnabled(desktop_manager.isDesktop())

        def notify_minimized() -> None:
            self.showMinimized()
            QTimer.singleShot(
                700,
                lambda: notify(
                    self.tr("Background task complete"),
                    self.tr("Notifications remain available while the window is minimized."),
                    kind=NotificationKind.SUCCESS,
                    manager=desktop_manager,
                ),
            )

        minimized.clicked.connect(notify_minimized)
        clear = QPushButton(self.tr("Clear all"))
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
            if self.edge_dock_example is not None:
                self.edge_dock_example.close()
            for manager in self.notification_managers:
                manager.clear()

    def _create_message_box_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("Message boxes"))
        comparison = QGridLayout()
        comparison.setHorizontalSpacing(24)
        comparison.setVerticalSpacing(8)
        comparison.addWidget(QLabel("QMessageBox"), 0, 0)
        comparison.addWidget(QLabel("ModernMessageBox"), 0, 1)
        comparison.setColumnStretch(0, 1)
        comparison.setColumnStretch(1, 1)
        examples = (
            (
                self.tr("Information"),
                QStyle.StandardPixmap.SP_MessageBoxInformation,
                self._show_information,
            ),
            (
                self.tr("Question"),
                QStyle.StandardPixmap.SP_MessageBoxQuestion,
                self._show_question,
            ),
            (
                self.tr("Warning"),
                QStyle.StandardPixmap.SP_MessageBoxWarning,
                self._show_warning,
            ),
            (
                self.tr("Critical"),
                QStyle.StandardPixmap.SP_MessageBoxCritical,
                self._show_critical,
            ),
            (
                self.tr("Detailed message"),
                QStyle.StandardPixmap.SP_FileDialogDetailedView,
                self._show_detailed_message,
            ),
        )
        for row, (text, icon, callback) in enumerate(examples, start=1):
            for column, box_type in enumerate((QMessageBox, ModernMessageBox)):
                button = QPushButton(standard_icon(icon), text)
                button.setFixedWidth(220)
                button.clicked.connect(
                    lambda _checked=False, show=callback, widget_type=box_type: show(widget_type)
                )
                comparison.addWidget(button, row, column, Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(comparison)
        layout.addStretch()
        return page

    def _create_tab_widget_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("Tab widget"))
        layout.addWidget(QLabel(self.tr("Switch between fixed sections using the tabs.")))
        comparison = QGridLayout()
        comparison.setHorizontalSpacing(24)
        self.native_tab_widget = QTabWidget(page)
        self.tab_widget = ModernTabWidget(page)
        for column, (heading, tabs) in enumerate(
            (("QTabWidget", self.native_tab_widget), ("ModernTabWidget", self.tab_widget))
        ):
            comparison.addWidget(QLabel(heading), 0, column)
            comparison.setColumnStretch(column, 1)
            tabs.setFixedHeight(220)
            for title, description in (
                (self.tr("General"), self.tr("General settings for this section.")),
                (self.tr("Details"), self.tr("More details in a separate section.")),
            ):
                section = QWidget()
                section_layout = QVBoxLayout(section)
                description_label = QLabel(description)
                description_label.setWordWrap(True)
                section_layout.addWidget(description_label)
                section_layout.addStretch()
                tabs.addTab(section, title)
            comparison.addWidget(tabs, 1, column)
        layout.addLayout(comparison)
        layout.addWidget(QLabel("ModernSegmentedControl"))
        self.segmented_control = ModernSegmentedControl(
            [self.tr("General"), self.tr("Details")], page
        )
        layout.addWidget(self.segmented_control, 0, Qt.AlignmentFlag.AlignLeft)
        segment_status = QLabel(self.tr("General settings for this section."))
        descriptions = (
            self.tr("General settings for this section."),
            self.tr("More details in a separate section."),
        )
        self.segmented_control.currentChanged.connect(
            lambda index: segment_status.setText(descriptions[index])
        )
        layout.addWidget(segment_status)
        disabled_segments = ModernSegmentedControl([self.tr("General"), self.tr("Disabled")], page)
        disabled_segments.setItemEnabled(1, False)
        layout.addWidget(disabled_segments, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return page

    def _create_combo_box_page(self) -> QWidget:
        page, layout = self._create_page("ModernComboBox")
        layout.addWidget(QLabel(self.tr("Rounded controls, familiar Qt interactions.")))
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)
        grid.addWidget(QLabel(self.tr("Native QComboBox")), 0, 1)
        grid.addWidget(QLabel("ModernComboBox"), 0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        layout.addLayout(grid)
        status = QLabel(self.tr("Choose an item to see the native activated signal."))
        status.setWordWrap(True)
        for row, (label, example_type) in enumerate(
            (
                (self.tr("Standard"), "standard"),
                (self.tr("Icons"), "icons"),
                (self.tr("Placeholder"), "placeholder"),
                (self.tr("Editable"), "editable"),
                (self.tr("Disabled"), "disabled"),
                (self.tr("Long list"), "long-list"),
                (self.tr("Right to left"), "rtl"),
            ),
            start=1,
        ):
            grid.addWidget(QLabel(label), row, 0)
            for column, widget_type in enumerate((QComboBox, ModernComboBox), start=1):
                combo = widget_type()
                combo.setMinimumWidth(230)
                combo.addItems(["Windows 11", "Windows 10", "Linux", "macOS"])
                if example_type == "icons":
                    combo.setItemIcon(0, QIcon(":/pyside6_modern_widgets/icons/settings.png"))
                    combo.setItemIcon(1, QIcon(":/pyside6_modern_widgets/icons/application.png"))
                    combo.insertSeparator(2)
                elif example_type == "placeholder":
                    combo.setPlaceholderText(self.tr("Choose an operating system"))
                    combo.setCurrentIndex(-1)
                elif example_type == "editable":
                    combo.setEditable(True)
                    combo.setInsertPolicy(QComboBox.InsertPolicy.InsertAtBottom)
                elif example_type == "disabled":
                    combo.setEnabled(False)
                elif example_type == "long-list":
                    combo.clear()
                    combo.addItems(
                        [
                            self.tr("Option %1").replace("%1", f"{number:02d}")
                            for number in range(1, 51)
                        ]
                    )
                    combo.setMaxVisibleItems(8)
                elif example_type == "rtl":
                    combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                combo.activated.connect(
                    lambda index, combo=combo, label=label: status.setText(
                        self.tr("%1 / %2: index=%3, text=%4")
                        .replace("%1", type(combo).__name__)
                        .replace("%2", label)
                        .replace("%3", str(index))
                        .replace("%4", combo.currentText())
                    )
                )
                grid.addWidget(combo, row, column)
        layout.addStretch()
        layout.addWidget(status)
        return page

    def _create_line_edit_page(self) -> QWidget:
        page, layout = self._create_page("ModernLineEdit")
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)
        grid.addWidget(QLabel(self.tr("Native QLineEdit")), 0, 1)
        grid.addWidget(QLabel("ModernLineEdit"), 0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        for row, (label, state) in enumerate(
            (
                (self.tr("Standard"), "standard"),
                (self.tr("Placeholder"), "placeholder"),
                (self.tr("Clear button"), "clear"),
                (self.tr("Read-only"), "read-only"),
                (self.tr("Password"), "password"),
                (self.tr("Disabled"), "disabled"),
                (self.tr("Right to left"), "rtl"),
            ),
            start=1,
        ):
            grid.addWidget(QLabel(label), row, 0)
            for column, widget_type in enumerate((QLineEdit, ModernLineEdit), start=1):
                editor = widget_type()
                editor.setMinimumWidth(230)
                editor.setAccessibleName(f"{label} {widget_type.__name__}")
                if state == "placeholder":
                    editor.setPlaceholderText(self.tr("Enter a name"))
                else:
                    editor.setText(self.tr("Workspace name"))
                if state == "clear":
                    editor.setClearButtonEnabled(True)
                elif state == "read-only":
                    editor.setReadOnly(True)
                elif state == "password":
                    editor.setEchoMode(QLineEdit.EchoMode.Password)
                elif state == "disabled":
                    editor.setEnabled(False)
                elif state == "rtl":
                    editor.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                grid.addWidget(editor, row, column)
        layout.addLayout(grid)
        layout.addStretch()
        return page

    def _create_spin_editors_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("Spin editors"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(14)
        grid.addWidget(QLabel(self.tr("Native Qt")), 0, 1)
        grid.addWidget(QLabel(self.tr("Modern")), 0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        sample_date = QDateTime(QDate(2026, 10, 1), QTime(12, 21))
        for row, (label, kind) in enumerate(
            (
                (self.tr("Number"), "number"),
                (self.tr("Decimal"), "decimal"),
                (self.tr("Range and suffix"), "range"),
                (self.tr("Disabled"), "disabled-number"),
                (self.tr("Date and time"), "datetime"),
                (self.tr("Date only"), "date"),
                (self.tr("Time only"), "time"),
                (self.tr("Calendar popup"), "calendar"),
            ),
            start=1,
        ):
            grid.addWidget(QLabel(label), row, 0)
            for column, modern in enumerate((False, True), start=1):
                editor: QWidget
                if kind in ("number", "range", "disabled-number"):
                    number_editor = ModernSpinBox() if modern else QSpinBox()
                    number_editor.setRange(0, 100)
                    number_editor.setValue(50)
                    if kind == "range":
                        number_editor.setRange(10, 60)
                        number_editor.setSuffix(" %")
                    elif kind == "disabled-number":
                        number_editor.setEnabled(False)
                    editor = number_editor
                elif kind == "decimal":
                    decimal_editor = ModernDoubleSpinBox() if modern else QDoubleSpinBox()
                    decimal_editor.setRange(0.0, 100.0)
                    decimal_editor.setValue(12.5)
                    editor = decimal_editor
                elif kind == "date":
                    date_editor = (
                        ModernDateEdit(sample_date.date())
                        if modern
                        else QDateEdit(sample_date.date())
                    )
                    date_editor.setDisplayFormat("yyyy/M/d")
                    editor = date_editor
                elif kind == "time":
                    time_editor = (
                        ModernTimeEdit(sample_date.time())
                        if modern
                        else QTimeEdit(sample_date.time())
                    )
                    time_editor.setDisplayFormat("HH:mm")
                    editor = time_editor
                else:
                    datetime_editor = (
                        ModernDateTimeEdit(sample_date) if modern else QDateTimeEdit(sample_date)
                    )
                    datetime_editor.setDisplayFormat("yyyy/M/d HH:mm")
                    if kind == "calendar":
                        datetime_editor.setCalendarPopup(True)
                    editor = datetime_editor
                editor.setMinimumWidth(235)
                editor.setAccessibleName(f"{label} {type(editor).__name__}")
                grid.addWidget(editor, row, column)
        layout.addLayout(grid)
        layout.addStretch()
        return page

    def _create_more_inputs_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("More inputs"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)
        grid.addWidget(QLabel(self.tr("Native Qt")), 0, 1)
        grid.addWidget(QLabel(self.tr("Modern")), 0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        for row, (label, native_type, modern_type) in enumerate(
            (
                (self.tr("Plain text"), QPlainTextEdit, ModernPlainTextEdit),
                (self.tr("Rich text"), QTextEdit, ModernTextEdit),
                (self.tr("Shortcut"), QKeySequenceEdit, ModernKeySequenceEdit),
                (self.tr("Font"), QFontComboBox, ModernFontComboBox),
            ),
            start=1,
        ):
            grid.addWidget(QLabel(label), row, 0)
            for column, widget_type in enumerate((native_type, modern_type), start=1):
                editor = widget_type()
                editor.setAccessibleName(f"{label} {widget_type.__name__}")
                if row in (1, 2):
                    editor.setPlainText(self.tr("Sample text"))
                    editor.setFixedHeight(100)
                elif row == 3:
                    editor.setKeySequence(QKeySequence("Ctrl+K"))
                grid.addWidget(editor, row, column)
        layout.addLayout(grid)
        layout.addStretch()
        return page

    def _create_switch_page(self) -> QWidget:
        page, layout = self._create_page("ModernSwitch")
        hint = QLabel(
            self.tr("Click to toggle. Use Tab and Space to try the keyboard focus indicator.")
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        form = QFormLayout()
        form.setVerticalSpacing(14)
        form.addRow("QLineEdit", QLineEdit(self.tr("Native text field")))
        for widget_type in (QComboBox, ModernComboBox):
            combo = widget_type()
            combo.addItems([self.tr("Default size"), self.tr("No fixed height")])
            form.addRow(widget_type.__name__, combo)
        switch = ModernSwitch(self.tr("Enable notifications"))
        switch.setChecked(True)
        form.addRow("ModernSwitch", switch)
        states = QHBoxLayout()
        for checked in (False, True):
            disabled = ModernSwitch(self.tr("Disabled"))
            disabled.setChecked(checked)
            disabled.setEnabled(False)
            states.addWidget(disabled)
        form.addRow(self.tr("Disabled states"), states)
        rtl = ModernSwitch(self.tr("Right to left"))
        rtl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        rtl.setChecked(True)
        form.addRow("RTL", rtl)
        layout.addLayout(form)
        status = QLabel(self.tr("Notifications: on"))
        switch.toggled.connect(
            lambda checked: status.setText(
                self.tr("Notifications: on") if checked else self.tr("Notifications: off")
            )
        )
        layout.addWidget(status)
        layout.addStretch()
        return page

    def _create_settings_page(self) -> QWidget:
        page, layout = self._create_page(self.tr("Settings"))
        manager = theme_manager()
        layout.addWidget(QLabel(self.tr("Appearance")))
        self.theme_mode_combo = QComboBox()
        for label, mode in (
            (self.tr("Follow system"), ThemeMode.SYSTEM),
            (self.tr("Light"), ThemeMode.LIGHT),
            (self.tr("Dark"), ThemeMode.DARK),
        ):
            self.theme_mode_combo.addItem(label, mode.value)
        self._sync_theme_mode(manager.mode())
        self.theme_mode_combo.currentIndexChanged.connect(self._set_theme_mode)
        manager.modeChanged.connect(self._sync_theme_mode)
        layout.addWidget(self.theme_mode_combo)

        self.wallpaper_checkbox = QCheckBox(self.tr("Use desktop wallpaper colors"))
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
        page, layout = self._create_page(self.tr("Toolbars"))
        hint = QLabel(
            self.tr(
                "Compare the same actions in native and modern toolbars. "
                "Narrow both to compare overflow, or hover and click to compare button states."
            )
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        comparison = QGridLayout()
        comparison.setHorizontalSpacing(24)
        comparison.setVerticalSpacing(8)
        layout.addLayout(comparison)
        status = QLabel(self.tr("Choose an action"))
        status.setWordWrap(True)
        toolbars = []
        for column, (label, toolbar_type, menu_type) in enumerate(
            (
                (self.tr("Native QToolBar"), QToolBar, QMenu),
                ("ModernToolBar", ModernToolBar, ModernMenu),
            )
        ):
            comparison.addWidget(QLabel(label), 0, column)
            toolbar = toolbar_type(self.tr("Editing"), page)
            toolbar.setMovable(False)
            toolbar.setFloatable(False)
            toolbar.setIconSize(QSize(18, 18))
            toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            toolbar.setFixedWidth(260)
            for text, icon in (
                (self.tr("Open"), QStyle.StandardPixmap.SP_DialogOpenButton),
                (self.tr("Save"), QStyle.StandardPixmap.SP_DialogSaveButton),
                (self.tr("Back"), QStyle.StandardPixmap.SP_ArrowBack),
                (self.tr("Forward"), QStyle.StandardPixmap.SP_ArrowForward),
            ):
                toolbar.addAction(standard_icon(icon), text)
            toolbar.addSeparator()
            toggle = toolbar.addAction(
                standard_icon(QStyle.StandardPixmap.SP_FileDialogListView), self.tr("Panel")
            )
            toggle.setCheckable(True)
            toggle.setChecked(True)
            toolbar.addAction(
                standard_icon(QStyle.StandardPixmap.SP_DialogCancelButton),
                self.tr("Unavailable"),
            ).setEnabled(False)
            more = menu_type(self.tr("More"), page)
            more.addAction(self.tr("Details"))
            more.setIcon(standard_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
            toolbar.addAction(more.menuAction())
            toolbar.actionTriggered.connect(
                lambda action, label=label: status.setText(
                    self.tr("%1: %2").replace("%1", label).replace("%2", action.text())
                )
            )
            more.triggered.connect(
                lambda action, label=label: status.setText(
                    self.tr("%1: %2").replace("%1", label).replace("%2", action.text())
                )
            )
            comparison.addWidget(toolbar, 1, column, Qt.AlignmentFlag.AlignLeft)
            comparison.setColumnMinimumWidth(column, 320)
            comparison.setColumnStretch(column, 1)
            toolbars.append(toolbar)
        width_label = QLabel(self.tr("Width of each toolbar: %1 px").replace("%1", "260"))
        layout.addWidget(width_label)
        width = ModernSlider(Qt.Orientation.Horizontal)
        width.setRange(100, 320)
        width.setValue(260)
        width.valueChanged.connect(
            lambda value: width_label.setText(
                self.tr("Width of each toolbar: %1 px").replace("%1", str(value))
            )
        )
        layout.addWidget(width)
        text = QCheckBox(self.tr("Show text beside icons"))
        layout.addWidget(text)
        rtl = QCheckBox(self.tr("Right-to-left layout"))
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
        page, layout = self._create_page(self.tr("Menus"))
        self.menu_button = QPushButton(
            standard_icon(QStyle.StandardPixmap.SP_TitleBarMenuButton),
            self.tr("Open ModernMenu"),
        )
        self.menu_button.setFixedWidth(220)
        self.menu_button.clicked.connect(self._show_menu)
        layout.addWidget(self.menu_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.native_menu_button = QPushButton(
            standard_icon(QStyle.StandardPixmap.SP_TitleBarMenuButton),
            self.tr("Open native QMenu"),
        )
        self.native_menu_button.setFixedWidth(220)
        self.native_menu_button.clicked.connect(self._show_native_menu)
        layout.addWidget(self.native_menu_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.choice_groups: list[QActionGroup] = []
        self.example_menu = ModernMenu(self.tr("Actions"), self)
        self._populate_example_menu(self.example_menu)

        self.native_menu = QMenu(self.tr("Native actions"), self)
        self._populate_example_menu(self.native_menu)
        layout.addStretch()
        return page

    def _populate_example_menu(self, menu: QMenu) -> None:
        default_action = menu.addAction(self.tr("Default action"))
        menu.setDefaultAction(default_action)
        menu.addAction(
            standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton),
            self.tr("Qt standard icon"),
        )
        menu.addAction(
            QIcon(":/pyside6_modern_widgets/icons/application.png"),
            self.tr("Custom icon"),
        )
        menu.addSeparator()

        toggle_action = menu.addAction(self.tr("Checkable toggle"))
        toggle_action.setCheckable(True)
        toggle_action.setChecked(True)

        choice_menu = menu.addMenu(self.tr("Single choice"))
        choice_group = QActionGroup(choice_menu)
        choice_group.setExclusive(True)
        self.choice_groups.append(choice_group)
        for text, selected in (
            (self.tr("Compact"), False),
            (self.tr("Comfortable"), True),
            (self.tr("Spacious"), False),
        ):
            action = choice_menu.addAction(text)
            action.setCheckable(True)
            choice_group.addAction(action)
            if selected:
                action.setChecked(True)

        menu.addSeparator()
        combined_shortcut = menu.addAction(self.tr("Combined shortcut"))
        combined_shortcut.setShortcut(QKeySequence("Ctrl+Shift+S"))
        combined_shortcut.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        alt_shortcut = menu.addAction(self.tr("Alt shortcut"))
        alt_shortcut.setShortcut(QKeySequence("Alt+M"))
        alt_shortcut.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        menu.addAction(self.tr("&Keyboard mnemonic"))

        nested_menu = menu.addMenu(self.tr("Nested menus"))
        level_two_menu = nested_menu.addMenu(self.tr("Level 2"))
        level_three_menu = level_two_menu.addMenu(self.tr("Level 3"))
        level_three_menu.addAction(self.tr("Deep action"))

        menu.addSeparator()
        unavailable_action = menu.addAction(self.tr("Unavailable action"))
        unavailable_action.setEnabled(False)

    def _show_menu(self) -> None:
        position = self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft())
        self.example_menu.popup(position)

    def _show_native_menu(self) -> None:
        position = self.native_menu_button.mapToGlobal(self.native_menu_button.rect().bottomLeft())
        self.native_menu.popup(position)

    def _show_dialog(self, dialog_type: type[QDialog]) -> None:
        dialog = dialog_type(self)
        dialog.setWindowTitle(self.tr("Save changes"))

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(self.tr("The document has unsaved changes.")))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec()

    def _show_information(self, box_type: type[QMessageBox]) -> None:
        box_type.information(
            self,
            self.tr("Update complete"),
            self.tr("The application is up to date."),
        )

    def _show_question(self, box_type: type[QMessageBox]) -> None:
        box_type.question(
            self,
            self.tr("Replace file"),
            self.tr("A file with this name already exists. Replace it?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

    def _show_warning(self, box_type: type[QMessageBox]) -> None:
        box_type.warning(
            self,
            self.tr("Unsaved changes"),
            self.tr("Closing now will discard your changes."),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

    def _show_critical(self, box_type: type[QMessageBox]) -> None:
        box_type.critical(
            self,
            self.tr("Connection failed"),
            self.tr("The server could not be reached."),
            QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Retry,
        )

    def _show_detailed_message(self, box_type: type[QMessageBox]) -> None:
        message_box = box_type(
            QMessageBox.Icon.Warning,
            self.tr("Import completed with warnings"),
            self.tr("Some records could not be imported."),
            QMessageBox.StandardButton.Ok,
            self,
        )
        message_box.setInformativeText(self.tr("Open the details to review the skipped records."))
        message_box.setDetailedText(
            self.tr(
                "Row 17: missing email address\n"
                "Row 24: duplicate identifier\n"
                "Row 31: unsupported date format"
            )
        )
        message_box.setCheckBox(QCheckBox(self.tr("Do not show import warnings again")))
        message_box.exec()

    def _create_actions(self) -> None:
        self.home_action = QAction(self.tr("Back to Home"), self)
        self.home_action.setMenuRole(QAction.MenuRole.NoRole)
        self.home_action.triggered.connect(lambda: self.navigation.setCurrentIndex(0))

        self.compact_action = QAction(self.tr("Compact Navigation"), self)
        self.compact_action.setCheckable(True)
        self.compact_action.toggled.connect(self.navigation.sidebar.setCollapsed)
        self.navigation.sidebar.collapsedChanged.connect(self.compact_action.setChecked)

        self.quit_action = QAction(self.tr("Quit"), self)
        self.quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self.quit_action.triggered.connect(QApplication.quit)

        self.full_screen_action = QAction(self.tr("Toggle Full Screen"), self)
        self.full_screen_action.setCheckable(True)
        self.full_screen_action.setShortcut(QKeySequence("F11"))
        self.full_screen_action.toggled.connect(self._toggle_full_screen)

    def _create_menu_bar(self) -> None:
        menu_bar = ModernMenuBar(self)
        menu_bar.setNativeMenuBar(True)

        file_menu = menu_bar.addMenu(self.tr("&File"))
        file_menu.addAction(self.home_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        view_menu = menu_bar.addMenu(self.tr("&View"))
        view_menu.addAction(self.compact_action)
        view_menu.addSeparator()
        view_menu.addAction(self.full_screen_action)

        window_menu = menu_bar.addMenu(self.tr("&Window"))
        window_menu.addAction(self.tr("Minimize"), self.showMinimized)
        window_menu.addAction(self.tr("Maximize / Restore"), self._toggle_maximized)
        window_menu.addSeparator()
        close_action = window_menu.addAction(self.tr("Close"), self.close)
        close_action.setShortcut(QKeySequence.StandardKey.Close)

        assert self.titleBar is not None
        self.titleBar.addCustomWidget(menu_bar, align="left")

        self.theme_button = QPushButton(self)
        self.theme_button.setFixedHeight(24)
        self.theme_button.clicked.connect(self._toggle_theme)
        theme_manager().themeChanged.connect(self._sync_theme_button)
        self._sync_theme_button()
        self.titleBar.addCustomWidget(self.theme_button, align="right")

    def _toggle_theme(self) -> None:
        manager = theme_manager()
        manager.setMode(ThemeMode.LIGHT if manager.isDark() else ThemeMode.DARK)

    def _sync_theme_button(self, *_args) -> None:
        self.theme_button.setText(self.tr("Light") if theme_manager().isDark() else self.tr("Dark"))

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
    ModernToolTip.install()
    locale = example_locale()
    install_translators(app, locale)
    app.setApplicationName(QCoreApplication.translate("ExampleWindow", "Modern Widgets Example"))
    window = ExampleWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
