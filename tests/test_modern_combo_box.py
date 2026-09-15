from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QIntValidator,
    QPainter,
    QPalette,
    QStandardItem,
    QStandardItemModel,
    QWheelEvent,
)
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCompleter,
    QFrame,
    QLineEdit,
    QListView,
    QStyle,
    QStyledItemDelegate,
    QStyleFactory,
    QStyleOptionComboBox,
)

from pyside6_modern_widgets import (
    DARK_THEME,
    LIGHT_THEME,
    ModernComboBox,
    ModernWindow,
    ThemeMode,
    palette_for_theme,
)
from pyside6_modern_widgets import modern_combo_box as combo_module
from pyside6_modern_widgets.modern_menu import (
    _ACRYLIC_INPUT_ALPHA,
    _MENU_ITEM_EXTRA_HEIGHT,
    _MENU_VERTICAL_MARGIN,
)

_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def combos():
    widgets = [QComboBox(), ModernComboBox()]
    for combo in widgets:
        combo.addItems(["Alpha", "Beta", "Gamma"])
        combo.resize(240, 36)
    yield widgets
    for combo in widgets:
        combo.hidePopup()
        combo.close()
        combo.deleteLater()
    _APP.processEvents()


def _signals(combo):
    events = []
    combo.currentIndexChanged.connect(lambda value: events.append(("index", value)))
    combo.currentTextChanged.connect(lambda value: events.append(("text", value)))
    combo.activated.connect(lambda value: events.append(("activated", value)))
    return events


def test_data_and_programmatic_signals_match_qcombobox(combos):
    results = []
    for combo in combos:
        events = _signals(combo)
        combo.setItemData(1, {"id": 42})
        combo.setCurrentIndex(1)
        assert combo.currentData() == {"id": 42}
        combo.insertItem(0, "First", 7)
        combo.setItemText(combo.currentIndex(), "Renamed")
        combo.removeItem(0)
        combo.setCurrentText("Gamma")
        combo.clear()
        combo.setPlaceholderText("Choose an item")
        assert combo.currentIndex() == -1
        results.append(events)
    assert results[0] == results[1]
    assert not any(name == "activated" for name, value in results[1])


@pytest.mark.parametrize("editable", [False, True])
@pytest.mark.parametrize("dismiss", [Qt.Key.Key_Return, Qt.Key.Key_Escape])
def test_popup_keyboard_signals_match_qcombobox(combos, editable, dismiss):
    results = []
    for combo in combos:
        combo.setEditable(editable)
        combo.show()
        combo.setFocus()
        _APP.processEvents()
        events = _signals(combo)
        combo.showPopup()
        _APP.processEvents()
        QTest.keyClick(combo.view(), Qt.Key.Key_Down)
        QTest.keyClick(combo.view(), dismiss)
        _APP.processEvents()
        results.append((combo.currentIndex(), combo.currentText(), events))
        assert not combo.view().isVisible()
        combo.hide()
    assert results[0] == results[1]


