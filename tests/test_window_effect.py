from __future__ import annotations

import ctypes
from ctypes import POINTER, c_int

from pyside6_modern_widgets import ThemeMode, WindowEffect, WindowMaterial


class _FakeDwmApi:
    def __init__(self, *, failed_attribute: int | None = None) -> None:
        self.failed_attribute = failed_attribute
        self.extended = False
        self.attributes: list[tuple[int, int]] = []

    def DwmExtendFrameIntoClientArea(self, _handle, _margins) -> int:
        self.extended = True
        return 0

    def DwmSetWindowAttribute(self, _handle, attribute, value, _size) -> int:
        native_value = ctypes.cast(value, POINTER(c_int)).contents.value
        self.attributes.append((attribute, native_value))
        return -1 if attribute == self.failed_attribute else 0


def _supported_effect(fake_dwm: _FakeDwmApi) -> WindowEffect:
    effect = WindowEffect()
    effect._dwmapi = fake_dwm
    effect.is_supported = True
    effect.is_transparency_enabled = lambda: True
    return effect


def test_apply_resolves_auto_and_sets_native_attributes() -> None:
    fake_dwm = _FakeDwmApi()
    effect = _supported_effect(fake_dwm)

    assert effect.apply(123, WindowMaterial.AUTO, ThemeMode.LIGHT)
    assert fake_dwm.extended
    assert (20, 0) in fake_dwm.attributes
    assert (38, int(WindowMaterial.MICA)) in fake_dwm.attributes
    assert (33, 2) in fake_dwm.attributes


def test_apply_reports_failed_hresult() -> None:
    fake_dwm = _FakeDwmApi(failed_attribute=38)
    effect = _supported_effect(fake_dwm)

    assert not effect.apply(123, WindowMaterial.ACRYLIC, ThemeMode.DARK)
    assert (20, 1) in fake_dwm.attributes
    assert (38, int(WindowMaterial.ACRYLIC)) in fake_dwm.attributes


def test_none_clears_effect_even_when_transparency_is_disabled() -> None:
    fake_dwm = _FakeDwmApi()
    effect = _supported_effect(fake_dwm)
    effect.is_transparency_enabled = lambda: False

    assert not effect.apply(123, WindowMaterial.MICA)
    assert effect.apply(123, WindowMaterial.NONE)
    assert fake_dwm.attributes == [(38, int(WindowMaterial.NONE))]


def test_compute_style_is_independent_from_native_application() -> None:
    native = WindowEffect.compute_style(
        is_maximized=False,
        is_active=True,
        corner_radius=10,
        effect_applied=True,
    )
    fallback = WindowEffect.compute_style(
        is_maximized=True,
        is_active=True,
        corner_radius=10,
        effect_applied=False,
    )

    assert native.bg_color == "rgba(255, 255, 255, 0.01)"
    assert not native.use_watercolor
    assert fallback.bg_color == "transparent"
    assert fallback.corner_radius == 0
    assert fallback.use_watercolor


def test_compute_style_uses_dark_qt_colors() -> None:
    native = WindowEffect.compute_style(
        is_maximized=False,
        is_active=False,
        corner_radius=10,
        effect_applied=True,
        theme=ThemeMode.DARK,
    )
    fallback = WindowEffect.compute_style(
        is_maximized=False,
        is_active=True,
        corner_radius=10,
        effect_applied=False,
        theme=ThemeMode.AUTO,
        system_dark=True,
    )

    assert native.bg_color == "rgb(43, 43, 43)"
    assert native.text_color == "#F5F5F5"
    assert fallback.bg_color == "rgb(32, 32, 32)"
    assert fallback.text_color == "#F5F5F5"
