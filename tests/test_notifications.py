from __future__ import annotations

import threading

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, QRect, Qt, Signal
from PySide6.QtGui import QAction, QColor, QEnterEvent, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QVBoxLayout, QWidget
from shiboken6 import isValid

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernMetrics,
    ModernNotification,
    ModernWindow,
    NotificationKind,
    NotificationManager,
    NotificationPosition,
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
    first = manager.notify("First", duration=0)
    second = manager.notify("Second", duration=100)
    shown, closed = [], []
    manager.notificationShown.connect(shown.append)
    manager.notificationClosed.connect(lambda key, reason: closed.append((key, reason)))
    QTest.qWait(160)
    assert manager.visibleIds() == [first]
    assert manager.queuedIds() == [second]
    manager.dismiss(first)
    settle()
    assert manager.visibleIds() == [second]
    assert shown == [second]
    QTest.qWait(160)
    assert manager.notificationIds() == []
    assert closed == [(first, "dismissed"), (second, "expired")]


def test_pause_reasons_preserve_remaining_time(managers):
    create, *_ = managers
    manager = create()
    key = manager.notify("Read this", duration=160)
    card = manager.notification(key)
    QTest.qWait(30)
    _APP.sendEvent(card, QEnterEvent(QPointF(1, 1), QPointF(1, 1), QPointF(1, 1)))
    manager.pause(key)
    QTest.qWait(200)
    manager.resume(key)
    QTest.qWait(200)
    assert manager.notification(key) is card
    _APP.sendEvent(card, QEvent(QEvent.Type.Leave))
    QTest.qWait(200)
    assert manager.notification(key) is None


def test_upsert_preserves_identity_order_and_updates_progress(managers):
    create, *_ = managers
    manager = create(max_visible=1)
    first = manager.notify("Download", duration=0, notification_id="job", progress=-1)
    card = manager.notification(first)
    queued = manager.notify("Queued", duration=0)
    assert (
        manager.notify("Downloading", "50%", notification_id="job", duration=0, progress=50)
        == first
    )
    assert manager.notification(first) is card
    assert manager.visibleIds() == [first]
    assert manager.queuedIds() == [queued]
    assert card.progress() == 50
    assert manager.updateNotification(
        first, title="Complete", kind="success", progress=None, duration=80
    )
    assert card.kind() == NotificationKind.SUCCESS
    assert card.progress() is None
    QTest.qWait(150)
    assert manager.notification(first) is None
    assert manager.visibleIds() == [queued]
    assert not manager.updateNotification("missing", title="Nothing")


def test_queue_overflow_is_bounded_and_clear_does_not_promote(managers):
    create, *_ = managers
    manager = create(max_visible=1, max_queued=2)
    closed = []
    shown = []
    manager.notificationClosed.connect(lambda key, reason: closed.append((key, reason)))
    manager.notificationShown.connect(shown.append)
    ids = [manager.notify(str(index), duration=0) for index in range(5)]
    assert manager.visibleIds() == ids[:1]
    assert manager.queuedIds() == ids[-2:]
    assert closed == [(ids[1], "overflow"), (ids[2], "overflow")]
    manager.clear()
    settle()
    assert manager.notificationIds() == []
    assert shown == ids[:1]


def test_actions_activation_and_native_qactions(managers):
    create, *_ = managers
    manager = create()
    key = manager.notify("Ready", "<b>Plain text</b>", duration=0, actions={"open": "Open file"})
    card = manager.notification(key)
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
    assert manager.notification(key) is card
    persistent = card.addActionButton("retry", "Retry", close_on_trigger=False)
    QTest.mouseClick(persistent, Qt.MouseButton.LeftButton)
    assert actions == [(key, "retry")]
    assert manager.notification(key) is card
    button = next(b for b in card.findChildren(QPushButton) if b.text() == "Open file")
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert actions[-1] == (key, "open")
    assert clicks == [key]
    assert closed == [(key, "action")]


@pytest.mark.parametrize("position", list(NotificationPosition))
def test_corner_stacks_fit_available_area(managers, position):
    create, *_ = managers
    manager = create(position=position)
    ids = [manager.notify("Notice", "Text", duration=0) for _ in range(3)]
    settle()
    cards = [manager.notification(key) for key in ids]
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
        "Long title " * 30, "Long body text. " * 300, duration=0, actions={"ok": "Acknowledge"}
    )
    settle()
    card = manager.notification(key)
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
    key = manager.notify("Background task", duration=0)
    settle()
    card = manager.notification(key)
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
    key = manager.notify("Inside", duration=180)
    card = manager.notification(key)
    assert card.parentWidget() is host
    assert host.rect().contains(card.geometry())
    host.resize(400, 350)
    settle()
    assert host.rect().contains(card.geometry())
    host.hide()
    settle()
    QTest.qWait(240)
    assert manager.notification(key) is card
    host.show()
    settle()
    QTest.qWait(230)
    assert manager.notification(key) is None


def test_window_keyboard_focus_pauses_expiry_and_escape_dismisses(managers):
    create, _, field = managers
    manager = create(desktop=False)
    key = manager.notify("Keyboard", duration=100, actions={"open": "Open"})
    card = manager.notification(key)
    card.closeButton.setFocus()
    QTest.qWait(180)
    assert manager.notification(key) is card
    QTest.keyClick(card.closeButton, Qt.Key.Key_Escape)
    assert manager.notification(key) is None
    field.setFocus()


