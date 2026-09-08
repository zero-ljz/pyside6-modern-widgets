from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QWidget

from pyside6_modern_widgets import ModernDialog
from pyside6_modern_widgets._window_chrome import WindowTitleBar
from pyside6_modern_widgets.theme import DEFAULT_METRICS, theme_manager


class _WindowProbe(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.Window | Qt.WindowType.WindowMaximizeButtonHint,
        )
        self.maximize_calls = 0
        self.normal_calls = 0
        self.full_screen = False

    def isFullScreen(self) -> bool:
        return self.full_screen

    def showMaximized(self) -> None:
        self.maximize_calls += 1

    def showNormal(self) -> None:
        self.normal_calls += 1


class ModernDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        self.application.processEvents()

    def test_constructor_accepts_standard_parent_and_flags(self) -> None:
        parent = QWidget()
        dialog = ModernDialog(
            parent,
            Qt.WindowType.Tool | Qt.WindowType.WindowCloseButtonHint,
        )

        self.assertIs(dialog.parentWidget(), parent)
        self.assertEqual(
            dialog.windowFlags() & Qt.WindowType.WindowType_Mask,
            Qt.WindowType.Tool,
        )
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.FramelessWindowHint)

    def test_default_constructor_preserves_standard_close_capability(self) -> None:
        dialog = ModernDialog()

        self.assertTrue(dialog.windowFlags() & Qt.WindowType.WindowSystemMenuHint)
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.WindowCloseButtonHint)
        self.assertFalse(dialog._title_bar.closeButton.isHidden())

    def test_window_flag_changes_preserve_frameless_chrome(self) -> None:
        dialog = ModernDialog()
        customized_dialog = (
            Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint
        )

        dialog.setWindowFlags(customized_dialog)
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertFalse(dialog._title_bar.isHidden())
        self.assertTrue(dialog._title_bar.closeButton.isHidden())
        self.assertEqual(dialog.contentsMargins().top(), dialog._title_bar.height())

        dialog.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertFalse(dialog._title_bar.closeButton.isHidden())

        dialog.setWindowFlags(Qt.WindowType.Popup)
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(dialog._title_bar.isHidden())
        self.assertEqual(dialog.contentsMargins().top(), 0)

        dialog.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.FramelessWindowHint)

    def test_full_screen_uses_square_surface_and_has_no_resize_edges(self) -> None:
        dialog = ModernDialog()
        dialog.resize(320, 240)
        dialog.showFullScreen()
        self.application.processEvents()

        self.assertTrue(dialog.isFullScreen())
        self.assertEqual(dialog._background_frame._corner_radius, 0)
        self.assertEqual(dialog._chrome_overlay._corner_radius, 0)
        self.assertEqual(dialog._resize_edges_at(QPoint(0, 0)), Qt.Edge(0))

        dialog.close()

    def test_application_event_filter_only_runs_while_visible(self) -> None:
        dialog = ModernDialog()
        self.assertFalse(dialog._application_event_filter_installed)

        dialog.show()
        self.application.processEvents()
        self.assertTrue(dialog._application_event_filter_installed)

        dialog.hide()
        self.application.processEvents()
        self.assertFalse(dialog._application_event_filter_installed)

        dialog.show()
        self.application.processEvents()
        dialog.close()
        self.application.processEvents()
        self.assertFalse(dialog._application_event_filter_installed)

    def test_title_bar_maximize_requires_hint_and_resizable_dimensions(self) -> None:
        window = _WindowProbe()
        title_bar = WindowTitleBar(
            window,
            theme=theme_manager().theme(),
            metrics=DEFAULT_METRICS,
            allows_maximize=True,
        )

        title_bar._toggle_maximize()
        self.assertEqual(window.maximize_calls, 1)

        window.setFixedSize(320, 240)
        title_bar._toggle_maximize()
        self.assertEqual(window.maximize_calls, 1)

        window.setMinimumSize(0, 0)
        window.setMaximumSize(16777215, 16777215)
        window.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        title_bar._toggle_maximize()
        self.assertEqual(window.maximize_calls, 1)

        window.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        window.full_screen = True
        title_bar._toggle_maximize()
        self.assertEqual(window.maximize_calls, 1)

    def test_manual_resize_fallback_respects_constraints(self) -> None:
        dialog = ModernDialog()
        dialog.setGeometry(100, 100, 320, 240)
        dialog.setMinimumSize(250, 180)

        dialog._begin_manual_resize(Qt.Edge.LeftEdge | Qt.Edge.TopEdge, QPoint(100, 100))
        dialog._update_manual_resize(QPoint(200, 200))

        self.assertEqual(dialog.geometry().getRect(), (170, 160, 250, 180))


if __name__ == "__main__":
    unittest.main()
