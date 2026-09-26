# pyside6-modern-widgets

Cross-platform desktop widgets for PySide6. The package provides frameless
window chrome, navigation, and tabs while retaining familiar Qt widget APIs.

- `ModernWindow`: a modern-chrome replacement for top-level `QWidget` windows
  with selected `QMainWindow`-compatible methods.
- `ModernDialog`: a frameless `QDialog` that preserves the standard dialog API.
- `ModernMessageBox`: a `QMessageBox` subclass with themed frameless chrome,
  native buttons, keyboard handling, and convenience methods.
- `ModernMenu`: a native `QMenu` with Windows 11 system acrylic (and an
  opaque fallback elsewhere) plus rounded outer and selected-item
  backgrounds.
- `ModernMenuBar`: a `QMenuBar` that creates `ModernMenu` drop-down menus.
- `ModernToolBar`: a `QToolBar` with modern controls and an accessible overflow
  button that opens a `ModernMenu` instead of Qt's default toolbar popup.
- `ModernComboBox`: a modern `QComboBox` with rounded surfaces,
  a `ModernMenu`-style acrylic popup, and native Qt selection and editing behavior.
- `ModernSwitch`: an animated switch with system accent colors and native
  checkbox interaction, sized to sit alongside combo boxes and line edits.
- `ModernSegmentedControl`: compact exclusive choices with themed selected,
  hover, and disabled states and native Qt button signals.
- `ModernTabWidget`: compact themed tabs for fixed pages, preserving the native
  `QTabWidget` API without document-tab add, close, or move behaviors.
- `ModernFlyout`: an anchored popup for arbitrary widgets, with automatic screen
  edge placement, scrollable content, and light dismiss.
- `ModernNotification` / `NotificationManager`: custom desktop or in-window
  notifications with actions, progress, bounded queues, and non-activating delivery.
- `EdgeDockController`: optional screen-edge snapping and hover-to-restore
  auto-hide for floating top-level widgets.
- `NavigationSidebar`: a collapsible navigation sidebar.
- `NavigationView`: a sidebar and synchronized page stack in one widget.
- `TabView`: a WinUI-inspired document tab view with add, close, and move behaviors.

## Supported environment

Supports Windows, macOS, and Linux with Python 3.10-3.12, PySide6 6.8.3, and
the Fusion style. Window backgrounds and title content use the same Qt-painted,
wallpaper-colored theme behavior on every platform.

On Windows, the custom chrome retains native activation, moving, resizing,
minimize/maximize/restore transitions, Aero Snap, shadows, and the system menu.
Windows 11 additionally provides DWM-rounded corners and Snap Layouts from the
custom maximize button; Windows 10 uses an opaque square-corner surface. On
platforms without equivalent frameless-window APIs, Qt supplies system moving,
resizing, and a menu with the available window commands.

On macOS, `ModernWindow` keeps the native `NSWindow` frame and traffic-light
controls, with themed content extended into the transparent title bar. The
custom Windows-style controls and window icon are hidden, and title-bar double
clicks follow the user's macOS preference. `ModernMessageBox` uses a standard
native title bar for dragging and preserves Qt's macOS content margins, while
keeping themed Qt message content and buttons.

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

## Internationalization

The widgets use Qt translation catalogs for text owned by the library, including
window controls, navigation and tab tooltips, notification accessibility text,
and the portable system menu. English is the source language and Simplified
Chinese is bundled. Text supplied by the application, such as page names,
notification content and action labels, remains under application control.

Load and install the library translator after constructing `QApplication`. The
application keeps control of the active locale and translator lifetime:

```python
from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication
from pyside6_modern_widgets import load_translator

app = QApplication([])
widgets_translator = load_translator(QLocale.system(), app)
if widgets_translator is not None:
    app.installTranslator(widgets_translator)
```

Installing or removing a translator at runtime updates existing widgets through
Qt's `LanguageChange` event. Qt's own standard button text is provided by the
separate `qtbase` catalogs in `QLibraryInfo.TranslationsPath`; applications that
need those translations should install the matching Qt translator as well.

After changing source strings, update and compile the bundled catalog with:

