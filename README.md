# pyside6-modern-widgets

Cross-platform desktop widgets for PySide6. The package provides frameless
window chrome, navigation, and tabs while retaining familiar Qt widget APIs.

- `ModernWindow`: a frameless replacement for top-level `QWidget` windows with
  selected `QMainWindow`-compatible methods.
- `ModernDialog`: a frameless `QDialog` that preserves the standard dialog API.
- `ModernMessageBox`: a `QMessageBox` subclass with themed frameless chrome,
  native buttons, keyboard handling, and convenience methods.
- `ModernMenu`: a native `QMenu` with Windows 11 system acrylic (and an
  opaque fallback elsewhere) plus rounded outer and selected-item
  backgrounds.
- `ModernMenuBar`: a `QMenuBar` that creates `ModernMenu` drop-down menus.
- `ModernComboBox`: a modern `QComboBox` with rounded surfaces,
  a `ModernMenu`-style acrylic popup, and native Qt selection and editing behavior.
- `ModernSwitch`: an animated switch with system accent colors and native
  checkbox interaction, sized to sit alongside combo boxes and line edits.
- `ModernFlyout`: an anchored popup for arbitrary widgets, with automatic screen
  edge placement, scrollable content, and light dismiss.
- `NavigationSidebar`: a collapsible navigation sidebar.
- `NavigationView`: a sidebar and synchronized page stack in one widget.
- `TabView`: a WinUI-inspired tab widget.

## Supported environment

Supports Windows, macOS, and Linux with Python 3.10-3.12, PySide6 6.8.3, and
the Fusion style. Window backgrounds, including the custom title bar, use the
same Qt-painted, wallpaper-colored theme behavior on every platform.

On Windows, the custom chrome retains native activation, moving, resizing,
minimize/maximize/restore transitions, Aero Snap, shadows, and the system menu.
Windows 11 additionally provides DWM-rounded corners and Snap Layouts from the
custom maximize button; Windows 10 uses an opaque square-corner surface. On
platforms without equivalent frameless-window APIs, Qt supplies system moving,
resizing, and a menu with the available window commands.

## Installation

```shell
pip install pyside6-modern-widgets
```

## Upgrading to 0.5.0

