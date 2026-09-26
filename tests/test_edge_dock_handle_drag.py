"""Handle gestures: click, edge drops, cross-screen drops and lifecycle cancellation."""

import sys

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QCursor, QEnterEvent, QIcon, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from shiboken6 import isValid

from pyside6_modern_widgets import (
    DockConfig,
    DockRestoreTrigger,
    DockSide,
    EdgeDockController,
    ModernWindow,
)

_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def collapsed(monkeypatch, theme_manager_instance, request):
    options = getattr(request, "param", {})
    target_class = ModernWindow if options.get("modern") else QWidget
    window = target_class(None, Qt.FramelessWindowHint)
    window.resize(240, 160)
    window.move(250, 250)
    controller = EdgeDockController(
        window,
        DockConfig(
            anim_duration=0,
            sides=options.get(
                "sides", (DockSide.LEFT, DockSide.RIGHT, DockSide.TOP, DockSide.BOTTOM)
            ),
            handle_icon=QIcon(":/pyside6_modern_widgets/icons/application.png"),
            handle_draggable=True,
        ),
    )
    pointer = [QPoint(100000, 100000)]
    held = [False]
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: pointer[0]))
    monkeypatch.setattr(controller, "_buttons_pressed", lambda **_kwargs: held[0])
    window.show()
    _APP.processEvents()
    controller.dock(DockSide.LEFT)
    controller.collapse()
    assert controller.isCollapsed()

    def send(kind, point, *, button=Qt.NoButton, buttons=Qt.NoButton):
        pointer[0] = point
        held[0] = bool(buttons & Qt.LeftButton)
        local = controller._handle.mapFromGlobal(point)
        event = QMouseEvent(kind, QPointF(local), QPointF(point), button, buttons, Qt.NoModifier)
        QApplication.sendEvent(controller._handle, event)

    def press():
        point = controller._handle.frameGeometry().center()
        send(QEvent.MouseButtonPress, point, button=Qt.LeftButton, buttons=Qt.LeftButton)
        return point

    def move(point):
        send(QEvent.MouseMove, point, buttons=Qt.LeftButton)

    def release(point):
        send(QEvent.MouseButtonRelease, point, button=Qt.LeftButton)

    yield window, controller, press, move, release, pointer, held
    held[0] = False
    if isValid(window):
        window.close()
        window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    _APP.processEvents()


def test_drag_option_selects_click_and_rejects_hover_until_disabled(collapsed):
    _, controller, _, _, _, _, _ = collapsed
    assert not DockConfig().handle_draggable
    assert controller.handleDraggable()
    assert controller.restoreTrigger() == DockRestoreTrigger.CLICK
    point = QPointF(controller._handle.rect().center())
    QApplication.sendEvent(controller._handle, QEnterEvent(point, point, point))
    assert controller.isCollapsed()
    with pytest.raises(ValueError, match="disable handle dragging"):
        controller.setRestoreTrigger("hover")
    controller.setHandleDraggable(False)
    controller.setRestoreTrigger("hover")
    assert not controller.handleDraggable()
    QApplication.sendEvent(controller._handle, QEnterEvent(point, point, point))
    assert not controller.isCollapsed()


def test_click_waits_for_release_and_small_motion_does_not_drag(collapsed):
    window, controller, press, move, release, _, _ = collapsed
    position = window.pos()
    start = press()
    assert controller.isCollapsed()
    move(start + QPoint(1, 1))
    assert controller.isCollapsed()
    release(start + QPoint(1, 1))
    assert window.isVisible()
    assert window.pos() == position
    assert controller.dockSide() == DockSide.LEFT
    assert controller._handle_gesture is None
    assert QWidget.mouseGrabber() is not controller._handle


