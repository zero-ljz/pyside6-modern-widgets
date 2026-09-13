from __future__ import annotations

import subprocess
import sys
from dataclasses import replace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernDialog,
    ModernMenu,
    ModernMenuBar,
    ModernMessageBox,
    ModernWindow,
    NavigationSidebar,
    NavigationView,
    TabView,
    ThemeMode,
    palette_for_theme,
    theme_from_wallpaper,
)

_APP = QApplication.instance()


def test_manual_dark_returns_to_real_system_scheme(theme_manager_instance, system_appearance):
    manager = theme_manager_instance
    modes, themes = [], []
    manager.modeChanged.connect(modes.append)
    manager.themeChanged.connect(themes.append)
    manager.setMode(ThemeMode.DARK)
    assert manager.isDark()
    assert _APP.palette().color(QPalette.ColorRole.Window) == QColor(DARK_THEME.surface)

    # The OS is still light even though the application palette is now dark.
    manager.setMode(ThemeMode.SYSTEM)
    assert manager.mode() == ThemeMode.SYSTEM
    assert not manager.isDark()
    assert manager.theme() == LIGHT_THEME
    system_appearance.setScheme(Qt.ColorScheme.Dark)
    assert manager.mode() == ThemeMode.SYSTEM
    assert manager.isDark()
    assert themes == [DARK_THEME, LIGHT_THEME, DARK_THEME]
    assert modes == [ThemeMode.DARK, ThemeMode.SYSTEM]


def test_fixed_mode_tracks_but_does_not_apply_system_changes(
    theme_manager_instance, system_appearance
):
    manager = theme_manager_instance
    manager.setMode(ThemeMode.LIGHT)
    changes = []
    manager.themeChanged.connect(changes.append)
    system_appearance.setScheme(Qt.ColorScheme.Dark)
    assert manager.theme() == LIGHT_THEME
    assert changes == []
    manager.setMode(ThemeMode.SYSTEM)
    assert manager.theme() == DARK_THEME
    assert changes == [DARK_THEME]


def test_unknown_scheme_has_light_fallback_independent_of_palette(
    theme_manager_instance, system_appearance
):
    manager = theme_manager_instance
    manager.setMode(ThemeMode.DARK)
    system_appearance.setScheme(Qt.ColorScheme.Unknown)
    manager.setMode(ThemeMode.SYSTEM)
    assert manager.theme() == LIGHT_THEME
    assert not manager.isDark()


def test_mode_signals_are_distinct_and_emit_after_state_is_applied(theme_manager_instance):
    manager = theme_manager_instance
    modes, themes = [], []
    manager.modeChanged.connect(modes.append)

    def theme_changed(theme):
        assert manager.theme() == theme
        assert _APP.palette().color(QPalette.ColorRole.Window) == QColor(theme.surface)
        themes.append(theme)

    manager.themeChanged.connect(theme_changed)
    manager.setMode(ThemeMode.LIGHT)  # SYSTEM already resolved to light.
    manager.setMode(ThemeMode.LIGHT)
    assert modes == [ThemeMode.LIGHT]
    assert themes == []
    manager.setMode(ThemeMode.DARK)
    manager.setMode(ThemeMode.DARK)
    assert themes == [DARK_THEME]


