"""Immutable values shared by notification handles and their Qt views."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from PySide6.QtGui import QIcon


class NotificationKind(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationState(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    VISIBLE = "visible"
    SUSPENDED = "suspended"
    CLOSED = "closed"


@dataclass(frozen=True)
class NotificationAction:
    id: str
    text: str
    close_on_trigger: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("action id must be a non-empty string")
        if not isinstance(self.text, str):
            raise TypeError("action text must be a string")
        if not isinstance(self.close_on_trigger, bool):
            raise TypeError("close_on_trigger must be a bool")


@dataclass(frozen=True)
class NotificationSnapshot:
    """Accepted content and lifecycle state, independent of the QWidget lifetime.

    timeout_ms is the configured timeout, not the remaining time. The optional
    icon is copied when taking a snapshot, so modifying it cannot change a card.
    """

    id: str
    title: str
    message: str
    kind: NotificationKind
    timeout_ms: int | None
    actions: tuple[NotificationAction, ...]
    progress: int | None
    icon: QIcon | None
    state: NotificationState = NotificationState.PENDING
    close_reason: str | None = None
    timeout_paused: bool = False


class _Unset(Enum):
    VALUE = 0


_UNSET = _Unset.VALUE


def _timeout(value: int | None) -> int | None:
    if value is not None and (type(value) is not int or not 1 <= value <= 2_147_483_647):
        raise ValueError("timeout_ms must be None or an integer from 1 to 2147483647")
    return value


def _actions(values: Iterable[NotificationAction]) -> tuple[NotificationAction, ...]:
    result = tuple(values)
    if any(not isinstance(action, NotificationAction) for action in result):
        raise TypeError("actions must contain NotificationAction values")
    if len({action.id for action in result}) != len(result):
        raise ValueError("action IDs must be unique within a notification")
    return result


def _patch(
    *,
    title: str | _Unset = _UNSET,
    message: str | _Unset = _UNSET,
    kind: NotificationKind | str | _Unset = _UNSET,
    timeout_ms: int | None | _Unset = _UNSET,
    actions: Iterable[NotificationAction] | _Unset = _UNSET,
    progress: int | None | _Unset = _UNSET,
    icon: QIcon | None | _Unset = _UNSET,
) -> dict:
    result: dict = {}
    for name, text in (("title", title), ("message", message)):
        if not isinstance(text, _Unset):
            if not isinstance(text, str):
                raise TypeError(f"{name} must be a string")
            result[name] = text
    if not isinstance(kind, _Unset):
        result["kind"] = NotificationKind(kind)
    if not isinstance(timeout_ms, _Unset):
        result["timeout_ms"] = _timeout(timeout_ms)
    if not isinstance(actions, _Unset):
        result["actions"] = _actions(actions)
    if not isinstance(progress, _Unset):
        if progress is not None and (type(progress) is not int or not -1 <= progress <= 100):
            raise ValueError("progress must be None or an integer from -1 to 100")
        result["progress"] = progress
    if not isinstance(icon, _Unset):
        if icon is not None and not isinstance(icon, QIcon):
            raise TypeError("icon must be a QIcon or None")
        result["icon"] = QIcon(icon) if icon is not None else None
    return result