```shell
pyside6-lupdate -extensions py src/pyside6_modern_widgets \
  -source-language en_US -target-language zh_CN \
  -ts src/pyside6_modern_widgets/translations/pyside6_modern_widgets_zh_CN.ts
pyside6-lrelease src/pyside6_modern_widgets/translations/pyside6_modern_widgets_zh_CN.ts \
  -qm src/pyside6_modern_widgets/translations/pyside6_modern_widgets_zh_CN.qm
```

## Screen-edge docking

Attach `EdgeDockController` to a floating top-level `QWidget` or `ModernWindow`.
Only empty space in the chosen drag widget starts a drag; child controls keep
their mouse and keyboard behavior. A dedicated drag strip also works:

```python
from pyside6_modern_widgets import DockConfig, DockSide, EdgeDockController

dock = EdgeDockController(window, drag_widget=drag_strip, auto_hide=True)
dock.setAutoHide(False)  # Keep snapping, without hiding.
dock.setEnabled(False)  # Restore a collapsed window and suspend the behavior.
dock.setEnabled(True)
dock.dock(DockSide.RIGHT)  # Explicitly dock a visible window.
dock.expand()  # Also use this when reopening from a launcher or shortcut.
dock.dismiss()  # Hide both the window and its handle, without closing the window.
dock.setDragWidget(new_drag_strip)  # Rebind after replacing your window content.
```

The default handle is a thin strip. Pass a `QIcon` for a square icon handle; its
size is `handle_icon_size + 2 * handle_padding` in Qt logical pixels. The icon
keeps its aspect ratio and remains upright on all four edges. Handles are limited
to the available work area on small displays. For example:

```python
from PySide6.QtGui import QIcon
from pyside6_modern_widgets import DockConfig, DockRestoreTrigger, EdgeDockController

dock = EdgeDockController(
    window,
    DockConfig(
        handle_icon=QIcon(":/app/notes.svg"),
        handle_icon_size=24,
        handle_padding=6,
        handle_tooltip="Restore notes",
        restore_trigger=DockRestoreTrigger.CLICK,
    ),
    drag_widget=drag_strip,
)
dock.setHandleIcon(QIcon(":/app/unread.svg"))  # Also works while collapsed.
dock.setHandleIconSize(32)
dock.setHandlePadding(8)
dock.setHandleToolTip("Restore unread notes")
dock.setRestoreTrigger("hover")  # Hover or left click; "click" requires left click.
dock.setHandleIcon(None)  # Return to the configured thin strip.
```

Use this configuration when creating the controller, rather than attaching a
second controller to the same window. A null `QIcon` (including an unavailable
image) uses the thin-strip fallback. `handle_width` and `handle_length` apply only
to the strip; colors apply to both backgrounds. Runtime handle updates keep the
docking state and do not reopen the target. Changing the trigger takes effect on
the next entry or click. Matching getters (`handleIcon()`, `handleIconSize()`,
`handlePadding()`, `handleToolTip()`, `restoreTrigger()`) expose current settings.

`DockConfig` controls the snap distance, margin, handle dimensions and colors, animation
duration, hide delay, and enabled `sides`. Defaults enable left, right, and top;
include `DockSide.BOTTOM` to enable the bottom edge. Coordinates and sizes are
Qt logical pixels, including on mixed-DPI displays. Distances use the window's
frame and its screen's available work area; dragging can cross display boundaries.
Releasing a window near or beyond an enabled edge snaps it back to that edge,
even if it extends far outside the work area. At corners the greatest overflow
wins; inside the work area the nearest enabled edge wins. Configuration order
breaks ties. Releasing beyond a disabled edge brings the window back into the
work area without enabling auto-hide. No clamping occurs during a drag, so a
window can still move onto a second display.

