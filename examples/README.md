# Examples

Install the package in editable mode from the repository root:

```shell
python -m pip install -e .
```

Run the window and navigation example:

```shell
python examples/navigation_view_example.py
```

Both examples support English and Simplified Chinese. English is the source
language; when the system locale is `zh_CN`, each example installs Qt's standard
catalog, the component library catalog, and its own `examples_zh_CN` catalog
before constructing the window. Library-owned and example-owned text therefore
remain in separate translation domains.

After changing example text, update and compile its catalog with:

```shell
pyside6-lupdate -extensions py examples/navigation_view_example.py \
  examples/tab_view_example.py -source-language en_US -target-language zh_CN \
  -ts examples/translations/examples_zh_CN.ts
pyside6-lrelease examples/translations/examples_zh_CN.ts \
  -qm examples/translations/examples_zh_CN.qm
```

It includes interactive `ModernDialog`, `ModernMessageBox`, and side-by-side
`ModernMenu`/native `QMenu` examples, plus **Combo box**, **Switch**, **Flyout**, and
**Notifications** and **Toolbar** pages.

The **Toolbar** page compares native `QToolBar` and `ModernToolBar` side by side,
using matching actions and icon sizes. The shared width slider, text-beside-icons
option, and right-to-left toggle update both toolbars. Open each overflow to try
a checkable action, disabled action and native/modern submenu. Appearance buttons
on the page switch between System, Light, and Dark; the status line identifies
which toolbar triggered an action.

The **Notifications** page demonstrates desktop and in-window delivery, four
severity levels, all four corners, screen selection, and a queue of eight updates.
Try a persistent notification, a long scrollable message, or a simulated download
with a Cancel action and completion update. Hover pauses expiry. The pause switch
suspends delivery, and Clear all removes visible and queued cards. Native desktop
notifications stay visible after minimizing the main window; Wayland defaults to
window delivery. Appearance controls update visible cards immediately.

The **Flyout** page opens quick settings at each side of a button. Try text input,
Tab navigation, nested combo popups, and switching appearance inside the panel.
Click outside or press Escape to dismiss; values persist on reopening. Move the
window near a screen edge to test placement fallback, or open the long panel to
test scrolling. Escape closes a nested combo popup before closing the panel.

The **Combo box** page compares `ModernComboBox` and native `QComboBox` side by side, including icons,
separators, placeholders, editing, disabled controls, long lists and right-to-left
layout. Switch System/Light/Dark appearance and try the mouse, arrow keys, typing,
Enter and Escape. Modern popups use `ModernMenu`'s acrylic styling
on Windows 11, with an opaque fallback elsewhere. Editable controls and popups
have four square corners; non-editable combos remain rounded. The status line
displays Qt's `activated` signal.

The **Switch** page compares `ModernSwitch` with `QLineEdit`, `QComboBox`, and
`ModernComboBox` without fixed heights. Try System/Light/Dark appearance, system
accent colors, clicking the label, Tab/Space input, disabled states, and
right-to-left layout. The switch focus outline appears for keyboard interaction
and hides on mouse clicks. Both control pages include appearance buttons.

The example places a `ModernMenuBar` in the title bar's left custom-widget area
and hides the title text while keeping the window icon visible. Narrow the
window to try menu overflow and the navigation sidebar's automatic overlay mode.
The source also configures centered title alignment; use `setTitleVisible(True)`
to display the centered text alongside the menus.
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
