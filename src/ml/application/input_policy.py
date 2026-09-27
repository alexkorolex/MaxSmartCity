"""Deterministic input bounds applied before tokenization or model inference."""

from dataclasses import dataclass, replace

from src.ml.domain.requests import DecisionRequest


@dataclass(frozen=True, slots=True)
class InputPolicy:
    """Bound user text deterministically before any model-specific preprocessing."""

    max_characters: int

    def apply(self, request: DecisionRequest) -> tuple[DecisionRequest, bool]:
        """Return the bounded request and whether truncation was applied."""

        text = request.report.text
        if len(text) <= self.max_characters:
            return request, False
        truncated_report = replace(request.report, text=text[: self.max_characters])
        return replace(request, report=truncated_report), True
