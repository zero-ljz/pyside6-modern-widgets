"""A QWidget-based frameless window with selected QMainWindow-compatible APIs."""

from __future__ import annotations

import ctypes
import sys
from ctypes import byref
from ctypes.wintypes import HWND, MSG, RECT

from PySide6.QtCore import QEvent, QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import _resources  # noqa: F401
from .window_effect import WindowEffect, WindowStyleState

WM_NCHITTEST = 0x0084
WM_SETTINGCHANGE = 0x001A
HTLEFT, HTRIGHT, HTTOP, HTBOTTOM = 10, 11, 12, 15
HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT = 13, 14, 16, 17

button_style = """
QPushButton { border: none; background-color: transparent; }
QPushButton:hover { background-color: rgba(0, 0, 0, 0.05); }
QPushButton:pressed { background-color: rgba(0, 0, 0, 0.15); }
"""


def _user32():
    if sys.platform != "win32":
        return None
    try:
        return ctypes.windll.user32
    except (AttributeError, OSError):
        return None


def _resource_icon(name: str) -> QIcon:
    return QIcon(f":/pyside6_modern_widgets/icons/{name}")


class BackgroundFrame(QFrame):
    """Painting surface used by the frameless window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("backgroundFrame")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.corner_radius = 10
        self.use_watercolor = False

    def setCornerRadius(self, radius: int) -> None:
        self.corner_radius = radius
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not (
            self.use_watercolor
            and self.parent_window
            and self.parent_window.isActiveWindow()
        ):
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.corner_radius, self.corner_radius)
        painter.setClipPath(path)
        painter.fillRect(self.rect(), QColor(255, 252, 245))

        for color, x, y, radius in (
            (QColor(255, 183, 178, 120), 0.1, 0.1, 0.5),
            (QColor(199, 206, 234, 120), 0.9, 0.9, 0.6),
            (QColor(226, 240, 203, 120), 0.2, 0.9, 0.4),
        ):
            gradient = QRadialGradient(
                self.width() * x,
                self.height() * y,
                self.width() * radius,
            )
            gradient.setColorAt(0, color)
            gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self.rect())

        painter.setClipping(False)
        border_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(150, 150, 150, 128), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(border_rect, self.corner_radius, self.corner_radius)


class CustomTitleBar(QWidget):
    """Title bar retained from the original BaseWindow implementation."""

    def __init__(self, parent: ModernWindow | None = None) -> None:
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("CustomTitleBar")
        self.setAutoFillBackground(True)
        self.drag_start_pos: QPoint | None = None
        self.m_is_pressed = False
        self.m_start_pos: QPoint | None = None
        self.m_window_pos: QPoint | None = None
        self.initUI()

    def initUI(self) -> None:
        self.setFixedHeight(32)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        self.setPalette(palette)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 0, 5, 0)
        self.layout.setSpacing(5)

        self.left_layout = QHBoxLayout()
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(1)
        self.layout.addLayout(self.left_layout)

        self.iconLabel = QLabel(self)
        self.iconLabel.setFixedSize(20, 20)
        self.iconLabel.setScaledContents(True)
        self.iconLabel.hide()
        self.layout.addWidget(self.iconLabel)

        title = self.parent.windowTitle() if self.parent is not None else ""
        self.titleLabel = QLabel(title, self)
        self.titleLabel.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.titleLabel.setStyleSheet("font-size: 14px;")
        self.layout.addWidget(self.titleLabel)
        self.layout.addSpacerItem(
            QSpacerItem(
                40,
                20,
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum,
            )
        )

        self.right_layout = QHBoxLayout()
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(1)
        self.layout.addLayout(self.right_layout)

        self.pinButton = self._create_button(
            _resource_icon("pin.png"),
            "置顶",
            self.toggleOnTop,
            checkable=True,
        )
        self.minimizeButton = self._create_button(
            _resource_icon("minimize.png"),
            "最小化",
            self.parent.showMinimized,
        )
        self.maximizeButton = self._create_button(
            _resource_icon("maximize.png"),
            "最大化",
            self.changeMaximize,
        )
        self.closeButton = QPushButton("✕", self)
        self.closeButton.setToolTip("关闭")
        self.closeButton.setFixedSize(30, 30)
        self.closeButton.clicked.connect(self.parent.close)
        self.closeButton.setStyleSheet(
            "QPushButton { border: none; font-size: 18px; } "
            "QPushButton:hover { color: red; }"
        )
        for button in (
            self.pinButton,
            self.minimizeButton,
            self.maximizeButton,
            self.closeButton,
        ):
            self.layout.addWidget(button)

    def _create_button(self, icon, tooltip, callback, *, checkable=False):
        button = QPushButton(self)
        button.setIcon(icon)
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        button.setFixedSize(30, 30)
        button.setStyleSheet(button_style)
        button.clicked.connect(callback)
        return button

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        menu = QMenu(self)
        quit_action = menu.addAction(
            _resource_icon("shutdown.png"),
            "退出程序",
        )

        def confirm_exit() -> None:
            answer = QMessageBox.question(
                self,
                "确认退出",
                "确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                QApplication.quit()

        quit_action.triggered.connect(confirm_exit)
        menu.exec(event.globalPos())

    def setIcon(self, icon: QIcon) -> None:
        self.iconLabel.setVisible(not icon.isNull())
        if not icon.isNull():
            self.iconLabel.setPixmap(icon.pixmap(20, 20))

    def addCustomWidget(self, widget: QWidget, align: str = "right") -> None:
        if align == "left":
            self.left_layout.addWidget(widget)
        else:
            self.right_layout.addWidget(widget)

    def setTitle(self, title: str) -> None:
        self.titleLabel.setText(title)

    def toggleOnTop(self) -> None:
        was_maximized = self.parent.isMaximized()
        stored_rect = self.parent.normalGeometry()
        on_top = self.pinButton.isChecked()
        self.parent.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on_top)
        self.pinButton.setIcon(
            _resource_icon("push-pin.png" if on_top else "pin.png")
        )
        self.pinButton.setToolTip("取消置顶" if on_top else "置顶")
        if was_maximized:
            self.parent.showNormal()
            self.parent.setGeometry(stored_rect)
            self.parent.showMaximized()
        else:
            self.parent.showNormal()
        self.parent.apply_window_effect()

    def updateMaximizeIcon(self, isMaximized: bool) -> None:
        self.maximizeButton.setIcon(
            _resource_icon("restore.png" if isMaximized else "maximize.png")
        )
        self.maximizeButton.setToolTip("向下还原" if isMaximized else "最大化")

    def changeMaximize(self) -> None:
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if isinstance(child, QPushButton):
                super().mousePressEvent(event)
                return
            self.drag_start_pos = event.globalPosition().toPoint()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton:
            current_pos = event.globalPosition().toPoint()
            if self.parent.isMaximized() and self.drag_start_pos:
                delta = current_pos - self.drag_start_pos
                if delta.manhattanLength() > 5:
                    local_x = event.position().x()
                    local_y = event.position().y()
                    percent_x = local_x / max(1, self.parent.width())
                    width_after = self.parent.normalGeometry().width()
                    self.parent.showNormal()
                    new_x = current_pos.x() - int(width_after * percent_x)
                    new_y = current_pos.y() - int(local_y)
                    self.parent.move(new_x, new_y)
                    self.m_is_pressed = True
                    self.m_start_pos = current_pos
                    self.m_window_pos = QPoint(new_x, new_y)
                    self.drag_start_pos = None
            elif self.m_is_pressed and self.m_start_pos and self.m_window_pos:
                self.parent.move(self.m_window_pos + current_pos - self.m_start_pos)
                event.accept()
            elif self.drag_start_pos:
                delta = current_pos - self.drag_start_pos
                if delta.manhattanLength() > 5:
                    handle = self.parent.windowHandle()
                    if handle:
                        handle.startSystemMove()
                        self.drag_start_pos = None
                        QTimer.singleShot(
                            100,
                            lambda: self.updateMaximizeIcon(
                                self.parent.isMaximized()
                            ),
                        )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self.m_is_pressed = False
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if not isinstance(child, QPushButton):
                self.changeMaximize()
                event.accept()


class ModernWindow(QWidget):
    """Original BaseWindow design, renamed and detached from the host project."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.effect_manager = WindowEffect()
        self.setMouseTracking(True)
        self.setWindowTitle("基础窗体")
        self.winId()
        if self.windowHandle():
            self.windowHandle().screenChanged.connect(self.on_screen_changed)

        self.cornerRadius = 10
        self._menu_bar: QMenuBar | None = None
        self._status_bar: QStatusBar | None = None
        self.initWindow()
        self.apply_window_effect()

    def initWindow(self) -> None:
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.frame = BackgroundFrame(self)
        self.frame.setObjectName("backgroundFrame")
        self.apply_window_effect()
        self.layout.addWidget(self.frame)

        self.frameLayout = QVBoxLayout(self.frame)
        self.frameLayout.setContentsMargins(0, 0, 0, 0)
        self.frameLayout.setSpacing(0)

        self.titleBar = CustomTitleBar(self)
        self.frameLayout.addWidget(self.titleBar)

        self.toolbarLayout = QVBoxLayout()
        self.toolbarLayout.setSpacing(0)
        self.frameLayout.addLayout(self.toolbarLayout)

        self.content = QWidget(self)
        self.frameLayout.addWidget(self.content)

    def apply_window_effect(self) -> None:
        state = self.effect_manager.compute_style(
            is_maximized=self.isMaximized(),
            is_active=self.isActiveWindow(),
            hwnd=int(self.winId()),
            corner_radius=self.cornerRadius,
        )
        self._apply_style_state(state)
        self.repaint()

    def _apply_style_state(self, state: WindowStyleState) -> None:
        if hasattr(self, "frame") and self.frame:
            self.frame.use_watercolor = state.use_watercolor
            self.frame.setCornerRadius(state.corner_radius)
        self.setStyleSheet(
            f"""
            #backgroundFrame {{
                border: 1px solid rgba(150, 150, 150, 0.5);
                border-radius: {state.corner_radius}px;
                background-color: {state.bg_color};
            }}
            QLabel {{ color: {state.text_color}; }}
            """
        )

    def addTitleBarButton(
        self,
        icon,
        callback=None,
        tooltip: str = "",
        align: str = "right",
    ) -> QPushButton | None:
        if not hasattr(self, "titleBar") or self.titleBar is None:
            return None
        button = QPushButton(self.titleBar)
        if isinstance(icon, str):
            button.setIcon(QIcon(icon))
        elif isinstance(icon, QIcon):
            button.setIcon(icon)
        button.setFixedSize(30, 30)
        button.setStyleSheet(button_style)
        if tooltip:
            button.setToolTip(tooltip)
        if callback:
            button.clicked.connect(callback)
        self.titleBar.addCustomWidget(button, align=align)
        return button

    def setWindowIcon(self, icon: QIcon) -> None:  # noqa: N802
        super().setWindowIcon(icon)
        if hasattr(self, "titleBar") and self.titleBar:
            self.titleBar.setIcon(icon)

    def setWindowTitle(self, title: str) -> None:  # noqa: N802
        super().setWindowTitle(title)
        if hasattr(self, "titleBar") and self.titleBar is not None:
            self.titleBar.setTitle(title)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not event.spontaneous() and not self.isMaximized():
            QTimer.singleShot(50, self._trigger_refresh)

    def _trigger_refresh(self) -> None:
        if self.isMaximized():
            return
        width = self.width()
        self.resize(width + 1, self.height())
        self.resize(width, self.height())

    def menuBar(self) -> QMenuBar:  # noqa: N802
        if self._menu_bar is None:
            self._menu_bar = QMenuBar(self)
            self._menu_bar.setStyleSheet(
                """
                QMenuBar { background: transparent; border: none; }
                QMenuBar::item { background: transparent; }
                QMenuBar::item:selected {
                    background: rgba(0,0,0,0.1);
                    border-radius: 4px;
                }
                """
            )
            self.frameLayout.insertWidget(1, self._menu_bar)
        return self._menu_bar

    def addToolBar(self, *args) -> QToolBar:  # noqa: N802
        toolbar = next((arg for arg in args if isinstance(arg, QToolBar)), None)
        if toolbar is None:
            title = next((arg for arg in args if isinstance(arg, str)), "")
            toolbar = QToolBar(title, self) if title else QToolBar(self)
        toolbar.setStyleSheet("QToolBar { background: transparent; border: none; }")
        self.toolbarLayout.addWidget(toolbar)
        return toolbar

    def statusBar(self) -> QStatusBar:  # noqa: N802
        if self._status_bar is None:
            self._status_bar = QStatusBar(self)
            self._status_bar.setStyleSheet(
                "QStatusBar { background: transparent; border: none; }"
            )
            self._status_bar.setSizeGripEnabled(False)
            self.frameLayout.addWidget(self._status_bar)
        return self._status_bar

    def setCentralWidget(self, widget: QWidget) -> None:  # noqa: N802
        self.frameLayout.removeWidget(self.content)
        self.content.deleteLater()
        self.content = widget
        self.content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if self._status_bar:
            index = self.frameLayout.indexOf(self._status_bar)
            self.frameLayout.insertWidget(index, self.content)
        else:
            self.frameLayout.addWidget(self.content)

    def setCornerRadius(self, radius: int) -> None:
        self.cornerRadius = radius
        self.apply_window_effect()

    def on_screen_changed(self, _screen) -> None:
        QTimer.singleShot(0, self._force_resize)

    def _force_resize(self) -> None:
        current_size = self.size()
        self.resize(current_size.width() + 1, current_size.height())
        self.resize(current_size)

    def changeEvent(self, event) -> None:  # noqa: N802
        if event.type() == QEvent.Type.WindowStateChange:
            is_maximized = self.isMaximized()
            if hasattr(self, "titleBar") and self.titleBar:
                self.titleBar.updateMaximizeIcon(is_maximized)
            if not self.isMinimized():
                self.apply_window_effect()
        elif event.type() == QEvent.Type.ActivationChange and not self.isMinimized():
            self.apply_window_effect()
        super().changeEvent(event)

    def hideTitleBar(self) -> None:
        if hasattr(self, "titleBar") and self.titleBar:
            self.titleBar.hide()
            self.frameLayout.removeWidget(self.titleBar)
            self.titleBar.deleteLater()
            self.titleBar = None

    def nativeEvent(self, eventType, message):  # noqa: N802
        user32 = _user32()
        if eventType != "windows_generic_MSG" or user32 is None:
            return super().nativeEvent(eventType, message)

        msg = MSG.from_address(int(message))
        if msg.message == WM_SETTINGCHANGE:
            self.apply_window_effect()
        elif msg.message == WM_NCHITTEST and not self.isMaximized():
            x_screen = msg.lParam & 0xFFFF
            y_screen = (msg.lParam >> 16) & 0xFFFF
            x_screen = x_screen - 0x10000 if x_screen > 0x7FFF else x_screen
            y_screen = y_screen - 0x10000 if y_screen > 0x7FFF else y_screen

            win_rect = RECT()
            user32.GetWindowRect(HWND(int(self.winId())), byref(win_rect))
            local_x = x_screen - win_rect.left
            local_y = y_screen - win_rect.top
            width = win_rect.right - win_rect.left
            height = win_rect.bottom - win_rect.top
            border_width = 8
            left = local_x < border_width
            right = local_x > width - border_width
            top = local_y < border_width
            bottom = local_y > height - border_width

            if top and left:
                return True, HTTOPLEFT
            if top and right:
                return True, HTTOPRIGHT
            if bottom and left:
                return True, HTBOTTOMLEFT
            if bottom and right:
                return True, HTBOTTOMRIGHT
            if left:
                return True, HTLEFT
            if right:
                return True, HTRIGHT
            if top:
                return True, HTTOP
            if bottom:
                return True, HTBOTTOM
        return super().nativeEvent(eventType, message)
