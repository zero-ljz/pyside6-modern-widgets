"""Real caption dragging, including the native modal move loop and wrapped labels."""

import ctypes
import json
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QTranslator
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from examples.edge_dock_example import EdgeDockExample
from pyside6_modern_widgets import ModernWindow
from pyside6_modern_widgets._windows_window import (
    _WindowPosition,
    bring_window_to_front,
    mouse_buttons_pressed,
    read_message,
    window_is_at_cursor,
)

_APP = QApplication.instance() or QApplication([])

# A separate process is required: QWidget.nativeEvent enters Windows' modal move
# loop synchronously, so a Python thread in this process cannot drive the mouse.
_DRIVER = """
import ctypes, json, sys, time
from ctypes import wintypes
user32 = ctypes.WinDLL('user32')
try:
    # Match Qt's per-monitor awareness so cursor coordinates are physical pixels.
    assert user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    hwnd, sx, sy, ex, ey, round_trip = map(int, sys.argv[1:])
    time.sleep(.2)
    targets = [(ex, ey), (sx, sy)] if round_trip else [(ex, ey)]
    for ex, ey in targets:
        for i in range(1, 25):
            user32.SetCursorPos(round(sx + (ex - sx) * i / 24), round(sy + (ey - sy) * i / 24))
            time.sleep(.02)
        sx, sy = ex, ey
    # Measure the HWND while the button is still held. A release-time resize
    # workaround must fail this test, even if the final QWidget size is right.
    time.sleep(.2)
    user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    rect = wintypes.RECT()
    assert user32.GetWindowRect(hwnd, ctypes.byref(rect))
    print(json.dumps([rect.right - rect.left, rect.bottom - rect.top,
                      bool(user32.GetAsyncKeyState(1) & 0x8000)]), flush=True)
finally:
    user32.mouse_event(4, 0, 0, 0, 0)
"""


class _ObservedControls(EdgeDockExample):
    observe_caption = False

    def nativeEvent(self, event_type, address):
        message = read_message(int(address))
        if self.observe_caption and message.message == 0x0047:  # WM_WINDOWPOSCHANGED
            position = ctypes.cast(message.l_param, ctypes.POINTER(_WindowPosition)).contents
            if not position.flags & 0x0001:  # SWP_NOSIZE
                self.native_sizes.append((position.cx, position.cy, self._native_dpi.scale))
        return super().nativeEvent(event_type, address)

    def resizeEvent(self, event):
        if self.observe_caption:
            self.logical_sizes.append(event.size())
        super().resizeEvent(event)


@pytest.mark.parametrize("language", ["en", "zh_CN"])
@pytest.mark.parametrize("owned", [False, True])
def test_native_controls_caption_round_trips_preserve_size(theme_manager_instance, language, owned):
    if sys.platform != "win32" or QApplication.platformName() != "windows":
        pytest.skip("requires native Windows desktop interaction")
    screens = sorted(QApplication.screens(), key=lambda screen: screen.devicePixelRatio())
    if len(screens) < 2 or screens[0].devicePixelRatio() == screens[-1].devicePixelRatio():
        pytest.skip("requires two displays with different DPI")
    if mouse_buttons_pressed():
        pytest.skip("a physical mouse button is held")
    low, high = screens[0], screens[-1]
    translator = QTranslator()
    if language == "zh_CN":
        assert translator.load(
            str(Path(__file__).parents[1] / "examples/translations/examples_zh_CN.qm")
        )
        _APP.installTranslator(translator)
    parent = ModernWindow() if owned else None
    if parent is not None:
        parent.show()
    window = _ObservedControls(parent)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    user32.mouse_event.argtypes = (
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_size_t,
    )
    previous_cursor = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(previous_cursor))
    worker = None

    def drag(start, end, *, round_trip=False):
        nonlocal worker
        assert bring_window_to_front(hwnd)
        user32.SetCursorPos(*start)
        QTest.qWait(150)
        assert window_is_at_cursor(hwnd)
        worker = subprocess.Popen(
            [sys.executable, "-c", _DRIVER, *map(str, (hwnd, *start, *end, int(round_trip)))],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        user32.mouse_event(2, 0, 0, 0, 0)
        QTest.qWait(1800 if round_trip else 1200)
        output, error = worker.communicate(timeout=3)
        assert worker.returncode == 0, error
        worker = None
        width, height, held = json.loads(output)
        assert held, "measurement must precede mouse release"
        return width, height

    try:
        window.move(low.availableGeometry().topLeft() + QPoint(100, 100))
        window.show()
        QTest.qWait(500)
        size = window.size()
        hwnd = int(window.winId())
        for screen in (high, low, high, low):
            native = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(native))
            start = (
                native.left + round(80 * window.devicePixelRatioF()),
                native.top + round(15 * window.devicePixelRatioF()),
            )
            end = (
                screen.geometry().left() + round(150 * screen.devicePixelRatio()),
                screen.geometry().top() + round(100 * screen.devicePixelRatio()),
            )
            window.native_sizes = []
            window.logical_sizes = []
            window.observe_caption = True
            held_size = drag(start, end)
            window.observe_caption = False
            scale = screen.devicePixelRatio()
            assert held_size == (round(size.width() * scale), round(size.height() * scale))
            assert window.native_sizes, "must observe the actual native DPI resize"
            for width, height, scale in window.native_sizes:
                assert abs(width - size.width() * scale) <= 1
                assert abs(height - size.height() * scale) <= 1
            assert all(observed == size for observed in window.logical_sizes)
            assert window.screen() is screen
            assert window.size() == size, (language, owned, screen.name(), size, window.size())
        # Cross to the other display and back without ever releasing the mouse.
        native = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(native))
        start = (
            native.left + round(80 * low.devicePixelRatio()),
            native.top + round(15 * low.devicePixelRatio()),
        )
        end = (
            high.geometry().left() + round(150 * high.devicePixelRatio()),
            high.geometry().top() + round(100 * high.devicePixelRatio()),
        )
        window.native_sizes = []
        window.logical_sizes = []
        window.observe_caption = True
        held_size = drag(start, end, round_trip=True)
        window.observe_caption = False
        assert window.screen() is low
        assert held_size == (
            round(size.width() * low.devicePixelRatio()),
            round(size.height() * low.devicePixelRatio()),
        )
        assert {scale for _, _, scale in window.native_sizes} == {
            low.devicePixelRatio(),
            high.devicePixelRatio(),
        }
        for width, height, scale in window.native_sizes:
            assert abs(width - size.width() * scale) <= 1
            assert abs(height - size.height() * scale) <= 1
        assert all(observed == size for observed in window.logical_sizes)
        assert window.size() == size
        # Moving must not leave a size lock behind for native border resizing.
        native = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(native))
        start = (native.right - 3, native.bottom - 3)
        end = (
            start[0] + round(40 * low.devicePixelRatio()),
            start[1] + round(30 * low.devicePixelRatio()),
        )
        drag(start, end)
        assert abs(window.width() - size.width() - 40) <= 1
        assert abs(window.height() - size.height() - 30) <= 1
        # Programmatic resizing remains available too.
        window.resize(size.width() + 60, size.height() + 50)
        QTest.qWait(500)
        assert window.width() == size.width() + 60
        assert window.height() == size.height() + 50
    finally:
        user32.mouse_event(4, 0, 0, 0, 0)
        if worker is not None:
            worker.wait(timeout=3)
        user32.SetCursorPos(previous_cursor.x, previous_cursor.y)
        window.close()
        window.deleteLater()
        if parent is not None:
            parent.close()
            parent.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        if language == "zh_CN":
            _APP.removeTranslator(translator)
