from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, QRect, Qt, Signal
from PySide6.QtGui import QAction, QColor, QEnterEvent, QIcon, QPalette, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QVBoxLayout, QWidget
from shiboken6 import isValid

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernMetrics,
    ModernNotification,
    ModernWindow,
    NotificationAction,
    NotificationKind,
    NotificationManager,
    NotificationPosition,
    NotificationState,
    ThemeMode,
)

_APP = QApplication.instance() or QApplication([])


def settle():
    _APP.processEvents()
    QTest.qWait(10)


def delete_pending():
    for _ in range(2):
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    _APP.processEvents()


@pytest.fixture
def managers(theme_manager_instance):
    host = ModernWindow()
    body = QWidget()
    layout = QVBoxLayout(body)
    field = QLineEdit("Keep typing")
    layout.addWidget(field)
    layout.addStretch()
    host.setCentralWidget(body)
    host.resize(640, 600)
    host.show()
    host.activateWindow()
    settle()
    field.setFocus()
    created = []

    def create(**options):
        options.setdefault("metrics", ModernMetrics(animation_duration=0))
        manager = NotificationManager(host, **options)
        created.append(manager)
        return manager

    yield create, host, field
    for manager in created:
        if isValid(manager):
            manager.clear()
            manager.deleteLater()
    host.close()
    host.deleteLater()
    delete_pending()


def test_fifo_queue_and_expiry_begin_on_display(managers):
    create, *_ = managers
    manager = create(max_visible=1)
    first = manager.notify("First", timeout_ms=None)
    second = manager.notify("Second", timeout_ms=100)
    shown, closed = [], []
    manager.notificationShown.connect(shown.append)
    manager.notificationClosed.connect(lambda key, reason: closed.append((key, reason)))
    QTest.qWait(160)
    assert list(manager.notifications(NotificationState.VISIBLE)) == [first]
    assert list(manager.notifications(NotificationState.QUEUED)) == [second]
    first.dismiss()
    settle()
    assert list(manager.notifications(NotificationState.VISIBLE)) == [second]
    assert shown == [second]
    QTest.qWait(160)
    assert list(manager.notifications()) == []
    assert closed == [(first, "dismissed"), (second, "expired")]


def test_pause_reasons_preserve_remaining_time(managers):
    create, *_ = managers
    manager = create()
    key = manager.notify("Read this", timeout_ms=160)
    card = key.widget()
    QTest.qWait(30)
    _APP.sendEvent(card, QEnterEvent(QPointF(1, 1), QPointF(1, 1), QPointF(1, 1)))
    key.pauseTimeout()
    QTest.qWait(200)
    key.resumeTimeout()
    QTest.qWait(200)
    assert key.widget() is card
    _APP.sendEvent(card, QEvent(QEvent.Type.Leave))
    QTest.qWait(200)
    assert key.widget() is None


def test_handle_update_preserves_identity_order_and_unspecified_fields(managers):
    create, *_ = managers
    manager = create(max_visible=1)
    first = manager.notify(
        "Download",
        timeout_ms=None,
        kind="warning",
        progress=-1,
        actions=[NotificationAction("cancel", "Cancel", False)],
    )
    card = first.widget()
    queued = manager.notify("Queued", timeout_ms=None)
    assert first.update(title="Downloading", message="50%", progress=50)
    assert first.widget() is card
    assert manager.notifications(NotificationState.VISIBLE) == (first,)
    assert manager.notifications(NotificationState.QUEUED) == (queued,)
    assert card.progress() == 50
    assert first.snapshot().kind == NotificationKind.WARNING
    assert first.snapshot().timeout_ms is None
    assert first.snapshot().actions == (NotificationAction("cancel", "Cancel", False),)
    assert first.update(title="Complete", kind="success", progress=None, actions=[], timeout_ms=80)
    assert card.kind() == NotificationKind.SUCCESS
    assert card.progress() is None
    QTest.qWait(150)
    assert first.isClosed()
    assert first.widget() is None
    assert manager.notifications(NotificationState.VISIBLE) == (queued,)
    assert not first.update(title="Too late")


