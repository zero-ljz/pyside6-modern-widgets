"""A modern, Qt-painted alternative to the common QMessageBox API."""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from .modern_dialog import ModernDialog
from .theme import DEFAULT_METRICS, ModernMetrics, ModernTheme


class ModernMessageBox(ModernDialog):
    """A message box with modern chrome and familiar QMessageBox semantics."""

    Icon = QMessageBox.Icon
    ButtonRole = QMessageBox.ButtonRole
    StandardButton = QMessageBox.StandardButton

    buttonClicked = Signal(QAbstractButton)

    _ICON_PIXMAPS: ClassVar[dict[QMessageBox.Icon, QStyle.StandardPixmap]] = {
        Icon.Information: QStyle.StandardPixmap.SP_MessageBoxInformation,
        Icon.Warning: QStyle.StandardPixmap.SP_MessageBoxWarning,
        Icon.Critical: QStyle.StandardPixmap.SP_MessageBoxCritical,
        Icon.Question: QStyle.StandardPixmap.SP_MessageBoxQuestion,
    }

    def __init__(
        self,
        icon: QMessageBox.Icon | QWidget = Icon.NoIcon,
        title: str = "",
        text: str = "",
        buttons: QMessageBox.StandardButton = StandardButton.NoButton,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        if isinstance(icon, QWidget):
            if title or text or buttons != self.StandardButton.NoButton or parent is not None:
                raise TypeError("parent-only construction cannot include message-box arguments")
            parent = icon
            icon = self.Icon.NoIcon

        super().__init__(parent, theme=theme, metrics=metrics)
        self._icon = icon
        self._icon_pixmap = QPixmap()
        self._clicked_button: QAbstractButton | None = None
        self._default_button: QPushButton | None = None
        self._escape_button: QAbstractButton | None = None
        self._check_box: QCheckBox | None = None
        self._custom_button_results: dict[QAbstractButton, int] = {}
        self._next_custom_result = 2

        self._message_layout = QVBoxLayout(self)
        self._message_layout.setContentsMargins(20, 18, 20, 18)
        self._message_layout.setSpacing(12)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)
        self._message_layout.addLayout(body_layout)

        self._icon_label = QLabel(self)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._icon_label.setAccessibleName(self.tr("Message icon"))
        body_layout.addWidget(self._icon_label, 0, Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)
        body_layout.addLayout(text_layout, 1)

        self._text_label = QLabel(self)
        self._text_label.setWordWrap(True)
        self._text_label.setTextFormat(Qt.TextFormat.AutoText)
        self._text_label.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self._text_label.setOpenExternalLinks(True)
        text_layout.addWidget(self._text_label)

        self._informative_label = QLabel(self)
        self._informative_label.setWordWrap(True)
        self._informative_label.setTextFormat(Qt.TextFormat.AutoText)
        self._informative_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self._informative_label.setOpenExternalLinks(True)
        text_layout.addWidget(self._informative_label)

        self._details_button = QPushButton(self.tr("Show Details..."), self)
        self._details_button.setCheckable(True)
        self._details_button.toggled.connect(self._set_details_visible)
        self._message_layout.addWidget(
            self._details_button,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )

        self._details_editor = QPlainTextEdit(self)
        self._details_editor.setReadOnly(True)
        self._details_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._details_editor.setMinimumHeight(120)
        self._message_layout.addWidget(self._details_editor)

        self._button_box = QDialogButtonBox(self)
        self._button_box.clicked.connect(self._on_button_clicked)
        self._message_layout.addWidget(self._button_box)

        self.setWindowTitle(title)
        self.setText(text)
        self.setInformativeText("")
        self.setDetailedText("")
        self.setIcon(icon)
        self.setStandardButtons(buttons)
        self.setMinimumWidth(320)

    def text(self) -> str:
        return self._text_label.text()

    def setText(self, text: str) -> None:
        self._text_label.setText(text)
        self._text_label.setVisible(bool(text))

    def informativeText(self) -> str:
        return self._informative_label.text()

    def setInformativeText(self, text: str) -> None:
        self._informative_label.setText(text)
        self._informative_label.setVisible(bool(text))

    def detailedText(self) -> str:
        return self._details_editor.toPlainText()

    def setDetailedText(self, text: str) -> None:
        self._details_editor.setPlainText(text)
        self._details_button.setVisible(bool(text))
        if not text:
            self._details_button.setChecked(False)
        self._details_editor.setVisible(bool(text) and self._details_button.isChecked())

    def textFormat(self) -> Qt.TextFormat:
        return self._text_label.textFormat()

    def setTextFormat(self, text_format: Qt.TextFormat) -> None:
        self._text_label.setTextFormat(text_format)
        self._informative_label.setTextFormat(text_format)

    def textInteractionFlags(self) -> Qt.TextInteractionFlag:
        return self._text_label.textInteractionFlags()

    def setTextInteractionFlags(self, flags: Qt.TextInteractionFlag) -> None:
        self._text_label.setTextInteractionFlags(flags)
        self._informative_label.setTextInteractionFlags(flags)

    def icon(self) -> QMessageBox.Icon:
        return self._icon

    def setIcon(self, icon: QMessageBox.Icon) -> None:
        self._icon = icon
        standard_pixmap = self._ICON_PIXMAPS.get(icon)
        if standard_pixmap is None:
            self.setIconPixmap(QPixmap())
            self._icon = icon
            return
        size = self.style().pixelMetric(QStyle.PixelMetric.PM_MessageBoxIconSize)
        self._icon_pixmap = self.style().standardIcon(standard_pixmap).pixmap(size, size)
        self._icon_label.setPixmap(self._icon_pixmap)
        self._icon_label.show()

    def iconPixmap(self) -> QPixmap:
        return QPixmap(self._icon_pixmap)

    def setIconPixmap(self, pixmap: QPixmap) -> None:
        self._icon = self.Icon.NoIcon
        self._icon_pixmap = QPixmap(pixmap)
        self._icon_label.setPixmap(self._icon_pixmap)
        self._icon_label.setVisible(not pixmap.isNull())

    def standardButtons(self) -> QMessageBox.StandardButton:
        return self.StandardButton(self._button_box.standardButtons().value)

    def setStandardButtons(self, buttons: QMessageBox.StandardButton) -> None:
        dialog_buttons = QDialogButtonBox.StandardButton(buttons.value)
        self._button_box.setStandardButtons(dialog_buttons)
        self._default_button = None
        self._escape_button = None

    def addButton(self, *args):
        if len(args) == 1 and isinstance(args[0], self.StandardButton):
            standard = QDialogButtonBox.StandardButton(args[0].value)
            return self._button_box.addButton(standard)
        if len(args) != 2:
            raise TypeError("addButton expects a standard button or a button and role")

        button_or_text, role = args
        dialog_role = QDialogButtonBox.ButtonRole(role.value)
        if isinstance(button_or_text, QAbstractButton):
            self._button_box.addButton(button_or_text, dialog_role)
            button = button_or_text
        else:
            button = self._button_box.addButton(button_or_text, dialog_role)
        self._custom_button_results[button] = self._next_custom_result
        self._next_custom_result += 1
        return button

    def removeButton(self, button: QAbstractButton) -> None:
        self._button_box.removeButton(button)
        self._custom_button_results.pop(button, None)
        if button is self._default_button:
            self._default_button = None
        if button is self._escape_button:
            self._escape_button = None

    def buttons(self) -> list[QAbstractButton]:
        return self._button_box.buttons()

    def button(self, which: QMessageBox.StandardButton) -> QPushButton | None:
        standard = QDialogButtonBox.StandardButton(which.value)
        return self._button_box.button(standard)

    def standardButton(self, button: QAbstractButton) -> QMessageBox.StandardButton:
        standard = self._button_box.standardButton(button)
        return self.StandardButton(standard.value)

    def buttonRole(self, button: QAbstractButton) -> QMessageBox.ButtonRole:
        role = self._button_box.buttonRole(button)
        return self.ButtonRole(role.value)

    def clickedButton(self) -> QAbstractButton | None:
        return self._clicked_button

    def defaultButton(self) -> QPushButton | None:
        return self._default_button

    def setDefaultButton(
        self,
        button: QPushButton | QMessageBox.StandardButton,
    ) -> None:
        default = self.button(button) if isinstance(button, self.StandardButton) else button
        if default is None:
            return
        if self._default_button is not None:
            self._default_button.setDefault(False)
        self._default_button = default
        default.setDefault(True)
        default.setAutoDefault(True)

    def escapeButton(self) -> QAbstractButton | None:
        return self._escape_button

    def setEscapeButton(
        self,
        button: QAbstractButton | QMessageBox.StandardButton,
    ) -> None:
        escape = self.button(button) if isinstance(button, self.StandardButton) else button
        if escape is not None:
            self._escape_button = escape

    def checkBox(self) -> QCheckBox | None:
        return self._check_box

    def setCheckBox(self, check_box: QCheckBox | None) -> None:
        if self._check_box is not None:
            self._message_layout.removeWidget(self._check_box)
            self._check_box.setParent(None)
        self._check_box = check_box
        if check_box is not None:
            self._message_layout.insertWidget(
                self._message_layout.indexOf(self._button_box),
                check_box,
            )

    def exec(self) -> int:
        self._clicked_button = None
        return super().exec()

    def reject(self) -> None:
        escape = self._escape_button or self._inferred_escape_button()
        if escape is None:
            super().reject()
        else:
            self._on_button_clicked(escape)

    def showEvent(self, event) -> None:
        if not self.buttons():
            self.setStandardButtons(self.StandardButton.Ok)
        super().showEvent(event)

    def _set_details_visible(self, visible: bool) -> None:
        self._details_button.setText(
            self.tr("Hide Details...") if visible else self.tr("Show Details...")
        )
        self._details_editor.setVisible(visible)
        if self.isVisible():
            self.adjustSize()

    def _on_button_clicked(self, button: QAbstractButton) -> None:
        self._clicked_button = button
        self.buttonClicked.emit(button)
        standard = self.standardButton(button)
        result = (
            standard.value
            if standard != self.StandardButton.NoButton
            else self._custom_button_results[button]
        )
        self.done(result)

    def _inferred_escape_button(self) -> QAbstractButton | None:
        for standard in (
            self.StandardButton.Cancel,
            self.StandardButton.Close,
            self.StandardButton.No,
            self.StandardButton.Abort,
        ):
            button = self.button(standard)
            if button is not None:
                return button
        return None

    @classmethod
    def _show_message(
        cls,
        icon: QMessageBox.Icon,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton,
        default_button: QMessageBox.StandardButton,
    ) -> QMessageBox.StandardButton:
        message_box = cls(icon, title, text, buttons, parent)
        if default_button != cls.StandardButton.NoButton:
            message_box.setDefaultButton(default_button)
        result = message_box.exec()
        return cls.StandardButton(result)

    @classmethod
    def information(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton = StandardButton.Ok,
        defaultButton: QMessageBox.StandardButton = StandardButton.NoButton,
    ) -> QMessageBox.StandardButton:
        return cls._show_message(cls.Icon.Information, parent, title, text, buttons, defaultButton)

    @classmethod
    def question(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton = StandardButton.Yes | StandardButton.No,
        defaultButton: QMessageBox.StandardButton = StandardButton.NoButton,
    ) -> QMessageBox.StandardButton:
        return cls._show_message(cls.Icon.Question, parent, title, text, buttons, defaultButton)

    @classmethod
    def warning(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton = StandardButton.Ok,
        defaultButton: QMessageBox.StandardButton = StandardButton.NoButton,
    ) -> QMessageBox.StandardButton:
        return cls._show_message(cls.Icon.Warning, parent, title, text, buttons, defaultButton)

    @classmethod
    def critical(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton = StandardButton.Ok,
        defaultButton: QMessageBox.StandardButton = StandardButton.NoButton,
    ) -> QMessageBox.StandardButton:
        return cls._show_message(cls.Icon.Critical, parent, title, text, buttons, defaultButton)
