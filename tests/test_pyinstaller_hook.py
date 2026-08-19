from __future__ import annotations

import runpy
from pathlib import Path

from pyside6_modern_widgets._pyinstaller import get_hook_dirs


def test_pyinstaller_hook_is_registered_and_collects_resources() -> None:
    hook_dirs = get_hook_dirs()
    assert len(hook_dirs) == 1

    hook_path = Path(hook_dirs[0]) / "hook-pyside6_modern_widgets.py"
    assert hook_path.is_file()

    hook = runpy.run_path(str(hook_path))
    assert "pyside6_modern_widgets._resources" in hook["hiddenimports"]

    collected_files = {Path(source).name for source, _destination in hook["datas"]}
    assert "resources.qrc" in collected_files
    assert "icons8-application-48.png" in collected_files
