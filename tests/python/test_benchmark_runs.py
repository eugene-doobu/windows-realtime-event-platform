import json
from pathlib import Path

from simlab.runner.execution import RunMode
from simlab.schemas.scenario import Scenario
from simlab.tools.benchmark_runs import benchmark_scenario_sizes


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
    )

    assert len(artifact.entries) == 2
    assert artifact.entries[0].population_size == 60
    assert artifact.entries[1].population_size == 120
    assert all(entry.edge_count > 0 for entry in artifact.entries)
    assert all(entry.total_time_ms >= entry.kernel_time_ms >= 0.0 for entry in artifact.entries)
