# Examples

Install the package in editable mode from the repository root:

```shell
python -m pip install -e .
```

Run the modern combo box example:

```shell
python examples/combo_box_example.py
```

It compares `ModernComboBox` and native `QComboBox` side by side, including icons,
separators, placeholders, editing, disabled controls, long lists and right-to-left
layout. Switch System/Light/Dark appearance and try the mouse, arrow keys, typing,
Enter and Escape. The ordinary modern popup uses `ModernMenu`'s acrylic styling
on Windows 11, with an opaque fallback elsewhere. Editable popups use a solid
theme surface with two square corners facing the input. The status line
displays Qt's `activated` signal.

Run the window and navigation example. It includes interactive `ModernDialog`,
`ModernMessageBox`, and side-by-side `ModernMenu`/native `QMenu` examples:

```shell
python examples/navigation_view_example.py
```

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
