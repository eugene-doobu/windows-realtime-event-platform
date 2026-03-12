"""Build chart-friendly analysis artifacts from interaction outputs."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from simlab.schemas.artifacts import (
    GroupActionSummaryArtifact,
    GroupActionSummaryEntry,
    GroupRoundSummaryArtifact,
    GroupRoundSummaryEntry,
    InteractionSummaryArtifact,
    NarrativeDominanceArtifact,
    NarrativeRoundSummaryEntry,
    ReactionEvent,
    RepresentativeThreadArtifact,
    ThreadArtifact,
    ThreadMessage,
)

_NARRATIVE_POLARITY = {
    "clarification_accepted": 1.0,
    "reform_needed": 0.5,
    "burden_unfair": -1.0,
    "future_distrust": -0.75,
}


@dataclass(frozen=True, slots=True)
class AnalysisArtifacts:
    group_action_summary: GroupActionSummaryArtifact
    group_round_summary: GroupRoundSummaryArtifact
    narrative_dominance: NarrativeDominanceArtifact
    representative_thread: RepresentativeThreadArtifact


def build_interaction_analysis_artifacts(
    *,
    run_id: str,
    scenario_id: str,
    interaction_summary: InteractionSummaryArtifact,
    threads: list[ThreadArtifact],
    messages: list[ThreadMessage],
    reactions: list[ReactionEvent],
) -> AnalysisArtifacts:
    return AnalysisArtifacts(
        group_action_summary=_build_group_action_summary(
            run_id=run_id,
            scenario_id=scenario_id,
            interaction_summary=interaction_summary,
        ),
        group_round_summary=_build_group_round_summary(
            run_id=run_id,
            scenario_id=scenario_id,
            interaction_summary=interaction_summary,
            messages=messages,
            reactions=reactions,
        ),
        narrative_dominance=_build_narrative_dominance(
            run_id=run_id,
            scenario_id=scenario_id,
            messages=messages,
            reactions=reactions,
        ),
        representative_thread=_build_representative_thread(
            run_id=run_id,
            scenario_id=scenario_id,
            threads=threads,
            messages=messages,
            reactions=reactions,
        ),
    )


def _build_group_action_summary(
    *,
    run_id: str,
    scenario_id: str,
    interaction_summary: InteractionSummaryArtifact,
) -> GroupActionSummaryArtifact:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    total_expressive_actions = 0

    for metric in interaction_summary.group_metrics:
        bucket = grouped[metric.group_id]
        bucket["activation"] += metric.activation_count
        bucket["post"] += metric.post_count
        bucket["reply"] += metric.reply_count
        bucket["react"] += metric.reaction_count
        bucket["ignore"] += metric.ignore_count
        total_expressive_actions += metric.post_count + metric.reply_count + metric.reaction_count

    groups: list[GroupActionSummaryEntry] = []
    for group_id, counts in sorted(grouped.items()):
        expressive_action_count = counts["post"] + counts["reply"] + counts["react"]
        dominant_action = max(
            ("post", "reply", "react", "ignore"),
            key=lambda action: (counts[action], action),
        )
        groups.append(
            GroupActionSummaryEntry(
                group_id=group_id,
                activation_count=counts["activation"],
                post_count=counts["post"],
                reply_count=counts["reply"],
                reaction_count=counts["react"],
                ignore_count=counts["ignore"],
                expressive_action_count=expressive_action_count,
                expression_share=(
                    expressive_action_count / total_expressive_actions
                    if total_expressive_actions > 0
                    else 0.0
                ),
                dominant_action=dominant_action,
            )
        )

    return GroupActionSummaryArtifact(
        run_id=run_id,
        scenario_id=scenario_id,
        groups=groups,
    )


def _build_group_round_summary(
    *,
    run_id: str,
    scenario_id: str,
    interaction_summary: InteractionSummaryArtifact,
    messages: list[ThreadMessage],
    reactions: list[ReactionEvent],
) -> GroupRoundSummaryArtifact:
    event_counters: dict[tuple[int, str], Counter[str]] = defaultdict(Counter)
    narrative_scores: dict[tuple[int, str], list[float]] = defaultdict(list)

    for message in messages:
        key = (message.round_index, message.group_id)
        event_counters[key]["message"] += 1
        event_counters[key][message.narrative_token] += 1
        narrative_scores[key].append(_NARRATIVE_POLARITY.get(message.narrative_token, 0.0))

    for reaction in reactions:
        key = (reaction.round_index, reaction.group_id)
        event_counters[key]["reaction"] += 1
        event_counters[key][reaction.narrative_token] += 1
        narrative_scores[key].append(_NARRATIVE_POLARITY.get(reaction.narrative_token, 0.0))

    rounds: list[GroupRoundSummaryEntry] = []
    for metric in interaction_summary.group_metrics:
        key = (metric.round_index, metric.group_id)
        counts = event_counters[key]
        dominant_narrative = _dominant_narrative(counts)
        scores = narrative_scores[key]
        rounds.append(
            GroupRoundSummaryEntry(
                round_index=metric.round_index,
                group_id=metric.group_id,
                activation_count=metric.activation_count,
                expressive_action_count=metric.post_count + metric.reply_count + metric.reaction_count,
                dominant_narrative=dominant_narrative,
                narrative_stance_proxy=(sum(scores) / len(scores) if scores else 0.0),
                post_count=metric.post_count,
                reply_count=metric.reply_count,
                reaction_count=metric.reaction_count,
                ignore_count=metric.ignore_count,
            )
        )

    return GroupRoundSummaryArtifact(
        run_id=run_id,
        scenario_id=scenario_id,
        rounds=rounds,
    )


def _build_narrative_dominance(
    *,
    run_id: str,
    scenario_id: str,
    messages: list[ThreadMessage],
    reactions: list[ReactionEvent],
) -> NarrativeDominanceArtifact:
    counts_by_round: dict[int, Counter[str]] = defaultdict(Counter)

    for message in messages:
        counts_by_round[message.round_index][message.narrative_token] += 1
    for reaction in reactions:
        counts_by_round[reaction.round_index][reaction.narrative_token] += 1

    rounds: list[NarrativeRoundSummaryEntry] = []
    for round_index in sorted(counts_by_round):
        counts = counts_by_round[round_index]
        total_events = sum(counts.values())
        dominant_narrative = _dominant_narrative(counts)
        dominant_share = (
            counts[dominant_narrative] / total_events
            if dominant_narrative is not None and total_events > 0
            else 0.0
        )
        rounds.append(
            NarrativeRoundSummaryEntry(
                round_index=round_index,
                total_events=total_events,
                dominant_narrative=dominant_narrative,
                dominant_share=dominant_share,
                narrative_counts=dict(sorted(counts.items())),
            )
        )

    return NarrativeDominanceArtifact(
        run_id=run_id,
        scenario_id=scenario_id,
        rounds=rounds,
    )


def _build_representative_thread(
    *,
    run_id: str,
    scenario_id: str,
    threads: list[ThreadArtifact],
    messages: list[ThreadMessage],
    reactions: list[ReactionEvent],
) -> RepresentativeThreadArtifact:
    if not threads:
        return RepresentativeThreadArtifact(
            run_id=run_id,
            scenario_id=scenario_id,
            thread_id=None,
            channel_id=None,
            narrative_token=None,
            message_count=0,
            reaction_count=0,
            participant_groups=[],
            message_ids=[],
            reaction_ids=[],
        )

    representative = max(
        threads,
        key=lambda thread: (thread.message_count + thread.reaction_count, thread.created_round, thread.thread_id),
    )
    representative_messages = [
        message.message_id
        for message in messages
        if message.thread_id == representative.thread_id
    ]
    representative_reactions = [
        reaction.reaction_id
        for reaction in reactions
        if reaction.thread_id == representative.thread_id
    ]
    return RepresentativeThreadArtifact(
        run_id=run_id,
        scenario_id=scenario_id,
        thread_id=representative.thread_id,
        channel_id=representative.channel_id,
        narrative_token=representative.narrative_token,
        message_count=representative.message_count,
        reaction_count=representative.reaction_count,
        participant_groups=representative.participant_groups,
        message_ids=representative_messages,
        reaction_ids=representative_reactions,
    )


def _dominant_narrative(counts: Counter[str]) -> str | None:
    candidates = {
        key: value
        for key, value in counts.items()
        if key not in {"message", "reaction"}
    }
    if not candidates:
        return None
    return max(sorted(candidates), key=lambda narrative: (candidates[narrative], narrative))
