"""Custom notification cards for desktop and in-window delivery."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import (
    QByteArray,
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QIcon, QPainter, QPalette, QPen, QWindow
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ._window_chrome import WindowDpiState, uses_windows_window_state
from ._windows_window import redraw_native_window
from .modern_menu import (
    _enable_windows_acrylic,
    _enable_windows_rounded_corners,
    _soft_line_color,
    _surface_color,
)
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    inherited_theme,
    palette_for_theme,
    theme_manager,
    tinted_icon,
)


class NotificationKind(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class _TitleLabel(QLabel):
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(self.palette().color(QPalette.ColorRole.WindowText))
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(
            self.rect(), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeading, text
        )


class ModernNotification(QWidget):
    """A themed notification card. NotificationManager supplies delivery and timing.

    Text is always plain text. Actions emit their ID before optionally closing.
    Body activation emits activated() without performing an application action.
    Long content scrolls while the close button remains visible.
    """

    activated = Signal()
    actionTriggered = Signal(str)
    dismissed = Signal(str)
    hoveredChanged = Signal(bool)
    contentChanged = Signal()

    def __init__(
        self,
        title: str = "",
        message: str = "",
        parent: QWidget | None = None,
        *,
        kind: NotificationKind | str = NotificationKind.INFO,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        kind = NotificationKind(kind)
        super().__init__(parent)
        self._theme_override = theme
        self._inherited_theme: ModernTheme | None = None
        self._metrics = metrics
        self._kind = kind
        self._icon_override: QIcon | None = None
        self._progress: int | None = None
        self._native_corners = False
        self._native_acrylic = False
        self._desktop = False
        self._close_reason = "dismissed"
        self._dismissed = False
        self._pressed = False
        self._buttons: dict[str, QPushButton] = {}
        self._action_closes: dict[str, bool] = {}
        self._native_dpi = WindowDpiState()
        self._screen_change_window: QWindow | None = None
        self._surface_refresh_timer = QTimer(self)
        self._surface_refresh_timer.setSingleShot(True)
        self._surface_refresh_timer.timeout.connect(self._refresh_after_display_change)
        self._surface_settle_timer = QTimer(self)
        self._surface_settle_timer.setSingleShot(True)
        self._surface_settle_timer.timeout.connect(self._refresh_after_display_change)
        self._move_animation = QPropertyAnimation(self, QByteArray(b"pos"), self)
        self._move_animation.setDuration(max(0, metrics.animation_duration))
        self._move_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_WindowPropagation)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        self._layout = QVBoxLayout(self)
        self._layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(6)
        self._header = QHBoxLayout()
        self._header.setSpacing(8)
        self._icon = QLabel()
        self._icon.setFixedSize(20, 20)
        self._title = _TitleLabel(title)
        self._title.setTextFormat(Qt.TextFormat.PlainText)
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        font = self._title.font()
        font.setBold(True)
        self._title.setFont(font)
        self._title.setToolTip(title)
        self.closeButton = QToolButton(self)
        self.closeButton.setAutoRaise(True)
        self.closeButton.setStyleSheet("QToolButton { background: transparent; border: none; }")
        self.closeButton.setIconSize(QSize(16, 16))
        self.closeButton.setFixedSize(30, 30)
        self.closeButton.installEventFilter(self)
        self.closeButton.clicked.connect(lambda: self.dismiss("dismissed"))
        self._header.addWidget(self._icon)
        self._header.addWidget(self._title, 1)
        # Keep a generous close target without turning the heading into a title bar.
        self._header.setContentsMargins(0, 0, self.closeButton.width(), 0)
        self._layout.addLayout(self._header)

        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._scroll.setAutoFillBackground(False)
        self._scroll.viewport().setAutoFillBackground(False)
        body = QWidget()
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(10)
        self._message = QLabel(message)
        self._message.setTextFormat(Qt.TextFormat.PlainText)
        self._message.setWordWrap(True)
        self._message.setMinimumWidth(0)
        message_policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        message_policy.setHeightForWidth(True)
        self._message.setSizePolicy(message_policy)
        self._body_layout.addWidget(self._message)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.hide()
        self._body_layout.addWidget(self._progress_bar)
        self._actions_layout = QVBoxLayout()
        self._actions_layout.setSpacing(6)
        self._body_layout.addLayout(self._actions_layout)
        self._scroll.setWidget(body)
        body.setAutoFillBackground(False)
        self._layout.addWidget(self._scroll)
        for widget in (self._title, self._icon, self._message, body, self._scroll.viewport()):
            widget.installEventFilter(self)
        theme_manager().themeChanged.connect(self._on_theme_changed)
        self._retranslate_ui()
        self._sync_accessibility()
        self._apply_theme()

    def title(self) -> str:
        return self._title.text()

    def setTitle(self, title: str) -> None:
        self._title.setText(title)
        self._title.setToolTip(title)
        self._changed()

    def message(self) -> str:
        return self._message.text()

    def setMessage(self, message: str) -> None:
        self._message.setText(message)
        self._changed()

    def kind(self) -> NotificationKind:
        return self._kind

    def setKind(self, kind: NotificationKind | str) -> None:
        self._kind = NotificationKind(kind)
        self._sync_icon()
        self._changed()

    def setIcon(self, icon: QIcon | None) -> None:
        """Set a custom icon; None restores the severity icon."""
        self._icon_override = QIcon(icon) if icon is not None else None
        self._sync_icon()

    def progress(self) -> int | None:
        return self._progress

    def setProgress(self, value: int | None) -> None:
        """Use 0..100 for progress, -1 for busy, or None to hide the bar."""
        if value is not None and (not isinstance(value, int) or not -1 <= value <= 100):
            raise ValueError("progress must be None or an integer from -1 to 100")
        self._progress = value
        self._progress_bar.setVisible(value is not None)
        if value is not None:
            self._progress_bar.setRange(0, 0 if value == -1 else 100)
            self._sync_progress_tooltip()
            if value >= 0:
                self._progress_bar.setValue(value)
        self._changed()

    def addActionButton(
        self, action_id: str, text: str, *, close_on_trigger: bool = True
    ) -> QPushButton:
        """Add or update an action and return its ordinary QPushButton."""
        if not action_id:
            raise ValueError("action_id must not be empty")
        button = self._buttons.get(action_id)
        if button is None:
            button = QPushButton()
            button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            button.setFocusPolicy(
                Qt.FocusPolicy.NoFocus if self._desktop else Qt.FocusPolicy.StrongFocus
            )
            button.clicked.connect(lambda _checked=False, key=action_id: self._trigger_action(key))
            self._buttons[action_id] = button
            self._actions_layout.addWidget(button)
        button.setText(text)
        button.setToolTip(text)
        self._action_closes[action_id] = close_on_trigger
        self._changed()
        return button

    def removeActionButton(self, action_id: str) -> None:
        button = self._buttons.pop(action_id, None)
        self._action_closes.pop(action_id, None)
        if button is not None:
            self._actions_layout.removeWidget(button)
            button.hide()
            button.deleteLater()
            self._changed()

    def clearActionButtons(self) -> None:
        for key in list(self._buttons):
            self.removeActionButton(key)

    def _trigger_action(self, action_id: str) -> None:
        close = self._action_closes.get(action_id, False)
        self.actionTriggered.emit(action_id)
        if close:
            self.dismiss("action")

    def dismiss(self, reason: str = "dismissed") -> None:
        self._close_reason = reason
        self.close()

    def theme(self) -> ModernTheme:
        if self._theme_override is not None:
            return self._theme_override
        return self._inherited_theme if self._inherited_theme is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        self._theme_override = theme
        self._apply_theme()

    def _on_theme_changed(self, _theme: ModernTheme) -> None:
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.setPalette(palette_for_theme(self.theme(), self.palette()))
        self._sync_close_icon(self.closeButton.underMouse())
        self._sync_progress_style()
        self._sync_icon()
        self.update()

    def _sync_close_icon(self, hovered: bool) -> None:
        self.closeButton.setIcon(
            tinted_icon(
                QIcon(":/pyside6_modern_widgets/icons/close.svg"),
                self.theme().text if hovered else self.theme().text_muted,
            )
        )

    def _sync_progress_style(self) -> None:
        accent = self.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent).name()
        self._progress_bar.setStyleSheet(
            f"QProgressBar {{ border: 0; border-radius: 3px; background: {self.theme().border}; }}"
            f"QProgressBar::chunk {{ border-radius: 3px; background: {accent}; }}"
        )

    def _sync_icon(self) -> None:
        if self._icon_override is not None:
            icon = self._icon_override
        else:
            pixmap = {
                NotificationKind.INFO: QStyle.StandardPixmap.SP_MessageBoxInformation,
                NotificationKind.SUCCESS: QStyle.StandardPixmap.SP_DialogApplyButton,
                NotificationKind.WARNING: QStyle.StandardPixmap.SP_MessageBoxWarning,
                NotificationKind.ERROR: QStyle.StandardPixmap.SP_MessageBoxCritical,
            }[self._kind]
            icon = self.style().standardIcon(pixmap)
        self._icon.setPixmap(icon.pixmap(self._icon.size(), self.devicePixelRatioF()))

    def _sync_accessibility(self) -> None:
        if self._kind == NotificationKind.INFO:
            kind = self.tr("Information")
        elif self._kind == NotificationKind.SUCCESS:
            kind = self.tr("Success")
        elif self._kind == NotificationKind.WARNING:
            kind = self.tr("Warning")
        else:
            kind = self.tr("Error")
        name = self.tr("%1: %2").replace("%1", kind).replace("%2", self.title())
        self.setAccessibleName(name)
        self.setAccessibleDescription(self.message())

    def _sync_progress_tooltip(self) -> None:
        if self._progress == -1:
            self._progress_bar.setToolTip(self.tr("Working…"))
        elif self._progress is not None:
            self._progress_bar.setToolTip(self.tr("%1%").replace("%1", str(self._progress)))

    def _retranslate_ui(self) -> None:
        self.closeButton.setAccessibleName(self.tr("Dismiss notification"))
        self.closeButton.setToolTip(self.tr("Dismiss"))
        self._progress_bar.setAccessibleName(self.tr("Progress"))
        self._sync_progress_tooltip()
        self._sync_accessibility()

    def _changed(self) -> None:
        self._sync_accessibility()
        self.updateGeometry()
        self.contentChanged.emit()

    def _configure_desktop(self) -> None:
        self._desktop = True
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.closeButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for button in self._buttons.values():
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _fit_size(self, width: int, max_height: int) -> QSize:
        self.ensurePolished()
        self.setFixedWidth(width)
        margins = self._layout.contentsMargins()
        inner_width = max(1, width - margins.left() - margins.right())
        # Reserve the scrollbar width during measurement so its appearance
        # cannot clip wrapped text or create a size oscillation.
        text_width = max(1, inner_width - self._scroll.verticalScrollBar().sizeHint().width())
        self._message.setVisible(bool(self.message()))
        self._body_layout.invalidate()
        body_height = self._body_layout.totalHeightForWidth(text_width)
        if body_height < 0:
            body_height = self._body_layout.sizeHint().height()
        body_height = max(0, body_height)
        header_height = self._header.sizeHint().height()
        chrome_height = margins.top() + margins.bottom() + header_height
        if body_height:
            chrome_height += self._layout.spacing()
        body_height = min(body_height, max(0, max_height - chrome_height))
        self._scroll.setVisible(body_height > 0)
        self._scroll.setFixedHeight(body_height)
        size = QSize(width, min(max_height, chrome_height + body_height))
        self.resize(size)
        self._layout.activate()
        return size

    def sizeHint(self) -> QSize:
        if not hasattr(self, "_body_layout"):
            return super().sizeHint()
        height = self._body_layout.totalHeightForWidth(310)
        if height < 0:
            height = self._body_layout.sizeHint().height()
        margins = self._layout.contentsMargins()
        chrome_height = (
            margins.top()
            + margins.bottom()
            + self._header.sizeHint().height()
            + self._layout.spacing()
        )
        return QSize(360, min(360, max(80, height + chrome_height)))

    def minimumSizeHint(self) -> QSize:
        return QSize(120, 80)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.closeButton.move(self.width() - self.closeButton.width() - 6, 6)
        self.closeButton.raise_()

    def _move_to(self, point: QPoint, animate: bool) -> None:
        if (
            self._move_animation.endValue() == point
            and self._move_animation.state() == QPropertyAnimation.State.Running
        ):
            return
        self._move_animation.stop()
        if animate and self.isVisible() and self._metrics.animation_duration > 0:
            self._move_animation.setStartValue(self.pos())
            self._move_animation.setEndValue(point)
            self._move_animation.start()
        else:
            self.move(point)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.closeButton:
            if event.type() == QEvent.Type.Enter:
                self._sync_close_icon(True)
            elif event.type() == QEvent.Type.Leave:
                self._sync_close_icon(False)
            return super().eventFilter(watched, event)
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._pressed = True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            pressed, self._pressed = self._pressed, False
            if (
                pressed
                and event.button() == Qt.MouseButton.LeftButton
                and watched.rect().contains(event.position().toPoint())
            ):
                self.activated.emit()
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event) -> None:
        self._pressed = event.button() == Qt.MouseButton.LeftButton
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        pressed, self._pressed = self._pressed, False
        if (
            pressed
            and event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.activated.emit()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:
        self.hoveredChanged.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.hoveredChanged.emit(False)
        super().leaveEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        if event.isAccepted() and not self._dismissed:
            self._dismissed = True
            self._move_animation.stop()
            self.dismissed.emit(self._close_reason)

    def showEvent(self, event) -> None:
        self._dismissed = False
        super().showEvent(event)
        self._connect_screen_change_signal()
        self._native_dpi.sync_window(self)
        self._refresh_surface()
        self._schedule_display_refresh()

    def hideEvent(self, event) -> None:
        self._surface_refresh_timer.stop()
        self._surface_settle_timer.stop()
        self._disconnect_screen_change_signal()
        super().hideEvent(event)

    def event(self, event) -> bool:
        handled = super().event(event)
        if (
            hasattr(self, "_surface_refresh_timer")
            and event.type() == QEvent.Type.DevicePixelRatioChange
        ):
            self._schedule_display_refresh()
        return handled

    def nativeEvent(self, event_type, message):
        if not hasattr(self, "_native_dpi"):
            return super().nativeEvent(event_type, message)
        previous_dpi = self._native_dpi.dpi
        handled = self._native_dpi.handle_native_event(self, message)
        if self._native_dpi.dpi != previous_dpi:
            self._schedule_display_refresh()
        if handled:
            return True, 0
        return super().nativeEvent(event_type, message)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if hasattr(self, "_progress_bar") and event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        if hasattr(self, "_body_layout") and event.type() in (
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
            QEvent.Type.LayoutDirectionChange,
        ):
            self._sync_icon()
            self._changed()
        if (
            hasattr(self, "_metrics")
            and self.isVisible()
            and event.type() == QEvent.Type.PaletteChange
        ):
            self._sync_progress_style()
            self._refresh_surface()

    def _connect_screen_change_signal(self) -> None:
        window_handle = self.windowHandle()
        if window_handle is None or window_handle is self._screen_change_window:
            return
        self._disconnect_screen_change_signal()
        self._screen_change_window = window_handle
        window_handle.screenChanged.connect(self._handle_screen_changed)

    def _disconnect_screen_change_signal(self) -> None:
        window_handle = self._screen_change_window
        self._screen_change_window = None
        if window_handle is not None:
            try:
                window_handle.screenChanged.disconnect(self._handle_screen_changed)
            except (RuntimeError, TypeError):
                pass

    def _handle_screen_changed(self, _screen) -> None:
        self._schedule_display_refresh()

    def _schedule_display_refresh(self) -> None:
        self._surface_refresh_timer.start(0)
        self._surface_settle_timer.start(100)

    def _refresh_after_display_change(self) -> None:
        if not self.isVisible():
            return
        self._native_dpi.sync_window(self)
        self._sync_icon()
        self.updateGeometry()
        self._refresh_surface()
        # The manager must measure the card again after Qt adopts the target DPR.
        self.contentChanged.emit()

    def _refresh_surface(self) -> None:
        self._native_corners = self._desktop and _enable_windows_rounded_corners(
            self, self._metrics.corner_radius
        )
        self._native_acrylic = self._native_corners and _enable_windows_acrylic(self)
        self.repaint()
        window_handle = self.windowHandle()
        if window_handle is not None:
            window_handle.requestUpdate()
            if self._desktop and uses_windows_window_state():
                redraw_native_window(int(window_handle.winId()))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        surface = _surface_color(self.palette(), self)
        surface.setAlpha(1 if self._native_acrylic else 255)
        if self._native_corners:
            # DWM clips and outlines the native surface. A second rounded stroke
            # has a different radius and produces doubled, uneven corner edges.
            painter.fillRect(self.rect(), surface)
            return
        painter.setBrush(surface)
        painter.setPen(QPen(_soft_line_color(self.palette(), 30), 1))
        radius = self._metrics.corner_radius
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
