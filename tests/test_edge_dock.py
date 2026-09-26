from __future__ import annotations

import sys

import pytest
from PySide6.QtCore import (
    QCoreApplication,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QRect,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QCursor, QEnterEvent, QIcon, QMouseEvent, QPainter, QPixmap
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QMenu, QVBoxLayout, QWidget
from shiboken6 import isValid

from pyside6_modern_widgets import (
    DockConfig,
    DockHandleMode,
    DockSide,
    EdgeDockController,
    ModernWindow,
)
from pyside6_modern_widgets.edge_dock import _edge_rect

_APP = QApplication.instance() or QApplication([])


def _two_color_icon():
    pixmap = QPixmap(24, 24)
    pixmap.fill(QColor("red"))
    painter = QPainter(pixmap)
    painter.fillRect(12, 0, 12, 24, QColor("blue"))
    painter.end()
    return QIcon(pixmap)


@pytest.mark.parametrize("side", list(DockSide)[1:])
def test_icon_handle_stays_upright_and_inside_each_edge(docked, side):
    window, previous, strip, _ = docked
    previous.detach()
    controller = EdgeDockController(
        window,
        DockConfig(
            animation_duration_ms=0,
            sides=tuple(list(DockSide)[1:]),
            handle_icon=_two_color_icon(),
            handle_mode=DockHandleMode.CLICK,
        ),
        drag_widget=strip,
    )
    controller.dock(side)
    controller.collapse()
    handle = controller._handle
    assert controller.isCollapsed()
    assert handle.size() == QSize(36, 36)
    area = window.screen().availableGeometry().adjusted(2, 2, -2, -2)
    assert area.contains(handle.geometry())
    assert getattr(handle.geometry(), side.value)() == getattr(area, side.value)()
    image = handle.grab().toImage()
    ratio = image.devicePixelRatio()
    assert image.pixelColor(int(10 * ratio), int(18 * ratio)) == QColor("red")
    assert image.pixelColor(int(26 * ratio), int(18 * ratio)) == QColor("blue")


def test_live_handle_updates_preserve_collapse_and_allow_strip_fallback(docked):
    window, controller, _, _ = docked
    controller.setHandleMode("click")
    controller.dock(DockSide.LEFT)
    controller.collapse()
    position = window.pos()
    events = []
    controller.collapsedChanged.connect(events.append)
    controller.setHandleIcon(_two_color_icon())
    controller.setHandleIconSize(32)
    controller.setHandlePadding(8)
    controller.setHandleToolTip("Restore notes")
    assert controller.handleIconSize() == 32
    assert controller.handlePadding() == 8
    assert controller.handleToolTip() == "Restore notes"
    assert controller._handle.toolTip() == "Restore notes"
    assert controller._handle.accessibleName() == "Restore notes"
    assert controller._handle.size() == QSize(48, 48)
    # Returned icons are values; caller mutation must not change the live icon.
    copy = controller.handleIcon()
    copy.swap(QIcon())
    assert not controller.handleIcon().isNull()
    controller.setHandleIcon(None)
    assert controller.handleIcon().isNull()
    assert controller._handle.size() == QSize(6, 80)
    assert controller.isCollapsed() and not window.isVisible()
    assert controller._handle.isVisible()
    assert window.pos() == position
    assert events == []


@pytest.mark.parametrize("icon", [False, True])
@pytest.mark.parametrize("trigger", list(DockHandleMode))
def test_handle_restore_trigger_controls_hover_and_left_click(docked, trigger, icon):
    window, controller, _, _ = docked
    controller.setHandleMode(trigger)
    if icon:
        controller.setHandleIcon(_two_color_icon())
    controller.dock(DockSide.LEFT)
    controller.collapse()
    handle = controller._handle
    point = QPointF(handle.rect().center())
    QApplication.sendEvent(handle, QEnterEvent(point, point, point))
    if trigger == DockHandleMode.HOVER_OR_CLICK:
        assert window.isVisible()
        controller.collapse()
    else:
        assert controller.isCollapsed()
        assert not window.isVisible()
    QTest.mouseClick(handle, Qt.RightButton)
    assert controller.isCollapsed()
    QTest.mouseClick(handle, Qt.LeftButton)
    assert window.isVisible()
    assert not controller.isCollapsed()
    assert not handle.isVisible()


def test_switching_trigger_while_collapsed_applies_to_next_entry(docked):
    _, controller, _, _ = docked
    controller.setHandleMode("click")
    controller.dock(DockSide.LEFT)
    controller.collapse()
    controller.setHandleMode("hover_or_click")
    assert controller.handleMode() == DockHandleMode.HOVER_OR_CLICK
    point = QPointF(controller._handle.rect().center())
    QApplication.sendEvent(controller._handle, QEnterEvent(point, point, point))
    assert not controller.isCollapsed()


@pytest.mark.parametrize(
    "kwargs", [{"handle_icon_size": 0}, {"handle_padding": -1}, {"handle_mode": "invalid"}]
)
def test_invalid_handle_config(kwargs):
    with pytest.raises(ValueError):
        DockConfig(**kwargs)


def test_invalid_handle_updates_are_atomic_and_detach_makes_them_inert(docked):
    _, controller, _, _ = docked
    controller.setHandleMode("click")
    controller.setHandleIcon(_two_color_icon())
    controller.dock(DockSide.LEFT)
    controller.collapse()
    for setter, value in (
        (controller.setHandleIconSize, 0),
        (controller.setHandlePadding, -1),
        (controller.setHandleMode, "invalid"),
    ):
        with pytest.raises(ValueError):
            setter(value)
    assert controller._handle.size() == QSize(36, 36)
    assert controller.handleMode() == DockHandleMode.CLICK
    controller.detach()
    controller.setHandleIcon(None)
    controller.setHandleIconSize(48)
    controller.setHandlePadding(12)
    controller.setHandleToolTip("ignored")
    controller.setHandleMode("hover_or_click")
    assert not controller.handleIcon().isNull()
    assert controller.handleIconSize() == 24
    assert controller.handlePadding() == 6
    assert controller.handleToolTip() == ""
    assert controller.handleMode() == DockHandleMode.CLICK


def test_icon_handle_shrinks_to_small_work_area(docked, monkeypatch):
    _, controller, _, _ = docked
    area = QRect(-500, -300, 30, 26)

    class Screen:
        def availableGeometry(self):
            return area

    monkeypatch.setattr(controller, "_screen", lambda: Screen())
    controller.setHandleIcon(_two_color_icon())
    controller.setHandleMode("click")
    controller.dock(DockSide.LEFT)
    controller.collapse()
    assert area.adjusted(2, 2, -2, -2).contains(controller._handle.geometry())
    assert not controller._handle.grab().isNull()


@pytest.fixture
def docked(monkeypatch, theme_manager_instance):
    window = QWidget(None, Qt.WindowType.FramelessWindowHint)
    window.resize(240, 160)
    window.move(250, 250)
    layout = QVBoxLayout(window)
    strip = QLabel("Drag")
    field = QLineEdit("select this text")
    layout.addWidget(strip)
    layout.addWidget(field)
    controller = EdgeDockController(
        window, DockConfig(animation_duration_ms=0, hide_delay_ms=30), drag_widget=strip
    )
    window.show()
    _APP.processEvents()
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: QPoint(10000, 10000)))
    yield window, controller, strip, field
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    _APP.processEvents()


