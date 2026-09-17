from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QImage, QKeySequence, QPainter, QPalette, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QMainWindow,
    QStyle,
    QStyleOptionToolButton,
    QToolBar,
    QToolButton,
    QWidget,
    QWidgetAction,
)
from shiboken6 import isValid

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernMenu,
    ModernToolBar,
    ModernWindow,
    ThemeMode,
)

_APP = QApplication.instance() or QApplication([])


def settle() -> None:
    for _ in range(5):
        _APP.processEvents()


def inspect_popup(toolbar: ModernToolBar) -> list[QAction]:
    opened = []
    contents = []

    def inspect() -> None:
        menu = toolbar.overflowMenu()
        opened.append(menu.isVisible() and QApplication.activePopupWidget() is menu)
        contents.extend(menu.actions())
        menu.close()

    QTimer.singleShot(30, inspect)
    QTest.mouseClick(toolbar.overflowButton(), Qt.MouseButton.LeftButton)
    assert opened == [True]
    return contents


@pytest.mark.parametrize("docked", [False, True])
def test_overflow_popup_keeps_actions_shortcuts_submenus_and_native_toolbar_api(docked):
    window = QMainWindow() if docked else ModernWindow()
    toolbar = ModernToolBar("Tools", window)
    toolbar.setIconSize(QSize(18, 18))
    if docked:
        window.addToolBar(toolbar)
    else:
        window.titleBar.addCustomWidget(toolbar, align="left")
    toolbar.setFixedWidth(155)
    toolbar.addAction("Open")
    toolbar.addSeparator()
    toggle = toolbar.addAction("Toggle panel")
    toggle.setCheckable(True)
    toggle.setShortcut(QKeySequence("Ctrl+Shift+B"))
    disabled = toolbar.addAction("Unavailable")
    disabled.setEnabled(False)
    toolbar.addSeparator()
    submenu = ModernMenu("More", window)
    submenu.addAction("Nested action")
    toolbar.addAction(submenu.menuAction())
    toolbar.addSeparator()
    triggered = []
    toolbar.actionTriggered.connect(triggered.append)
    window.resize(800, 400)
    window.show()
    settle()
    try:
        assert isinstance(toolbar.overflowMenu(), ModernMenu)
        contents = inspect_popup(toolbar)
        assert contents[0] is toggle
        assert not contents[-1].isSeparator()
        assert contents[-1].menu() is submenu
        assert not disabled.isEnabled()
        toggle.trigger()
        assert toggle.isChecked()
        assert triggered == [toggle]
        assert toggle.shortcut() == QKeySequence("Ctrl+Shift+B")
        toggle.setText("Renamed toggle")
        disabled.setEnabled(True)
        toolbar.removeAction(submenu.menuAction())
        added = toolbar.addAction("Added later")
        settle()
        contents = inspect_popup(toolbar)
        assert contents[0].text() == "Renamed toggle"
        assert contents[0].isChecked()
        assert disabled.isEnabled()
        assert submenu.menuAction() not in contents
        assert contents[-1] is added
        added.setVisible(False)
        settle()
        assert added not in toolbar.overflowMenu().actions()
        toolbar.setFixedWidth(700)
        settle()
        assert not toolbar.overflowButton().isVisible()
        assert toolbar.widgetForAction(toggle).isVisible()
        toolbar.widgetForAction(toggle).click()
        assert not toggle.isChecked()
        toolbar.setFixedWidth(155)
        settle()
        assert toggle in inspect_popup(toolbar)
    finally:
        window.close()
        window.deleteLater()


@pytest.mark.parametrize("orientation", [Qt.Orientation.Horizontal, Qt.Orientation.Vertical])
@pytest.mark.parametrize(
    "direction", [Qt.LayoutDirection.LeftToRight, Qt.LayoutDirection.RightToLeft]
)
def test_overflow_scales_with_icons_and_supports_orientation_and_rtl(orientation, direction):
    toolbar = ModernToolBar()
    toolbar.setOrientation(orientation)
    toolbar.setLayoutDirection(direction)
    toolbar.setIconSize(QSize(32, 32))
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
    for index in range(10):
        toolbar.addAction(f"Action {index}")
    toolbar.resize(190, 50) if orientation == Qt.Orientation.Horizontal else toolbar.resize(
        100, 160
    )
    toolbar.show()
    settle()
    try:
        button = toolbar.overflowButton()
        assert button.isVisible()
        assert not button.icon().isNull()
        assert inspect_popup(toolbar)[-1] is toolbar.actions()[-1]
    finally:
        toolbar.close()
        toolbar.deleteLater()


