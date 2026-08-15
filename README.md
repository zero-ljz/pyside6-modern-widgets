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

`ModernWindow` intentionally remains based on `QWidget`, so it is suitable for both
primary and auxiliary windows. Its compatibility surface is limited to the common
`menuBar()`, `addToolBar()`, `statusBar()`, and `setCentralWidget()` methods; it does
not implement `QMainWindow` docking or state-management features.

The bundled window and navigation icons are provided by
[Icons8](https://icons8.com) and remain subject to the Icons8 license.
