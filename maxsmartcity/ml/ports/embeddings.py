"""Replaceable text embedding interface."""

from collections.abc import Sequence
from typing import Protocol

import numpy as np


class TextEmbeddingProvider(Protocol):
    """Turns texts into normalized dense vectors.

    Implementations may run locally or remotely. The semantic recommendation layer
    only depends on this protocol, so an unavailable model never blocks the core
    report workflow.
    """

    @property
    def model_name(self) -> str: ...

    def embed(self, texts: Sequence[str]) -> np.ndarray: ...
