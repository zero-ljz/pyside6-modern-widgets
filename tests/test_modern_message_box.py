from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QMessageBox, QPushButton

from pyside6_modern_widgets import LIGHT_THEME, ModernDialog, ModernMessageBox

_APP = QApplication.instance() or QApplication([])


def _application() -> QApplication:
    return _APP


def test_modern_message_box_preserves_common_message_properties() -> None:
    box = ModernMessageBox(
        ModernMessageBox.Icon.Warning,
        "Warning",
        "Primary text",
        ModernMessageBox.StandardButton.Ok | ModernMessageBox.StandardButton.Cancel,
        theme=LIGHT_THEME,
    )
    box.setInformativeText("Informative text")

    assert isinstance(box, ModernDialog)
    assert not isinstance(box, QMessageBox)
    assert box.windowTitle() == "Warning"
    assert box.text() == "Primary text"
    assert box.informativeText() == "Informative text"
    assert box.icon() == ModernMessageBox.Icon.Warning
    assert not box.iconPixmap().isNull()
    assert box.standardButtons() == (
        ModernMessageBox.StandardButton.Ok | ModernMessageBox.StandardButton.Cancel
    )


def test_modern_message_box_inherits_shared_surface_policy(monkeypatch) -> None:
    from pyside6_modern_widgets import modern_dialog
    from pyside6_modern_widgets._window_chrome import WindowSurfacePolicy

    policy = WindowSurfacePolicy(opaque_surface=True, native_corners=False)
    monkeypatch.setattr(modern_dialog, "current_window_surface_policy", lambda: policy)

    box = ModernMessageBox(parent=None, theme=LIGHT_THEME)

    assert box._surface_policy is policy
    assert box.testAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
    assert not box.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert box._background_frame._corner_radius == 0
    assert box._chrome_overlay._corner_radius == 0


def test_modern_message_box_exec_returns_the_clicked_standard_button() -> None:
    box = ModernMessageBox(
        ModernMessageBox.Icon.Question,
        "Question",
        "Continue?",
        ModernMessageBox.StandardButton.Yes | ModernMessageBox.StandardButton.No,
        theme=LIGHT_THEME,
    )
    yes_button = box.button(ModernMessageBox.StandardButton.Yes)
    assert yes_button is not None
    clicked = QSignalSpy(box.buttonClicked)
    QTimer.singleShot(0, yes_button.click)

    result = box.exec()

    assert result == ModernMessageBox.StandardButton.Yes.value
    assert box.clickedButton() is yes_button
    assert box.standardButton(yes_button) == ModernMessageBox.StandardButton.Yes
    assert clicked.count() == 1


def test_modern_message_box_escape_uses_configured_button() -> None:
    box = ModernMessageBox(
        ModernMessageBox.Icon.Question,
        "Question",
        "Continue?",
        ModernMessageBox.StandardButton.Yes | ModernMessageBox.StandardButton.No,
        theme=LIGHT_THEME,
    )
    box.setEscapeButton(ModernMessageBox.StandardButton.No)
    QTimer.singleShot(0, lambda: QTest.keyClick(box, Qt.Key.Key_Escape))

    result = box.exec()

    assert result == ModernMessageBox.StandardButton.No.value
    assert box.clickedButton() is box.button(ModernMessageBox.StandardButton.No)


def test_modern_message_box_supports_details_and_a_checkbox() -> None:
    box = ModernMessageBox(parent=None, theme=LIGHT_THEME)
    check_box = QCheckBox("Do not ask again")
    box.setCheckBox(check_box)
    box.setDetailedText("Traceback details")

    assert box.checkBox() is check_box
    assert box.detailedText() == "Traceback details"
    assert box._details_button.isVisibleTo(box)
    assert not box._details_editor.isVisibleTo(box)

    box._details_button.click()

    assert box._details_editor.isVisibleTo(box)


def test_modern_message_box_supports_custom_buttons() -> None:
    box = ModernMessageBox(parent=None, theme=LIGHT_THEME)
    custom = QPushButton("Inspect")

    returned = box.addButton(custom, ModernMessageBox.ButtonRole.ActionRole)
    custom.click()

    assert returned is custom
    assert box.clickedButton() is custom
    assert box.result() == 2
    assert box.buttonRole(custom) == ModernMessageBox.ButtonRole.ActionRole

    box.removeButton(custom)
    assert custom not in box.buttons()


def test_modern_message_box_sets_default_button() -> None:
    box = ModernMessageBox(
        ModernMessageBox.Icon.Information,
        "Saved",
        "The file was saved.",
        ModernMessageBox.StandardButton.Ok | ModernMessageBox.StandardButton.Cancel,
        theme=LIGHT_THEME,
    )

    box.setDefaultButton(ModernMessageBox.StandardButton.Cancel)

    assert box.defaultButton() is box.button(ModernMessageBox.StandardButton.Cancel)
    assert box.defaultButton() is not None
    assert box.defaultButton().isDefault()


def test_modern_message_box_convenience_method_returns_standard_button(monkeypatch) -> None:
    observed: list[ModernMessageBox] = []

    def execute(box: ModernMessageBox) -> int:
        observed.append(box)
        return ModernMessageBox.StandardButton.Ok.value

    monkeypatch.setattr(ModernMessageBox, "exec", execute)

    result = ModernMessageBox.information(
        None,
        "Saved",
        "The file was saved.",
    )

    assert result == ModernMessageBox.StandardButton.Ok
    assert observed[0].icon() == ModernMessageBox.Icon.Information
    assert observed[0].standardButtons() == ModernMessageBox.StandardButton.Ok


def test_modern_message_box_adds_ok_when_shown_without_buttons() -> None:
    box = ModernMessageBox(parent=None, theme=LIGHT_THEME)
    box.show()
    _application().processEvents()

    assert box.standardButtons() == ModernMessageBox.StandardButton.Ok
