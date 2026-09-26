"""Exercise edge docking from a launcher that stays available when the tool hides."""

import sys

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyside6_modern_widgets import (
    DockConfig,
    DockRestoreTrigger,
    DockSide,
    EdgeDockController,
    ModernComboBox,
    ModernSwitch,
    ModernWindow,
)

if __package__:
    from ._example_i18n import example_locale, install_translators
else:
    from _example_i18n import example_locale, install_translators


class EdgeDockExample(ModernWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Screen-edge docking controls"))
        self.resize(460, 570)
        self.floating_window = ModernWindow(self, Qt.WindowType.Tool)
        self.floating_window.setWindowTitle(self.tr("Floating tool"))
        self.floating_window.resize(400, 240)
        tool_content = QWidget()
        self.tool_layout = QVBoxLayout(tool_content)
        self.drag_strip = self._new_drag_strip()
        self.tool_layout.addWidget(self.drag_strip)
        self.tool_layout.addWidget(QLineEdit(self.tr("Text selection still works")))
        hint = QLabel(
            self.tr("Use the controls window to hide, reopen, or replace this drag strip.")
        )
        hint.setWordWrap(True)
        self.tool_layout.addWidget(hint)
        close = QPushButton(self.tr("Close tool"))
        close.clicked.connect(self.floating_window.close)
        self.tool_layout.addWidget(close)
        self.floating_window.setCentralWidget(tool_content)

        content = QWidget()
        layout = QVBoxLayout(content)
        instructions = QLabel(
            self.tr(
                "Drag the tool's strip to a screen edge, then move away to auto-hide it. "
                "Restore it using the selected hover or click action. This controls window stays "
                "available even when the tool and its handle are hidden."
            )
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        self.enabled_switch = ModernSwitch(self.tr("Enable docking"))
        self.enabled_switch.setChecked(True)
        self.auto_hide_switch = ModernSwitch(self.tr("Hide when the pointer leaves"))
        self.auto_hide_switch.setChecked(True)
        layout.addWidget(self.enabled_switch)
        layout.addWidget(self.auto_hide_switch)

        handle_options = QFormLayout()
        self.handle_style = ModernComboBox()
        self.handle_style.addItems(
            [self.tr("Thin strip"), self.tr("Application icon"), self.tr("Settings icon")]
        )
        self.handle_icon_size = QSpinBox()
        self.handle_icon_size.setRange(16, 64)
        self.handle_icon_size.setValue(24)
        self.restore_trigger = ModernComboBox()
        self.restore_trigger.addItem(self.tr("Hover or click"), DockRestoreTrigger.HOVER)
        self.restore_trigger.addItem(self.tr("Click only"), DockRestoreTrigger.CLICK)
        handle_options.addRow(self.tr("Handle appearance"), self.handle_style)
        handle_options.addRow(self.tr("Icon size"), self.handle_icon_size)
        handle_options.addRow(self.tr("Restore action"), self.restore_trigger)
        layout.addLayout(handle_options)

        actions = QGridLayout()
        show = QPushButton(self.tr("Show / restore tool"))
        show.clicked.connect(self.show_floating)
        dismiss = QPushButton(self.tr("Hide tool and handle"))
        dismiss.clicked.connect(self.dismiss_floating)
        actions.addWidget(show, 0, 0)
        actions.addWidget(dismiss, 0, 1)
        self.edge_buttons = []
        for index, (side, label) in enumerate(
            (
                (DockSide.LEFT, self.tr("Dock left")),
                (DockSide.RIGHT, self.tr("Dock right")),
                (DockSide.TOP, self.tr("Dock top")),
                (DockSide.BOTTOM, self.tr("Dock bottom")),
            )
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, side=side: self.dock_to(side))
            actions.addWidget(button, 1 + index // 2, index % 2)
            self.edge_buttons.append(button)
        replace = QPushButton(self.tr("Replace drag strip"))
        replace.clicked.connect(self.replace_drag_strip)
        self.attach_button = QPushButton()
        self.attach_button.clicked.connect(self.toggle_attachment)
        actions.addWidget(replace, 3, 0)
        actions.addWidget(self.attach_button, 3, 1)
        layout.addLayout(actions)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()
        self.setCentralWidget(content)

        self.dock: EdgeDockController | None = None
        self.enabled_switch.toggled.connect(self.set_docking_enabled)
        self.auto_hide_switch.toggled.connect(self.set_auto_hide)
        self.handle_style.currentIndexChanged.connect(self.update_handle_options)
        self.handle_icon_size.valueChanged.connect(self.update_handle_options)
        self.restore_trigger.currentIndexChanged.connect(self.update_handle_options)
        self.toggle_attachment()

    def _new_drag_strip(self) -> QLabel:
        strip = QLabel(self.tr("Drag here to a screen edge"))
        strip.setMinimumHeight(48)
        strip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return strip

    def show_floating(self) -> None:
        if self.dock is not None:
            self.dock.expand()
        else:
            self.floating_window.show()
            self.floating_window.raise_()
            self.floating_window.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.dismiss_floating()
        super().closeEvent(event)

    def dismiss_floating(self) -> None:
        if self.dock is not None:
            # hide() alone cannot remove the handle of an already collapsed tool.
            self.dock.dismiss()
        else:
            self.floating_window.hide()

    def dock_to(self, side: DockSide) -> None:
        if self.dock is not None:
            self.dock.expand()
            self.dock.dock(side)

    def replace_drag_strip(self) -> None:
        old_strip = self.drag_strip
        self.drag_strip = self._new_drag_strip()
        self.drag_strip.setText(self.tr("New drag strip - drag me"))
        self.tool_layout.replaceWidget(old_strip, self.drag_strip)
        if self.dock is not None:
            self.dock.setDragWidget(self.drag_strip)
        old_strip.hide()
        old_strip.deleteLater()

    def toggle_attachment(self) -> None:
        if self.dock is not None:
            # A detached controller cannot be enabled again; create a new one.
            self.dock.detach()
            self.dock.deleteLater()
            self.dock = None
        else:
            self.dock = EdgeDockController(
                self.floating_window,
                DockConfig(
                    sides=(DockSide.LEFT, DockSide.RIGHT, DockSide.TOP, DockSide.BOTTOM),
                    handle_icon=self.selected_handle_icon(),
                    handle_icon_size=self.handle_icon_size.value(),
                    handle_tooltip=self.tr("Restore floating tool"),
                    restore_trigger=self.restore_trigger.currentData(),
                ),
                drag_widget=self.drag_strip,
                auto_hide=self.auto_hide_switch.isChecked(),
            )
            self.dock.setEnabled(self.enabled_switch.isChecked())
            self.dock.dockSideChanged.connect(self.update_status)
            self.dock.collapsedChanged.connect(self.update_status)
        self.update_status()

    def selected_handle_icon(self) -> QIcon:
        paths = (
            "",
            ":/pyside6_modern_widgets/icons/application.png",
            ":/pyside6_modern_widgets/icons/settings.png",
        )
        return QIcon(paths[self.handle_style.currentIndex()])

    def update_handle_options(self) -> None:
        if self.dock is not None:
            # Works while collapsed; the handle is resized without reopening the tool.
            self.dock.setRestoreTrigger(self.restore_trigger.currentData())
            self.dock.setHandleIcon(self.selected_handle_icon())
            self.dock.setHandleIconSize(self.handle_icon_size.value())
        self.update_status()

    def set_docking_enabled(self, enabled: bool) -> None:
        if self.dock is not None:
            self.dock.setEnabled(enabled)
        self.update_status()

    def set_auto_hide(self, enabled: bool) -> None:
        if self.dock is not None:
            self.dock.setAutoHide(enabled)
        self.update_status()

    def update_status(self) -> None:
        attached = self.dock is not None
        self.enabled_switch.setEnabled(attached)
        self.auto_hide_switch.setEnabled(attached)
        self.handle_style.setEnabled(attached)
        self.handle_icon_size.setEnabled(attached and self.handle_style.currentIndex() != 0)
        self.restore_trigger.setEnabled(attached)
        self.attach_button.setText(
            self.tr("Detach docking") if attached else self.tr("Attach docking")
        )
        enabled = self.dock is not None and self.dock.isEnabled()
        for button in self.edge_buttons:
            button.setEnabled(enabled)
        if self.dock is None:
            self.status.setText(self.tr("Docking detached. Attach again to enable edge docking."))
        elif not enabled:
            self.status.setText(self.tr("Docking disabled. Enable it to snap and auto-hide again."))
        else:
            state = (
                self.tr("Handle visible") if self.dock.isCollapsed() else self.tr("Handle hidden")
            )
            side = {
                DockSide.NONE: self.tr("None"),
                DockSide.LEFT: self.tr("Left"),
                DockSide.RIGHT: self.tr("Right"),
                DockSide.TOP: self.tr("Top"),
                DockSide.BOTTOM: self.tr("Bottom"),
            }[self.dock.dockSide()]
            self.status.setText(self.tr("Edge: %1 | %2").replace("%1", side).replace("%2", state))


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    install_translators(app, example_locale())
    window = EdgeDockExample()
    window.show()
    window.floating_window.move(window.frameGeometry().topRight() + QPoint(24, 0))
    window.show_floating()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
