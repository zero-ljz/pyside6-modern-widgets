"""Public API for pyside6-modern-widgets."""

from .modern_window import ModernWindow
from .navigation_sidebar import NavigationPosition, NavigationSidebar, NavigationStyle
from .navigation_view import NavigationView
from .tab_view import TabView
from .window_effect import WindowEffect, WindowStyleState

__all__ = [
    "ModernWindow",
    "NavigationPosition",
    "NavigationSidebar",
    "NavigationStyle",
    "NavigationView",
    "TabView",
    "WindowEffect",
    "WindowStyleState",
]

__version__ = "0.1.2"
