"""Desktop wallpaper discovery and deterministic color extraction."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage

WallpaperSignature = tuple[str, int, int]


def desktop_wallpaper_path() -> Path | None:
    """Return the current desktop wallpaper when the platform exposes it."""
    path: str | None
    if sys.platform == "win32":
        path = _windows_wallpaper_path()
    elif sys.platform == "darwin":
        path = _command_output(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get picture of current desktop',
            ]
        )
    else:
        path = _linux_wallpaper_path()
    if not path:
        return None
    wallpaper = Path(path).expanduser()
    return wallpaper if wallpaper.is_file() else None


def wallpaper_colors(
    path: str | os.PathLike[str] | None = None,
    *,
    count: int = 3,
) -> tuple[QColor, ...]:
    """Extract visually significant colors from a wallpaper image."""
    wallpaper = Path(path) if path is not None else desktop_wallpaper_path()
    if wallpaper is None:
        return ()
    image = QImage(str(wallpaper))
    if image.isNull():
        return ()
    image = image.convertToFormat(QImage.Format.Format_RGB32).scaled(
        72,
        72,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    buckets: dict[tuple[int, int, int], list[int]] = {}
    totals = [0, 0, 0, 0]
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            red, green, blue = color.red(), color.green(), color.blue()
            key = (red // 32, green // 32, blue // 32)
            bucket = buckets.setdefault(key, [0, 0, 0, 0])
            bucket[0] += red
            bucket[1] += green
            bucket[2] += blue
            bucket[3] += 1
            totals[0] += red
            totals[1] += green
            totals[2] += blue
            totals[3] += 1

    candidates: list[tuple[float, QColor]] = []
    for red, green, blue, samples in buckets.values():
        color = QColor(red // samples, green // samples, blue // samples)
        saturation = color.hslSaturationF()
        score = samples * (0.4 + saturation * 0.6)
        candidates.append((score, color))
    candidates.sort(key=lambda item: item[0], reverse=True)

    selected: list[QColor] = []
    for _score, candidate in candidates:
        if all(_color_distance(candidate, existing) >= 58 for existing in selected):
            selected.append(candidate)
        if len(selected) == max(1, count):
            break
    if totals[3] and len(selected) < max(1, count):
        average = QColor(
            totals[0] // totals[3],
            totals[1] // totals[3],
            totals[2] // totals[3],
        )
        if all(_color_distance(average, existing) >= 24 for existing in selected):
            selected.append(average)
    return tuple(selected[: max(1, count)])


def wallpaper_signature(path: Path | None = None) -> WallpaperSignature | None:
    """Return cheap metadata used to detect a changed wallpaper."""
    wallpaper = path if path is not None else desktop_wallpaper_path()
    if wallpaper is None:
        return None
    try:
        stat = wallpaper.stat()
    except OSError:
        return None
    return (str(wallpaper), stat.st_mtime_ns, stat.st_size)


def _windows_wallpaper_path() -> str | None:
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(32768)
        succeeded = ctypes.windll.user32.SystemParametersInfoW(0x0073, len(buffer), buffer, 0)
        return buffer.value if succeeded else None
    except (AttributeError, OSError):
        return None


def _linux_wallpaper_path() -> str | None:
    for schema, key in (
        ("org.gnome.desktop.background", "picture-uri-dark"),
        ("org.gnome.desktop.background", "picture-uri"),
    ):
        value = _command_output(["gsettings", "get", schema, key])
        if not value:
            continue
        value = value.strip("'\"")
        parsed = urlparse(value)
        path = unquote(parsed.path) if parsed.scheme == "file" else value
        if path and Path(path).is_file():
            return path
    return None


def _command_output(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and value else None


def _color_distance(first: QColor, second: QColor) -> float:
    red = first.red() - second.red()
    green = first.green() - second.green()
    blue = first.blue() - second.blue()
    return (red * red + green * green + blue * blue) ** 0.5
