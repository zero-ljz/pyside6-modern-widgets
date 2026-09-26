"""Opt-in screen-edge docking and auto-hide for floating top-level widgets."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from PySide6.QtCore import (
    QByteArray,
    QEasingCurve,
    QEvent,
    QMetaObject,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QCursor, QMouseEvent, QPainter
from PySide6.QtWidgets import QApplication, QWidget
from shiboken6 import isValid

from ._window_chrome import uses_windows_window_state
from ._windows_window import bring_window_to_front, mouse_buttons_pressed, window_is_at_cursor
from .modern_window import ModernWindow


class DockSide(str, Enum):
    NONE = "none"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


class _DockState(Enum):
    FLOATING = "floating"
    DOCKED = "docked"
    COLLAPSED = "collapsed"
    DISABLED = "disabled"
    DETACHED = "detached"


@dataclass(frozen=True)
class DockConfig:
    """Distances are Qt logical pixels; durations are milliseconds."""

    dock_distance: int = 50
    safe_margin: int = 2
    handle_width: int = 6
    handle_length: int = 80
    handle_color: QColor = field(default_factory=lambda: QColor(150, 150, 150))
    handle_hover_color: QColor = field(default_factory=lambda: QColor(200, 200, 200))
    anim_duration: int = 250
    hide_delay: int = 500
    sides: tuple[DockSide, ...] = (DockSide.LEFT, DockSide.RIGHT, DockSide.TOP)

    def __post_init__(self) -> None:
        for name in ("dock_distance", "safe_margin", "anim_duration", "hide_delay"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.handle_width <= 0 or self.handle_length <= 0:
            raise ValueError("handle dimensions must be positive")
        sides = tuple(DockSide(side) for side in self.sides)
        if not sides or DockSide.NONE in sides:
            raise ValueError("sides must contain at least one screen edge")
        object.__setattr__(self, "sides", sides)


def _edge_rect(rect: QRect, area: QRect, side: DockSide, margin: int) -> QRect:
    """Fit a frame to a work area without assuming a non-negative screen origin."""
    area = area.adjusted(margin, margin, -margin, -margin)
    result = QRect(rect)
    x = min(max(rect.x(), area.left()), max(area.left(), area.right() - rect.width() + 1))
    y = min(max(rect.y(), area.top()), max(area.top(), area.bottom() - rect.height() + 1))
    if side == DockSide.LEFT:
        x = area.left()
    elif side == DockSide.RIGHT:
        x = max(area.left(), area.right() - rect.width() + 1)
    elif side == DockSide.TOP:
        y = area.top()
    elif side == DockSide.BOTTOM:
        y = max(area.top(), area.bottom() - rect.height() + 1)
    result.moveTopLeft(QPoint(x, y))
    return result


class _EdgeHandle(QWidget):
    restored = Signal()

    def __init__(self, target: QWidget, config: DockConfig) -> None:
        super().__init__(
            target,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self._config = config

    def paintEvent(self, event) -> None:
        color = self._config.handle_hover_color if self.underMouse() else self._config.handle_color
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        radius = min(self.width(), self.height()) / 2
        painter.drawRoundedRect(self.rect(), radius, radius)

    def enterEvent(self, event) -> None:
        self.update()
        self.restored.emit()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.restored.emit()
        super().mousePressEvent(event)


class EdgeDockController(QObject):
    """Attach edge docking to a top-level widget without changing its window flags.

    Only empty space in drag_widget (the target by default) starts a drag. Child
    controls retain their input. Pass a dedicated drag strip for custom chrome;
    native/system dragging is not intercepted. Call snap() after external moves.
    The target owns the controller and handle. detach() removes the behavior.
    Only one controller may be attached to a target. Use dismiss() to hide both
    the window and its handle, and setDragWidget() when replacing the drag surface.
    """

    dockSideChanged = Signal(object)
    collapsedChanged = Signal(bool)

    def __init__(
        self,
        target: QWidget,
        config: DockConfig | None = None,
        *,
        drag_widget: QWidget | None = None,
        auto_hide: bool = True,
    ) -> None:
        if not target.isWindow():
            raise ValueError("target must be a top-level widget")
        surface = target if drag_widget is None else drag_widget
        if surface is not target and (surface.isWindow() or not target.isAncestorOf(surface)):
            raise ValueError("drag_widget must belong to target")
        for child in target.children():
            if isinstance(child, EdgeDockController) and child._state != _DockState.DETACHED:
                raise ValueError("target already has an attached EdgeDockController")
        super().__init__(target)
        self._target = target
        self._surface: QWidget | None = None
        self._surface_connection: QMetaObject.Connection | None = None
        self._connections: list[QMetaObject.Connection] = []
        self._config = config or DockConfig()
        self._state: _DockState = _DockState.FLOATING
        self._auto_hide = bool(auto_hide)
        self._side = DockSide.NONE
        self._notified_side = DockSide.NONE
        self._notified_collapsed = False
        self._notifying = False
        self._revision = 0
        self._changing_visibility = False
        self._moving = False
        self._press: QPoint | None = None
        self._dragging = False
        self._system_move = False
        self._saved_cursor: QCursor | None = None
        self._start_pos = QPoint()
        self._handle = _EdgeHandle(target, self._config)
        self._handle.restored.connect(self.expand)
        self.destroyed.connect(self._handle.deleteLater)
        self._animation = QPropertyAnimation(target, QByteArray(b"pos"), self)
        self._animation.setDuration(self._config.anim_duration)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.finished.connect(self._check_auto_hide)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(self._config.hide_delay)
        self._hide_timer.timeout.connect(self.collapse)
        self._monitor = QTimer(self)
        self._monitor.setInterval(200)
        self._monitor.timeout.connect(self._check_auto_hide)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh_geometry)
        self._drag_watch = QTimer(self)
        self._drag_watch.setInterval(30)
        self._drag_watch.timeout.connect(self._check_drag_finished)
        self._snap_timer = QTimer(self)
        self._snap_timer.setSingleShot(True)
        self._snap_timer.timeout.connect(self.snap)
        self._foreground_timer = QTimer(self)
        self._foreground_timer.setSingleShot(True)
        self._foreground_timer.timeout.connect(self._raise_and_activate_target)
        self._foreground_settle_timer = QTimer(self)
        self._foreground_settle_timer.setSingleShot(True)
        self._foreground_settle_timer.timeout.connect(self._check_restored_foreground)
        if isinstance(target, ModernWindow):
            self._connections.append(
                target._system_move_finished.connect(self._complete_system_drag)
            )
        target.installEventFilter(self)
        self.setDragWidget(surface)
        app = QApplication.instance()
        assert isinstance(app, QApplication)
        self._connections.append(app.screenAdded.connect(self._watch_screen))
        self._connections.append(app.screenRemoved.connect(self._schedule_refresh))
        for screen in app.screens():
            self._watch_screen(screen)

    def isEnabled(self) -> bool:
        return self._state not in (_DockState.DISABLED, _DockState.DETACHED)

    def setEnabled(self, enabled: bool) -> None:
        if self._state == _DockState.DETACHED or bool(enabled) == self.isEnabled():
            return
        self._cancel_activity()
        self._transition(
            _DockState.FLOATING if enabled else _DockState.DISABLED,
            show=True if self.isCollapsed() else None,
        )

    def autoHide(self) -> bool:
        return self._auto_hide

    def setAutoHide(self, enabled: bool) -> None:
        if self._state == _DockState.DETACHED:
            return
        self._auto_hide = bool(enabled)
        if not enabled and self.isCollapsed():
            self.expand()
        self._sync_monitor()

    def dockSide(self) -> DockSide:
        return self._side

    def isCollapsed(self) -> bool:
        return self._state == _DockState.COLLAPSED

    def setDragWidget(self, widget: QWidget | None = None) -> None:
        """Bind a drag surface; None selects the target's empty space.

        Destroying the surface suspends dragging until another surface is bound.
        Docking and auto-hide remain available in the meantime.
        """
        if self._state == _DockState.DETACHED:
            return
        surface = self._target if widget is None else widget
        if surface is not self._target and (
            surface.isWindow() or not self._target.isAncestorOf(surface)
        ):
            raise ValueError("drag_widget must belong to target")
        self._finish_drag()
        self._snap_timer.stop()
        self._unbind_surface()
        self._surface = surface
        if surface is not self._target:
            surface.installEventFilter(self)
            self._surface_connection = surface.destroyed.connect(self._surface_destroyed)

    def _unbind_surface(self) -> None:
        if self._surface_connection is not None:
            if self._surface_connection:
                QObject.disconnect(self._surface_connection)
            self._surface_connection = None
        if (
            self._surface is not None
            and isValid(self._surface)
            and self._surface is not self._target
        ):
            self._surface.removeEventFilter(self)
        self._surface = None

    def _surface_destroyed(self) -> None:
        self._surface = None
        self._surface_connection = None
        self._finish_drag()
        self._snap_timer.stop()

    def dismiss(self) -> None:
        """Hide the target and its handle, clearing docking without closing it.

        Use this instead of target.hide() when the target may already be collapsed:
        Qt does not send another Hide event for an already hidden widget.
        """
        if self._state == _DockState.DETACHED:
            return
        self._cancel_activity()
        state = _DockState.FLOATING if self.isEnabled() else _DockState.DISABLED
        self._transition(state, show=False)

    def detach(self) -> None:
        """Restore a collapsed target and permanently remove this controller."""
        if self._state == _DockState.DETACHED:
            return
        self._cancel_activity()
        self._unbind_surface()
        self._target.removeEventFilter(self)
        for connection in self._connections:
            if connection:
                QObject.disconnect(connection)
        self._connections.clear()
        self._transition(_DockState.DETACHED, show=True if self.isCollapsed() else None)

    def _transition(
        self,
        state: _DockState,
        side: DockSide = DockSide.NONE,
        *,
        show: bool | None = None,
        animate: bool = False,
        activate: bool = False,
    ) -> bool:
        """Commit geometry, visibility and timers before notifying observers."""
        assert (side != DockSide.NONE) == (state in (_DockState.DOCKED, _DockState.COLLAPSED))
        self._revision += 1
        revision = self._revision
        self._animation.stop()
        self._hide_timer.stop()
        self._foreground_timer.stop()
        self._foreground_settle_timer.stop()
        self._state, self._side = state, side
        changing = self._changing_visibility
        self._changing_visibility = True
        try:
            if state == _DockState.COLLAPSED:
                self._position()
                if not self._is_current(revision):
                    return False
                self._target.hide()
                if not self._is_current(revision):
                    return False
                self._handle.show()
                self._handle.raise_()
            else:
                self._handle.hide()
                if show is True:
                    self._target.show()
                elif show is False:
                    self._target.hide()
                if not self._is_current(revision):
                    return False
                if state == _DockState.DOCKED:
                    self._position(animate=animate)
        finally:
            self._changing_visibility = changing
        if not self._is_current(revision):
            return False
        self._sync_monitor()
        if activate:
            self._schedule_foreground()
        self._publish_state()
        return self._is_current(revision)

    def _is_current(self, revision: int) -> bool:
        # A widget's show/hide/move handler can itself invoke another transition.
        return isValid(self) and self._revision == revision

    def _publish_state(self) -> None:
        # Slots may immediately disable, detach, dismiss or reopen the target.
        # Emit only committed values and reconcile again after each callback.
        if self._notifying:
            return
        self._notifying = True
        try:
            while isValid(self):
                if self._notified_side != self._side:
                    self._notified_side = self._side
                    self.dockSideChanged.emit(self._side)
                elif self._notified_collapsed != self.isCollapsed():
                    self._notified_collapsed = self.isCollapsed()
                    self.collapsedChanged.emit(self.isCollapsed())
                else:
                    break
        finally:
            self._notifying = False

    def _screen(self, point: QPoint | None = None):
        center = self._target.frameGeometry().center() if point is None else point
        return QApplication.screenAt(center) or self._target.screen()

    def snap(self) -> None:
        """Snap near or beyond an enabled edge; keep released windows on screen."""
        if not self.isEnabled() or not self._target.isVisible():
            return
        if self._target.isMaximized() or self._target.isFullScreen():
            return
        frame = self._target.frameGeometry()
        screen = self._screen()
        if screen is None:
            return
        area = screen.availableGeometry()
        # Signed gaps: crossing an edge must not move the window out of snap range.
        # At corners, prefer the greatest overflow, then configuration order.
        distances = {
            DockSide.LEFT: frame.left() - area.left(),
            DockSide.RIGHT: area.right() - frame.right(),
            DockSide.TOP: frame.top() - area.top(),
            DockSide.BOTTOM: area.bottom() - frame.bottom(),
        }
        side = min(self._config.sides, key=distances.__getitem__)
        if distances[side] <= self._config.dock_distance:
            self.dock(side)
        else:
            # Disabled edges still constrain the released frame, without auto-hide.
            rect = _edge_rect(frame, area, DockSide.NONE, self._config.safe_margin)
            if not self._transition(_DockState.FLOATING):
                return
            if rect != frame:
                self._move_frame(rect, animate=True)

    def dock(self, side: DockSide | str) -> None:
        """Explicitly dock to an enabled edge, or undock with DockSide.NONE."""
        side = DockSide(side)
        if side != DockSide.NONE and side not in self._config.sides:
            raise ValueError("side is not enabled in DockConfig.sides")
        if not self.isEnabled():
            return
        if side == DockSide.NONE:
            self._cancel_activity()
            self._transition(_DockState.FLOATING, show=True if self.isCollapsed() else None)
            return
        if (
            not self._target.isVisible()
            or self._target.isMaximized()
            or self._target.isFullScreen()
        ):
            return
        self._cancel_activity()
        self._transition(_DockState.DOCKED, side, animate=True)

    def _position(self, *, animate: bool = False) -> None:
        screen = self._screen()
        if screen is None or self._side == DockSide.NONE:
            return
        frame = self._target.frameGeometry()
        rect = _edge_rect(frame, screen.availableGeometry(), self._side, self._config.safe_margin)
        self._move_frame(rect, animate=animate)
        if isValid(self) and self.isCollapsed():
            self._position_handle(rect, screen.availableGeometry())

    def _move_frame(self, rect: QRect, *, animate: bool) -> None:
        end = self._target.pos() + rect.topLeft() - self._target.frameGeometry().topLeft()
        self._animation.stop()
        if animate and self._config.anim_duration:
            self._animation.setStartValue(self._target.pos())
            self._animation.setEndValue(end)
            self._animation.start()
        else:
            self._moving = True
            try:
                self._target.move(end)
            finally:
                self._moving = False

    def _position_handle(self, frame: QRect, area: QRect) -> None:
        cfg = self._config
        vertical = self._side in (DockSide.LEFT, DockSide.RIGHT)
        width, height = (
            (cfg.handle_width, cfg.handle_length)
            if vertical
            else (cfg.handle_length, cfg.handle_width)
        )
        width = min(width, max(1, area.width() - 2 * cfg.safe_margin))
        height = min(height, max(1, area.height() - 2 * cfg.safe_margin))
        rect = QRect(0, 0, width, height)
        rect.moveCenter(frame.center())
        self._handle.setGeometry(_edge_rect(rect, area, self._side, cfg.safe_margin))

    def _can_hide(self) -> bool:
        return (
            self._state == _DockState.DOCKED
            and self._auto_hide
            and self._target.isVisible()
            and not self._target.isMinimized()
            and not self._target.isMaximized()
            and not self._target.isFullScreen()
            and self._press is None
            and self._animation.state() != QPropertyAnimation.State.Running
            and not self._buttons_pressed()
            and QApplication.activePopupWidget() is None
            and QApplication.activeModalWidget() is None
            and not self._target.frameGeometry().adjusted(-10, -10, 10, 10).contains(QCursor.pos())
        )

    def _sync_monitor(self) -> None:
        active = self._state == _DockState.DOCKED and self._auto_hide and self._target.isVisible()
        if active:
            self._monitor.start()
        else:
            self._monitor.stop()
            self._hide_timer.stop()

    def _check_auto_hide(self) -> None:
        if self._can_hide():
            if not self._hide_timer.isActive():
                self._hide_timer.start()
        else:
            self._hide_timer.stop()

    def collapse(self) -> None:
        """Auto-hide only when idle, outside the window, and without open popups."""
        if not self._can_hide():
            return
        self._cancel_activity()
        self._transition(_DockState.COLLAPSED, self._side)

    def _raise_and_activate_target(self) -> None:
        """Restore the target to the foreground without changing its topmost flag."""
        if not self.isEnabled() or self.isCollapsed() or not self._target.isVisible():
            return
        self._target.raise_()
        self._target.activateWindow()
        handle = self._target.windowHandle()
        if handle is not None:
            bring_window_to_front(int(handle.winId()))

    def _schedule_foreground(self) -> None:
        if not self.isEnabled() or self.isCollapsed() or not self._target.isVisible():
            return
        self._raise_and_activate_target()
        self._foreground_timer.start(0)
        if uses_windows_window_state():
            self._foreground_settle_timer.start(150)

    def _check_restored_foreground(self) -> None:
        if (
            not self.isEnabled()
            or self.isCollapsed()
            or not self._target.isVisible()
            or not self._target.frameGeometry().contains(QCursor.pos())
            or QApplication.activePopupWidget() is not None
            or QApplication.activeModalWidget() is not None
        ):
            return
        handle = self._target.windowHandle()
        if handle is not None and window_is_at_cursor(int(handle.winId())) is False:
            self._raise_and_activate_target()

    def expand(self) -> None:
        """Show the target and remove its edge handle, including external reopens."""
        if self._state == _DockState.DETACHED:
            return
        state = _DockState.DOCKED if self.isCollapsed() else self._state
        self._transition(state, self._side, show=True, activate=True)

    def _finish_drag(self) -> None:
        was_system_move = self._system_move
        self._drag_watch.stop()
        self._system_move = False
        self._press = None
        self._dragging = False
        if self._saved_cursor is not None:
            if self._surface is not None and isValid(self._surface):
                self._surface.setCursor(self._saved_cursor)
            self._saved_cursor = None
        if was_system_move and isValid(self._target) and isinstance(self._target, ModernWindow):
            self._target._finish_system_move()

    def _cancel_activity(self) -> None:
        for timer in (
            self._monitor,
            self._hide_timer,
            self._refresh_timer,
            self._snap_timer,
            self._foreground_timer,
            self._foreground_settle_timer,
        ):
            timer.stop()
        self._animation.stop()
        self._finish_drag()

    def _reset(self) -> None:
        self._cancel_activity()
        self._transition(_DockState.FLOATING)

    def _start_system_drag(self, position: QPoint) -> bool:
        # Mark the handoff before entering the OS move loop: it can release Qt's
        # mouse grab and dispatch the finish notification before this call returns.
        self._system_move = True
        self._drag_watch.start()
        if isinstance(self._target, ModernWindow):
            started = self._target.startSystemMove(position)
        else:
            handle = self._target.windowHandle()
            started = handle is not None and handle.startSystemMove()
        if not started:
            self._system_move = False
            self._drag_watch.stop()
        return started

    def _complete_system_drag(self) -> None:
        if not self._system_move:
            return
        moved = self._target.pos() != self._start_pos
        self._finish_drag()
        # Let native DPI changes and Qt's release handler settle before snapping.
        if moved:
            self._snap_timer.start(0)

    def _check_drag_finished(self) -> None:
        if not self._buttons_pressed(left_only=True):
            self._complete_system_drag()

    @staticmethod
    def _buttons_pressed(*, left_only: bool = False) -> bool:
        pressed = (
            mouse_buttons_pressed(left_only=left_only) if uses_windows_window_state() else None
        )
        if pressed is None:
            buttons = QApplication.mouseButtons()
            return bool(buttons & Qt.MouseButton.LeftButton) if left_only else bool(buttons)
        return pressed

    def _watch_screen(self, screen) -> None:
        if self._state == _DockState.DETACHED:
            return
        self._connections.extend(
            (
                screen.availableGeometryChanged.connect(self._schedule_refresh),
                screen.geometryChanged.connect(self._schedule_refresh),
                screen.logicalDotsPerInchChanged.connect(self._schedule_refresh),
            )
        )
        self._schedule_refresh()

    def _schedule_refresh(self, *args) -> None:
        if self.isEnabled() and self._side != DockSide.NONE:
            self._refresh_timer.start(0)

    def _refresh_geometry(self) -> None:
        if self.isEnabled() and self._side != DockSide.NONE:
            self._position()
            self._handle.update()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if not self.isEnabled():
            return False
        kind = event.type()
        if watched is self._target:
            if kind == QEvent.Type.Close:
                # Close is a request, not a completed hide. Restore first so a
                # veto or a confirmation dialog cannot strand a hidden target.
                # An accepted close subsequently sends Hide and clears state.
                if self.isCollapsed() and not self._changing_visibility:
                    self.expand()
            elif kind == QEvent.Type.Hide:
                if not self._changing_visibility:
                    self._reset()
            elif kind == QEvent.Type.Show:
                if not self._changing_visibility:
                    if self.isCollapsed():
                        self._transition(_DockState.DOCKED, self._side, activate=True)
                    else:
                        self._sync_monitor()
            elif kind == QEvent.Type.WindowStateChange:
                self._reset()
            elif kind in (QEvent.Type.Resize, QEvent.Type.ScreenChangeInternal):
                self._schedule_refresh()
            elif (
                kind == QEvent.Type.Move
                and not self._moving
                and not self._changing_visibility
                and not self.isCollapsed()
                and self._animation.state() != QPropertyAnimation.State.Running
            ):
                self._transition(_DockState.FLOATING)
        if self._surface is not None and watched is self._surface:
            if kind == QEvent.Type.Enter:
                self._hide_timer.stop()
            elif kind == QEvent.Type.UngrabMouse and not self._system_move:
                self._finish_drag()
            if not isinstance(event, QMouseEvent):
                return False
            if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                if (
                    self._target.isMaximized()
                    or self._target.isFullScreen()
                    or self._surface.childAt(event.position().toPoint()) is not None
                ):
                    return False
                self._animation.stop()
                self._snap_timer.stop()
                self._hide_timer.stop()
                self._press = event.globalPosition().toPoint()
                self._start_pos = self._target.pos()
                self._start_system_drag(self._press)
                return True
            if kind == QEvent.Type.MouseMove and self._press is not None:
                if self._system_move:
                    return False
                if not event.buttons() & Qt.MouseButton.LeftButton:
                    self._finish_drag()
                    return False
                delta = event.globalPosition().toPoint() - self._press
                if (
                    not self._dragging
                    and delta.manhattanLength() < QApplication.startDragDistance()
                ):
                    return True
                if not self._dragging:
                    self._dragging = True
                    self._saved_cursor = self._surface.cursor()
                    self._surface.setCursor(Qt.CursorShape.ClosedHandCursor)
                    if not self._transition(_DockState.FLOATING):
                        return True
                # Do not clamp during a drag: the pointer can cross onto another monitor.
                self._target.move(self._start_pos + delta)
                return True
            if (
                kind == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
                and self._press is not None
            ):
                dragging = self._dragging
                if self._system_move:
                    self._complete_system_drag()
                    return False
                self._finish_drag()
                if dragging:
                    self.snap()
                return True
        return False
