"""A QToolBar with modern controls and an accessible, themed overflow menu."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QPainter, QPen
from PySide6.QtWidgets import QProxyStyle, QStyle, QToolBar, QToolButton, QWidget, QWidgetAction

from .modern_menu import ModernMenu
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    inherited_theme,
    palette_for_theme,
    theme_manager,
    tinted_icon,
)


class _ToolBarStyle(QProxyStyle):
    def __init__(self, toolbar: ModernToolBar) -> None:
        super().__init__(toolbar.style().name() or "fusion")
        self.setParent(toolbar)
        self._toolbar = toolbar

    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if element == QStyle.PrimitiveElement.PE_PanelToolBar:
            return
        if isinstance(widget, QToolButton):
            theme = self._toolbar.theme()
            if element in (
                QStyle.PrimitiveElement.PE_PanelButtonTool,
                QStyle.PrimitiveElement.PE_PanelButtonCommand,
                QStyle.PrimitiveElement.PE_PanelButtonBevel,
                QStyle.PrimitiveElement.PE_IndicatorButtonDropDown,
            ):
                # Paint inside the native button rectangle; never change layout
                # metrics or the separate menu-arrow subcontrol's hit region.
                state = option.state
                color = None
                if state & QStyle.StateFlag.State_Enabled:
                    if state & (QStyle.StateFlag.State_Sunken | QStyle.StateFlag.State_On):
                        color = theme.control_pressed
                    elif state & QStyle.StateFlag.State_MouseOver:
                        color = theme.control_hover
                if color is not None:
                    painter.save()
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(color))
                    painter.drawRoundedRect(
                        QRectF(option.rect),
                        self._toolbar._metrics.control_radius,
                        self._toolbar._metrics.control_radius,
                    )
                    painter.restore()
                if element == QStyle.PrimitiveElement.PE_IndicatorButtonDropDown:
                    self.drawPrimitive(
                        QStyle.PrimitiveElement.PE_IndicatorArrowDown, option, painter, widget
                    )
                return
            if element == QStyle.PrimitiveElement.PE_IndicatorArrowDown:
                # Native Windows arrows can use an opaque theme bitmap on a
                # transparent toolbar. Keep the native rect, paint a themed glyph.
                color = theme.text_muted if widget.isEnabled() else theme.text_disabled
                center = QRectF(option.rect).center()
                painter.save()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setPen(
                    QPen(
                        QColor(color),
                        1.2,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin,
                    )
                )
                painter.drawLine(center + QPointF(-2.5, -1.5), center + QPointF(0, 1))
                painter.drawLine(center + QPointF(0, 1), center + QPointF(2.5, -1.5))
                painter.restore()
                return
        super().drawPrimitive(element, option, painter, widget)


class ModernToolBar(QToolBar):
    """Accept ``(parent)`` or ``(title, parent)`` and retain Qt's action/docking API.

    Overflow uses the original QActions, retaining shortcuts, checked states,
    submenus and signals. Use QWidgetAction.createWidget() for controls that need
    a second instance in the popup; addWidget() controls remain in the toolbar.
    """

    def __init__(
        self,
        title: str | QWidget | None = None,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        if isinstance(title, QWidget):
            if parent is not None:
                raise TypeError("parent specified twice")
            parent, title = title, None
        elif title is not None and not isinstance(title, str):
            raise TypeError("title must be a string or QWidget parent")
        if title is None:
            super().__init__(parent)
        else:
            super().__init__(title, parent)
        self._metrics = metrics
        self._theme_override = theme
        self._styled_theme: ModernTheme | None = None
        self._applying_theme = False
        self._modern_style = _ToolBarStyle(self)
        self.setStyle(self._modern_style)
        extension = self.findChild(QToolButton, "qt_toolbar_ext_button")
        if extension is None:
            raise RuntimeError("Qt toolbar extension button is unavailable")
        self._extension: QToolButton = extension
        self._retranslate_ui()
        # A toolbar stylesheet would intercept ModernMenu's proxy-style drawing.
        # Own the popup through the window, and also clean it up with the toolbar.
        self._overflow: ModernMenu = ModernMenu(self._menu_owner(), metrics=metrics)
        self.destroyed.connect(self._overflow.deleteLater)
        self._extension.setMenu(self._overflow)
        self._extension.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._overflow.aboutToShow.connect(self._sync_overflow)
        self._update_timer: QTimer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._sync_overflow)
        self.orientationChanged.connect(self._schedule_update)
        self.iconSizeChanged.connect(self._schedule_update)
        theme_manager().themeChanged.connect(self._on_theme_changed)
        self._apply_theme()

    def _retranslate_ui(self) -> None:
        text = self.tr("More actions")
        self._extension.setToolTip(text)
        self._extension.setAccessibleName(text)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override colors locally; None restores ancestor/global inheritance."""
        self._theme_override = theme
        self._apply_theme()

    def overflowMenu(self) -> ModernMenu:
        """Return the popup; its contents are managed from hidden toolbar actions."""
        return self._overflow

    def overflowButton(self) -> QToolButton:
        """Return the extension button, e.g. to customize its tooltip."""
        return self._extension

    def _menu_owner(self) -> QWidget | None:
        window = self.window()
        return window if window is not self else None

    def _on_theme_changed(self, _theme: ModernTheme) -> None:
        self._apply_theme()

    def _apply_theme(self) -> None:
        if self._applying_theme:
            return
        self._applying_theme = True
        try:
            theme = self.theme()
            if theme != self._styled_theme:
                self._styled_theme = theme
                self.setPalette(palette_for_theme(theme, self.palette()))
            owner = self._menu_owner()
            if self._overflow.parentWidget() is not owner:
                self._overflow.setParent(owner, self._overflow.windowFlags())
            self._overflow.setPalette(self.palette())
            self._style_buttons()
            self._update_extension_icon()
        finally:
            self._applying_theme = False

    def _style_buttons(self) -> None:
        buttons = [self._extension]
        for action in self.actions():
            # Leave caller-supplied addWidget()/QWidgetAction controls untouched.
            if not isinstance(action, QWidgetAction):
                button = self.widgetForAction(action)
                if isinstance(button, QToolButton):
                    buttons.append(button)
        for button in buttons:
            if getattr(button, "_modern_toolbar_style", None) is not self._modern_style:
                button.setStyle(self._modern_style)
                button._modern_toolbar_style = self._modern_style  # type: ignore[attr-defined]
            button.update()

    def _update_extension_icon(self) -> None:
        state = (self.palette().cacheKey(), self.orientation(), self.layoutDirection())
        if state == getattr(self, "_icon_state", None):
            return
        self._icon_state = state
        standard = (
            QStyle.StandardPixmap.SP_ToolBarVerticalExtensionButton
            if self.orientation() == Qt.Orientation.Vertical
            else QStyle.StandardPixmap.SP_ToolBarHorizontalExtensionButton
        )
        icon = self._modern_style.standardIcon(standard, None, self._extension)
        self._extension.setIcon(tinted_icon(icon, self.theme().text_muted))

    def _schedule_update(self, *_args) -> None:
        self._update_timer.start(0)

    def _sync_overflow(self) -> None:
        self._apply_theme()
        # QToolBarLayout keeps filling its original private QMenu even after
        # setMenu(). Populate our popup from the settled toolbar layout instead.
        actions: list[QAction] = []
        separator = None
        for action in self.actions():
            if not action.isVisible():
                continue
            if action.isSeparator():
                separator = action
                continue
            widget = self.widgetForAction(action)
            if widget is None or not widget.isHidden():
                continue
            if isinstance(action, QWidgetAction) and action.defaultWidget() is not None:
                continue
            if separator is not None and actions:
                actions.append(separator)
            separator = None
            actions.append(action)
        if actions != self._overflow.actions():
            active = self._overflow.activeAction()
            # QMenu.clear() can invalidate PySide wrappers for shared actions.
            # Detach individually so toolbar owners and callers keep valid QActions.
            for previous in self._overflow.actions():
                self._overflow.removeAction(previous)
            self._overflow.addActions(actions)
            if active in actions:
                self._overflow.setActiveAction(active)
        # Native QMainWindow docking may otherwise switch the extension to an
        # expanding toolbar panel. Both embedding modes use the same popup here.
        if self._extension.menu() is not self._overflow:
            self._extension.setMenu(self._overflow)
        if self._extension.popupMode() != QToolButton.ToolButtonPopupMode.InstantPopup:
            self._extension.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

    def event(self, event) -> bool:
        handled = super().event(event)
        if hasattr(self, "_update_timer"):
            if event.type() == QEvent.Type.LanguageChange:
                self._retranslate_ui()
            if event.type() in (
                QEvent.Type.ParentChange,
                QEvent.Type.PaletteChange,
                QEvent.Type.LayoutDirectionChange,
            ):
                self._apply_theme()
            if event.type() == QEvent.Type.ActionAdded:
                self._style_buttons()
            if event.type() in (
                QEvent.Type.LayoutRequest,
                QEvent.Type.Resize,
                QEvent.Type.Show,
                QEvent.Type.ActionAdded,
                QEvent.Type.ActionRemoved,
                QEvent.Type.ActionChanged,
                QEvent.Type.ParentChange,
                QEvent.Type.StyleChange,
            ):
                self._schedule_update()
        return handled
