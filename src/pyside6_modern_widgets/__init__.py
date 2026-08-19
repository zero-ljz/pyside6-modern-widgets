"""Public API for pyside6-modern-widgets."""

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
    theme_manager,
)
from .window_effect import WindowEffect, WindowStyleState

__all__ = [
    "DARK_THEME",
    "DEFAULT_METRICS",
    "LIGHT_THEME",
    "ModernMetrics",
    "ModernTheme",
    "ModernWindow",
    "NavigationPosition",
    "NavigationSidebar",
    "NavigationView",
    "TabView",
    "ThemeManager",
    "WindowEffect",
    "WindowStyleState",
    "theme_manager",
]

__version__ = "0.2.0"