@pytest.mark.parametrize("editable", [False, True])
def test_popup_mouse_selection_preserves_activation(combos, editable):
    results = []
    for combo in combos:
        combo.setEditable(editable)
        combo.show()
        events = _signals(combo)
        combo.showPopup()
        _APP.processEvents()
        rect = combo.view().visualRect(combo.model().index(2, 0))
        QTest.mouseClick(combo.view().viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
        _APP.processEvents()
        results.append((combo.currentIndex(), events))
        combo.hidePopup()
        combo.hide()
    assert results[0] == results[1]
    assert results[1][0] == 2
    assert ("activated", 2) in results[1][1]


def test_closed_keyboard_search_separators_disabled_items_and_wheel_match(combos):
    results = []
    for combo in combos:
        combo.insertSeparator(1)
        combo.model().item(2).setEnabled(False)
        combo.show()
        combo.setFocus()
        events = _signals(combo)
        QTest.keyClick(combo, Qt.Key.Key_Down)
        assert combo.currentText() == "Gamma"
        QTest.keyClicks(combo, "a")
        wheel = QWheelEvent(
            QPointF(10, 10),
            QPointF(combo.mapToGlobal(QPoint(10, 10))),
            QPoint(),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        _APP.sendEvent(combo, wheel)
        results.append((combo.currentIndex(), events))
        combo.hide()
    assert results[0] == results[1]


def test_editing_validator_completer_and_insert_policy_match(combos):
    results = []
    for combo in combos:
        combo.clear()
        combo.addItems(["10", "20"])
        combo.setEditable(True)
        editor = QLineEdit(combo)
        combo.setLineEdit(editor)
        validator = QIntValidator(0, 100, combo)
        completer = QCompleter(["10", "20"], combo)
        combo.setValidator(validator)
        combo.setCompleter(completer)
        combo.setInsertPolicy(QComboBox.InsertPolicy.InsertAtBottom)
        combo.show()
        events = _signals(combo)
        editor.selectAll()
        QTest.keyClicks(editor, "42")
        QTest.keyClick(editor, Qt.Key.Key_Return)
        assert combo.lineEdit() is editor
        assert combo.validator() is validator
        assert combo.completer() is completer
        results.append((combo.currentText(), combo.count(), events))
        combo.hide()
    assert results[0] == results[1]
    assert results[1][:2] == ("42", 3)


def test_custom_model_root_column_view_and_delegate_survive_theme_changes(theme_manager_instance):
    combo = ModernComboBox()
    model = QStandardItemModel(combo)
    root = QStandardItem("Root")
    root.appendRow([QStandardItem("id"), QStandardItem("Display")])
    model.appendRow(root)
    combo.setModel(model)
    combo.setRootModelIndex(root.index())
    combo.setModelColumn(1)
    view = QListView()
    combo.setView(view)
    delegate = QStyledItemDelegate(combo)
    combo.setItemDelegate(delegate)
    combo.show()
    combo.showPopup()
    theme_manager_instance.setMode(ThemeMode.DARK)
    _APP.processEvents()
    assert combo.model() is model
    assert combo.view() is view
    assert combo.itemDelegate() is delegate
    assert combo.currentText() == "Display"
    assert view.palette().color(QPalette.ColorRole.Base) == QColor(DARK_THEME.surface)
    combo.hidePopup()
    combo.close()


def test_parent_and_local_theme_overrides(theme_manager_instance):
    window = ModernWindow()
    combo = ModernComboBox(window)
    window.setTheme(DARK_THEME)
    assert combo.theme() == DARK_THEME
    assert combo.palette().color(QPalette.ColorRole.Base) == QColor(DARK_THEME.surface)
    combo.setTheme(LIGHT_THEME)
    theme_manager_instance.setMode(ThemeMode.DARK)
    assert combo.theme() == LIGHT_THEME
    combo.setTheme(None)
    assert combo.theme() == DARK_THEME
    combo.setParent(None)
    theme_manager_instance.setMode(ThemeMode.LIGHT)
    assert combo.theme() == LIGHT_THEME
    combo.close()
    window.close()


def test_rtl_geometry_and_large_font_do_not_overlap(combos):
    combo = combos[1]
    font = combo.font()
    font.setPointSize(24)
    combo.setFont(font)
    combo.resize(combo.sizeHint())
    assert combo.height() >= combo.fontMetrics().height() + 8
    for direction in (Qt.LayoutDirection.LeftToRight, Qt.LayoutDirection.RightToLeft):
        combo.setLayoutDirection(direction)
        option = QStyleOptionComboBox()
        combo.initStyleOption(option)
        arrow = combo.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, option, QStyle.SubControl.SC_ComboBoxArrow, combo
        )
        field = combo.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, option, QStyle.SubControl.SC_ComboBoxEditField, combo
        )
        assert not arrow.intersects(field)
        assert (arrow.center().x() > field.center().x()) == (
            direction == Qt.LayoutDirection.LeftToRight
        )


