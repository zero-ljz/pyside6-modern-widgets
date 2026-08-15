"""Windows DWM effects with a graceful painted fallback."""

from __future__ import annotations

import ctypes
import platform
import sys
from ctypes import Structure, byref, c_int, sizeof
from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class WindowStyleState:
    """Visual state computed for a modern window."""

    bg_color: str
    text_color: str
    corner_radius: int
    use_watercolor: bool


class WindowEffect:
    """Apply Windows 11 Mica/Acrylic effects when the system supports them."""

    MATERIAL_NONE = 1
    MATERIAL_MICA = 2
    MATERIAL_ACRYLIC = 3
    MATERIAL_MICA_ALT = 4

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

    def set_effect(self, hwnd: int, material_type: int, theme_mode: str = "auto") -> bool:
        if not self.is_supported or self._dwmapi is None:
            return False

        handle = ctypes.c_void_p(hwnd)
        margins = _Margins(-1, -1, -1, -1)
        try:
            self._dwmapi.DwmExtendFrameIntoClientArea(handle, byref(margins))
            is_dark = (
                theme_mode == "dark"
                or (theme_mode == "auto" and self.is_system_dark_mode())
            )
            dark_value = c_int(int(is_dark))
            self._dwmapi.DwmSetWindowAttribute(
                handle, 20, byref(dark_value), sizeof(dark_value)
            )
            material_value = c_int(material_type)
            self._dwmapi.DwmSetWindowAttribute(
                handle, 38, byref(material_value), sizeof(material_value)
            )
        except (AttributeError, OSError):
            return False
        return True

    def compute_style(
        self,
        *,
        is_maximized: bool,
        is_active: bool,
        hwnd: int,
        corner_radius: int,
        bg_color: str | None = None,
        text_color: str | None = None,
    ) -> WindowStyleState:
        radius = 0 if is_maximized else max(0, corner_radius)
        mica_enabled = self.is_supported and self.is_transparency_enabled()
        use_watercolor = not mica_enabled

        if bg_color is None:
            if mica_enabled:
                self.set_effect(hwnd, self.MATERIAL_MICA, "light")
                self._set_rounded_corners(hwnd)
                bg_color = (
                    "rgba(255, 255, 255, 0.01)"
                    if is_active
                    else "rgb(243, 243, 243)"
                )
            else:
                bg_color = "transparent" if is_active else "rgb(243, 243, 243)"

        return WindowStyleState(
            bg_color=bg_color,
            text_color=text_color or "black",
            corner_radius=radius,
            use_watercolor=use_watercolor,
        )

    def _set_rounded_corners(self, hwnd: int) -> None:
        if self._dwmapi is None:
            return
        value = c_int(2)
        try:
            self._dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), 33, byref(value), sizeof(value)
            )
        except (AttributeError, OSError):
            pass
