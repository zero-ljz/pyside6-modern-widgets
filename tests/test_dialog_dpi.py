"""Mixed-DPI native drag regression without any application-specific widgets."""

import ctypes
import os
import subprocess
import sys
import textwrap

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QWidget

from pyside6_modern_widgets import ModernDialog, ModernMessageBox, ModernWindow
from pyside6_modern_widgets import _window_chrome as chrome_module
from pyside6_modern_widgets import modern_window as window_module
from pyside6_modern_widgets._windows_window import (
    WM_DPICHANGED,
    WM_EXITSIZEMOVE,
    WM_GETDPISCALEDSIZE,
    WM_GETMINMAXINFO,
    WindowsMessage,
    _MinMaxInfo,
)

_APP = QApplication.instance() or QApplication([])


@pytest.mark.skipif(sys.platform != "win32", reason="Requires the Windows Qt platform plugin")
def test_native_dpi_size_query_uses_target_bounds_before_dpi_change():
    # Exercise Qt's actual WM_GETDPISCALEDSIZE and WM_GETMINMAXINFO handlers in
    # a separate native process, without changing the user's display settings.
    script = textwrap.dedent("""
        import ctypes
        from ctypes import wintypes
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        from pyside6_modern_widgets import (
            ModernDialog, ModernMessageBox, ModernWindow, theme_manager,
        )
        from pyside6_modern_widgets._windows_window import (
            WM_EXITSIZEMOVE, WM_GETDPISCALEDSIZE, WM_GETMINMAXINFO,
            _MinMaxInfo, window_dpi,
        )

        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QApplication([])
        theme_manager().setWallpaperEnabled(False)
        send = ctypes.WinDLL("user32").SendMessageW
        send.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        send.restype = wintypes.LPARAM
        for cls in (ModernDialog, ModernWindow, ModernMessageBox):
            window = cls()
            window.setAttribute(Qt.WA_DontShowOnScreen)
            window.setMinimumSize(480, 350)
            window.setMaximumSize(1000, 800)
            window.resize(500, 370)
            window.show()
            app.processEvents()
            hwnd = int(window.winId())
            dpi, scale = window_dpi(hwnd), window.devicePixelRatioF()
            target = 96 if dpi > 96 else 168
            minimum = window.minimumSize().toTuple()
            maximum = window.maximumSize().toTuple()
            size = wintypes.SIZE()
            assert send(hwnd, WM_GETDPISCALEDSIZE, target, ctypes.addressof(size)) == 1
            info = _MinMaxInfo()
            send(hwnd, WM_GETMINMAXINFO, 0, ctypes.addressof(info))
            expected = tuple(int(v * scale * target / dpi + 0.5) for v in minimum)
            assert (info.ptMinTrackSize.x, info.ptMinTrackSize.y) == expected, cls.__name__
            expected = tuple(int(v * scale * target / dpi + 0.5) for v in maximum)
            assert (info.ptMaxTrackSize.x, info.ptMaxTrackSize.y) == expected, cls.__name__
            send(hwnd, WM_EXITSIZEMOVE, 0, 0)
            send(hwnd, WM_GETMINMAXINFO, 0, ctypes.addressof(info))
            expected = tuple(int(v * scale + 0.5) for v in minimum)
            assert (info.ptMinTrackSize.x, info.ptMinTrackSize.y) == expected, cls.__name__
            window.close()
    """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "windows",
            "QT_SCALE_FACTOR_ROUNDING_POLICY": "PassThrough",
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr, result.stderr


@pytest.mark.parametrize("window_class", [ModernDialog, ModernWindow, ModernMessageBox])
def test_target_constraints_apply_during_dpi_size_query_and_clear_on_cancel(
    monkeypatch, window_class
):
    # Windows asks for the target size before WM_DPICHANGED. Its intervening
    # minimum-size query must not clamp that size to the source monitor's minimum.
    module = window_module if window_class is ModernWindow else chrome_module
    monkeypatch.setattr(QWidget, "nativeEvent", lambda *_: (False, 0))
    monkeypatch.setattr(
        QApplication,
        "highDpiScaleFactorRoundingPolicy",
        lambda: Qt.HighDpiScaleFactorRoundingPolicy.PassThrough,
    )
    window = window_class()
    window.setMinimumSize(480, 350)
    window.setMaximumSize(1000, 800)
    monkeypatch.setattr(chrome_module, "uses_windows_window_state", lambda: True)
    if window_class is ModernWindow:
        monkeypatch.setattr(window, "_uses_windows_window_state", lambda: True)
        window._native_frame_enabled = True
    window._native_dpi.reset(168, 1.75)
    message = [WindowsMessage(1, 0, 0, 0)]
    monkeypatch.setattr(module, "read_message", lambda _: message[0])

    def constraints():
        info = _MinMaxInfo()
        info.ptMinTrackSize.x, info.ptMinTrackSize.y = 840, 613
        info.ptMaxTrackSize.x, info.ptMaxTrackSize.y = 1750, 1400
        message[0] = WindowsMessage(1, WM_GETMINMAXINFO, 0, ctypes.addressof(info))
        handled = window.nativeEvent(b"windows_generic_MSG", 0)
        return handled, info

    try:
        for cancelled in (True, False):
            # Repeated speculative queries must not compound the scale change.
            for dpi in (96, 168, 96, 96):
                message[0] = WindowsMessage(1, WM_GETDPISCALEDSIZE, dpi, 0)
                assert window.nativeEvent(b"windows_generic_MSG", 0) == (False, 0)
                handled, info = constraints()
                assert handled == (True, 0)
                assert (info.ptMinTrackSize.x, info.ptMinTrackSize.y) == (
                    int(480 * dpi / 96 + 0.5),
                    int(350 * dpi / 96 + 0.5),
                )
                assert (info.ptMaxTrackSize.x, info.ptMaxTrackSize.y) == (
                    int(1000 * dpi / 96 + 0.5),
                    int(800 * dpi / 96 + 0.5),
                )
            assert window._native_dpi.dpi == 168
            assert window._native_dpi.scale == 1.75
            if cancelled:
                message[0] = WindowsMessage(1, WM_EXITSIZEMOVE, 0, 0)
                window.nativeEvent(b"windows_generic_MSG", 0)
                assert constraints()[0] == (False, 0)
            else:
                message[0] = WindowsMessage(1, WM_DPICHANGED, 96 | (96 << 16), 0)
                window.nativeEvent(b"windows_generic_MSG", 0)
                assert window._native_dpi.scale == 1.0
                handled, info = constraints()
                assert handled == (True, 0)
                assert (info.ptMinTrackSize.x, info.ptMinTrackSize.y) == (480, 350)
    finally:
        monkeypatch.setattr(chrome_module, "uses_windows_window_state", lambda: False)
        if window_class is ModernWindow:
            monkeypatch.setattr(window, "_uses_windows_window_state", lambda: False)
            window._native_frame_enabled = False
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(window, QEvent.Type.DeferredDelete)


def test_message_box_dpi_constraints_follow_details_expansion(monkeypatch):
    box = ModernMessageBox(
        ModernMessageBox.Icon.Warning, "Details", "Test message", ModernMessageBox.StandardButton.Ok
    )
    box.setDetailedText("Diagnostic information\n" * 12)
    box.show()
    _APP.processEvents()
    collapsed_size = box.size()
    details = next(
        button
        for button in box.buttons()
        if box.standardButton(button) == ModernMessageBox.StandardButton.NoButton
    )
    monkeypatch.setattr(QWidget, "nativeEvent", lambda *_: (False, 0))
    monkeypatch.setattr(chrome_module, "uses_windows_window_state", lambda: True)
    monkeypatch.setattr(
        QApplication,
        "highDpiScaleFactorRoundingPolicy",
        lambda: Qt.HighDpiScaleFactorRoundingPolicy.PassThrough,
    )
    message = [WindowsMessage(1, 0, 0, 0)]
    monkeypatch.setattr(chrome_module, "read_message", lambda _: message[0])
    box._native_dpi.reset(168, 1.75)
    try:
        for expanded in (False, True, False):
            for dpi, scale in ((96, 1.0), (168, 1.75)):
                message[0] = WindowsMessage(1, WM_DPICHANGED, dpi | (dpi << 16), 0)
                assert box.nativeEvent(b"windows_generic_MSG", 0) == (False, 0)
                info = _MinMaxInfo()
                info.ptMaxTrackSize.x = info.ptMaxTrackSize.y = 100000
                message[0] = WindowsMessage(1, WM_GETMINMAXINFO, 0, ctypes.addressof(info))
                assert box.nativeEvent(b"windows_generic_MSG", 0) == (True, 0)
                assert (info.ptMinTrackSize.x, info.ptMinTrackSize.y) == (
                    int(box.minimumWidth() * scale + 0.5),
                    int(box.minimumHeight() * scale + 0.5),
                )
                assert (info.ptMaxTrackSize.x, info.ptMaxTrackSize.y) == (
                    *(
                        int(bound * scale + 0.5) if bound < 16777215 else 100000
                        for bound in (box.maximumWidth(), box.maximumHeight())
                    ),
                )
            assert (box.height() > collapsed_size.height()) == expanded
            details.click()
            _APP.processEvents()
    finally:
        monkeypatch.setattr(chrome_module, "uses_windows_window_state", lambda: False)
        box.close()
        box.deleteLater()
        QCoreApplication.sendPostedEvents(box, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("window_class", [ModernDialog, ModernWindow])
@pytest.mark.parametrize("qt_screen_updated", [False, True])
@pytest.mark.parametrize(
    ("initial_scale", "policy", "low_scale"),
    [
        (1.75, "PassThrough", 1.0),
        (3.5, "PassThrough", 2.0),
        (2.0, "Round", 1.0),
        (1.0, "Floor", 1.0),
    ],
)
def test_window_and_dialog_drag_use_target_dpi_constraints(
    monkeypatch, window_class, qt_screen_updated, initial_scale, policy, low_scale
):
    # Use the same native message sequence and bounds for both public widgets.
    module = chrome_module if window_class is ModernDialog else window_module
    monkeypatch.setattr(QWidget, "nativeEvent", lambda *_: (False, 0))
    monkeypatch.setattr(
        QApplication,
        "highDpiScaleFactorRoundingPolicy",
        lambda: getattr(Qt.HighDpiScaleFactorRoundingPolicy, policy),
    )
    dialog = window_class()
    monkeypatch.setattr(dialog, "devicePixelRatioF", lambda: initial_scale)
    dialog.setMinimumSize(480, 350)
    dialog.setMaximumSize(1000, 800)
    dialog.resize(500, 370)
    dialog.show()
    _APP.processEvents()
    if window_class is ModernWindow:
        # Enable native handling after offscreen initialization to avoid asking
        # Windows to install a frame on an offscreen platform's fake handle.
        monkeypatch.setattr(dialog, "_uses_windows_window_state", lambda: True)
        dialog._native_frame_enabled = True
        dialog._native_dpi.reset(168, initial_scale)
    if window_class is ModernDialog:
        monkeypatch.setattr(chrome_module, "uses_windows_window_state", lambda: True)
        dialog._native_dpi.reset(168, initial_scale)
    message = [WindowsMessage(1, 0, 0, 0)]
    monkeypatch.setattr(module, "read_message", lambda _: message[0])
    try:
        previous_scale = initial_scale
        # Include rapid reversals at the monitor boundary, not just one move.
        for dpi, scale in ((96, low_scale), (168, initial_scale), (96, low_scale)) * 3:
            qt_scale = scale if qt_screen_updated else previous_scale
            monkeypatch.setattr(dialog, "devicePixelRatioF", lambda qt_scale=qt_scale: qt_scale)
            message[0] = WindowsMessage(1, WM_DPICHANGED, dpi | (dpi << 16), 0)
            assert dialog.nativeEvent(b"windows_generic_MSG", 0) == (False, 0)
            info = _MinMaxInfo()
            info.ptMinTrackSize.x, info.ptMinTrackSize.y = 840, 613
            info.ptMaxSize.x, info.ptMaxSize.y = 1920, 1080
            info.ptMaxPosition.x, info.ptMaxPosition.y = -1920, 20
            message[0] = WindowsMessage(1, WM_GETMINMAXINFO, 0, ctypes.addressof(info))
            assert dialog.nativeEvent(b"windows_generic_MSG", 0) == (True, 0)
            assert (info.ptMinTrackSize.x, info.ptMinTrackSize.y) == (
                int(480 * scale + 0.5),
                int(350 * scale + 0.5),
            )
            assert (info.ptMaxTrackSize.x, info.ptMaxTrackSize.y) == (
                int(1000 * scale + 0.5),
                int(800 * scale + 0.5),
            )
            assert (info.ptMaxSize.x, info.ptMaxSize.y) == (1920, 1080)
            assert (info.ptMaxPosition.x, info.ptMaxPosition.y) == (-1920, 20)
            previous_scale = scale
        assert dialog.size().toTuple() == (500, 370)
        dialog.resize(620, 460)
        assert dialog.size().toTuple() == (620, 460)
    finally:
        if window_class is ModernWindow:
            monkeypatch.setattr(dialog, "_uses_windows_window_state", lambda: False)
            dialog._native_frame_enabled = False
        monkeypatch.setattr(chrome_module, "uses_windows_window_state", lambda: False)
        dialog.close()
        dialog.deleteLater()
        QCoreApplication.sendPostedEvents(dialog, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("window_class", [ModernDialog, ModernMessageBox])
def test_non_windows_dialog_does_not_decode_native_messages(monkeypatch, window_class):
    monkeypatch.setattr(chrome_module, "uses_windows_window_state", lambda: False)
    monkeypatch.setattr(QWidget, "nativeEvent", lambda *_: (False, 0))

    def unexpected_read(_):
        pytest.fail("Non-Windows dialogs must not decode Win32 pointers")

    monkeypatch.setattr(chrome_module, "read_message", unexpected_read)
    dialog = window_class()
    assert dialog.nativeEvent(b"other_platform", 0) == (False, 0)
    dialog.close()


@pytest.mark.parametrize("window_class", [ModernDialog, ModernMessageBox])
def test_dialog_refreshes_dpi_after_native_handle_change(monkeypatch, window_class):
    dpi = [168]
    monkeypatch.setattr(chrome_module, "window_dpi", lambda _: dpi[0])
    dialog = window_class()
    monkeypatch.setattr(dialog, "devicePixelRatioF", lambda: dpi[0] / 96)
    dialog.show()
    monkeypatch.setattr(chrome_module, "uses_windows_window_state", lambda: True)
    _APP.sendEvent(dialog, QEvent(QEvent.Type.WinIdChange))
    try:
        assert dialog._native_dpi.dpi == 168
        assert dialog._native_dpi.scale == 1.75
        dpi[0] = 96
        _APP.sendEvent(dialog, QEvent(QEvent.Type.WinIdChange))
        assert dialog._native_dpi.dpi == 96
        assert dialog._native_dpi.scale == 1.0
    finally:
        monkeypatch.setattr(chrome_module, "uses_windows_window_state", lambda: False)
        dialog.close()
        dialog.deleteLater()
        QCoreApplication.sendPostedEvents(dialog, QEvent.Type.DeferredDelete)