@pytest.mark.parametrize("editable", [False, True])
def test_popup_retains_qt_container_and_uses_menu_row_spacing(combos, editable):
    native, modern = combos
    native_style = QStyleFactory.create("Fusion")
    native_style.setParent(native)
    native.setStyle(native_style)
    heights = []
    for combo in (native, modern):
        # Both modern modes now use the ordinary menu's vertical padding.
        combo.setEditable(editable if combo is modern else False)
        original_popup = combo.view().window()
        original_delegate = combo.itemDelegate()
        original_margins = original_popup.contentsMargins()
        combo.show()
        combo.showPopup()
        _APP.processEvents()
        view = combo.view()
        popup = view.window()
        assert popup is original_popup
        assert combo.itemDelegate() is original_delegate
        if combo is modern and editable:
            original_margins.setTop(original_margins.top() + _MENU_VERTICAL_MARGIN)
            original_margins.setBottom(original_margins.bottom() + _MENU_VERTICAL_MARGIN)
        assert popup.contentsMargins() == original_margins
        assert popup.windowType() == Qt.WindowType.Popup
        heights.append(view.visualRect(combo.model().index(0, 0)).height())
        combo.hidePopup()
        combo.hide()
    assert heights[1] == heights[0] + _MENU_ITEM_EXTRA_HEIGHT


@pytest.mark.parametrize("editable", [False, True])
@pytest.mark.parametrize("acrylic", [False, True])
def test_popup_surface_remains_clickable_and_refreshes_acrylic_tint(
    combos, monkeypatch, editable, acrylic
):
    combo = combos[1]
    combo.setTheme(LIGHT_THEME)
    combo.setEditable(editable)
    tints = []
    monkeypatch.setattr(
        combo_module, "_enable_windows_rounded_corners", lambda *args, **kwargs: acrylic
    )

    def enable_acrylic(popup, *, enabled=True):
        if enabled:
            tints.append(popup.palette().color(QPalette.ColorRole.Window))
        return enabled

    monkeypatch.setattr(combo_module, "_enable_windows_acrylic", enable_acrylic)
    combo.show()
    combo.showPopup()
    _APP.processEvents()
    popup = combo.view().window()
    for theme in (LIGHT_THEME, DARK_THEME):
        combo.setTheme(theme)
        _APP.processEvents()
        assert combo._modern_style._native_acrylic == (acrylic and not editable)
        if acrylic and not editable:
            assert tints[-1] == QColor(theme.surface)
        pixmap = popup.grab()
        scale = pixmap.devicePixelRatio()
        image = pixmap.toImage()
        row = combo.view().visualRect(combo.model().index(1, 0))
        point = combo.view().viewport().mapTo(popup, QPoint(180, row.center().y()))
        alpha = image.pixelColor(round(point.x() * scale), round(point.y() * scale)).alpha()
        assert alpha == (_ACRYLIC_INPUT_ALPHA if acrylic and not editable else 255)
        corner_y = image.height() - 1 if editable else 0
        assert image.pixelColor(0, corner_y).alpha() == 0


@pytest.mark.parametrize("editable", [False, True])
@pytest.mark.parametrize("effect_enabled", [False, True])
def test_popup_preserves_animation_preference(combos, monkeypatch, editable, effect_enabled):
    combo = combos[1]
    combo.setEditable(editable)
    state = {"enabled": effect_enabled}
    monkeypatch.setattr(QApplication, "isEffectEnabled", lambda effect: state["enabled"])
    monkeypatch.setattr(
        QApplication, "setEffectEnabled", lambda effect, enabled: state.update(enabled=enabled)
    )
    native_show = QComboBox.showPopup
    during_show = []

    def observe_show(widget):
        during_show.append(state["enabled"])
        native_show(widget)

    monkeypatch.setattr(QComboBox, "showPopup", observe_show)
    combo.show()
    for _ in range(2):
        combo.showPopup()
        assert state["enabled"] == effect_enabled
        combo.hidePopup()
    assert during_show == [effect_enabled and not editable] * 2


