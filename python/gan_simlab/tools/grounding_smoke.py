"""Run a grounded smoke scenario and print the resulting artifact summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gan_simlab.config import load_grounding_settings
from gan_simlab.runner.execution import RunMode
from gan_simlab.runner.launch import bootstrap_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a grounded smoke scenario and print the artifact summary.")
    parser.add_argument(
        "scenario",
        type=Path,
        nargs="?",
        default=Path("fixtures") / "synthetic_public_issue" / "scenario_grounded.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts") / "grounding-smoke",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts") / "cache" / "prepared",
    )
    args = parser.parse_args()

    settings = load_grounding_settings()
    if not settings.postgres_dsn:
        raise SystemExit("GAN_SIMLAB_RAG_POSTGRES_DSN is not configured.")

    run_id = bootstrap_run(
        args.scenario,
        args.output_dir,
        run_mode=RunMode.SMOKE,
        cache_dir=args.cache_dir,
        grounding_settings=settings,
    )
    run_dir = args.output_dir / run_id
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    grounding = json.loads((run_dir / "grounding.json").read_text(encoding="utf-8"))

    print(f"run_id={run_id}")
    print(f"grounding_enabled={summary['grounding_enabled']}")
    print(f"grounding_source_count={summary['grounding_source_count']}")
    print(f"query_count={grounding['query_count']}")
    print(f"artifact_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
