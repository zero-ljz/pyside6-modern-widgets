"""Modern painting for buttons whose identity and behavior belong to Qt."""

from __future__ import annotations

from PySide6.QtCore import QChildEvent, QEvent, QObject, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QProxyStyle,
    QPushButton,
    QStyle,
    QStyleOption,
    QStyleOptionButton,
    QWidget,
)

from .modern_push_button import ModernPushButton, _ButtonOption, _paint_modern_button
from .theme import ModernMetrics, inherited_theme


class _ModernButtonStyle(QProxyStyle):
    def __init__(self, button: QPushButton, metrics: ModernMetrics) -> None:
        super().__init__("Fusion")
        self.setParent(button)
        self._metrics = metrics

    def drawControl(
        self,
        element: QStyle.ControlElement,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None = None,
    ) -> None:
        if (
            element == QStyle.ControlElement.CE_PushButton
            and isinstance(option, QStyleOptionButton)
            and isinstance(widget, QPushButton)
        ):
            painter.save()
            _paint_modern_button(
                widget, _ButtonOption(option), painter, inherited_theme(widget), self._metrics
            )
            painter.restore()
            return
        super().drawControl(element, option, painter, widget)


class ButtonStyleBinding(QObject):
    """Style existing and lazily created message-box buttons without replacing them."""

    def __init__(self, button_box: QDialogButtonBox, metrics: ModernMetrics) -> None:
        super().__init__(button_box)
        self._button_box = button_box
        self._metrics = metrics
        button_box.installEventFilter(self)
        self.refresh()

    def refresh(self) -> None:
        for button in self._button_box.buttons():
            if isinstance(button, QPushButton):
                self._style_button(button)
                button.update()

    def _style_button(self, button: QPushButton) -> None:
        if isinstance(button, ModernPushButton) or isinstance(button.style(), _ModernButtonStyle):
            return
        # Each button owns its style; removing/deleting it keeps Qt ownership intact.
        button.setStyle(_ModernButtonStyle(button, self._metrics))
        button.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ChildPolished and isinstance(event, QChildEvent):
            child = event.child()
            if isinstance(child, QPushButton):
                self._style_button(child)
        elif event.type() in (QEvent.Type.Show, QEvent.Type.LayoutRequest):
            self.refresh()
        return False