@pytest.mark.parametrize("side", [DockSide.LEFT, DockSide.RIGHT, DockSide.TOP, DockSide.BOTTOM])
def test_drop_on_each_edge_keeps_collapsed_and_updates_restore_position(collapsed, side):
    window, controller, press, move, release, _, _ = collapsed
    area = window.screen().availableGeometry()
    destination = {
        DockSide.LEFT: QPoint(area.left() + 3, area.bottom() - 40),
        DockSide.RIGHT: QPoint(area.right() - 3, area.top() + 80),
        DockSide.TOP: QPoint(area.right() - 80, area.top() + 3),
        DockSide.BOTTOM: QPoint(area.left() + 80, area.bottom() - 3),
    }[side]
    visible_changes = []
    controller.collapsedChanged.connect(visible_changes.append)
    original = window.frameGeometry()
    press()
    move(destination)
    assert controller.isCollapsed()
    assert window.frameGeometry() == original
    assert controller._handle.frameGeometry().contains(destination)
    release(destination)
    assert controller.isCollapsed()
    assert controller.dockSide() == side
    assert visible_changes == []
    assert not window.isVisible()
    assert area.contains(controller._handle.frameGeometry())
    assert getattr(controller._handle.frameGeometry(), side.value)() == getattr(
        area, side.value
    )() + (2 if side in (DockSide.LEFT, DockSide.TOP) else -2)
    controller.expand()
    assert area.contains(window.frameGeometry())
    assert getattr(window.frameGeometry(), side.value)() == getattr(area, side.value)() + (
        2 if side in (DockSide.LEFT, DockSide.TOP) else -2
    )


def test_interior_drop_expands_near_grab_point_and_clears_docking(collapsed):
    window, controller, press, move, release, _, _ = collapsed
    start = press()
    offset = start - window.frameGeometry().topLeft()
    destination = window.screen().availableGeometry().center()
    move(destination)
    assert not window.isVisible()
    release(destination)
    assert window.isVisible()
    assert not controller.isCollapsed()
    assert controller.dockSide() == DockSide.NONE
    assert window.frameGeometry().topLeft() == destination - offset
    assert not controller._handle.isVisible()
    assert not controller._monitor.isActive()
    assert QWidget.keyboardGrabber() is not controller._handle


def test_strip_handle_rotates_only_after_committing_new_edge(collapsed):
    window, controller, press, move, release, _, _ = collapsed
    controller.setHandleIcon(None)
    assert controller._handle.width() == 6
    destination = window.screen().availableGeometry().topLeft() + QPoint(300, 4)
    press()
    move(destination)
    assert controller._handle.width() == 6
    release(destination)
    assert controller.isCollapsed()
    assert controller.dockSide() == DockSide.TOP
    assert controller._handle.width() == 80
    assert controller._handle.height() == 6


class Screen:
    def __init__(self, area):
        self.area = area

    def geometry(self):
        return self.area

    def availableGeometry(self):
        return self.area


@pytest.mark.parametrize("edge", [True, False])
def test_cross_screen_drop_uses_pointer_screen_and_negative_coordinates(
    collapsed, monkeypatch, edge
):
    window, controller, press, move, release, _, _ = collapsed
    original_screen = window.screen()
    secondary = Screen(QRect(-1600, -200, 1600, 1000))
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: [original_screen, secondary]))
    monkeypatch.setattr(
        QApplication,
        "screenAt",
        staticmethod(
            lambda point: secondary if secondary.area.contains(point) else original_screen
        ),
    )
    destination = QPoint(-1596, 400) if edge else QPoint(-900, 400)
    press()
    move(destination)
    release(destination)
    assert secondary.area.contains(window.frameGeometry())
    if edge:
        assert controller.isCollapsed()
        assert secondary.area.contains(controller._handle.frameGeometry())
        assert controller.dockSide() == DockSide.LEFT
        controller.expand()
        assert window.frameGeometry().left() == -1598
        assert secondary.area.contains(window.frameGeometry())
    else:
        assert window.isVisible()
        assert controller.dockSide() == DockSide.NONE