Auto-hide waits while the pointer is inside, a mouse button is down, an animation
is running, or a popup/modal dialog is open. Hovering or clicking the gray edge
handle restores the window by default; `DockRestoreTrigger.CLICK` disables hover
restoration and requires a left click. Its default color is RGB (150, 150, 150), with
RGB (200, 200, 200) on hover; override `handle_color` / `handle_hover_color` in
`DockConfig` to customize it. External `show()` removes the handle. Hiding a visible
window, accepting a close, minimizing, maximizing, or entering full-screen clears
docking state. A close request on a collapsed window expands it before its
`closeEvent()` runs: if closing is cancelled, the window remains visible and docked.
Use `dock.dismiss()` to hide a window and remove its handle from any attached state.
Calling `window.hide()` on an already collapsed window does **not** dismiss the
handle: the window is already hidden, so Qt sends no additional hide event.
Screen geometry changes reposition docked windows and handles. Maximized and
full-screen windows do not dock. The target owns the controller and handle;
`detach()` permanently removes the behavior, disconnects external notifications,
and restores a collapsed window. Repeated detaches are safe; subsequent commands
on that controller do nothing. Only one controller may be attached to each target,
including while disabled; detach it before attaching a replacement.
If the drag widget is destroyed, dragging stops while docking and auto-hide remain
available. Bind a replacement with `setDragWidget(widget)`, or pass `None` to use
the target's empty space.
Inspect `dockSide()` / `isCollapsed()` or connect `dockSideChanged` /
`collapsedChanged` to observe state. Notifications are emitted after geometry,
visibility, and timers have been updated; slots may disable, dismiss, or detach
the controller immediately.

Native title-bar dragging remains controlled by the platform; use the dedicated
drag widget for automatic snapping, or call `snap()` after an external move.
The drag widget delegates to `ModernWindow.startSystemMove()` (or the Qt window
handle for ordinary widgets), preserving the existing native mixed-DPI handling.
Snapping is deferred until system dragging ends, including when the OS consumes
the mouse release. Manual movement is used only when system movement is unavailable.
This behavior requires a desktop platform that permits global window placement
and pointer queries; Wayland compositors may restrict those operations.
The controller does not change application quit policy or the target's window flags.

Run `python examples/edge_dock_example.py` for a floating tool with a separate
controls window. Try dismiss/restore, replacing the drag strip, and detaching and
reattaching docking without losing the ability to reopen the tool.
The navigation example also provides an **Edge docking** page with a launch button.
Both support English and Simplified Chinese; pass `--language en` or
`--language zh_CN` to override the system language at startup.

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

The control uses WinUI-style translucent fills for each theme and interaction state:
the default is white at about 70% opacity in light mode and 6% in dark mode.
The default editor shares the control surface; text, arrows and borders remain crisp.
Explicit surface palette brushes and custom line edits keep their own painting.
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

The closed control follows the current native Qt combo-box height. Popup rows
retain the roomier modern menu spacing.

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

The capsule stays 32 by 16 logical pixels regardless of font or native style;
Qt still scales it for the display DPI. The minimum widget height is 20 logical
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

## Modern segmented control

`ModernSegmentedControl(labels, parent=None, *, theme=None)` creates a compact
row of exclusive `QPushButton` choices. Its public `buttons` list keeps the
label order; `group` is an exclusive `QButtonGroup` whose button IDs are the
zero-based label indices. The first button starts checked (an empty list has
no selection). Use normal Qt button signals and methods:

```python
from pyside6_modern_widgets import ModernSegmentedControl

segments = ModernSegmentedControl(["All", "Open", "Closed"])
segments.group.idClicked.connect(lambda index: print("Selected:", index))
segments.buttons[2].setChecked(True)
```

The control uses 1-pixel layout margins, no spacing, a 26-pixel minimum
button content height, and a maximum-width/fixed-height size policy. Buttons
remain keyboard accessible and can be disabled individually. Colors use the
current theme's surface, border, text, and tab-state tokens for light/dark,
hover, checked, and disabled appearances. The control follows its nearest
themed ancestor or the global theme; `setTheme(DARK_THEME)` overrides locally
and `setTheme(None)` restores inheritance. Open **Tab widget** in the navigation
example to try enabled and disabled segments alongside fixed-section tabs.

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

## Notifications

`NotificationManager` delivers custom notification cards without taking keyboard
focus. Keep one manager for the application; it owns the cards, their timers,
and their per-screen stacks. Its parent controls lifetime and theme inheritance.
Desktop cards stay visible when that parent is minimized or hidden.

```python
from pyside6_modern_widgets import NotificationManager

notifications = NotificationManager(window)
notifications.notify("Export complete", "Your report is ready.", kind="success")

job = notifications.notify(
    "Downloading",
    "Starting…",
    notification_id="download-1",
    duration=0,
    progress=0,
    actions={"cancel": "Cancel"},
)
notifications.updateNotification(job, message="Downloading… 65%", progress=65)
notifications.updateNotification(
    job,
    title="Download complete",
    message="Your file is ready.",
    kind="success",
    progress=None,
    actions={"open": "Open file"},
    duration=5000,
)
notifications.actionTriggered.connect(
    lambda notification_id, action_id: print(notification_id, action_id)
)
```

