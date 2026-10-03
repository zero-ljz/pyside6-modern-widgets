from __future__ import annotations

import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QMessageBox, QPushButton

from pyside6_modern_widgets import DARK_THEME, LIGHT_THEME, ModernMessageBox, ModernPushButton
from pyside6_modern_widgets.theme import DEFAULT_METRICS

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


def test_translucent_message_box_keeps_its_background_painted():
    box = ModernMessageBox(text="Pixel test", buttons=Button.Ok, theme=LIGHT_THEME)
    box.show()
    _APP.processEvents()
    try:
        if box._surface_policy.opaque_surface:
            pytest.skip("This platform uses an opaque message-box surface")
        assert box.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert box._background_frame.isVisible()
        frame = box._background_frame
        pixel = frame.grab().toImage().pixelColor(frame.width() - 10, frame.height() - 10)
        assert pixel == QColor(LIGHT_THEME.surface_alternate)
    finally:
        _dispose(box)


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


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
@pytest.mark.parametrize("default", [False, True])
@pytest.mark.parametrize("enabled", [False, True])
def test_standard_buttons_use_modern_painting_and_follow_theme(theme, default, enabled):
    theme = replace(theme, accent="#197F64")
    box = ModernMessageBox(buttons=Button.Save | Button.Cancel, theme=theme)
    button = box.button(Button.Save)
    reference = ModernPushButton(theme=theme)
    try:
        assert type(button) is QPushButton
        for widget in (button, reference):
            widget.setText("")
            widget.setDefault(default)
            widget.setEnabled(enabled)
            widget.setFixedSize(100, 32)
        expected = theme.accent if default else theme.surface
        if not enabled:
            expected = theme.border if default else theme.surface_alternate
        for widget in (button, reference):
            assert widget.grab().toImage().pixelColor(50, 24) == QColor(expected)
        box.setTheme(replace(theme, surface="#A6C8BD", accent="#894A66"))
        if enabled:
            assert button.grab().toImage().pixelColor(50, 24) == QColor(
                "#894A66" if default else "#A6C8BD"
            )
        assert box.button(Button.Save) is button
        assert box.standardButton(button) == Button.Save
    finally:
        reference.deleteLater()
        _dispose(box)


def test_lazily_created_standard_custom_and_details_buttons_use_modern_painting():
    box = ModernMessageBox(theme=LIGHT_THEME)
    box.show()
    _APP.processEvents()
    try:
        box.setStandardButtons(Button.Save | Button.Cancel)
        custom = QPushButton("Custom")
        box.addButton(custom, Role.ActionRole)
        box.setDetailedText("Diagnostic information")
        _APP.processEvents()
        details = next(
            button
            for button in box.buttons()
            if button is not custom and box.standardButton(button) == Button.NoButton
        )
        for button in (box.button(Button.Save), box.button(Button.Cancel), custom, details):
            button.setEnabled(False)
            button.resize(100, 32)
            assert button.grab().toImage().pixelColor(50, 24) == QColor(
                LIGHT_THEME.border if button.isDefault() else LIGHT_THEME.surface_alternate
            )
            button.setEnabled(True)
        assert box.buttonRole(custom) == Role.ActionRole
        details.click()
        assert box.isVisible()
        details.click()
        assert box.isVisible()
        box.removeButton(custom)
        assert custom not in box.buttons()
        box.setStandardButtons(Button.Yes | Button.No)
        _APP.processEvents()
        yes = box.button(Button.Yes)
        box.setDefaultButton(yes)
        QTest.keyClick(yes, Qt.Key.Key_Return)
        assert box.clickedButton() is yes
        assert box.result() == Button.Yes.value
    finally:
        _dispose(box)


def test_message_button_preserves_custom_modern_button_theme_and_metrics():
    box = ModernMessageBox(theme=LIGHT_THEME, metrics=replace(DEFAULT_METRICS, control_radius=0))
    custom = ModernPushButton("Custom", theme=DARK_THEME)
    original_style = custom.style()
    box.addButton(custom, Role.ActionRole)
    try:
        box.setStandardButtons(Button.Save | Button.Cancel)
        button = box.button(Button.Cancel)
        button.setEnabled(False)
        button.resize(100, 32)
        image = button.grab().toImage()
        assert image.pixelColor(1, 1) == QColor(LIGHT_THEME.surface_alternate)
        custom.ensurePolished()
        assert custom.style() is original_style
        assert custom.theme() == DARK_THEME
    finally:
        _dispose(box)


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
        outcomes.append((box.result(), list(events)))
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


