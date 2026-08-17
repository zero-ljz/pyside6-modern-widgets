"""Windows DWM effects with a graceful painted fallback."""

from __future__ import annotations

import ctypes
import platform
import sys
from contextlib import suppress
from ctypes import Structure, byref, c_int, sizeof
from dataclasses import dataclass
from enum import Enum, IntEnum

if sys.platform == "win32":
    import winreg
else:  # pragma: no cover - exercised by non-Windows consumers
    winreg = None  # type: ignore[assignment]


class _Margins(Structure):
    _fields_ = [
        ("cxLeftWidth", c_int),
        ("cxRightWidth", c_int),
        ("cyTopHeight", c_int),
        ("cyBottomHeight", c_int),
    ]


class WindowMaterial(IntEnum):
    """Native Windows system-backdrop materials."""

    AUTO = 0
    NONE = 1
    MICA = 2
    ACRYLIC = 3
    MICA_ALT = 4


class ThemeMode(str, Enum):
    """Theme mode shared by native backdrops and modern widgets."""

    AUTO = "auto"
    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True, slots=True)
class WindowStyleState:
    """Visual state computed for a modern window."""

    bg_color: str
    text_color: str
    corner_radius: int
    use_watercolor: bool


class WindowEffect:
    """Apply Windows 11 Mica/Acrylic effects when the system supports them."""

    def __init__(self) -> None:
        self.build_version = self._windows_build()
        self._dwmapi = self._load_dwmapi()
        self.is_supported = self._dwmapi is not None and self.build_version >= 22621

    @staticmethod
    def _windows_build() -> int:
        if sys.platform != "win32":
            return 0
        try:
            return int(platform.version().split(".")[-1])
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _load_dwmapi():
        if sys.platform != "win32":
            return None
        try:
            return ctypes.windll.dwmapi
        except (AttributeError, OSError):
            return None

    @staticmethod
    def _personalization_value(name: str, default: int) -> int:
        if winreg is None:
            return default
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            ) as key:
                value, _ = winreg.QueryValueEx(key, name)
                return int(value)
        except (OSError, TypeError, ValueError):
            return default

    def is_system_dark_mode(self) -> bool:
        return self._personalization_value("AppsUseLightTheme", 1) == 0

    def is_transparency_enabled(self) -> bool:
        return self._personalization_value("EnableTransparency", 1) == 1

    @staticmethod
    def _succeeded(result: int) -> bool:
        return int(result) >= 0

    def apply(
        self,
        hwnd: int,
        material: WindowMaterial | int = WindowMaterial.AUTO,
        theme: ThemeMode | str = ThemeMode.AUTO,
    ) -> bool:
        """Apply a backdrop to a native handle and report whether DWM accepted it."""
        material = WindowMaterial(material)
        theme = ThemeMode(theme)
        if material is WindowMaterial.AUTO:
            material = WindowMaterial.MICA

        if not self.is_supported or self._dwmapi is None:
            return False
        if material is not WindowMaterial.NONE and not self.is_transparency_enabled():
            return False

        handle = ctypes.c_void_p(hwnd)
        try:
            if material is WindowMaterial.NONE:
                material_value = c_int(int(material))
                result = self._dwmapi.DwmSetWindowAttribute(
                    handle, 38, byref(material_value), sizeof(material_value)
                )
                return self._succeeded(result)

            margins = _Margins(-1, -1, -1, -1)
            extend_result = self._dwmapi.DwmExtendFrameIntoClientArea(
                handle, byref(margins)
            )
            is_dark = (
                theme is ThemeMode.DARK
                or (theme is ThemeMode.AUTO and self.is_system_dark_mode())
            )
            dark_value = c_int(int(is_dark))
            dark_result = self._dwmapi.DwmSetWindowAttribute(
                handle, 20, byref(dark_value), sizeof(dark_value)
            )
            material_value = c_int(int(material))
            material_result = self._dwmapi.DwmSetWindowAttribute(
                handle, 38, byref(material_value), sizeof(material_value)
            )
        except (AttributeError, OSError):
            return False
        if not all(
            self._succeeded(result)
            for result in (extend_result, dark_result, material_result)
        ):
            return False
        self._set_rounded_corners(hwnd)
        return True

    @staticmethod
    def compute_style(
        *,
        is_maximized: bool,
        is_active: bool,
        corner_radius: int,
        effect_applied: bool,
        theme: ThemeMode | str = ThemeMode.LIGHT,
        system_dark: bool = False,
        bg_color: str | None = None,
        text_color: str | None = None,
    ) -> WindowStyleState:
        """Compute the Qt-side appearance without changing native window state."""
        radius = 0 if is_maximized else max(0, corner_radius)
        use_watercolor = not effect_applied
        theme = ThemeMode(theme)
        is_dark = theme is ThemeMode.DARK or (
            theme is ThemeMode.AUTO and system_dark
        )

        if bg_color is None:
            if effect_applied:
                bg_color = (
                    "rgba(255, 255, 255, 0.01)"
                    if is_active
                    else ("rgb(43, 43, 43)" if is_dark else "rgb(243, 243, 243)")
                )
            else:
                bg_color = (
                    "rgb(32, 32, 32)"
                    if is_dark
                    else "transparent"
                    if is_active
                    else "rgb(243, 243, 243)"
                )

        return WindowStyleState(
            bg_color=bg_color,
            text_color=text_color or ("#F5F5F5" if is_dark else "#202020"),
            corner_radius=radius,
            use_watercolor=use_watercolor,
        )

    def _set_rounded_corners(self, hwnd: int) -> None:
        if self._dwmapi is None:
            return
        value = c_int(2)
        with suppress(AttributeError, OSError):
            self._dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), 33, byref(value), sizeof(value)
            )