def _mouse(widget, kind, local, global_pos, button, buttons):
    event = QMouseEvent(kind, QPointF(local), QPointF(global_pos), button, buttons, Qt.NoModifier)
    QApplication.sendEvent(widget, event)


def _drag(widget, delta):
    local = widget.rect().center()
    start = widget.mapToGlobal(local)
    _mouse(widget, QEvent.Type.MouseButtonPress, local, start, Qt.LeftButton, Qt.LeftButton)
    _mouse(widget, QEvent.Type.MouseMove, local + delta, start + delta, Qt.NoButton, Qt.LeftButton)
    _mouse(widget, QEvent.Type.MouseButtonRelease, local, start + delta, Qt.LeftButton, Qt.NoButton)


@pytest.mark.parametrize("side", list(DockSide)[1:])
@pytest.mark.parametrize("area", [QRect(0, 0, 1920, 1040), QRect(-1920, -200, 1920, 1040)])
def test_edge_geometry_uses_work_area_and_inclusive_right_bottom(side, area):
    rect = _edge_rect(QRect(-3000, -4000, 240, 160), area, side, 2)
    inside = area.adjusted(2, 2, -2, -2)
    assert inside.contains(rect)
    coordinate = {
        DockSide.LEFT: "left",
        DockSide.RIGHT: "right",
        DockSide.TOP: "top",
        DockSide.BOTTOM: "bottom",
    }[side]
    assert getattr(rect, coordinate)() == getattr(inside, coordinate)()


def test_oversize_window_keeps_top_left_reachable():
    assert _edge_rect(
        QRect(5, 5, 2000, 2000), QRect(-800, 0, 800, 600), DockSide.RIGHT, 2
    ).topLeft() == QPoint(-798, 2)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"hide_delay_ms": -1},
        {"handle_width": 0},
        {"animation_duration_ms": -1},
        {"dock_distance": -1},
        {"sides": ()},
        {"sides": (DockSide.NONE,)},
    ],
)
def test_invalid_config(kwargs):
    with pytest.raises(ValueError):
        DockConfig(**kwargs)


def test_target_and_drag_surface_validation(docked):
    window, _, _, field = docked
    with pytest.raises(ValueError, match="top-level"):
        EdgeDockController(field)
    other = QWidget()
    try:
        with pytest.raises(ValueError, match="belong"):
            EdgeDockController(window, drag_widget=other)
    finally:
        other.deleteLater()


def test_snap_selects_nearest_edge_and_respects_disabled_bottom(docked):
    window, controller, _, _ = docked
    area = window.screen().availableGeometry()
    window.move(area.left() + 25, area.top() + 5)
    controller.snap()
    assert controller.dockSide() == DockSide.TOP
    assert window.frameGeometry().top() == area.top() + 2
    window.move(area.center().x() - 120, area.bottom() - window.height() + 1)
    controller.snap()
    assert controller.dockSide() == DockSide.NONE
    with pytest.raises(ValueError, match="not enabled"):
        controller.dock(DockSide.BOTTOM)


