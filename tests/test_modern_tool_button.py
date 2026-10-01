from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QImage, QPainter, QPalette, QPixmap, QWheelEvent
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QStyle,
    QStyleFactory,
    QStyleOptionToolButton,
    QToolBar,
    QToolButton,
    QWidget,
)

from pyside6_modern_widgets import DARK_THEME, LIGHT_THEME, ModernToolButton

_APP = QApplication.instance() or QApplication([])
_STYLES = list(Qt.ToolButtonStyle)
_POPUPS = list(QToolButton.ToolButtonPopupMode)


@pytest.fixture
def widgets():
    owned = []

    def create(cls=ModernToolButton, **kwargs):
        widget = cls(**kwargs)
        if cls is QToolButton:
            style = QStyleFactory.create("Fusion")
            style.setParent(widget)
            widget.setStyle(style)
        owned.append(widget)
        return widget

    yield create
    for widget in reversed(owned):
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def solid_icon():
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor("#ED178D"))
    return QIcon(pixmap)


def option_for(button):
    option = QStyleOptionToolButton()
    button.initStyleOption(option)
    return option


def sub_rect(button, subcontrol):
    return button.style().subControlRect(
        QStyle.CC_ToolButton, option_for(button), subcontrol, button
    )


@pytest.mark.parametrize("style", _STYLES)
@pytest.mark.parametrize("popup", _POPUPS)
@pytest.mark.parametrize("rtl", [False, True])
def test_fusion_geometry_hit_regions_and_visible_icons(widgets, style, popup, rtl):
    buttons = [widgets(cls) for cls in (QToolButton, ModernToolButton)]
    for point_size, icon_size in ((9, 16), (16, 24)):
        images = []
        for button in buttons:
            button.setText("&Open 文档")
            button.setIcon(solid_icon())
            button.setIconSize(QSize(icon_size, icon_size))
            font = button.font()
            font.setPointSize(point_size)
            button.setFont(font)
            button.setToolButtonStyle(style)
            button.setPopupMode(popup)
            button.setMenu(QMenu(button))
            button.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
            button.resize(button.sizeHint())
            images.append(button.grab().toImage())
        native, modern = buttons
        assert modern.sizeHint() == native.sizeHint()
        assert modern.minimumSizeHint() == native.minimumSizeHint()
        assert modern.sizePolicy() == native.sizePolicy()
        assert modern.focusPolicy() == native.focusPolicy()
        assert modern.autoRaise() == native.autoRaise()
        for subcontrol in (QStyle.SC_ToolButton, QStyle.SC_ToolButtonMenu):
            rect = sub_rect(native, subcontrol)
            assert rect == sub_rect(modern, subcontrol)
            assert native.style().hitTestComplexControl(
                QStyle.CC_ToolButton, option_for(native), rect.center(), native
            ) == modern.style().hitTestComplexControl(
                QStyle.CC_ToolButton, option_for(modern), rect.center(), modern
            )
        if style != Qt.ToolButtonTextOnly:
            pixels = []
            for image in images:
                pixels.append(
                    {
                        (x, y)
                        for x in range(image.width())
                        for y in range(image.height())
                        if image.pixelColor(x, y) == QColor("#ED178D")
                    }
                )
            # The corner menu chevron can cover different icon pixels from
            # Fusion's triangle, but must not move or resize the visible icon.
            assert all(pixels)
            bounds = [
                (
                    min(x for x, y in mask),
                    min(y for x, y in mask),
                    max(x for x, y in mask),
                    max(y for x, y in mask),
                )
                for mask in pixels
            ]
            assert bounds[0] == bounds[1]


@pytest.mark.parametrize("arrow", [Qt.UpArrow, Qt.DownArrow, Qt.LeftArrow, Qt.RightArrow])
def test_modern_arrow_glyphs_replace_native_triangles(widgets, arrow):
    masks = []
    sizes = []
    for cls in (QToolButton, ModernToolButton):
        button = widgets(cls)
        if cls is ModernToolButton:
            button.setTheme(replace(LIGHT_THEME, text="#ED178D"))
        palette = button.palette()
        palette.setColor(QPalette.ButtonText, QColor("#ED178D"))
        palette.setColor(QPalette.WindowText, QColor("#ED178D"))
        button.setPalette(palette)
        button.setArrowType(arrow)
        button.resize(button.sizeHint())
        sizes.append((button.sizeHint(), button.minimumSizeHint()))
        image = button.grab().toImage()
        masks.append(
            {
                (x, y)
                for x in range(image.width())
                for y in range(image.height())
                if image.pixelColor(x, y).red() - image.pixelColor(x, y).green() > 30
                and image.pixelColor(x, y).blue() - image.pixelColor(x, y).green() > 20
            }
        )
    assert sizes[0] == sizes[1]
    assert all(masks) and masks[0] != masks[1]