def test_capacity_rejects_new_requests_and_clear_does_not_promote(managers):
    create, *_ = managers
    manager = create(max_visible=1, capacity=3)
    closed, shown = [], []
    manager.notificationClosed.connect(lambda handle, reason: closed.append((handle, reason)))
    manager.notificationShown.connect(shown.append)
    handles = [manager.notify(str(index), timeout_ms=None) for index in range(3)]
    for submit in (manager.notify, manager.post):
        with pytest.raises(OverflowError, match="capacity"):
            submit("Full")
    assert manager.notifications() == tuple(handles)
    assert manager.notifications(NotificationState.VISIBLE) == (handles[0],)
    assert closed == []
    manager.clear()
    settle()
    assert manager.notifications() == ()
    assert shown == handles[:1]
    assert closed == [(handle, "cleared") for handle in handles]
    assert not manager.notify("Capacity released").isClosed()


def test_actions_activation_and_native_qactions(managers):
    create, *_ = managers
    manager = create()
    key = manager.notify(
        "Ready",
        "<b>Plain text</b>",
        timeout_ms=None,
        actions=[NotificationAction("open", "Open file")],
    )
    card = key.widget()
    actions, clicks, closed = [], [], []
    manager.actionTriggered.connect(lambda key, action: actions.append((key, action)))
    manager.notificationActivated.connect(clicks.append)
    manager.notificationClosed.connect(lambda key, reason: closed.append((key, reason)))
    assert card._message.textFormat() == Qt.TextFormat.PlainText
    assert card.accessibleDescription() == "<b>Plain text</b>"
    native = QAction("Native", card)
    card.addAction(native)
    assert native in card.actions()
    QTest.mouseClick(card._message, Qt.MouseButton.LeftButton)
    assert clicks == [key]
    assert key.widget() is card
    key.update(
        actions=[
            NotificationAction("open", "Open file"),
            NotificationAction("retry", "Retry", False),
        ]
    )
    persistent = card._buttons["retry"]
    QTest.mouseClick(persistent, Qt.MouseButton.LeftButton)
    assert actions == [(key, "retry")]
    assert key.widget() is card
    button = next(b for b in card.findChildren(QPushButton) if b.text() == "Open file")
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert actions[-1] == (key, "open")
    assert clicks == [key]
    assert closed == [(key, "action")]


@pytest.mark.parametrize("position", list(NotificationPosition))
def test_corner_stacks_fit_available_area(managers, position):
    create, *_ = managers
    manager = create(position=position)
    ids = [manager.notify("Notice", "Text", timeout_ms=None) for _ in range(3)]
    settle()
    cards = [key.widget() for key in ids]
    area = cards[0].screen().availableGeometry().adjusted(16, 16, -16, -16)
    assert all(area.contains(card.geometry()) for card in cards)
    assert not cards[0].geometry().intersects(cards[1].geometry())
    if position in (NotificationPosition.BOTTOM_LEFT, NotificationPosition.BOTTOM_RIGHT):
        assert cards[0].geometry().bottom() == area.bottom()
        assert cards[1].y() < cards[0].y()
    else:
        assert cards[0].y() == area.top()
        assert cards[1].y() > cards[0].y()
    if position in (NotificationPosition.TOP_RIGHT, NotificationPosition.BOTTOM_RIGHT):
        assert cards[0].geometry().right() == area.right()
    else:
        assert cards[0].x() == area.left()


def test_long_text_scrolls_without_hiding_actions_or_close(managers):
    create, *_ = managers
    manager = create(width=280)
    key = manager.notify(
        "Long title " * 30,
        "Long body text. " * 300,
        timeout_ms=None,
        actions=[NotificationAction("ok", "Acknowledge")],
    )
    settle()
    card = key.widget()
    assert card.height() <= 360
    assert card.width() == 280
    assert card._scroll.verticalScrollBar().maximum() > 0
    assert card._scroll.horizontalScrollBar().maximum() == 0
    assert card.closeButton.isVisible()
    assert card.rect().contains(card.closeButton.geometry().center())
    button = next(b for b in card.findChildren(QPushButton) if b.text() == "Acknowledge")
    card._scroll.ensureWidgetVisible(button)
    settle()
    point = button.mapTo(card._scroll.viewport(), button.rect().center())
    assert card._scroll.viewport().rect().contains(point)


def test_show_does_not_take_focus_or_minimize_with_owner(managers):
    create, host, field = managers
    manager = create()
    key = manager.notify("Background task", timeout_ms=None)
    settle()
    card = key.widget()
    assert card.parentWidget() is None
    assert card.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert card.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert not card.testAttribute(Qt.WidgetAttribute.WA_QuitOnClose)
    # The offscreen plugin activates tool windows despite the no-activate flag.
    # The same test runs against the native Windows plugin for focus verification.
    if QApplication.platformName() != "offscreen":
        assert field.hasFocus()
    assert QApplication.activePopupWidget() is None
    host.showMinimized()
    settle()
    assert card.isVisible()


