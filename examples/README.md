# Examples

Install the package in editable mode from the repository root:

```shell
python -m pip install -e .
```

Run the window and navigation example:

```shell
python examples/navigation_view_example.py
```

The navigation, tab, and edge-dock examples support English and Simplified Chinese. English is the source
language; when the system locale is `zh_CN`, each example installs Qt's standard
catalog, the component library catalog, and its own `examples_zh_CN` catalog
before constructing the window. Library-owned and example-owned text therefore
remain in separate translation domains.

In the navigation example, select **Edge docking** and click **Open edge-docking
demo**. Repeated launches reuse the demo and restore its floating tool. Closing
the demo leaves navigation open; closing navigation also closes the demo and its
restore handle.

Navigation and standalone edge docking also accept an explicit language override:

```shell
python examples/navigation_view_example.py --language zh_CN
python examples/navigation_view_example.py --language en
python examples/edge_dock_example.py --language zh_CN
```

Language is selected at startup. The launched demo shares the navigation example's
language, including buttons, instructions, docking sides, and status messages.

Run `python examples/edge_dock_example.py` for the standalone screen-edge docking
example. It opens a controls window and a floating tool. Drag the tool's labeled
strip between displays or near an edge, toggle auto-hide, and move away to show
the restore handle. The text field retains normal selection. This example enables
all four edges, including the optional bottom edge.

The controls window remains available while the tool is hidden:

- **Handle appearance** switches between the thin strip and application/settings
  icons, including while collapsed. **Icon size** changes the icon bounds, and
  **Handle interaction** selects hover-or-click, click-only, or drag-or-click.
- Select **Drag or click** to move handles across edges and screens. Drag
  the collapsed handle to another edge/display and release to remain folded, or
  release inside a screen to expand the tool. Click without dragging to restore;
  press Escape while dragging to cancel. Switch directly to either other mode.
- **Collapse tool** explicitly folds a docked tool, including with auto-hide off.
- **Save dock position** keeps the current screen, edge and fractional position in
  memory; **Restore dock position** reapplies it, including while folded. Applications
  can persist the same `DockPlacement` value to their own settings.
- **Hide tool and handle** uses `dismiss()`, including when the tool is already
  collapsed; **Show / restore tool** uses `expand()`. Closing the tool also leaves
  the controls available to reopen it.
- **Replace drag strip** binds a new widget with `setDragWidget()` and deletes the
  old strip without replacing the controller.
- **Enable docking** temporarily disables or re-enables the existing controller.
- **Detach docking** restores a collapsed tool and removes docking permanently;
  **Attach docking** creates a new controller for the same tool.

The status line observes the committed docking side and handle visibility. Close
the controls window to exit the example.

After changing example text, update and compile its catalog with:

```shell
pyside6-lupdate -extensions py examples/navigation_view_example.py \
  examples/tab_view_example.py examples/edge_dock_example.py \
  -source-language en_US -target-language zh_CN \
  -ts examples/translations/examples_zh_CN.ts
pyside6-lrelease examples/translations/examples_zh_CN.ts \
  -qm examples/translations/examples_zh_CN.qm
```

It includes interactive `ModernDialog`, `ModernMessageBox`, and side-by-side
`ModernMenu`/native `QMenu` examples, plus **Combo box**, **Switch**, **Flyout**,
**Notifications**, **Toolbar**, **Tab widget**, and **Edge docking** pages.

The **Toolbar** page compares native `QToolBar` and `ModernToolBar` side by side,
using matching actions and icon sizes. The shared width slider, text-beside-icons
option, and right-to-left toggle update both toolbars. Open each overflow to try
a checkable action, disabled action and native/modern submenu. The status line
identifies which toolbar triggered an action.

The **Tab widget** page demonstrates `ModernTabWidget` with two fixed sections.
Select a tab to switch content; unlike the standalone `TabView` example, these
tabs cannot be added, closed, or dragged. It also shows `ModernSegmentedControl`:
choose a segment to update the status text, compare its disabled state, and use
the title-bar theme button to see its light/dark colors change.

The **Notifications** page demonstrates desktop and in-window delivery, four
severity levels, all four corners, screen selection, and a queue of eight updates.
Try a persistent notification, a long scrollable message, or a simulated download
with a Cancel action and completion update. Hover pauses expiry. The pause switch
suspends delivery without discarding cards, and Clear all cancels displayed and
pending notifications. The download keeps a `NotificationHandle` and updates
only its progress/message until completion; actions use `NotificationAction`.
Native desktop
notifications stay visible after minimizing the main window; Wayland defaults to
window delivery. Use the title-bar theme button to see visible cards update immediately.

The **Flyout** page opens quick settings at each side of a button. Try text input,
Tab navigation, nested combo popups, and switching appearance inside the panel.
Click outside or press Escape to dismiss; values persist on reopening. Move the
window near a screen edge to test placement fallback, or open the long panel to
test scrolling. Escape closes a nested combo popup before closing the panel.

The **Combo box** page compares `ModernComboBox` and native `QComboBox` side by side, including icons,
separators, placeholders, editing, disabled controls, long lists and right-to-left
layout. Switch the title-bar theme button and try the mouse, arrow keys, typing,
Enter and Escape. Modern popups use `ModernMenu`'s acrylic styling
on Windows 11, with an opaque fallback elsewhere. Editable controls and popups
have four square corners; non-editable combos remain rounded. The status line
displays Qt's `activated` signal.

The **Switch** page compares `ModernSwitch` with `QLineEdit`, `QComboBox`, and
`ModernComboBox` without fixed heights. Try the title-bar theme button, system
accent colors, clicking the label, Tab/Space input, disabled states, and
right-to-left layout. The switch focus outline appears for keyboard interaction
and hides on mouse clicks.

The example places a `ModernMenuBar` in the title bar's left custom-widget area,
keeps the centered title and window icon visible, and offers a theme button on
the right. Narrow the window to try menu overflow and the navigation sidebar's
automatic overlay mode.
Open Settings to switch between System, Light, and Dark at runtime and toggle
wallpaper colors independently. Existing pages, menus, and dialogs update without
recreating the window. The tab example's text also inherits the active palette.

Run the multi-tab `ModernWindow` example without a menu bar:

```shell
python examples/tab_view_example.py
```

The tab example supports adding, closing (including middle-click), selecting, and dragging
tabs. `TabView` also provides `Ctrl+T`, `Ctrl+W`, `Ctrl+Tab`, and `Ctrl+Shift+Tab`
shortcuts.
