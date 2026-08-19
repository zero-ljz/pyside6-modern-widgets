"""PyInstaller hook for pyside6-modern-widgets."""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files(
    "pyside6_modern_widgets",
    includes=["resources.qrc", "resources/icons/*.png"],
)
hiddenimports = ["pyside6_modern_widgets._resources"]
