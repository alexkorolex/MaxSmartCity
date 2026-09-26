"""Grounded template-first report generator."""

import hashlib

from src.ml.data.template_generation.models import (
    IssueFrame,
    TemplateExample,
    TemplateGenerationConfig,
)
from src.ml.data.template_generation.providers import RussianAddressProvider


class TemplateExampleGenerator:
    def __init__(self, config: TemplateGenerationConfig) -> None:
        self._config = config
        self._addresses = RussianAddressProvider(config.seed)

    def generate(self) -> tuple[TemplateExample, ...]:
        return tuple(
            self._generate_one(frame, frame_index, variant_index)
            for frame_index, frame in enumerate(self._config.frames)
            for variant_index in range(self._config.variants_per_frame)
        )

    def _generate_one(
        self,
        frame: IssueFrame,
        frame_index: int,
        variant_index: int,
    ) -> TemplateExample:
        address = self._addresses.next_address()
        base_problem = frame.problem_variants[variant_index % len(frame.problem_variants)]
        templates_by_id = {template.id: template for template in self._config.templates}
        template_id = frame.allowed_template_ids[
            (frame_index + variant_index) % len(frame.allowed_template_ids)
        ]
        text = templates_by_id[template_id].text.format(
            street=address.street,
            street_sentence=address.street_sentence,
            house_number=address.house_number,
            at_street=address.at_street,
            problem=base_problem,
        )
        example_id = hashlib.sha256(
            f"{self._config.version}:{frame.id}:{variant_index}".encode()
        ).hexdigest()[:16]
        return TemplateExample(
            example_id=f"TPL-{example_id}",
            config_version=self._config.version,
            frame_id=frame.id,
            category_ids=frame.category_ids,
            subcategory_id=frame.subcategory_id,
            context_tags=frame.context_tags,
            danger_signals=frame.danger_signals,
            location_scope=frame.location_scope,
            address_required=True,
            street=address.street,
            house_number=address.house_number,
            template_id=template_id,
            base_problem=base_problem,
            text=text,
        )