def test_screen_selection_uses_window_center_and_handles_negative_origins(docked, monkeypatch):
    window, controller, _, _ = docked
    area = QRect(-1600, -200, 1600, 1000)

    class SecondaryScreen:
        def availableGeometry(self):
            return area

    screen = SecondaryScreen()
    points = []

    def screen_at(point):
        points.append(QPoint(point))
        return screen

    monkeypatch.setattr(QApplication, "screenAt", staticmethod(screen_at))
    window.move(-1590, 100)
    center = window.frameGeometry().center()
    controller.snap()
    assert points[0] == center
    assert window.x() == -1598
    controller.collapse()
    assert area.contains(controller._handle.geometry())
    assert controller._handle.x() == -1598
    # Model a changed work area or a removed monitor's fallback screen.
    area = QRect(0, 0, 1000, 700)
    controller._schedule_refresh()
    _APP.processEvents()
    assert area.contains(controller._handle.geometry())
    controller.expand()
    assert area.contains(window.frameGeometry())


def test_drag_is_unclamped_until_release_then_recovers_offscreen_window(docked):
    window, controller, strip, _ = docked
    start = window.pos()
    local = strip.rect().center()
    pointer = strip.mapToGlobal(local)
    _mouse(strip, QEvent.Type.MouseButtonPress, local, pointer, Qt.LeftButton, Qt.LeftButton)
    _mouse(
        strip, QEvent.Type.MouseMove, local, pointer + QPoint(-1800, 0), Qt.NoButton, Qt.LeftButton
    )
    assert window.pos() == start + QPoint(-1800, 0)
    _mouse(
        strip,
        QEvent.Type.MouseButtonRelease,
        local,
        pointer + QPoint(-1800, 0),
        Qt.LeftButton,
        Qt.NoButton,
    )
    assert controller._press is None
    assert controller.dockSide() == DockSide.LEFT
    assert window.screen().availableGeometry().contains(window.frameGeometry())


@pytest.mark.parametrize("side", [DockSide.LEFT, DockSide.RIGHT, DockSide.TOP])
@pytest.mark.parametrize("overflow", [150, 1200])
def test_large_overflow_still_snaps_on_release(docked, side, overflow):
    window, controller, strip, _ = docked
    # Use an outer desktop edge; on a real multi-monitor desktop, crossing an
    # internal edge can legitimately land inside the neighboring display.
    screens = QApplication.screens()
    if side == DockSide.RIGHT:
        screen = max(screens, key=lambda screen: screen.availableGeometry().right())
    elif side == DockSide.LEFT:
        screen = min(screens, key=lambda screen: screen.availableGeometry().left())
    else:
        screen = min(screens, key=lambda screen: screen.availableGeometry().top())
    area = screen.availableGeometry()
    window.move(area.center() - window.rect().center())
    _APP.processEvents()
    destination = QPoint(window.pos())
    if side == DockSide.LEFT:
        destination.setX(area.left() - overflow)
    elif side == DockSide.RIGHT:
        destination.setX(area.right() - window.width() + 1 + overflow)
    else:
        destination.setY(area.top() - overflow)
    _drag(strip, destination - window.pos())
    assert controller.dockSide() == side
    assert area.contains(window.frameGeometry())
    expected = {
        DockSide.LEFT: area.left() + 2,
        DockSide.RIGHT: area.right() - 2,
        DockSide.TOP: area.top() + 2,
    }[side]
    assert getattr(window.frameGeometry(), side.value)() == expected


