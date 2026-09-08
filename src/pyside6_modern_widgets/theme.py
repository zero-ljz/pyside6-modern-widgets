"""Shared visual tokens and runtime theme management."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QEvent, QFileSystemWatcher, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette
from PySide6.QtWidgets import QApplication

from ._wallpaper import desktop_wallpaper_path, wallpaper_colors, wallpaper_signature


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


def theme_from_wallpaper(
    theme: ModernTheme,
    path: str | os.PathLike[str] | None = None,
) -> ModernTheme:
    """Return a modern surface colored from the current desktop wallpaper."""
    is_dark = QColor(theme.surface).lightness() < 128
    colors = wallpaper_colors(path)
    if not colors:
        fallback = DARK_THEME if is_dark else LIGHT_THEME
        return replace(
            theme,
            focus=fallback.focus,
            watercolor_base=fallback.watercolor_base,
            watercolor_spots=fallback.watercolor_spots,
        )
    alpha_values = (0x50, 0x48, 0x40) if is_dark else (0x66, 0x58, 0x50)
    spots = tuple(
        (
            _wallpaper_spot_color(color, is_dark, alpha_values[index]),
            ((0.08, 0.08, 0.52), (0.92, 0.18, 0.58), (0.22, 0.92, 0.48))[index],
        )
        for index, color in enumerate(colors[:3])
    )
    average = QColor(
        sum(color.red() for color in colors) // len(colors),
        sum(color.green() for color in colors) // len(colors),
        sum(color.blue() for color in colors) // len(colors),
    )
    base = _blend_colors(QColor("#15191D" if is_dark else "#FAFAFA"), average, 0.1)
    focus = _wallpaper_focus_color(colors[0], is_dark)
    return replace(
        theme,
        focus=focus.name(QColor.NameFormat.HexRgb).upper(),
        watercolor_base=base.name(QColor.NameFormat.HexRgb).upper(),
        watercolor_spots=tuple((color, *geometry) for color, geometry in spots),
    )


def _wallpaper_spot_color(color: QColor, is_dark: bool, alpha: int) -> str:
    hue = color.hslHueF()
    saturation = color.hslSaturationF()
    lightness = color.lightnessF()
    saturation = min(0.78, max(0.24, saturation)) if saturation >= 0.08 else 0.0
    lightness = min(0.62, max(0.34, lightness)) if is_dark else min(0.78, max(0.52, lightness))
    adjusted = QColor.fromHslF(max(0.0, hue), saturation, lightness, alpha / 255)
    return adjusted.name(QColor.NameFormat.HexArgb).upper()


def _wallpaper_focus_color(color: QColor, is_dark: bool) -> QColor:
    hue = color.hslHueF()
    saturation = color.hslSaturationF()
    saturation = min(0.82, max(0.36, saturation)) if saturation >= 0.08 else 0.0
    return QColor.fromHslF(max(0.0, hue), saturation, 0.68 if is_dark else 0.4)


def _blend_colors(background: QColor, foreground: QColor, amount: float) -> QColor:
    inverse = 1.0 - amount
    return QColor(
        round(background.red() * inverse + foreground.red() * amount),
        round(background.green() * inverse + foreground.green() * amount),
        round(background.blue() * inverse + foreground.blue() * amount),
    )


DEFAULT_METRICS = ModernMetrics()


def theme_for_palette(palette: QPalette) -> ModernTheme:
    """Choose the built-in theme matching an application palette."""
    return DARK_THEME if palette.color(QPalette.ColorRole.Window).lightness() < 128 else LIGHT_THEME


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

    WALLPAPER_POLL_INTERVAL_MS = 1000
    WALLPAPER_REFRESH_DELAY_MS = 350

    themeChanged = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._theme = LIGHT_THEME
        self._follows_system = False
        self._application: QApplication | None = None
        self._wallpaper_path: Path | None = None
        self._wallpaper_signature: tuple[str, int, int] | None = None
        self._wallpaper_watcher: QFileSystemWatcher | None = None
        self._wallpaper_poll_timer: QTimer | None = None
        self._wallpaper_refresh_timer: QTimer | None = None

    def theme(self) -> ModernTheme:
        self._ensure_wallpaper_monitor()
        return self._theme

    def setTheme(self, theme: ModernTheme) -> None:
        self._follows_system = False
        application = QApplication.instance()
        if isinstance(application, QApplication):
            application.setPalette(palette_for_theme(theme, application.palette()))
        self._set_theme(theme)

    def refreshWallpaperTheme(self) -> None:
        """Re-read the desktop wallpaper and publish its colors."""
        path = desktop_wallpaper_path()
        self._wallpaper_path = path
        self._wallpaper_signature = wallpaper_signature(path)
        self._sync_wallpaper_watch(path)
        self._set_theme(theme_from_wallpaper(self._theme, path))

    def followsSystemTheme(self) -> bool:
        return self._follows_system

    def setFollowsSystemTheme(self, enabled: bool) -> None:
        self._ensure_wallpaper_monitor()
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
                theme_from_wallpaper(
                    theme_for_palette(application.palette()),
                    self._wallpaper_path,
                )
            )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self._follows_system and event.type() == QEvent.Type.ApplicationPaletteChange:
            application = QApplication.instance()
            if isinstance(application, QApplication):
                self._set_theme(
                    theme_from_wallpaper(
                        theme_for_palette(application.palette()),
                        self._wallpaper_path,
                    )
                )
        return super().eventFilter(watched, event)

    def _ensure_wallpaper_monitor(self) -> None:
        application = QApplication.instance()
        if not isinstance(application, QApplication) or self._wallpaper_poll_timer is not None:
            return
        self._wallpaper_watcher = QFileSystemWatcher(self)
        self._wallpaper_watcher.fileChanged.connect(self._queue_wallpaper_refresh)

        self._wallpaper_poll_timer = QTimer(self)
        self._wallpaper_poll_timer.setInterval(self.WALLPAPER_POLL_INTERVAL_MS)
        self._wallpaper_poll_timer.setTimerType(Qt.TimerType.VeryCoarseTimer)
        self._wallpaper_poll_timer.timeout.connect(self._poll_wallpaper_update)

        self._wallpaper_refresh_timer = QTimer(self)
        self._wallpaper_refresh_timer.setSingleShot(True)
        self._wallpaper_refresh_timer.setInterval(self.WALLPAPER_REFRESH_DELAY_MS)
        self._wallpaper_refresh_timer.timeout.connect(self._refresh_changed_wallpaper)

        self._wallpaper_path = desktop_wallpaper_path()
        self._wallpaper_signature = wallpaper_signature(self._wallpaper_path)
        self._sync_wallpaper_watch(self._wallpaper_path)
        self._set_theme(theme_from_wallpaper(self._theme, self._wallpaper_path))
        self._wallpaper_poll_timer.start()

    def _queue_wallpaper_refresh(self, _path: str) -> None:
        if self._wallpaper_refresh_timer is not None:
            self._wallpaper_refresh_timer.start()

    def _refresh_changed_wallpaper(self) -> None:
        self._wallpaper_signature = None
        self._poll_wallpaper_update()

    def _poll_wallpaper_update(self) -> None:
        path = desktop_wallpaper_path()
        signature = wallpaper_signature(path)
        self._sync_wallpaper_watch(path)
        if signature == self._wallpaper_signature:
            return
        self._wallpaper_path = path
        self._wallpaper_signature = signature
        self._set_theme(theme_from_wallpaper(self._theme, path))

    def _sync_wallpaper_watch(self, path: Path | None) -> None:
        if self._wallpaper_watcher is None:
            return
        desired = str(path) if path is not None else None
        watched = self._wallpaper_watcher.files()
        obsolete = [entry for entry in watched if entry != desired]
        if obsolete:
            self._wallpaper_watcher.removePaths(obsolete)
        if desired is not None and desired not in watched:
            self._wallpaper_watcher.addPath(desired)

    def _set_theme(self, theme: ModernTheme) -> None:
        if theme == self._theme:
            return
        self._theme = theme
        self.themeChanged.emit(theme)


_THEME_MANAGER = ThemeManager()


def theme_manager() -> ThemeManager:
    """Return the process-wide theme manager."""
    return _THEME_MANAGER