def test_disabled_delivery_retains_queue_and_time(managers):
    create, *_ = managers
    manager = create()
    key = manager.notify("Pause", duration=100)
    manager.setEnabled(False)
    next_key = manager.notify("Next", duration=0)
    QTest.qWait(180)
    assert manager.visibleIds() == []
    assert manager.queuedIds() == [key, next_key]
    manager.setEnabled(True)
    QTest.qWait(160)
    assert manager.notification(key) is None
    assert manager.visibleIds() == [next_key]


def test_theme_changes_and_card_override(managers, theme_manager_instance):
    create, host, _ = managers
    manager = create()
    host.setTheme(DARK_THEME)
    key = manager.notify("Theme", duration=0)
    card = manager.notification(key)
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


def test_reused_id_survives_old_card_deferred_deletion(managers):
    create, *_ = managers
    manager = create()
    manager.notify("Old", notification_id="same", duration=0)
    old = manager.notification("same")
    manager.dismiss("same")
    manager.notify("New", notification_id="same", duration=0)
    current = manager.notification("same")
    delete_pending()
    assert not isValid(old)
    assert manager.notification("same") is current
    current.deleteLater()
    delete_pending()
    assert manager.notification("same") is None


def test_manager_deletion_removes_desktop_windows(managers):
    create, *_ = managers
    manager = create()
    cards = [manager.notification(manager.notify(str(i), duration=0)) for i in range(4)]
    manager.deleteLater()
    delete_pending()
    assert all(not isValid(card) for card in cards)


def test_signals_allow_reentrant_dismiss_and_notify(managers):
    create, *_ = managers
    manager = create()
    manager.notificationShown.connect(
        lambda key: manager.dismiss(key) if key == "discard" else None
    )
    manager.notificationClosed.connect(
        lambda key, _reason: (
            manager.notify("Replacement", notification_id="replacement", duration=0)
            if key == "discard"
            else None
        )
    )
    manager.notify("Discard", notification_id="discard", duration=0)
    settle()
    assert manager.visibleIds() == ["replacement"]


def test_worker_post_and_gui_thread_guard(managers):
    create, *_ = managers
    manager = create()
    results, errors = [], []

    def worker():
        results.append(manager.post("Worker", duration=0, progress=42))
        try:
            manager.notify("Wrong thread")
        except RuntimeError as error:
            errors.append(str(error))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert manager.notificationIds() == []
    settle()
    assert manager.notification(results[0]).progress() == 42
    assert errors and "post()" in errors[0]


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
    first = manager.notify("Left", duration=0, screen=left)
    second = manager.notify("Right", duration=0, screen=right)
    third = manager.notify("Wait on left", duration=0, screen=left)
    assert manager.visibleIds() == [first, second]
    assert manager.queuedIds() == [third]
    assert left.rect.contains(manager.notification(first).geometry())
    assert right.rect.contains(manager.notification(second).geometry())
    screens.remove(left)
    manager._screen_removed(left)
    settle()
    assert manager.visibleIds() == [first]
    assert right.rect.contains(manager.notification(first).geometry())
    assert manager.queuedIds() == [second, third]


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
        {"max_queued": -1},
        {"width": 100},
        {"margin": -1},
        {"default_duration": -1},
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
    key = manager.notify("Original", duration=0)
    with pytest.raises(ValueError):
        manager.updateNotification(key, title="Changed", progress=101)
    assert manager.notification(key).title() == "Original"
    with pytest.raises(ValueError):
        manager.notify("Invalid", notification_id="", duration=0)
    with pytest.raises(ValueError):
        manager.notify("Invalid", actions={"": "Empty"})
    assert manager.notificationIds() == [key]


def test_progress_uses_active_accent_and_updates_with_palette(managers):
    create, *_ = managers
    manager = create()
    key = manager.notify("Progress", progress=100, duration=0)
    card = manager.notification(key)
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
    ids = [manager.notify(str(i), "Message", duration=0) for i in range(3)]
    assert manager.visibleIds() == ids
    manager.setMaxVisible(1)
    settle()
    assert manager.visibleIds() == ids[:1]
    assert manager.queuedIds() == ids[1:]
    screen.rect = QRect(0, 0, 500, 300)
    screen.availableGeometryChanged.emit(screen.rect)
    settle()
    assert screen.rect.contains(manager.notification(ids[0]).geometry())
    manager.setMaxVisible(3)
    settle()
    assert len(manager.visibleIds()) >= 2
    assert all(
        screen.rect.contains(manager.notification(key).geometry()) for key in manager.visibleIds()
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
    key = manager.notify("Mixed DPI", duration=0)
    card = manager.notification(key)
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
    card = manager.notification(manager.notify("Screen", duration=0))
    settle()

    assert card._screen_change_window is card.windowHandle()
    card.hide()
    assert card._screen_change_window is None
    card.show()
    assert card._screen_change_window is card.windowHandle()


def test_desktop_card_delegates_native_dpi_constraints(managers, monkeypatch):
    create, *_ = managers
    manager = create()
    card = manager.notification(manager.notify("DPI", duration=0))
    calls = []
    monkeypatch.setattr(
        card._native_dpi,
        "handle_native_event",
        lambda widget, message: calls.append((widget, message)) or True,
    )

    assert card.nativeEvent(b"windows_generic_MSG", 123) == (True, 0)
    assert calls == [(card, 123)]
