"""Seeded Russian address and morphology providers."""

import re

from faker import Faker
from pymorphy3 import MorphAnalyzer

from maxsmartcity.ml.data.template_generation.models import RussianAddress


class RussianAddressProvider:
    def __init__(self, seed: int) -> None:
        self._faker = Faker("ru_RU", use_weighting=False)
        self._faker.seed_instance(seed)
        self._morph = MorphAnalyzer()

    def next_address(self) -> RussianAddress:
        title = self._next_clean_title()
        house_number = str(self._faker.random_int(min=1, max=200))
        street, at_street = self._street_forms(title)
        return RussianAddress(
            street=street,
            street_sentence=street[:1].upper() + street[1:],
            house_number=house_number,
            at_street=at_street,
        )

    def _next_clean_title(self) -> str:
        for _ in range(100):
            title = self._faker.unique.street_title().strip()
            if re.fullmatch(r"[А-ЯЁа-яё-]+(?: [А-ЯЁа-яё-]+)*", title) and len(title) >= 4:
                return title
        msg = "Faker could not produce a clean Russian street title"
        raise RuntimeError(msg)

    def _street_forms(self, title: str) -> tuple[str, str]:
        if " " not in title:
            parsed = self._morph.parse(title)[0]
            if "ADJF" in parsed.tag and "femn" in parsed.tag:
                inflected = parsed.inflect({"loct"})
                if inflected is not None:
                    location_title = _restore_case(title, inflected.word)
                    return f"{title} улица", f"на {location_title} улице"
        return f"улица {title}", f"на улице {title}"


def _restore_case(source: str, value: str) -> str:
    return value.capitalize() if source[:1].isupper() else value
