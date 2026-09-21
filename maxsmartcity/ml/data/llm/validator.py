"""Deterministic checks for LLM-generated report candidates."""

import re

from maxsmartcity.ml.data.llm.config import LlmGenerationConfig
from maxsmartcity.ml.data.llm.models import (
    GeneratedVariant,
    GenerationPass,
    ScenarioFact,
    VariantValidation,
)


class GeneratedVariantValidator:
    def __init__(self, config: LlmGenerationConfig) -> None:
        self._config = config

    def validate(
        self,
        fact: ScenarioFact,
        generation_pass: GenerationPass,
        variants: tuple[GeneratedVariant, ...],
    ) -> tuple[VariantValidation, ...]:
        normalized_texts = [_normalize(item.text) for item in variants]
        duplicate_texts = {value for value in normalized_texts if normalized_texts.count(value) > 1}
        return tuple(
            VariantValidation(
                variant=item,
                errors=self._errors(
                    fact,
                    generation_pass,
                    item,
                    normalized_texts[index] in duplicate_texts,
                ),
            )
            for index, item in enumerate(variants)
        )

    def _errors(
        self,
        fact: ScenarioFact,
        generation_pass: GenerationPass,
        variant: GeneratedVariant,
        is_duplicate: bool,
    ) -> tuple[str, ...]:
        errors: list[str] = []
        text = variant.text.strip()
        normalized = _normalize(text)
        if len(text) < self._config.min_text_length:
            errors.append("TEXT_TOO_SHORT")
        if len(text) > self._config.max_text_length:
            errors.append("TEXT_TOO_LONG")
        if variant.style_id not in generation_pass.styles:
            errors.append("STYLE_NOT_ALLOWED")
        elif not _matches_declared_style(text, variant.style_id):
            errors.append("STYLE_CONSTRAINT_NOT_MET")
        if is_duplicate:
            errors.append("DUPLICATE_WITHIN_RESPONSE")
        if any(_normalize(term) in normalized for term in self._config.forbidden_terms):
            errors.append("FORBIDDEN_SOURCE_TERM")
        address_found = contains_address(text, fact.street, fact.house_number)
        if variant.address_included != address_found:
            errors.append("ADDRESS_FLAG_MISMATCH")
        if fact.address_requirement == "REQUIRED" and not address_found:
            errors.append("REQUIRED_ADDRESS_MISSING")
        if fact.address_requirement == "FORBIDDEN" and address_found:
            errors.append("FORBIDDEN_ADDRESS_PRESENT")
        if fact.danger_signals and not mentions_danger(text, fact.danger_signals):
            errors.append("DANGER_SIGNAL_NOT_LEXICALIZED")
        if "negated_danger" in fact.context_tags and not _preserves_negated_danger(text):
            errors.append("NEGATED_DANGER_NOT_PRESERVED")
        return tuple(errors)


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[а-яёa-z0-9]+", value.casefold()))


def contains_address(text: str, street: str, house_number: str) -> bool:
    normalized_text = _normalize(text)
    normalized_number = _normalize(house_number)
    ignored = {"улица", "проспект", "переулок", "проезд"}
    street_tokens = [
        token for token in _normalize(street).split() if token not in ignored and len(token) >= 3
    ]
    street_found = any(token[:3] in normalized_text for token in street_tokens)
    number_found = normalized_number in normalized_text.split()
    return street_found and number_found


def mentions_danger(text: str, danger_signals: tuple[str, ...]) -> bool:
    normalized = _normalize(text)
    marker_groups = {
        "WATER_NEAR_ELECTRICITY": (("вод", "теч", "кап"), ("щит", "электр", "провод")),
        "SPARKS": (("искр",),),
        "SPARKING": (("искр",),),
        "EXPOSED_WIRE": (("огол", "оборван"), ("провод", "кабел")),
        "GAS_SMELL": (("газ",), ("запах", "пах")),
        "SMOKE": (("дым", "задым"),),
        "FIRE": (("горит", "огонь", "плам"),),
        "OPEN_FLAME": (("горит", "огонь", "плам"),),
        "FLOODING": (("затап", "льёт", "льется", "льётся", "течёт", "течет"),),
        "STRUCTURAL_RISK": (("трещин", "перекрыт", "обруш"),),
    }
    return all(
        all(any(marker in normalized for marker in group) for group in marker_groups[signal])
        if signal in marker_groups
        else _normalize(signal) in normalized
        for signal in danger_signals
    )


def _preserves_negated_danger(text: str) -> bool:
    normalized = _normalize(text)
    return any(
        marker in normalized
        for marker in (
            "не искр",
            "без искр",
            "искрения нет",
            "искр нет",
        )
    )


def _matches_declared_style(text: str, style_id: str) -> bool:
    if style_id == "caps":
        letters = [character for character in text if character.isalpha()]
        return bool(letters) and sum(character.isupper() for character in letters) / len(letters) >= 0.7
    if style_id == "emoji":
        return re.search(r"[\u2600-\u27bf\U0001f300-\U0001faff]", text) is not None
    if style_id == "self_correction":
        normalized = _normalize(text)
        return any(
            marker in normalized for marker in ("точнее", "вернее", "то есть", "нет поправлюсь", "ой нет")
        )
    if style_id == "short":
        return len(text) <= 140
    return True