def test_window_delivery_tracks_resize_and_pauses_when_hidden(managers):
    create, host, _ = managers
    manager = create(desktop=False)
    key = manager.notify("Inside", timeout_ms=180)
    card = key.widget()
    assert card.parentWidget() is host
    assert host.rect().contains(card.geometry())
    host.resize(400, 350)
    settle()
    assert host.rect().contains(card.geometry())
    host.hide()
    settle()
    QTest.qWait(240)
    assert key.widget() is card
    host.show()
    settle()
    QTest.qWait(230)
    assert key.widget() is None


def test_window_keyboard_focus_pauses_expiry_and_escape_dismisses(managers):
    create, _, field = managers
    manager = create(desktop=False)
    key = manager.notify("Keyboard", timeout_ms=100, actions=[NotificationAction("open", "Open")])
    card = key.widget()
    card.closeButton.setFocus()
    QTest.qWait(180)
    assert key.widget() is card
    QTest.keyClick(card.closeButton, Qt.Key.Key_Escape)
    assert key.widget() is None
    field.setFocus()


def test_disabled_delivery_retains_queue_and_time(managers):
    create, *_ = managers
    manager = create()
    key = manager.notify("Pause", timeout_ms=100)
    manager.setDeliveryPaused(True)
    next_key = manager.notify("Next", timeout_ms=None)
    QTest.qWait(180)
    assert list(manager.notifications(NotificationState.VISIBLE)) == []
    assert manager.notifications(NotificationState.SUSPENDED) == (key,)
    assert manager.notifications(NotificationState.QUEUED) == (next_key,)
    manager.setDeliveryPaused(False)
    QTest.qWait(160)
    assert key.widget() is None
    assert list(manager.notifications(NotificationState.VISIBLE)) == [next_key]


def test_theme_changes_and_card_override(managers, theme_manager_instance):
    create, host, _ = managers
    manager = create()
    host.setTheme(DARK_THEME)
    key = manager.notify("Theme", timeout_ms=None)
    card = key.widget()
    assert card.theme() == DARK_THEME
    assert card.palette().color(QPalette.ColorRole.Window) == QColor(DARK_THEME.surface)
    host.setTheme(LIGHT_THEME)
    assert card.theme() == LIGHT_THEME
    card.setTheme(DARK_THEME)
    manager.setTheme(LIGHT_THEME)
    assert card.theme() == DARK_THEME
    card.setTheme(None)
    assert card.theme() == LIGHT_THEME
    manager.setTheme(None)
    host.setTheme(None)
    theme_manager_instance.setMode(ThemeMode.DARK)
    assert card.theme() == DARK_THEME


def test_closed_handle_cannot_affect_a_new_lifetime(managers):
    create, *_ = managers
    manager = create()
    old_handle = manager.notify("Task", timeout_ms=None)
    old_card = old_handle.widget()
    assert old_handle.dismiss()
    current = manager.notify("Task", timeout_ms=None)
    assert old_handle.id() != current.id()
    assert not old_handle.update(title="Old producer")
    assert not old_handle.dismiss()
    assert not old_handle.pauseTimeout()
    delete_pending()
    assert not isValid(old_card)
    assert current.widget().title() == "Task"
    current.widget().deleteLater()
    delete_pending()
    assert current.isClosed()
    assert current.closeReason() == "destroyed"


def test_old_view_does_not_forward_actions_after_handle_is_closed(managers):
    create, *_ = managers
    manager = create()
    handle = manager.notify("Task", timeout_ms=None)
    card = handle.widget()
    actions, activations = [], []
    manager.actionTriggered.connect(lambda *args: actions.append(args))
    manager.notificationActivated.connect(activations.append)
    handle.dismiss()
    card.actionTriggered.emit("old")
    card.activated.emit()
    assert actions == []
    assert activations == []


def test_manager_deletion_removes_desktop_windows(managers):
    create, *_ = managers
    manager = create()
    cards = [manager.notify(str(i), timeout_ms=None).widget() for i in range(4)]
    manager.deleteLater()
    delete_pending()
    assert all(not isValid(card) for card in cards)