def test_custom_theme_pair_survives_mode_switches(theme_manager_instance, system_appearance):
    manager = theme_manager_instance
    light = replace(LIGHT_THEME, name="brand-day", accent="#123456")
    dark = replace(DARK_THEME, name="brand-night", accent="#ABCDEF")
    manager.setThemes(light=light, dark=dark)
    assert manager.mode() == ThemeMode.SYSTEM
    assert manager.theme() == light
    system_appearance.setScheme(Qt.ColorScheme.Dark)
    assert manager.theme() == dark
    manager.setMode(ThemeMode.LIGHT)
    assert manager.theme() == light
    with pytest.raises(TypeError):
        manager.setMode("dark")
    with pytest.raises(TypeError):
        manager.setThemes(light=None, dark=dark)
    assert manager.theme() == light
    assert ThemeMode(manager.mode().value) == manager.mode()


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME], ids=["light", "dark"])
def test_palette_covers_native_controls_in_all_color_groups(theme):
    theme = replace(theme, accent="#7030A0", on_accent="#FFFFFF")
    palette = palette_for_theme(theme)
    role = QPalette.ColorRole
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        assert palette.color(group, role.Highlight) == QColor(theme.accent)
        assert palette.color(group, role.HighlightedText) == QColor(theme.on_accent)
        assert palette.color(group, role.ToolTipBase) == QColor(theme.tooltip_surface)
        assert palette.color(group, role.ToolTipText) == QColor(theme.text)
        assert palette.color(group, role.PlaceholderText) == QColor(theme.text_muted)
        assert palette.color(group, role.AlternateBase) == QColor(theme.surface_alternate)
        assert palette.color(group, role.Link) == QColor(theme.accent)
    disabled = QPalette.ColorGroup.Disabled
    assert palette.color(disabled, role.Text) == QColor(theme.text_disabled)
    assert palette.color(disabled, role.Base) == QColor(theme.surface)
    assert palette.color(disabled, role.Window) == QColor(theme.surface)
    assert palette.color(disabled, role.ToolTipText) == QColor(theme.text_disabled)


@pytest.mark.parametrize(
    "widget_type",
    [ModernWindow, ModernDialog, ModernMessageBox, NavigationView, NavigationSidebar, TabView],
)
def test_existing_widgets_follow_global_and_can_restore_local_override(
    theme_manager_instance, widget_type
):
    manager = theme_manager_instance
    following, fixed = widget_type(), widget_type(theme=LIGHT_THEME)
    try:
        manager.setMode(ThemeMode.DARK)
        assert following.theme() == DARK_THEME
        assert fixed.theme() == LIGHT_THEME
        assert following.palette().color(QPalette.ColorRole.Text) == QColor(DARK_THEME.text)
        fixed.setTheme(None)
        assert fixed.theme() == DARK_THEME
        manager.setMode(ThemeMode.LIGHT)
        assert following.theme() == fixed.theme() == LIGHT_THEME
        following.setTheme(DARK_THEME)
        manager.setThemes(light=replace(LIGHT_THEME, text="#111111"), dark=DARK_THEME)
        assert following.theme() == DARK_THEME
        assert fixed.theme().text == "#111111"
    finally:
        for widget in (following, fixed):
            widget.close()
            widget.deleteLater()
        _APP.processEvents()


def test_business_controls_and_open_menus_refresh(theme_manager_instance, monkeypatch):
    from pyside6_modern_widgets import modern_menu as menu_module

    tints = []
    monkeypatch.setattr(menu_module, "_enable_windows_rounded_corners", lambda *args: True)

    def enable_acrylic(menu):
        tints.append(menu.palette().color(QPalette.ColorRole.Window))
        return True

    monkeypatch.setattr(menu_module, "_enable_windows_acrylic", enable_acrylic)
    window = ModernWindow()
    page = QWidget()
    layout = QVBoxLayout(page)
    label, edit, disabled = QLabel("Text"), QLineEdit(), QPushButton("Disabled")
    edit.setPlaceholderText("Placeholder")
    disabled.setEnabled(False)
    for control in (label, edit, disabled):
        layout.addWidget(control)
    window.setCentralWidget(page)
    menu_bar = window.menuBar()
    menu = menu_bar.addMenu("File")
    submenu = menu.addMenu("Recent")
    submenu.addAction("Document")
    standalone = ModernMenu()
    standalone.addAction("Standalone")
    try:
        window.show()
        menu.show()
        standalone.show()
        _APP.processEvents()
        theme_manager_instance.setMode(ThemeMode.DARK)
        _APP.processEvents()
        for widget in (label, edit, menu_bar, menu, submenu, standalone):
            assert widget.palette().color(QPalette.ColorRole.WindowText) == QColor(DARK_THEME.text)
        assert edit.palette().color(QPalette.ColorRole.Base) == QColor(DARK_THEME.surface)
        assert disabled.palette().color(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText
        ) == QColor(DARK_THEME.text_disabled)
        assert QColor(DARK_THEME.surface) in tints
        assert isinstance(menu_bar, ModernMenuBar)
        # New popups use the current palette too.
        late_menu = menu.addMenu("Created after switch")
        assert late_menu.palette().color(QPalette.ColorRole.Window) == QColor(DARK_THEME.surface)
    finally:
        menu.close()
        standalone.close()
        window.close()
        standalone.deleteLater()
        window.deleteLater()
        _APP.processEvents()


