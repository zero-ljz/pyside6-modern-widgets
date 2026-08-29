# pyside6-modern-widgets

Cross-platform desktop widgets for PySide6. The package provides frameless
window chrome, navigation, and tabs while retaining familiar Qt widget APIs.

- `ModernWindow`: a lightweight, frameless `QWidget` window with selected
  `QMainWindow`-compatible methods.
- `NavigationSidebar`: a collapsible navigation sidebar.
- `NavigationView`: a sidebar and synchronized page stack in one widget.
- `TabView`: a WinUI-inspired tab widget.

## Supported environment

Supports Windows, macOS, and Linux with Python 3.10-3.12, PySide6 6.8.3, and
the Fusion style. Window backgrounds, including the custom title bar, use the
same Qt-painted watercolor themes and behavior on every platform.

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

## Themes

Widgets follow the process-wide theme manager by default. A theme change also
updates the application palette so regular Qt content remains readable:

```python
from pyside6_modern_widgets import DARK_THEME, theme_manager

theme_manager().setTheme(DARK_THEME)
```

Use `theme_manager().setFollowsSystemTheme(True)` to select a built-in theme
from application palette changes. Pass `theme=LIGHT_THEME` or
`theme=DARK_THEME` to an individual widget for a local override. Layout metrics
can be customized with `ModernMetrics` without modifying component internals.
The Theme Style submenu in the upper-right window menu switches between the
modern and classic watercolor palettes while preserving the current light or
dark mode and application accent color.

`TabView` uses the standard Qt argument order: `addTab(widget, text)` or
`addTab(widget, icon, text)`. The former reverse `(widget, text, icon)` order is
not supported.

Runnable window/navigation and multi-tab examples are available in the
[`examples`](examples) directory.

`NavigationView` automatically collapses into an overlay sidebar at widths up
to `900px` and returns to the side-by-side layout at `1040px`. On return it
restores the expand/collapse intent last selected with the sidebar toggle.
Applications with a custom responsive policy can call
`setAutoSidebarOverlay(False)` and control the mode with `setSidebarOverlay()`.

`ModernWindow` intentionally remains based on `QWidget`, so it is suitable for both
primary and auxiliary windows. Its compatibility surface is limited to the common
`menuBar()`, `addToolBar()`, `statusBar()`, and `setCentralWidget()` methods; it does
not implement `QMainWindow` docking or state-management features.

The bundled window and navigation icons are provided by
[Icons8](https://icons8.com) and remain subject to the Icons8 license.
