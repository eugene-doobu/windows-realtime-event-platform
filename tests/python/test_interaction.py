import json
from pathlib import Path

from gan_simlab.interaction import generate_interactions
from gan_simlab.runner.execution import RunMode
from gan_simlab.runner.kernel_client import run_kernel
from gan_simlab.runner.population import prepare_simulation_input
from gan_simlab.schemas.scenario import InterventionKind, Scenario


def _load_scenario(filename: str) -> Scenario:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / filename
    )
    return Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8")))


def test_generate_interactions_prefers_high_activity_group() -> None:
    scenario = _load_scenario("scenario.json")
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

    activation_by_group: dict[str, int] = {}
    for metric in interaction.summary.group_metrics:
        activation_by_group[metric.group_id] = activation_by_group.get(metric.group_id, 0) + metric.activation_count

    assert interaction.summary.thread_count > 0
    assert interaction.summary.message_count > 0
    assert activation_by_group.get("young_workers", 0) >= activation_by_group.get("benefit_recipients", 0)


def test_generate_interactions_is_deterministic_for_fixed_seed() -> None:
    scenario = _load_scenario("scenario.json")
    prepared = prepare_simulation_input(scenario)
    kernel_result = run_kernel(
        initial_state=prepared.initial_state,
        graph=prepared.graph,
        config=prepared.config,
    )

    first = generate_interactions(
        run_id="test-run",
        scenario=scenario,
        run_mode=RunMode.STANDARD,
        final_state=kernel_result["final_state"],
        round_metrics=kernel_result["round_metrics"],
        persona=prepared.persona,
        group_labels=prepared.group_labels,
    )
    second = generate_interactions(
        run_id="test-run",
        scenario=scenario,
        run_mode=RunMode.STANDARD,
        final_state=kernel_result["final_state"],
        round_metrics=kernel_result["round_metrics"],
        persona=prepared.persona,
        group_labels=prepared.group_labels,
    )

    assert [thread.model_dump() for thread in first.threads] == [thread.model_dump() for thread in second.threads]
    assert [message.model_dump() for message in first.messages] == [message.model_dump() for message in second.messages]
    assert [reaction.model_dump() for reaction in first.reactions] == [reaction.model_dump() for reaction in second.reactions]
    assert first.summary.model_dump() == second.summary.model_dump()


def test_generate_interactions_uses_trust_baseline_for_clarification_response() -> None:
    scenario = _load_scenario("scenario_grounded.json").model_copy(deep=True)
    for intervention in scenario.simulation.interventions:
        if intervention.kind == InterventionKind.CLARIFICATION:
            intervention.target_groups = []
            intervention.target_channels = [channel.id for channel in scenario.simulation.channels]
            intervention.round_index = 2
            intervention.narrative_push["clarification_accepted"] = 0.95

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

    activation_by_group: dict[str, int] = {}
    clarification_mentions: dict[str, int] = {}
    for metric in interaction.summary.group_metrics:
        activation_by_group[metric.group_id] = activation_by_group.get(metric.group_id, 0) + metric.activation_count
    for message in interaction.messages:
        if message.narrative_token == "clarification_accepted":
            clarification_mentions[message.group_id] = clarification_mentions.get(message.group_id, 0) + 1
    for reaction in interaction.reactions:
        if reaction.narrative_token == "clarification_accepted":
            clarification_mentions[reaction.group_id] = clarification_mentions.get(reaction.group_id, 0) + 1

    benefit_rate = clarification_mentions.get("benefit_recipients", 0) / activation_by_group["benefit_recipients"]
    young_rate = clarification_mentions.get("young_workers", 0) / activation_by_group["young_workers"]

    assert benefit_rate > young_rate


def test_generate_interactions_uses_rumor_susceptibility_for_rumor_emission() -> None:
    scenario = _load_scenario("scenario_grounded.json").model_copy(deep=True)
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
            narrative_push={"future_distrust": 0.95, "burden_unfair": 0.8},
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

    activation_by_group: dict[str, int] = {}
    rumor_messages: dict[str, int] = {}
    for metric in interaction.summary.group_metrics:
        activation_by_group[metric.group_id] = activation_by_group.get(metric.group_id, 0) + metric.activation_count
    for message in interaction.messages:
        if message.narrative_token in {"future_distrust", "burden_unfair"}:
            rumor_messages[message.group_id] = rumor_messages.get(message.group_id, 0) + 1

    young_rate = rumor_messages.get("young_workers", 0) / activation_by_group["young_workers"]
    benefit_rate = rumor_messages.get("benefit_recipients", 0) / activation_by_group["benefit_recipients"]

    assert young_rate > benefit_rate


def test_generate_interactions_uses_correction_acceptance_for_fact_check_response() -> None:
    scenario = _load_scenario("scenario_grounded.json").model_copy(deep=True)
    scenario.population.variation_sigma = 0.0
    for archetype in scenario.population.archetypes:
        archetype.narrative_affinity = {"clarification_accepted": 1.0}
        archetype.base_activity = 0.55
        archetype.base_salience = 0.7
        archetype.post_tendency = 0.2
        archetype.reply_tendency = 0.2
        archetype.reaction_tendency = 0.95
        archetype.trust_in_officials_baseline = 0.5
    scenario.simulation.narrative_tokens = ["clarification_accepted"]
    for archetype in scenario.population.archetypes:
        if archetype.id == "young_workers":
            archetype.correction_acceptance = 0.2
        elif archetype.id == "benefit_recipients":
            archetype.correction_acceptance = 0.9
    scenario.simulation.interventions = [
        intervention
        for intervention in scenario.simulation.interventions
        if intervention.kind != InterventionKind.CLARIFICATION
    ]
    scenario.simulation.interventions.append(
        type(scenario.simulation.interventions[0])(
            round_index=2,
            kind=InterventionKind.FACT_CHECK,
            target_groups=[],
            target_channels=[channel.id for channel in scenario.simulation.channels],
            narrative_push={"clarification_accepted": 0.95},
            trust_delta=0.05,
            stance_delta=0.0,
            salience_delta=-0.05,
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

    clarification_reactions: dict[str, int] = {}
    endorsed_reactions: dict[str, int] = {}
    for reaction in interaction.reactions:
        if reaction.narrative_token != "clarification_accepted":
            continue
        clarification_reactions[reaction.group_id] = clarification_reactions.get(reaction.group_id, 0) + 1
        if reaction.reaction_kind == "endorse":
            endorsed_reactions[reaction.group_id] = endorsed_reactions.get(reaction.group_id, 0) + 1

    benefit_rate = endorsed_reactions.get("benefit_recipients", 0) / clarification_reactions["benefit_recipients"]
    young_rate = endorsed_reactions.get("young_workers", 0) / clarification_reactions["young_workers"]

    assert benefit_rate > young_rate
