# pyside6-modern-widgets

Focused Windows desktop widgets for PySide6. The package provides frameless
window chrome, navigation, tabs, and lightweight Windows visual effects while
retaining familiar Qt widget APIs.

- `ModernWindow`: a lightweight, frameless `QWidget` window with selected
  `QMainWindow`-compatible methods and Windows 11 effects.
- `NavigationSidebar`: a collapsible navigation sidebar.
- `NavigationView`: a sidebar and synchronized page stack in one widget.
- `TabView`: a WinUI-inspired tab widget.
- `WindowEffect`: a small Windows DWM effect wrapper.

## Supported environment

Supports Windows 10 and 11, Python 3.10-3.12, PySide6 6.8.3, and the Fusion
style. Built-in light and dark themes share the same layout and interaction
model.

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

`TabView` uses the standard Qt argument order: `addTab(widget, text)` or
`addTab(widget, icon, text)`. The former reverse `(widget, text, icon)` order is
not supported.

The native window effects target Windows. On unsupported Windows versions or
when transparency is disabled, the window automatically uses a painted fallback.

Runnable window/navigation and multi-tab examples are available in the
[`examples`](examples) directory.

`ModernWindow` intentionally remains based on `QWidget`, so it is suitable for both
primary and auxiliary windows. Its compatibility surface is limited to the common
`menuBar()`, `addToolBar()`, `statusBar()`, and `setCentralWidget()` methods; it does
not implement `QMainWindow` docking or state-management features.

The bundled window and navigation icons are provided by
[Icons8](https://icons8.com) and remain subject to the Icons8 license.
