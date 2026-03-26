import json
from pathlib import Path

import pytest

from gan_simlab.runner.kernel_client import (
    _run_reference_kernel,
    native_kernel_available,
    run_kernel,
)
from gan_simlab.runner.population import prepare_simulation_input
from gan_simlab.schemas.scenario import Scenario


@pytest.mark.skipif(not native_kernel_available(), reason="native kernel is not installed")
def test_native_kernel_matches_reference_kernel_with_tolerance() -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario.json"
    )
    scenario = Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8")))
    prepared = prepare_simulation_input(scenario)

    native = run_kernel(
        initial_state=prepared.initial_state,
        graph=prepared.graph,
        config=prepared.config,
    )
    reference = _run_reference_kernel(
        initial_state=prepared.initial_state,
        graph=prepared.graph,
        config=prepared.config,
    )

    assert len(native["round_metrics"]) == len(reference["round_metrics"])

    for native_metric, reference_metric in zip(
        native["round_metrics"],
        reference["round_metrics"],
        strict=True,
    ):
        assert native_metric["total_exposures"] == reference_metric["total_exposures"]
        assert native_metric["total_posts"] == reference_metric["total_posts"]
        assert native_metric["mean_stance"] == pytest.approx(reference_metric["mean_stance"], abs=1e-6)
        assert native_metric["mean_trust"] == pytest.approx(reference_metric["mean_trust"], abs=1e-6)
        assert native_metric["mean_salience"] == pytest.approx(reference_metric["mean_salience"], abs=1e-6)
        assert native_metric["rumor_share"] == pytest.approx(reference_metric["rumor_share"], abs=1e-6)
        assert native_metric["clarification_share"] == pytest.approx(
            reference_metric["clarification_share"],
            abs=1e-6,
        )
