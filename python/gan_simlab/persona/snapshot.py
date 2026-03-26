"""Persona snapshot artifact generation."""

from __future__ import annotations

from collections import Counter

from gan_simlab.schemas.artifacts import PersonaGroupSummary, PersonaSample, PersonaSnapshotArtifact


def build_persona_snapshot(
    *,
    run_id: str,
    scenario_id: str,
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
    group_labels: dict[int, str],
    samples_per_group: int = 3,
) -> PersonaSnapshotArtifact:
    group_indices: dict[int, list[int]] = {}
    for agent_id, raw_group_id in enumerate(persona["group_id"]):
        group_indices.setdefault(int(raw_group_id), []).append(agent_id)

    sample_agents: list[PersonaSample] = []
    for current_group_id in sorted(group_indices):
        for agent_id in group_indices[current_group_id][:samples_per_group]:
            sample_agents.append(_build_persona_sample(agent_id=agent_id, persona=persona, group_labels=group_labels))

    group_summaries = [
        _build_group_summary(
            group_id=current_group_id,
            agent_ids=group_indices[current_group_id],
            persona=persona,
            group_labels=group_labels,
        )
        for current_group_id in sorted(group_indices)
    ]

    return PersonaSnapshotArtifact(
        run_id=run_id,
        scenario_id=scenario_id,
        population_size=len(persona["group_id"]),
        sample_agents=sample_agents,
        group_summaries=group_summaries,
    )


def _build_persona_sample(
    *,
    agent_id: int,
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
    group_labels: dict[int, str],
) -> PersonaSample:
    group_id = int(persona["group_id"][agent_id])
    return PersonaSample(
        agent_id=agent_id,
        group_id=group_labels[group_id],
        age_band=str(persona["age_band"][agent_id]),
        job_type=str(persona["job_type"][agent_id]),
        household_stage=str(persona["household_stage"][agent_id]),
        education_level=str(persona["education_level"][agent_id]),
        region_type=str(persona["region_type"][agent_id]),
        income_pressure=float(persona["income_pressure"][agent_id]),
        media_diet=dict(persona["media_diet"][agent_id]),
        conflict_tolerance=float(persona["conflict_tolerance"][agent_id]),
        conformity=float(persona["conformity"][agent_id]),
        risk_aversion=float(persona["risk_aversion"][agent_id]),
        trust_in_officials_baseline=float(persona["trust_in_officials_baseline"][agent_id]),
        rumor_susceptibility=float(persona["rumor_susceptibility"][agent_id]),
        correction_acceptance=float(persona["correction_acceptance"][agent_id]),
        reply_tendency=float(persona["reply_tendency"][agent_id]),
        post_tendency=float(persona["post_tendency"][agent_id]),
        reaction_tendency=float(persona["reaction_tendency"][agent_id]),
        verbosity=float(persona["verbosity"][agent_id]),
        tone_style=str(persona["tone_style"][agent_id]),
        argument_style=str(persona["argument_style"][agent_id]),
    )


def _build_group_summary(
    *,
    group_id: int,
    agent_ids: list[int],
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
    group_labels: dict[int, str],
) -> PersonaGroupSummary:
    tone_counter = Counter(str(persona["tone_style"][agent_id]) for agent_id in agent_ids)
    argument_counter = Counter(str(persona["argument_style"][agent_id]) for agent_id in agent_ids)
    return PersonaGroupSummary(
        group_id=group_labels[group_id],
        population=len(agent_ids),
        mean_income_pressure=_mean(float(persona["income_pressure"][agent_id]) for agent_id in agent_ids),
        mean_conflict_tolerance=_mean(float(persona["conflict_tolerance"][agent_id]) for agent_id in agent_ids),
        mean_trust_in_officials_baseline=_mean(
            float(persona["trust_in_officials_baseline"][agent_id])
            for agent_id in agent_ids
        ),
        mean_rumor_susceptibility=_mean(
            float(persona["rumor_susceptibility"][agent_id])
            for agent_id in agent_ids
        ),
        mean_correction_acceptance=_mean(
            float(persona["correction_acceptance"][agent_id])
            for agent_id in agent_ids
        ),
        mean_reply_tendency=_mean(float(persona["reply_tendency"][agent_id]) for agent_id in agent_ids),
        mean_verbosity=_mean(float(persona["verbosity"][agent_id]) for agent_id in agent_ids),
        dominant_tone_style=tone_counter.most_common(1)[0][0],
        dominant_argument_style=argument_counter.most_common(1)[0][0],
    )


def _mean(values) -> float:
    materialized = list(values)
    return sum(materialized) / len(materialized) if materialized else 0.0
