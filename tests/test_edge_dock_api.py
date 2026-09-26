"""Public contracts for configuration, explicit commands and saved placement."""

from dataclasses import asdict, replace

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QSize, Qt
from PySide6.QtGui import QColor, QCursor, QIcon
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication, QWidget

from pyside6_modern_widgets import (
    DockConfig,
    DockHandleMode,
    DockPlacement,
    DockSide,
    DockState,
    EdgeDockController,
)

_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def dock(monkeypatch):
    window = QWidget(None, Qt.FramelessWindowHint)
    window.resize(240, 160)
    window.move(200, 200)
    window.show()
    _APP.processEvents()
    controller = EdgeDockController(window, DockConfig(animation_duration_ms=0, auto_hide=False))
    monkeypatch.setattr(controller, "_buttons_pressed", lambda **_: False)
    yield window, controller
    controller.detach()
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_config_and_qt_values_are_independent_snapshots(dock):
    _, controller = dock
    color = QColor("red")
    config = DockConfig(handle_color=color, handle_hover_color=color)
    color.setRgb(0, 255, 0)
    assert config.handle_color == QColor("red")
    controller.setConfig(config)
    config.handle_color.setRgb(0, 0, 255)
    config.handle_hover_color.setRgb(0, 0, 255)
    snapshot = controller.config()
    assert snapshot.handle_color == QColor("red")
    assert snapshot.handle_hover_color == QColor("red")
    snapshot.handle_color.setRgb(0, 255, 0)
    snapshot.handle_icon.swap(QIcon(":/pyside6_modern_widgets/icons/application.png"))
    assert controller.config().handle_color == QColor("red")
    assert controller.handleIcon().isNull()


def test_atomic_config_updates_apply_timers_geometry_and_removed_edge(dock):
    window, controller = dock
    controller.dock(DockSide.LEFT)
    controller.collapse()
    observed = []
    controller.configChanged.connect(
        lambda: observed.append((controller.config(), controller.state(), window.isVisible()))
    )
    cfg = replace(
        controller.config(),
        handle_width=12,
        handle_length=90,
        hide_delay_ms=100,
        animation_duration_ms=40,
        dock_distance=30,
        safe_margin=5,
    )
    controller.setConfig(cfg)
    assert len(observed) == 1
    assert controller.isCollapsed()
    assert controller._handle.size() == QSize(12, 90)
    assert controller._hide_timer.interval() == 100
    assert controller._animation.duration() == 40
    controller.setConfig(replace(cfg, sides=(DockSide.RIGHT,)))
    assert len(observed) == 2
    assert observed[-1][1:] == (DockState.FLOATING, True)
    with pytest.raises(ValueError):
        controller.setConfig(replace(cfg, sides=()))
    assert len(observed) == 2
    assert controller.config().sides == (DockSide.RIGHT,)


def test_equal_config_does_not_cancel_gesture_or_emit(dock, monkeypatch):
    _, controller = dock
    cfg = replace(
        controller.config(), handle_icon=QIcon(":/pyside6_modern_widgets/icons/application.png")
    )
    controller.setConfig(cfg)
    changes = QSignalSpy(controller.configChanged)
    cancellations = []
    monkeypatch.setattr(controller, "_cancel_activity", lambda: cancellations.append(True))
    controller.setConfig(controller.config())
    controller.setHandleMode(controller.handleMode())
    assert changes.count() == 0
    assert cancellations == []


def test_explicit_collapse_ignores_auto_hide_and_pointer_but_auto_timer_does_not(dock, monkeypatch):
    window, controller = dock
    controller.dock(DockSide.LEFT)
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: window.frameGeometry().center()))
    assert controller.collapse()
    assert controller.expand()
    controller._auto_collapse()
    assert window.isVisible()
    controller.setAutoHide(True)
    controller._auto_collapse()
    assert window.isVisible()
    assert controller.collapse()
    controller.setAutoHide(False)
    assert controller.isCollapsed()
    assert controller.collapse()  # Idempotent success.


def test_explicit_collapse_stops_docking_animation(dock):
    _, controller = dock
    controller.setConfig(replace(controller.config(), animation_duration_ms=250))
    assert controller.dock(DockSide.RIGHT)
    assert controller.collapse()
    assert controller.isCollapsed()


