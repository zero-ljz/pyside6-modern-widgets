# pyside6-modern-widgets

Modern Windows widgets for PySide6:

- `ModernWindow`: a lightweight, frameless `QWidget` window with selected
  `QMainWindow`-compatible methods and Windows 11 effects.
- `NavigationSidebar`: a collapsible navigation sidebar.
- `NavigationView`: a sidebar and synchronized page stack in one widget.
- `TabView`: a WinUI-inspired tab widget.
- `WindowEffect`: a small Windows DWM effect wrapper.

## Installation

```shell
pip install pyside6-modern-widgets
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

The native window effects target Windows. On unsupported Windows versions or
when transparency is disabled, the window automatically uses a painted fallback.

## Window effects

`ModernWindow` enables an automatic Windows backdrop by default and reapplies it
when the window is activated, maximized, restored, or moved between display
configurations. Applications can select a material without managing the native
window handle:

```python
from pyside6_modern_widgets import ModernWindow, ThemeMode, WindowMaterial

window = ModernWindow(
    material=WindowMaterial.ACRYLIC,
    theme=ThemeMode.LIGHT,
)
window.setWindowMaterial(WindowMaterial.MICA)
window.setWindowEffectsEnabled(False)
window.toggleThemeMode()
```

`ThemeMode` controls both the native backdrop and the colors of `ModernWindow`,
`NavigationSidebar`, `NavigationView`, and `TabView`. The title bar includes a
sun/moon button for switching between light and dark modes. Use `ThemeMode.AUTO`
to follow the Windows application theme.

`WindowEffect` remains available as a low-level API for other top-level windows.
Callers using it directly are responsible for the native handle and for
reapplying the effect when that handle or the window state changes.

## Qt style compatibility

Fusion is the reference style used for visual consistency. The widgets also
support the Qt styles commonly available on Windows (`windows11`,
`windowsvista`, and `Windows`) for layout and interaction, although small native
details such as standard icons can differ. The library does not change the
application's global style; applications remain free to select one with
`QApplication.setStyle()`.

Runnable window/navigation and multi-tab examples are available in the
[`examples`](examples) directory.

`ModernWindow` intentionally remains based on `QWidget`, so it is suitable for both
primary and auxiliary windows. Its compatibility surface is limited to the common
`menuBar()`, `addToolBar()`, `statusBar()`, and `setCentralWidget()` methods; it does
not implement `QMainWindow` docking or state-management features.

The bundled window and navigation icons are provided by
[Icons8](https://icons8.com) and remain subject to the Icons8 license.
