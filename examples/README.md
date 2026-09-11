# Examples

Install the package in editable mode from the repository root:

```shell
python -m pip install -e .
```

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

Run the multi-tab `ModernWindow` example without a menu bar:

```shell
python examples/tab_view_example.py
```

The tab example supports adding, closing (including middle-click), selecting, and dragging
tabs. `TabView` also provides `Ctrl+T`, `Ctrl+W`, `Ctrl+Tab`, and `Ctrl+Shift+Tab`
shortcuts.