def test_disabled_bottom_recovers_without_docking(docked):
    window, controller, strip, _ = docked
    area = window.screen().availableGeometry()
    window.move(area.center().x() - window.width() // 2, area.center().y())
    _drag(strip, QPoint(0, area.height() * 2))
    assert controller.dockSide() == DockSide.NONE
    assert area.contains(window.frameGeometry())
    assert not controller._monitor.isActive()


def test_drag_onto_secondary_display_does_not_snap_back_to_primary(docked, monkeypatch):
    window, controller, strip, _ = docked
    primary = window.screen()
    area = QRect(-1920, 0, 1920, 1080)

    class SecondaryScreen:
        def availableGeometry(self):
            return area

    secondary = SecondaryScreen()
    monkeypatch.setattr(
        QApplication,
        "screenAt",
        staticmethod(lambda point: secondary if area.contains(point) else primary),
    )
    destination = QPoint(-1200, 250)
    _drag(strip, destination - window.pos())
    assert window.pos() == destination
    assert controller.dockSide() == DockSide.NONE


def test_click_does_not_move_and_drag_restores_cursor(docked):
    window, _, strip, _ = docked
    strip.setCursor(Qt.CrossCursor)
    start = window.pos()
    _drag(strip, QPoint(1, 1))
    assert window.pos() == start
    _drag(strip, QPoint(120, 30))
    assert strip.cursor().shape() == Qt.CrossCursor


def test_child_text_selection_does_not_drag_window(docked):
    window, _, _, field = docked
    start = window.pos()
    QTest.mouseClick(field, Qt.LeftButton)
    QTest.keyClick(field, Qt.Key_A, Qt.ControlModifier)
    assert field.selectedText() == "select this text"
    assert window.pos() == start


def test_propagated_child_press_is_not_used_as_a_drag(docked):
    window, previous, strip, _ = docked
    previous.detach()
    controller = EdgeDockController(window, DockConfig(animation_duration_ms=0))
    start = window.pos()
    # Labels ignore mouse presses, which Qt propagates up to their parent.
    _drag(strip, QPoint(100, 100))
    assert window.pos() == start
    assert controller._press is None


def test_auto_hide_timer_rechecks_pointer_before_collapsing(docked, monkeypatch):
    window, controller, _, _ = docked
    controller.dock(DockSide.LEFT)
    controller._check_auto_hide()
    assert controller._hide_timer.isActive()
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: window.frameGeometry().center()))
    QTest.qWait(50)
    assert window.isVisible()
    assert not controller.isCollapsed()
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: QPoint(10000, 10000)))
    controller._check_auto_hide()
    QTest.qWait(50)
    assert controller.isCollapsed()
    assert not window.isVisible()
    assert controller._handle.isVisible()


def test_drag_pending_and_popups_prevent_auto_hide(docked):
    window, controller, strip, _ = docked
    controller.dock(DockSide.LEFT)
    QTest.mousePress(strip, Qt.LeftButton)
    controller.collapse()
    assert window.isVisible()
    QTest.mouseRelease(strip, Qt.LeftButton)
    menu = QMenu(window)
    menu.addAction("Action")
    menu.popup(window.mapToGlobal(QPoint(10, 10)))
    _APP.processEvents()
    try:
        controller.collapse()
        assert window.isVisible()
    finally:
        menu.close()


def test_handle_hover_and_external_show_restore_without_stale_handle(docked):
    window, controller, _, _ = docked
    controller.dock(DockSide.RIGHT)
    controller.collapse()
    assert controller.isCollapsed()
    point = QPointF(controller._handle.rect().center())
    QApplication.sendEvent(controller._handle, QEnterEvent(point, point, point))
    assert window.isVisible()
    assert not controller._handle.isVisible()
    controller.collapse()
    window.show()
    assert not controller.isCollapsed()
    assert not controller._handle.isVisible()
    assert controller.dockSide() == DockSide.RIGHT


def test_expand_raises_and_activates_target(docked, monkeypatch):
    window, controller, _, _ = docked
    controller.dock(DockSide.LEFT)
    calls = []
    monkeypatch.setattr(window, "raise_", lambda: calls.append("raise"))
    monkeypatch.setattr(window, "activateWindow", lambda: calls.append("activate"))
    monkeypatch.setattr(controller, "_can_hide", lambda: True)

    controller.collapse()
    assert controller.isCollapsed()
    monkeypatch.setattr(controller, "_can_hide", lambda: False)
    controller.expand()

    assert calls == ["raise", "activate"]
    assert controller._foreground_timer.isActive()
    _APP.processEvents()
    assert calls[:4] == ["raise", "activate", "raise", "activate"]

    monkeypatch.setattr(controller, "_can_hide", lambda: True)
    controller.collapse()
    assert controller.isCollapsed()
    assert not controller._foreground_timer.isActive()
    calls.clear()
    controller._raise_and_activate_target()
    assert calls == []


def test_external_show_restores_foreground_after_show_event(docked, monkeypatch):
    window, controller, _, _ = docked
    controller.dock(DockSide.LEFT)
    calls = []
    monkeypatch.setattr(window, "raise_", lambda: calls.append("raise"))
    monkeypatch.setattr(window, "activateWindow", lambda: calls.append("activate"))
    monkeypatch.setattr(controller, "_can_hide", lambda: True)

    controller.collapse()
    assert controller.isCollapsed()
    monkeypatch.setattr(controller, "_can_hide", lambda: False)
    window.show()
    _APP.processEvents()

    assert calls[:4] == ["raise", "activate", "raise", "activate"]


def test_restore_rechecks_native_occlusion_at_cursor(docked, monkeypatch):
    from pyside6_modern_widgets import edge_dock

    window, controller, _, _ = docked
    calls = []
    monkeypatch.setattr(edge_dock, "uses_windows_window_state", lambda: True)
    monkeypatch.setattr(edge_dock, "window_is_at_cursor", lambda _hwnd: False)
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: window.frameGeometry().center()))
    monkeypatch.setattr(window, "raise_", lambda: calls.append("raise"))
    monkeypatch.setattr(window, "activateWindow", lambda: calls.append("activate"))

    controller._check_restored_foreground()
    assert calls == ["raise", "activate"]

    calls.clear()
    monkeypatch.setattr(edge_dock, "window_is_at_cursor", lambda _hwnd: True)
    controller._check_restored_foreground()
    assert calls == []