def test_theme_inheritance_override_reparenting_and_toolbar_styles_do_not_style_popup(
    theme_manager_instance,
):
    manager = theme_manager_instance
    manager.setMode(ThemeMode.LIGHT)
    first, second = ModernWindow(), ModernWindow(theme=DARK_THEME)
    toolbar = ModernToolBar(first)
    toolbar.addAction("Action")
    try:
        assert toolbar.theme() == manager.theme()
        manager.setMode(ThemeMode.DARK)
        assert toolbar.theme() == manager.theme()
        custom = replace(LIGHT_THEME, control_hover="#FF123456")
        first.setTheme(custom)
        assert toolbar.theme().control_hover == "#FF123456"
        first.setTheme(replace(custom, control_hover="#FF654321"))
        assert toolbar.theme().control_hover == "#FF654321"
        toolbar.setTheme(DARK_THEME)
        assert toolbar.theme() == DARK_THEME
        assert toolbar.overflowMenu().palette().color(QPalette.ColorRole.Window).name() == "#2b2b2b"
        toolbar.setTheme(None)
        assert toolbar.theme() == first.theme()
        toolbar.setStyleSheet("QToolButton { padding: 4px; background: transparent; }")
        assert toolbar.overflowMenu().style().metaObject().className() == "_RoundedMenuStyle"
        toolbar.setParent(second)
        settle()
        assert toolbar.theme() == DARK_THEME
        assert toolbar.overflowMenu().parentWidget() is second
        popup = toolbar.overflowMenu()
        first.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert isValid(toolbar) and isValid(popup)
        toolbar.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert not isValid(popup)
    finally:
        if isValid(first):
            first.close()
        second.close()
        second.deleteLater()


def test_widget_actions_create_popup_instances_without_stealing_default_widgets():
    class SearchAction(QWidgetAction):
        def createWidget(self, parent):
            widget = QLineEdit(parent)
            widget.setPlaceholderText("Search")
            return widget

    toolbar = ModernToolBar()
    toolbar.setFixedWidth(120)
    toolbar.addAction("Open document")
    default = QLineEdit()
    default_action = toolbar.addWidget(default)
    search = SearchAction(toolbar)
    toolbar.addAction(search)
    toolbar.show()
    settle()
    try:
        contents = inspect_popup(toolbar)
        assert default_action not in contents
        assert default.parentWidget() is toolbar
        assert search in contents
        # Qt can also instantiate a control in its private, unused overflow menu.
        assert len(search.createdWidgets()) >= 2
        assert toolbar.widgetForAction(search).parentWidget() is toolbar
        assert toolbar.overflowMenu().findChild(QLineEdit) is not None
        toolbar.resize(800, 100)
        toolbar.setFixedWidth(800)
        settle()
        assert default.parentWidget() is toolbar
        assert len(search.createdWidgets()) == 1
    finally:
        toolbar.close()
        toolbar.deleteLater()


def test_constructor_and_accessors():
    parent = QWidget()
    toolbar = ModernToolBar(parent)
    titled = ModernToolBar("Editing", parent)
    assert toolbar.parentWidget() is parent
    assert titled.windowTitle() == "Editing"
    assert isinstance(toolbar.overflowButton(), QToolButton)
    with pytest.raises(TypeError, match="parent specified twice"):
        ModernToolBar(parent, parent)
    parent.close()
    parent.deleteLater()


def test_window_title_overload_creates_modern_toolbar_without_replacing_its_style():
    window = ModernWindow()
    toolbar = window.addToolBar("Tools")
    assert isinstance(toolbar, ModernToolBar)
    assert not toolbar.styleSheet()
    window.close()
    window.deleteLater()


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
@pytest.mark.parametrize(
    "state",
    [
        QStyle.StateFlag.State_MouseOver,
        QStyle.StateFlag.State_Sunken,
        QStyle.StateFlag.State_On,
    ],
)
@pytest.mark.parametrize("overflow", [False, True])
def test_button_state_surface_uses_full_native_rect(theme, state, overflow):
    toolbar = ModernToolBar(theme=theme)
    toolbar.setIconSize(QSize(18, 18))
    action = toolbar.addAction("Action")
    button = toolbar.overflowButton() if overflow else toolbar.widgetForAction(action)
    button.ensurePolished()
    button.resize(30, 30)
    option = QStyleOptionToolButton()
    option.initFrom(button)
    option.rect = button.rect()
    option.icon = QIcon()
    option.text = ""
    option.subControls = QStyle.SubControl.SC_ToolButton
    option.state = QStyle.StateFlag.State_Enabled | state
    canvas = QImage(30, 30, QImage.Format.Format_ARGB32_Premultiplied)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    button.style().drawPrimitive(
        QStyle.PrimitiveElement.PE_PanelButtonTool, option, painter, button
    )
    painter.end()
    center_alpha = canvas.pixelColor(15, 15).alpha()
    assert 0 < center_alpha < 60
    # Only the corners are rounded: no extra inset on any of the four sides.
    for x, y in ((15, 0), (15, 29), (0, 15), (29, 15)):
        assert canvas.pixelColor(x, y).alpha() == center_alpha
    toolbar.close()
    toolbar.deleteLater()