@pytest.mark.parametrize("dismiss_first", [False, True])
def test_shown_callbacks_can_create_and_dismiss_without_losing_notifications(
    managers, dismiss_first
):
    create, *_ = managers
    manager = create(max_visible=3, capacity=3)
    shown, following = [], []
    manager.notificationShown.connect(shown.append)

    def on_shown(handle):
        if handle.snapshot().title == "First":
            if dismiss_first:
                handle.dismiss()
            following.append(manager.notify("Next", timeout_ms=None))

    manager.notificationShown.connect(on_shown)
    first = manager.notify("First", timeout_ms=None)
    settle()
    assert shown == [first, following[0]]
    assert manager.notifications(NotificationState.VISIBLE) == (
        tuple(following) if dismiss_first else (first, following[0])
    )


def test_reentrant_notify_burst_preserves_fifo_and_capacity(managers):
    create, *_ = managers
    manager = create(max_visible=3, capacity=6)
    following = []

    def on_shown(handle):
        if handle.snapshot().title == "First":
            following.extend(manager.notify(str(i), timeout_ms=None) for i in range(5))

    manager.notificationShown.connect(on_shown)
    first = manager.notify("First", timeout_ms=None)
    settle()
    assert manager.notifications(NotificationState.VISIBLE) == (first, *following[:2])
    assert manager.notifications(NotificationState.QUEUED) == tuple(following[2:])


@pytest.mark.parametrize("process_events", [False, True])
def test_clear_defers_reentrant_delivery_until_batch_finishes(managers, process_events):
    create, *_ = managers
    manager = create(max_visible=1, capacity=2)
    first = manager.notify("First", timeout_ms=None)
    waiting = manager.notify("Waiting", timeout_ms=None)
    shown, closed, following = [], [], []
    manager.notificationShown.connect(shown.append)
    manager.notificationClosed.connect(lambda h, reason: closed.append((h, reason)))

    def on_closed(handle, _reason):
        if handle is first:
            assert first.isClosed() and waiting.isClosed()
            following.append(manager.notify("New", timeout_ms=None))
            if process_events:
                settle()

    manager.notificationClosed.connect(on_closed)
    manager.clear()
    settle()
    assert shown == following
    assert closed == [(first, "cleared"), (waiting, "cleared")]
    assert manager.notifications(NotificationState.VISIBLE) == tuple(following)


def test_nested_clear_cancels_its_own_snapshot_only(managers):
    create, *_ = managers
    manager = create(max_visible=1)
    first = manager.notify("First", timeout_ms=None)
    waiting = manager.notify("Waiting", timeout_ms=None)
    following = []

    def on_closed(handle, _reason):
        if handle is first:
            canceled = manager.post("Nested", timeout_ms=None)
            manager.clear()
            following.extend((canceled, manager.notify("Replacement", timeout_ms=None)))

    manager.notificationClosed.connect(on_closed)
    manager.clear()
    delete_pending()
    settle()
    assert first.isClosed() and waiting.isClosed() and following[0].isClosed()
    assert manager.notifications(NotificationState.VISIBLE) == (following[1],)


def test_worker_post_updates_are_coalesced_and_gui_access_is_guarded(managers):
    create, *_ = managers
    manager = create(capacity=1)
    results, errors, wakes = [], [], []
    manager._wake.connect(lambda: wakes.append(1), Qt.ConnectionType.DirectConnection)

    def worker():
        handle = manager.post(
            "Worker",
            timeout_ms=None,
            kind="warning",
            actions=[NotificationAction("cancel", "Cancel", False)],
        )
        results.append(handle)
        for index in range(1000):
            assert handle.update(message=str(index), progress=index % 101)
        for operation in (lambda: manager.notify("Wrong thread"), handle.widget):
            try:
                operation()
            except RuntimeError as error:
                errors.append(str(error))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    handle = results[0]
    assert manager.notifications(NotificationState.PENDING) == (handle,)
    assert handle.widget() is None
    assert wakes == [1]
    settle()
    assert handle.widget().message() == "999"
    assert handle.snapshot().kind == NotificationKind.WARNING
    assert handle.snapshot().timeout_ms is None
    assert handle.snapshot().actions == (NotificationAction("cancel", "Cancel", False),)
    assert len(errors) == 2 and all("post()" in error for error in errors)


