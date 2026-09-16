"""Public API for pyside6-modern-widgets."""

from .modern_combo_box import ModernComboBox
from .modern_dialog import ModernDialog
from .modern_menu import ModernMenu
from .modern_menu_bar import ModernMenuBar
from .modern_message_box import ModernMessageBox
from .modern_switch import ModernSwitch
from .modern_window import ModernWindow
from .navigation_sidebar import NavigationPosition, NavigationSidebar
from .navigation_view import NavigationView
from .tab_view import TabView
from .theme import (
    DARK_THEME,
    DEFAULT_METRICS,
    LIGHT_THEME,
    ModernMetrics,
    ModernTheme,
    ThemeManager,
    ThemeMode,
    palette_for_theme,
    theme_from_wallpaper,
    theme_manager,
)

__all__ = [
    "DARK_THEME",
    "DEFAULT_METRICS",
    "LIGHT_THEME",
    "ModernComboBox",
    "ModernDialog",
    "ModernMenu",
    "ModernMenuBar",
    "ModernMessageBox",
    "ModernMetrics",
    "ModernSwitch",
    "ModernTheme",
    "ModernWindow",
    "NavigationPosition",
    "NavigationSidebar",
    "NavigationView",
    "TabView",
    "ThemeManager",
    "ThemeMode",
    "palette_for_theme",
    "theme_from_wallpaper",
    "theme_manager",
]

__version__ = "0.5.5"
