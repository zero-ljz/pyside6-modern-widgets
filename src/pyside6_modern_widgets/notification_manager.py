"""Bounded, thread-safe notification requests and GUI-thread delivery."""

from __future__ import annotations

import threading
import weakref
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import Enum
from uuid import uuid4

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QScreen
from PySide6.QtWidgets import QApplication, QWidget
from shiboken6 import isValid

from .modern_notification import ModernNotification
from .notification import (
    _UNSET,
    NotificationAction,
    NotificationKind,
    NotificationSnapshot,
    NotificationState,
    _patch,
    _timeout,
    _Unset,
)
from .theme import DEFAULT_METRICS, ModernMetrics, ModernTheme, inherited_theme, theme_manager


class NotificationPosition(str, Enum):
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"


def _non_negative(value: int, name: str) -> int:
    if type(value) is not int or not 0 <= value <= 2_147_483_647:
        raise ValueError(f"{name} must be an integer from 0 to 2147483647")
    return value


class NotificationHandle:
    """One notification lifetime, including the time before GUI delivery.

    update(), dismiss(), pauseTimeout(), resumeTimeout(), and snapshot queries
    are thread-safe. True means a command was accepted, not that Qt has painted
    it. Closed handles retain their final snapshot and reject further commands.
    Only widget() requires the GUI thread; its result is a borrowed Qt view.
    """

    def __init__(
        self, store: _NotificationStore, data: NotificationSnapshot, screen: QScreen | None
    ) -> None:
        self._store = store
        self._data = data
        self._screen = screen
        self._timeout_revision = 0

    def id(self) -> str:
        return self._data.id

    def snapshot(self) -> NotificationSnapshot:
        with self._store.lock:
            data = self._data
            return replace(data, icon=QIcon(data.icon) if data.icon is not None else None)

    def state(self) -> NotificationState:
        with self._store.lock:
            return self._data.state

    def isClosed(self) -> bool:
        return self.state() == NotificationState.CLOSED

    def closeReason(self) -> str | None:
        with self._store.lock:
            return self._data.close_reason

    def update(
        self,
        *,
        title: str | _Unset = _UNSET,
        message: str | _Unset = _UNSET,
        kind: NotificationKind | str | _Unset = _UNSET,
        timeout_ms: int | None | _Unset = _UNSET,
        actions: Iterable[NotificationAction] | _Unset = _UNSET,
        progress: int | None | _Unset = _UNSET,
        icon: QIcon | None | _Unset = _UNSET,
    ) -> bool:
        """Patch supplied fields. None makes timeout persistent or clears progress/icon.

        actions=[] removes the actions. An explicit timeout restarts the clock;
        other fields preserve it. Validation is atomic and runs on the caller.
        """
        return self._store.change(
            self,
            _patch(
                title=title,
                message=message,
                kind=kind,
                timeout_ms=timeout_ms,
                actions=actions,
                progress=progress,
                icon=icon,
            ),
        )

    def dismiss(self) -> bool:
        """Cancel this lifetime, even if delivery has not started."""
        return self._store.close(self, "dismissed")

    def pauseTimeout(self) -> bool:
        """Pause expiry independently of hover, focus, and delivery suspension."""
        return self._store.change(self, {"timeout_paused": True})

    def resumeTimeout(self) -> bool:
        return self._store.change(self, {"timeout_paused": False})

    def widget(self) -> ModernNotification | None:
        """Borrow the current view on the GUI thread, or None before/after its lifetime.

        Content, geometry and visibility belong to the manager. Use update() for
        content; the view is available for visual inspection and Qt integration.
        """
        manager = self._store.manager()
        if manager is None or not isValid(manager):
            return None
        manager._check_thread()
        record = manager._records.get(self)
        return record.card if record is not None and not self.isClosed() else None


