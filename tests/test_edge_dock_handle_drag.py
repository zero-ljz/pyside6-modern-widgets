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
    DockHandleMode,
    DockPlacement,
    DockSide,
    EdgeDockController,
    ModernWindow,
)

_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def collapsed(monkeypatch, theme_manager_instance, request):
    options = getattr(request, "param", {})
    target_class = ModernWindow if options.get("modern") else QWidget
    window = target_class(None, Qt.Window if options.get("framed") else Qt.FramelessWindowHint)
    window.resize(240, 160)
    window.move(250, 250)
    controller = EdgeDockController(
        window,
        DockConfig(
            animation_duration_ms=0,
            sides=options.get(
                "sides", (DockSide.LEFT, DockSide.RIGHT, DockSide.TOP, DockSide.BOTTOM)
            ),
            handle_icon=QIcon(":/pyside6_modern_widgets/icons/application.png"),
            handle_mode=DockHandleMode.DRAG_OR_CLICK,
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


def test_handle_modes_are_complete_and_can_be_switched_directly(collapsed):
    _, controller, _, _, _, _, _ = collapsed
    assert DockConfig().handle_mode == DockHandleMode.HOVER_OR_CLICK
    assert controller.handleMode() == DockHandleMode.DRAG_OR_CLICK
    point = QPointF(controller._handle.rect().center())
    QApplication.sendEvent(controller._handle, QEnterEvent(point, point, point))
    assert controller.isCollapsed()
    controller.setHandleMode("hover_or_click")
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
        controller.setHandleMode(DockHandleMode.CLICK)
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


@pytest.mark.parametrize(
    "collapsed",
    [{"modern": False}, {"modern": True}, {"framed": True}, {"modern": True, "framed": True}],
    indirect=True,
)
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


@pytest.mark.parametrize("collapsed", [{"modern": False}, {"modern": True}], indirect=True)
def test_native_programmatic_placement_preserves_size_visible_and_folded(collapsed):
    if QApplication.platformName() in ("offscreen", "minimal") or len(QApplication.screens()) < 2:
        pytest.skip("requires a native desktop with multiple displays")
    window, controller, _, _, _, _, _ = collapsed
    original_size = window.size()
    for folded in (True, False):
        for screen in QApplication.screens() + list(reversed(QApplication.screens())):
            controller.collapse() if folded else controller.expand()
            assert controller.setPlacement(DockPlacement(DockSide.RIGHT, screen.name(), 0.6))
            QTest.qWait(100)
            assert controller.isCollapsed() == folded
            controller.expand()
            QTest.qWait(100)
            assert window.size() == original_size
            assert window.screen() is screen
            assert screen.availableGeometry().contains(window.frameGeometry())


@pytest.mark.parametrize("collapsed", [{"modern": False}, {"modern": True}], indirect=True)
def test_native_hidden_round_trips_preserve_constrained_tool_size(collapsed):
    if QApplication.platformName() in ("offscreen", "minimal") or len(QApplication.screens()) < 2:
        pytest.skip("requires a native desktop with multiple displays")
    from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout

    window, controller, press, move, release, pointer, held = collapsed
    controller.expand()
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.addWidget(QLabel("Drag here to a screen edge"))
    layout.addWidget(QLineEdit("Text selection still works"))
    layout.addWidget(QLabel("Use the controls to hide or restore this tool."))
    layout.addWidget(QPushButton("Close tool"))
    if isinstance(window, ModernWindow):
        window.setCentralWidget(content)
    else:
        QVBoxLayout(window).addWidget(content)
    window.resize(400, 240)
    _APP.processEvents()
    original_size = window.size()
    pointer[0] = QPoint(100000, 100000)
    controller.collapse()
    screens = QApplication.screens()
    for cycle in range(3):
        for screen in screens + list(reversed(screens)):
            area = screen.availableGeometry()
            destination = QPoint(area.right() - 4, area.center().y())
            press()
            move(destination)
            QTest.qWait(40)
            release(destination)
            QTest.qWait(40)
            assert controller.isCollapsed()
        controller.expand()
        QTest.qWait(100)
        assert window.size() == original_size, (cycle, window.size(), original_size)
        pointer[0] = QPoint(100000, 100000)
        held[0] = False
        controller.collapse()


@pytest.mark.parametrize("preview_only", [False, True])
@pytest.mark.parametrize("start_screen", [0, 1])
def test_native_gallery_tool_hidden_round_trips(
    theme_manager_instance, monkeypatch, preview_only, start_screen
):
    if QApplication.platformName() in ("offscreen", "minimal") or len(QApplication.screens()) < 2:
        pytest.skip("requires a native desktop with multiple displays")
    from examples.edge_dock_example import EdgeDockExample

    demo = EdgeDockExample()
    demo.show()
    demo.floating_window.move(QApplication.screens()[start_screen].availableGeometry().center())
    demo.show_floating()
    demo.handle_mode.setCurrentIndex(2)
    controller = demo.dock
    window = demo.floating_window
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: QPoint(100000, 100000)))
    monkeypatch.setattr(controller, "_buttons_pressed", lambda **_kwargs: True)
    _APP.processEvents()
    original_size = window.size()

    def send(kind, point, buttons):
        QApplication.sendEvent(
            controller._handle,
            QMouseEvent(
                kind,
                QPointF(controller._handle.mapFromGlobal(point)),
                QPointF(point),
                Qt.NoButton if kind == QEvent.MouseMove else Qt.LeftButton,
                buttons,
                Qt.NoModifier,
            ),
        )

    try:
        controller.dock(DockSide.LEFT)
        QTest.qWait(300)
        for cycle in range(4):
            monkeypatch.setattr(controller, "_buttons_pressed", lambda **_kwargs: False)
            controller.collapse()
            assert controller.isCollapsed(), (
                controller._state,
                window.isVisible(),
                controller._animation.state(),
            )
            monkeypatch.setattr(controller, "_buttons_pressed", lambda **_kwargs: True)
            for screen in QApplication.screens() + list(reversed(QApplication.screens())):
                area = screen.availableGeometry()
                destination = QPoint(area.right() - 4, area.center().y())
                send(
                    QEvent.MouseButtonPress,
                    controller._handle.frameGeometry().center(),
                    Qt.LeftButton,
                )
                send(QEvent.MouseMove, area.center(), Qt.LeftButton)
                if preview_only:
                    for other in reversed(QApplication.screens()):
                        send(QEvent.MouseMove, other.availableGeometry().center(), Qt.LeftButton)
                        QTest.qWait(40)
                send(QEvent.MouseMove, destination, Qt.LeftButton)
                QTest.qWait(40)
                send(QEvent.MouseButtonRelease, destination, Qt.NoButton)
                QTest.qWait(120)
                assert controller.isCollapsed(), (
                    cycle,
                    screen.name(),
                    controller._state,
                    window.size(),
                    destination,
                    controller._handle_gesture,
                )
            controller.expand()
            QTest.qWait(150)
            assert window.size() == original_size, (cycle, window.size(), original_size)
    finally:
        demo.close()
        demo.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
