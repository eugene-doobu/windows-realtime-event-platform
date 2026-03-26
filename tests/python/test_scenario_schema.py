import json
from pathlib import Path

from gan_simlab.schemas.scenario import Scenario


def test_fixture_scenario_validates() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario.json"
    )
    scenario = Scenario.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))

    assert scenario.scenario_id == "synthetic-public-issue"
    assert scenario.population.size == 300
    assert scenario.simulation.rounds == 10
    assert scenario.population.archetypes[0].tone_style == "frustrated"


def test_grounded_fixture_scenario_validates() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario_grounded.json"
    )
    scenario = Scenario.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))

    assert scenario.grounding.enabled is True
    assert scenario.grounding.top_k == 3
    assert len(scenario.grounding.document_paths) == 3
    assert scenario.population.archetypes[1].argument_style == "cost_benefit"
