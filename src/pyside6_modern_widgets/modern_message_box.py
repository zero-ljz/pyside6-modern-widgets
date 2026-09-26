"""A themed QMessageBox with native macOS or portable frameless chrome."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QMessageBox, QWidget

from . import _system_menu
from ._macos_window import (
    set_macos_window_appearance,
    uses_macos_native_title_bar,
    window_flags_with_chrome,
)
from ._theme_binding import ThemeBinding
from ._window_chrome import (
    BackgroundFrame,
    WindowChrome,
    WindowChromeOverlay,
    WindowDpiState,
    WindowTitleBar,
    current_window_surface_policy,
)
from .modern_menu import _enable_windows_rounded_corners
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    inherited_theme,
)


class ModernMessageBox(QMessageBox):
    """Keep QMessageBox content and behavior, adding only themed window chrome."""

    themeChanged = Signal(object)

    def __init__(
        self,
        icon: QMessageBox.Icon | QWidget | None = QMessageBox.Icon.NoIcon,
        title: str = "",
        text: str = "",
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Dialog | Qt.WindowType.MSWindowsFixedSizeDialogHint,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        self._uses_native_macos_title_bar = uses_macos_native_title_bar()
        self._native_dpi = WindowDpiState()
        if isinstance(icon, QWidget):
            if title or text or buttons != self.StandardButton.NoButton or parent is not None:
                raise TypeError("parent-only construction cannot include message-box arguments")
            parent = icon
            icon = self.Icon.NoIcon
        elif icon is None:
            icon = self.Icon.NoIcon

        super().__init__(
            icon,
            title,
            text,
            buttons,
            parent,
            window_flags_with_chrome(
                flags, native_macos_title_bar=self._uses_native_macos_title_bar
            ),
        )
        # Keep Qt's widget implementation so our palette and chrome also work on
        # platforms that otherwise substitute an operating-system message box.
        self.setOption(QMessageBox.Option.DontUseNativeDialog)
        if self._uses_native_macos_title_bar:
            QWidget.setWindowTitle(self, title)
        self._theme_override = theme
        self._theme = theme if theme is not None else inherited_theme(self)
        self._metrics = metrics
        self._corner_radius = metrics.corner_radius
        self._surface_policy = current_window_surface_policy(
            native_macos_title_bar=self._uses_native_macos_title_bar
        )
        self._surface_policy.apply_to(self)

        paint_radius = self._surface_policy.paint_corner_radius(self._corner_radius)
        self._background_frame = BackgroundFrame(
            self,
            theme=self._theme,
            corner_radius=paint_radius,
            opaque_surface=self._surface_policy.opaque_surface,
        )
        self._background_frame.setObjectName("backgroundFrame")
        self._background_frame.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._title_bar = WindowTitleBar(self, theme=self._theme, metrics=metrics)
        self._title_bar.setIcon(self.windowIcon())
        self._system_menu_controller = _system_menu.SystemMenuController(
            self, self._title_bar, self._metrics
        )
        self._chrome_overlay = WindowChromeOverlay(
            self, theme=self._theme, corner_radius=paint_radius
        )
        self._chrome = WindowChrome(
            self,
            self._background_frame,
            self._chrome_overlay,
            self._title_bar,
            self._surface_policy,
        )
        self._background_frame.show()
        self._chrome_overlay.show()
        self.windowTitleChanged.connect(self._title_bar.setTitle)
        self.windowIconChanged.connect(self._title_bar.setIcon)
        self._sync_chrome_with_window_flags()
        self._apply_window_style()
        self._theme_binding: ThemeBinding = ThemeBinding(self, self.theme, self._apply_window_style)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override locally; None restores ancestor/global theme inheritance."""
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def cornerRadius(self) -> int:
        return self._corner_radius

    def setCornerRadius(self, radius: int) -> None:
        self._corner_radius = max(0, radius)
        self._apply_window_style()

    def showSystemWindowMenu(self, position: QPoint) -> bool:
        if self._uses_native_macos_title_bar:
            return False
        return self._system_menu_controller.show(position)

    def setWindowTitle(self, title: str) -> None:
        # QMessageBox intentionally ignores titles on macOS. This class keeps
        # a titled native dialog so its caption remains a usable drag region.
        QWidget.setWindowTitle(self, title)

    def _apply_window_style(self) -> None:
        self._theme = self.theme()
        self._chrome.apply(self._theme, self._corner_radius)
        if self._uses_native_macos_title_bar:
            self._title_bar.hide()
            self._chrome_overlay.hide()
        palette = self.palette()
        background = QColor(self._theme.surface_alternate)
        for group in (
            QPalette.ColorGroup.Active,
            QPalette.ColorGroup.Inactive,
            QPalette.ColorGroup.Disabled,
        ):
            palette.setColor(group, QPalette.ColorRole.Window, background)
        self.setPalette(palette)
        self._sync_macos_appearance()

    def _sync_macos_appearance(self) -> None:
        if self._uses_native_macos_title_bar and self.isVisible() and self.internalWinId():
            set_macos_window_appearance(
                self, dark=QColor(self._theme.surface_alternate).lightness() < 128
            )

    def _refresh_native_surface(self) -> None:
        """Apply Windows 11 acrylic and rounded corners when the native handle exists."""
        if not self.isWindow():
            return
        # Message boxes use a clean surface; the watercolor background belongs to
        # the main window.
        self._background_frame.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAutoFillBackground(True)
        _enable_windows_rounded_corners(self, self._corner_radius)

    def setWindowFlags(self, flags: Qt.WindowType) -> None:
        super().setWindowFlags(
            window_flags_with_chrome(
                flags, native_macos_title_bar=self._uses_native_macos_title_bar
            )
        )
        if hasattr(self, "_chrome"):
            self._sync_chrome_with_window_flags()

    def setWindowFlag(self, flag: Qt.WindowType, on: bool = True) -> None:
        super().setWindowFlag(flag, on)
        super().setWindowFlag(
            Qt.WindowType.FramelessWindowHint, not self._uses_native_macos_title_bar
        )
        if hasattr(self, "_chrome"):
            self._sync_chrome_with_window_flags()

    def _sync_chrome_with_window_flags(self) -> None:
        if self._uses_native_macos_title_bar:
            self._title_bar.hide()
            self._chrome_overlay.hide()
            # QMessageBox's macOS layout uses QWidget contents margins rather
            # than layout margins. Keep all four, including after details change.
            self._layout_chrome()
            return
        visible = self._title_bar.syncWindowFlags(self.windowFlags())
        self.setContentsMargins(0, self._title_bar.height() if visible else 0, 0, 0)
        self._layout_chrome()

    def _layout_chrome(self) -> None:
        self._chrome.layout()

    def event(self, event) -> bool:
        handled = super().event(event)
        # QMessageBox can dispatch events while its C++ constructor is running.
        if not hasattr(self, "_chrome"):
            return handled
        if event.type() in (QEvent.Type.Show, QEvent.Type.WinIdChange):
            self._native_dpi.sync_window(self)
            if event.type() == QEvent.Type.WinIdChange and self.isVisible():
                self._sync_macos_appearance()
        if event.type() == QEvent.Type.Show:
            self._sync_chrome_with_window_flags()
            self._apply_window_style()
            self._refresh_native_surface()
        elif event.type() == QEvent.Type.PaletteChange:
            self._refresh_native_surface()
        elif event.type() == QEvent.Type.Resize:
            self._layout_chrome()
        elif event.type() == QEvent.Type.WindowStateChange:
            self._apply_window_style()
        return handled

    def nativeEvent(self, event_type, message):
        if self._native_dpi.handle_native_event(self, message):
            return True, 0
        return super().nativeEvent(event_type, message)

    @classmethod
    def _show_message(
        cls,
        icon: QMessageBox.Icon,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton,
        default_button: QMessageBox.StandardButton,
    ) -> QMessageBox.StandardButton:
        message_box = cls(icon, title, text, buttons, parent)
        if default_button != cls.StandardButton.NoButton:
            message_box.setDefaultButton(default_button)
        result = message_box.exec()
        return cls.StandardButton(result)

    @classmethod
    def information(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        defaultButton: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
    ) -> QMessageBox.StandardButton:
        return cls._show_message(cls.Icon.Information, parent, title, text, buttons, defaultButton)

    @classmethod
    def question(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No,
        defaultButton: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
    ) -> QMessageBox.StandardButton:
        return cls._show_message(cls.Icon.Question, parent, title, text, buttons, defaultButton)

    @classmethod
    def warning(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        defaultButton: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
    ) -> QMessageBox.StandardButton:
        return cls._show_message(cls.Icon.Warning, parent, title, text, buttons, defaultButton)

    @classmethod
    def critical(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        defaultButton: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
    ) -> QMessageBox.StandardButton:
        return cls._show_message(cls.Icon.Critical, parent, title, text, buttons, defaultButton)
