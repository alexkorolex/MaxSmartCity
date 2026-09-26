"""Local ONNX text embeddings with a lazy optional dependency."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from threading import Lock
from typing import Protocol, cast

import httpx
import numpy as np

from src.ml.ports.models import ComponentUnavailableError

DEFAULT_MODEL = "maxsmartcity/multilingual-e5-small-int8"
_E5_SOURCE_MODEL = "Xenova/multilingual-e5-small"


class _EmbeddingModel(Protocol):
    def embed(self, documents: Sequence[str]) -> Iterable[np.ndarray]: ...


class FastEmbedProvider:
    """A small multilingual local model suitable for CPU inference."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        cache_dir: Path | None = None,
        threads: int | None = None,
    ) -> None:
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._threads = threads
        self._model: _EmbeddingModel | None = None
        self._load_lock = Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Backward-compatible query embedding used by smoke tests."""

        return self.embed_queries(texts)

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed(texts, prefix="query")

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed(texts, prefix="passage")

    def _embed(self, texts: Sequence[str], *, prefix: str) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        model = self._load()
        try:
            prepared = [f"{prefix}: {text}" for text in texts] if self._uses_e5_prefix else list(texts)
            vectors = np.asarray(list(model.embed(prepared)), dtype=np.float32)
        except (OSError, RuntimeError, ValueError) as exc:
            raise ComponentUnavailableError("LOCAL_EMBEDDING_INFERENCE_FAILED") from exc
        if vectors.ndim != 2 or vectors.shape[0] != len(texts):
            raise ComponentUnavailableError("LOCAL_EMBEDDING_OUTPUT_INVALID")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise ComponentUnavailableError("LOCAL_EMBEDDING_OUTPUT_ZERO_VECTOR")
        return vectors / norms

    def _load(self) -> _EmbeddingModel:
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is not None:
                return self._model
            return self._load_locked()

    def _load_locked(self) -> _EmbeddingModel:
        try:
            from fastembed import TextEmbedding
            from fastembed.common.model_description import ModelSource, PoolingType
        except ImportError as exc:
            raise ComponentUnavailableError(
                "LOCAL_EMBEDDING_DEPENDENCY_MISSING: install the 'semantic' extra"
            ) from exc
        try:
            if self._model_name == DEFAULT_MODEL and not any(
                item["model"] == DEFAULT_MODEL for item in TextEmbedding.list_supported_models()
            ):
                TextEmbedding.add_custom_model(
                    model=DEFAULT_MODEL,
                    pooling=PoolingType.MEAN,
                    normalization=True,
                    sources=ModelSource(hf=_E5_SOURCE_MODEL),
                    dim=384,
                    model_file="onnx/model_quantized.onnx",
                    description="Quantized multilingual E5-small for Russian semantic grouping",
                    license="mit",
                    size_in_gb=0.14,
                )
            self._model = cast(
                _EmbeddingModel,
                TextEmbedding(
                    model_name=self._model_name,
                    cache_dir=str(self._cache_dir) if self._cache_dir is not None else None,
                    threads=self._threads,
                ),
            )
        except (OSError, RuntimeError, ValueError, httpx.HTTPError) as exc:
            raise ComponentUnavailableError("LOCAL_EMBEDDING_MODEL_UNAVAILABLE") from exc
        return self._model

    @property
    def _uses_e5_prefix(self) -> bool:
        return self._model_name == DEFAULT_MODEL or "multilingual-e5" in self._model_name.casefold()
