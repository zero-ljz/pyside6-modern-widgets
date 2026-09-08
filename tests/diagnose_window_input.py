"""Run an example with input-state logging: python tests/diagnose_window_input.py."""

from __future__ import annotations

import argparse
import ctypes
import faulthandler
import json
import runpy
import sys
import time
from ctypes import wintypes
from pathlib import Path
from typing import TextIO

from PySide6.QtCore import QAbstractNativeEventFilter, QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QWidget

from pyside6_modern_widgets import theme_manager


def describe(widget: QObject | None) -> dict | None:
    if widget is None:
        return None
    result = {"class": type(widget).__name__, "name": widget.objectName()}
    if isinstance(widget, QWidget):
        result.update(
            visible=widget.isVisible(),
            enabled=widget.isEnabled(),
            transparent=widget.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents),
            title=widget.windowTitle(),
        )
    return result


class GuiThreadInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


class InputTrace(QObject):
    def __init__(self, app: QApplication, log: TextIO, stacks: TextIO) -> None:
        super().__init__(app)
        self.log = log
        self.stacks = stacks
        self.last_tick = time.monotonic()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.snapshot)
        self.timer.start(1000)
        app.installEventFilter(self)

    def write(self, kind: str, **fields) -> None:
        self.log.write(json.dumps({"time": time.time(), "kind": kind, **fields}) + "\n")
        self.log.flush()

    def snapshot(self) -> None:
        now = time.monotonic()
        cursor = QCursor.pos()
        native = None
        if sys.platform == "win32":
            info = GuiThreadInfo(cbSize=ctypes.sizeof(GuiThreadInfo))
            user32 = ctypes.windll.user32
            user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GuiThreadInfo)]
            user32.GetGUIThreadInfo.restype = wintypes.BOOL
            if user32.GetGUIThreadInfo(
                ctypes.windll.kernel32.GetCurrentThreadId(), ctypes.byref(info)
            ):
                native = {
                    name: getattr(info, name)
                    for name in (
                        "flags",
                        "hwndActive",
                        "hwndCapture",
                        "hwndMenuOwner",
                        "hwndMoveSize",
                    )
                }
        self.write(
            "heartbeat",
            elapsed=now - self.last_tick,
            cursor=[cursor.x(), cursor.y()],
            under_cursor=describe(QApplication.widgetAt(cursor)),
            active=describe(QApplication.activeWindow()),
            popup=describe(QApplication.activePopupWidget()),
            modal=describe(QApplication.activeModalWidget()),
            mouse_grabber=describe(QWidget.mouseGrabber()),
            native=native,
        )
        self.last_tick = now
        faulthandler.dump_traceback_later(8, repeat=True, file=self.stacks)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.WindowBlocked,
            QEvent.Type.WindowUnblocked,
            QEvent.Type.GrabMouse,
            QEvent.Type.UngrabMouse,
        ):
            fields = {}
            if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
                fields.update(
                    position=[event.position().x(), event.position().y()],
                    global_position=[event.globalPosition().x(), event.globalPosition().y()],
                    button=event.button().name,
                    buttons=event.buttons().value,
                )
                if isinstance(watched, QWidget):
                    local = watched.mapFromGlobal(event.globalPosition().toPoint())
                    fields.update(
                        mapped_position=[local.x(), local.y()],
                        size=[watched.width(), watched.height()],
                    )
            self.write("qt_event", event=event.type().name, receiver=describe(watched), **fields)
        return False


class NativeInputTrace(QAbstractNativeEventFilter):
    def __init__(self, trace: InputTrace) -> None:
        super().__init__()
        self.trace = trace

    def nativeEventFilter(self, event_type, message):
        if sys.platform == "win32":
            msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
            if msg.message in (0x001A, 0x001F, 0x00A1, 0x00A2, 0x0201, 0x0202, 0x0215, 0x031A):
                self.trace.write(
                    "native_event",
                    hwnd=msg.hWnd,
                    message=hex(msg.message),
                    wparam=msg.wParam,
                    lparam=msg.lParam,
                )
        return False, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example", choices=("navigation", "tabs"), default="navigation")
    parser.add_argument("--log", type=Path, default=Path("build/window-input.jsonl"))
    parser.add_argument(
        "--duration", type=float, help="Close automatically after this many seconds"
    )
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    stack_path = args.log.with_suffix(".stacks.log")
    example, class_name = {
        "navigation": ("navigation_view_example.py", "ExampleWindow"),
        "tabs": ("tab_view_example.py", "TabViewWindow"),
    }[args.example]
    example_path = Path(__file__).resolve().parents[1] / "examples" / example
    app = QApplication([sys.argv[0]])
    app.setStyle("Fusion")
    with args.log.open("w", encoding="utf-8") as log, stack_path.open("w") as stacks:
        trace = InputTrace(app, log, stacks)
        native_trace = NativeInputTrace(trace)
        app.installNativeEventFilter(native_trace)
        faulthandler.enable(file=stacks)
        faulthandler.dump_traceback_later(8, repeat=True, file=stacks)

        def theme_changed(theme) -> None:
            trace.write("theme_changed", mode=theme.name, colors=theme.watercolor_spots)

        manager = theme_manager()
        manager.themeChanged.connect(theme_changed)
        try:
            window = runpy.run_path(str(example_path))[class_name]()
            window.setWindowTitle(window.windowTitle() + " [Input Diagnostics]")
            window.show()
            trace.snapshot()
            if args.duration is not None:
                QTimer.singleShot(max(1, int(args.duration * 1000)), app.quit)
            print(f"Input log: {args.log.resolve()}", flush=True)
            print(f"Blocked-thread stacks: {stack_path.resolve()}", flush=True)
            return app.exec()
        finally:
            trace.timer.stop()
            manager.themeChanged.disconnect(theme_changed)
            app.removeEventFilter(trace)
            app.removeNativeEventFilter(native_trace)
            faulthandler.cancel_dump_traceback_later()
            faulthandler.disable()


if __name__ == "__main__":
    raise SystemExit(main())