@pytest.mark.parametrize("cancel", ["dismiss", "clear"])
def test_worker_cancellation_before_delivery_never_shows_a_card(managers, cancel):
    create, *_ = managers
    manager = create()
    handles, shown, closed = [], [], []
    manager.notificationShown.connect(shown.append)
    manager.notificationClosed.connect(lambda h, reason: closed.append((h, reason)))

    def worker():
        handle = manager.post("Canceled", timeout_ms=None)
        handles.append(handle)
        handle.update(progress=50)
        if cancel == "clear":
            manager.clear()
        else:
            handle.dismiss()

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    handle = handles[0]
    assert handle.isClosed()
    assert not handle.update(title="Late update")
    assert manager.notifications() == ()
    settle()
    assert shown == []
    assert handle.widget() is None
    assert closed == [(handle, "cleared" if cancel == "clear" else "dismissed")]


def test_worker_clear_has_a_boundary_for_later_posts(managers):
    create, *_ = managers
    manager = create()
    handles = []

    def worker():
        handles.append(manager.post("Before clear"))
        manager.clear()
        handles.append(manager.post("After clear", timeout_ms=None))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    settle()
    assert handles[0].closeReason() == "cleared"
    assert manager.notifications(NotificationState.VISIBLE) == (handles[1],)


def test_pending_posts_and_cleanup_share_the_capacity_limit(managers):
    create, *_ = managers
    manager = create(capacity=3)
    handles, rejected = [], []
    for index in range(100):
        try:
            handles.append(manager.post(str(index), timeout_ms=None))
        except OverflowError:
            rejected.append(index)
    assert len(rejected) == 97
    assert manager.notifications(NotificationState.PENDING) == tuple(handles)

    def worker():
        for handle in handles:
            handle.dismiss()

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    with pytest.raises(OverflowError):
        manager.post("Awaiting GUI cleanup")
    settle()
    assert manager.post("Capacity released").state() == NotificationState.PENDING


def test_concurrent_producers_keep_independent_handles_and_emit_on_gui_thread(managers):
    create, *_ = managers
    manager = create(capacity=8)
    handles, callback_threads = [], []
    manager.notificationShown.connect(lambda _: callback_threads.append(threading.get_ident()))
    barrier = threading.Barrier(4)

    def worker(index):
        handle = manager.post(str(index), timeout_ms=None)
        barrier.wait()
        for progress in range(101):
            handle.update(message=f"{index}:{progress}", progress=progress)
        handles.append(handle)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    settle()
    assert len({handle.id() for handle in handles}) == 4
    assert all(h.snapshot().message == f"{h.snapshot().title}:100" for h in handles)
    assert callback_threads and set(callback_threads) == {threading.get_ident()}


@pytest.mark.parametrize("suspend", ["delivery", "host"])
def test_suspension_at_full_capacity_preserves_notification_and_remaining_time(managers, suspend):
    create, host, _ = managers
    manager = create(desktop=False, capacity=1)
    handle = manager.notify("Read this", timeout_ms=180)
    QTest.qWait(30)
    if suspend == "delivery":
        manager.setDeliveryPaused(True)
    else:
        host.hide()
    settle()
    QTest.qWait(220)
    assert handle.state() == NotificationState.SUSPENDED
    assert handle.closeReason() is None
    handle.pauseTimeout()
    if suspend == "delivery":
        manager.setDeliveryPaused(False)
    else:
        host.show()
    QTest.qWait(220)
    assert handle.state() == NotificationState.VISIBLE
    handle.resumeTimeout()
    QTest.qWait(220)
    assert handle.closeReason() == "expired"


def test_content_update_is_atomic_and_observer_can_destroy_view(managers):
    create, *_ = managers
    manager = create()
    handle = manager.notify("Before", "Before", timeout_ms=None)
    card = handle.widget()
    observed, failed = [], []
    manager.deliveryFailed.connect(lambda *args: failed.append(args))

    def on_content():
        observed.append((card.title(), card.message(), card.progress(), list(card._buttons)))
        handle.dismiss()
        card.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    card.contentChanged.connect(on_content)
    assert handle.update(
        title="After",
        message="Complete",
        progress=100,
        actions=[NotificationAction("open", "Open")],
        timeout_ms=100,
    )
    settle()
    assert observed == [("After", "Complete", 100, ["open"])]
    assert handle.closeReason() == "dismissed"
    assert failed == []


