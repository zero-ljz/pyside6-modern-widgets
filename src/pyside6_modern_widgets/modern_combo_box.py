"""Modern rounded painting over Qt's native combo box behavior."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QStyle,
    QStyleOption,
    QStyleOptionViewItem,
    QWidget,
)

from .modern_menu import (
    _MENU_ITEM_EXTRA_HEIGHT,
    _enable_windows_acrylic,
    _enable_windows_rounded_corners,
    _RoundedMenuStyle,
    _supports_windows_acrylic,
)
from .theme import DEFAULT_METRICS, ModernMetrics, ModernTheme, palette_for_theme, theme_manager


class _ComboBoxStyle(_RoundedMenuStyle):
    """Change presentation without replacing Qt's popup, delegate or input handling."""

    def __init__(self, combo: ModernComboBox) -> None:
        # Own a separate style; passing QApplication.style() transfers ownership.
        super().__init__(combo._metrics.control_radius, "Fusion")
        # Match the acrylic popup's Qt surface to DWMWCP_ROUND's 8-DIP
        # outer corner. The closed control keeps the normal control radius.
        if self._radius > 0 and _supports_windows_acrylic():
            self._surface_radius = 8
        self.setParent(combo)
        self._combo = combo

    def sizeFromContents(self, content_type, option, size, widget=None):
        result = super().sizeFromContents(content_type, option, size, widget)
        if content_type == QStyle.ContentsType.CT_ComboBox:
            result.setHeight(result.height() + 2)
        if content_type == QStyle.ContentsType.CT_ItemViewItem:
            result.setHeight(result.height() + _MENU_ITEM_EXTRA_HEIGHT)
        return result

    def drawComplexControl(self, control, option, painter, widget=None) -> None:
        if control != QStyle.ComplexControl.CC_ComboBox:
            super().drawComplexControl(control, option, painter, widget)
            return
        if not option.frame:
            super().drawComplexControl(control, option, painter, widget)
            return
        theme = self._combo.theme()
        radius = self._radius
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        pressed = bool(option.state & QStyle.StateFlag.State_On)
        # Fusion treats an editable combo as a line edit (any focus), while
        # its non-editable button only highlights keyboard focus.
        focused = (
            enabled
            and bool(option.state & QStyle.StateFlag.State_HasFocus)
            and (option.editable or bool(option.state & QStyle.StateFlag.State_KeyboardFocusChange))
        )
        border_width = 2 if focused else 1
        inset = border_width / 2
        rect = QRectF(option.rect).adjusted(inset, inset, -inset, -inset)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        surface_role = QPalette.ColorRole.Base if option.editable else QPalette.ColorRole.Button
        painter.setBrush(option.palette.brush(surface_role))
        painter.drawRoundedRect(rect, radius, radius)
        if enabled and (pressed or option.state & QStyle.StateFlag.State_MouseOver):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.control_pressed if pressed else theme.control_hover))
            painter.drawRoundedRect(rect, radius, radius)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        border = option.palette.color(QPalette.ColorRole.Mid)
        if focused:
            # Match QFusionStylePrivate::highlightedOutline: inherit Qt's
            # current highlight role, including system accent/palette changes.
            border = option.palette.color(QPalette.ColorRole.Highlight).darker(125)
            if border.value() > 160:
                border.setHsl(border.hue(), border.saturation(), 160)
        painter.setPen(QPen(border, border_width))
        painter.drawRoundedRect(rect, radius, radius)

        if not option.subControls & QStyle.SubControl.SC_ComboBoxArrow:
            painter.restore()
            return
        arrow = self.subControlRect(
            control, option, QStyle.SubControl.SC_ComboBoxArrow, widget
        ).center()
        pen = QPen(option.palette.color(QPalette.ColorRole.ButtonText), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath(QPointF(arrow.x() - 4, arrow.y() - 2))
        path.lineTo(arrow.x(), arrow.y() + 2)
        path.lineTo(arrow.x() + 4, arrow.y() - 2)
        painter.drawPath(path)
        painter.restore()

    def drawControl(self, element, option, painter, widget=None) -> None:
        if element == QStyle.ControlElement.CE_MenuEmptyArea:
            return
        if element == QStyle.ControlElement.CE_ItemViewItem:
            item = QStyleOptionViewItem(option)
            palette = QPalette(option.palette)
            palette.setColor(
                QPalette.ColorRole.HighlightedText, palette.color(QPalette.ColorRole.Text)
            )
            item.palette = palette  # type: ignore[attr-defined]
            # The rounded selection background provides keyboard focus feedback.
            item.state &= ~QStyle.StateFlag.State_HasFocus  # type: ignore[attr-defined]
            super().drawControl(element, item, painter, widget)
            return
        super().drawControl(element, option, painter, widget)

    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if element == QStyle.PrimitiveElement.PE_PanelItemViewItem and option.state & (
            QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_MouseOver
        ):
            self.drawSelection(option, painter, widget)
            return
        super().drawPrimitive(element, option, painter, widget)


class ModernComboBox(QComboBox):
    """A ``QComboBox`` with rounded surfaces and native Qt semantics.

    Models, delegates, signals, editing, completion and popup input remain owned
    by Qt. ``setTheme(None)`` restores the containing modern widget's theme, or
    the global theme when there is no themed ancestor.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        super().__init__(parent)
        self._metrics = metrics
        self._theme_override = theme
        self._styled_theme: ModernTheme | None = None
        self._applying_theme = False
        self._palette_override = QPalette()
        self._theme_ancestors: list[QWidget] = []
        self._popup: QWidget | None = None
        self._modern_style = _ComboBoxStyle(self)
        self.setStyle(self._modern_style)
        # Configure only Qt's initial list, once. A caller-supplied view and any
        # later changes to this list retain their own style, frame and palette.
        view = self.view()
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setAutoFillBackground(False)
        view.viewport().setAutoFillBackground(False)
        view.setStyle(self._modern_style)
        view_palette = QPalette()
        view_palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        view.setPalette(view_palette)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        theme_manager().themeChanged.connect(self._on_theme_changed)
        self._watch_theme_ancestors()
        self._apply_theme()

    def theme(self) -> ModernTheme:
        if self._theme_override is not None:
            return self._theme_override
        ancestor = self.parentWidget()
        while ancestor is not None:
            get_theme = getattr(ancestor, "theme", None)
            if callable(get_theme):
                inherited = get_theme()
                if isinstance(inherited, ModernTheme):
                    return inherited
            ancestor = ancestor.parentWidget()
        return theme_manager().theme()

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override the theme locally, or pass None to resume inheritance."""
        self._theme_override = theme
        self._apply_theme()

    def _on_theme_changed(self, _theme: ModernTheme) -> None:
        self._apply_theme()

    def setPalette(self, palette: QPalette | Qt.GlobalColor | QColor) -> None:
        if not hasattr(self, "_palette_override"):
            super().setPalette(palette)
            return
        self._palette_override = QPalette(palette)
        self._apply_theme()

    def _watch_theme_ancestors(self) -> None:
        for previous in self._theme_ancestors:
            previous.removeEventFilter(self)
        self._theme_ancestors.clear()
        ancestor = self.parentWidget()
        while ancestor is not None:
            ancestor.installEventFilter(self)
            self._theme_ancestors.append(ancestor)
            ancestor = ancestor.parentWidget()

    def eventFilter(self, watched, event) -> bool:
        if watched is self._popup:
            if event.type() == QEvent.Type.Paint:
                # Paint exactly one menu surface. The native container's frame
                # painting would otherwise add a second border over the acrylic.
                option = QStyleOption()
                option.initFrom(self._popup)
                painter = QPainter(self._popup)
                self._modern_style.drawPrimitive(
                    QStyle.PrimitiveElement.PE_PanelMenu, option, painter, self._popup
                )
                painter.end()
                return True
            if event.type() == QEvent.Type.Show or (
                event.type() == QEvent.Type.PaletteChange and self._popup.isVisible()
            ):
                self._refresh_popup_acrylic()
        if watched in self._theme_ancestors:
            if event.type() == QEvent.Type.ParentChange:
                self._watch_theme_ancestors()
            if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ParentChange):
                self._apply_theme()
        return super().eventFilter(watched, event)

    def _refresh_popup_acrylic(self) -> None:
        if self._popup is None:
            return
        self._modern_style.setNativeAcrylic(
            _enable_windows_rounded_corners(self._popup, self._metrics.control_radius)
            and _enable_windows_acrylic(self._popup)
        )
        self._popup.update()

    def _apply_theme(self) -> None:
        if self._applying_theme:
            return
        self._applying_theme = True
        try:
            self._styled_theme = self.theme()
            themed = palette_for_theme(self._styled_theme, self.palette())
            palette = self._palette_override.resolve(themed)
            palette.setResolveMask(self._palette_override.resolveMask() | themed.resolveMask())
            super().setPalette(palette)
            # Qt snapshots the container palette when opening; keep the owned
            # acrylic surface in sync without assigning a palette to the view.
            self.view().window().setPalette(self.palette())
            self.update()
            self.view().viewport().update()
            self.view().window().update()
        finally:
            self._applying_theme = False

    def event(self, event) -> bool:
        handled = super().event(event)
        if hasattr(self, "_styled_theme") and event.type() == QEvent.Type.ParentChange:
            self._watch_theme_ancestors()
            self._apply_theme()
        return handled

    def showPopup(self) -> None:
        view = self.view()
        popup = view.window()
        if popup is not self._popup:
            if self._popup is not None:
                self._popup.removeEventFilter(self)
            self._popup = popup
            popup.setAttribute(Qt.WidgetAttribute.WA_WindowPropagation, True)
            popup.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            popup.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
            popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            popup.installEventFilter(self)
        # Qt's editable-combo animation uses a QRollEffect screenshot window,
        # which cannot capture DWM acrylic and shows black on repeated opens.
        # Qt exposes only an application-wide switch for this effect. Scope it
        # to this synchronous call and restore the user's preference immediately.
        animate = self.isEditable() and QApplication.isEffectEnabled(Qt.UIEffect.UI_AnimateCombo)
        if animate:
            QApplication.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, False)
        try:
            super().showPopup()
        finally:
            if animate:
                QApplication.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, True)
