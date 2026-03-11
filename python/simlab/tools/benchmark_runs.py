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
    repeats: int = 1,
) -> BenchmarkArtifact:
    entries: list[BenchmarkEntry] = []
    for size in sizes:
        scenario_variant = scenario.model_copy(deep=True)
        scenario_variant.population.size = size
        successful_runs = 0
        failed_runs = 0
        prepare_samples: list[float] = []
        kernel_samples: list[float] = []
        interaction_samples: list[float] = []
        total_samples: list[float] = []
        state_generation_samples: list[float] = []
        graph_generation_samples: list[float] = []
        config_generation_samples: list[float] = []
        edge_count = 0
        estimated_total_prepared_bytes = 0
        final_mean_stance = 0.0
        final_mean_trust = 0.0

        for repeat_index in range(repeats):
            try:
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
                    run_id=f"benchmark-{size}-{repeat_index}",
                    scenario=scenario_variant,
                    run_mode=run_mode,
                    final_state=kernel_result["final_state"],
                    round_metrics=kernel_result["round_metrics"],
                    persona=prepared.persona,
                    group_labels=prepared.group_labels,
                )
                interaction_time_ms = (perf_counter() - interaction_started_at) * 1000.0
            except Exception:
                failed_runs += 1
                continue

            final_round = kernel_result["round_metrics"][-1]
            successful_runs += 1
            prepare_samples.append(prepare_time_ms)
            kernel_samples.append(kernel_time_ms)
            interaction_samples.append(interaction_time_ms)
            total_samples.append(prepare_time_ms + kernel_time_ms + interaction_time_ms)
            state_generation_samples.append(prepared.profile.state_generation_time_ms)
            graph_generation_samples.append(prepared.profile.graph_generation_time_ms)
            config_generation_samples.append(prepared.profile.config_generation_time_ms)
            edge_count = prepared.profile.edge_count
            estimated_total_prepared_bytes = prepared.profile.estimated_total_bytes
            final_mean_stance += float(final_round["mean_stance"])
            final_mean_trust += float(final_round["mean_trust"])

        if successful_runs == 0:
            raise RuntimeError(f"benchmark failed for population size {size}")
        entries.append(
            BenchmarkEntry(
                population_size=size,
                rounds=scenario_variant.simulation.rounds,
                repeat_count=repeats,
                successful_runs=successful_runs,
                failed_runs=failed_runs,
                edge_count=edge_count,
                state_generation_time_ms=sum(state_generation_samples) / successful_runs,
                graph_generation_time_ms=sum(graph_generation_samples) / successful_runs,
                config_generation_time_ms=sum(config_generation_samples) / successful_runs,
                prepare_time_ms=sum(prepare_samples) / successful_runs,
                kernel_time_ms=sum(kernel_samples) / successful_runs,
                interaction_time_ms=sum(interaction_samples) / successful_runs,
                total_time_ms=sum(total_samples) / successful_runs,
                min_total_time_ms=min(total_samples),
                max_total_time_ms=max(total_samples),
                estimated_total_prepared_bytes=estimated_total_prepared_bytes,
                final_mean_stance=final_mean_stance / successful_runs,
                final_mean_trust=final_mean_trust / successful_runs,
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
        default=[100, 300, 1000, 3000],
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
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()

    scenario = Scenario.model_validate(json.loads(args.scenario.read_text(encoding="utf-8")))
    benchmark = benchmark_scenario_sizes(
        scenario=scenario,
        sizes=args.sizes,
        run_mode=RunMode(args.run_mode),
        repeats=args.repeats,
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
                    f"- `{entry.population_size}` agents: success `{entry.successful_runs}/{entry.repeat_count}`, prepare `{entry.prepare_time_ms:.2f}` ms, graph `{entry.graph_generation_time_ms:.2f}` ms, kernel `{entry.kernel_time_ms:.2f}` ms, interaction `{entry.interaction_time_ms:.2f}` ms, memory `{entry.estimated_total_prepared_bytes}` bytes, edges `{entry.edge_count}`"
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
