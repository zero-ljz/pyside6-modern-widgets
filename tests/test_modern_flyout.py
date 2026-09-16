from __future__ import annotations

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    FlyoutPlacement,
    ModernComboBox,
    ModernFlyout,
    ModernMenu,
    ModernWindow,
    ThemeMode,
)
from pyside6_modern_widgets.modern_flyout import _popup_geometry

_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def panel(theme_manager_instance):
    window = ModernWindow()
    body = QWidget()
    layout = QVBoxLayout(body)
    anchor = QPushButton("Open")
    layout.addWidget(anchor)
    layout.addStretch()
    window.setCentralWidget(body)
    window.resize(440, 300)
    window.move(40, 40)
    window.show()
    window.activateWindow()
    _APP.processEvents()
    anchor.setFocus()
    flyout = ModernFlyout(window)
    content = QWidget()
    form = QVBoxLayout(content)
    field = QLineEdit()
    combo = ModernComboBox()
    combo.addItems(["One", "Two"])
    button = QPushButton("Apply")
    for widget in (field, combo, button):
        form.addWidget(widget)
    flyout.setContentWidget(content)
    yield window, anchor, flyout, field, combo, button
    flyout.close()
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    _APP.processEvents()


@pytest.mark.parametrize("placement", list(FlyoutPlacement))
def test_requested_placement_and_gap(placement):
    anchor = QRect(400, 400, 100, 30)
    rect = _popup_geometry(anchor, QSize(180, 100), QRect(0, 0, 1000, 1000), placement, 8, False)
    if placement == FlyoutPlacement.BOTTOM:
        assert rect.top() == anchor.bottom() + 9
    elif placement == FlyoutPlacement.TOP:
        assert rect.bottom() == anchor.top() - 9
    elif placement == FlyoutPlacement.LEFT:
        assert rect.right() == anchor.left() - 9
    else:
        assert rect.left() == anchor.right() + 9
    assert not rect.intersects(anchor)


@pytest.mark.parametrize(
    "anchor,placement",
    [
        (QRect(-600, 450, 100, 30), FlyoutPlacement.BOTTOM),
        (QRect(-600, 10, 100, 30), FlyoutPlacement.TOP),
        (QRect(-990, 200, 100, 30), FlyoutPlacement.LEFT),
        (QRect(-110, 200, 100, 30), FlyoutPlacement.RIGHT),
    ],
)
def test_flip_at_screen_edges_with_negative_screen_origin(anchor, placement):
    screen = QRect(-1000, 0, 1000, 500)
    rect = _popup_geometry(anchor, QSize(180, 100), screen, placement, 8, False)
    assert screen.contains(rect)
    assert not rect.intersects(anchor)
    if placement == FlyoutPlacement.BOTTOM:
        assert rect.bottom() < anchor.top()
    elif placement == FlyoutPlacement.TOP:
        assert rect.top() > anchor.bottom()
    elif placement == FlyoutPlacement.LEFT:
        assert rect.left() > anchor.right()
    else:
        assert rect.right() < anchor.left()


def test_cross_axis_clamping_and_rtl():
    screen = QRect(0, 0, 800, 600)
    anchor = QRect(740, 100, 60, 30)
    rect = _popup_geometry(anchor, QSize(250, 120), screen, FlyoutPlacement.BOTTOM, 8, False)
    assert rect.top() == 138
    assert rect.right() == screen.right()
    anchor = QRect(300, 100, 100, 30)
    rect = _popup_geometry(anchor, QSize(250, 120), screen, FlyoutPlacement.BOTTOM, 8, True)
    assert rect.right() == anchor.right()


def test_open_keyboard_focus_escape_and_reuse(panel):
    _, anchor, flyout, field, combo, button = panel
    events = []
    flyout.opened.connect(lambda: events.append("open"))
    flyout.closed.connect(lambda: events.append("close"))
    flyout.popup(anchor)
    _APP.processEvents()
    assert flyout.isVisible()
    assert QApplication.activePopupWidget() is flyout
    assert field.hasFocus()
    QTest.keyClicks(field, "Saved text")
    QTest.keyClick(field, Qt.Key.Key_Tab)
    assert combo.hasFocus()
    QTest.keyClick(combo, Qt.Key.Key_Tab)
    assert button.hasFocus()
    QTest.keyClick(button, Qt.Key.Key_Escape)
    _APP.processEvents()
    assert not flyout.isVisible()
    assert anchor.hasFocus()
    flyout.close()
    assert events == ["open", "close"]
    flyout.popup(anchor, "top")
    assert field.text() == "Saved text"
    assert flyout.contentWidget() is field.parentWidget()
    assert events == ["open", "close", "open"]


def test_child_combo_owns_first_escape(panel):
    _, anchor, flyout, _, combo, _ = panel
    flyout.popup(anchor)
    combo.setFocus()
    combo.showPopup()
    _APP.processEvents()
    child_popup = combo.view().window()
    assert child_popup.isVisible()
    QTest.keyClick(child_popup, Qt.Key.Key_Escape)
    _APP.processEvents()
    assert not child_popup.isVisible()
    assert flyout.isVisible()
    assert QApplication.activePopupWidget() is flyout
    QTest.keyClick(combo, Qt.Key.Key_Escape)
    assert not flyout.isVisible()