@pytest.mark.parametrize("orientation", [Qt.Orientation.Horizontal, Qt.Orientation.Vertical])
@pytest.mark.parametrize(
    "direction", [Qt.LayoutDirection.LeftToRight, Qt.LayoutDirection.RightToLeft]
)
def test_native_button_geometry_overflow_thresholds_and_menu_hit_regions(orientation, direction):
    native, modern = QToolBar(), ModernToolBar()
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    try:
        for toolbar in (native, modern):
            toolbar.setMovable(False)
            toolbar.setOrientation(orientation)
            toolbar.setLayoutDirection(direction)
            toolbar.setIconSize(QSize(18, 18))
            for text in ("Open", "Save", "Back", "Forward"):
                toolbar.addAction(QIcon(pixmap), text)
            toolbar.addSeparator()
            menu = ModernMenu("More", toolbar)
            menu.setIcon(QIcon(pixmap))
            menu.addAction("Details")
            toolbar.addAction(menu.menuAction())
            toolbar.show()
        for text_style in (Qt.ToolButtonIconOnly, Qt.ToolButtonTextBesideIcon):
            for extent in (102, 160, 260):
                for toolbar in (native, modern):
                    toolbar.setToolButtonStyle(text_style)
                    toolbar.resize(
                        QSize(extent, 40) if orientation == Qt.Horizontal else QSize(80, extent)
                    )
                settle()
                assert native.sizeHint() == modern.sizeHint()
                for left, right in zip(native.actions(), modern.actions()):
                    native_button, modern_button = (
                        native.widgetForAction(left),
                        modern.widgetForAction(right),
                    )
                    assert native_button.isHidden() == modern_button.isHidden()
                    if not native_button.isHidden():
                        assert native_button.geometry() == modern_button.geometry()
                assert (
                    native.findChild(QToolButton, "qt_toolbar_ext_button").geometry()
                    == modern.overflowButton().geometry()
                )
        # Full-width split menu: both native subcontrols retain their own hit region.
        native.setOrientation(Qt.Horizontal)
        modern.setOrientation(Qt.Horizontal)
        native.resize(800, 40)
        modern.resize(800, 40)
        settle()
        buttons = [bar.widgetForAction(bar.actions()[-1]) for bar in (native, modern)]
        options = []
        for button in buttons:
            option = QStyleOptionToolButton()
            button.initStyleOption(option)
            options.append(option)
        for part in (QStyle.SubControl.SC_ToolButton, QStyle.SubControl.SC_ToolButtonMenu):
            rects = [
                button.style().subControlRect(
                    QStyle.ComplexControl.CC_ToolButton, option, part, button
                )
                for button, option in zip(buttons, options)
            ]
            assert rects[0] == rects[1]
            assert (
                buttons[1]
                .style()
                .hitTestComplexControl(
                    QStyle.ComplexControl.CC_ToolButton, options[1], rects[1].center(), buttons[1]
                )
                == part
            )
        button = buttons[1]
        menu = modern.actions()[-1].menu()
        opened = []

        def close_menu():
            opened.append(menu.isVisible())
            menu.close()

        QTimer.singleShot(30, close_menu)
        arrow = button.style().subControlRect(
            QStyle.ComplexControl.CC_ToolButton,
            options[1],
            QStyle.SubControl.SC_ToolButtonMenu,
            button,
        )
        QTest.mouseClick(button, Qt.LeftButton, pos=arrow.center())
        assert opened == [True]
    finally:
        for toolbar in (native, modern):
            toolbar.close()
            toolbar.deleteLater()


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
@pytest.mark.parametrize("pressed", [False, True])
def test_split_menu_arrow_is_visible_without_an_opaque_panel(theme, pressed):
    toolbar = ModernToolBar(theme=theme)
    menu = ModernMenu("More", toolbar)
    menu.addAction("Details")
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    menu.setIcon(QIcon(pixmap))
    toolbar.addAction(menu.menuAction())
    toolbar.show()
    settle()
    try:
        button = toolbar.widgetForAction(menu.menuAction())
        button.setDown(pressed)
        option = QStyleOptionToolButton()
        button.initStyleOption(option)
        option.state &= ~QStyle.StateFlag.State_HasFocus
        arrow = button.style().subControlRect(
            QStyle.ComplexControl.CC_ToolButton,
            option,
            QStyle.SubControl.SC_ToolButtonMenu,
            button,
        )
        canvas = QImage(button.size(), QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        button.style().drawComplexControl(
            QStyle.ComplexControl.CC_ToolButton, option, painter, button
        )
        painter.end()
        # The arrow should be visible; an opaque rectangle in its slot is not.
        opaque = sum(
            canvas.pixelColor(x, y).alpha() > 200
            for x in range(arrow.left(), arrow.right() + 1)
            for y in range(arrow.top(), arrow.bottom() + 1)
        )
        assert 0 < opaque < arrow.width() * arrow.height() // 4
    finally:
        toolbar.close()
        toolbar.deleteLater()