@pytest.mark.parametrize(
    "collapsed", [{"sides": (DockSide.LEFT, DockSide.RIGHT, DockSide.TOP)}], indirect=True
)
def test_disabled_edge_drop_expands_and_clamps_instead_of_collapsing(collapsed):
    window, previous, press, move, release, _, _ = collapsed
    area = window.screen().availableGeometry()
    destination = QPoint(area.center().x(), area.bottom() + 100)
    press()
    move(destination)
    release(destination)
    assert window.isVisible()
    assert previous.dockSide() == DockSide.NONE
    assert area.contains(window.frameGeometry())


def test_screen_gap_chooses_nearest_display():
    # ScreenAt returns None in mixed-DPI virtual desktop gaps.
    point = QPoint(-50, 100)
    left = Screen(QRect(-1000, 0, 800, 600))
    right = Screen(QRect(0, 0, 800, 600))
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: [left, right]))
        monkeypatch.setattr(QApplication, "screenAt", staticmethod(lambda point: None))
        assert EdgeDockController._nearest_screen(point) is right


@pytest.mark.parametrize(
    "cancel", ["escape", "ungrab", "keyboard_ungrab", "screen_change", "appearance", "disable_drag"]
)
def test_cancelled_drag_restores_original_handle_without_opening(collapsed, cancel):
    window, controller, press, move, release, _, _ = collapsed
    original_handle = controller._handle.geometry()
    original_frame = window.frameGeometry()
    press()
    destination = original_handle.center() + QPoint(140, 130)
    move(destination)
    if cancel == "escape":
        QTest.keyClick(controller._handle, Qt.Key_Escape)
    elif cancel == "ungrab":
        QApplication.sendEvent(controller._handle, QEvent(QEvent.UngrabMouse))
    elif cancel == "keyboard_ungrab":
        QApplication.sendEvent(controller._handle, QEvent(QEvent.UngrabKeyboard))
    elif cancel == "screen_change":
        controller._refresh_geometry()
    elif cancel == "appearance":
        controller.setHandleToolTip("Updated")
    else:
        controller.setHandleDraggable(False)
    release(destination)
    assert controller._handle_gesture is None
    assert controller.isCollapsed()
    assert not window.isVisible()
    assert window.frameGeometry() == original_frame
    assert controller._handle.geometry() == original_handle
    assert not controller._handle_drag_watch.isActive()
    assert QWidget.mouseGrabber() is not controller._handle


@pytest.mark.parametrize("action", ["dismiss", "detach", "disable", "expand", "close"])
def test_external_lifecycle_interrupts_drag_without_stale_drop(collapsed, action):
    window, controller, press, move, release, _, _ = collapsed
    press()
    destination = window.screen().availableGeometry().center()
    move(destination)
    if action == "disable":
        controller.setEnabled(False)
    elif action == "close":
        window.close()
    else:
        getattr(controller, action)()
    position = window.pos()
    release(destination)
    assert controller._handle_gesture is None
    assert window.pos() == position
    assert not controller._handle.isVisible()
    assert window.isVisible() == (action in ("detach", "disable", "expand"))


def test_missing_release_commits_drag_but_not_click(collapsed):
    window, controller, press, move, _, _, held = collapsed
    press()
    held[0] = False
    controller._check_handle_release()
    assert controller.isCollapsed()
    press()
    move(window.screen().availableGeometry().center())
    held[0] = False
    controller._check_handle_release()
    assert window.isVisible()
    assert controller.dockSide() == DockSide.NONE


