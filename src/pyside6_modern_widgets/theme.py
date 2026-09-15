"""Shared visual tokens and runtime theme management."""

from __future__ import annotations

import os
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from ._wallpaper import (
    WallpaperSignature,
    desktop_wallpaper_path,
    wallpaper_colors,
    wallpaper_signature,
)


def inherited_theme(widget: QWidget) -> ModernTheme:
    """Find the nearest ancestor theme, falling back to the application theme."""
    ancestor = widget.parentWidget()
    while ancestor is not None:
        get_theme = getattr(ancestor, "theme", None)
        if callable(get_theme):
            theme = get_theme()
            if isinstance(theme, ModernTheme):
                return theme
        ancestor = ancestor.parentWidget()
    return theme_manager().theme()


@dataclass(frozen=True, slots=True)
class ModernTheme:
    """Colors and typography used by all modern widgets."""

    name: str
    text: str
    text_muted: str
    text_disabled: str
    surface: str
    surface_alternate: str
    tooltip_surface: str
    accent: str | None
    on_accent: str | None
    link_visited: str
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
    surface_alternate="#F5F5F5",
    tooltip_surface="#FFFFFF",
    accent=None,
    on_accent=None,
    link_visited="#7030A0",
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
    surface_alternate="#323232",
    tooltip_surface="#323232",
    accent=None,
    on_accent=None,
    link_visited="#CF9FFF",
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
    return _theme_from_colors(theme, wallpaper_colors(path))


def _theme_from_colors(theme: ModernTheme, colors: tuple[QColor, ...]) -> ModernTheme:
    is_dark = QColor(theme.surface).lightness() < 128
    if not colors:
        return theme
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


def palette_for_theme(theme: ModernTheme, base: QPalette | None = None) -> QPalette:
    """Return a Qt palette carrying the theme's semantic colors."""
    palette = QPalette(base) if base is not None else QPalette()
    # Rebuild the resolve mask so inherited system roles stay inherited, even
    # after switching away from a theme with an explicit accent. Qt resolves
    # these against its native palette (application) or parent (widget).
    palette.setResolveMask(0)
    role = QPalette.ColorRole
    surface = QColor(theme.surface)
    colors = {
        role.Window: surface,
        role.Base: surface,
        role.Button: surface,
        role.AlternateBase: QColor(theme.surface_alternate),
        role.ToolTipBase: QColor(theme.tooltip_surface),
        role.Text: QColor(theme.text),
        role.WindowText: QColor(theme.text),
        role.ButtonText: QColor(theme.text),
        role.ToolTipText: QColor(theme.text),
        role.BrightText: QColor(theme.text),
        role.PlaceholderText: QColor(theme.text_muted),
        role.LinkVisited: QColor(theme.link_visited),
        role.Light: surface.lighter(150),
        role.Midlight: surface.lighter(115),
        role.Mid: QColor(theme.border),
        role.Dark: surface.darker(150),
        role.Shadow: surface.darker(200),
    }
    if theme.accent is not None:
        for accent_role in (role.Highlight, role.Accent, role.Link):
            colors[accent_role] = QColor(theme.accent)
    if theme.on_accent is not None:
        colors[role.HighlightedText] = QColor(theme.on_accent)
    for group in (
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
        QPalette.ColorGroup.Disabled,
    ):
        for color_role, color in colors.items():
            palette.setColor(group, color_role, color)
    for color_role in (
        role.Text,
        role.WindowText,
        role.ButtonText,
        role.ToolTipText,
        role.BrightText,
        role.PlaceholderText,
        role.LinkVisited,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, color_role, QColor(theme.text_disabled))
    if theme.accent is not None:
        for accent_role in (role.Accent, role.Link):
            palette.setColor(QPalette.ColorGroup.Disabled, accent_role, QColor(theme.text_disabled))
        palette.setColor(QPalette.ColorGroup.Disabled, role.Highlight, QColor(theme.border))
    if theme.on_accent is not None:
        palette.setColor(
            QPalette.ColorGroup.Disabled, role.HighlightedText, QColor(theme.text_disabled)
        )
    return palette


def _chrome_palette(theme: ModernTheme, base: QPalette) -> QPalette:
    """Let Qt select inactive chrome colors without fading ordinary page content."""
    palette = palette_for_theme(theme, base)
    foreground = QColor(theme.text)
    foreground.setAlphaF(foreground.alphaF() * 0.5)
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Inactive, role, foreground)
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


@dataclass(frozen=True)
class _WallpaperSnapshot:
    path: Path | None
    signature: WallpaperSignature | None
    colors: tuple[QColor, ...] | None