Kinds accept `"info"`, `"success"`, `"warning"`, `"error"`, or `NotificationKind`.
Titles and messages are plain text, including text containing markup. Titles
elide with the full text available in a tooltip; long bodies and action lists
scroll while the close button stays visible. Progress accepts `0..100`, `-1` for
busy, or `None` to hide it. An optional `icon=QIcon(...)` replaces the severity icon.
Cards include accessible names, descriptions, action labels, and progress values.

| Constructor option | Default / behavior |
| --- | --- |
| `position` | `NotificationPosition.BOTTOM_RIGHT`; all four screen corners supported, also as strings such as `"top-left"`. |
| `max_visible` | 3 per screen; available height can reduce this further. |
| `max_queued` | 100 across the manager; overflow dismisses the oldest queued card. |
| `width`, `margin`, `spacing` | 360, 16, 12 logical pixels. Cards fit the available area and are at most 360 pixels tall. |
| `default_duration` | 5000 milliseconds. `notify(duration=0)` makes a persistent card. |
| `desktop` | Automatic desktop delivery on Windows/macOS/X11; in-window delivery on Wayland. `False` explicitly selects in-window delivery. |
| `theme`, `metrics` | Inherited theme and `ModernMetrics()`; set `animation_duration=0` to disable entry and stack movement animations. |

Delivery is FIFO within each screen, with the oldest visible card nearest the
selected corner. Screen placement excludes taskbars/docks through Qt's available
geometry. `setScreen(screen)` changes the default destination;
`notify(screen=screen)` pins one notification to that display. Otherwise the
manager follows its parent window's screen, then the primary screen. Screen
removal migrates affected cards to the default destination. Geometry and DPI
changes reflow the stacks. Use `setPosition()` and `setMaxVisible()` for runtime
changes. Independently created managers do not coordinate their stacks.

Expiry starts when a queued card becomes visible, pauses while hovered or while
an in-window action has keyboard focus, and resumes with the remaining time.
`pause(id)` / `resume(id)` add an independent manual pause. `setEnabled(False)`
hides cards and pauses delivery/expiry while retaining a bounded queue; enabling
resumes them. In-window cards also pause while their host is hidden or minimized.

`notify(notification_id=existing_id, ...)` replaces that notification's contents
and restarts its timeout without changing FIFO order. `updateNotification()`
changes only supplied fields and preserves time unless `duration` is provided;
it returns `False` for an unknown ID. `actions={}` clears the actions, and an
explicit `progress=None` clears progress. Progress completion does not implicitly
close a persistent notification: supply a new duration when the task completes.

`notification(id)` returns the owned `ModernNotification` while registered;
`notificationIds()`, `visibleIds()`, and `queuedIds()` return snapshots.
`dismiss(id)` closes one card; `clear()` closes all registered and queued cards.
Dismissed cards are deleted with `deleteLater()` and must not be reused. Use the
manager for delivery, geometry, and visibility instead of reparenting or hiding
its cards. Deleting the manager deletes its desktop windows too; notification
windows do not prevent normal application exit. A parent window merely closing
without being deleted does not destroy a manager—call `clear()` if desired.

| Signal | Meaning |
| --- | --- |
| `notificationShown(id)` | First delivery of a card, after it becomes visible. Resuming a hidden card does not emit again. |
| `notificationClosed(id, reason)` | Card removed; standard reasons are `dismissed`, `expired`, `action`, `cleared`, `overflow`, or `destroyed`. |
| `actionTriggered(id, action_id)` | An action was clicked. Standard actions close the card after emitting this signal. |
| `notificationActivated(id)` | The body was clicked; no application action or automatic dismissal is performed. |
| `countChanged(visible, queued)` | Total counts changed across all screens. |
| `deliveryFailed(id, message)` | An asynchronous `post()` could not be delivered. |

