"""A compact, animated switch with native Qt checkbox semantics."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QRect, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QSizePolicy,
    QStyle,
    QStyleOptionButton,
    QWidget,
)

from .theme import DEFAULT_METRICS, ModernMetrics, ModernTheme, inherited_theme, theme_manager


class ModernSwitch(QCheckBox):
    """A switch accepting ``(parent)`` or ``(text, parent)`` like QCheckBox.

    Use the standard checked state and ``toggled(bool)`` signal. The default
    track is 32 by 16 logical pixels, independent of host fonts and styles.
    The widget grows vertically when needed to fit its label.
    The enabled track reads Qt's system Accent role unless the theme overrides it.
    """

    def __init__(
        self,
        text: str | QWidget | None = "",
        parent: QWidget | None = None,
        *,
        theme: ModernTheme | None = None,
        metrics: ModernMetrics = DEFAULT_METRICS,
    ) -> None:
        if isinstance(text, QWidget) or text is None:
            parent, text = text, ""
        super().__init__(text, parent)
        self._keyboard_focus = False
        self._theme_override = theme
        self._position = float(self.isChecked())
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(metrics.animation_duration)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._on_position_changed)
        self.toggled.connect(self._sync_position)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        theme_manager().themeChanged.connect(self._on_theme_changed)

    def theme(self) -> ModernTheme:
        return self._theme_override if self._theme_override is not None else inherited_theme(self)

    def setTheme(self, theme: ModernTheme | None) -> None:
        """Override colors locally, or pass None to restore theme inheritance."""
        self._theme_override = theme
        self.update()

    def _on_theme_changed(self, _theme: ModernTheme) -> None:
        self.update()

    def sizeHint(self) -> QSize:
        height = 20
        width = 38
        if self.text():
            label = self.fontMetrics().size(Qt.TextFlag.TextShowMnemonic, self.text())
            width += 8 + label.width()
            height = max(height, label.height())
        return QSize(width, height)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def hitButton(self, pos: QPoint) -> bool:
        # Include the label and the whole compact track, unlike QCheckBox's
        # native indicator hit rectangle, which has different dimensions.
        return self.rect().contains(pos)

    def checkStateSet(self) -> None:
        super().checkStateSet()
        if hasattr(self, "_animation"):
            self._sync_position()

    def _sync_position(self, _checked: bool = False) -> None:
        target = float(self.isChecked())
        if not self.isVisible() or not self.isEnabled():
            self._animation.stop()
            if self._position != target:
                self._position = target
                self.update()
        elif self._animation.endValue() != target:
            self._animation.stop()
            self._animation.setStartValue(self._position)
            self._animation.setEndValue(target)
            self._animation.start()

    def _on_position_changed(self, value: float) -> None:
        self._position = float(value)
        self.update()

    def event(self, event) -> bool:
        if hasattr(self, "_keyboard_focus"):
            keyboard_focus = self._keyboard_focus
            if event.type() == QEvent.Type.FocusIn and event.reason() not in (
                Qt.FocusReason.ActiveWindowFocusReason,
                Qt.FocusReason.PopupFocusReason,
            ):
                keyboard_focus = event.reason() in (
                    Qt.FocusReason.TabFocusReason,
                    Qt.FocusReason.BacktabFocusReason,
                    Qt.FocusReason.ShortcutFocusReason,
                )
            elif event.type() == QEvent.Type.MouseButtonPress:
                keyboard_focus = False
            elif event.type() == QEvent.Type.KeyPress:
                keyboard_focus = True
            if keyboard_focus != self._keyboard_focus:
                self._keyboard_focus = keyboard_focus
                self.update()
        handled = super().event(event)
        if hasattr(self, "_animation"):
            if event.type() in (QEvent.Type.Show, QEvent.Type.Hide, QEvent.Type.EnabledChange):
                self._sync_position()
            if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
                self.updateGeometry()
        return handled

    def paintEvent(self, event) -> None:
        # Also reconcile changes made with signals blocked (e.g. settings loads).
        self._sync_position()
        theme = self.theme()
        option = QStyleOptionButton()
        self.initStyleOption(option)
        enabled = self.isEnabled()
        checked = self.isChecked()
        accent = (
            QColor(theme.accent)
            if theme.accent
            # Window activation does not change the switch's checked state.
            # Some Windows palettes make Inactive.Accent match the surface,
            # which hides the track and changes the contrasting thumb color.
            else self.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent)
        )
        track_color = accent if checked else QColor(theme.surface_alternate)
        border_color = accent if checked else QColor(theme.text_muted)
        thumb_color = QColor(theme.text_muted)
        if checked:
            # Custom system accents can be very light; keep the thumb legible.
            thumb_color = (
                QColor(theme.on_accent)
                if theme.on_accent
                else QColor("#FFFFFF" if accent.lightnessF() < 0.6 else "#202020")
            )
        if not enabled:
            track_color = QColor(theme.border if checked else theme.surface_alternate)
            border_color = QColor(theme.border)
            thumb_color = QColor(theme.text_disabled)

        height = max(0, min(16, self.height() - 4))
        track = QRectF(3, (self.height() - height) / 2, height * 2, height)
        rtl = self.layoutDirection() == Qt.LayoutDirection.RightToLeft
        if rtl:
            track.moveRight(self.width() - 3)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(track_color)
        painter.drawRoundedRect(track, height / 2, height / 2)
        if enabled and (self.underMouse() or self.isDown()):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(
                QColor(theme.control_pressed if self.isDown() else theme.control_hover)
            )
            painter.drawRoundedRect(track, height / 2, height / 2)

        diameter = height - (6 if self.isDown() else 8)
        progress = 1 - self._position if rtl else self._position
        center_x = track.left() + height / 2 + progress * (track.width() - height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(thumb_color)
        painter.drawEllipse(
            QRectF(center_x - diameter / 2, track.center().y() - diameter / 2, diameter, diameter)
        )

        if self.text():
            text_rect = QRect(
                int(track.right()) + 8, 0, self.width() - int(track.right()) - 11, self.height()
            )
            alignment = Qt.AlignmentFlag.AlignLeft
            if rtl:
                text_rect = QRect(3, 0, int(track.left()) - 11, self.height())
                alignment = Qt.AlignmentFlag.AlignRight
            flags = int(alignment | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextShowMnemonic)
            if not self.style().styleHint(QStyle.StyleHint.SH_UnderlineShortcut, option, self):
                flags |= int(Qt.TextFlag.TextHideMnemonic)
            painter.setPen(QColor(theme.text if enabled else theme.text_disabled))
            painter.drawText(text_rect, flags, self.text())

        if enabled and self.hasFocus() and self._keyboard_focus:
            painter.setPen(QPen(accent, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(track.adjusted(-2, -2, 2, 2), height / 2 + 2, height / 2 + 2)
        painter.end()
