# ModernPushButton

`ModernPushButton` subclasses `QPushButton` and replaces only its painting. All
native constructors, properties, signals, menu activation, keyboard shortcuts,
dialog default/auto-default behavior and auto-repeat remain Qt-owned.

```python
from pyside6_modern_widgets import ModernPushButton

save = ModernPushButton("&Save", parent)
save.setDefault(True)
save.clicked.connect(save_document)

toggle = ModernPushButton("Preview", parent, checkable=True)
toggle.toggled.connect(set_preview_visible)
```

Use `setTheme(theme)` for a local override and `setTheme(None)` to restore
ancestor/application inheritance. Checked and default buttons use the theme's
accent or the active system palette's `Accent` role. Ordinary surfaces, hover,
press, disabled text and borders follow the shared theme. Keyboard focus uses
an inset outline, with contrasting foreground on accented buttons. Custom
icons keep their original colors and Qt's normal/active/disabled and on/off modes.

## Fusion measurements

Measured with PySide6 6.8.3, Windows, Fusion, Microsoft YaHei UI 9 pt, at 125%
display scaling. All dimensions below are **logical pixels**, for the label
`Button` and a 16×16 icon. Both classes report the same measurements.

| Content / feature | sizeHint | minimumSizeHint | Content rectangle (x, y, w, h) |
| --- | --- | --- | --- |
| Text | 80×24 | 80×24 | 1, 1, 78, 22 |
| Icon and text | 80×24 | 80×24 | 1, 1, 78, 22 |
| Icon only | 28×24 | 28×24 | 1, 1, 26, 22 |
| Menu and text | 80×24 | 80×24 | 1, 1, 78, 22 |
| Flat / default and text | 80×24 | 80×24 | 1, 1, 78, 22 |
| Empty | 39×24 | 39×24 | 1, 1, 37, 22 |

The 80×24 button's Fusion focus rectangle is `(2, 3, 76, 18)`. The menu
indicator reserves 12 logical pixels; its visible glyph occupies Fusion's
6×6 indicator rectangle. The modern border is 1 logical pixel, with the shared
`control_radius` (4 by default). Text/icon layout, 4-pixel icon/text spacing,
mnemonics and icon DPR handling use Fusion's native label painter.

These values are observations, not fixed size hints: fonts, text and icon sizes
continue to affect sizing. Each button owns a Fusion style without changing the
application style. Layout and menu indicators mirror under RTL. QPushButton has
no orientation API; ordinary horizontal and vertical Qt layouts can contain it.
Do not multiply sizes by devicePixelRatio: Qt scales logical geometry itself.

The regression tests compare native/modern suggested sizes, minimum sizes,
content/focus rectangles and rendered icon bounds. They also exercise mouse
cancellation, Space/Enter, wheel non-activation, disabled behavior, signal order,
dialog defaults, menu selection and inherited themes. Native Windows rendering
is checked at 100%, 125%, 150% and 200% scaling.

Run `python examples/navigation_view_example.py` and select **Buttons** for the
interactive comparison, including RTL. Use **Settings** or the title-bar theme
button to switch appearance.