Version 0.5.0 adds modern dialogs, message boxes, menus, and menu bars, plus
independent title-bar text/icon visibility and centered title text. It also
improves Windows maximize/restore behavior and content-aware navigation layout.
See the [changelog](CHANGELOG.md#050---2026-09-11) for the full release notes.

When upgrading from 0.4.x, remove uses of `WatercolorStyle`,
`theme_with_watercolor_style`, `ORIGINAL_LIGHT_THEME`, and `ORIGINAL_DARK_THEME`.
These exports and the title-bar Theme Style submenu have been removed. Widgets
now follow desktop-wallpaper colors by default; `LIGHT_THEME`, `DARK_THEME`,
`ModernTheme`, and widget-level `setTheme()` remain available for local overrides.

Automatic navigation overlay thresholds now depend on the current page's
minimum width instead of fixed window widths. Use `setAutoSidebarOverlay(False)`
and `setSidebarOverlay()` if your application needs explicit control.

## PyInstaller

The installed package automatically registers its PyInstaller hook. Applications
using these widgets can be frozen normally without package-specific
`--hidden-import` or `--add-data` options:

```shell
pyinstaller your_app.py
```

## Modern combo box

Replace `QComboBox` with `ModernComboBox` and keep the usual Qt APIs and signals:

```python
from pyside6_modern_widgets import ModernComboBox

combo = ModernComboBox(parent)
combo.addItem("Windows 11", userData="win11")
combo.addItem("Linux", userData="linux")
combo.setPlaceholderText("Choose a platform")
combo.setCurrentIndex(-1)
combo.currentIndexChanged.connect(lambda index: print(index, combo.currentData()))

# Optional: native editing, completion, validation and insertion policies.
combo.setEditable(True)
```

The control uses a full focus border with Qt Fusion's focus timing and system
highlight-derived color: keyboard focus for non-editable combos, and input focus
for editable combos. Its popup shares `ModernMenu`'s
surface, subtle outline, row spacing and selection background, including Windows
11 system acrylic and an opaque fallback elsewhere. It retains Qt's popup
container, keyboard/mouse/wheel input, models, separators, icons and signals.
The default item delegate keeps rows transparent under application style sheets,
so they do not cover the acrylic surface.
`setView()` and `setItemDelegate()` remain
available; custom views and delegates control their own painting. The initial
Qt list receives the modern defaults once; opening does not overwrite later
view styles, frames, background fills or palettes. An opaque custom view can
cover the acrylic surface beneath it. Explicit `setPalette()` roles take
precedence over theme defaults, and `setPalette(QPalette())` restores them.
`setFrame(False)` uses native frameless rendering. Popup placement, closing
and scrolling follow Qt's Fusion behavior, including Qt's platform-dependent
handling of `maxVisibleItems` for non-editable combos.

Editable modern combos open directly: Qt's screenshot-based slide animation
cannot capture the system acrylic backdrop. The application's animation
preference is restored immediately after opening.
Editable controls and their popups have four square corners, with Windows 11
acrylic on the popup. Non-editable controls and popups retain their rounded corners.
Qt still determines popup placement.
Editable default-list items use the same font-aware minimum row height as
ordinary modern combo items, with an extra 8 logical pixels of padding on each
side and 2 pixels of spacing above and below the list. Closed-control spacing
and caller-supplied views remain unchanged.

It inherits its containing modern widget's theme, or the global theme when used
on its own. Use `setTheme(DARK_THEME)` for a local override and `setTheme(None)` to
restore inheritance. The optional `metrics` argument uses `ModernMetrics`.
Qt paints the control and popup foreground; Windows supplies the acrylic backdrop.

Run `python examples/navigation_view_example.py` and open **Combo box** for a
native/modern comparison with editable, disabled, placeholder, icon, long-list
and right-to-left examples.

## Modern switch

`ModernSwitch` accepts the same text/parent constructor forms as `QCheckBox` and
uses its standard `setChecked()`, `isChecked()`, `toggled(bool)`, and `clicked(bool)`
APIs. Click the track or label, or use Tab and Space from the keyboard.

```python
from pyside6_modern_widgets import ModernSwitch

switch = ModernSwitch("Enable notifications")
switch.setChecked(True)
switch.toggled.connect(lambda enabled: print("Notifications:", enabled))
```

The capsule stays 36 by 18 logical pixels regardless of font or native style;
Qt still scales it for the display DPI. The minimum widget height is 22 logical
pixels, growing to fit larger labels without enlarging the track. Layouts remain
free to resize the widget. Labels, keyboard focus, hover/pressed states, disabled states,
and right-to-left layouts are supported. The focus outline appears during keyboard
interaction and hides on mouse clicks. For a switch without visible text, use
`setAccessibleName()` to describe its purpose to assistive tools.

The enabled track reads the current Qt `QPalette.Accent` color, including system
accent updates. It inherits its containing modern widget's theme or the global
theme; `setTheme(DARK_THEME)` overrides it locally and `setTheme(None)` restores
inheritance. Explicit theme `accent` / `on_accent` tokens override the track/thumb
colors. Optional `metrics=ModernMetrics(...)` controls animation duration.

Run `python examples/navigation_view_example.py` and open **Switch** to compare
the default heights with native form controls and try System/Light/Dark appearance
and enabled/disabled switches.

## Modern flyout

`ModernFlyout` hosts any `QWidget`, including forms, switches, and combo boxes.
Opening is non-blocking; click outside or press Escape to close. Values remain
in the content when the panel is reopened.

```python
from PySide6.QtWidgets import QLineEdit, QPushButton, QVBoxLayout, QWidget
from pyside6_modern_widgets import ModernFlyout

button = QPushButton("Quick settings", window)
flyout = ModernFlyout(window)
content = QWidget()
layout = QVBoxLayout(content)
layout.addWidget(QLineEdit("Workspace name"))
done = QPushButton("Done")
done.clicked.connect(flyout.close)
layout.addWidget(done)
flyout.setContentWidget(content)
button.clicked.connect(lambda: flyout.popup(button))
```

Use `popup(anchor, placement="bottom", gap=8)` with a visible anchor. Placement
accepts `"bottom"`, `"top"`, `"left"`, `"right"`, or the corresponding
`FlyoutPlacement` enum. Top/bottom align to the anchor's leading edge, including
right-to-left layouts; left/right center vertically. If there is insufficient
room, the opposite side is tried first, followed by the other sides. Placement
stays within the anchor screen's available area with an 8-logical-pixel margin.
Oversized content gets scrollbars. Leave the panel's minimum size unconstrained
to allow it to fit small screens; set content size hints or minimum sizes instead.

Moving or resizing the anchor or its ancestors updates placement. Hiding,
destroying, or reparenting the anchor dismisses the panel. Keyboard focus enters
the content; Qt restores the previous focus on dismissal. Nested menus and combo
popups keep their normal behavior: Escape dismisses the inner popup first.
`opened` and `closed` signal visibility transitions. `close()` hides the panel
without deleting it unless Qt's `WA_DeleteOnClose` is explicitly enabled.

`setContentWidget()` takes ownership and deletes the previous content, like
`QScrollArea.setWidget()`. `contentWidget()` returns it; `takeContentWidget()`
detaches it and transfers ownership back to the caller. Install the content's
layout before passing it to the panel. The panel supplies 12 pixels of padding
around its scroll area. Transparent content preserves the backdrop; deliberately
opaque content can cover it.

The panel follows its anchor's theme, or its parent/global theme before the first
opening. `setTheme(DARK_THEME)` overrides it and `setTheme(None)` restores
inheritance. Windows 11 uses the same native acrylic surface as `ModernMenu`;
other platforms use an opaque rounded surface. Optional `metrics=ModernMetrics(...)`
controls the outer corner radius.

Run `python examples/navigation_view_example.py` and open **Flyout** to try all
four placements, editable settings, nested combo popups, live appearance changes,
and a long scrollable panel.

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

`ModernWindow.menuBar()` returns a `ModernMenuBar`, so menus created from a
title or icon automatically use `ModernMenu`, including nested submenus.
`ModernMenuBar` itself provides a transparent background and rounded selection
highlight, including when constructed manually. It follows its containing
modern window's theme, or the global theme when used on its own.
When space is limited, its overflow button also opens a `ModernMenu` with the
same rounded surface and selection styling as the regular drop-down menus.

To place a manually created menu bar in the title bar's left control area:

```python
from pyside6_modern_widgets import ModernMenuBar

menu_bar = ModernMenuBar(window)
menu_bar.setNativeMenuBar(False)
menu_bar.addMenu("&File").addAction("Open")
window.titleBar.addCustomWidget(menu_bar, align="left")
window.setTitleVisible(False)
```

`setTitleVisible()` controls only title text. `setIconVisible()` independently
controls the title bar icon. Both default to `True` and preserve the actual
window title and icon used by the operating system. Updating either while it is
hidden does not show it again. `isTitleVisible()` and `isIconVisible()` return
the configured visibility, even when the window itself is hidden. An empty
window icon is not drawn, regardless of the icon visibility setting.

The icon stays at the far left whenever it is visible. Title text is left-aligned
by default, between the icon and left custom widgets such as menus. Use
`setTitleAlignment("center")` to center only the text on the window, with menus
following the icon, or `setTitleAlignment("left")` to restore the default order.
`titleAlignment()` returns the selected mode. In narrow windows, the centered
text stays within the space between the left controls and the window buttons.
Blank space remains available for dragging. Right custom widgets appear before
the window buttons. All six methods are also available on `window.titleBar`.

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
    QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
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

Message text, details, checkboxes, button ownership, default and escape buttons,
return values, and completion signals are handled by `QMessageBox` itself.
The component customizes its palette, background, and title bar. It uses Qt's
widget message box on every platform so this appearance remains available.

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

The process-wide manager defaults to **System mode with wallpaper colors enabled**.
Select a mode after creating `QApplication`, before creating windows. Use the Fusion
style for consistent palette support across platforms; the library does not change
the application's style. Existing widgets update when the theme changes.

```python
from PySide6.QtWidgets import QApplication
from pyside6_modern_widgets import ModernWindow, ThemeMode, theme_manager

app = QApplication([])
app.setStyle("Fusion")
manager = theme_manager()
manager.setMode(ThemeMode.SYSTEM)  # Or ThemeMode.LIGHT / ThemeMode.DARK.
manager.setWallpaperEnabled(False)  # Optional: use the exact base theme colors.

window = ModernWindow()
window.show()
app.exec()
```

| API | Contract |
| --- | --- |
| `setMode(ThemeMode.SYSTEM / LIGHT / DARK)` | Select the user's preference. Accepts a `ThemeMode` enum. |
| `mode()` | Return the selected preference, even when System currently resolves to Dark. |
| `isDark()` | Return whether the resolved mode is Dark. |
| `theme()` | Return the effective immutable `ModernTheme` tokens. |
| `setThemes(light=..., dark=...)` | Replace the two base themes without changing mode or wallpaper policy. |
| `setWallpaperEnabled(bool)` / `wallpaperEnabled()` | Control wallpaper accents independently of mode. |
| `refreshWallpaperTheme()` | Request an asynchronous refresh; no effect while wallpaper is disabled. |
| `modeChanged(mode)` | Emitted only when the selected preference changes. |
| `themeChanged(theme)` | Emitted only when effective tokens change, after the application palette is applied. |
| `wallpaperEnabledChanged(enabled)` | Emitted when the wallpaper policy changes. |

System mode reads `QApplication.styleHints().colorScheme()` and listens for
`colorSchemeChanged`; it never infers the OS setting from the palette it has
written. An unknown system scheme falls back to Light. Fixed Light/Dark modes
ignore system changes visually but remember them for the next switch to System.
An OS appearance change can emit `themeChanged` while `mode()` remains `SYSTEM`.
Repeatedly setting the same effective state does not emit duplicate signals.

Use the manager on the QApplication GUI thread. Configuration before application
creation is supported; it attaches on the first subsequent `theme()` or setter
call (including when a globally themed widget is constructed). The library owns
the application's semantic palette roles once attached. It does not install a
global style sheet or store preferences automatically.

### Custom colors and wallpaper

Customize a pair of themes using semantic tokens, not per-widget color literals:

```python
from dataclasses import replace
from pyside6_modern_widgets import DARK_THEME, LIGHT_THEME, ThemeMode, theme_manager

manager = theme_manager()
manager.setWallpaperEnabled(False)
manager.setThemes(
    light=replace(LIGHT_THEME, accent="#0067C0", on_accent="#FFFFFF", focus="#0067C0"),
    dark=replace(DARK_THEME, accent="#60CDFF", on_accent="#003047", focus="#60CDFF"),
)
manager.setMode(ThemeMode.SYSTEM)
```

Supply a light-colored theme in `light` and a dark-colored theme in `dark`;
theme names are labels and do not control mode selection. `accent` and
`on_accent` default to `None`: Qt's native Accent, Highlight, HighlightedText, and
Link roles remain inherited, so the system accent is preserved across light/dark
switches. Explicit strings override the selection background/text pair; restore
`None` to resume inheritance. To read the currently resolved system accent, use
`QApplication.palette().color(QPalette.ColorRole.Accent)` (or `Highlight` for
selection backgrounds). Wallpaper colors do not override these roles. `surface_alternate`,
`tooltip_surface`, and `link_visited` cover additional Qt palette roles.

Enabling wallpaper colors allows the manager to derive `focus`, `watercolor_base`,
and `watercolor_spots` from the wallpaper, leaving other base tokens intact.
Disabling immediately restores the selected base theme, stops monitoring, and
discards pending results. Re-enabling can use cached colors while requesting a
fresh sample. If no wallpaper is available, the configured base theme is used.
Sampling always resolves against the latest mode and base themes.

Wallpaper discovery, metadata checks, and sampling run off the GUI thread. A file
watcher and a one-second metadata poll detect changes; only changed images are
resampled. Repeated refresh requests are coalesced. Transient query errors retain
the current colors until a later successful refresh.

Inactive windows use a solid background (`#F3F3F3` for light themes, the surface
color for dark themes). Activation restores the wallpaper effect with a reversible
250 ms linear fade. Layout metrics remain independently configurable through
`ModernMetrics`.
Title text and menu bars use a 50%-alpha foreground in Qt's `Inactive` palette
group. Qt selects the group automatically; activation does not rewrite styles
or change layout. Title-bar window and button icons read the same palette group
when painted, preserving their original colors and icon modes. Button backgrounds,
hover/pressed behavior, and disabled rendering remain handled by Qt's style.
Ordinary page content retains its normal inactive contrast.

Windows 11 menu acrylic follows the owner theme, including changes while a menu
is open. Very light native acrylic tints are limited to lightness 240 so a pure
white theme surface does not wash out the backdrop. This leaves the Qt surface
palette and opaque fallback unchanged.

### Local overrides and application pages

`ModernWindow`, `ModernDialog`, `ModernMessageBox`, `NavigationView`,
`NavigationSidebar`, and `TabView` share this contract:

```python
window.setTheme(DARK_THEME)  # Fix this component and its internal chrome.
window.setTheme(None)  # Resume following the global manager.
```

The constructor's `theme=` argument has the same semantics. Overrides stay fixed
across global mode and wallpaper changes. Setting a window theme does not
recursively override independently themed library widgets placed inside it.
`ModernMenu` inherits its owner's Qt palette (including submenus); `ModernMenuBar`
uses the nearest themed ancestor, or the global theme when standalone.

Ordinary Qt controls inherit the application or parent palette, including disabled
text, placeholders, selection colors, tooltips, links, and alternating surfaces.
Explicit widget palettes and hardcoded QSS colors can override that inheritance.
The public `palette_for_theme(theme, base=None)` helper creates a matching palette
without changing application state. For custom QSS or painting, read `theme()`
initially and subscribe to `themeChanged`:

```python
from PySide6.QtWidgets import QLabel
from pyside6_modern_widgets import theme_manager


class StatusLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__("Ready", parent)
        self.applyTheme(theme_manager().theme())
        theme_manager().themeChanged.connect(self.applyTheme)

    def applyTheme(self, theme):
        self.setStyleSheet(f"color: {theme.text_muted};")
```

Monochrome library icons are recolored by their components. Application-owned
icons and custom artwork should be refreshed by the application when needed.

### Saving the user's preference

Persist the selected mode, not the currently resolved light/dark appearance:

```python
from PySide6.QtCore import QSettings
from pyside6_modern_widgets import ThemeMode, theme_manager

settings = QSettings("Example", "MyApp")
manager = theme_manager()
saved_mode = settings.value("appearance/mode", "system", type=str)
try:
    mode = ThemeMode(saved_mode)
except ValueError:
    mode = ThemeMode.SYSTEM
manager.setMode(mode)
manager.modeChanged.connect(lambda mode: settings.setValue("appearance/mode", mode.value))
```

The previous manager-level `setTheme()`, `setFollowsSystemTheme()`, and
`followsSystemTheme()` APIs are removed. Use `setMode()` and `setThemes()`;
widget-level `setTheme()` remains the local-override API.

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
