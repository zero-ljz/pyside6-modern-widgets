"""Mixed-DPI native drag regression without any application-specific widgets."""

import ctypes

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QWidget

from pyside6_modern_widgets import ModernDialog, ModernWindow
from pyside6_modern_widgets import modern_dialog as dialog_module
from pyside6_modern_widgets import modern_window as window_module
from pyside6_modern_widgets._windows_window import (
    WM_DPICHANGED,
    WM_GETMINMAXINFO,
    WindowsMessage,
    _MinMaxInfo,
)

_APP = QApplication.instance() or QApplication([])


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
    module = dialog_module if window_class is ModernDialog else window_module
    if window_class is ModernDialog:
        monkeypatch.setattr(module, "uses_windows_window_state", lambda: True)
        monkeypatch.setattr(module, "window_dpi", lambda _: 168)
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
        dialog.close()
        dialog.deleteLater()
        QCoreApplication.sendPostedEvents(dialog, QEvent.Type.DeferredDelete)


def test_non_windows_dialog_does_not_decode_native_messages(monkeypatch):
    monkeypatch.setattr(dialog_module, "uses_windows_window_state", lambda: False, raising=False)
    monkeypatch.setattr(QWidget, "nativeEvent", lambda *_: (False, 0))

    def unexpected_read(_):
        pytest.fail("Non-Windows dialogs must not decode Win32 pointers")

    monkeypatch.setattr(dialog_module, "read_message", unexpected_read, raising=False)
    dialog = ModernDialog()
    assert dialog.nativeEvent(b"other_platform", 0) == (False, 0)
    dialog.close()


def test_dialog_refreshes_dpi_after_native_handle_change(monkeypatch):
    monkeypatch.setattr(dialog_module, "uses_windows_window_state", lambda: True, raising=False)
    dpi = [168]
    monkeypatch.setattr(dialog_module, "window_dpi", lambda _: dpi[0], raising=False)
    dialog = ModernDialog()
    monkeypatch.setattr(dialog, "devicePixelRatioF", lambda: dpi[0] / 96)
    dialog.show()
    try:
        assert dialog._native_dpi.dpi == 168
        assert dialog._native_dpi.scale == 1.75
        dpi[0] = 96
        _APP.sendEvent(dialog, QEvent(QEvent.Type.WinIdChange))
        assert dialog._native_dpi.dpi == 96
        assert dialog._native_dpi.scale == 1.0
    finally:
        dialog.close()
