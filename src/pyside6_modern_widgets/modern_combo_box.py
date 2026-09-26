"""Modern rounded painting over Qt's native combo box behavior."""

from __future__ import annotations

from typing import cast

from PySide6.QtCore import QEvent, QMargins, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QLineEdit,
    QProxyStyle,
    QStyle,
    QStyledItemDelegate,
    QStyleOption,
    QStyleOptionMenuItem,
    QStyleOptionViewItem,
    QWidget,
)

from ._theme_binding import ThemeBinding
from .modern_menu import (
    _MENU_ITEM_EXTRA_HEIGHT,
    _MENU_VERTICAL_MARGIN,
    _base_style_name,
    _enable_windows_acrylic,
    _enable_windows_rounded_corners,
    _RoundedMenuStyle,
    _supports_windows_acrylic,
)
from .theme import (
    DEFAULT_METRICS,
    ModernMetrics,
    ModernTheme,
    inherited_theme,
    palette_for_theme,
)

# WinUI ControlFillColor: default, pointer over, pressed, disabled (ARGB).
_CONTROL_FILLS_LIGHT = ("#B3FFFFFF", "#80F9F9F9", "#4DF9F9F9", "#4DF9F9F9")
_CONTROL_FILLS_DARK = ("#0FFFFFFF", "#15FFFFFF", "#08FFFFFF", "#0BFFFFFF")


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

    def surfacePath(self, rect: QRectF) -> QPainterPath:
        if not self._combo.isEditable():
            return super().surfacePath(rect)
        path = QPainterPath()
        path.addRect(rect)
        return path

    def sizeFromContents(self, content_type, option, size, widget=None):
        result = super().sizeFromContents(content_type, option, size, widget)
        if content_type == QStyle.ContentsType.CT_ComboBox:
            native_style = QApplication.style()
            if native_style is not self:
                native_size = native_style.sizeFromContents(content_type, option, size, widget)
                result.setHeight(native_size.height())
        if content_type == QStyle.ContentsType.CT_ItemViewItem:
            result.setHeight(result.height() + _MENU_ITEM_EXTRA_HEIGHT)
            if self._is_default_item(widget):
                result.setWidth(result.width() + 16)
            if self._combo.isEditable() and self._is_default_item(widget):
                # Ask the same style as the non-editable menu delegate for its
                # font/icon-aware row height instead of imposing a fixed size.
                menu = QStyleOptionMenuItem()
                menu.font = option.font  # type: ignore[attr-defined]
                menu.fontMetrics = option.fontMetrics  # type: ignore[attr-defined]
                menu.icon = option.icon  # type: ignore[attr-defined]
                menu_size = super().sizeFromContents(
                    QStyle.ContentsType.CT_MenuItem, menu, size, self._combo
                )
                result.setHeight(max(result.height(), menu_size.height()))
        return result

    def _is_default_item(self, widget) -> bool:
        return widget is not None and widget is getattr(self._combo, "_default_view", None)

    def subElementRect(self, element, option, widget=None):
        if self._is_default_item(widget) and element in (
            QStyle.SubElement.SE_ItemViewItemText,
            QStyle.SubElement.SE_ItemViewItemDecoration,
            QStyle.SubElement.SE_ItemViewItemCheckIndicator,
        ):
            item = QStyleOptionViewItem(option)
            item.rect = option.rect.adjusted(8, 0, -8, 0)  # type: ignore[attr-defined]
            return super().subElementRect(element, item, widget)
        return super().subElementRect(element, option, widget)

    def _draw_chevron(
        self,
        option,
        painter,
        center: QPointF,
        *,
        upward: bool = False,
        scale: float = 1.0,
        line_width: float = 1.5,
        color_role: QPalette.ColorRole = QPalette.ColorRole.ButtonText,
    ) -> None:
        direction = -1 if upward else 1
        half_width = 4 * scale
        half_height = 2 * scale
        color_group = (
            option.palette.currentColorGroup()
            if option.state & QStyle.StateFlag.State_Enabled
            else QPalette.ColorGroup.Disabled
        )
        path = QPainterPath(center + QPointF(-half_width, -direction * half_height))
        path.lineTo(center + QPointF(0, direction * half_height))
        path.lineTo(center + QPointF(half_width, -direction * half_height))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(
            QPen(
                option.palette.color(color_group, color_role),
                line_width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawPath(path)
        painter.restore()

    def drawComplexControl(self, control, option, painter, widget=None) -> None:
        if control != QStyle.ComplexControl.CC_ComboBox:
            super().drawComplexControl(control, option, painter, widget)
            return
        if not option.frame:
            super().drawComplexControl(control, option, painter, widget)
            return
        theme = self._combo.theme()
        radius = 0 if option.editable else self._radius
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        pressed = bool(option.state & QStyle.StateFlag.State_On)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
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
        arrow_rect = self.subControlRect(
            control, option, QStyle.SubControl.SC_ComboBoxArrow, widget
        )
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        surface_role = QPalette.ColorRole.Base if option.editable else QPalette.ColorRole.Button
        fills = (
            _CONTROL_FILLS_DARK if QColor(theme.surface).lightness() < 128 else _CONTROL_FILLS_LIGHT
        )
        state_index = 3 if not enabled else 2 if pressed else 1 if hovered else 0
        surface = QBrush(QColor(fills[state_index]))
        idle_surface = QBrush(QColor(fills[0 if enabled else 3]))
        if self._combo._palette_override.isBrushSet(
            option.palette.currentColorGroup(), surface_role
        ):
            surface = idle_surface = option.palette.brush(surface_role)

        surfaces = [(QRectF(option.rect), surface)]
        if option.editable and enabled and (pressed or hovered):
            # Keep editor fill stable while the arrow button changes state.
            # Paint adjacent regions once each, so translucent fills do not stack.
            field_rect = QRectF(option.rect)
            button_rect = QRectF(option.rect)
            if option.direction == Qt.LayoutDirection.RightToLeft:
                button_rect.setRight(arrow_rect.right() + 1)
                field_rect.setLeft(button_rect.right())
            else:
                button_rect.setLeft(arrow_rect.left())
                field_rect.setRight(button_rect.left())
            surfaces = [(field_rect, idle_surface), (button_rect, surface)]
        for clip_rect, brush in surfaces:
            painter.save()
            painter.setClipRect(clip_rect, Qt.ClipOperation.IntersectClip)
            painter.setBrush(brush)
            painter.drawRoundedRect(rect, radius, radius)
            painter.restore()

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
        if option.editable:
            separator_x = (
                arrow_rect.right() + 0.5
                if option.direction == Qt.LayoutDirection.RightToLeft
                else arrow_rect.left() + 0.5
            )
            painter.setPen(QPen(border, 1))
            painter.drawLine(QPointF(separator_x, rect.top()), QPointF(separator_x, rect.bottom()))
        self._draw_chevron(option, painter, QPointF(arrow_rect.center()))
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


class _ComboBoxScrollerStyle(QProxyStyle):
    """Keep native scroller geometry while replacing only its solid arrow."""

    def __init__(self, combo: ModernComboBox, combo_style: _ComboBoxStyle) -> None:
        super().__init__(_base_style_name(combo))
        self.setParent(combo)
        self._combo_style = combo_style

    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if element in (
            QStyle.PrimitiveElement.PE_IndicatorArrowUp,
            QStyle.PrimitiveElement.PE_IndicatorArrowDown,
        ):
            self._combo_style._draw_chevron(
                option,
                painter,
                QRectF(option.rect).center(),
                upward=element == QStyle.PrimitiveElement.PE_IndicatorArrowUp,
                scale=0.8,
                line_width=1.0,
                color_role=QPalette.ColorRole.Text,
            )
            return
        super().drawPrimitive(element, option, painter, widget)


class _ComboBoxDelegate(QStyledItemDelegate):
    """Draw default rows without Qt's QSS-wrapped menu delegate's opaque fill."""

    def __init__(self, combo):
        super().__init__(combo)
        self._combo = combo

    def _menu_option(self, option, index):
        item = QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        menu = QStyleOptionMenuItem()
        menu.rect = item.rect
        menu.palette = item.palette
        menu.state = item.state
        menu.font = item.font
        menu.fontMetrics = item.fontMetrics
        menu.icon = item.icon
        if index.data(Qt.ItemDataRole.AccessibleDescriptionRole) == "separator":
            menu.menuItemType = QStyleOptionMenuItem.MenuItemType.Separator
        return menu

    def sizeHint(self, option, index):
        menu = self._menu_option(option, index)
        size = super().sizeHint(option, index)
        menu_size = self._combo._modern_style.sizeFromContents(
            QStyle.ContentsType.CT_MenuItem, menu, size, self._combo
        )
        if menu.menuItemType == QStyleOptionMenuItem.MenuItemType.Separator:
            return menu_size
        size.setHeight(max(size.height(), menu_size.height()))
        return size

    def paint(self, painter, option, index):
        if index.data(Qt.ItemDataRole.AccessibleDescriptionRole) == "separator":
            self._combo._modern_style.drawControl(
                QStyle.ControlElement.CE_MenuItem,
                self._menu_option(option, index),
                painter,
                self._combo,
            )
            return
        super().paint(painter, option, index)


class ModernComboBox(QComboBox):
    """A ``QComboBox`` with rounded surfaces and native Qt semantics.

    Models, delegates, signals, editing, completion and popup input remain owned
    by Qt. ``setTheme(None)`` restores the containing modern widget's theme, or
    the global theme when there is no themed ancestor.
    """

    themeChanged = Signal(object)

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
        self._default_line_edit: QLineEdit | None = None
        self._popup: QWidget | None = None
        self._popup_margins: QMargins | None = None
        self._modern_style = _ComboBoxStyle(self)
        self._scroller_style = _ComboBoxScrollerStyle(self, self._modern_style)
        self.setStyle(self._modern_style)
        # Configure only Qt's initial list, once. A caller-supplied view and any
        # later changes to this list retain their own style, frame and palette.
        view = self.view()
        self._default_view = view
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setAutoFillBackground(False)
        view.viewport().setAutoFillBackground(False)
        view.setStyle(self._modern_style)
        view_palette = QPalette()
        view_palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        view.setPalette(view_palette)
        self.setItemDelegate(_ComboBoxDelegate(self))
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._apply_theme()
        self._theme_binding: ThemeBinding = ThemeBinding(self, self.theme, self._apply_theme)
        self._theme_binding.changed.connect(self.themeChanged.emit)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override locally; None restores owner/ancestor/global inheritance."""
        if theme is not None and not isinstance(theme, ModernTheme):
            raise TypeError("theme must be a ModernTheme or None")
        self._theme_override = theme
        self._theme_binding.refresh()

    def setEditable(self, editable: bool) -> None:
        was_editable = self.isEditable()
        super().setEditable(editable)
        if editable and not was_editable:
            self._default_line_edit = self.lineEdit()
        self._refresh_editor_surface()

    def _refresh_editor_surface(self) -> None:
        editor = self.lineEdit()
        if editor is not None and editor is self._default_line_edit and self.hasFrame():
            # The combo paints the entire translucent surface. Qt's editor must
            # not cover it with a second base fill. Leave custom editors alone.
            palette = editor.palette()
            palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
            editor.setPalette(palette)

    def setFrame(self, enabled: bool) -> None:
        super().setFrame(enabled)
        editor = self.lineEdit()
        if editor is not None and editor is self._default_line_edit:
            editor.setPalette(self.palette())
        self._refresh_editor_surface()

    def setPalette(self, palette: QPalette | Qt.GlobalColor | QColor) -> None:
        if not hasattr(self, "_palette_override"):
            super().setPalette(palette)
            return
        self._palette_override = QPalette(palette)
        self._apply_theme()

    def eventFilter(self, watched, event) -> bool:
        # QComboBox may invoke this virtual method from its base constructor.
        if not hasattr(self, "_popup"):
            return super().eventFilter(watched, event)
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
        return super().eventFilter(watched, event)

    def _refresh_popup_acrylic(self) -> None:
        if self._popup is None:
            return
        self._modern_style.setNativeAcrylic(
            _enable_windows_rounded_corners(
                self._popup, self._metrics.control_radius, square=self.isEditable()
            )
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
            self._refresh_editor_surface()
            # Qt snapshots the container palette when opening; keep the owned
            # acrylic surface in sync without assigning a palette to the view.
            self.view().window().setPalette(self.palette())
            self.update()
            self.view().viewport().update()
            self.view().window().update()
        finally:
            self._applying_theme = False

    def showPopup(self) -> None:
        view = self.view()
        popup = view.window()
        if popup is not self._popup:
            if self._popup is not None:
                self._popup.removeEventFilter(self)
            self._popup = popup
            self._popup_margins = popup.contentsMargins()
            popup.setAttribute(Qt.WidgetAttribute.WA_WindowPropagation, True)
            popup.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            popup.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
            popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            popup.installEventFilter(self)
        if self._popup_margins is not None:
            margins = self._popup_margins
            spacing = (
                _MENU_VERTICAL_MARGIN if self.isEditable() and view is self._default_view else 0
            )
            popup.setContentsMargins(
                margins.left(), margins.top() + spacing, margins.right(), margins.bottom() + spacing
            )
        popup_children = cast(list[QWidget], popup.findChildren(QWidget))
        for child in popup_children:
            if child.metaObject().className() == "QComboBoxPrivateScroller":
                child.setStyle(self._scroller_style)
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
