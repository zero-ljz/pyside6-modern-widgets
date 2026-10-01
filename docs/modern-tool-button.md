# ModernToolButton

`ModernToolButton` subclasses `QToolButton`. It paints rounded surfaces and state
colors while retaining Fusion's sizes, hit regions, label layout and arrow
positions. Directional and menu arrows use outlined, round-ended chevrons,
matching the other modern controls. Qt owns mouse, keyboard, wheel, shortcuts,
action synchronization, auto-repeat and popup timing. No additional keyboard
shortcuts are introduced.

```python
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolButton
from pyside6_modern_widgets import ModernMenu, ModernToolButton

button = ModernToolButton(parent)
action = QAction(icon, "&Open", button)
action.triggered.connect(open_document)
button.setDefaultAction(action)
button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

menu = ModernMenu(button)
menu.addAction("Recent documents")
button.setMenu(menu)
button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
```

All five `toolButtonStyle` values, four directional arrows, `setAutoRaise()`,
checkable actions and all three popup modes retain native behavior:

- `DelayedPopup`: a short click runs the action; holding opens the menu.
- `MenuButtonPopup`: the main region runs the action; the separate arrow opens
  the menu. Both regions and their hit testing mirror in RTL.
- `InstantPopup`: pressing opens the menu instead of running the default action.

`setTheme(theme)` overrides the inherited theme; `setTheme(None)` restores it.
Checked buttons use the theme accent or the active system palette's `Accent`.
Hover, pressed, keyboard focus and disabled states follow the shared theme.
Unchecked auto-raise buttons have no idle surface. Icons retain their colors,
native active/disabled variants and checked on/off states. Only the display
palette is adjusted, leaving action properties and the widget palette intact.

The component calls its painter directly so an unrelated ancestor stylesheet
cannot divert arrow-button drawing to Qt's Windows fallback. It does not
replace the `QToolButton` instances created internally by `ModernToolBar`.

## Measured Fusion geometry

PySide6 6.8.3 on Windows, Microsoft YaHei UI 9 pt, label `Button`, icon 16×16,
125% display scaling. Dimensions are **logical pixels** and both classes report
the same suggested and minimum sizes:

| Content / mode | sizeHint and minimumSizeHint | Main region | Menu region |
| --- | --- | --- | --- |
| Icon only / FollowStyle default | 24×23 | 24×23 | — |
| Text only | 55×23 | 55×23 | — |
| Text beside icon | 75×23 | 75×23 | — |
| Text under icon | 55×43 | 55×43 | — |
| Directional arrow | 24×23 | 24×23 | — |
| Icon, MenuButtonPopup | 36×23 | 24×23 | 12×23 |
| Icon, DelayedPopup / InstantPopup | 24×23 | 24×23 | Chevron in native corner region |

These are measurements, not fixed dimensions. Fonts, icons, action priority,
toolbar icon size and text determine the native size hints. Text beside/below
icons provides horizontal/vertical content arrangement; tool buttons can also
be placed in either toolbar orientation without adding an orientation API.

The border is 1 logical pixel and uses `ModernMetrics.control_radius` (4 by
default). The focus outline sits inside the main region, including under RTL.
Qt handles device scaling; callers should not multiply sizes by DPR.

Tests compare native suggested/minimum sizes, subcontrol hit regions, visible
icon bounds and modern directional arrows at actual DPR 1, 1.25, 1.5 and 2. Native
input/action/popup comparisons, inherited themes, state rendering and parent
stylesheet compatibility are covered separately.

Run `python examples/navigation_view_example.py` and select **Tool buttons**.
The **Styles and states**, **Arrows** and **Menus** tabs include native/modern
pairs, an RTL toggle and action feedback. **Arrows** shows all four directions
in normal, checked and disabled states. The example supports English and
Simplified Chinese.