def _read_wallpaper(previous: WallpaperSignature | None, force: bool) -> _WallpaperSnapshot:
    """Run discovery, metadata IO and QImage sampling without accessing Qt widgets."""
    path = desktop_wallpaper_path()
    # None means discovery failed, not a request to discover the wallpaper again.
    signature = wallpaper_signature(path) if path is not None else None
    colors = None
    if force or signature != previous:
        colors = wallpaper_colors(path) if path is not None else ()
    return _WallpaperSnapshot(path, signature, colors)


_WALLPAPER_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="wallpaper")


class ThemeMode(str, Enum):
    """Persistable user preference, independent of the resolved color scheme."""

    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class ThemeManager(QObject):
    """Manage application colors on the GUI thread.

    Defaults to SYSTEM with wallpaper colors enabled. Unknown system schemes
    resolve to LIGHT. Modes, base themes, and wallpaper policy are independent.
    Use theme_manager() for widgets; additional managers also affect QApplication.
    """

    WALLPAPER_POLL_INTERVAL_MS = 1000
    WALLPAPER_REFRESH_DELAY_MS = 350

    themeChanged = Signal(object)
    modeChanged = Signal(object)
    wallpaperEnabledChanged = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._mode = ThemeMode.SYSTEM
        self._light_theme = LIGHT_THEME
        self._dark_theme = DARK_THEME
        self._theme = LIGHT_THEME
        self._system_scheme = Qt.ColorScheme.Unknown
        self._application: QApplication | None = None
        self._base_palette: QPalette | None = None
        self._wallpaper_enabled = True
        self._wallpaper_path: Path | None = None
        self._wallpaper_signature: WallpaperSignature | None = None
        self._wallpaper_colors: tuple[QColor, ...] = ()
        self._wallpaper_watcher: QFileSystemWatcher | None = None
        self._wallpaper_poll_timer: QTimer | None = None
        self._wallpaper_refresh_timer: QTimer | None = None
        self._wallpaper_result_timer: QTimer | None = None
        self._wallpaper_future: Future[_WallpaperSnapshot] | None = None
        self._wallpaper_refresh_pending = False
        self._wallpaper_revision = 0
        self._wallpaper_request_revision = 0

    def theme(self) -> ModernTheme:
        """Return the effective tokens; attach lazily once QApplication exists."""
        if self._ensure_application():
            self._update_theme()
        self._ensure_wallpaper_monitor()
        return self._theme

    def mode(self) -> ThemeMode:
        """Return the selected preference, including SYSTEM when following the OS."""
        return self._mode

    def setMode(self, mode: ThemeMode) -> None:
        """Select a mode; system detection never reads our application palette."""
        if not isinstance(mode, ThemeMode):
            raise TypeError("mode must be a ThemeMode")
        changed = mode != self._mode
        self._mode = mode
        self._update_theme()
        if changed:
            self.modeChanged.emit(mode)

    def isDark(self) -> bool:
        """Return whether the effective mode is dark, including in SYSTEM mode."""
        self.theme()
        return self._resolved_mode() == ThemeMode.DARK

    def setThemes(self, *, light: ModernTheme, dark: ModernTheme) -> None:
        """Replace both base themes without changing mode or wallpaper policy."""
        if not isinstance(light, ModernTheme) or not isinstance(dark, ModernTheme):
            raise TypeError("light and dark must be ModernTheme instances")
        self._light_theme = light
        self._dark_theme = dark
        self._update_theme()

    def wallpaperEnabled(self) -> bool:
        return self._wallpaper_enabled

    def setWallpaperEnabled(self, enabled: bool) -> None:
        """Enable wallpaper accents or restore the unmodified base theme.

        Disabling stops monitoring and invalidates in-flight samples. An already
        running worker is drained without publishing its result.
        """
        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a bool")
        if enabled == self._wallpaper_enabled:
            self._update_theme()
            return
        self._wallpaper_enabled = enabled
        self._wallpaper_revision += 1
        self._wallpaper_refresh_pending = False
        if not enabled:
            for timer in (self._wallpaper_poll_timer, self._wallpaper_refresh_timer):
                if timer is not None:
                    timer.stop()
            self._sync_wallpaper_watch(None)
        self._update_theme()
        self.wallpaperEnabledChanged.emit(enabled)

    def refreshWallpaperTheme(self) -> None:
        """Refresh asynchronously when wallpaper is enabled; otherwise do nothing."""
        if not self._wallpaper_enabled:
            return
        if self._ensure_application():
            self._update_theme()
            return
        if self._wallpaper_poll_timer is None:
            self._ensure_wallpaper_monitor()
        else:
            self._request_wallpaper_update(force=True)

    def _ensure_application(self) -> bool:
        application = QApplication.instance()
        if not isinstance(application, QApplication) or application is self._application:
            return False
        self._application = application
        self._base_palette = QPalette(application.palette())
        hints = application.styleHints()
        self._system_scheme = hints.colorScheme()
        hints.colorSchemeChanged.connect(self._on_system_color_scheme_changed)
        return True

    def _on_system_color_scheme_changed(self, scheme: Qt.ColorScheme) -> None:
        self._system_scheme = scheme
        if self._mode == ThemeMode.SYSTEM:
            self._update_theme()

    def _resolved_mode(self) -> ThemeMode:
        if self._mode != ThemeMode.SYSTEM:
            return self._mode
        # Unknown platforms use a deterministic light fallback, never our palette.
        return ThemeMode.DARK if self._system_scheme == Qt.ColorScheme.Dark else ThemeMode.LIGHT

    def _update_theme(self) -> None:
        self._ensure_application()
        theme = self._dark_theme if self._resolved_mode() == ThemeMode.DARK else self._light_theme
        if self._wallpaper_enabled and self._wallpaper_colors:
            theme = _theme_from_colors(theme, self._wallpaper_colors)
        changed = theme != self._theme
        # Palette events can synchronously query the manager: expose the new tokens first.
        self._theme = theme
        if self._application is not None:
            palette = palette_for_theme(theme, self._base_palette)
            if palette != self._application.palette():
                self._application.setPalette(palette)
        if changed:
            self.themeChanged.emit(theme)
        self._ensure_wallpaper_monitor()

    def _ensure_wallpaper_monitor(self) -> None:
        application = QApplication.instance()
        if not self._wallpaper_enabled or not isinstance(application, QApplication):
            return
        if self._wallpaper_poll_timer is not None:
            if not self._wallpaper_poll_timer.isActive():
                self._wallpaper_poll_timer.start()
                self._request_wallpaper_update(force=True)
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

        self._wallpaper_result_timer = QTimer(self)
        self._wallpaper_result_timer.setInterval(50)
        self._wallpaper_result_timer.timeout.connect(self._receive_wallpaper_update)
        self._request_wallpaper_update(force=True)
        self._wallpaper_poll_timer.start()

    def _queue_wallpaper_refresh(self, _path: str) -> None:
        if self._wallpaper_enabled and self._wallpaper_refresh_timer is not None:
            self._wallpaper_refresh_timer.start()

    def _refresh_changed_wallpaper(self) -> None:
        self._request_wallpaper_update(force=True)

    def _poll_wallpaper_update(self) -> None:
        self._request_wallpaper_update(force=False)

    def _request_wallpaper_update(self, *, force: bool) -> None:
        if not self._wallpaper_enabled or self._wallpaper_result_timer is None:
            return
        if self._wallpaper_future is not None:
            # Routine polls never build a queue behind a slow OS command. A file
            # change or explicit refresh needs at most one follow-up sample.
            self._wallpaper_refresh_pending |= force
            return
        self._wallpaper_request_revision = self._wallpaper_revision
        self._wallpaper_future = _WALLPAPER_EXECUTOR.submit(
            _read_wallpaper, self._wallpaper_signature, force
        )
        self._wallpaper_result_timer.start()

    def _receive_wallpaper_update(self) -> None:
        future = self._wallpaper_future
        if future is None or not future.done():
            return
        self._wallpaper_future = None
        assert self._wallpaper_result_timer is not None
        self._wallpaper_result_timer.stop()
        request_revision = self._wallpaper_request_revision
        try:
            snapshot = future.result()
        except (OSError, ValueError):
            # Transient discovery/read failures leave the current theme intact;
            # the next poll can retry without leaving the worker marked busy.
            snapshot = None
        if (
            snapshot is not None
            and self._wallpaper_enabled
            and request_revision == self._wallpaper_revision
        ):
            self._wallpaper_path = snapshot.path
            self._wallpaper_signature = snapshot.signature
            self._sync_wallpaper_watch(snapshot.path)
            if snapshot.colors is not None:
                self._wallpaper_colors = snapshot.colors
                self._update_theme()
        if self._wallpaper_refresh_pending:
            self._wallpaper_refresh_pending = False
            self._request_wallpaper_update(force=True)

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


_THEME_MANAGER: ThemeManager | None = None


def theme_manager() -> ThemeManager:
    """Return the process-wide manager. Use on the QApplication GUI thread."""
    global _THEME_MANAGER
    if _THEME_MANAGER is None:
        _THEME_MANAGER = ThemeManager()
    return _THEME_MANAGER
