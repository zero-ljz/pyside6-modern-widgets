"""Shared visual tokens and runtime theme management."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette
from PySide6.QtWidgets import QApplication


class WatercolorStyle(Enum):
    """Built-in window surface style families."""

    STANDARD = "standard"
    MODERN = "modern"
    ORIGINAL = "original"


@dataclass(frozen=True, slots=True)
class ModernTheme:
    """Colors and typography used by all modern widgets."""

    name: str
    text: str
    text_muted: str
    text_disabled: str
    surface: str
    border: str
    control_hover: str
    control_pressed: str
    danger: str
    navigation_background: str
    navigation_content: str
    scrollbar: str
    scrollbar_hover: str
    tab_bar: str
    tab_selected: str
    tab_hover: str
    tab_divider: str
    focus: str
    watercolor_base: str
    watercolor_spots: tuple[tuple[str, float, float, float], ...]
    watercolor_style: WatercolorStyle = WatercolorStyle.MODERN


@dataclass(frozen=True, slots=True)
class ModernMetrics:
    """Shared logical-pixel metrics used by all modern widgets."""

    corner_radius: int = 10
    control_radius: int = 4
    title_bar_height: int = 34
    title_button_size: int = 30
    navigation_item_height: int = 36
    navigation_collapsed_width: int = 48
    navigation_expanded_width: int = 224
    tab_height: int = 38
    tab_min_width: int = 80
    tab_max_width: int = 200
    animation_duration: int = 250


LIGHT_THEME = ModernTheme(
    name="light",
    text="#000000",
    text_muted="#454545",
    text_disabled="#8A8A8A",
    surface="#FFFFFF",
    border="#E5E5E5",
    control_hover="#0D000000",
    control_pressed="#26000000",
    danger="#C42B1C",
    navigation_background="transparent",
    navigation_content="#F0F0F0",
    scrollbar="#CCCCCC",
    scrollbar_hover="#999999",
    tab_bar="#F3F3F3",
    tab_selected="#FFFFFF",
    tab_hover="#EAEAEA",
    tab_divider="#D1D1D1",
    focus="#707070",
    watercolor_base="#F7FAFC",
    watercolor_spots=(
        ("#667DD3FC", 0.08, 0.08, 0.52),
        ("#55F6A6A1", 0.92, 0.18, 0.58),
        ("#557ED6C4", 0.22, 0.92, 0.48),
    ),
)

DARK_THEME = ModernTheme(
    name="dark",
    text="#FFFFFF",
    text_muted="#D6D6D6",
    text_disabled="#777777",
    surface="#2B2B2B",
    border="#454545",
    control_hover="#14FFFFFF",
    control_pressed="#29FFFFFF",
    danger="#FF99A4",
    navigation_background="transparent",
    navigation_content="#202020",
    scrollbar="#666666",
    scrollbar_hover="#888888",
    tab_bar="#202020",
    tab_selected="#2B2B2B",
    tab_hover="#333333",
    tab_divider="#484848",
    focus="#A0A0A0",
    watercolor_base="#151A1F",
    watercolor_spots=(
        ("#503B82F6", 0.08, 0.08, 0.52),
        ("#45F472B6", 0.92, 0.18, 0.58),
        ("#4034D399", 0.22, 0.92, 0.48),
    ),
)

STANDARD_LIGHT_THEME = replace(
    LIGHT_THEME,
    watercolor_base="#F7F7F7",
    watercolor_spots=(),
    watercolor_style=WatercolorStyle.STANDARD,
)

STANDARD_DARK_THEME = replace(
    DARK_THEME,
    watercolor_base=DARK_THEME.surface,
    watercolor_spots=(),
    watercolor_style=WatercolorStyle.STANDARD,
)

ORIGINAL_LIGHT_THEME = replace(
    LIGHT_THEME,
    watercolor_base="#FFFCF5",
    watercolor_spots=(
        ("#78FFB7B2", 0.1, 0.1, 0.5),
        ("#78C7CEEA", 0.9, 0.9, 0.6),
        ("#78E2F0CB", 0.2, 0.9, 0.4),
    ),
    watercolor_style=WatercolorStyle.ORIGINAL,
)

ORIGINAL_DARK_THEME = replace(
    DARK_THEME,
    watercolor_base="#202020",
    watercolor_spots=(
        ("#503B3151", 0.1, 0.1, 0.5),
        ("#50314759", 0.9, 0.9, 0.6),
        ("#50314F45", 0.2, 0.9, 0.4),
    ),
    watercolor_style=WatercolorStyle.ORIGINAL,
)

DEFAULT_METRICS = ModernMetrics()


def theme_for_palette(palette: QPalette) -> ModernTheme:
    """Choose the built-in theme matching an application palette."""
    return (
        STANDARD_DARK_THEME
        if palette.color(QPalette.ColorRole.Window).lightness() < 128
        else STANDARD_LIGHT_THEME
    )


def theme_with_watercolor_style(
    theme: ModernTheme,
    style: WatercolorStyle,
) -> ModernTheme:
    """Return ``theme`` with the selected window surface style applied."""
    if theme.watercolor_style is style:
        return theme
    is_dark = QColor(theme.surface).lightness() < 128
    reference = {
        (False, WatercolorStyle.STANDARD): STANDARD_LIGHT_THEME,
        (True, WatercolorStyle.STANDARD): STANDARD_DARK_THEME,
        (False, WatercolorStyle.MODERN): LIGHT_THEME,
        (True, WatercolorStyle.MODERN): DARK_THEME,
        (False, WatercolorStyle.ORIGINAL): ORIGINAL_LIGHT_THEME,
        (True, WatercolorStyle.ORIGINAL): ORIGINAL_DARK_THEME,
    }[is_dark, style]
    return replace(
        theme,
        watercolor_base=reference.watercolor_base,
        watercolor_spots=reference.watercolor_spots,
        watercolor_style=style,
    )


def palette_for_theme(theme: ModernTheme, base: QPalette | None = None) -> QPalette:
    """Return a Qt palette carrying the theme's semantic colors."""
    palette = QPalette(base or QApplication.palette())
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        for role in (
            QPalette.ColorRole.Text,
            QPalette.ColorRole.WindowText,
            QPalette.ColorRole.ButtonText,
            QPalette.ColorRole.ToolTipText,
        ):
            palette.setColor(group, role, QColor(theme.text))
        palette.setColor(group, QPalette.ColorRole.Window, QColor(theme.surface))
        palette.setColor(group, QPalette.ColorRole.Base, QColor(theme.surface))
        palette.setColor(group, QPalette.ColorRole.Button, QColor(theme.surface))
    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            role,
            QColor(theme.text_disabled),
        )
    return palette


