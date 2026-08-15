"""WinUI-inspired tabs built on Qt's proven QTabWidget implementation."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QTabBar, QTabWidget, QToolButton, QWidget


class _TabBar(QTabBar):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDrawBase(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setExpanding(False)
        self.setMovable(True)
        self.setUsesScrollButtons(True)
        self.setDocumentMode(True)


class TabView(QTabWidget):
    """A QTabWidget-compatible tab view with WinUI-inspired styling."""

    addTabClicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTabBar(_TabBar(self))
        self.setDocumentMode(True)
        self.setTabsClosable(True)
        self.setMovable(True)
        self._add_button = QToolButton(self)
        self._add_button.setText("+")
        self._add_button.setToolTip("New tab")
        self._add_button.setFixedSize(34, 32)
        self._add_button.clicked.connect(self.addTabClicked.emit)
        self.setCornerWidget(self._add_button, Qt.Corner.TopRightCorner)
        self.setStyleSheet(
            """
            QTabWidget::pane {
                border: none;
                border-top: 1px solid #E5E5E5;
                background: #FFFFFF;
            }
            QTabBar { background: #F3F3F3; }
            QTabBar::tab {
                min-width: 80px;
                max-width: 200px;
                height: 30px;
                padding: 3px 10px;
                margin-top: 3px;
                border: 1px solid transparent;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                color: #454545;
            }
            QTabBar::tab:hover { background: #EAEAEA; }
            QTabBar::tab:selected {
                background: #FFFFFF;
                border-color: #E5E5E5;
                color: #000000;
            }
            QToolButton {
                border: none;
                border-radius: 4px;
                background: transparent;
                font-size: 18px;
            }
            QToolButton:hover { background: #EAEAEA; }
            """
        )
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+T"), self, self.addTabClicked.emit)
        QShortcut(QKeySequence("Ctrl+W"), self, self._request_current_close)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self.nextTab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self.previousTab)

    def _request_current_close(self) -> None:
        if self.currentIndex() >= 0:
            self.tabCloseRequested.emit(self.currentIndex())

    def nextTab(self) -> None:
        if self.count():
            self.setCurrentIndex((self.currentIndex() + 1) % self.count())

    def previousTab(self) -> None:
        if self.count():
            self.setCurrentIndex((self.currentIndex() - 1) % self.count())
