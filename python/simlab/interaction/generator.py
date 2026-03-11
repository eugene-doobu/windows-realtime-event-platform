"""Generate deterministic thread, message, and reaction artifacts."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from random import Random

from simlab.runner.execution import RunMode
from simlab.schemas.artifacts import (
    AgentAction,
    InteractionGroupMetric,
    InteractionSummaryArtifact,
    ReactionEvent,
    RoundActionMetric,
    ThreadArtifact,
    ThreadMessage,
)
from simlab.schemas.scenario import Scenario

_RUMOR_NARRATIVES = {"burden_unfair", "future_distrust"}
_CORRECTION_NARRATIVES = {"clarification_accepted"}


@dataclass(frozen=True, slots=True)
class InteractionArtifacts:
    actions: list[AgentAction]
    threads: list[ThreadArtifact]
    messages: list[ThreadMessage]
    reactions: list[ReactionEvent]
    summary: InteractionSummaryArtifact


def generate_interactions(
    *,
    run_id: str,
    scenario: Scenario,
    run_mode: RunMode,
    final_state: dict[str, list[float] | list[int]],
    round_metrics: list[dict[str, float | int]],
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
    group_labels: dict[int, str],
) -> InteractionArtifacts:
    rng = Random(scenario.simulation.random_seed + 1_001)
    threads: list[ThreadArtifact] = []
    messages: list[ThreadMessage] = []
    reactions: list[ReactionEvent] = []
    actions: list[AgentAction] = []
    group_metric_counters: dict[tuple[int, str], Counter[str]] = {}
    round_metric_counters: dict[int, Counter[str]] = {}
    action_counts = Counter[str]()
    per_round_active_agents: list[int] = []
    latest_message_by_thread: dict[str, str] = {}
    thread_message_counts: Counter[str] = Counter()
    thread_reaction_counts: Counter[str] = Counter()
    thread_groups: dict[str, set[str]] = {}
    message_lookup: dict[str, ThreadMessage] = {}
    archetype_by_group = {
        archetype.id: archetype for archetype in scenario.population.archetypes
    }
    interventions_by_round = _index_interventions_by_round(scenario)
    channel_by_id = {channel.id: channel for channel in scenario.simulation.channels}

    for round_metric in round_metrics:
        round_index = int(round_metric["round_index"])
        active_agents = _select_active_agents(
            final_state=final_state,
            persona=persona,
            round_index=round_index,
            run_mode=run_mode,
            rng=rng,
        )
        per_round_active_agents.append(len(active_agents))

        for ordinal, agent_id in enumerate(active_agents):
            group_id = group_labels[int(final_state["group_id"][agent_id])]
            channel_id = _select_channel_for_agent(
                media_diet=dict(persona["media_diet"][agent_id]),
                scenario=scenario,
                rng=rng,
            )
            relevant_interventions = _relevant_interventions(
                interventions_by_round=interventions_by_round,
                round_index=round_index,
                group_id=group_id,
                channel_id=channel_id,
            )
            narrative_token = _select_narrative_for_agent(
                scenario=scenario,
                agent_id=agent_id,
                group_id=group_id,
                stance=float(final_state["stance"][agent_id]),
                trust=float(final_state["trust"][agent_id]),
                final_state=final_state,
                persona=persona,
                archetype_by_group=archetype_by_group,
                relevant_interventions=relevant_interventions,
                channel=channel_by_id[channel_id],
                rng=rng,
            )
            decision = _choose_action_type(
                agent_id=agent_id,
                persona=persona,
                final_state=final_state,
                has_existing_threads=bool(threads),
                relevant_interventions=relevant_interventions,
                channel=channel_by_id[channel_id],
                rng=rng,
            )
            counter = group_metric_counters.setdefault((round_index, group_id), Counter())
            round_counter = round_metric_counters.setdefault(round_index, Counter())
            counter["activation"] += 1
            round_counter["activation"] += 1

            if decision == "ignore":
                actions.append(
                    AgentAction(
                        round_index=round_index,
                        agent_id=agent_id,
                        group_id=group_id,
                        action_type="ignore",
                        narrative_token=narrative_token,
                        channel_id=channel_id,
                    )
                )
                counter["ignore"] += 1
                round_counter["ignore"] += 1
                action_counts["ignore"] += 1
                continue

            if decision == "post" or not threads:
                thread_id = f"thread-r{round_index:02d}-{len(threads):04d}"
                message_id = f"msg-r{round_index:02d}-{len(messages):05d}"
                message = ThreadMessage(
                    message_id=message_id,
                    thread_id=thread_id,
                    round_index=round_index,
                    agent_id=agent_id,
                    group_id=group_id,
                    action_type="post",
                    narrative_token=narrative_token,
                    channel_id=channel_id,
                    tone_style=str(persona["tone_style"][agent_id]),
                    argument_style=str(persona["argument_style"][agent_id]),
                )
                thread = ThreadArtifact(
                    thread_id=thread_id,
                    channel_id=channel_id,
                    narrative_token=narrative_token,
                    created_round=round_index,
                    root_message_id=message_id,
                    message_count=1,
                    reaction_count=0,
                    participant_groups=[group_id],
                )
                actions.append(
                    AgentAction(
                        round_index=round_index,
                        agent_id=agent_id,
                        group_id=group_id,
                        action_type="post",
                        target_thread_id=thread_id,
                        narrative_token=narrative_token,
                        channel_id=channel_id,
                    )
                )
                threads.append(thread)
                messages.append(message)
                message_lookup[message_id] = message
                latest_message_by_thread[thread_id] = message_id
                thread_message_counts[thread_id] += 1
                thread_groups[thread_id] = {group_id}
                counter["post"] += 1
                round_counter["post"] += 1
                action_counts["post"] += 1
                continue

            target_thread = _select_target_thread(
                threads=threads,
                thread_groups=thread_groups,
                group_id=group_id,
                rng=rng,
            )
            target_message_id = latest_message_by_thread[target_thread.thread_id]
            interaction_channel_id = target_thread.channel_id
            reaction_interventions = _relevant_interventions(
                interventions_by_round=interventions_by_round,
                round_index=round_index,
                group_id=group_id,
                channel_id=interaction_channel_id,
            )
            target_message = message_lookup[target_message_id]
            if decision == "reply":
                message_id = f"msg-r{round_index:02d}-{len(messages):05d}"
                message = ThreadMessage(
                    message_id=message_id,
                    thread_id=target_thread.thread_id,
                    round_index=round_index,
                    agent_id=agent_id,
                    group_id=group_id,
                    action_type="reply",
                    narrative_token=narrative_token,
                    channel_id=interaction_channel_id,
                    tone_style=str(persona["tone_style"][agent_id]),
                    argument_style=str(persona["argument_style"][agent_id]),
                    parent_message_id=target_message_id,
                )
                actions.append(
                    AgentAction(
                        round_index=round_index,
                        agent_id=agent_id,
                        group_id=group_id,
                        action_type="reply",
                        target_message_id=target_message_id,
                        target_thread_id=target_thread.thread_id,
                        narrative_token=narrative_token,
                        channel_id=interaction_channel_id,
                    )
                )
                messages.append(message)
                message_lookup[message_id] = message
                latest_message_by_thread[target_thread.thread_id] = message_id
                thread_message_counts[target_thread.thread_id] += 1
                thread_groups[target_thread.thread_id].add(group_id)
                counter["reply"] += 1
                round_counter["reply"] += 1
                action_counts["reply"] += 1
            else:
                reaction_kind = _select_reaction_kind(
                    agent_id=agent_id,
                    final_state=final_state,
                    persona=persona,
                    target_narrative=target_message.narrative_token,
                    relevant_interventions=reaction_interventions,
                    channel=channel_by_id[interaction_channel_id],
                    rng=rng,
                )
                reaction_id = f"react-r{round_index:02d}-{len(reactions):05d}"
                reaction = ReactionEvent(
                    reaction_id=reaction_id,
                    thread_id=target_thread.thread_id,
                    round_index=round_index,
                    agent_id=agent_id,
                    group_id=group_id,
                    target_message_id=target_message_id,
                    reaction_kind=reaction_kind,
                    narrative_token=target_message.narrative_token,
                    channel_id=interaction_channel_id,
                )
                actions.append(
                    AgentAction(
                        round_index=round_index,
                        agent_id=agent_id,
                        group_id=group_id,
                        action_type="react",
                        target_message_id=target_message_id,
                        target_thread_id=target_thread.thread_id,
                        narrative_token=target_message.narrative_token,
                        channel_id=interaction_channel_id,
                    )
                )
                reactions.append(reaction)
                thread_reaction_counts[target_thread.thread_id] += 1
                thread_groups[target_thread.thread_id].add(group_id)
                counter["react"] += 1
                round_counter["react"] += 1
                action_counts["react"] += 1

    finalized_threads = [
        thread.model_copy(
            update={
                "message_count": thread_message_counts[thread.thread_id],
                "reaction_count": thread_reaction_counts[thread.thread_id],
                "participant_groups": sorted(thread_groups[thread.thread_id]),
            }
        )
        for thread in threads
    ]

    group_metrics: list[InteractionGroupMetric] = []
    for (round_index, group_id), counts in sorted(group_metric_counters.items()):
        group_metrics.append(
            InteractionGroupMetric(
                round_index=round_index,
                group_id=group_id,
                activation_count=counts["activation"],
                post_count=counts["post"],
                reply_count=counts["reply"],
                reaction_count=counts["react"],
                ignore_count=counts["ignore"],
            )
        )

    round_action_metrics = [
        RoundActionMetric(
            round_index=round_index,
            activation_count=counts["activation"],
            post_count=counts["post"],
            reply_count=counts["reply"],
            reaction_count=counts["react"],
            ignore_count=counts["ignore"],
        )
        for round_index, counts in sorted(round_metric_counters.items())
    ]

    summary = InteractionSummaryArtifact(
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        total_rounds=len(round_metrics),
        thread_count=len(finalized_threads),
        message_count=len(messages),
        reaction_count=len(reactions),
        action_counts=dict(action_counts),
        per_round_active_agents=per_round_active_agents,
        round_metrics=round_action_metrics,
        group_metrics=group_metrics,
    )
    return InteractionArtifacts(
        actions=actions,
        threads=finalized_threads,
        messages=messages,
        reactions=reactions,
        summary=summary,
    )


def _select_active_agents(
    *,
    final_state: dict[str, list[float] | list[int]],
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
    round_index: int,
    run_mode: RunMode,
    rng: Random,
) -> list[int]:
    population_size = len(final_state["group_id"])
    if run_mode is RunMode.SMOKE:
        active_count = min(population_size, max(6, population_size // 12))
    elif run_mode is RunMode.STANDARD:
        active_count = min(population_size, max(12, population_size // 10))
    else:
        active_count = min(population_size, max(20, population_size // 8))

    scored: list[tuple[float, int, int]] = []
    group_members: dict[int, list[tuple[float, int]]] = {}
    for agent_id in range(population_size):
        base_score = (
            (float(final_state["activity"][agent_id]) * 0.4)
            + (float(final_state["salience"][agent_id]) * 0.4)
            + (float(final_state["influence"][agent_id]) * 0.2)
        )
        persona_bonus = (
            (float(persona["post_tendency"][agent_id]) * 0.15)
            + (float(persona["reply_tendency"][agent_id]) * 0.1)
            + (float(persona["reaction_tendency"][agent_id]) * 0.05)
        )
        round_bonus = (round_index + 1) * 0.01
        noise = rng.random() * 0.05
        score = base_score + persona_bonus + round_bonus + noise
        current_group_id = int(final_state["group_id"][agent_id])
        scored.append((score, agent_id, current_group_id))
        group_members.setdefault(current_group_id, []).append((score, agent_id))

    selected: list[int] = []
    for current_group_id, members in sorted(group_members.items()):
        members.sort(key=lambda item: (-item[0], item[1]))
        quota = max(1, round((len(members) / population_size) * active_count))
        selected.extend(agent_id for _, agent_id in members[:quota])

    if len(selected) < active_count:
        ranked = sorted(scored, key=lambda item: (-item[0], item[1]))
        selected_set = set(selected)
        for _, agent_id, _ in ranked:
            if agent_id in selected_set:
                continue
            selected.append(agent_id)
            selected_set.add(agent_id)
            if len(selected) >= active_count:
                break

    if len(selected) > active_count:
        selected = selected[:active_count]
    return selected


def _choose_action_type(
    *,
    agent_id: int,
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
    final_state: dict[str, list[float] | list[int]],
    has_existing_threads: bool,
    relevant_interventions,
    channel,
    rng: Random,
) -> str:
    stance = abs(float(final_state["stance"][agent_id]))
    salience = float(final_state["salience"][agent_id])
    clarification_score = _clarification_uptake_score(
        agent_id=agent_id,
        final_state=final_state,
        persona=persona,
        relevant_interventions=relevant_interventions,
    )
    rumor_score = _rumor_spread_score(
        agent_id=agent_id,
        final_state=final_state,
        persona=persona,
        relevant_interventions=relevant_interventions,
        channel=channel,
    )
    post_score = float(persona["post_tendency"][agent_id]) + (salience * 0.3) + (stance * 0.1)
    reply_score = (
        float(persona["reply_tendency"][agent_id])
        + (float(persona["conflict_tolerance"][agent_id]) * 0.2)
        + ((1.0 - float(persona["conformity"][agent_id])) * 0.1)
        + (0.15 if has_existing_threads else 0.0)
    )
    react_score = (
        float(persona["reaction_tendency"][agent_id])
        + (float(persona["conformity"][agent_id]) * 0.15)
        + (float(persona["risk_aversion"][agent_id]) * 0.05)
    )
    post_score += (rumor_score * 0.2) + (clarification_score * 0.1)
    reply_score += (rumor_score * 0.1) + (clarification_score * 0.15)
    react_score += (clarification_score * 0.1) + (rumor_score * 0.05)
    ignore_threshold = 0.42 + (rng.random() * 0.05) - (clarification_score * 0.05) - (rumor_score * 0.05)
    if max(post_score, reply_score, react_score) < ignore_threshold:
        return "ignore"
    if has_existing_threads and react_score >= post_score and (react_score + 0.05) >= reply_score:
        return "react"
    if reply_score >= post_score and reply_score >= react_score and has_existing_threads:
        return "reply"
    if post_score >= react_score:
        return "post"
    return "react"


def _select_target_thread(
    *,
    threads: list[ThreadArtifact],
    thread_groups: dict[str, set[str]],
    group_id: str,
    rng: Random,
) -> ThreadArtifact:
    cross_group_threads = [thread for thread in threads if group_id not in thread_groups[thread.thread_id]]
    if cross_group_threads:
        return cross_group_threads[(len(cross_group_threads) + int(rng.random() * 10)) % len(cross_group_threads)]
    return threads[(len(threads) + int(rng.random() * 10)) % len(threads)]


def _select_channel_for_agent(
    *,
    media_diet: dict[str, float],
    scenario: Scenario,
    rng: Random,
) -> str:
    if not media_diet:
        return scenario.simulation.channels[0].id
    preferred_kind = max(
        sorted(media_diet.items()),
        key=lambda item: (item[1], item[0]),
    )[0]
    candidates = [channel.id for channel in scenario.simulation.channels if channel.kind.value == preferred_kind]
    if candidates:
        return candidates[int(rng.random() * len(candidates)) % len(candidates)]
    return scenario.simulation.channels[0].id


def _select_narrative_for_agent(
    *,
    scenario: Scenario,
    agent_id: int,
    group_id: str,
    stance: float,
    trust: float,
    final_state: dict[str, list[float] | list[int]],
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
    archetype_by_group,
    relevant_interventions,
    channel,
    rng: Random,
) -> str:
    affinities = archetype_by_group[group_id].narrative_affinity
    clarification_score = _clarification_uptake_score(
        agent_id=agent_id,
        final_state=final_state,
        persona=persona,
        relevant_interventions=relevant_interventions,
    )
    rumor_score = _rumor_spread_score(
        agent_id=agent_id,
        final_state=final_state,
        persona=persona,
        relevant_interventions=relevant_interventions,
        channel=channel,
    )
    if clarification_score >= max(0.6, rumor_score + 0.05) and "clarification_accepted" in scenario.simulation.narrative_tokens:
        return "clarification_accepted"
    if rumor_score >= 0.65 and "future_distrust" in scenario.simulation.narrative_tokens:
        return "future_distrust"
    if (stance < -0.2 or rumor_score >= 0.55) and "burden_unfair" in scenario.simulation.narrative_tokens:
        return "burden_unfair"
    if not affinities:
        return scenario.simulation.narrative_tokens[int(rng.random() * len(scenario.simulation.narrative_tokens))]
    if trust < 0.45 and "future_distrust" in scenario.simulation.narrative_tokens:
        return "future_distrust"
    return max(
        sorted(affinities.items()),
        key=lambda item: (item[1], item[0]),
    )[0]


def _select_reaction_kind(
    *,
    agent_id: int,
    final_state: dict[str, list[float] | list[int]],
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
    target_narrative: str,
    relevant_interventions,
    channel,
    rng: Random,
) -> str:
    clarification_score = _clarification_uptake_score(
        agent_id=agent_id,
        final_state=final_state,
        persona=persona,
        relevant_interventions=relevant_interventions,
    )
    rumor_score = _rumor_spread_score(
        agent_id=agent_id,
        final_state=final_state,
        persona=persona,
        relevant_interventions=relevant_interventions,
        channel=channel,
    )
    if target_narrative in _CORRECTION_NARRATIVES:
        if clarification_score >= max(0.55, rumor_score + 0.05):
            return "endorse"
        if clarification_score < 0.45:
            return "question"
    if target_narrative in _RUMOR_NARRATIVES:
        if rumor_score >= max(0.55, clarification_score + 0.05):
            return "amplify"
        return "question"
    if float(final_state["trust"][agent_id]) < 0.4 and float(persona["conflict_tolerance"][agent_id]) > 0.6:
        return "question"
    if float(persona["conformity"][agent_id]) > 0.6:
        return "amplify"
    return "endorse" if rng.random() < 0.6 else "question"


def _index_interventions_by_round(scenario: Scenario) -> dict[int, list]:
    indexed: dict[int, list] = {}
    for intervention in scenario.simulation.interventions:
        indexed.setdefault(intervention.round_index, []).append(intervention)
    return indexed


def _relevant_interventions(
    *,
    interventions_by_round: dict[int, list],
    round_index: int,
    group_id: str,
    channel_id: str,
) -> list:
    relevant = []
    for intervention in interventions_by_round.get(round_index, []):
        group_match = not intervention.target_groups or group_id in intervention.target_groups
        channel_match = not intervention.target_channels or channel_id in intervention.target_channels
        if group_match and channel_match:
            relevant.append(intervention)
    return relevant


def _clarification_uptake_score(
    *,
    agent_id: int,
    final_state: dict[str, list[float] | list[int]],
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
    relevant_interventions,
) -> float:
    intervention_bonus = 0.0
    clarification_bonus = 0.0
    fact_check_bonus = 0.0
    for intervention in relevant_interventions:
        if intervention.kind.value == "clarification":
            narrative_bonus = intervention.narrative_push.get("clarification_accepted", 0.0)
            clarification_bonus += max(0.0, intervention.trust_delta) + max(0.0, intervention.stance_delta) + narrative_bonus
        elif intervention.kind.value == "fact_check":
            narrative_bonus = intervention.narrative_push.get("clarification_accepted", 0.0)
            fact_check_bonus += max(0.0, intervention.trust_delta) + narrative_bonus
    intervention_bonus = min(1.0, clarification_bonus + fact_check_bonus)
    has_fact_check = fact_check_bonus > 0.0
    trust_weight = 0.22 if has_fact_check else 0.3
    baseline_weight = 0.22 if has_fact_check else 0.35
    correction_weight = 0.46 if has_fact_check else 0.25
    raw_score = (
        (float(final_state["trust"][agent_id]) * trust_weight)
        + (float(persona["trust_in_officials_baseline"][agent_id]) * baseline_weight)
        + (float(persona["correction_acceptance"][agent_id]) * correction_weight)
        + (intervention_bonus * 0.1)
    )
    return max(0.0, min(1.0, raw_score))


def _rumor_spread_score(
    *,
    agent_id: int,
    final_state: dict[str, list[float] | list[int]],
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
    relevant_interventions,
    channel,
) -> float:
    rumor_intervention_bonus = 0.0
    clarification_drag = 0.0
    for intervention in relevant_interventions:
        if intervention.kind.value == "rumor":
            rumor_intervention_bonus += 0.25 + max(intervention.narrative_push.values(), default=0.0)
        if intervention.kind.value in {"clarification", "fact_check"}:
            clarification_drag += 0.15 + max(intervention.narrative_push.get("clarification_accepted", 0.0), 0.0)
    negativity = max(0.0, -float(final_state["stance"][agent_id]))
    channel_factor = _channel_rumor_factor(channel)
    raw_score = (
        (float(persona["rumor_susceptibility"][agent_id]) * 0.35)
        + (float(final_state["salience"][agent_id]) * 0.2)
        + (negativity * 0.2)
        + (channel_factor * 0.2)
        + (min(1.0, rumor_intervention_bonus) * 0.15)
        - (min(1.0, clarification_drag) * 0.15)
        - (float(persona["correction_acceptance"][agent_id]) * 0.1)
    )
    return max(0.0, min(1.0, raw_score))


def _channel_rumor_factor(channel) -> float:
    raw_factor = (
        (channel.repost_factor * 0.4)
        + ((1.0 - channel.rumor_decay) * 0.35)
        + (channel.trust_penalty * 0.25)
    )
    return max(0.0, min(1.0, raw_factor))
