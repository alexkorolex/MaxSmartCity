"""Plan or execute controlled AI Tunnel paraphrases for template seeds."""

import argparse
import json
import os
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

from maxsmartcity.ml.data.llm.client import AitunnelLexicalizationClient
from maxsmartcity.ml.data.llm.prompt import load_system_prompt
from maxsmartcity.ml.data.template_generation.config import load_template_generation_config
from maxsmartcity.ml.data.template_generation.generator import TemplateExampleGenerator
from maxsmartcity.ml.data.template_generation.paraphrase import (
    TemplateParaphraseRunner,
    load_template_paraphrase_config,
    select_one_seed_per_frame,
    select_scenarios,
)
from maxsmartcity.ml.data.template_generation.writer import load_template_examples


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--templates-config", type=Path)
    source_group.add_argument("--seeds-file", type=Path)
    parser.add_argument("--llm-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env.local"))
    parser.add_argument("--scenario-ids-file", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.templates_config is not None:
        generated_examples = TemplateExampleGenerator(
            load_template_generation_config(args.templates_config)
        ).generate()
    else:
        if args.seeds_file is None:
            msg = "one template seed source is required"
            raise RuntimeError(msg)
        generated_examples = load_template_examples(args.seeds_file)
    examples = select_one_seed_per_frame(generated_examples)
    if args.scenario_ids_file is not None:
        payload = json.loads(args.scenario_ids_file.read_text(encoding="utf-8"))
        raw_ids = payload.get("scenario_ids") if isinstance(payload, dict) else None
        if (
            not isinstance(raw_ids, list)
            or not raw_ids
            or not all(isinstance(item, str) and item for item in raw_ids)
        ):
            msg = "scenario ids file must contain a non-empty scenario_ids string list"
            raise ValueError(msg)
        examples = select_scenarios(examples, frozenset(raw_ids))
    config = load_template_paraphrase_config(args.llm_config)
    system_prompt = load_system_prompt(config.prompt_file)
    if args.execute:
        load_dotenv(args.env_file, override=False)
        api_key = os.getenv("AITUNNEL_API_KEY")
        if not api_key:
            msg = f"AITUNNEL_API_KEY is not configured in environment or {args.env_file}"
            raise RuntimeError(msg)
        config = replace(
            config,
            model=os.getenv("AITUNNEL_MODEL", config.model),
            base_url=os.getenv("AITUNNEL_BASE_URL", config.base_url),
        )
        client = AitunnelLexicalizationClient(
            api_key=api_key,
            base_url=config.base_url,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
    else:
        client = None
    runner = TemplateParaphraseRunner(
        config=config,
        system_prompt=system_prompt,
        client=client,
    )
    plan = runner.write_plan(examples, args.output_dir)
    result = runner.execute(examples, args.output_dir) if args.execute else plan
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