def test_foreground_settling_retries_late_occlusion_with_a_fixed_budget(docked, monkeypatch):
    from pyside6_modern_widgets import edge_dock

    window, controller, _, _ = docked
    monkeypatch.setattr(edge_dock, "uses_windows_window_state", lambda: True)
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: window.frameGeometry().center()))
    occluded = [False]
    monkeypatch.setattr(edge_dock, "window_is_at_cursor", lambda _: not occluded[0])
    calls = []
    monkeypatch.setattr(controller, "_raise_and_activate_target", lambda: calls.append(True))
    controller._schedule_foreground()
    controller._foreground_timer.stop()
    calls.clear()
    controller._check_restored_foreground()  # Initially in front.
    assert calls == []
    assert controller._foreground_settle_timer.isActive()
    occluded[0] = True  # The previous active window reasserts foreground later.
    for _ in range(2):
        controller._foreground_settle_timer.stop()
        controller._check_restored_foreground()
    assert len(calls) == 2
    assert controller._foreground_checks_left == 0
    assert not controller._foreground_settle_timer.isActive()


@pytest.mark.parametrize("cancel", ["pointer_left", "popup", "dismiss", "detach", "disable"])
def test_foreground_retries_stop_when_restore_is_no_longer_relevant(docked, monkeypatch, cancel):
    from pyside6_modern_widgets import edge_dock

    window, controller, _, _ = docked
    monkeypatch.setattr(edge_dock, "uses_windows_window_state", lambda: True)
    monkeypatch.setattr(edge_dock, "window_is_at_cursor", lambda _: False)
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: window.frameGeometry().center()))
    calls = []
    monkeypatch.setattr(controller, "_raise_and_activate_target", lambda: calls.append(True))
    controller._schedule_foreground()
    controller._foreground_timer.stop()
    calls.clear()
    if cancel == "pointer_left":
        monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: QPoint(-10000, -10000)))
    elif cancel == "popup":
        monkeypatch.setattr(QApplication, "activePopupWidget", staticmethod(lambda: window))
    elif cancel == "disable":
        controller.setEnabled(False)
    else:
        getattr(controller, cancel)()
    controller._check_restored_foreground()
    assert calls == []
    assert not controller._foreground_settle_timer.isActive()
    assert controller._foreground_checks_left == 0


def test_foreground_retries_wait_for_mouse_release(docked, monkeypatch):
    from pyside6_modern_widgets import edge_dock

    window, controller, _, _ = docked
    monkeypatch.setattr(edge_dock, "uses_windows_window_state", lambda: True)
    monkeypatch.setattr(edge_dock, "window_is_at_cursor", lambda _: False)
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: window.frameGeometry().center()))
    calls = []
    monkeypatch.setattr(controller, "_raise_and_activate_target", lambda: calls.append(True))
    controller._schedule_foreground()
    controller._foreground_timer.stop()
    calls.clear()
    monkeypatch.setattr(controller, "_buttons_pressed", lambda **_: True)
    controller._check_restored_foreground()
    assert calls == []
    monkeypatch.setattr(controller, "_buttons_pressed", lambda **_: False)
    controller._check_restored_foreground()
    assert calls == [True]


def test_activation_callback_can_dismiss_without_rearming_foreground_timers(docked, monkeypatch):
    from pyside6_modern_widgets import edge_dock

    window, controller, _, _ = docked
    monkeypatch.setattr(edge_dock, "uses_windows_window_state", lambda: True)
    monkeypatch.setattr(window, "activateWindow", controller.dismiss)
    controller.expand()
    assert not window.isVisible()
    assert not controller._foreground_timer.isActive()
    assert not controller._foreground_settle_timer.isActive()


@pytest.mark.parametrize("action", ["hide", "close", "showMinimized", "showMaximized"])
def test_external_lifecycle_clears_state_and_timers(docked, action):
    window, controller, _, _ = docked
    controller.dock(DockSide.LEFT)
    getattr(window, action)()
    _APP.processEvents()
    assert controller.dockSide() == DockSide.NONE
    assert not controller._handle.isVisible()
    assert not controller._monitor.isActive()
    assert not controller._hide_timer.isActive()


def test_close_while_collapsed_cannot_resurrect_handle(docked):
    window, controller, _, _ = docked
    controller.dock(DockSide.LEFT)
    controller.collapse()
    window.close()
    QTest.qWait(50)
    assert not controller._handle.isVisible()
    assert controller.dockSide() == DockSide.NONE
    assert not controller.isCollapsed()


def test_disabling_auto_hide_retains_docking_and_disable_restores(docked):
    window, controller, _, _ = docked
    controller.dock(DockSide.LEFT)
    controller.collapse()
    controller.setAutoHide(False)
    assert controller.isCollapsed()
    assert controller.dockSide() == DockSide.LEFT
    assert not controller._monitor.isActive()
    controller.expand()
    assert controller.collapse()
    assert controller.isCollapsed()
    controller.setAutoHide(True)
    controller.collapse()
    controller.setEnabled(False)
    assert window.isVisible()
    assert not controller._handle.isVisible()
    assert controller.dockSide() == DockSide.NONE
    controller.setEnabled(True)
    controller.dock(DockSide.RIGHT)
    assert controller.dockSide() == DockSide.RIGHT


