from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QPoint, QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPalette, QPixmap, QWheelEvent
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QMenu,
    QPushButton,
    QStyle,
    QStyleFactory,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)

from pyside6_modern_widgets import DARK_THEME, LIGHT_THEME, ModernDialog, ModernPushButton

_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def widgets(theme_manager_instance):
    owned = []

    def create(cls=ModernPushButton, *args, **kwargs):
        widget = cls(*args, **kwargs)
        owned.append(widget)
        if cls is QPushButton:
            style = QStyleFactory.create("Fusion")
            style.setParent(widget)
            widget.setStyle(style)
        return widget

    yield create
    for widget in reversed(owned):
        widget.close()
        widget.deleteLater()
    _APP.processEvents()


def solid_icon():
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor("#ED178D"))
    return QIcon(pixmap)


@pytest.mark.parametrize("kind", ["text", "icon", "icon_only", "empty", "menu", "flat", "default"])
@pytest.mark.parametrize("rtl", [False, True])
@pytest.mark.parametrize("point_size", [9, 16])
def test_fusion_geometry_and_size_hints(widgets, kind, rtl, point_size):
    buttons = [widgets(cls) for cls in (QPushButton, ModernPushButton)]
    options = []
    for button in buttons:
        button.setText("" if kind in ("empty", "icon_only") else "Save &document 文档")
        font = button.font()
        font.setPointSize(point_size)
        button.setFont(font)
        button.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        if kind in ("icon", "icon_only"):
            button.setIcon(solid_icon())
            button.setIconSize(QSize(24, 24))
        if kind == "menu":
            button.setMenu(QMenu(button))
        if kind == "flat":
            button.setFlat(True)
        if kind == "default":
            button.setDefault(True)
        button.ensurePolished()
        button.resize(button.sizeHint())
        option = QStyleOptionButton()
        button.initStyleOption(option)
        options.append(option)
    native, modern = buttons
    assert modern.sizeHint() == native.sizeHint()
    assert modern.minimumSizeHint() == native.minimumSizeHint()
    assert modern.sizePolicy() == native.sizePolicy()
    assert modern.focusPolicy() == native.focusPolicy()
    assert modern.iconSize() == native.iconSize()
    for element in (QStyle.SE_PushButtonContents, QStyle.SE_PushButtonFocusRect):
        assert modern.style().subElementRect(element, options[1], modern) == (
            native.style().subElementRect(element, options[0], native)
        )


@pytest.mark.parametrize("rtl", [False, True])
@pytest.mark.parametrize("menu", [False, True])
def test_visible_icon_bounds_match_fusion(widgets, rtl, menu):
    bounds = []
    for cls in (QPushButton, ModernPushButton):
        button = widgets(cls, solid_icon(), "&Open")
        button.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        if menu:
            button.setMenu(QMenu(button))
        button.resize(button.sizeHint())
        image = button.grab().toImage()
        pixels = [
            (x, y)
            for x in range(image.width())
            for y in range(image.height())
            if image.pixelColor(x, y) == QColor("#ED178D")
        ]
        assert pixels
        bounds.append(
            (
                min(x for x, y in pixels),
                min(y for x, y in pixels),
                max(x for x, y in pixels),
                max(y for x, y in pixels),
            )
        )
    assert bounds[0] == bounds[1]


def signal_trace(button):
    trace = []
    button.pressed.connect(lambda: trace.append("pressed"))
    button.released.connect(lambda: trace.append("released"))
    button.clicked.connect(lambda value: trace.append(("clicked", value)))
    button.toggled.connect(lambda value: trace.append(("toggled", value)))
    return trace


