"""Public API for pyside6-modern-widgets."""

from .edge_dock import DockConfig, DockSide, EdgeDockController
from .i18n import load_translator
from .modern_combo_box import ModernComboBox
from .modern_dialog import ModernDialog
from .modern_flyout import FlyoutPlacement, ModernFlyout
from .modern_menu import ModernMenu
from .modern_menu_bar import ModernMenuBar
from .modern_message_box import ModernMessageBox
from .modern_notification import ModernNotification, NotificationKind
from .modern_switch import ModernSwitch
from .modern_tool_bar import ModernToolBar
from .modern_window import ModernWindow
from .navigation_sidebar import NavigationPosition, NavigationSidebar
from .navigation_view import NavigationView
from .notification_manager import NotificationManager, NotificationPosition
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
    "DockConfig",
    "DockSide",
    "EdgeDockController",
    "FlyoutPlacement",
    "ModernComboBox",
    "ModernDialog",
    "ModernFlyout",
    "ModernMenu",
    "ModernMenuBar",
    "ModernMessageBox",
    "ModernMetrics",
    "ModernNotification",
    "ModernSwitch",
    "ModernTheme",
    "ModernToolBar",
    "ModernWindow",
    "NavigationPosition",
    "NavigationSidebar",
    "NavigationView",
    "NotificationKind",
    "NotificationManager",
    "NotificationPosition",
    "TabView",
    "ThemeManager",
    "ThemeMode",
    "load_translator",
    "palette_for_theme",
    "theme_from_wallpaper",
    "theme_manager",
]

__version__ = "0.5.10"