def test_detach_restores_target_and_removes_drag_behavior(docked):
    window, controller, strip, _ = docked
    controller.dock(DockSide.LEFT)
    controller.collapse()
    controller.detach()
    assert window.isVisible()
    start = window.pos()
    _drag(strip, QPoint(100, 50))
    assert window.pos() == start
    controller.setEnabled(True)
    assert not controller.isEnabled()


def test_resize_keeps_right_edge_and_animation_is_reused(docked):
    window, previous, strip, _ = docked
    previous.detach()
    controller = EdgeDockController(window, DockConfig(animation_duration_ms=40), drag_widget=strip)
    controller.setAutoHide(False)
    animation = controller._animation
    finished = QSignalSpy(animation.finished)
    controller.dock(DockSide.LEFT)
    controller.dock(DockSide.RIGHT)
    assert finished.wait(1000)
    assert controller._animation is animation
    assert controller.dockSide() == DockSide.RIGHT
    assert window.frameGeometry().right() == window.screen().availableGeometry().right() - 2
    window.resize(300, 190)
    _APP.processEvents()
    assert window.frameGeometry().right() == window.screen().availableGeometry().right() - 2


def test_target_destruction_owns_handle_and_controller(theme_manager_instance, monkeypatch):
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: QPoint(10000, 10000)))
    window = ModernWindow()
    window.resize(320, 240)
    controller = EdgeDockController(window, DockConfig(animation_duration_ms=0))
    window.show()
    _APP.processEvents()
    controller.dock(DockSide.LEFT)
    controller.collapse()
    handle = controller._handle
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    _APP.processEvents()
    assert not isValid(handle)
    assert not isValid(controller)


def test_system_drag_survives_ungrab_and_snaps_after_native_finish(
    monkeypatch, theme_manager_instance
):
    window = ModernWindow()
    surface = QLabel("Drag", window)
    surface.setGeometry(20, 50, 180, 40)
    window.resize(400, 240)
    window.move(220, 200)
    controller = EdgeDockController(
        window, DockConfig(animation_duration_ms=0), drag_widget=surface, auto_hide=False
    )
    window.show()
    _APP.processEvents()
    original_size = window.size()
    original_pos = window.pos()
    calls = []
    handle = window.windowHandle()
    monkeypatch.setattr(handle, "startSystemMove", lambda: calls.append(True) or True)
    monkeypatch.setattr(QApplication, "mouseButtons", staticmethod(lambda: Qt.LeftButton))
    local = surface.rect().center()
    pointer = surface.mapToGlobal(local)
    try:
        _mouse(surface, QEvent.Type.MouseButtonPress, local, pointer, Qt.LeftButton, Qt.LeftButton)
        _mouse(
            surface,
            QEvent.Type.MouseMove,
            local,
            pointer + QPoint(20, 0),
            Qt.NoButton,
            Qt.LeftButton,
        )
        assert calls == [True]
        assert controller._system_move
        assert window.pos() == original_pos  # The controller must not also move it.
        QApplication.sendEvent(surface, QEvent(QEvent.Type.UngrabMouse))
        assert controller._system_move
        area = window.screen().availableGeometry()
        window.move(area.left() + 12, area.top() + 150)
        # No Qt MouseButtonRelease arrives after the native move loop.
        window._finish_system_move()
        assert not controller._system_move
        assert controller.dockSide() == DockSide.NONE  # Deferred past the native event.
        _APP.processEvents()
        assert controller.dockSide() == DockSide.LEFT
        assert window.frameGeometry().left() == area.left() + 2
        assert window.size() == original_size
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_portable_system_drag_completion_without_release(docked, monkeypatch):
    window, controller, surface, _ = docked
    monkeypatch.setattr(window.windowHandle(), "startSystemMove", lambda: True)
    held = [Qt.LeftButton]
    monkeypatch.setattr(QApplication, "mouseButtons", staticmethod(lambda: held[0]))
    local = surface.rect().center()
    pointer = surface.mapToGlobal(local)
    _mouse(surface, QEvent.Type.MouseButtonPress, local, pointer, Qt.LeftButton, Qt.LeftButton)
    _mouse(
        surface, QEvent.Type.MouseMove, local, pointer + QPoint(20, 0), Qt.NoButton, Qt.LeftButton
    )
    window.move(window.screen().availableGeometry().left() + 5, window.y())
    controller._check_drag_finished()
    assert controller._system_move
    held[0] = Qt.NoButton
    controller._check_drag_finished()
    _APP.processEvents()
    assert controller.dockSide() == DockSide.LEFT
    assert not controller._drag_watch.isActive()