def test_content_observer_update_is_applied_after_current_batch(managers):
    create, *_ = managers
    manager = create()
    handle = manager.notify("Before", timeout_ms=None)
    card = handle.widget()
    observed = []

    def on_content():
        observed.append((card.title(), card.message()))
        if card.title() == "First":
            handle.update(title="Second")

    card.contentChanged.connect(on_content)
    handle.update(title="First", message="Committed")
    settle()
    # Display/DPI refreshes can request layout again; every observed content
    # snapshot must still be complete, with the reentrant update applied last.
    assert observed[0] == ("First", "Committed")
    assert observed[-1] == ("Second", "Committed")
    assert set(observed) == {("First", "Committed"), ("Second", "Committed")}
    assert handle.snapshot().title == card.title() == "Second"


def test_managed_view_rejects_conflicting_content_writes(managers):
    create, *_ = managers
    handle = create().notify("Managed", timeout_ms=None)
    card = handle.widget()
    for operation in (
        lambda: card.setTitle("Wrong"),
        lambda: card.clearActionButtons(),
        lambda: card.setProgress(50),
    ):
        with pytest.raises(RuntimeError, match="NotificationHandle.update"):
            operation()
    assert handle.snapshot().title == card.title() == "Managed"


def test_declarative_actions_keep_behavior_and_focus_during_updates(managers):
    create, *_ = managers
    handle = create(desktop=False).notify(
        "Retry", timeout_ms=None, actions=[NotificationAction("retry", "Retry", False)]
    )
    card = handle.widget()
    button = card._buttons["retry"]
    button.setFocus()
    handle.update(progress=50)
    handle.update(actions=[NotificationAction("retry", "Try again", False)])
    assert card._buttons["retry"] is button
    assert button.hasFocus()
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert not handle.isClosed()
    assert button.text() == "Try again"


def test_inputs_and_returned_snapshots_do_not_mutate_accepted_content(managers):
    create, *_ = managers
    manager = create()
    pixmap = QPixmap(8, 8)
    pixmap.fill(QColor("red"))
    icon = QIcon(pixmap)
    actions = [NotificationAction("retry", "Retry", False)]
    handle = manager.post("Copy", icon=icon, actions=actions)
    accepted_key = handle.snapshot().icon.cacheKey()
    actions.clear()
    pixmap.fill(QColor("blue"))
    icon.addPixmap(pixmap)
    snapshot = handle.snapshot()
    with pytest.raises(FrozenInstanceError):
        snapshot.title = "Wrong"
    snapshot.icon.addPixmap(pixmap)
    assert handle.snapshot().icon.cacheKey() == accepted_key
    settle()
    assert handle.widget()._buttons["retry"].text() == "Retry"


def test_timeout_defaults_omission_and_explicit_none(managers):
    create, *_ = managers
    manager = create(default_timeout_ms=100)
    default = manager.notify("Default")
    persistent = manager.notify("Persistent", timeout_ms=None)
    default.update(timeout_ms=None)
    persistent.update(progress=100)
    QTest.qWait(150)
    assert not default.isClosed() and not persistent.isClosed()
    persistent.update(timeout_ms=80)
    QTest.qWait(150)
    assert persistent.closeReason() == "expired"
    assert default.snapshot().timeout_ms is None


def test_accepted_timeout_change_wins_over_a_stale_timer_event(managers):
    create, *_ = managers
    manager = create()
    handle = manager.notify("Still working", timeout_ms=100)
    thread = threading.Thread(target=lambda: handle.update(timeout_ms=None))
    thread.start()
    thread.join()
    manager._expire(handle)
    QTest.qWait(150)
    assert not handle.isClosed()


@pytest.mark.parametrize("command", ["restart", "pause"])
@pytest.mark.parametrize("release_number", [1, 2])
def test_timeout_mutation_and_expiry_have_one_acceptance_boundary(
    managers, monkeypatch, command, release_number
):
    create, *_ = managers
    manager = create()
    handle = manager.notify("Working", timeout_ms=5000)
    original_lock = manager._store.lock
    gui_thread = threading.get_ident()
    results = []

    def worker():
        results.append(
            handle.update(timeout_ms=None) if command == "restart" else handle.pauseTimeout()
        )

    class InterleavedLock:
        releases = 0

        def __enter__(self):
            original_lock.acquire()

        def __exit__(self, *_args):
            original_lock.release()
            if threading.get_ident() == gui_thread:
                self.releases += 1
                if self.releases == release_number:
                    # Force a worker change between expiry's initial liveness check,
                    # eligibility check, and closing, wherever a lock is released.
                    thread = threading.Thread(target=worker)
                    thread.start()
                    thread.join(timeout=5)
                    assert not thread.is_alive()

    with monkeypatch.context() as patch:
        patch.setattr(manager._store, "lock", InterleavedLock())
        manager._expire(handle)

    settle()
    assert len(results) == 1
    if results[0]:
        assert not handle.isClosed()
    else:
        assert handle.closeReason() == "expired"