def test_screen_removal_after_drop_recovers_handle_and_target(collapsed, monkeypatch):
    window, controller, press, move, release, _, _ = collapsed
    primary = window.screen()
    secondary = Screen(QRect(-1600, 0, 1600, 900))
    screens = [primary, secondary]
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: screens))
    monkeypatch.setattr(
        QApplication,
        "screenAt",
        staticmethod(
            lambda point: (
                secondary if secondary in screens and secondary.area.contains(point) else None
            )
        ),
    )
    press()
    destination = QPoint(-1595, 300)
    move(destination)
    release(destination)
    assert controller.isCollapsed()
    screens.remove(secondary)
    controller._refresh_geometry()
    assert primary.availableGeometry().contains(controller._handle.frameGeometry())
    controller.expand()
    assert primary.availableGeometry().contains(window.frameGeometry())


def test_destruction_during_handle_drag_has_no_dead_object_calls(collapsed, monkeypatch):
    window, controller, press, move, _, _, _ = collapsed
    errors = []
    monkeypatch.setattr(sys, "excepthook", lambda kind, error, traceback: errors.append(error))
    press()
    move(window.screen().availableGeometry().center())
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    _APP.processEvents()
    assert not isValid(controller)
    assert errors == []


@pytest.mark.parametrize("collapsed", [{"modern": False}, {"modern": True}], indirect=True)
def test_native_handle_drop_across_available_displays(collapsed):
    if QApplication.platformName() in ("offscreen", "minimal") or len(QApplication.screens()) < 2:
        pytest.skip("requires a native desktop with multiple displays")
    window, controller, press, move, release, pointer, held = collapsed
    original_size = window.size()
    original_handle_size = controller._handle.size()
    for screen in QApplication.screens() + list(reversed(QApplication.screens())):
        area = screen.availableGeometry()
        # First move the folded tool to the destination display's right edge.
        destination = QPoint(area.right() - 4, area.center().y())
        press()
        move(destination)
        QTest.qWait(40)  # Process native DPI/capture events while still dragging.
        assert controller._handle_gesture is not None
        assert not window.isVisible()
        release(destination)
        _APP.processEvents()
        assert controller.isCollapsed()
        assert controller.dockSide() == DockSide.RIGHT
        assert controller._handle.screen() is screen
        assert controller._handle.size() == original_handle_size
        assert area.contains(controller._handle.frameGeometry())
        controller.expand()
        _APP.processEvents()
        assert window.screen() is screen
        assert window.size() == original_size
        assert area.contains(window.frameGeometry())
        assert window.frameGeometry().right() == area.right() - 2
        pointer[0] = QPoint(100000, 100000)
        held[0] = False
        controller.collapse()
        assert controller.isCollapsed()
        # Then release in its interior and verify native frame/DPI settling.
        press()
        move(area.center())
        release(area.center())
        _APP.processEvents()
        assert window.isVisible()
        assert window.screen() is screen
        assert window.size() == original_size
        assert controller.dockSide() == DockSide.NONE
        assert area.contains(window.frameGeometry())
        pointer[0] = QPoint(100000, 100000)
        controller.dock(DockSide.LEFT)
        controller.collapse()
        assert controller.isCollapsed()


@pytest.mark.parametrize("collapsed", [{"modern": False}, {"modern": True}], indirect=True)
def test_native_interior_drop_across_available_displays(collapsed):
    if QApplication.platformName() in ("offscreen", "minimal") or len(QApplication.screens()) < 2:
        pytest.skip("requires a native desktop with multiple displays")
    window, controller, press, move, release, pointer, held = collapsed
    original_size = window.size()
    for screen in QApplication.screens() + list(reversed(QApplication.screens())):
        destination = screen.availableGeometry().center()
        press()
        move(destination)
        QTest.qWait(40)
        assert controller._handle_gesture is not None
        release(destination)
        _APP.processEvents()
        assert window.isVisible()
        assert window.screen() is screen
        assert window.size() == original_size
        assert controller.dockSide() == DockSide.NONE
        assert window.frameGeometry().contains(destination)
        assert screen.availableGeometry().contains(window.frameGeometry())
        pointer[0] = QPoint(100000, 100000)
        held[0] = False
        controller.dock(DockSide.LEFT)
        controller.collapse()
        assert controller.isCollapsed()
