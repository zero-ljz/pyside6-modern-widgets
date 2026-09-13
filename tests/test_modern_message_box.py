from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from pyside6_modern_widgets import ModernMessageBox

_APP = QApplication.instance() or QApplication([])
Button = QMessageBox.StandardButton
Role = QMessageBox.ButtonRole


def _observe(box):
    events = []
    for name in ("buttonClicked", "accepted", "rejected", "finished"):
        getattr(box, name).connect(
            lambda *args, name=name: events.append((name, box.isVisible(), box.result()))
        )
    return events


def _dispose(box):
    box.blockSignals(True)
    box.done(0)
    box.deleteLater()


@pytest.mark.parametrize(
    "button", [Button.Ok, Button.Yes, Button.No, Button.Cancel, Button.Discard]
)
def test_standard_button_results_and_signal_order_match_qt(button):
    outcomes = []
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        box.setStandardButtons(button | Button.Close)
        events = _observe(box)
        box.show()
        _APP.processEvents()
        box.button(button).click()
        outcomes.append((box.result(), box.isVisible(), list(events)))
        assert box.clickedButton() is box.button(button)
        _dispose(box)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize(
    "role",
    [
        Role.AcceptRole,
        Role.YesRole,
        Role.RejectRole,
        Role.NoRole,
        Role.ActionRole,
        Role.HelpRole,
        Role.ApplyRole,
        Role.ResetRole,
        Role.DestructiveRole,
    ],
)
def test_custom_button_roles_emit_the_same_completion_signals_as_qt(role):
    outcomes = []
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        button = box.addButton("Custom", role)
        events = _observe(box)
        box.show()
        _APP.processEvents()
        button.click()
        assert box.clickedButton() is button
        assert not box.isVisible()
        # Custom button return codes are owned by each message-box implementation.
        outcomes.append([(name, visible) for name, visible, _result in events])
        assert events[-1][2] == box.result()
        _dispose(box)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("action", ["escape", "close"])
@pytest.mark.parametrize(
    "buttons",
    [
        Button.Ok,
        Button.Save | Button.Discard,
        Button.Save | Button.Discard | Button.Cancel,
        Button.Yes | Button.No,
        Button.Retry | Button.Abort | Button.Ignore,
    ],
)
def test_escape_and_window_close_match_qt(buttons, action):
    outcomes = []
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        box.setStandardButtons(buttons)
        events = _observe(box)
        box.show()
        _APP.processEvents()
        if action == "escape":
            QTest.keyClick(box, Qt.Key.Key_Escape)
        else:
            box.close()
        clicked = box.clickedButton()
        outcomes.append(
            (
                box.isVisible(),
                box.result(),
                box.standardButton(clicked) if clicked else None,
                list(events),
            )
        )
        _dispose(box)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize(
    "roles",
    [
        (Role.AcceptRole,),
        (Role.RejectRole, Role.NoRole),
        (Role.RejectRole, Role.RejectRole, Role.NoRole),
        (Role.NoRole, Role.NoRole),
    ],
)
def test_escape_infers_a_unique_custom_button_by_role(roles):
    outcomes = []
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        buttons = [box.addButton(str(index), role) for index, role in enumerate(roles)]
        events = _observe(box)
        box.show()
        _APP.processEvents()
        QTest.keyClick(box, Qt.Key.Key_Escape)
        clicked = box.clickedButton()
        outcomes.append(
            (
                box.isVisible(),
                buttons.index(clicked) if clicked else None,
                [name for name, _visible, _result in events],
            )
        )
        _dispose(box)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("enabled", [True, False])
def test_explicit_escape_button_is_respected(enabled):
    outcomes = []
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        box.setStandardButtons(Button.Save | Button.Discard)
        box.setEscapeButton(Button.Save)
        box.button(Button.Save).setEnabled(enabled)
        box.show()
        _APP.processEvents()
        QTest.keyClick(box, Qt.Key.Key_Escape)
        outcomes.append((box.isVisible(), box.result()))
        _dispose(box)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("action", ["accept", "reject", "done"])
def test_programmatic_completion_still_uses_qdialog_codes(action):
    outcomes = []
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        box.setStandardButtons(Button.Yes | Button.No)
        box.show()
        _APP.processEvents()
        events = _observe(box)
        if action == "done":
            box.done(Button.Yes.value)
        else:
            getattr(box, action)()
        outcomes.append((box.result(), list(events)))
        _dispose(box)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("button", [Button.Yes, Button.No])
def test_modal_exec_preserves_button_result_and_completion_signals(button):
    outcomes = []
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        box.setStandardButtons(Button.Yes | Button.No)
        events = _observe(box)
        QTimer.singleShot(0, box.button(button).click)
        result = box.exec()
        assert result == button.value
        outcomes.append(list(events))
        _dispose(box)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("read_before_replacing", [False, True])
def test_deleted_default_button_can_be_replaced_like_qt(read_before_replacing):
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        box.setStandardButtons(Button.Yes | Button.Cancel)
        box.setDefaultButton(Button.Yes)
        box.show()
        _APP.processEvents()
        try:
            deleted_button = box.button(Button.Yes)
            deleted_button.deleteLater()
            QCoreApplication.sendPostedEvents(deleted_button, QEvent.Type.DeferredDelete)
            _APP.processEvents()
            # Qt 6.8's native getter retains a dangling pointer after direct
            # deletion; only compare the replacement behavior with QMessageBox.
            if read_before_replacing and isinstance(box, ModernMessageBox):
                assert box.defaultButton() is None
            box.setDefaultButton(Button.Cancel)
            assert box.defaultButton() is box.button(Button.Cancel)
            assert box.defaultButton().isDefault()
            QTest.keyClick(box, Qt.Key.Key_Return)
            assert not box.isVisible()
            assert box.clickedButton() is box.button(Button.Cancel)
            assert box.result() == Button.Cancel.value
        finally:
            _dispose(box)
