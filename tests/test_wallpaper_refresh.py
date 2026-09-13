from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pyside6_modern_widgets import theme as theme_module
from pyside6_modern_widgets.theme import DARK_THEME, LIGHT_THEME, ThemeManager, theme_manager

_APP = QApplication.instance() or QApplication([])


def _wait_until(predicate):
    deadline = time.monotonic() + 3
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(10)
    assert predicate()


@pytest.fixture
def manager(monkeypatch):
    # Isolate test workers from the process-wide wallpaper monitor used by widgets.
    global_manager = theme_manager()
    timers = [global_manager._wallpaper_poll_timer, global_manager._wallpaper_refresh_timer]
    running = [timer for timer in timers if timer is not None and timer.isActive()]
    for timer in running:
        timer.stop()
    _wait_until(lambda: global_manager._wallpaper_future is None)
    palette = _APP.palette()
    with ThreadPoolExecutor(max_workers=1) as executor:
        monkeypatch.setattr(theme_module, "_WALLPAPER_EXECUTOR", executor)
        instance = ThemeManager()
        try:
            yield instance
        finally:
            for timer in instance.findChildren(QTimer):
                timer.stop()
            instance.deleteLater()
            QCoreApplication.sendPostedEvents(instance, QEvent.Type.DeferredDelete)
            _APP.setPalette(palette)
    for timer in running:
        timer.start()


@pytest.mark.parametrize("slow_stage", ["discovery", "sampling"])
def test_slow_wallpaper_work_keeps_gui_responsive_and_publishes_on_gui_thread(
    manager, monkeypatch, tmp_path, slow_stage
):
    path = tmp_path / "wallpaper.png"
    path.touch()
    entered, release = threading.Event(), threading.Event()
    calls = []
    gui_thread = threading.get_ident()

    def block():
        entered.set()
        assert release.wait(2)

    def discover():
        calls.append(("discovery", threading.get_ident()))
        if slow_stage == "discovery":
            block()
        return path

    def sample(_path):
        calls.append(("sampling", threading.get_ident()))
        if slow_stage == "sampling":
            block()
        return (QColor("red"),)

    monkeypatch.setattr(theme_module, "desktop_wallpaper_path", discover)
    monkeypatch.setattr(theme_module, "wallpaper_colors", sample)
    signals = []
    manager.themeChanged.connect(lambda theme: signals.append((theme, threading.get_ident())))
    ticks = []
    heartbeat = QTimer()
    heartbeat.setInterval(10)
    heartbeat.timeout.connect(lambda: ticks.append(True))
    heartbeat.start()
    try:
        assert manager.theme() == LIGHT_THEME
        _wait_until(entered.is_set)
        for _ in range(10):
            manager._poll_wallpaper_update()
        QTest.qWait(60)
        assert len(ticks) >= 2
        assert not manager._wallpaper_future.done()
        assert not signals
    finally:
        release.set()
        heartbeat.stop()
    _wait_until(lambda: manager._wallpaper_future is None)
    assert [stage for stage, _thread in calls] == ["discovery", "sampling"]
    assert all(worker != gui_thread for _stage, worker in calls)
    assert len(signals) == 1
    assert signals[0][1] == gui_thread
    assert manager.theme().watercolor_base != LIGHT_THEME.watercolor_base


def test_missing_wallpaper_is_discovered_once_per_poll(manager, monkeypatch):
    discoveries = []
    monkeypatch.setattr(theme_module, "desktop_wallpaper_path", lambda: discoveries.append(1))

    def unexpected(_path):
        pytest.fail("Missing wallpaper must not trigger metadata lookup or image loading")

    monkeypatch.setattr(theme_module, "wallpaper_signature", unexpected)
    monkeypatch.setattr(theme_module, "wallpaper_colors", unexpected)
    manager.refreshWallpaperTheme()
    _wait_until(lambda: manager._wallpaper_future is None)
    assert discoveries == [1]
    manager._poll_wallpaper_update()
    _wait_until(lambda: manager._wallpaper_future is None)
    assert discoveries == [1, 1]


def test_unchanged_wallpaper_skips_sampling_but_explicit_refresh_resamples(
    manager, monkeypatch, tmp_path
):
    path = tmp_path / "wallpaper.png"
    path.touch()
    samples = []
    monkeypatch.setattr(theme_module, "desktop_wallpaper_path", lambda: path)
    monkeypatch.setattr(
        theme_module, "wallpaper_colors", lambda path: samples.append(path) or (QColor("red"),)
    )
    manager.refreshWallpaperTheme()
    _wait_until(lambda: manager._wallpaper_future is None)
    manager._poll_wallpaper_update()
    _wait_until(lambda: manager._wallpaper_future is None)
    assert samples == [path]
    manager.refreshWallpaperTheme()
    _wait_until(lambda: manager._wallpaper_future is None)
    assert samples == [path, path]
    assert str(path) in manager._wallpaper_watcher.files()


@pytest.mark.parametrize("manual_theme", [False, True])
def test_refresh_requests_coalesce_and_late_results_respect_manual_theme(
    manager, monkeypatch, tmp_path, manual_theme
):
    path = tmp_path / "wallpaper.png"
    path.touch()
    entered, release = threading.Event(), threading.Event()
    discoveries = []

    def discover():
        discoveries.append(1)
        if len(discoveries) == 1:
            entered.set()
            assert release.wait(2)
        return path

    monkeypatch.setattr(theme_module, "desktop_wallpaper_path", discover)
    monkeypatch.setattr(theme_module, "wallpaper_colors", lambda _path: (QColor("red"),))
    manager.theme()
    try:
        _wait_until(entered.is_set)
        for _ in range(10):
            manager.refreshWallpaperTheme()
        selected = replace(DARK_THEME, focus="#123456")
        if manual_theme:
            manager.setTheme(selected)
    finally:
        release.set()
    _wait_until(lambda: manager._wallpaper_future is None)
    assert len(discoveries) == (1 if manual_theme else 2)
    if manual_theme:
        assert manager.theme() == selected
        # Following the system again can use the cached colors immediately.
        manager.setFollowsSystemTheme(True)
        assert manager.theme().surface == DARK_THEME.surface
        assert manager.theme().watercolor_base != selected.watercolor_base
        _wait_until(lambda: manager._wallpaper_future is None)


def test_failed_background_query_can_retry(manager, monkeypatch):
    attempts = []

    def discover():
        attempts.append(1)
        if len(attempts) == 1:
            raise OSError("Temporary wallpaper lookup failure")

    monkeypatch.setattr(theme_module, "desktop_wallpaper_path", discover)
    manager.refreshWallpaperTheme()
    _wait_until(lambda: manager._wallpaper_future is None)
    assert manager.theme() == LIGHT_THEME
    manager._poll_wallpaper_update()
    _wait_until(lambda: manager._wallpaper_future is None)
    assert attempts == [1, 1]
