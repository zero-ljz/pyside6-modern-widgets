"""Public API for pyside6-modern-widgets."""

from .edge_dock import (
    DockConfig,
    DockHandleMode,
    DockPlacement,
    DockSide,
    DockState,
    EdgeDockController,
)
from .i18n import load_translator
from .modern_combo_box import ModernComboBox
from .modern_dialog import ModernDialog
from .modern_flyout import FlyoutPlacement, ModernFlyout
from .modern_menu import ModernMenu
from .modern_menu_bar import ModernMenuBar
from .modern_message_box import ModernMessageBox
from .modern_notification import ModernNotification
from .modern_segmented_control import ModernSegmentedControl
from .modern_switch import ModernSwitch
from .modern_tab_widget import ModernTabWidget
from .modern_tool_bar import ModernToolBar
from .modern_window import ModernWindow
from .navigation_sidebar import NavigationPosition, NavigationSidebar
from .navigation_view import NavigationView
from .notification import (
    NotificationAction,
    NotificationKind,
    NotificationSnapshot,
    NotificationState,
)
from .notification_manager import NotificationHandle, NotificationManager, NotificationPosition
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
    "DockHandleMode",
    "DockPlacement",
    "DockSide",
    "DockState",
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
    "ModernSegmentedControl",
    "ModernSwitch",
    "ModernTabWidget",
    "ModernTheme",
    "ModernToolBar",
    "ModernWindow",
    "NavigationPosition",
    "NavigationSidebar",
    "NavigationView",
    "NotificationAction",
    "NotificationHandle",
    "NotificationKind",
    "NotificationManager",
    "NotificationPosition",
    "NotificationSnapshot",
    "NotificationState",
    "TabView",
    "ThemeManager",
    "ThemeMode",
    "load_translator",
    "palette_for_theme",
    "theme_from_wallpaper",
    "theme_manager",
]

__version__ = "0.6.0"