def test_windows_drag_completion_uses_live_state_when_qt_release_is_missing(docked, monkeypatch):
    from pyside6_modern_widgets import edge_dock

    window, controller, surface, _ = docked
    monkeypatch.setattr(window.windowHandle(), "startSystemMove", lambda: True)
    monkeypatch.setattr(QApplication, "mouseButtons", staticmethod(lambda: Qt.LeftButton))
    monkeypatch.setattr(edge_dock, "uses_windows_window_state", lambda: True)
    monkeypatch.setattr(edge_dock, "mouse_buttons_pressed", lambda **kwargs: False)
    local = surface.rect().center()
    pointer = surface.mapToGlobal(local)
    _mouse(surface, QEvent.Type.MouseButtonPress, local, pointer, Qt.LeftButton, Qt.LeftButton)
    window.move(window.screen().availableGeometry().left() + 10, window.y())
    controller._check_drag_finished()
    _APP.processEvents()
    assert controller.dockSide() == DockSide.LEFT
    assert not controller._system_move
    controller.collapse()
    assert controller.isCollapsed()  # Stale Qt LeftButton must not block auto-hide.


@pytest.mark.parametrize("collapsed", [False, True])
def test_rejected_close_preserves_accessible_docked_window(
    theme_manager_instance, monkeypatch, collapsed
):
    class VetoWindow(QWidget):
        def closeEvent(self, event):
            # A confirmation dialog can now safely be parented to a visible target.
            assert self.isVisible()
            event.ignore()

    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: QPoint(10000, 10000)))
    window = VetoWindow(None, Qt.FramelessWindowHint)
    window.resize(240, 160)
    controller = EdgeDockController(
        window, DockConfig(animation_duration_ms=0, hide_delay_ms=10000)
    )
    try:
        window.show()
        _APP.processEvents()
        controller.dock(DockSide.LEFT)
        if collapsed:
            controller.collapse()
            assert controller.isCollapsed()
        assert window.close() is False
        _APP.processEvents()
        assert window.isVisible()
        assert controller.dockSide() == DockSide.LEFT
        assert not controller.isCollapsed()
        assert not controller._handle.isVisible()
    finally:
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


@pytest.mark.parametrize("collapsed", [False, True])
def test_dismiss_removes_all_restore_ui_and_allows_reopening(docked, collapsed):
    window, controller, _, _ = docked
    controller.dock(DockSide.RIGHT)
    if collapsed:
        controller.collapse()
    controller.dismiss()
    controller.dismiss()
    QTest.qWait(250)  # Old hide/monitor/foreground callbacks must not resurrect it.
    assert not window.isVisible()
    assert not controller._handle.isVisible()
    assert not controller.isCollapsed()
    assert controller.dockSide() == DockSide.NONE
    assert controller.isEnabled()
    controller.expand()
    assert window.isVisible()
    assert controller.dockSide() == DockSide.NONE


def test_plain_hide_of_collapsed_target_requires_explicit_dismiss(docked):
    window, controller, _, _ = docked
    controller.dock(DockSide.LEFT)
    controller.collapse()
    window.hide()  # Already hidden: Qt sends no Hide event.
    assert controller.isCollapsed()
    assert controller._handle.isVisible()
    controller.dismiss()
    assert not controller._handle.isVisible()


def test_destroyed_drag_surface_can_be_replaced_and_detached(docked):
    window, controller, strip, field = docked
    controller.dock(DockSide.LEFT)
    controller.collapse()
    strip.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert controller.isCollapsed()
    controller.expand()
    controller.setAutoHide(False)
    replacement = QLabel("Replacement", window)
    window.layout().addWidget(replacement)
    _APP.processEvents()
    controller.setDragWidget(replacement)
    _drag(replacement, QPoint(100, 50))
    assert controller.dockSide() == DockSide.NONE
    start = window.pos()
    QTest.mouseClick(field, Qt.LeftButton)
    assert window.pos() == start
    replacement.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    controller.detach()
    controller.detach()
    assert not controller.isEnabled()
    assert window.isVisible()


def test_destroyed_surface_cancels_native_drag_and_pending_snap(docked, monkeypatch):
    window, controller, strip, _ = docked
    monkeypatch.setattr(window.windowHandle(), "startSystemMove", lambda: True)
    local = strip.rect().center()
    pointer = strip.mapToGlobal(local)
    _mouse(strip, QEvent.MouseButtonPress, local, pointer, Qt.LeftButton, Qt.LeftButton)
    window.move(window.screen().availableGeometry().left() + 5, window.y())
    strip.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    controller._check_drag_finished()
    _APP.processEvents()
    assert controller.dockSide() == DockSide.NONE
    assert controller._press is None
    assert not controller._drag_watch.isActive()


def test_binding_new_surface_removes_old_surface_drag_behavior(docked):
    window, controller, strip, _ = docked
    replacement = QLabel("Replacement", window)
    window.layout().addWidget(replacement)
    _APP.processEvents()
    controller.setDragWidget(replacement)
    start = window.pos()
    _drag(strip, QPoint(100, 50))
    assert window.pos() == start
    _drag(replacement, QPoint(100, 50))
    assert window.pos() != start