def tinted_icon(icon: QIcon, color: str, size: int = 48) -> QIcon:
    """Tint a monochrome icon while preserving its alpha channel."""
    pixmap = icon.pixmap(size, size)
    if pixmap.isNull():
        return icon
    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return QIcon(pixmap)


class ThemeManager(QObject):
    """Publish one runtime theme to widgets that do not use a local override."""

    themeChanged = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._theme = STANDARD_LIGHT_THEME
        self._follows_system = False
        self._application: QApplication | None = None

    def theme(self) -> ModernTheme:
        return self._theme

    def setTheme(self, theme: ModernTheme) -> None:
        self._follows_system = False
        application = QApplication.instance()
        if isinstance(application, QApplication):
            application.setPalette(palette_for_theme(theme, application.palette()))
        self._set_theme(theme)

    def setWatercolorStyle(self, style: WatercolorStyle) -> None:
        """Change the window surface without replacing the application palette."""
        self._set_theme(theme_with_watercolor_style(self._theme, style))

    def followsSystemTheme(self) -> bool:
        return self._follows_system

    def setFollowsSystemTheme(self, enabled: bool) -> None:
        self._follows_system = enabled
        application = QApplication.instance()
        application = application if isinstance(application, QApplication) else None
        if application is not self._application:
            if self._application is not None:
                self._application.removeEventFilter(self)
            self._application = application
            if application is not None:
                application.installEventFilter(self)
        if enabled and application is not None:
            self._set_theme(
                theme_with_watercolor_style(
                    theme_for_palette(application.palette()),
                    self._theme.watercolor_style,
                )
            )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self._follows_system and event.type() == QEvent.Type.ApplicationPaletteChange:
            application = QApplication.instance()
            if isinstance(application, QApplication):
                self._set_theme(
                    theme_with_watercolor_style(
                        theme_for_palette(application.palette()),
                        self._theme.watercolor_style,
                    )
                )
        return super().eventFilter(watched, event)

    def _set_theme(self, theme: ModernTheme) -> None:
        if theme == self._theme:
            return
        self._theme = theme
        self.themeChanged.emit(theme)


_THEME_MANAGER = ThemeManager()


def theme_manager() -> ThemeManager:
    """Return the process-wide theme manager."""
    return _THEME_MANAGER