def test_handles_outlive_manager_without_touching_deleted_qt_objects(managers):
    create, *_ = managers
    manager = create()
    displayed = manager.notify("Displayed", timeout_ms=None)
    pending = manager.post("Pending", timeout_ms=None)
    manager.deleteLater()
    delete_pending()
    results = []

    def worker():
        for handle in (displayed, pending):
            results.extend((handle.update(progress=50), handle.dismiss(), handle.resumeTimeout()))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert results == [False] * 6
    assert displayed.widget() is None and pending.widget() is None
    assert displayed.closeReason() == pending.closeReason() == "destroyed"


class FakeScreen(QObject):
    availableGeometryChanged = Signal(QRect)
    geometryChanged = Signal(QRect)
    logicalDotsPerInchChanged = Signal(float)

    def __init__(self, rect):
        super().__init__()
        self.rect = rect

    def availableGeometry(self):
        return self.rect


def test_multiple_screens_negative_coordinates_and_removal(managers, monkeypatch):
    create, *_ = managers
    left = FakeScreen(QRect(-900, 0, 900, 700))
    right = FakeScreen(QRect(0, 0, 1000, 700))
    screens = [left, right]
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: screens))
    manager = create(max_visible=1)
    manager.setScreen(right)
    first = manager.notify("Left", timeout_ms=None, screen=left)
    second = manager.notify("Right", timeout_ms=None, screen=right)
    third = manager.notify("Wait on left", timeout_ms=None, screen=left)
    assert list(manager.notifications(NotificationState.VISIBLE)) == [first, second]
    assert list(manager.notifications(NotificationState.QUEUED)) == [third]
    assert left.rect.contains(first.widget().geometry())
    assert right.rect.contains(second.widget().geometry())
    screens.remove(left)
    manager._screen_removed(left)
    settle()
    assert list(manager.notifications(NotificationState.VISIBLE)) == [first]
    assert right.rect.contains(first.widget().geometry())
    assert manager.notifications(NotificationState.SUSPENDED) == (second,)
    assert manager.notifications(NotificationState.QUEUED) == (third,)


def test_wayland_defaults_to_window_delivery(managers, monkeypatch):
    create, *_ = managers
    monkeypatch.setattr(QApplication, "platformName", lambda: "wayland")
    manager = create()
    assert not manager.isDesktop()
    with pytest.raises(ValueError, match="Wayland"):
        create(desktop=True)
    with pytest.raises(ValueError, match="host"):
        NotificationManager()


@pytest.mark.parametrize(
    "options",
    [
        {"max_visible": 0},
        {"capacity": 0},
        {"width": 100},
        {"margin": -1},
        {"default_timeout_ms": 0},
        {"position": "middle"},
    ],
)
def test_invalid_configuration(managers, options):
    create, *_ = managers
    with pytest.raises(ValueError):
        create(**options)


def test_invalid_updates_are_atomic(managers):
    create, *_ = managers
    manager = create()
    handle = manager.notify("Original", timeout_ms=None)
    before = handle.snapshot()
    with pytest.raises(ValueError):
        handle.update(title="Changed", progress=101)
    with pytest.raises(ValueError):
        handle.update(title="Changed", timeout_ms=0)
    with pytest.raises(ValueError):
        handle.update(
            actions=[NotificationAction("same", "One"), NotificationAction("same", "Two")]
        )
    with pytest.raises(TypeError):
        manager.notify("Invalid", actions={"old": "Mapping API"})
    assert handle.snapshot() == before
    assert handle.widget().title() == "Original"
    assert manager.notifications() == (handle,)


