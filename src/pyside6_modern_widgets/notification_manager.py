"""Screen-aware delivery, bounded queues, and timers for modern notifications."""

from __future__ import annotations

import weakref
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QScreen
from PySide6.QtWidgets import QApplication, QWidget
from shiboken6 import isValid

from .modern_notification import ModernNotification, NotificationKind
from .theme import DEFAULT_METRICS, ModernMetrics, ModernTheme, inherited_theme, theme_manager


class NotificationPosition(str, Enum):
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"


class _Unset(Enum):
    VALUE = 0


_UNSET = _Unset.VALUE


@dataclass
class _Notification:
    card: ModernNotification
    timer: QTimer
    remaining: int
    screen: QScreen | None
    visible: bool = False
    shown: bool = False
    paused: set[str] = field(default_factory=set)


def _non_negative(value: int, name: str) -> int:
    if not isinstance(value, int) or not 0 <= value <= 2_147_483_647:
        raise ValueError(f"{name} must be an integer from 0 to 2147483647")
    return value


class NotificationManager(QObject):
    """Own custom notifications, with FIFO delivery per screen.

    Keep one manager per application (or per independent host). Desktop cards
    have no QWidget owner so minimizing the host does not hide them. Deleting
    this manager deletes all of its cards. Wayland uses child cards in a supplied
    host widget. notify/update/dismiss are GUI-thread APIs; post() is thread-safe.
    """

    notificationShown = Signal(str)
    notificationClosed = Signal(str, str)
    notificationActivated = Signal(str)
    actionTriggered = Signal(str, str)
    countChanged = Signal(int, int)
    deliveryFailed = Signal(str, str)
    _posted = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        position: NotificationPosition | str = NotificationPosition.BOTTOM_RIGHT,
        max_visible: int = 3,
        max_queued: int = 100,
        width: int = 360,
        margin: int = 16,
        spacing: int = 12,
        default_duration: int = 5000,
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
        if _non_negative(width, "width") < 160:
            raise ValueError("width must be at least 160 logical pixels")
        _non_negative(max_queued, "max_queued")
        _non_negative(margin, "margin")
        _non_negative(spacing, "spacing")
        _non_negative(default_duration, "default_duration")
        wayland = QApplication.platformName().startswith("wayland")
        if wayland and desktop:
            raise ValueError("Wayland requires in-window notifications (desktop=False)")
        desktop = not wayland if desktop is None else desktop
        if not desktop and parent is None:
            raise ValueError("In-window notifications require a host QWidget")
        super().__init__(parent)
        self._owner = weakref.ref(parent) if parent is not None else None
        self._desktop = desktop
        self._position = position
        self._max_visible = max_visible
        self._max_queued = max_queued
        self._width, self._margin, self._spacing = width, margin, spacing
        self._default_duration = default_duration
        self._theme_override = theme
        self._metrics = metrics
        self._records: dict[str, _Notification] = {}
        self._screen: QScreen | None = None
        self._counts = (0, 0)
        self._reflowing = False
        self._enabled = True
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.timeout.connect(self._reflow)
        self._posted.connect(self._deliver_post, Qt.ConnectionType.QueuedConnection)
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
        if QThread.currentThread() != self.thread():
            raise RuntimeError("Use post() or a queued Qt signal from a worker thread")

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
        """Choose a default screen; None follows the host, then the primary screen."""
        self._check_thread()
        self._validate_screen(screen)
        self._screen = screen
        self._schedule()

    def setMaxVisible(self, count: int) -> None:
        self._check_thread()
        if _non_negative(count, "count") == 0:
            raise ValueError("count must be positive")
        self._max_visible = count
        self._schedule()

    def maxVisible(self) -> int:
        return self._max_visible

    def setEnabled(self, enabled: bool) -> None:
        """Pause delivery and expiry while disabled; keep the bounded queue."""
        self._check_thread()
        self._enabled = bool(enabled)
        self._reflow()

    def isEnabled(self) -> bool:
        return self._enabled

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
            record.card._inherited_theme = self.theme()
            record.card._apply_theme()

    @staticmethod
    def _validate_screen(screen: QScreen | None) -> None:
        if screen is not None and (not isValid(screen) or screen not in QApplication.screens()):
            raise ValueError("screen must be a currently connected QScreen")

    @staticmethod
    def _validate_content(
        title: str,
        message: str,
        kind: NotificationKind | str,
        duration: int | None,
        actions: Mapping[str, str] | None,
        progress: int | None,
    ) -> NotificationKind:
        if not isinstance(title, str) or not isinstance(message, str):
            raise TypeError("title and message must be strings")
        kind = NotificationKind(kind)
        if duration is not None:
            _non_negative(duration, "duration")
        if progress is not None and (not isinstance(progress, int) or not -1 <= progress <= 100):
            raise ValueError("progress must be None or an integer from -1 to 100")
        if actions is not None and any(
            not isinstance(key, str) or not key or not isinstance(text, str)
            for key, text in actions.items()
        ):
            raise ValueError("actions must map non-empty string IDs to text")
        return kind

    @Slot(str, str, result=str)
    def notify(
        self,
        title: str,
        message: str = "",
        *,
        notification_id: str | None = None,
        kind: NotificationKind | str = NotificationKind.INFO,
        duration: int | None = None,
        actions: Mapping[str, str] | None = None,
        progress: int | None = None,
        screen: QScreen | None = None,
        icon: QIcon | None = None,
    ) -> str:
        """Show or enqueue a card. Reusing an ID replaces its content and timeout.

        duration is milliseconds; 0 is persistent, None uses default_duration.
        max_visible applies per screen, max_queued to the entire manager. Queue
        overflow drops the oldest queued card with reason 'overflow'.
        """
        self._check_thread()
        kind = self._validate_content(title, message, kind, duration, actions, progress)
        self._validate_screen(screen)
        if icon is not None and not isinstance(icon, QIcon):
            raise TypeError("icon must be a QIcon or None")
        if notification_id is not None and (
            not isinstance(notification_id, str) or not notification_id
        ):
            raise ValueError("notification_id must be a non-empty string")
        key = notification_id or uuid4().hex
        timeout = self._default_duration if duration is None else duration
        if key in self._records:
            self.updateNotification(
                key,
                title=title,
                message=message,
                kind=kind,
                duration=timeout,
                actions=actions or {},
                progress=progress,
            )
            record = self._records.get(key)
            if record is not None:
                record.screen = screen
                record.card.setIcon(icon)
            self._reflow()
            return key
        host = self._host()
        card = ModernNotification(
            title,
            message,
            None if self._desktop else host,
            kind=kind,
            metrics=self._metrics,
        )
        if self._desktop:
            card._configure_desktop()
        if host is not None:
            card.setFont(host.font())
            card.setLayoutDirection(host.layoutDirection())
        card._inherited_theme = self.theme()
        card._apply_theme()
        card.setProgress(progress)
        card.setIcon(icon)
        for action_id, text in (actions or {}).items():
            card.addActionButton(action_id, text)
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda key=key: self.dismiss(key, "expired"))
        record = _Notification(card, timer, timeout, screen)
        self._records[key] = record
        self.destroyed.connect(card.deleteLater)
        card.dismissed.connect(
            lambda reason, key=key, record=record: self._card_dismissed(key, record, reason)
        )
        card.destroyed.connect(
            lambda _obj=None, key=key, record=record: self._card_destroyed(key, record)
        )
        card.actionTriggered.connect(lambda action, key=key: self.actionTriggered.emit(key, action))
        card.activated.connect(lambda key=key: self.notificationActivated.emit(key))
        card.hoveredChanged.connect(lambda hovered, key=key: self._set_pause(key, "hover", hovered))
        card.contentChanged.connect(self._schedule)
        self._reflow()
        return key

    def post(
        self,
        title: str,
        message: str = "",
        *,
        notification_id: str | None = None,
        kind: NotificationKind | str = NotificationKind.INFO,
        duration: int | None = None,
        actions: Mapping[str, str] | None = None,
        progress: int | None = None,
    ) -> str:
        """Thread-safe, asynchronous notify(). Returns the ID before delivery.

        Uses the manager's default screen. Content validation runs immediately;
        delivery errors are reported by deliveryFailed(id, message).
        """
        kind = self._validate_content(title, message, kind, duration, actions, progress)
        if notification_id is not None and (
            not isinstance(notification_id, str) or not notification_id
        ):
            raise ValueError("notification_id must be a non-empty string")
        key = notification_id or uuid4().hex
        self._posted.emit(
            (
                title,
                message,
                {
                    "notification_id": key,
                    "kind": kind,
                    "duration": duration,
                    "actions": dict(actions) if actions is not None else None,
                    "progress": progress,
                },
            )
        )
        return key

    @Slot(object)
    def _deliver_post(self, request) -> None:
        title, message, options = request
        try:
            self.notify(title, message, **options)
        except (RuntimeError, ValueError, TypeError) as error:
            self.deliveryFailed.emit(options["notification_id"], str(error))

    def notification(self, notification_id: str) -> ModernNotification | None:
        """Return the owned card while queued/visible, or None after dismissal."""
        record = self._records.get(notification_id)
        return record.card if record is not None else None

    def notificationIds(self) -> list[str]:
        return list(self._records)

    def visibleIds(self) -> list[str]:
        return [key for key, record in self._records.items() if record.visible]

    def queuedIds(self) -> list[str]:
        return [key for key, record in self._records.items() if not record.visible]

    def updateNotification(
        self,
        notification_id: str,
        *,
        title: str | None = None,
        message: str | None = None,
        kind: NotificationKind | str | None = None,
        duration: int | None = None,
        actions: Mapping[str, str] | None = None,
        progress: int | None | _Unset = _UNSET,
    ) -> bool:
        """Update supplied fields without changing FIFO order. Unknown IDs return False.

        An explicit duration restarts expiry; other updates preserve remaining
        time. progress=None clears progress. actions={} removes all actions.
        """
        self._check_thread()
        record = self._records.get(notification_id)
        if record is None:
            return False
        card = record.card
        self._validate_content(
            card.title() if title is None else title,
            card.message() if message is None else message,
            card.kind() if kind is None else kind,
            duration,
            actions,
            card.progress() if isinstance(progress, _Unset) else progress,
        )
        if title is not None:
            card.setTitle(title)
        if message is not None:
            card.setMessage(message)
        if kind is not None:
            card.setKind(kind)
        if not isinstance(progress, _Unset):
            card.setProgress(progress)
        if actions is not None:
            card.clearActionButtons()
            for key, text in actions.items():
                card.addActionButton(key, text)
        if duration is not None:
            record.timer.stop()
            record.remaining = duration
            self._resume(record)
        self._schedule()
        return True

    def dismiss(self, notification_id: str, reason: str = "dismissed") -> bool:
        self._check_thread()
        record = self._records.get(notification_id)
        if record is None:
            return False
        record.card.dismiss(reason)
        return True

    @Slot()
    def clear(self) -> None:
        """Dismiss all currently registered cards, including the waiting queue."""
        self._check_thread()
        for key in list(self._records):
            self.dismiss(key, "cleared")

    def pause(self, notification_id: str) -> None:
        self._check_thread()
        self._set_pause(notification_id, "manual", True)

    def resume(self, notification_id: str) -> None:
        self._check_thread()
        self._set_pause(notification_id, "manual", False)

    def _set_pause(self, key: str, reason: str, paused: bool) -> None:
        record = self._records.get(key)
        if record is None:
            return
        if paused:
            self._stop_clock(record)
            record.paused.add(reason)
        else:
            record.paused.discard(reason)
            self._resume(record)

    @staticmethod
    def _stop_clock(record: _Notification) -> None:
        if record.timer.isActive():
            record.remaining = max(1, record.timer.remainingTime())
            record.timer.stop()

    @staticmethod
    def _resume(record: _Notification) -> None:
        if (
            record.visible
            and not record.paused
            and record.remaining > 0
            and not record.timer.isActive()
        ):
            record.timer.start(record.remaining)

    def _focus_changed(self, _old: QWidget | None, new: QWidget | None) -> None:
        for key, record in list(self._records.items()):
            focused = new is not None and (new is record.card or record.card.isAncestorOf(new))
            self._set_pause(key, "focus", focused)

    def _remove(self, key: str, reason: str, *, destroyed: bool = False) -> None:
        record = self._records.pop(key, None)
        if record is None:
            return
        record.timer.stop()
        record.timer.deleteLater()
        if not destroyed and isValid(record.card):
            record.card.hide()
            record.card.deleteLater()
        self._schedule()
        self._emit_counts()
        self.notificationClosed.emit(key, reason)

    def _card_dismissed(self, key: str, record: _Notification, reason: str) -> None:
        if self._records.get(key) is record:
            self._remove(key, reason)

    def _card_destroyed(self, key: str, record: _Notification) -> None:
        if isValid(self) and self._records.get(key) is record:
            self._remove(key, "destroyed", destroyed=True)

    def _screen_added(self, screen: QScreen) -> None:
        screen.availableGeometryChanged.connect(self._schedule)
        screen.geometryChanged.connect(self._schedule)
        screen.logicalDotsPerInchChanged.connect(self._schedule)
        self._schedule()

    def _screen_removed(self, screen: QScreen) -> None:
        if self._screen is screen:
            self._screen = None
        for record in self._records.values():
            if record.screen is screen:
                record.screen = None
        self._schedule()

    def _target_screen(self, record: _Notification) -> QScreen | None:
        screens = QApplication.screens()
        for screen in (record.screen, self._screen):
            if screen is not None and isValid(screen) and screen in screens:
                return screen
        host = self._host()
        return host.screen() if host is not None else QApplication.primaryScreen()

    def _schedule(self, *_args) -> None:
        self._layout_timer.start(0)

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
                for record in self._records.values():
                    record.card.setFont(watched.font())
                    record.card.setLayoutDirection(watched.layoutDirection())
                self._schedule()
        return super().eventFilter(watched, event)

    def _reflow(self) -> None:
        if self._reflowing:
            self._schedule()
            return
        self._reflowing = True
        try:
            host = self._host()
            can_show = self._enabled and (
                self._desktop
                or (host is not None and host.isVisible() and not host.window().isMinimized())
            )
            groups: dict[QScreen | None, list[tuple[str, _Notification]]] = defaultdict(list)
            for key, record in list(self._records.items()):
                screen = self._target_screen(record) if self._desktop else None
                groups[screen].append((key, record))
            for screen, records in groups.items():
                bounds = (
                    screen.availableGeometry()
                    if screen is not None
                    else (host.rect() if host is not None else QRect())
                )
                area = bounds.adjusted(self._margin, self._margin, -self._margin, -self._margin)
                used, count = 0, 0
                for key, record in records:
                    if self._records.get(key) is not record:
                        continue
                    remaining = area.height() - used
                    show = (
                        can_show
                        and self._enabled
                        and area.width() >= 120
                        and remaining >= 80
                        and count < self._max_visible
                    )
                    if not show:
                        self._stop_clock(record)
                        record.visible = False
                        record.card.hide()
                        continue
                    size = record.card._fit_size(
                        min(self._width, area.width()), min(360, remaining)
                    )
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
                    animate = record.visible and area.contains(record.card.geometry())
                    target = QPoint(x, y)
                    was_visible = record.visible
                    record.card._move_to(target, animate)
                    record.visible = True
                    record.card.show()
                    record.card.raise_()
                    if not was_visible and self._metrics.animation_duration > 0:
                        start = target + QPoint(0, -12 if bottom else 12)
                        if area.contains(QRect(start, size)):
                            record.card.move(start)
                            record.card._move_to(target, True)
                    self._resume(record)
                    used += size.height() + self._spacing
                    count += 1
                    if not record.shown:
                        record.shown = True
                        self.notificationShown.emit(key)
            # Bound pending work even while delivery is paused or a host hidden.
            queued = self.queuedIds()
            for key in queued[: max(0, len(queued) - self._max_queued)]:
                self.dismiss(key, "overflow")
            self._emit_counts()
        finally:
            self._reflowing = False

    def _emit_counts(self) -> None:
        counts = (len(self.visibleIds()), len(self.queuedIds()))
        if counts != self._counts:
            self._counts = counts
            self.countChanged.emit(*counts)
