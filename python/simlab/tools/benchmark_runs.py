"""Benchmark synthetic runs across multiple population sizes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from simlab.interaction import generate_interactions
from simlab.runner.execution import RunMode
from simlab.runner.kernel_client import kernel_backend_name, run_kernel
from simlab.runner.population import prepare_simulation_input
from simlab.runner.reporting import write_report
from simlab.schemas.artifacts import BenchmarkArtifact, BenchmarkEntry
from simlab.schemas.scenario import Scenario


def benchmark_scenario_sizes(
    *,
    scenario: Scenario,
    sizes: list[int],
    run_mode: RunMode = RunMode.STANDARD,
) -> BenchmarkArtifact:
    entries: list[BenchmarkEntry] = []
    for size in sizes:
        scenario_variant = scenario.model_copy(deep=True)
        scenario_variant.population.size = size

        prepare_started_at = perf_counter()
        prepared = prepare_simulation_input(scenario_variant)
        prepare_time_ms = (perf_counter() - prepare_started_at) * 1000.0

        kernel_started_at = perf_counter()
        kernel_result = run_kernel(
            initial_state=prepared.initial_state,
            graph=prepared.graph,
            config=prepared.config,
        )
        kernel_time_ms = (perf_counter() - kernel_started_at) * 1000.0

        interaction_started_at = perf_counter()
        generate_interactions(
            run_id=f"benchmark-{size}",
            scenario=scenario_variant,
            run_mode=run_mode,
            final_state=kernel_result["final_state"],
            round_metrics=kernel_result["round_metrics"],
            persona=prepared.persona,
            group_labels=prepared.group_labels,
        )
        interaction_time_ms = (perf_counter() - interaction_started_at) * 1000.0

        final_round = kernel_result["round_metrics"][-1]
        entries.append(
            BenchmarkEntry(
                population_size=size,
                rounds=scenario_variant.simulation.rounds,
                edge_count=len(prepared.graph["targets"]),
                prepare_time_ms=prepare_time_ms,
                kernel_time_ms=kernel_time_ms,
                interaction_time_ms=interaction_time_ms,
                total_time_ms=prepare_time_ms + kernel_time_ms + interaction_time_ms,
                final_mean_stance=float(final_round["mean_stance"]),
                final_mean_trust=float(final_round["mean_trust"]),
            )
        )

    return BenchmarkArtifact(
        scenario_id=scenario.scenario_id,
        kernel_backend=kernel_backend_name(),
        entries=entries,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark synthetic runs across multiple population sizes.")
    parser.add_argument(
        "scenario",
        type=Path,
        nargs="?",
        default=Path("fixtures") / "synthetic_public_issue" / "scenario.json",
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=[100, 300, 1000],
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts") / "benchmarks" / "benchmark.json",
    )
    parser.add_argument(
        "--run-mode",
        choices=[mode.value for mode in RunMode],
        default=RunMode.STANDARD.value,
    )
    args = parser.parse_args()

    scenario = Scenario.model_validate(json.loads(args.scenario.read_text(encoding="utf-8")))
    benchmark = benchmark_scenario_sizes(
        scenario=scenario,
        sizes=args.sizes,
        run_mode=RunMode(args.run_mode),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(benchmark.model_dump(), indent=2), encoding="utf-8")
    write_report(
        args.output.with_suffix(".md"),
        "\n".join(
            [
                "# Benchmark Report",
                "",
                f"- Scenario: `{benchmark.scenario_id}`",
                f"- Kernel backend: `{benchmark.kernel_backend}`",
                "",
                *[
                    f"- `{entry.population_size}` agents: prepare `{entry.prepare_time_ms:.2f}` ms, kernel `{entry.kernel_time_ms:.2f}` ms, interaction `{entry.interaction_time_ms:.2f}` ms, edges `{entry.edge_count}`"
                    for entry in benchmark.entries
                ],
                "",
            ]
        ),
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