class _NotificationStore:
    """Pure Python state; no QWidget/QTimer operations while holding this lock.

    A dirty entry holds the latest accepted content, not a list of commands.
    Closed entries occupy capacity until GUI cleanup, keeping both queues bounded.
    """

    def __init__(self, manager: NotificationManager, capacity: int, timeout_ms: int | None):
        self.manager = weakref.ref(manager)
        self.capacity = capacity
        self.default_timeout = timeout_ms
        self.lock = threading.RLock()
        self.entries: dict[str, NotificationHandle] = {}
        self.dirty: dict[str, NotificationHandle] = {}
        self.alive = True
        self.wake_pending = False

    def request(self, *, deferred: bool = False) -> None:
        manager = self.manager()
        if manager is None or not isValid(manager):
            self.shutdown()
            return
        try:
            manager._request_sync(deferred=deferred)
        except RuntimeError:
            if isValid(manager):
                raise
            self.shutdown()

    def accept(
        self, content: dict, screen: QScreen | None, *, deferred: bool
    ) -> NotificationHandle:
        with self.lock:
            if not self.alive:
                raise RuntimeError("NotificationManager has been destroyed")
            if len(self.entries) >= self.capacity:
                raise OverflowError(
                    "Notification capacity reached; update or dismiss an existing handle"
                )
            data = NotificationSnapshot(id=uuid4().hex, **content)
            handle = NotificationHandle(self, data, screen)
            self.entries[data.id] = handle
            self.dirty[data.id] = handle
        self.request(deferred=deferred)
        return handle

    def change(self, handle: NotificationHandle, changes: dict) -> bool:
        with self.lock:
            if not self.alive or handle._data.state == NotificationState.CLOSED:
                return False
            if changes:
                handle._data = replace(handle._data, **changes)
                if "timeout_ms" in changes:
                    handle._timeout_revision += 1
                self.dirty[handle.id()] = handle
        if changes:
            self.request()
        return True

    def _close_locked(self, handle: NotificationHandle, reason: str) -> bool:
        if not self.alive or handle._data.state == NotificationState.CLOSED:
            return False
        handle._data = replace(handle._data, state=NotificationState.CLOSED, close_reason=reason)
        self.dirty[handle.id()] = handle
        return True

    def close(self, handle: NotificationHandle, reason: str) -> bool:
        with self.lock:
            accepted = self._close_locked(handle, reason)
        if accepted:
            self.request()
        return accepted

    def clear(self) -> None:
        with self.lock:
            for handle in self.entries.values():
                self._close_locked(handle, "cleared")
        self.request()

    def set_state(self, handle: NotificationHandle, state: NotificationState) -> bool:
        with self.lock:
            if handle._data.state == NotificationState.CLOSED:
                return False
            handle._data = replace(handle._data, state=state)
            return True

    def has_dirty(self) -> bool:
        with self.lock:
            return bool(self.dirty)

    def retire(self, handle: NotificationHandle) -> bool:
        with self.lock:
            self.dirty.pop(handle.id(), None)
            return self.entries.pop(handle.id(), None) is not None

    def shutdown(self, *_args) -> None:
        with self.lock:
            self.alive = False
            for handle in self.entries.values():
                if handle._data.state != NotificationState.CLOSED:
                    handle._data = replace(
                        handle._data, state=NotificationState.CLOSED, close_reason="destroyed"
                    )
            self.entries.clear()
            self.dirty.clear()
            self.wake_pending = False


@dataclass
class _Notification:
    card: ModernNotification
    timer: QTimer
    remaining: int | None
    timeout_revision: int = -1
    visible: bool = False
    shown: bool = False
    hovered: bool = False
    focused: bool = False