@pytest.mark.parametrize("editable", [False, True])
@pytest.mark.parametrize("theme", [LIGHT_THEME, DARK_THEME])
def test_focus_border_timing_and_color_match_native_rendering(combos, editable, theme):
    native, modern = combos
    native_style = QStyleFactory.create("Fusion")
    native_style.setParent(native)
    native.setStyle(native_style)
    modern.setTheme(theme)
    for combo in combos:
        combo.setEditable(editable)

    flag = QStyle.StateFlag
    states = (
        flag.State_None,
        flag.State_Enabled,
        flag.State_Enabled | flag.State_HasFocus,
        flag.State_Enabled | flag.State_HasFocus | flag.State_KeyboardFocusChange,
        flag.State_Enabled | flag.State_KeyboardFocusChange,
        flag.State_Enabled | flag.State_HasFocus | flag.State_On,
        flag.State_Enabled | flag.State_HasFocus | flag.State_On | flag.State_KeyboardFocusChange,
    )
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        for state in states:
            rendered = []
            for combo in combos:
                colors = []
                for accent in ("#0078d4", "#99d9ff"):
                    palette = palette_for_theme(theme)
                    palette.setColor(QPalette.ColorRole.Highlight, QColor(accent))
                    palette.setCurrentColorGroup(group)
                    option = QStyleOptionComboBox()
                    combo.initStyleOption(option)
                    option.rect = QRect(0, 0, 200, 32)
                    option.state = state
                    option.palette = palette
                    image = QImage(200, 32, QImage.Format.Format_ARGB32_Premultiplied)
                    image.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(image)
                    combo.style().drawComplexControl(
                        QStyle.ComplexControl.CC_ComboBox, option, painter, combo
                    )
                    painter.end()
                    colors.append(image.pixelColor(60, 0))
                rendered.append(colors)
            native_colors, modern_colors = rendered
            native_highlights = native_colors[0] != native_colors[1]
            modern_highlights = modern_colors[0] != modern_colors[1]
            assert modern_highlights == native_highlights, (editable, state, group)
            if native_highlights:
                assert modern_colors == native_colors


def test_explicit_palette_roles_survive_opening_and_theme_changes(combos):
    combo = combos[1]
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Text, QColor("#e02080"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#218342"))
    combo.setPalette(palette)
    combo.show()
    for theme in (LIGHT_THEME, DARK_THEME):
        combo.setTheme(theme)
        combo.showPopup()
        assert combo.palette().color(QPalette.ColorRole.Text) == QColor("#e02080")
        assert combo.palette().color(QPalette.ColorRole.Highlight) == QColor("#218342")
        assert combo.palette().color(QPalette.ColorRole.Base) == QColor(theme.surface)
        assert combo.view().palette().color(QPalette.ColorRole.Text) == QColor("#e02080")
        combo.hidePopup()
    combo.setPalette(QPalette())
    assert combo.palette().color(QPalette.ColorRole.Text) == QColor(DARK_THEME.text)


@pytest.mark.parametrize("replace_view", [False, True])
def test_view_configuration_is_not_overwritten_on_open(combos, replace_view):
    combo = combos[1]
    if replace_view:
        combo.setView(QListView())
    view = combo.view()
    style = QStyleFactory.create("Windows")
    style.setParent(view)
    view.setStyle(style)
    view.setFrameShape(QFrame.Shape.Box)
    view.setAutoFillBackground(True)
    view.viewport().setAutoFillBackground(True)
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Base, QColor("#c9def1"))
    view.setPalette(palette)
    combo.show()
    for theme in (LIGHT_THEME, DARK_THEME):
        combo.setTheme(theme)
        combo.showPopup()
        assert view.style() is style
        assert view.frameShape() == QFrame.Shape.Box
        assert view.autoFillBackground() and view.viewport().autoFillBackground()
        assert view.palette().color(QPalette.ColorRole.Base) == QColor("#c9def1")
        combo.hidePopup()