def test_only_one_attached_controller_can_own_a_target(docked):
    window, controller, _, _ = docked
    with pytest.raises(ValueError, match="already has"):
        EdgeDockController(window)
    controller.setEnabled(False)
    with pytest.raises(ValueError, match="already has"):
        EdgeDockController(window)
    controller.detach()
    replacement = EdgeDockController(window, DockConfig(animation_duration_ms=0))
    replacement.dock(DockSide.RIGHT)
    assert replacement.dockSide() == DockSide.RIGHT


def test_observers_see_committed_visibility_and_can_detach_during_collapse(docked):
    window, controller, _, _ = docked
    observed = []

    def collapsed_changed(collapsed):
        observed.append((collapsed, window.isVisible(), controller._handle.isVisible()))
        if collapsed:
            controller.detach()

    controller.collapsedChanged.connect(collapsed_changed)
    controller.dock(DockSide.LEFT)
    controller.collapse()
    assert observed == [(True, False, True), (False, True, False)]
    assert window.isVisible()
    assert not controller.isEnabled()
    assert controller.dockSide() == DockSide.NONE
    QTest.qWait(250)
    assert not controller._handle.isVisible()


def test_dock_observer_can_disable_without_leaving_an_animation(docked):
    window, previous, strip, _ = docked
    previous.detach()
    controller = EdgeDockController(
        window, DockConfig(animation_duration_ms=100), drag_widget=strip
    )

    def side_changed(side):
        if side != DockSide.NONE:
            controller.setEnabled(False)

    controller.dockSideChanged.connect(side_changed)
    controller.dock(DockSide.RIGHT)
    position = window.pos()
    QTest.qWait(150)
    assert window.pos() == position
    assert not controller.isEnabled()
    assert controller.dockSide() == DockSide.NONE


def test_detach_disconnects_screen_notifications(docked):
    class Screen(QObject):
        availableGeometryChanged = Signal(QRect)
        geometryChanged = Signal(QRect)
        logicalDotsPerInchChanged = Signal(float)

    class Controller(EdgeDockController):
        def _schedule_refresh(self, *args):
            calls.append(True)
            super()._schedule_refresh(*args)

    window, previous, _, _ = docked
    previous.detach()
    calls = []
    controller = Controller(window)
    screen = Screen()
    controller._watch_screen(screen)
    calls.clear()
    screen.geometryChanged.emit(QRect(0, 0, 1000, 800))
    assert calls == [True]
    controller.detach()
    calls.clear()
    screen.geometryChanged.emit(QRect(0, 0, 800, 600))
    screen.availableGeometryChanged.emit(QRect(0, 0, 800, 560))
    screen.logicalDotsPerInchChanged.emit(144.0)
    assert calls == []


def test_detached_controller_cannot_mutate_target(docked):
    window, controller, strip, _ = docked
    controller.detach()
    controller.dismiss()
    assert window.isVisible()
    window.hide()
    controller.expand()
    controller.setEnabled(True)
    controller.setDragWidget(strip)
    controller.dock(DockSide.LEFT)
    controller.collapse()
    _APP.processEvents()
    assert not window.isVisible()
    assert not controller._handle.isVisible()
    assert controller.dockSide() == DockSide.NONE
    assert not controller.isEnabled()


def test_widget_hide_handler_can_detach_without_leaving_a_restore_handle(
    theme_manager_instance, monkeypatch
):
    class Window(QWidget):
        def hideEvent(self, event):
            if controller.isCollapsed():
                controller.detach()
            super().hideEvent(event)

    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: QPoint(10000, 10000)))
    window = Window(None, Qt.FramelessWindowHint)
    window.resize(240, 160)
    controller = EdgeDockController(window, DockConfig(animation_duration_ms=0))
    try:
        window.show()
        _APP.processEvents()
        controller.dock(DockSide.LEFT)
        controller.collapse()
        assert window.isVisible()
        assert not controller.isEnabled()
        assert not controller._handle.isVisible()
        assert not controller.isCollapsed()
    finally:
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


@pytest.mark.parametrize("action", ["dismiss", "setEnabled", "detach"])
def test_lifecycle_action_cancels_a_pending_snap(docked, action):
    window, controller, _, _ = docked
    area = window.screen().availableGeometry()
    window.move(area.left() + 5, area.top() + 150)
    controller._snap_timer.start(0)
    if action == "setEnabled":
        controller.setEnabled(False)
    else:
        getattr(controller, action)()
    _APP.processEvents()
    assert controller.dockSide() == DockSide.NONE
    assert not controller.isCollapsed()
    assert not controller._handle.isVisible()


def test_target_destruction_during_system_drag_does_not_call_dead_window(
    theme_manager_instance, monkeypatch
):
    errors = []
    monkeypatch.setattr(sys, "excepthook", lambda kind, error, traceback: errors.append(error))
    window = ModernWindow()
    strip = QLabel("Drag", window)
    controller = EdgeDockController(window, drag_widget=strip)
    window.show()
    _APP.processEvents()
    monkeypatch.setattr(window, "_uses_windows_window_state", lambda: False)
    monkeypatch.setattr(window.windowHandle(), "startSystemMove", lambda: True)
    assert controller._start_system_drag(window.pos())
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    _APP.processEvents()
    assert not isValid(controller)
    assert not isValid(window)
    assert errors == []
