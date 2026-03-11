"""Population and graph builders for synthetic scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from simlab.schemas.scenario import Scenario


@dataclass(slots=True)
class PreparedSimulationInput:
    initial_state: dict[str, list[float] | list[int]]
    graph: dict[str, list[float] | list[int]]
    config: dict[str, int | list[dict[str, int | float | list[int] | list[float]]]]
    group_labels: dict[int, str]
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]]


def prepare_simulation_input(scenario: Scenario) -> PreparedSimulationInput:
    rng = Random(scenario.simulation.random_seed)
    archetypes = scenario.population.archetypes
    population_size = scenario.population.size

    counts = _allocate_group_counts(population_size, [archetype.share for archetype in archetypes])
    group_labels = {group_id: archetype.id for group_id, archetype in enumerate(archetypes)}

    stance: list[float] = []
    trust: list[float] = []
    salience: list[float] = []
    susceptibility: list[float] = []
    activity: list[float] = []
    influence: list[float] = []
    group_id: list[int] = []
    age_band: list[str] = []
    job_type: list[str] = []
    household_stage: list[str] = []
    education_level: list[str] = []
    region_type: list[str] = []
    income_pressure: list[float] = []
    media_diet: list[dict[str, float]] = []
    conflict_tolerance: list[float] = []
    conformity: list[float] = []
    risk_aversion: list[float] = []
    trust_in_officials_baseline: list[float] = []
    rumor_susceptibility: list[float] = []
    correction_acceptance: list[float] = []
    reply_tendency: list[float] = []
    post_tendency: list[float] = []
    reaction_tendency: list[float] = []
    verbosity: list[float] = []
    tone_style: list[str] = []
    argument_style: list[str] = []

    agent_groups: list[int] = []

    for current_group_id, (archetype, count) in enumerate(zip(archetypes, counts, strict=True)):
        for _ in range(count):
            stance.append(_jitter(rng, archetype.base_stance, scenario.population.variation_sigma, -1.0, 1.0))
            trust.append(_jitter(rng, archetype.base_trust, scenario.population.variation_sigma, 0.0, 1.0))
            salience.append(_jitter(rng, archetype.base_salience, scenario.population.variation_sigma, 0.0, 1.0))
            susceptibility.append(
                _jitter(rng, archetype.base_susceptibility, scenario.population.variation_sigma, 0.0, 1.0)
            )
            activity.append(_jitter(rng, archetype.base_activity, scenario.population.variation_sigma, 0.0, 1.0))
            influence.append(_jitter(rng, archetype.base_influence, scenario.population.variation_sigma, 0.0, 1.0))
            group_id.append(current_group_id)
            age_band.append(archetype.age_band)
            job_type.append(archetype.job_type)
            household_stage.append(archetype.household_stage)
            education_level.append(archetype.education_level)
            region_type.append(archetype.region_type)
            income_pressure.append(_jitter(rng, archetype.income_pressure, scenario.population.variation_sigma, 0.0, 1.0))
            media_diet.append(dict(archetype.media_diet))
            conflict_tolerance.append(
                _jitter(rng, archetype.conflict_tolerance, scenario.population.variation_sigma, 0.0, 1.0)
            )
            conformity.append(_jitter(rng, archetype.conformity, scenario.population.variation_sigma, 0.0, 1.0))
            risk_aversion.append(
                _jitter(rng, archetype.risk_aversion, scenario.population.variation_sigma, 0.0, 1.0)
            )
            trust_in_officials_baseline.append(
                _jitter(
                    rng,
                    archetype.trust_in_officials_baseline,
                    scenario.population.variation_sigma,
                    0.0,
                    1.0,
                )
            )
            rumor_susceptibility.append(
                _jitter(rng, archetype.rumor_susceptibility, scenario.population.variation_sigma, 0.0, 1.0)
            )
            correction_acceptance.append(
                _jitter(rng, archetype.correction_acceptance, scenario.population.variation_sigma, 0.0, 1.0)
            )
            reply_tendency.append(
                _jitter(rng, archetype.reply_tendency, scenario.population.variation_sigma, 0.0, 1.0)
            )
            post_tendency.append(
                _jitter(rng, archetype.post_tendency, scenario.population.variation_sigma, 0.0, 1.0)
            )
            reaction_tendency.append(
                _jitter(rng, archetype.reaction_tendency, scenario.population.variation_sigma, 0.0, 1.0)
            )
            verbosity.append(_jitter(rng, archetype.verbosity, scenario.population.variation_sigma, 0.0, 1.0))
            tone_style.append(archetype.tone_style)
            argument_style.append(archetype.argument_style)
            agent_groups.append(current_group_id)

    graph = _build_graph(
        rng=rng,
        agent_groups=agent_groups,
        intra_group_degree=scenario.population.intra_group_degree,
        inter_group_degree=scenario.population.inter_group_degree,
        influence=influence,
        influencer_ratio=scenario.population.influencer_ratio,
    )
    config = _build_kernel_config(scenario)

    initial_state = {
        "stance": stance,
        "trust": trust,
        "salience": salience,
        "susceptibility": susceptibility,
        "activity": activity,
        "influence": influence,
        "group_id": group_id,
    }
    persona = {
        "group_id": group_id,
        "age_band": age_band,
        "job_type": job_type,
        "household_stage": household_stage,
        "education_level": education_level,
        "region_type": region_type,
        "income_pressure": income_pressure,
        "media_diet": media_diet,
        "conflict_tolerance": conflict_tolerance,
        "conformity": conformity,
        "risk_aversion": risk_aversion,
        "trust_in_officials_baseline": trust_in_officials_baseline,
        "rumor_susceptibility": rumor_susceptibility,
        "correction_acceptance": correction_acceptance,
        "reply_tendency": reply_tendency,
        "post_tendency": post_tendency,
        "reaction_tendency": reaction_tendency,
        "verbosity": verbosity,
        "tone_style": tone_style,
        "argument_style": argument_style,
    }

    return PreparedSimulationInput(
        initial_state=initial_state,
        graph=graph,
        config=config,
        group_labels=group_labels,
        persona=persona,
    )


def _allocate_group_counts(total: int, shares: list[float]) -> list[int]:
    counts = [int(total * share) for share in shares]
    remainder = total - sum(counts)
    for index in range(remainder):
        counts[index % len(counts)] += 1
    return counts


def _jitter(rng: Random, base: float, sigma: float, lower: float, upper: float) -> float:
    value = base + rng.uniform(-sigma, sigma)
    return max(lower, min(upper, value))


def _build_graph(
    *,
    rng: Random,
    agent_groups: list[int],
    intra_group_degree: int,
    inter_group_degree: int,
    influence: list[float],
    influencer_ratio: float,
) -> dict[str, list[float] | list[int]]:
    agent_count = len(agent_groups)
    adjacency: list[list[tuple[int, float]]] = [[] for _ in range(agent_count)]
    group_members: dict[int, list[int]] = {}

    for agent_index, group_id in enumerate(agent_groups):
        group_members.setdefault(group_id, []).append(agent_index)

    cross_group_members: dict[int, list[int]] = {}
    for group_id in group_members:
        cross_group_members[group_id] = [
            agent_index
            for other_group_id, members in group_members.items()
            if other_group_id != group_id
            for agent_index in members
        ]

    influencer_count = min(
        agent_count,
        max(1, int(agent_count * influencer_ratio)) if influencer_ratio > 0.0 else 0,
    )
    influencer_indices = set(
        sorted(range(agent_count), key=lambda index: influence[index], reverse=True)[:influencer_count]
    )

    for source in range(agent_count):
        source_group = agent_groups[source]
        is_influencer = source in influencer_indices
        same_group_pool = [target for target in group_members[source_group] if target != source]
        cross_group_pool = cross_group_members[source_group]
        neighbor_targets = _sample_neighbors(
            rng,
            same_group_pool,
            _degree_with_bias(intra_group_degree, is_influencer),
        )
        neighbor_targets.extend(
            _sample_neighbors(
                rng,
                cross_group_pool,
                _degree_with_bias(inter_group_degree, is_influencer),
            )
        )

        for target in neighbor_targets:
            influencer_bonus = 0.15 if is_influencer else 0.0
            weight = max(
                0.05,
                min(1.0, 0.3 + ((influence[source] + influence[target]) * 0.35) + influencer_bonus),
            )
            adjacency[source].append((target, weight))

    offsets: list[int] = [0]
    targets: list[int] = []
    weights: list[float] = []

    for neighbors in adjacency:
        for target, weight in neighbors:
            targets.append(target)
            weights.append(weight)
        offsets.append(len(targets))

    return {"offsets": offsets, "targets": targets, "weights": weights}


def _sample_neighbors(rng: Random, pool: list[int], degree: int) -> list[int]:
    if degree <= 0 or not pool:
        return []
    sample_size = min(degree, len(pool))
    return rng.sample(pool, sample_size)


def _degree_with_bias(base_degree: int, is_influencer: bool) -> int:
    if not is_influencer:
        return base_degree
    return max(base_degree + 2, base_degree * 2)


def _build_kernel_config(scenario: Scenario) -> dict[str, int | list[dict[str, int | float | list[int] | list[float]]]]:
    group_index = {archetype.id: index for index, archetype in enumerate(scenario.population.archetypes)}
    channel_index = {channel.id: index for index, channel in enumerate(scenario.simulation.channels)}
    intervention_kind_index = {
        "announcement": 0,
        "clarification": 1,
        "support_measure": 2,
        "rumor": 3,
        "fact_check": 4,
    }

    channels = [
        {
            "channel_id": channel_index[channel.id],
            "exposure_weight": channel.exposure_weight,
            "repost_factor": channel.repost_factor,
            "rumor_decay": channel.rumor_decay,
            "trust_penalty": channel.trust_penalty,
        }
        for channel in scenario.simulation.channels
    ]

    interventions = [
        {
            "round_index": intervention.round_index,
            "kind_id": intervention_kind_index[intervention.kind.value],
            "target_group_ids": [group_index[group] for group in intervention.target_groups],
            "target_channel_ids": [channel_index[channel] for channel in intervention.target_channels],
            "narrative_push": [
                intervention.narrative_push.get(token, 0.0)
                for token in scenario.simulation.narrative_tokens
            ],
            "trust_delta": intervention.trust_delta,
            "stance_delta": intervention.stance_delta,
            "salience_delta": intervention.salience_delta,
        }
        for intervention in scenario.simulation.interventions
    ]

    return {
        "rounds": scenario.simulation.rounds,
        "random_seed": scenario.simulation.random_seed,
        "narrative_count": len(scenario.simulation.narrative_tokens),
        "max_posts_per_round": scenario.simulation.max_posts_per_round,
        "channels": channels,
        "interventions": interventions,
    }
