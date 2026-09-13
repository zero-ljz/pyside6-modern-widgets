"""A native QMessageBox with the package's themed frameless chrome."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QMessageBox, QWidget

from ._window_chrome import (
    BackgroundFrame,
    WindowChromeOverlay,
    WindowTitleBar,
    current_window_surface_policy,
)
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    palette_for_theme,
    theme_manager,
)


class ModernMessageBox(QMessageBox):
    """Keep QMessageBox content and behavior, adding only themed window chrome."""

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
        if isinstance(icon, QWidget):
            if title or text or buttons != self.StandardButton.NoButton or parent is not None:
                raise TypeError("parent-only construction cannot include message-box arguments")
            parent = icon
            icon = self.Icon.NoIcon
        elif icon is None:
            icon = self.Icon.NoIcon

        super().__init__(
            icon, title, text, buttons, parent, flags | Qt.WindowType.FramelessWindowHint
        )
        # Keep Qt's widget implementation so our palette and chrome also work on
        # platforms that otherwise substitute an operating-system message box.
        self.setOption(QMessageBox.Option.DontUseNativeDialog)
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self._metrics = metrics
        self._corner_radius = metrics.corner_radius
        self._surface_policy = current_window_surface_policy()
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
        self._chrome_overlay = WindowChromeOverlay(
            self, theme=self._theme, corner_radius=paint_radius
        )
        self._background_frame.show()
        self._chrome_overlay.show()
        self.windowTitleChanged.connect(self._title_bar.setTitle)
        self.windowIconChanged.connect(self._title_bar.setIcon)
        theme_manager().themeChanged.connect(self._on_global_theme_changed)
        self._sync_chrome_with_window_flags()
        self.apply_window_style()

    def theme(self) -> ModernTheme:
        return self._theme

    def setTheme(self, theme: ModernTheme | None) -> None:
        self._uses_global_theme = theme is None
        self._theme = theme or theme_manager().theme()
        self.apply_window_style()

    def setCornerRadius(self, radius: int) -> None:
        self._corner_radius = max(0, radius)
        self.apply_window_style()

    def apply_window_style(self) -> None:
        radius = 0 if self.isMaximized() or self.isFullScreen() else self._corner_radius
        paint_radius = self._surface_policy.paint_corner_radius(radius)
        self.setPalette(palette_for_theme(self._theme, self.palette()))
        self._background_frame.setTheme(self._theme)
        self._background_frame.setCornerRadius(paint_radius)
        self._title_bar.setTheme(self._theme)
        self._chrome_overlay.setTheme(self._theme)
        self._chrome_overlay.setCornerRadius(paint_radius)
        self._surface_policy.apply_native_corner_preference(self, radius > 0)
        self._layout_chrome()
        self.update()

    def _on_global_theme_changed(self, theme: ModernTheme) -> None:
        if self._uses_global_theme:
            self._theme = theme
            self.apply_window_style()

    def setWindowFlags(self, flags: Qt.WindowType) -> None:
        super().setWindowFlags(flags | Qt.WindowType.FramelessWindowHint)
        if hasattr(self, "_chrome_overlay"):
            self._sync_chrome_with_window_flags()

    def setWindowFlag(self, flag: Qt.WindowType, on: bool = True) -> None:
        super().setWindowFlag(flag, on)
        super().setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        if hasattr(self, "_chrome_overlay"):
            self._sync_chrome_with_window_flags()

    def _sync_chrome_with_window_flags(self) -> None:
        visible = self._title_bar.syncWindowFlags(self.windowFlags())
        self.setContentsMargins(0, self._title_bar.height() if visible else 0, 0, 0)
        self._layout_chrome()

    def _layout_chrome(self) -> None:
        self._background_frame.setGeometry(self.rect())
        self._background_frame.lower()
        self._title_bar.setGeometry(0, 0, self.width(), self._title_bar.height())
        self._chrome_overlay.setGeometry(self.rect())
        self._chrome_overlay.raise_()
        self._title_bar.raise_()

    def event(self, event) -> bool:
        handled = super().event(event)
        # QMessageBox can dispatch events while its C++ constructor is running.
        if not hasattr(self, "_chrome_overlay"):
            return handled
        if event.type() == QEvent.Type.Show:
            self._sync_chrome_with_window_flags()
            self.apply_window_style()
        elif event.type() == QEvent.Type.Resize:
            self._layout_chrome()
        elif event.type() == QEvent.Type.WindowStateChange:
            self.apply_window_style()
        return handled

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