The returned card supports `setTitle()`, `setMessage()`, `setKind()`, `setIcon()`,
`setProgress()`, and `setTheme()`. Add persistent actions with
`card.addActionButton("retry", "Retry", close_on_trigger=False)`; it returns a
normal `QPushButton`. `removeActionButton()` and `clearActionButtons()` manage
these buttons without replacing QWidget's native QAction API. A card-level
`setTheme()` overrides the manager; `None` resumes inheritance. Global and host
theme changes update existing cards, including native acrylic on Windows 11.

Create and operate managers on the QApplication GUI thread. Worker threads may
call `post(title, message, ...)`, which validates and copies the data, returns
an ID immediately, and queues delivery on the GUI thread. It accepts `kind`,
`duration`, `actions`, `progress`, and `notification_id`, and uses the manager's
default screen. Reposting the same ID updates it. Posts not yet delivered are
not part of `notificationIds()` or `clear()`; stop producers before clearing
when shutting down a job.

Custom desktop notifications exist only while the application runs. They do not
enter the OS notification center or automatically follow its do-not-disturb
settings. Desktop action buttons accept mouse input without activating the
notification window; use in-window delivery for Tab/Space/Enter/Escape keyboard
interaction. Wayland requires a host QWidget and uses the in-window fallback;
requesting `desktop=True` there raises `ValueError`. Desktop positioning/stacking
on other platforms remains subject to window-manager policy.

Run `python examples/navigation_view_example.py` and open **Notifications** for
severity samples, corner/screen selection, queue overflow into waiting delivery,
persistent cards, long messages, simulated download progress, and delivery after
minimizing. `python tests/notification_smoke.py` checks native focus and stacking;
`python tests/windows_appearance_smoke.py` also verifies Windows 11 acrylic.

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

### Modern toolbar

`ModernToolBar` accepts `(parent)` or `(title, parent)` like `QToolBar`. It keeps
the standard action, orientation, docking, icon-size and tool-button APIs. For
title-bar tools:

```python
from PySide6.QtCore import QSize, Qt
from pyside6_modern_widgets import ModernToolBar

toolbar = ModernToolBar(window)
toolbar.setMovable(False)
toolbar.setFloatable(False)
toolbar.setIconSize(QSize(18, 18))
toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
toolbar.addAction(open_action)  # Reuse the QAction from your menu.
toolbar.addAction(save_action)
window.titleBar.addCustomWidget(toolbar, align="left")
```

`window.addToolBar("Tools")` also creates a `ModernToolBar`. Existing toolbar
instances passed to `addToolBar()` keep their type.

Button sizes, spacing, menu-arrow hit regions and overflow thresholds follow
the native `QToolBar` style, including horizontal, vertical and right-to-left
layouts. Modern drawing changes colors and rounded state backgrounds without
adding padding or enlarging the extension button. Overflow actions retain their shortcuts,
enabled/checked states, submenus and `actionTriggered` connections. Resizing or
changing actions updates the popup; leading, trailing and repeated separators
are removed. Windows 11 uses the same acrylic surface as `ModernMenu`, with an
opaque fallback on other platforms.

Colors follow the containing modern window or global theme; use
`toolbar.setTheme(custom_theme)` for an override and `setTheme(None)` to restore
inheritance. `overflowButton()` exposes the button for tooltip/localization
changes; `overflowMenu()` exposes the managed popup. Do not add independent
actions to that popup: its contents come from hidden toolbar actions.
`addWidget()` controls remain owned by the toolbar and are not duplicated in
the overflow. Use a `QWidgetAction` subclass implementing `createWidget()` when
a control needs separate toolbar and popup instances; Qt can request additional
instances for its internal layout.

Run the navigation example's **Toolbar** page to vary the available width,
toggle text labels and right-to-left layout, and try the overflow actions.

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
        content = QLabel("Tool content")
        layout.addWidget(content)
        self.setDragRegion(content)
```

`setDragRegion(widget)` makes left-button drags on a non-interactive content
surface use the platform's system window movement, including monitor and DPI
transitions. Pass `False` as the second argument to unregister it. Subclasses
with custom hit testing can call `startSystemMove(global_position)` directly;
it uses native movement when available and a client-side fallback elsewhere.
On Windows, tool windows receive the same mixed-DPI size protection as regular
modern windows without acquiring taskbar or Alt+Tab behavior.

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