def test_native_mouse_keyboard_wheel_and_signal_order(widgets):
    results = []
    for cls in (QPushButton, ModernPushButton):
        button = widgets(cls, "Button")
        button.setCheckable(True)
        button.resize(button.sizeHint())
        button.show()
        _APP.processEvents()
        trace = signal_trace(button)
        QTest.mouseClick(button, Qt.LeftButton)
        assert button.isChecked()
        QTest.keyClick(button, Qt.Key_Space)
        assert not button.isChecked()
        # Releasing outside cancels the activation; reentering while held works.
        QTest.mousePress(button, Qt.LeftButton)
        QTest.mouseMove(button, QPoint(-10, -10))
        QTest.mouseRelease(button, Qt.LeftButton, pos=QPoint(-10, -10))
        assert not button.isChecked()
        before = trace.copy()
        wheel = QWheelEvent(
            QPointF(5, 5),
            QPointF(button.mapToGlobal(QPoint(5, 5))),
            QPoint(),
            QPoint(0, 120),
            Qt.NoButton,
            Qt.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        _APP.sendEvent(button, wheel)
        QTest.keyClick(button, Qt.Key_Return)  # Non-dialog, non-default button.
        assert trace == before
        button.setEnabled(False)
        QTest.mouseClick(button, Qt.LeftButton)
        QTest.keyClick(button, Qt.Key_Space)
        assert trace == before
        results.append(trace)
        button.hide()
    assert results[0] == results[1]
    assert results[1][:4] == ["pressed", ("toggled", True), "released", ("clicked", True)]


def test_native_constructor_forms_and_keyword_properties(widgets):
    parent = widgets(QWidget)
    icon = solid_icon()
    for button in (
        widgets(ModernPushButton, parent),
        widgets(ModernPushButton, "Text", parent),
        widgets(ModernPushButton, icon, "Text", parent),
        widgets(ModernPushButton, parent=parent, text="Text", checkable=True, checked=True),
    ):
        assert isinstance(button, QPushButton)
        assert button.parentWidget() is parent
    with pytest.raises(TypeError, match="theme must be"):
        widgets(ModernPushButton, theme="dark")
    with pytest.raises(TypeError, match="theme must be"):
        button.setTheme("dark")


def test_dialog_default_and_auto_default_activation_matches_native(widgets):
    results = []
    for cls in (QPushButton, ModernPushButton):
        dialog = widgets(QDialog)
        layout = QVBoxLayout(dialog)
        edit = QLineEdit(dialog)
        first = cls("Save", dialog)
        second = cls("Cancel", dialog)
        for widget in (edit, first, second):
            layout.addWidget(widget)
        first.setDefault(True)
        assert first.autoDefault() and second.autoDefault()
        traces = [signal_trace(first), signal_trace(second)]
        dialog.show()
        dialog.activateWindow()
        edit.setFocus(Qt.TabFocusReason)
        _APP.processEvents()
        QTest.keyClick(edit, Qt.Key_Return)
        second.setFocus(Qt.TabFocusReason)
        _APP.processEvents()
        QTest.keyClick(second, Qt.Key_Return)
        results.append(traces)
        dialog.hide()
    assert results[0] == results[1]
    assert all(trace == ["pressed", "released", ("clicked", False)] for trace in results[1])


def test_menu_activation_retains_native_signals(widgets):
    results = []
    for cls in (QPushButton, ModernPushButton):
        button = widgets(cls, "Menu")
        menu = QMenu(button)
        action = menu.addAction("Open")
        triggered = QSignalSpy(action.triggered)
        button.setMenu(menu)
        button.show()
        _APP.processEvents()
        trace = signal_trace(button)
        menu.aboutToShow.connect(lambda trace=trace: trace.append("menu"))
        action.triggered.connect(lambda checked=False, trace=trace: trace.append("action"))

        def choose(menu=menu, action=action):
            menu.setActiveAction(action)
            QTest.keyClick(menu, Qt.Key_Return)
            menu.close()

        # Start after Qt opens the popup: a timer armed before mouseClick can
        # fire during unrelated pending events in the full application suite.
        menu.aboutToShow.connect(lambda choose=choose: QTimer.singleShot(0, choose))
        QTest.mouseClick(button, Qt.LeftButton)
        assert triggered.count() or triggered.wait(1000)
        assert not menu.isVisible()
        assert "menu" in trace and "action" in trace
        results.append(trace)
        button.hide()
    assert results[0] == results[1]


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
def test_state_painting_and_system_accent(widgets, theme):
    button = widgets(theme=theme)
    button.resize(90, 28)
    palette = QPalette()
    palette.setColor(QPalette.Active, QPalette.Accent, QColor("#197F64"))
    palette.setColor(QPalette.Inactive, QPalette.Accent, QColor(theme.surface))
    button.setPalette(palette)
    # Inject render states to compare pixels without platform focus/hover timing.
    original = button.initStyleOption
    states = QStyle.State_Enabled

    def init(option):
        original(option)
        option.state = states

    button.initStyleOption = init

    def center():
        image = button.grab().toImage()
        return image.pixelColor(image.width() // 2, image.height() // 2)

    idle = center()
    assert idle == QColor(theme.surface)
    states |= QStyle.State_MouseOver
    hover = center()
    states |= QStyle.State_Sunken
    pressed = center()
    assert len({idle.rgba(), hover.rgba(), pressed.rgba()}) == 3
    states = QStyle.State_Enabled | QStyle.State_On
    assert center() == QColor("#197F64")
    button.setTheme(replace(theme, accent="#9944CC", on_accent="#FFFFFF"))
    assert center() == QColor("#9944CC")
    states = QStyle.State_On
    assert center() == QColor(theme.border)
    states = QStyle.State_Enabled
    no_focus = button.grab().toImage()
    states |= QStyle.State_HasFocus | QStyle.State_KeyboardFocusChange
    assert button.grab().toImage() != no_focus


def test_example_has_native_and_modern_button_pairs(widgets):
    from examples.navigation_view_example import ExampleWindow

    window = widgets(ExampleWindow)
    page = window._create_button_page()
    page.setParent(window)
    buttons = page.findChildren(QPushButton)
    modern = [button for button in buttons if isinstance(button, ModernPushButton)]
    native = [button for button in buttons if type(button) is QPushButton]
    assert len(modern) == len(native) == 8
    for a, b in zip(native, modern):
        assert a.text() == b.text()
        assert a.isCheckable() == b.isCheckable()
        assert a.isDefault() == b.isDefault()
        assert a.isFlat() == b.isFlat()
        assert (a.menu() is None) == (b.menu() is None)


@pytest.mark.parametrize("dialog_type", [QDialog, ModernDialog])
def test_dialog_example_button_roles_and_appearance(widgets, monkeypatch, dialog_type):
    from examples.navigation_view_example import ExampleWindow

    observed = []

    def inspect(dialog):
        button_box = dialog.findChild(QDialogButtonBox)
        buttons = button_box.buttons()
        expected_type = ModernPushButton if dialog_type is ModernDialog else QPushButton
        assert len(buttons) == 2
        assert all(type(button) is expected_type for button in buttons)
        roles = {button_box.buttonRole(button): button for button in buttons}
        assert set(roles) == {
            QDialogButtonBox.ButtonRole.AcceptRole,
            QDialogButtonBox.ButtonRole.RejectRole,
        }
        roles[QDialogButtonBox.ButtonRole.AcceptRole].click()
        assert dialog.result() == QDialog.DialogCode.Accepted
        roles[QDialogButtonBox.ButtonRole.RejectRole].click()
        assert dialog.result() == QDialog.DialogCode.Rejected
        observed.append(dialog)
        return dialog.result()

    monkeypatch.setattr(QDialog, "exec", inspect)
    window = widgets(ExampleWindow)
    window._show_dialog(dialog_type)
    assert len(observed) == 1
