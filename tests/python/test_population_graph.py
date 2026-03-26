import json
from pathlib import Path

from gan_simlab.persona import build_persona_snapshot
from gan_simlab.runner.population import prepare_simulation_input
from gan_simlab.schemas.scenario import Scenario


def test_influencer_bias_creates_higher_out_degree_nodes() -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario.json"
    )
    scenario = Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8")))
    prepared = prepare_simulation_input(scenario)

    offsets = prepared.graph["offsets"]
    out_degrees = [offsets[index + 1] - offsets[index] for index in range(len(offsets) - 1)]
    baseline_degree = scenario.population.intra_group_degree + scenario.population.inter_group_degree

    assert max(out_degrees) > baseline_degree


def test_prepare_simulation_input_includes_persona_fields() -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario.json"
    )
    scenario = Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8")))
    prepared = prepare_simulation_input(scenario)

    assert len(prepared.persona["age_band"]) == scenario.population.size
    assert "frustrated" in prepared.persona["tone_style"]
    assert max(prepared.persona["reply_tendency"]) <= 1.0


def test_prepare_simulation_input_is_reproducible_for_fixed_seed() -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario.json"
    )
    scenario = Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8")))

    first = prepare_simulation_input(scenario)
    second = prepare_simulation_input(scenario)

    assert first.initial_state == second.initial_state
    assert first.persona == second.persona
    assert first.graph == second.graph


def test_prepare_simulation_input_preserves_distribution_across_seeds() -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario.json"
    )
    scenario = Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8")))
    alternate = scenario.model_copy(deep=True)
    alternate.simulation.random_seed = 777

    first = prepare_simulation_input(scenario)
    second = prepare_simulation_input(alternate)
    first_snapshot = build_persona_snapshot(
        run_id="first",
        scenario_id=scenario.scenario_id,
        persona=first.persona,
        group_labels=first.group_labels,
    )
    second_snapshot = build_persona_snapshot(
        run_id="second",
        scenario_id=alternate.scenario_id,
        persona=second.persona,
        group_labels=second.group_labels,
    )

    first_groups = {summary.group_id: summary for summary in first_snapshot.group_summaries}
    second_groups = {summary.group_id: summary for summary in second_snapshot.group_summaries}

    assert {group_id: summary.population for group_id, summary in first_groups.items()} == {
        group_id: summary.population for group_id, summary in second_groups.items()
    }
    for group_id in first_groups:
        assert abs(first_groups[group_id].mean_reply_tendency - second_groups[group_id].mean_reply_tendency) < 0.08
        assert (
            abs(
                first_groups[group_id].mean_trust_in_officials_baseline
                - second_groups[group_id].mean_trust_in_officials_baseline
            )
            < 0.08
        )