@pytest.mark.parametrize("remove_first", [False, True])
def test_deleted_default_button_can_be_replaced_like_qt(remove_first):
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        box.setStandardButtons(Button.Yes | Button.Cancel)
        box.setDefaultButton(Button.Yes)
        box.show()
        _APP.processEvents()
        try:
            deleted_button = box.button(Button.Yes)
            if remove_first:
                box.removeButton(deleted_button)
            deleted_button.deleteLater()
            QCoreApplication.sendPostedEvents(deleted_button, QEvent.Type.DeferredDelete)
            _APP.processEvents()
            # Qt 6.8's getter is unsafe after direct deletion. Use removeButton
            # before destruction when querying the remaining default selection.
            if remove_first:
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


@pytest.mark.parametrize("buttons", [Button.Yes | Button.No, Button.Ok | Button.Cancel])
@pytest.mark.parametrize("explicit_default", [False, True])
@pytest.mark.parametrize("details", [False, True])
def test_enter_uses_native_default_button_with_modern_chrome(buttons, explicit_default, details):
    outcomes = []
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        box.setText("Continue?")
        box.setStandardButtons(buttons)
        if details:
            box.setDetailedText("Additional information")
        if explicit_default:
            box.setDefaultButton(Button.No if buttons & Button.No else Button.Cancel)
        box.show()
        box.activateWindow()
        QTest.qWait(50)
        try:
            focus = _APP.focusWidget()
            assert focus in box.buttons()
            events = _observe(box)
            QTest.keyClick(focus, Qt.Key.Key_Return)
            outcomes.append((box.isVisible(), box.result(), list(events)))
        finally:
            _dispose(box)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("action", ["escape", "close"])
def test_removing_and_deleting_escape_button_keeps_native_close_behavior(action):
    outcomes = []
    for box_class in (QMessageBox, ModernMessageBox):
        box = box_class()
        box.setStandardButtons(Button.Yes | Button.Cancel)
        box.setEscapeButton(Button.Yes)
        removed = box.button(Button.Yes)
        box.removeButton(removed)
        removed.deleteLater()
        QCoreApplication.sendPostedEvents(removed, QEvent.Type.DeferredDelete)
        box.show()
        _APP.processEvents()
        try:
            if action == "escape":
                QTest.keyClick(box, Qt.Key.Key_Escape)
            else:
                box.close()
            outcomes.append((box.isVisible(), box.result()))
        finally:
            _dispose(box)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("method", ["information", "question", "warning", "critical"])
def test_convenience_methods_create_modern_box_with_native_keyboard_behavior(method):
    observations = []

    def confirm():
        box = _APP.activeModalWidget()
        observations.append(isinstance(box, ModernMessageBox))
        QTest.keyClick(box, Qt.Key.Key_Return)

    # Bound the nested event loop if default-button handling regresses.
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(lambda: _APP.activeModalWidget().reject())
    timeout.start(2000)
    QTimer.singleShot(0, confirm)
    try:
        result = getattr(ModernMessageBox, method)(
            None, "Confirm", "Continue?", Button.Yes | Button.No
        )
        assert observations == [True]
        assert result == Button.Yes
    finally:
        timeout.stop()


def test_native_details_and_checkbox_layout_stays_below_title_bar():
    box = ModernMessageBox(QMessageBox.Icon.Warning, "Confirm", "Continue?", Button.Yes | Button.No)
    check_box = QCheckBox("Remember my choice")
    box.setInformativeText("Additional context")
    box.setCheckBox(check_box)
    box.setDetailedText("Diagnostic information")
    box.show()
    _APP.processEvents()
    try:
        details_button = next(
            button for button in box.buttons() if box.standardButton(button) == Button.NoButton
        )
        original_height = box.height()
        details_button.click()
        _APP.processEvents()
        assert box.isVisible()
        assert box.height() > original_height
        check_box.click()
        assert box.checkBox().isChecked()
        for widget in [check_box, *box.buttons(), box.findChild(QLabel, "qt_msgbox_label")]:
            position = widget.mapTo(box, widget.rect().topLeft())
            assert position.y() >= box._title_bar.height()
            assert position.y() + widget.height() <= box.height()
        details_button.click()
        _APP.processEvents()
        assert box.height() == original_height
        assert box.checkBox().isChecked()
    finally:
        _dispose(box)
