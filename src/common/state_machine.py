from collections import deque
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


def transition_path[StateT: StrEnum](
    current: StateT,
    target: StateT,
    transitions: Mapping[StateT, frozenset[StateT]],
) -> list[StateT]:
    previous: dict[StateT, StateT | None] = {current: None}
    queue = deque([current])
    while queue:
        state = queue.popleft()
        if state == target:
            break
        for following in sorted(transitions.get(state, frozenset())):
            if following not in previous:
                previous[following] = state
                queue.append(following)
    if target not in previous or target == current:
        raise InvalidStateTransition(current, target)
    path: list[StateT] = []
    step: StateT | None = target
    while step is not None and step != current:
        path.append(step)
        step = previous[step]
    return path[::-1]