def _render_combo_control(combo, state):
    option = QStyleOptionComboBox()
    combo.initStyleOption(option)
    option.rect = QRect(0, 0, 240, 32)
    option.state = state
    image = QImage(240, 32, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    combo.style().drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option, painter, combo)
    painter.end()
    return image


def test_frameless_editable_combo_keeps_native_rendering(combos):
    native, modern = combos
    style = QStyleFactory.create("Fusion")
    style.setParent(native)
    native.setStyle(style)
    native.setPalette(modern.palette())
    for combo in combos:
        combo.setEditable(True)
        combo.setFrame(False)
    assert _render_combo_control(native, QStyle.StateFlag.State_Enabled) == _render_combo_control(
        modern, QStyle.StateFlag.State_Enabled
    )


@pytest.mark.parametrize("editable", [False, True])
def test_open_state_changes_control_surface(combos, editable):
    combo = combos[1]
    combo.setEditable(editable)
    combo.show()
    before = QStyleOptionComboBox()
    combo.initStyleOption(before)
    combo.showPopup()
    opened = QStyleOptionComboBox()
    combo.initStyleOption(opened)
    assert opened.state & QStyle.StateFlag.State_On
    neutral = _render_combo_control(combo, QStyle.StateFlag.State_Enabled)
    pressed = _render_combo_control(
        combo, QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_On
    )
    assert neutral.pixelColor(230, 8) != pressed.pixelColor(230, 8)
    if editable:
        assert neutral.pixelColor(120, 16) == pressed.pixelColor(120, 16)


@pytest.mark.parametrize("editable", [False, True])
def test_closed_layout_remains_native_with_only_two_extra_pixels(combos, editable):
    native, modern = combos
    style = QStyleFactory.create("Fusion")
    style.setParent(native)
    native.setStyle(style)
    for combo in combos:
        combo.setEditable(editable)
    assert modern.sizeHint().width() == native.sizeHint().width()
    assert modern.sizeHint().height() == native.sizeHint().height() + 2
    for direction in (Qt.LayoutDirection.LeftToRight, Qt.LayoutDirection.RightToLeft):
        for sub_control in (
            QStyle.SubControl.SC_ComboBoxEditField,
            QStyle.SubControl.SC_ComboBoxArrow,
        ):
            rectangles = []
            for combo in combos:
                combo.setLayoutDirection(direction)
                option = QStyleOptionComboBox()
                combo.initStyleOption(option)
                rectangles.append(
                    combo.style().subControlRect(
                        QStyle.ComplexControl.CC_ComboBox, option, sub_control, combo
                    )
                )
            assert rectangles[0] == rectangles[1]


@pytest.mark.parametrize("above", [False, True])
def test_editable_popup_squares_only_the_edge_facing_the_combo(combos, above):
    combo = combos[1]
    combo.setEditable(True)
    screen = combo.screen().availableGeometry()
    combo.move(screen.left() + 100, screen.bottom() - 50 if above else screen.top() + 50)
    combo.show()
    for _ in range(2):
        combo.showPopup()
        _APP.processEvents()
        popup = combo.view().window()
        assert combo._modern_style._square_top == (not above)
        assert popup.mask().isEmpty()
        image = popup.grab().toImage()
        near_y = image.height() - 1 if above else 0
        far_y = 0 if above else image.height() - 1
        assert image.pixelColor(0, near_y).alpha() > 0
        assert image.pixelColor(image.width() - 1, near_y).alpha() > 0
        assert image.pixelColor(0, far_y).alpha() == 0
        assert image.pixelColor(image.width() - 1, far_y).alpha() == 0
        combo.hidePopup()
    combo.setEditable(False)
    combo.showPopup()
    assert combo.view().window().mask().isEmpty()
    assert combo._modern_style._square_top is None
