"""Public API for pyside6-modern-widgets."""

from .modern_window import ModernWindow
from .navigation_sidebar import NavigationPosition, NavigationSidebar
from .navigation_view import NavigationView
from .tab_view import TabView
from .theme import (
    DARK_THEME,
    DEFAULT_METRICS,
    LIGHT_THEME,
    ORIGINAL_DARK_THEME,
    ORIGINAL_LIGHT_THEME,
    ModernMetrics,
    ModernTheme,
    ThemeManager,
    WatercolorStyle,
    theme_manager,
    theme_with_watercolor_style,
)

__all__ = [
    "DARK_THEME",
    "DEFAULT_METRICS",
    "LIGHT_THEME",
    "ORIGINAL_DARK_THEME",
    "ORIGINAL_LIGHT_THEME",
    "ModernMetrics",
    "ModernTheme",
    "ModernWindow",
    "NavigationPosition",
    "NavigationSidebar",
    "NavigationView",
    "TabView",
    "ThemeManager",
    "WatercolorStyle",
    "theme_manager",
    "theme_with_watercolor_style",
]

__version__ = "0.4.1"
