from __future__ import annotations

import ctypes
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QWidget

from pyside6_modern_widgets import (
    ModernComboBox,
    ModernFlyout,
    ModernFontComboBox,
    ModernMenu,
    ModernMenuBar,
    ModernNotification,
    ModernToolBar,
    NotificationManager,
    modern_combo_box,
    modern_flyout,
    modern_menu,
    modern_notification,
)

_APP = QApplication.instance() or QApplication([])


def test_native_acrylic_policy_can_be_disabled(monkeypatch):
    class AccentPolicy(ctypes.Structure):
        _fields_ = [
            ("state", ctypes.c_int),
            ("flags", ctypes.c_int),
            ("gradient_color", ctypes.c_uint),
            ("animation_id", ctypes.c_int),
        ]

    class WindowCompositionAttributeData(ctypes.Structure):
        _fields_ = [
            ("attribute", ctypes.c_int),
            ("data", ctypes.c_void_p),
            ("size", ctypes.c_size_t),
        ]

    policies = []

    def set_attribute(_hwnd, data_ptr):
        data = ctypes.cast(data_ptr, ctypes.POINTER(WindowCompositionAttributeData)).contents
        accent = ctypes.cast(data.data, ctypes.POINTER(AccentPolicy)).contents
        policies.append((data.attribute, accent.state, accent.flags, accent.gradient_color))
        return True

    monkeypatch.setattr(modern_menu, "_supports_windows_acrylic", lambda: True)
    monkeypatch.setattr(
        ctypes,
        "windll",
        SimpleNamespace(user32=SimpleNamespace(SetWindowCompositionAttribute=set_attribute)),
        raising=False,
    )
    widget = QWidget()
    assert modern_menu._enable_windows_acrylic(widget)
    assert modern_menu._disable_windows_acrylic(widget)
    assert policies[0][:3] == (19, 4, 2)
    assert policies[1] == (19, 0, 0, 0)


def test_menu_toggle_updates_native_state_and_owned_submenus(monkeypatch):
    calls = []
    monkeypatch.setattr(modern_menu, "_enable_windows_rounded_corners", lambda *_args: True)
    monkeypatch.setattr(
        modern_menu, "_enable_windows_acrylic", lambda widget: calls.append("on") or True
    )
    monkeypatch.setattr(
        modern_menu, "_disable_windows_acrylic", lambda widget: calls.append("off") or True
    )
    menu = ModernMenu(acrylic=False)
    submenu = menu.addMenu("Nested")
    menu.addAction("Open")
    menu.show()
    _APP.processEvents()
    try:
        assert menu.isAcrylicEnabled() is False
        assert submenu.isAcrylicEnabled() is False
        assert menu._rounded_style._native_acrylic is False
        assert "on" not in calls
        menu.setAcrylicEnabled(True)
        assert menu._rounded_style._native_acrylic is True
        assert submenu.isAcrylicEnabled() is True
        menu.setAcrylicEnabled(False)
        assert menu._rounded_style._native_acrylic is False
        assert calls[-1] == "off"
    finally:
        menu.close()


def test_combo_popups_can_toggle_acrylic(monkeypatch):
    for combo_class in (ModernComboBox, ModernFontComboBox):
        calls = []
        monkeypatch.setattr(
            modern_combo_box, "_enable_windows_rounded_corners", lambda *_args, **_kwargs: True
        )
        monkeypatch.setattr(
            modern_combo_box,
            "_enable_windows_acrylic",
            lambda widget, calls=calls: calls.append("on") or True,
        )
        monkeypatch.setattr(
            modern_combo_box,
            "_disable_windows_acrylic",
            lambda widget, calls=calls: calls.append("off") or True,
        )
        combo = combo_class(acrylic=False)
        if isinstance(combo, ModernComboBox):
            combo.addItems(["One", "Two"])
        combo.show()
        combo.showPopup()
        _APP.processEvents()
        try:
            assert combo.isAcrylicEnabled() is False
            assert combo._modern_style._native_acrylic is False
            assert "on" not in calls
            combo.setAcrylicEnabled(True)
            combo._refresh_popup_acrylic()
            assert combo._modern_style._native_acrylic is True
            combo.setAcrylicEnabled(False)
            combo._refresh_popup_acrylic()
            assert combo._modern_style._native_acrylic is False
            assert calls[-1] == "off"
        finally:
            combo.hidePopup()
            combo.close()


def test_flyout_and_desktop_notification_toggle_acrylic(monkeypatch):
    for module, widget in (
        (modern_flyout, ModernFlyout(acrylic=False)),
        (modern_notification, ModernNotification(acrylic=False)),
    ):
        calls = []
        monkeypatch.setattr(module, "_enable_windows_rounded_corners", lambda *_args: True)
        monkeypatch.setattr(
            module, "_enable_windows_acrylic", lambda obj, calls=calls: calls.append("on") or True
        )
        monkeypatch.setattr(
            module, "_disable_windows_acrylic", lambda obj, calls=calls: calls.append("off") or True
        )
        if isinstance(widget, ModernNotification):
            widget._configure_desktop()
        widget.show()
        _APP.processEvents()
        try:
            assert widget.isAcrylicEnabled() is False
            assert widget._native_acrylic is False
            assert "on" not in calls
            widget.setAcrylicEnabled(True)
            assert widget._native_acrylic is True
            widget.setAcrylicEnabled(False)
            assert widget._native_acrylic is False
            assert calls[-1] == "off"
        finally:
            widget.close()


def test_containers_pass_acrylic_preference_to_their_popups():
    bar = ModernMenuBar(acrylic=False)
    menu = bar.addMenu("File")
    submenu = menu.addMenu("Recent")
    toolbar = ModernToolBar(acrylic=False)
    assert not menu.isAcrylicEnabled()
    assert not submenu.isAcrylicEnabled()
    assert not toolbar.overflowMenu().isAcrylicEnabled()
    bar.setAcrylicEnabled(True)
    toolbar.setAcrylicEnabled(True)
    assert menu.isAcrylicEnabled() and submenu.isAcrylicEnabled()
    assert toolbar.overflowMenu().isAcrylicEnabled()


def test_manager_passes_preference_to_existing_and_future_cards():
    host = QWidget()
    manager = NotificationManager(host, desktop=False, acrylic=False)
    first = manager.post("First", "Message")
    _APP.processEvents()
    assert first.widget() is not None
    assert not first.widget().isAcrylicEnabled()
    manager.setAcrylicEnabled(True)
    assert first.widget().isAcrylicEnabled()
    second = manager.post("Second", "Message")
    _APP.processEvents()
    assert second.widget() is not None
    assert second.widget().isAcrylicEnabled()
    manager.clear()
