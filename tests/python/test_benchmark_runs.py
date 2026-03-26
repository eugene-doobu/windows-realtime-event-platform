import json
from pathlib import Path

from gan_simlab.runner.execution import RunMode
from gan_simlab.schemas.scenario import Scenario
from gan_simlab.tools.benchmark_runs import benchmark_scenario_sizes


def test_benchmark_scenario_sizes_returns_runtime_metrics() -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario.json"
    )
    scenario = Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8")))
    scenario.population.size = 120

    artifact = benchmark_scenario_sizes(
        scenario=scenario,
        sizes=[60, 120],
        run_mode=RunMode.STANDARD,
        repeats=2,
    )

    assert len(artifact.entries) == 2
    assert artifact.entries[0].population_size == 60
    assert artifact.entries[1].population_size == 120
    assert all(entry.edge_count > 0 for entry in artifact.entries)
    assert all(entry.repeat_count == 2 for entry in artifact.entries)
    assert all(entry.successful_runs == 2 for entry in artifact.entries)
    assert all(entry.failed_runs == 0 for entry in artifact.entries)
    assert all(entry.graph_generation_time_ms >= 0.0 for entry in artifact.entries)
    assert all(entry.total_time_ms >= entry.kernel_time_ms >= 0.0 for entry in artifact.entries)
    assert all(entry.max_total_time_ms >= entry.min_total_time_ms >= 0.0 for entry in artifact.entries)
    assert all(entry.estimated_total_prepared_bytes > 0 for entry in artifact.entries)
