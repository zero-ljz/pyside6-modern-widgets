"""Public API for pyside6-modern-widgets."""

from .modern_dialog import ModernDialog
from .modern_menu import ModernMenu
from .modern_menu_bar import ModernMenuBar
from .modern_message_box import ModernMessageBox
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
    theme_from_wallpaper,
    theme_manager,
)

__all__ = [
    "DARK_THEME",
    "DEFAULT_METRICS",
    "LIGHT_THEME",
    "ModernDialog",
    "ModernMenu",
    "ModernMenuBar",
    "ModernMessageBox",
    "ModernMetrics",
    "ModernTheme",
    "ModernWindow",
    "NavigationPosition",
    "NavigationSidebar",
    "NavigationView",
    "TabView",
    "ThemeManager",
    "theme_from_wallpaper",
    "theme_manager",
]

__version__ = "0.4.3"