def test_child_menu_selection_keeps_flyout_open(panel):
    _, anchor, flyout, _, _, button = panel
    menu = ModernMenu(button)
    action = menu.addAction("Choose")
    selected = []
    action.triggered.connect(lambda: selected.append(True))
    button.setMenu(menu)
    flyout.popup(anchor)
    menu.popup(button.mapToGlobal(QPoint(0, button.height())))
    _APP.processEvents()
    menu.setActiveAction(action)
    QTest.keyClick(menu, Qt.Key.Key_Return)
    _APP.processEvents()
    assert selected == [True]
    assert flyout.isVisible()


def test_inside_click_and_outside_click(panel):
    _, anchor, flyout, field, _, _ = panel
    flyout.popup(anchor)
    QTest.mouseClick(field, Qt.MouseButton.LeftButton)
    assert flyout.isVisible()
    # Native popup grabs deliver outside positions to the popup itself.
    QTest.mouseClick(flyout, Qt.MouseButton.LeftButton, pos=QPoint(-10, -10))
    _APP.processEvents()
    assert not flyout.isVisible()


def test_anchor_move_hide_and_destroy(panel):
    window, anchor, flyout, *_ = panel
    flyout.popup(anchor)
    initial = flyout.pos()
    window.move(window.pos() + QPoint(20, 15))
    QTest.qWait(20)
    assert flyout.pos() == initial + QPoint(20, 15)
    anchor.hide()
    assert not flyout.isVisible()
    anchor.show()
    flyout.popup(anchor)
    anchor.deleteLater()
    QCoreApplication.sendPostedEvents(anchor, QEvent.Type.DeferredDelete)
    assert not flyout.isVisible()
    assert flyout.anchorWidget() is None


def test_local_and_global_theme_changes_while_open(panel, theme_manager_instance):
    window, anchor, flyout, field, *_ = panel
    window.setTheme(DARK_THEME)
    flyout.popup(anchor)
    assert flyout.theme() == DARK_THEME
    assert field.palette().color(QPalette.ColorRole.Base) == QColor(DARK_THEME.surface)
    window.setTheme(LIGHT_THEME)
    _APP.processEvents()
    assert flyout.theme() == LIGHT_THEME
    assert field.palette().color(QPalette.ColorRole.Base) == QColor(LIGHT_THEME.surface)
    flyout.setTheme(DARK_THEME)
    window.setTheme(None)
    theme_manager_instance.setMode(ThemeMode.LIGHT)
    assert flyout.theme() == DARK_THEME
    flyout.setTheme(None)
    assert flyout.theme() == LIGHT_THEME
    theme_manager_instance.setMode(ThemeMode.DARK)
    assert field.palette().color(QPalette.ColorRole.Base) == QColor(DARK_THEME.surface)


def test_large_content_scrolls_and_replacement_can_shrink(panel):
    _, anchor, flyout, *_ = panel
    content = QWidget()
    content.setMinimumSize(1200, 2000)
    flyout.setContentWidget(content)
    flyout.popup(anchor)
    _APP.processEvents()
    assert anchor.screen().availableGeometry().contains(flyout.geometry())
    scroll = flyout.findChild(QScrollArea)
    assert scroll.verticalScrollBar().maximum() > 0
    assert scroll.horizontalScrollBar().maximum() > 0
    previous_size = flyout.size()
    small = QPushButton("Small")
    flyout.setContentWidget(small)
    _APP.processEvents()
    assert flyout.width() < previous_size.width()
    assert flyout.height() < previous_size.height()
    assert not isValid(content)
    taken = flyout.takeContentWidget()
    assert taken is small
    assert taken.parentWidget() is None
    assert flyout.contentWidget() is None
    taken.deleteLater()


def test_invalid_arguments_leave_panel_usable(panel):
    _, anchor, flyout, field, *_ = panel
    for placement, gap in [("invalid", 8), ("top", -1)]:
        with pytest.raises(ValueError):
            flyout.popup(anchor, placement, gap=gap)
    with pytest.raises(ValueError):
        flyout.setContentWidget(flyout)
    flyout.popup(anchor)
    with pytest.raises(ValueError):
        flyout.popup(field)
    assert flyout.isVisible()


def test_tall_form_needs_only_vertical_scrolling(panel):
    _, anchor, flyout, *_ = panel
    content = QWidget()
    layout = QVBoxLayout(content)
    for index in range(80):
        layout.addWidget(QPushButton(f"Option {index}"))
    flyout.setContentWidget(content)
    flyout.popup(anchor)
    QTest.qWait(20)
    scroll = flyout.findChild(QScrollArea)
    assert scroll.verticalScrollBar().maximum() > 0
    assert scroll.horizontalScrollBar().maximum() == 0
