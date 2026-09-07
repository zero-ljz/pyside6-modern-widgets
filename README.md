# pyside6-modern-widgets

Cross-platform desktop widgets for PySide6. The package provides frameless
window chrome, navigation, and tabs while retaining familiar Qt widget APIs.

- `ModernWindow`: a frameless replacement for top-level `QWidget` windows with
  selected `QMainWindow`-compatible methods.
- `ModernDialog`: a frameless `QDialog` that preserves the standard dialog API.
- `ModernMessageBox`: a themed message box with familiar `QMessageBox` buttons
  and convenience methods.
- `ModernMenu`: a native `QMenu` with Windows system acrylic (and a
  translucent fallback elsewhere) plus rounded outer and selected-item
  backgrounds.
- `NavigationSidebar`: a collapsible navigation sidebar.
- `NavigationView`: a sidebar and synchronized page stack in one widget.
- `TabView`: a WinUI-inspired tab widget.

## Supported environment

Supports Windows, macOS, and Linux with Python 3.10-3.12, PySide6 6.8.3, and
the Fusion style. Window backgrounds, including the custom title bar, use the
same Qt-painted standard or watercolor themes and behavior on every platform.

Right-clicking the custom title bar opens the native Windows system menu. On
platforms without an equivalent frameless-window API, a Qt menu provides the
available restore, minimize, maximize, and close commands.

## Installation

```shell
pip install pyside6-modern-widgets
```

## PyInstaller

The installed package automatically registers its PyInstaller hook. Applications
using these widgets can be frozen normally without package-specific
`--hidden-import` or `--add-data` options:

```shell
pyinstaller your_app.py
```

## Example

```python
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QLabel

from pyside6_modern_widgets import ModernWindow

app = QApplication([])
window = ModernWindow()
window.setWindowTitle("Modern window")

file_menu = window.menuBar().addMenu("&File")
exit_action = QAction("Exit", window)
exit_action.triggered.connect(window.close)
file_menu.addAction(exit_action)

window.setCentralWidget(QLabel("Hello"))
window.resize(800, 500)
window.show()
app.exec()
```

An existing top-level `QWidget` subclass can keep its direct layout when its
base class changes to `ModernWindow`. The standard `QWidget(parent, f)`
constructor shape and window flags are preserved:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from pyside6_modern_widgets import ModernWindow


class ToolWindow(ModernWindow):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Tool content"))
```

Use either a layout installed directly on `ModernWindow` or its optional
`menuBar()`, `addToolBar()`, `statusBar()`, and `setCentralWidget()` compatibility
APIs. The two layout models intentionally cannot be mixed in one window.

`ModernDialog` accepts ordinary Qt layouts directly and retains `exec()`,
`accept()`, `reject()`, and the standard dialog result codes:

```python
from PySide6.QtWidgets import QDialogButtonBox, QLabel, QVBoxLayout

from pyside6_modern_widgets import ModernDialog

dialog = ModernDialog(window)
dialog.setWindowTitle("Settings")
layout = QVBoxLayout(dialog)
layout.addWidget(QLabel("Dialog content"))
buttons = QDialogButtonBox(
    QDialogButtonBox.StandardButton.Ok
    | QDialogButtonBox.StandardButton.Cancel
)
buttons.accepted.connect(dialog.accept)
buttons.rejected.connect(dialog.reject)
layout.addWidget(buttons)
dialog.exec()
```

`ModernMessageBox` provides the common information, question, warning, and
critical flows while returning `QMessageBox`-compatible standard buttons:

```python
from pyside6_modern_widgets import ModernMessageBox

answer = ModernMessageBox.question(
    window,
    "Confirm",
    "Continue with this operation?",
    ModernMessageBox.StandardButton.Yes | ModernMessageBox.StandardButton.No,
    ModernMessageBox.StandardButton.No,
)
```

`ModernMenu` accepts the same common constructor forms as `QMenu` and works
with ordinary `QAction` instances, separators, checkable actions, and submenus:

```python
from PySide6.QtGui import QAction

from pyside6_modern_widgets import ModernMenu

menu = ModernMenu("Actions", window)
menu.addAction(QAction("Open", menu))
menu.addSeparator()
menu.addMenu("Recent")
```

## Themes

Widgets use a neutral light-gray standard theme through the process-wide theme
manager by default. A theme change also updates the application palette so
regular Qt content remains readable:

```python
from pyside6_modern_widgets import STANDARD_DARK_THEME, theme_manager

theme_manager().setTheme(STANDARD_DARK_THEME)
```

Use `theme_manager().setFollowsSystemTheme(True)` to select a built-in theme
from application palette changes. Pass `theme=STANDARD_LIGHT_THEME` or
`theme=STANDARD_DARK_THEME` to an individual widget for a local override;
`LIGHT_THEME` and `DARK_THEME` select the modern watercolor surfaces. Layout
metrics can be customized with `ModernMetrics` without modifying component
internals.
The Theme Style submenu in the upper-right window menu switches between the
standard colorless surface and the modern or classic watercolor palettes while
preserving the current light or dark mode and application accent color.

`TabView` uses the standard Qt argument order: `addTab(widget, text)` or
`addTab(widget, icon, text)`. The former reverse `(widget, text, icon)` order is
not supported.

The runnable navigation example includes interactive window, dialog, and message
box pages. A separate multi-tab example is also available in the
[`examples`](examples) directory.

`NavigationView` automatically uses an overlay sidebar when expanding it beside
the current page would compress the page below its minimum width. A small
hysteresis margin prevents repeated mode changes near that width. On return to
the side-by-side layout, it restores the expand/collapse intent last selected
with the sidebar toggle. Overlay mode starts with its sidebar collapsed.
Applications with a custom responsive policy can call
`setAutoSidebarOverlay(False)` and control the mode with `setSidebarOverlay()`.

`ModernWindow` intentionally remains based on `QWidget`, so it is suitable for
top-level primary and auxiliary windows. Its compatibility surface is limited to the common
`menuBar()`, `addToolBar()`, `statusBar()`, and `setCentralWidget()` methods; it does
not implement `QMainWindow` docking or state-management features.

The bundled window and navigation icons are provided by
[Icons8](https://icons8.com) and remain subject to the Icons8 license.
