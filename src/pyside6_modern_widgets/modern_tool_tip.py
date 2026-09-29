"""Opt-in, application-wide tooltips without replacing the application's style."""

from __future__ import annotations

import math
import time
import weakref

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QRectF, QThread, QTimer
from PySide6.QtGui import (
    QAbstractTextDocumentLayout,
    QColor,
    QCursor,
    QPainter,
    QPalette,
    QPen,
    Qt,
    QTextDocument,
    QTextOption,
)
from PySide6.QtWidgets import QApplication, QToolTip, QWidget
from shiboken6 import isValid

from ._theme_binding import ThemeBinding
from .modern_menu import _enable_windows_acrylic, _enable_windows_rounded_corners, _soft_line_color
from .theme import ModernTheme, inherited_theme, palette_for_theme, theme_manager


class _ToolTipWindow(QWidget):
    _RADIUS = 4
    _PADDING_X = 10
    _PADDING_Y = 8

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._owner: weakref.ReferenceType[QWidget] | None = None
        self._native_acrylic = False
        self._document = QTextDocument(self)
        self._document.setDocumentMargin(0)
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self._document.setDefaultTextOption(option)
        self._apply_theme()
        self._binding = ThemeBinding(self, self.theme, self._apply_theme, source=self.owner)

    def owner(self) -> QWidget | None:
        owner = self._owner() if self._owner else None
        return owner if owner is not None and isValid(owner) else None

    def setOwner(self, owner: QWidget | None) -> None:
        if (owner is None and self._owner is None) or (owner is not None and owner is self.owner()):
            return
        self._owner = weakref.ref(owner) if owner is not None else None
        self._binding.rebind()

    def theme(self) -> ModernTheme:
        owner = self.owner()
        if owner is None:
            return theme_manager().theme()
        getter = getattr(owner, "theme", None)
        theme = getter() if callable(getter) else None
        return theme if isinstance(theme, ModernTheme) else inherited_theme(owner)

    def _apply_theme(self) -> None:
        theme = self.theme()
        palette = palette_for_theme(theme)
        palette.setColor(QPalette.ColorRole.Window, QColor(theme.tooltip_surface))
        self.setPalette(palette)
        if self.isVisible():
            self._refresh_surface()
        self.update()

    def _refresh_surface(self) -> None:
        self._native_acrylic = _enable_windows_rounded_corners(
            self, self._RADIUS, small=True
        ) and _enable_windows_acrylic(self)

    def present(self, owner: QWidget, position: QPoint, max_width: int) -> None:
        self.setOwner(owner)
        self.setLayoutDirection(owner.layoutDirection())
        self._document.setDefaultFont(QToolTip.font())
        option = self._document.defaultTextOption()
        option.setTextDirection(owner.layoutDirection())
        self._document.setDefaultTextOption(option)
        text = owner.toolTip()
        if Qt.mightBeRichText(text):
            self._document.setHtml(text)
        else:
            self._document.setPlainText(text)
        self.setAccessibleName(self._document.toPlainText())
        screen = QApplication.screenAt(position) or owner.screen()
        area = screen.availableGeometry().adjusted(4, 4, -4, -4)
        self._document.setTextWidth(-1)
        horizontal_padding = 2 * self._PADDING_X
        vertical_padding = 2 * self._PADDING_Y
        width = max(1, min(max_width - horizontal_padding, area.width() - horizontal_padding))
        self._document.setTextWidth(min(width, math.ceil(self._document.idealWidth())))
        size = self._document.size().toSize()
        size.setWidth(min(area.width(), size.width() + horizontal_padding))
        size.setHeight(
            min(area.height(), math.ceil(self._document.size().height()) + vertical_padding)
        )
        rect = QRect(position + QPoint(16, 20), size)
        if rect.bottom() > area.bottom():
            rect.moveBottom(position.y() - 8)
        rect.moveLeft(max(area.left(), min(rect.left(), area.right() - rect.width() + 1)))
        rect.moveTop(max(area.top(), min(rect.top(), area.bottom() - rect.height() + 1)))
        # Choose the cursor's screen before showing, including mixed-DPI desktops.
        self.winId()
        handle = self.windowHandle()
        if handle is not None:
            handle.setScreen(screen)
            owner_handle = owner.window().windowHandle()
            if owner_handle is not None:
                handle.setTransientParent(owner_handle)
        self.setGeometry(rect)
        self._refresh_surface()
        self.show()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        surface = self.palette().color(QPalette.ColorRole.Window)
        surface.setAlpha(1 if self._native_acrylic else 255)
        painter.setBrush(surface)
        painter.setPen(QPen(_soft_line_color(self.palette(), 30), 1))
        painter.drawRoundedRect(
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), self._RADIUS, self._RADIUS
        )
        painter.translate(self._PADDING_X, self._PADDING_Y)
        painter.setClipRect(
            QRectF(0, 0, self.width() - 2 * self._PADDING_X, self.height() - 2 * self._PADDING_Y)
        )
        context = QAbstractTextDocumentLayout.PaintContext()
        context.palette = self.palette()  # type: ignore[attr-defined]  # Missing in Qt's stub.
        self._document.documentLayout().draw(painter, context)


