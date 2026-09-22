from collections.abc import Mapping
from enum import StrEnum


class InvalidStateTransition(ValueError):
    def __init__(self, current: StrEnum, target: StrEnum) -> None:
        super().__init__(f"Transition {current.value} -> {target.value} is not allowed")
        self.current = current
        self.target = target


def ensure_transition[StateT: StrEnum](
    current: StateT,
    target: StateT,
    transitions: Mapping[StateT, frozenset[StateT]],
) -> None:
    if target not in transitions.get(current, frozenset()):
        raise InvalidStateTransition(current, target)