def test_placement_round_trip_same_side_notifications_and_missing_screen(dock):
    window, controller = dock
    observed = []
    controller.placementChanged.connect(observed.append)
    assert controller.setPlacement(DockPlacement(DockSide.LEFT, window.screen().name(), 0.25))
    first = controller.placement()
    assert first.side == DockSide.LEFT
    assert first.offset == pytest.approx(0.25, abs=0.002)
    assert controller.collapse()
    assert controller.setPlacement(replace(first, offset=0.75))
    assert controller.isCollapsed()
    assert observed[-1].offset == pytest.approx(0.75, abs=0.002)
    assert observed[-1].side == observed[0].side
    assert controller.setPlacement(None)
    assert controller.placement() is None and window.isVisible()
    # Values can be persisted with dataclasses/as JSON; missing monitors recover.
    restored = DockPlacement(**{**asdict(first), "side": "left", "screen_name": "missing"})
    assert controller.setPlacement(restored)
    assert controller.placement().screen_name == window.screen().name()
    assert controller.placement().offset == first.offset
    controller.dismiss()
    assert controller.setPlacement(first)
    assert window.isVisible()


@pytest.mark.parametrize(
    "kwargs", [{"offset": -1}, {"offset": 2}, {"offset": float("nan")}, {"side": "none"}]
)
def test_invalid_placement_is_rejected(kwargs):
    with pytest.raises(ValueError):
        DockPlacement(**{"side": "left", **kwargs})


def test_lifecycle_signals_and_detached_commands(dock):
    window, controller = dock
    states, enabled, attached, auto_hide = [], [], [], []
    controller.stateChanged.connect(states.append)
    controller.enabledChanged.connect(enabled.append)
    controller.attachedChanged.connect(attached.append)
    controller.autoHideChanged.connect(auto_hide.append)
    assert controller.target() is window and controller.dragWidget() is window
    controller.setAutoHide(True)
    controller.setEnabled(False)
    assert controller.isAttached() and not controller.isEnabled()
    assert not controller.setPlacement(DockPlacement(DockSide.LEFT))
    controller.setEnabled(True)
    controller.detach()
    assert states == [DockState.DISABLED, DockState.FLOATING, DockState.DETACHED]
    assert enabled == [False, True, False]
    assert attached == [False]
    assert auto_hide == [True]
    assert not controller.isAttached()
    assert not controller.dock("invalid")
    assert not controller.collapse()
    assert not controller.expand()
    assert not controller.dismiss()
    controller.setHandleMode("invalid")
    controller.setConfig(DockConfig())
    assert controller.autoHide()


def test_reentrant_config_and_placement_notifications_report_committed_state(dock):
    window, controller = dock
    events = []

    def configured():
        events.append(controller.handleMode())
        if controller.handleMode() == DockHandleMode.CLICK:
            controller.setHandleMode(DockHandleMode.DRAG_OR_CLICK)

    controller.configChanged.connect(configured)
    controller.setHandleMode(DockHandleMode.CLICK)
    assert events == [DockHandleMode.CLICK, DockHandleMode.DRAG_OR_CLICK]
    controller.placementChanged.connect(lambda value: controller.detach() if value else None)
    assert not controller.setPlacement(DockPlacement(DockSide.LEFT))
    assert not controller.isAttached() and window.isVisible()


@pytest.mark.parametrize("restore", ["expand", "detach", "disable", "show", "dismiss"])
def test_hidden_native_size_drift_does_not_replace_saved_logical_size(dock, restore):
    window, controller = dock
    original = window.size()
    controller.dock(DockSide.LEFT)
    controller.collapse()
    # Emulate Qt replacing a hidden QWidget/QWindow geometry cache with bounds
    # converted using the previous monitor's DPR. The visible logical size is
    # the source of truth, even if the round trip ends on the original screen.
    window.windowHandle().resize(QSize(432, 288))
    window.resize(432, 288)
    if restore == "disable":
        controller.setEnabled(False)
    elif restore == "show":
        window.show()
    else:
        getattr(controller, restore)()
    _APP.processEvents()
    assert window.size() == original
    if controller.isEnabled():
        controller.expand()
        window.resize(300, 180)
        controller.dock(DockSide.LEFT)
        controller.collapse()
        controller.expand()
        assert window.size() == QSize(300, 180)


def test_hidden_resize_respects_updated_layout_constraints(dock):
    window, controller = dock
    controller.dock(DockSide.LEFT)
    controller.collapse()
    window.setMinimumSize(300, 200)
    controller.expand()
    assert window.size() == QSize(300, 200)