class NotificationManager(QObject):
    """Own bounded notification lifetimes and FIFO stacks per screen.

    notify() is a GUI-thread create; post() is its asynchronous, thread-safe
    counterpart. Both always return a new handle. Handle commands and clear()
    include requests awaiting delivery. capacity limits all accepted lifetimes,
    including ones awaiting GUI cleanup; a full manager raises OverflowError.
    """

    notificationShown = Signal(object)
    notificationClosed = Signal(object, str)
    notificationActivated = Signal(object)
    actionTriggered = Signal(object, str)
    countChanged = Signal(int, int, int)
    deliveryFailed = Signal(object, str)
    _wake = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        position: NotificationPosition | str = NotificationPosition.BOTTOM_RIGHT,
        max_visible: int = 3,
        capacity: int = 100,
        width: int = 360,
        margin: int = 16,
        spacing: int = 12,
        default_timeout_ms: int | None = 5000,
        desktop: bool | None = None,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        app = QApplication.instance()
        if not isinstance(app, QApplication) or QThread.currentThread() != app.thread():
            raise RuntimeError("Create NotificationManager on the QApplication GUI thread")
        position = NotificationPosition(position)
        if _non_negative(max_visible, "max_visible") == 0:
            raise ValueError("max_visible must be positive")
        if _non_negative(capacity, "capacity") == 0:
            raise ValueError("capacity must be positive")
        if _non_negative(width, "width") < 160:
            raise ValueError("width must be at least 160 logical pixels")
        _non_negative(margin, "margin")
        _non_negative(spacing, "spacing")
        _timeout(default_timeout_ms)
        wayland = QApplication.platformName().startswith("wayland")
        if wayland and desktop:
            raise ValueError("Wayland requires in-window notifications (desktop=False)")
        desktop = not wayland if desktop is None else desktop
        if not desktop and parent is None:
            raise ValueError("In-window notifications require a host QWidget")
        super().__init__(parent)
        self._gui_thread = threading.get_ident()
        self._owner = weakref.ref(parent) if parent is not None else None
        self._desktop = desktop
        self._position = position
        self._max_visible = max_visible
        self._width, self._margin, self._spacing = width, margin, spacing
        self._theme_override = theme
        self._metrics = metrics
        self._records: dict[NotificationHandle, _Notification] = {}
        self._screen: QScreen | None = None
        self._counts = (0, 0, 0)
        self._syncing = False
        self._sync_pending = False
        self._rendering = False
        self._delivery_paused = False
        self._store = _NotificationStore(self, capacity, default_timeout_ms)
        self.destroyed.connect(self._store.shutdown)
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.timeout.connect(self._flush)
        self._wake.connect(self._on_wake, Qt.ConnectionType.QueuedConnection)
        app.screenAdded.connect(self._screen_added)
        app.screenRemoved.connect(self._screen_removed)
        app.focusChanged.connect(self._focus_changed)
        app.aboutToQuit.connect(self.clear)
        theme_manager().themeChanged.connect(self._theme_changed)
        for screen in app.screens():
            self._screen_added(screen)
        if parent is not None:
            parent.installEventFilter(self)

    def _check_thread(self) -> None:
        if threading.get_ident() != self._gui_thread:
            raise RuntimeError("Use post() and notification handles from a worker thread")

    def _host(self) -> QWidget | None:
        host = self._owner() if self._owner is not None else None
        return host if host is not None and isValid(host) else None

    def isDesktop(self) -> bool:
        return self._desktop

    def position(self) -> NotificationPosition:
        return self._position

    def setPosition(self, position: NotificationPosition | str) -> None:
        self._check_thread()
        self._position = NotificationPosition(position)
        self._schedule()

    def setScreen(self, screen: QScreen | None) -> None:
        """Choose the default screen; None follows the host, then the primary screen."""
        self._check_thread()
        self._validate_screen(screen)
        self._screen = screen
        self._schedule()

    def screen(self) -> QScreen | None:
        self._check_thread()
        return self._screen

    def setMaxVisible(self, count: int) -> None:
        self._check_thread()
        if _non_negative(count, "count") == 0:
            raise ValueError("count must be positive")
        self._max_visible = count
        self._schedule()

    def maxVisible(self) -> int:
        return self._max_visible

    def capacity(self) -> int:
        return self._store.capacity

    def setDeliveryPaused(self, paused: bool) -> None:
        """Hide cards and pause their clocks without dropping any accepted request."""
        self._check_thread()
        self._delivery_paused = bool(paused)
        self._flush()

    def isDeliveryPaused(self) -> bool:
        return self._delivery_paused

    def theme(self) -> ModernTheme:
        if self._theme_override is not None:
            return self._theme_override
        host = self._host()
        if host is not None:
            get_theme = getattr(host, "theme", None)
            if callable(get_theme):
                theme = get_theme()
                if isinstance(theme, ModernTheme):
                    return theme
            return inherited_theme(host)
        return theme_manager().theme()

    def setTheme(self, theme: ModernTheme | None) -> None:
        self._check_thread()
        self._theme_override = theme
        self._theme_changed()

    def _theme_changed(self, *_args) -> None:
        for record in list(self._records.values()):
            if isValid(record.card):
                record.card._inherited_theme = self.theme()
                record.card._apply_theme()

    @staticmethod
    def _validate_screen(screen: QScreen | None) -> None:
        if screen is not None and (not isValid(screen) or screen not in QApplication.screens()):
            raise ValueError("screen must be a currently connected QScreen")

    def _content(self, title, message, kind, timeout_ms, actions, progress, icon) -> dict:
        return _patch(
            title=title,
            message=message,
            kind=kind,
            timeout_ms=self._store.default_timeout
            if isinstance(timeout_ms, _Unset)
            else timeout_ms,
            actions=actions,
            progress=progress,
            icon=icon,
        )

    @Slot(str, str, result=object)
    def notify(
        self,
        title: str,
        message: str = "",
        *,
        kind: NotificationKind | str = NotificationKind.INFO,
        timeout_ms: int | None | _Unset = _UNSET,
        actions: Iterable[NotificationAction] = (),
        progress: int | None = None,
        screen: QScreen | None = None,
        icon: QIcon | None = None,
    ) -> NotificationHandle:
        """Create a new notification on the GUI thread. None means no timeout."""
        self._check_thread()
        self._validate_screen(screen)
        content = self._content(title, message, kind, timeout_ms, actions, progress, icon)
        # Release closed capacity and preserve FIFO order with already accepted posts.
        self._flush()
        return self._store.accept(content, screen, deferred=False)

    def post(
        self,
        title: str,
        message: str = "",
        *,
        kind: NotificationKind | str = NotificationKind.INFO,
        timeout_ms: int | None | _Unset = _UNSET,
        actions: Iterable[NotificationAction] = (),
        progress: int | None = None,
        icon: QIcon | None = None,
    ) -> NotificationHandle:
        """Thread-safe asynchronous create on the default screen.

        Content is copied and accepted before returning. The returned handle can
        immediately update or cancel it. Full capacity raises OverflowError on
        the caller; it never silently removes a different notification.
        """
        content = self._content(title, message, kind, timeout_ms, actions, progress, icon)
        return self._store.accept(content, None, deferred=True)

    def notifications(
        self, state: NotificationState | str | None = None
    ) -> tuple[NotificationHandle, ...]:
        """Thread-safe, ordered snapshot of live handles, including pending posts."""
        selected = NotificationState(state) if state is not None else None
        with self._store.lock:
            return tuple(
                handle
                for handle in self._store.entries.values()
                if handle._data.state != NotificationState.CLOSED
                and (selected is None or handle._data.state == selected)
            )

    @Slot()
    def clear(self) -> None:
        """Thread-safe cancellation of every lifetime accepted before this call.

        All are marked closed together. Requests created later, including from
        close callbacks, are independent of this batch.
        """
        self._store.clear()

    def _request_sync(self, *, deferred: bool = False) -> None:
        if threading.get_ident() == self._gui_thread and not deferred:
            self._flush()
            return
        with self._store.lock:
            if not self._store.alive or self._store.wake_pending:
                return
            self._store.wake_pending = True
            self._wake.emit()

    @Slot()
    def _on_wake(self) -> None:
        with self._store.lock:
            self._store.wake_pending = False
        self._flush()

    def _schedule(self, *_args) -> None:
        self._sync_pending = True
        if not self._syncing:
            self._layout_timer.start(0)

    def _card_content_changed(self) -> None:
        if not self._rendering:
            self._schedule()

    def _flush(self) -> None:
        if self._syncing:
            self._sync_pending = True
            return
        self._syncing = True
        self._sync_pending = False
        self._layout_timer.stop()
        closed: list[NotificationHandle] = []
        try:
            with self._store.lock:
                batch = list(self._store.dirty.values())
                self._store.dirty.clear()
            for handle in batch:
                if not handle.isClosed():
                    try:
                        self._sync_record(handle)
                    except (RuntimeError, ValueError, TypeError) as error:
                        if not isValid(self):
                            return
                        self._store.close(handle, "failed")
                        self.deliveryFailed.emit(handle, str(error))
                if handle.isClosed():
                    self._remove_record(handle)
                    if self._store.retire(handle):
                        closed.append(handle)
            # A content observer can clear the batch during rendering. Close its
            # remaining views before publishing any close callbacks or new shows.
            for handle in list(self._records):
                if handle.isClosed():
                    self._remove_record(handle)
                    if self._store.retire(handle):
                        closed.append(handle)
            if not self._sync_pending and not self._store.has_dirty():
                self._reflow()
            self._emit_counts()
            for handle in closed:
                if not isValid(self):
                    return
                self.notificationClosed.emit(handle, handle.closeReason())
        finally:
            self._syncing = False
            if isValid(self) and (self._sync_pending or self._store.has_dirty()):
                self._layout_timer.start(0)

    def _sync_record(self, handle: NotificationHandle) -> None:
        with self._store.lock:
            data, revision = handle._data, handle._timeout_revision
        record = self._records.get(handle)
        if record is None:
            host = self._host()
            card = ModernNotification(parent=None if self._desktop else host, metrics=self._metrics)
            if self._desktop:
                card._configure_desktop()
            if host is not None:
                card.setFont(host.font())
                card.setLayoutDirection(host.layoutDirection())
            card._inherited_theme = self.theme()
            card._apply_theme()
            card._managed = True
            timer = QTimer(self)
            timer.setSingleShot(True)
            record = _Notification(card, timer, data.timeout_ms)
            self._records[handle] = record
            timer.timeout.connect(lambda handle=handle: self._expire(handle))
            self.destroyed.connect(card.deleteLater)
            card.dismissed.connect(lambda reason, handle=handle: self._store.close(handle, reason))
            card.destroyed.connect(lambda _obj=None, handle=handle: self._card_destroyed(handle))
            card.actionTriggered.connect(
                lambda action, handle=handle: self._action_triggered(handle, action)
            )
            card.activated.connect(lambda handle=handle: self._activated(handle))
            card.hoveredChanged.connect(
                lambda hovered, handle=handle: self._hover_changed(handle, hovered)
            )
            card.contentChanged.connect(self._card_content_changed)
        self._rendering = True
        try:
            record.card._apply_content(data)
        finally:
            self._rendering = False
        if handle.isClosed() or not isValid(self) or not isValid(record.card):
            return
        if revision != record.timeout_revision:
            record.timer.stop()
            record.remaining = data.timeout_ms
            record.timeout_revision = revision
        if data.timeout_paused:
            self._stop_clock(record)
        else:
            self._resume(handle, record)
        if handle.state() == NotificationState.PENDING:
            self._store.set_state(handle, NotificationState.QUEUED)

    def _remove_record(self, handle: NotificationHandle) -> None:
        record = self._records.pop(handle, None)
        if record is None:
            return
        if isValid(record.timer):
            record.timer.stop()
            record.timer.deleteLater()
        if isValid(record.card):
            record.card.hide()
            record.card.deleteLater()

    def _card_destroyed(self, handle: NotificationHandle) -> None:
        if isValid(self):
            self._store.close(handle, "destroyed")

    def _action_triggered(self, handle: NotificationHandle, action: str) -> None:
        if isValid(self) and not handle.isClosed():
            self.actionTriggered.emit(handle, action)

    def _activated(self, handle: NotificationHandle) -> None:
        if isValid(self) and not handle.isClosed():
            self.notificationActivated.emit(handle)

    def _expire(self, handle: NotificationHandle) -> None:
        record = self._records.get(handle)
        if record is None or handle.isClosed():
            return
        with self._store.lock:
            stale = handle._timeout_revision != record.timeout_revision
            paused = handle._data.timeout_paused
            # Expiry and worker changes must share one acceptance boundary.
            # Otherwise a newly accepted timeout/pause can lose to this old timer.
            accepted = not (stale or paused) and self._store._close_locked(handle, "expired")
        if stale or paused:
            self._flush()
        elif accepted:
            self._store.request()

    @staticmethod
    def _stop_clock(record: _Notification) -> None:
        if record.timer.isActive():
            record.remaining = max(1, record.timer.remainingTime())
            record.timer.stop()

    def _resume(self, handle: NotificationHandle, record: _Notification) -> None:
        with self._store.lock:
            paused = handle._data.timeout_paused or handle._data.state == NotificationState.CLOSED
        if (
            record.visible
            and not paused
            and not record.hovered
            and not record.focused
            and record.remaining is not None
            and not record.timer.isActive()
        ):
            record.timer.start(record.remaining)

    def _hover_changed(self, handle: NotificationHandle, hovered: bool) -> None:
        if not isValid(self) or handle.isClosed():
            return
        record = self._records.get(handle)
        if record is not None:
            record.hovered = hovered
            if hovered:
                self._stop_clock(record)
            else:
                self._resume(handle, record)

    def _focus_changed(self, _old: QWidget | None, new: QWidget | None) -> None:
        for handle, record in list(self._records.items()):
            if handle.isClosed() or not isValid(record.card):
                continue
            record.focused = new is not None and (
                new is record.card or record.card.isAncestorOf(new)
            )
            if record.focused:
                self._stop_clock(record)
            else:
                self._resume(handle, record)

    def _screen_added(self, screen: QScreen) -> None:
        screen.availableGeometryChanged.connect(self._schedule)
        screen.geometryChanged.connect(self._schedule)
        screen.logicalDotsPerInchChanged.connect(self._schedule)
        self._schedule()

    def _screen_removed(self, screen: QScreen) -> None:
        if self._screen is screen:
            self._screen = None
        with self._store.lock:
            for handle in self._store.entries.values():
                if handle._screen is screen:
                    handle._screen = None
        self._schedule()

    def _target_screen(self, handle: NotificationHandle) -> QScreen | None:
        screens = QApplication.screens()
        for screen in (handle._screen, self._screen):
            if screen is not None and isValid(screen) and screen in screens:
                return screen
        host = self._host()
        return host.screen() if host is not None else QApplication.primaryScreen()

    def eventFilter(self, watched, event) -> bool:
        if isinstance(watched, QWidget) and watched is self._host():
            if event.type() in (
                QEvent.Type.Resize,
                QEvent.Type.Move,
                QEvent.Type.Show,
                QEvent.Type.Hide,
                QEvent.Type.WindowStateChange,
            ):
                self._schedule()
            elif event.type() == QEvent.Type.PaletteChange:
                self._theme_changed()
            elif event.type() in (QEvent.Type.FontChange, QEvent.Type.LayoutDirectionChange):
                for record in list(self._records.values()):
                    if isValid(record.card):
                        record.card.setFont(watched.font())
                        record.card.setLayoutDirection(watched.layoutDirection())
                self._schedule()
        return super().eventFilter(watched, event)

    def _reflow(self) -> None:
        host = self._host()
        can_show = not self._delivery_paused and (
            self._desktop
            or (host is not None and host.isVisible() and not host.window().isMinimized())
        )
        groups: dict[QScreen | None, list[tuple[NotificationHandle, _Notification]]] = defaultdict(
            list
        )
        for handle, record in list(self._records.items()):
            groups[self._target_screen(handle) if self._desktop else None].append((handle, record))
        for screen, records in groups.items():
            bounds = (
                screen.availableGeometry()
                if screen is not None
                else (host.rect() if host is not None else QRect())
            )
            area = bounds.adjusted(self._margin, self._margin, -self._margin, -self._margin)
            used, count = 0, 0
            for handle, record in records:
                if self._sync_pending or self._store.has_dirty() or not isValid(self):
                    return
                if handle.isClosed():
                    continue
                remaining = area.height() - used
                show = (
                    can_show
                    and area.width() >= 120
                    and remaining >= 80
                    and count < self._max_visible
                )
                if not show:
                    self._stop_clock(record)
                    record.visible = False
                    self._store.set_state(
                        handle,
                        NotificationState.SUSPENDED if record.shown else NotificationState.QUEUED,
                    )
                    record.card.hide()
                    # Hidden cards cannot retain a stale hover pause after resuming.
                    record.hovered = False
                    continue
                size = record.card._fit_size(min(self._width, area.width()), min(360, remaining))
                right = self._position in (
                    NotificationPosition.TOP_RIGHT,
                    NotificationPosition.BOTTOM_RIGHT,
                )
                bottom = self._position in (
                    NotificationPosition.BOTTOM_LEFT,
                    NotificationPosition.BOTTOM_RIGHT,
                )
                x = area.right() - size.width() + 1 if right else area.left()
                y = area.bottom() - used - size.height() + 1 if bottom else area.top() + used
                target = QPoint(x, y)
                was_visible = record.visible
                record.card._move_to(
                    target, record.visible and area.contains(record.card.geometry())
                )
                record.visible = True
                self._store.set_state(handle, NotificationState.VISIBLE)
                record.card.show()
                if handle.isClosed() or not isValid(record.card):
                    return
                record.card.raise_()
                if not was_visible and self._metrics.animation_duration > 0:
                    start = target + QPoint(0, -12 if bottom else 12)
                    if area.contains(QRect(start, size)):
                        record.card.move(start)
                        record.card._move_to(target, True)
                self._resume(handle, record)
                used += size.height() + self._spacing
                count += 1
                if not record.shown:
                    record.shown = True
                    self.notificationShown.emit(handle)

    def _emit_counts(self) -> None:
        if not isValid(self):
            return
        with self._store.lock:
            states = [
                handle._data.state
                for handle in self._store.entries.values()
                if handle._data.state != NotificationState.CLOSED
            ]
        visible = states.count(NotificationState.VISIBLE)
        suspended = states.count(NotificationState.SUSPENDED)
        counts = (visible, len(states) - visible - suspended, suspended)
        if counts != self._counts:
            self._counts = counts
            self.countChanged.emit(*counts)