def trace_button(button):
    events = []
    button.pressed.connect(lambda: events.append("pressed"))
    button.released.connect(lambda: events.append("released"))
    button.clicked.connect(lambda checked: events.append(("clicked", checked)))
    button.toggled.connect(lambda checked: events.append(("toggled", checked)))
    button.triggered.connect(lambda action: events.append(("triggered", action.text())))
    return events


def test_native_action_sync_mouse_keyboard_and_wheel(widgets):
    results = []
    for cls in (QToolButton, ModernToolButton):
        button = widgets(cls)
        action = QAction(solid_icon(), "&Open", button)
        action.setCheckable(True)
        button.setDefaultAction(action)
        button.resize(button.sizeHint())
        button.show()
        _APP.processEvents()
        events = trace_button(button)
        QTest.mouseClick(button, Qt.LeftButton)
        assert action.isChecked() and button.isChecked()
        QTest.keyClick(button, Qt.Key_Space)
        assert not action.isChecked() and not button.isChecked()
        QTest.mousePress(button, Qt.LeftButton)
        QTest.mouseMove(button, QPoint(-10, -10))
        QTest.mouseRelease(button, Qt.LeftButton, pos=QPoint(-10, -10))
        assert not button.isChecked()
        before = events.copy()
        wheel = QWheelEvent(
            QPointF(5, 5),
            QPointF(button.mapToGlobal(QPoint(5, 5))),
            QPoint(),
            QPoint(0, 120),
            Qt.NoButton,
            Qt.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        _APP.sendEvent(button, wheel)
        assert events == before
        action.setText("Renamed")
        action.setIconText("Short")
        action.setToolTip("Tip")
        action.setChecked(True)
        assert button.text() == "Short" and button.toolTip() == "Tip" and button.isChecked()
        action.setEnabled(False)
        before = events.copy()
        QTest.mouseClick(button, Qt.LeftButton)
        QTest.keyClick(button, Qt.Key_Space)
        assert events == before and not button.isEnabled()
        replacement = QAction("Replacement", button)
        button.setDefaultAction(replacement)
        assert button.isEnabled() and not button.isCheckable()
        assert button.defaultAction() is replacement
        results.append(events)
        button.hide()
    assert results[0] == results[1]


@pytest.mark.parametrize("popup", _POPUPS)
@pytest.mark.parametrize("rtl", [False, True])
@pytest.mark.parametrize("keyboard", [False, True])
def test_popup_modes_and_split_action_match_native(widgets, popup, rtl, keyboard):
    results = []
    for cls in (QToolButton, ModernToolButton):
        button = widgets(cls)
        action = QAction(solid_icon(), "Default", button)
        button.setDefaultAction(action)
        menu = QMenu(button)
        choice = menu.addAction("Choice")
        button.setMenu(menu)
        button.setPopupMode(popup)
        button.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        button.resize(button.sizeHint())
        button.show()
        _APP.processEvents()
        events = trace_button(button)
        opened = QSignalSpy(menu.aboutToShow)
        chosen = QSignalSpy(choice.triggered)
        choose_timer = QTimer(menu)
        choose_timer.setInterval(10)

        def choose(menu=menu, choice=choice, timer=choose_timer):
            if not menu.isVisible():
                return
            timer.stop()
            menu.setActiveAction(choice)
            QTest.keyClick(menu, Qt.Key_Return)
            menu.close()

        choose_timer.timeout.connect(choose)
        menu.aboutToShow.connect(choose_timer.start)
        main = sub_rect(button, QStyle.SC_ToolButton).center()
        QTest.mouseMove(button, main)
        _APP.processEvents()
        if not keyboard and popup != QToolButton.InstantPopup:
            QTest.mouseClick(button, Qt.LeftButton, pos=main)
            assert opened.count() == 0
            assert ("triggered", "Default") in events
        if keyboard:
            # QToolButton does not add an Alt+Down menu shortcut. Space retains
            # the native main-action/instant-popup/hold-for-delayed behavior.
            QTest.keyClick(button, Qt.Key_Down, Qt.AltModifier)
            assert opened.count() == 0
            if popup == QToolButton.MenuButtonPopup:
                QTest.keyClick(button, Qt.Key_Space)
                assert opened.count() == 0 and ("triggered", "Default") in events
                results.append(events)
                button.hide()
                continue
            if popup == QToolButton.DelayedPopup:
                QTest.keyPress(button, Qt.Key_Space)
            else:
                QTest.keyClick(button, Qt.Key_Space)
        elif popup == QToolButton.DelayedPopup:
            QTest.mousePress(button, Qt.LeftButton, pos=main)
        else:
            point = sub_rect(button, QStyle.SC_ToolButtonMenu).center()
            QTest.mouseClick(button, Qt.LeftButton, pos=point)
        assert chosen.count() or chosen.wait(2000)
        if popup == QToolButton.DelayedPopup:
            if keyboard:
                QTest.keyRelease(button, Qt.Key_Space)
            else:
                QTest.mouseRelease(button, Qt.LeftButton, pos=main)
        assert not menu.isVisible() and opened.count() == 1
        assert ("triggered", "Choice") in events
        results.append(events)
        button.hide()
    assert results[0] == results[1]


def paint_state(button, state, active=QStyle.SC_ToolButton):
    option = option_for(button)
    option.state = state
    option.activeSubControls = active
    image = QImage(button.size(), QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    button.style().drawComplexControl(QStyle.CC_ToolButton, option, painter, button)
    painter.end()
    return image


@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
@pytest.mark.parametrize("rtl", [False, True])
def test_theme_accent_split_pressed_focus_and_auto_raise(widgets, theme, rtl):
    button = widgets(theme=theme)
    button.resize(80, 30)
    button.setPopupMode(QToolButton.MenuButtonPopup)
    button.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
    palette = button.palette()
    palette.setColor(QPalette.Active, QPalette.Accent, QColor("#197F64"))
    palette.setColor(QPalette.Inactive, QPalette.Accent, QColor(theme.surface))
    button.setPalette(palette)
    enabled = QStyle.State_Enabled
    main = sub_rect(button, QStyle.SC_ToolButton).center()
    menu = sub_rect(button, QStyle.SC_ToolButtonMenu)
    menu_point = QPoint(menu.center().x(), 5)
    idle = paint_state(button, enabled)
    assert idle.pixelColor(main) == QColor(theme.surface)
    hover = paint_state(button, enabled | QStyle.State_MouseOver)
    assert hover.pixelColor(main) != idle.pixelColor(main)
    pressed = paint_state(button, enabled | QStyle.State_Sunken, QStyle.SC_ToolButtonMenu)
    assert pressed.pixelColor(main) == idle.pixelColor(main)
    assert pressed.pixelColor(menu_point) != idle.pixelColor(menu_point)
    assert paint_state(button, enabled | QStyle.State_On).pixelColor(main) == QColor("#197F64")
    button.setTheme(replace(theme, accent="#9944CC"))
    assert paint_state(button, enabled | QStyle.State_On).pixelColor(main) == QColor("#9944CC")
    assert paint_state(button, QStyle.State_On).pixelColor(main) == QColor(theme.border)
    flat = paint_state(button, enabled | QStyle.State_AutoRaise)
    assert flat.pixelColor(main).alpha() == 0
    focused = paint_state(
        button, enabled | QStyle.State_HasFocus | QStyle.State_KeyboardFocusChange
    )
    assert focused != idle
    assert focused.pixelColor(menu_point) == idle.pixelColor(menu_point)


@pytest.mark.parametrize("orientation", [Qt.Horizontal, Qt.Vertical])
def test_toolbar_parent_and_keyword_properties(widgets, orientation):
    toolbar = widgets(QToolBar)
    toolbar.setOrientation(orientation)
    toolbar.setIconSize(QSize(28, 28))
    button = widgets(parent=toolbar, text="Tools", checkable=True, checked=True, autoRaise=True)
    native = widgets(
        QToolButton, parent=toolbar, text="Tools", checkable=True, checked=True, autoRaise=True
    )
    assert isinstance(button, QToolButton) and button.isChecked() and button.autoRaise()
    assert option_for(button).iconSize == option_for(native).iconSize == QSize(28, 28)
    assert button.sizeHint() == native.sizeHint()
    with pytest.raises(TypeError, match="theme must be"):
        button.setTheme("dark")
    with pytest.raises(TypeError, match="theme must be"):
        widgets(theme="dark")


def test_gallery_contains_all_styles_and_popup_modes(widgets):
    from examples.navigation_view_example import ExampleWindow

    window = widgets(ExampleWindow)
    page = window._create_tool_button_page()
    page.setParent(window)
    buttons = page.findChildren(ModernToolButton)
    assert len(buttons) == 24
    assert {b.toolButtonStyle() for b in buttons} == set(_STYLES)
    assert {b.popupMode() for b in buttons} == set(_POPUPS)
    assert any(b.autoRaise() for b in buttons)
    assert all(b.defaultAction() for b in buttons)
    assert {b.arrowType() for b in buttons} == set(Qt.ArrowType)


@pytest.mark.parametrize(
    "arrow", [Qt.NoArrow, Qt.UpArrow, Qt.DownArrow, Qt.LeftArrow, Qt.RightArrow]
)
def test_ancestor_stylesheet_does_not_skip_themed_surface(widgets, arrow):
    host = widgets(QWidget)
    host.setObjectName("Host")
    host.setStyleSheet("QWidget#Host { background: #123456; }")
    button = widgets(parent=host, theme=replace(LIGHT_THEME, surface="#ABCD45"))
    button.setArrowType(arrow)
    button.resize(button.sizeHint())
    image = button.grab().toImage()
    dpr = image.devicePixelRatio()
    assert image.pixelColor(round(4 * dpr), round(4 * dpr)) == QColor("#ABCD45")
