import json
from pathlib import Path

from simlab.expression import render_conversation
from simlab.interaction import build_interaction_validation, generate_interactions
from simlab.persona import build_persona_snapshot
from simlab.runner.execution import RunMode
from simlab.runner.kernel_client import run_kernel
from simlab.runner.population import prepare_simulation_input
from simlab.schemas.scenario import InterventionKind, Scenario


def test_interaction_validation_checks_rumor_amplification_alignment() -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario_grounded.json"
    )
    scenario = Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8"))).model_copy(deep=True)
    scenario.population.variation_sigma = 0.0
    for archetype in scenario.population.archetypes:
        if archetype.id == "young_workers":
            archetype.post_tendency = 0.2
            archetype.reply_tendency = 0.3
            archetype.reaction_tendency = 0.95
            archetype.conformity = 0.82
        elif archetype.id == "benefit_recipients":
            archetype.post_tendency = 0.2
            archetype.reply_tendency = 0.3
            archetype.reaction_tendency = 0.35
            archetype.conformity = 0.2
            archetype.rumor_susceptibility = 0.15
    scenario.simulation.interventions = [
        intervention
        for intervention in scenario.simulation.interventions
        if intervention.kind != InterventionKind.CLARIFICATION
    ]
    scenario.simulation.interventions.append(
        type(scenario.simulation.interventions[0])(
            round_index=1,
            kind=InterventionKind.RUMOR,
            target_groups=[],
            target_channels=[channel.id for channel in scenario.simulation.channels],
            narrative_push={"future_distrust": 0.95, "burden_unfair": 0.85},
            trust_delta=-0.05,
            stance_delta=-0.1,
            salience_delta=0.1,
        )
    )

    prepared = prepare_simulation_input(scenario)
    kernel_result = run_kernel(
        initial_state=prepared.initial_state,
        graph=prepared.graph,
        config=prepared.config,
    )
    interaction = generate_interactions(
        run_id="test-run",
        scenario=scenario,
        run_mode=RunMode.STANDARD,
        final_state=kernel_result["final_state"],
        round_metrics=kernel_result["round_metrics"],
        persona=prepared.persona,
        group_labels=prepared.group_labels,
    )
    snapshot = build_persona_snapshot(
        run_id="test-run",
        scenario_id=scenario.scenario_id,
        persona=prepared.persona,
        group_labels=prepared.group_labels,
    )
    conversation = render_conversation(
        messages=interaction.messages,
        reactions=interaction.reactions,
        persona=prepared.persona,
    )

    validation = build_interaction_validation(
        run_id="test-run",
        scenario=scenario,
        interaction_summary=interaction.summary,
        persona_snapshot=snapshot,
        messages=interaction.messages,
        reactions=interaction.reactions,
        conversation=conversation,
    )

    checks = {check.check_id: check for check in validation.checks}
    assert "rumor_amplification_alignment" in checks
    assert checks["rumor_amplification_alignment"].passed is True