def test_theme_can_be_configured_before_application_creation():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QPalette
from pyside6_modern_widgets import DARK_THEME, ThemeMode, theme_manager
manager = theme_manager()
assert manager.mode() == ThemeMode.SYSTEM
assert manager.wallpaperEnabled()
manager.setWallpaperEnabled(False)
manager.setMode(ThemeMode.DARK)
app = QApplication([])
assert manager.theme() == DARK_THEME
assert app.palette().color(QPalette.ColorRole.Window) == QColor(DARK_THEME.surface)
assert manager.isDark()
""",
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


def test_missing_wallpaper_preserves_custom_base(tmp_path):
    theme = replace(DARK_THEME, focus="#123456", watercolor_base="#112233")
    assert theme_from_wallpaper(theme, tmp_path / "missing.png") == theme


def test_default_accent_roles_follow_qt_and_restore_after_custom_colors():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from dataclasses import replace
from PySide6.QtWidgets import QApplication, QLineEdit
from PySide6.QtGui import QColor, QPalette
from pyside6_modern_widgets import DARK_THEME, LIGHT_THEME, ThemeMode, theme_manager
app = QApplication([])
app.setStyle('Fusion')
native = app.palette()
roles = (QPalette.ColorRole.Accent, QPalette.ColorRole.Highlight,
         QPalette.ColorRole.HighlightedText, QPalette.ColorRole.Link)
groups = (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive,
          QPalette.ColorGroup.Disabled)
manager = theme_manager()
manager.setWallpaperEnabled(False)
edit = QLineEdit()
for mode in (ThemeMode.DARK, ThemeMode.LIGHT, ThemeMode.SYSTEM):
    manager.setMode(mode)
    app.processEvents()
    for group in groups:
        for role in roles:
            assert app.palette().color(group, role) == native.color(group, role), (group, role)
            assert edit.palette().color(group, role) == native.color(group, role), (group, role)
manager.setThemes(
    light=replace(LIGHT_THEME, accent='#7030A0', on_accent='#FFFFFF'),
    dark=replace(DARK_THEME, accent='#7030A0', on_accent='#FFFFFF'))
assert app.palette().color(QPalette.ColorRole.Highlight) == QColor('#7030A0')
manager.setThemes(light=LIGHT_THEME, dark=DARK_THEME)
app.processEvents()
for group in groups:
    for role in roles:
        assert app.palette().color(group, role) == native.color(group, role), (group, role)
        assert edit.palette().color(group, role) == native.color(group, role), (group, role)
""",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


def test_default_palette_inherits_updated_parent_accent():
    parent = QWidget()
    child = QLineEdit(parent)
    child.setPalette(palette_for_theme(DARK_THEME, child.palette()))
    try:
        for name in ("#008676", "#AC366E"):
            palette = parent.palette()
            palette.setColor(QPalette.ColorRole.Highlight, QColor(name))
            parent.setPalette(palette)
            assert child.palette().color(QPalette.ColorRole.Highlight) == QColor(name)
            assert child.palette().color(QPalette.ColorRole.Base) == QColor(DARK_THEME.surface)
    finally:
        parent.deleteLater()