def test_progress_uses_active_accent_and_updates_with_palette(managers):
    create, *_ = managers
    manager = create()
    key = manager.notify("Progress", progress=100, timeout_ms=None)
    card = key.widget()
    for color in ("#ad246a", "#168052"):
        palette = QPalette(_APP.palette())
        palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent, QColor(color))
        palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Accent, QColor("#ffffff"))
        _APP.setPalette(palette)
        settle()
        image = card._progress_bar.grab().toImage()
        assert image.pixelColor(image.width() // 2, image.height() // 2) == QColor(color)


def test_work_area_changes_and_max_visible_reflow(managers, monkeypatch):
    create, *_ = managers
    screen = FakeScreen(QRect(0, 0, 900, 900))
    monkeypatch.setattr(QApplication, "screens", staticmethod(lambda: [screen]))
    manager = create()
    manager.setScreen(screen)
    ids = [manager.notify(str(i), "Message", timeout_ms=None) for i in range(3)]
    assert list(manager.notifications(NotificationState.VISIBLE)) == ids
    manager.setMaxVisible(1)
    settle()
    assert list(manager.notifications(NotificationState.VISIBLE)) == ids[:1]
    assert list(manager.notifications(NotificationState.SUSPENDED)) == ids[1:]
    screen.rect = QRect(0, 0, 500, 300)
    screen.availableGeometryChanged.emit(screen.rect)
    settle()
    assert screen.rect.contains(ids[0].widget().geometry())
    manager.setMaxVisible(3)
    settle()
    assert len(list(manager.notifications(NotificationState.VISIBLE))) >= 2
    assert all(
        screen.rect.contains(key.widget().geometry())
        for key in list(manager.notifications(NotificationState.VISIBLE))
    )


@pytest.mark.parametrize("native_corners, acrylic", [(False, False), (True, False), (True, True)])
def test_surface_has_only_one_corner_outline(
    theme_manager_instance, monkeypatch, native_corners, acrylic
):
    from pyside6_modern_widgets import modern_notification

    monkeypatch.setattr(
        modern_notification, "_enable_windows_rounded_corners", lambda *_args: native_corners
    )
    monkeypatch.setattr(modern_notification, "_enable_windows_acrylic", lambda *_args: acrylic)
    card = ModernNotification(theme=LIGHT_THEME)
    card._configure_desktop()
    card.resize(360, 120)
    card.show()
    settle()
    try:
        image = card.grab().toImage()
        scale = image.devicePixelRatio()
        corner = round(10 * scale)
        alphas = [image.pixelColor(x, y).alpha() for y in range(corner) for x in range(corner)]
        if native_corners:
            # The compositor owns the outline; the Qt backing surface stays uniform.
            assert set(alphas) == {1 if acrylic else 255}
        else:
            assert image.pixelColor(0, 0).alpha() == 0
            assert any(0 < alpha < 255 for alpha in alphas)
    finally:
        card.close()
        card.deleteLater()
        delete_pending()


def test_desktop_card_refreshes_twice_after_display_metrics_change(managers, monkeypatch):
    from pyside6_modern_widgets import modern_notification

    create, *_ = managers
    refreshes = []
    monkeypatch.setattr(
        modern_notification,
        "_enable_windows_rounded_corners",
        lambda *_args: refreshes.append("surface") or False,
    )
    manager = create()
    key = manager.notify("Mixed DPI", timeout_ms=None)
    card = key.widget()
    settle()
    card._surface_refresh_timer.stop()
    card._surface_settle_timer.stop()
    refreshes.clear()
    reflows = []
    card.contentChanged.connect(lambda: reflows.append(card.geometry()))

    _APP.sendEvent(card, QEvent(QEvent.Type.DevicePixelRatioChange))

    assert card._surface_refresh_timer.isActive()
    assert card._surface_settle_timer.isActive()
    QTest.qWait(130)
    assert len(refreshes) >= 2
    assert len(reflows) >= 2
    assert card.screen().availableGeometry().contains(card.geometry())


def test_desktop_card_tracks_its_native_window_screen(managers):
    create, *_ = managers
    manager = create()
    card = manager.notify("Screen", timeout_ms=None).widget()
    settle()

    assert card._screen_change_window is card.windowHandle()
    card.hide()
    assert card._screen_change_window is None
    card.show()
    assert card._screen_change_window is card.windowHandle()


def test_desktop_card_delegates_native_dpi_constraints(managers, monkeypatch):
    create, *_ = managers
    manager = create()
    card = manager.notify("DPI", timeout_ms=None).widget()
    calls = []
    monkeypatch.setattr(
        card._native_dpi,
        "handle_native_event",
        lambda widget, message: calls.append((widget, message)) or True,
    )

    assert card.nativeEvent(b"windows_generic_MSG", 123) == (True, 0)
    assert calls == [(card, 123)]