class ModernToolTip(QObject):
    """Install once to modernize ordinary QWidget.setToolTip() tooltips.

    Delays are milliseconds; max_width is in Qt logical pixels. Item-view model
    tooltips and custom QToolTip.showText() calls retain their native behavior.
    Repeated install() calls update the existing controller. uninstall() restores
    native delivery without changing widget text or the application style.
    """

    _instance: ModernToolTip | None = None

    @classmethod
    def install(
        cls, *, delay_ms: int = 300, reshow_delay_ms: int = 100, max_width: int = 360
    ) -> ModernToolTip:
        app = QApplication.instance()
        if not isinstance(app, QApplication) or QThread.currentThread() != app.thread():
            raise RuntimeError("Install ModernToolTip on the QApplication GUI thread")
        for name, value, minimum in (
            ("delay_ms", delay_ms, 0),
            ("reshow_delay_ms", reshow_delay_ms, 0),
            ("max_width", max_width, 48),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an integer")
            if not minimum <= value <= 2_147_483_647:
                raise ValueError(f"{name} must be between {minimum} and 2147483647")
        manager = cls._instance
        if manager is None or not isValid(manager):
            manager = cls(app)
            cls._instance = manager
            app.installEventFilter(manager)
            app.aboutToQuit.connect(cls.uninstall)
        manager._delay = delay_ms
        manager._reshow_delay = reshow_delay_ms
        manager._max_width = max_width
        manager._cancel()
        return manager

    @classmethod
    def uninstall(cls) -> None:
        manager = cls._instance
        if manager is None or not isValid(manager):
            cls._instance = None
            return
        app = QApplication.instance()
        if app is not None and QThread.currentThread() != app.thread():
            raise RuntimeError("Uninstall ModernToolTip on the QApplication GUI thread")
        cls._instance = None
        if app is not None:
            app.removeEventFilter(manager)
            app.aboutToQuit.disconnect(cls.uninstall)
        manager._cancel()
        manager._popup.deleteLater()
        manager.deleteLater()

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._popup = _ToolTipWindow()
        self._target: weakref.ReferenceType[QWidget] | None = None
        self._hover: weakref.ReferenceType[QWidget] | None = None
        self._restore_hover = False
        self._position = QPoint()
        self._warm_until = 0.0
        self._dismissed = False
        self._delay, self._reshow_delay, self._max_width = 300, 100, 360
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._show_pending)
        self._expiry = QTimer(self)
        self._expiry.setSingleShot(True)
        self._expiry.timeout.connect(self._dismiss)

    def _target_widget(self) -> QWidget | None:
        target = self._target() if self._target else None
        return target if target is not None and isValid(target) else None

    @staticmethod
    def _tooltip_owner(widget: QWidget | None) -> QWidget | None:
        while widget is not None:
            if widget.toolTip():
                return widget
            if widget.isWindow():
                break
            widget = widget.parentWidget()
        return None

    @staticmethod
    def _allowed(owner: QWidget) -> bool:
        if not owner.isVisible() or QApplication.mouseButtons() != Qt.MouseButton.NoButton:
            return False
        modal = QApplication.activeModalWidget()
        if modal is not None and owner.window() is not modal:
            return False
        active = QApplication.activeWindow()
        return (
            owner.window() is active
            or owner.window().windowType() == Qt.WindowType.Popup
            or owner.window().testAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips)
        )

    def _dismiss(self) -> None:
        self._timer.stop()
        self._expiry.stop()
        if self._popup.isVisible():
            self._warm_until = time.monotonic() + 1.0
        self._popup.hide()
        self._popup.setOwner(None)
        self._dismissed = True

    def _cancel(self) -> None:
        self._dismiss()
        hover = self._hover() if self._hover else None
        if hover is not None and isValid(hover) and self._restore_hover:
            hover.setAttribute(Qt.WidgetAttribute.WA_Hover, False)
        target = self._target_widget()
        if target is not None:
            target.destroyed.disconnect(self._target_destroyed)
        self._target = self._hover = None
        self._restore_hover = False

    def _target_destroyed(self) -> None:
        self._target = None
        self._cancel()

    def _track(self) -> None:
        position = QCursor.pos()
        hover = QApplication.widgetAt(position)
        owner = self._tooltip_owner(hover)
        if hover is None or owner is None or not self._allowed(owner):
            self._cancel()
            return
        previous_hover = self._hover() if self._hover else None
        changed = owner is not self._target_widget() or hover is not previous_hover
        moved = position != self._position
        if changed:
            self._cancel()
            self._target = weakref.ref(owner)
            owner.destroyed.connect(self._target_destroyed)
            self._hover = weakref.ref(hover)
            self._restore_hover = not hover.testAttribute(Qt.WidgetAttribute.WA_Hover)
            hover.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._position = position
        if self._popup.isVisible():
            return
        if changed or moved:
            self._dismissed = False
            delay = self._reshow_delay if time.monotonic() < self._warm_until else self._delay
            self._timer.start(delay)

    def _show_pending(self) -> None:
        owner = self._target_widget()
        if (
            owner is None
            or self._dismissed
            or not self._allowed(owner)
            or self._tooltip_owner(QApplication.widgetAt(QCursor.pos())) is not owner
        ):
            self._cancel()
            return
        QToolTip.hideText()
        self._popup.present(owner, self._position, self._max_width)
        duration = owner.toolTipDuration()
        if duration < 0:
            duration = 10_000 + 40 * max(0, len(self._popup.accessibleName()) - 100)
        self._expiry.start(min(duration, 2_147_483_647))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ApplicationDeactivate:
            self._dismiss()
            return False
        if watched is self._popup or not isinstance(watched, QWidget):
            return False
        kind = event.type()
        if kind == QEvent.Type.ToolTip and self._tooltip_owner(watched) is not None:
            # Native wakeup must not create a second popup or revive an expired one.
            event.accept()
            return True
        if kind in (QEvent.Type.Enter, QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            self._track()
        elif kind == QEvent.Type.Leave:
            hover = self._hover() if self._hover else None
            if watched is hover:
                self._cancel()
        elif kind in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel,
            QEvent.Type.WindowDeactivate,
        ):
            self._dismiss()
        elif kind in (
            QEvent.Type.Hide,
            QEvent.Type.Close,
            QEvent.Type.ParentChange,
            QEvent.Type.Move,
            QEvent.Type.Resize,
        ):
            owner = self._target_widget()
            if owner is not None and (watched is owner or watched.isAncestorOf(owner)):
                self._cancel()
        elif kind == QEvent.Type.ToolTipChange and watched is self._target_widget():
            if not watched.toolTip():
                self._cancel()
            elif self._popup.isVisible():
                self._popup.present(watched, self._position, self._max_width)
        return False
