"""Plan or execute resumable AI Tunnel report lexicalization."""

import argparse
import json
import os
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

from maxsmartcity.ml.data.llm.client import AitunnelLexicalizationClient
from maxsmartcity.ml.data.llm.config import load_llm_generation_config
from maxsmartcity.ml.data.llm.input import load_scenario_facts
from maxsmartcity.ml.data.llm.models import ScenarioFact
from maxsmartcity.ml.data.llm.prompt import load_system_prompt
from maxsmartcity.ml.data.llm.runner import LlmGenerationRunner
from maxsmartcity.ml.data.llm.selection import load_selection_ids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env.local"))
    parser.add_argument("--scenario-id", action="append", default=[])
    parser.add_argument("--selection-file", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    config = load_llm_generation_config(args.config)
    facts = load_scenario_facts(args.input)
    if args.scenario_id and args.selection_file:
        parser.error("--scenario-id and --selection-file cannot be combined")
    if args.full and args.selection_file:
        parser.error("--full and --selection-file cannot be combined")
    selected = _select_facts(
        facts,
        pilot_ids=config.pilot_scenario_ids,
        requested_ids=tuple(args.scenario_id),
        selection_ids=load_selection_ids(args.selection_file) if args.selection_file else (),
        full=args.full,
        limit=args.limit,
    )
    prompt = load_system_prompt(config.prompt_file)
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
    runner = LlmGenerationRunner(config=config, system_prompt=prompt, client=client)
    tasks = runner.plan(selected)
    plan = runner.write_plan(tasks, args.output_dir)
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        return
    manifest = runner.execute(tasks, args.output_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


def _select_facts(
    facts: tuple[ScenarioFact, ...],
    *,
    pilot_ids: tuple[str, ...],
    requested_ids: tuple[str, ...],
    selection_ids: tuple[str, ...],
    full: bool,
    limit: int | None,
) -> tuple[ScenarioFact, ...]:
    by_id = {fact.scenario_spec_id: fact for fact in facts}
    target_ids = tuple(by_id) if full else pilot_ids
    if selection_ids:
        target_ids = selection_ids
    if requested_ids:
        target_ids = requested_ids
    unknown = set(target_ids) - set(by_id)
    if unknown:
        msg = f"requested scenario ids are absent from canonical input: {sorted(unknown)}"
        raise ValueError(msg)
    selected = tuple(by_id[item] for item in target_ids)
    if limit is not None:
        if limit <= 0:
            msg = "--limit must be a positive integer"
            raise ValueError(msg)
        selected = selected[:limit]
    return selected


if __name__ == "__main__":
    main()
