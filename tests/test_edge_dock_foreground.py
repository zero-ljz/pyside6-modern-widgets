"""Native foreground transfer from another process when restoring an edge tool."""

import os
import subprocess
import sys
import textwrap

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows foreground activation")
@pytest.mark.parametrize("modern", [False, True])
@pytest.mark.parametrize("mode", ["hover_or_click", "click", "drag_or_click"])
def test_restore_takes_foreground_from_another_process(modern, mode):
    cover_script = textwrap.dedent("""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication, QWidget
        app = QApplication([])
        window = QWidget()
        window.setWindowTitle("Edge dock foreground regression - covering window")
        window.setGeometry(0, 0, 500, 600)
        window.show()
        app.processEvents()
        print(int(window.winId()), flush=True)
        QTimer.singleShot(10000, app.quit)
        app.exec()
    """)
    script = textwrap.dedent("""
        import ctypes
        from ctypes import wintypes
        import subprocess
        import sys
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QEnterEvent
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication, QWidget
        from pyside6_modern_widgets import (
            DockConfig, DockSide, EdgeDockController, ModernWindow, theme_manager,
        )
        from pyside6_modern_widgets._windows_window import bring_window_to_front

        app = QApplication([])
        theme_manager().setWallpaperEnabled(False)
        target = (ModernWindow if MODERN else QWidget)()
        target.resize(240, 160)
        target.show()
        app.processEvents()
        controller = EdgeDockController(
            target, DockConfig(anim_duration=0, auto_hide=False, handle_mode=MODE)
        )
        controller._buttons_pressed = lambda **_: False
        controller.dock(DockSide.LEFT)
        assert controller.collapse()
        flags = target.windowFlags()
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetForegroundWindow.argtypes = ()
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int)
        user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        target_hwnd = int(target.winId())
        before_topmost = user32.GetWindowLongPtrW(target_hwnd, -20) & 0x00000008
        cover = subprocess.Popen(
            [sys.executable, "-c", COVER_SCRIPT], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        try:
            cover_hwnd = int(cover.stdout.readline())
            assert bring_window_to_front(cover_hwnd), "could not foreground the test cover"
            QTest.qWait(50)
            assert user32.GetForegroundWindow() == cover_hwnd
            if MODE == "hover_or_click":
                point = QPointF(controller._handle.rect().center())
                app.sendEvent(controller._handle, QEnterEvent(point, point, point))
            else:
                QTest.mouseClick(controller._handle, Qt.LeftButton)
            QTest.qWait(200)
            assert target.isVisible() and not controller.isCollapsed()
            assert user32.GetForegroundWindow() == target_hwnd
            assert target.windowFlags() == flags
            assert user32.GetWindowLongPtrW(target_hwnd, -20) & 0x00000008 == before_topmost
        finally:
            cover.terminate()
            cover.communicate(timeout=5)
            controller.detach()
            target.close()
    """)
    script = f"MODERN = {modern!r}\nMODE = {mode!r}\nCOVER_SCRIPT = {cover_script!r}\n" + script
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "QT_QPA_PLATFORM": "windows"},
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr, result.stderr
