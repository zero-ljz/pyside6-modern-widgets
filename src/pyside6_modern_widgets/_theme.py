"""Shared colors and theme resolution for the widget library."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtWidgets import QApplication

from .window_effect import ThemeMode


@dataclass(frozen=True, slots=True)
class ThemeColors:
    window: str
    inactive_window: str
    surface: str
    page: str
    text: str
    muted_text: str
    hover: str
    pressed: str
    border: str
    divider: str
    tab_hover: str
    tab_selected: str


LIGHT_COLORS = ThemeColors(
    window="#F3F3F3",
    inactive_window="#F3F3F3",
    surface="#FFFFFF",
    page="#F0F0F0",
    text="#202020",
    muted_text="#454545",
    hover="rgba(0, 0, 0, 0.05)",
    pressed="rgba(0, 0, 0, 0.15)",
    border="#E5E5E5",
    divider="#D1D1D1",
    tab_hover="#EAEAEA",
    tab_selected="#FFFFFF",
)

DARK_COLORS = ThemeColors(
    window="#202020",
    inactive_window="#2B2B2B",
    surface="#2B2B2B",
    page="#202020",
    text="#F5F5F5",
    muted_text="#D0D0D0",
    hover="rgba(255, 255, 255, 0.08)",
    pressed="rgba(255, 255, 255, 0.14)",
    border="#454545",
    divider="#484848",
    tab_hover="#353535",
    tab_selected="#2B2B2B",
)


def resolve_theme_mode(
    theme: ThemeMode | str,
    *,
    system_dark: bool = False,
) -> ThemeMode:
    theme = ThemeMode(theme)
    if theme is ThemeMode.AUTO:
        return ThemeMode.DARK if system_dark else ThemeMode.LIGHT
    return theme


def colors_for_theme(
    theme: ThemeMode | str,
    *,
    system_dark: bool = False,
) -> ThemeColors:
    resolved = resolve_theme_mode(theme, system_dark=system_dark)
    return DARK_COLORS if resolved is ThemeMode.DARK else LIGHT_COLORS


def resolve_application_theme(theme: ThemeMode | str) -> ThemeMode:
    app = QApplication.instance()
    system_dark = bool(app and app.styleHints().colorScheme() is Qt.ColorScheme.Dark)
    return resolve_theme_mode(theme, system_dark=system_dark)


def themed_icon(icon: QIcon, color: str, size: int = 48) -> QIcon:
    """Tint monochrome icons while preserving colored application icons."""
    if icon.isNull():
        return icon
    pixmap = icon.pixmap(size, size)
    image = pixmap.toImage()
    for y in range(image.height()):
        for x in range(image.width()):
            pixel = image.pixelColor(x, y)
            if pixel.alpha() and pixel.hsvSaturation() > 24:
                return icon
    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return QIcon(pixmap)
