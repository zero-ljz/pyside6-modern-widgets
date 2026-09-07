from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QImage

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ThemeManager,
    theme_from_wallpaper,
)
from pyside6_modern_widgets._wallpaper import wallpaper_colors


def test_wallpaper_colors_extract_distinct_dominant_colors(tmp_path) -> None:
    path = tmp_path / "wallpaper.png"
    image = QImage(90, 30, QImage.Format.Format_RGB32)
    image.fill(QColor("#D92F2F"))
    for x in range(30, 60):
        for y in range(image.height()):
            image.setPixelColor(x, y, QColor("#2FA34B"))
    for x in range(60, 90):
        for y in range(image.height()):
            image.setPixelColor(x, y, QColor("#315FD1"))
    assert image.save(str(path))

    colors = wallpaper_colors(path)

    assert len(colors) == 3
    for expected in (QColor("#D92F2F"), QColor("#2FA34B"), QColor("#315FD1")):
        assert any(
            abs(color.red() - expected.red()) < 20
            and abs(color.green() - expected.green()) < 20
            and abs(color.blue() - expected.blue()) < 20
            for color in colors
        )


def test_theme_from_wallpaper_preserves_mode_and_uses_wallpaper_color(tmp_path) -> None:
    path = tmp_path / "wallpaper.png"
    image = QImage(20, 20, QImage.Format.Format_RGB32)
    image.fill(QColor("#2968C8"))
    assert image.save(str(path))

    light = theme_from_wallpaper(LIGHT_THEME, path)
    dark = theme_from_wallpaper(DARK_THEME, path)

    assert light.surface == LIGHT_THEME.surface
    assert dark.surface == DARK_THEME.surface
    assert QColor(light.watercolor_spots[0][0]).hslHue() == QColor("#2968C8").hslHue()
    assert QColor(dark.watercolor_spots[0][0]).hslHue() == QColor("#2968C8").hslHue()
    assert light.watercolor_base != LIGHT_THEME.watercolor_base
    assert dark.watercolor_base != DARK_THEME.watercolor_base


def test_theme_from_wallpaper_uses_modern_fallback_for_an_unreadable_image(tmp_path) -> None:
    theme = theme_from_wallpaper(LIGHT_THEME, tmp_path / "missing.jpg")

    assert theme.watercolor_spots


def test_theme_manager_can_refresh_an_active_wallpaper_theme(monkeypatch) -> None:
    from pyside6_modern_widgets import theme as theme_module

    colors = iter(((QColor("#CC3344"),), (QColor("#228866"),)))
    monkeypatch.setattr(theme_module, "wallpaper_colors", lambda _path=None: next(colors))
    manager = ThemeManager()

    first_spot = manager.theme().watercolor_spots[0][0]
    manager.refreshWallpaperTheme()

    assert manager.theme().watercolor_spots[0][0] != first_spot


def test_theme_manager_polls_metadata_before_reextracting_colors(monkeypatch) -> None:
    from pyside6_modern_widgets import theme as theme_module

    fake_path = Path("wallpaper.jpg")
    state = {"revision": 1, "color": QColor("#CC3344"), "extractions": 0}
    monkeypatch.setattr(theme_module, "desktop_wallpaper_path", lambda: fake_path)
    monkeypatch.setattr(
        theme_module,
        "wallpaper_signature",
        lambda _path: (str(fake_path), state["revision"], 100),
    )

    def colors(_path=None):
        state["extractions"] += 1
        return (state["color"],)

    monkeypatch.setattr(theme_module, "wallpaper_colors", colors)
    manager = ThemeManager()
    manager.theme()

    manager._poll_wallpaper_update()
    assert state["extractions"] == 1

    state["revision"] = 2
    state["color"] = QColor("#228866")
    manager._poll_wallpaper_update()

    assert state["extractions"] == 2
    assert QColor(manager.theme().watercolor_spots[0][0]).hslHue() == QColor("#228866").hslHue()
    assert manager.WALLPAPER_POLL_INTERVAL_MS == 1000
