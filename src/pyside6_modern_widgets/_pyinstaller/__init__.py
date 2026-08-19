"""PyInstaller hook registration."""

from pathlib import Path


def get_hook_dirs() -> list[str]:
    """Return the directory containing this package's PyInstaller hooks."""
    return [str(Path(__file__).resolve().parent)]
