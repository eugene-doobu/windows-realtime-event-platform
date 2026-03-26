"""Validation checks for deterministic interaction artifacts."""

from __future__ import annotations

from collections import Counter

from gan_simlab.schemas.artifacts import (
    ConversationEntry,
    InteractionSummaryArtifact,
    InteractionValidationArtifact,
    InteractionValidationCheck,
    PersonaSnapshotArtifact,
    ReactionEvent,
    ThreadMessage,
)
from gan_simlab.schemas.scenario import Scenario


def build_interaction_validation(
    *,
    run_id: str,
    scenario: Scenario,
    interaction_summary: InteractionSummaryArtifact,
    persona_snapshot: PersonaSnapshotArtifact,
    messages: list[ThreadMessage],
    reactions: list[ReactionEvent],
    conversation: list[ConversationEntry],
) -> InteractionValidationArtifact:
    checks: list[InteractionValidationCheck] = []
    warnings: list[str] = []
    group_summaries = {
        summary.group_id: summary
        for summary in persona_snapshot.group_summaries
    }
    activation_by_group = Counter()
    reply_by_group = Counter()
    for metric in interaction_summary.group_metrics:
        activation_by_group[metric.group_id] += metric.activation_count
        reply_by_group[metric.group_id] += metric.reply_count

    checks.append(_check_round_volume_bounded(interaction_summary))

    reply_check = _check_reply_tendency_alignment(
        group_summaries=group_summaries,
        activation_by_group=activation_by_group,
        reply_by_group=reply_by_group,
    )
    if reply_check is not None:
        checks.append(reply_check)
    else:
        warnings.append("reply tendency alignment could not be evaluated")

    if _scenario_has_correction_signal(scenario):
        clarification_check = _check_clarification_alignment(
            group_summaries=group_summaries,
            activation_by_group=activation_by_group,
            messages=messages,
            reactions=reactions,
        )
        if clarification_check is not None:
            checks.append(clarification_check)
        else:
            warnings.append("clarification alignment could not be evaluated")

    if _scenario_has_rumor_signal(scenario):
        rumor_check = _check_rumor_alignment(
            group_summaries=group_summaries,
            activation_by_group=activation_by_group,
            reactions=reactions,
        )
        if rumor_check is not None:
            checks.append(rumor_check)
        else:
            warnings.append("rumor amplification alignment could not be evaluated")

    verbosity_check = _check_verbosity_alignment(
        group_summaries=group_summaries,
        conversation=conversation,
    )
    if verbosity_check is not None:
        checks.append(verbosity_check)
    else:
        warnings.append("verbosity alignment could not be evaluated")

    passed = all(check.passed for check in checks)
    return InteractionValidationArtifact(
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        passed=passed,
        checks=checks,
        warnings=warnings,
    )


def _check_round_volume_bounded(interaction_summary: InteractionSummaryArtifact) -> InteractionValidationCheck:
    bounded = all(
        (metric.post_count + metric.reply_count + metric.reaction_count + metric.ignore_count) == metric.activation_count
        and (metric.post_count + metric.reply_count + metric.reaction_count) <= metric.activation_count
        for metric in interaction_summary.round_metrics
    )
    return InteractionValidationCheck(
        check_id="round_volume_bounded",
        passed=bounded,
        actual=str(bounded).lower(),
        expected="true",
        message="round-level interaction volume stays within activation bounds",
    )


def _check_reply_tendency_alignment(
    *,
    group_summaries,
    activation_by_group: Counter,
    reply_by_group: Counter,
) -> InteractionValidationCheck | None:
    if len(group_summaries) < 2:
        return None
    high_group = max(group_summaries.values(), key=lambda summary: summary.mean_reply_tendency)
    low_group = min(group_summaries.values(), key=lambda summary: summary.mean_reply_tendency)
    if activation_by_group[high_group.group_id] == 0 or activation_by_group[low_group.group_id] == 0:
        return None
    high_rate = reply_by_group[high_group.group_id] / activation_by_group[high_group.group_id]
    low_rate = reply_by_group[low_group.group_id] / activation_by_group[low_group.group_id]
    return InteractionValidationCheck(
        check_id="reply_tendency_alignment",
        passed=high_rate >= low_rate,
        actual=round(high_rate - low_rate, 4),
        expected=">= 0.0",
        message="groups with higher reply tendency should reply at least as often",
    )


def _check_clarification_alignment(
    *,
    group_summaries,
    activation_by_group: Counter,
    messages: list[ThreadMessage],
    reactions: list[ReactionEvent],
) -> InteractionValidationCheck | None:
    if len(group_summaries) < 2:
        return None
    clarification_counts = Counter()
    for message in messages:
        if message.narrative_token == "clarification_accepted":
            clarification_counts[message.group_id] += 1
    for reaction in reactions:
        if reaction.narrative_token == "clarification_accepted":
            clarification_counts[reaction.group_id] += 1
    if not clarification_counts:
        return None

    high_group = max(group_summaries.values(), key=lambda summary: summary.mean_trust_in_officials_baseline)
    low_group = min(group_summaries.values(), key=lambda summary: summary.mean_trust_in_officials_baseline)
    if activation_by_group[high_group.group_id] == 0 or activation_by_group[low_group.group_id] == 0:
        return None
    high_rate = clarification_counts[high_group.group_id] / activation_by_group[high_group.group_id]
    low_rate = clarification_counts[low_group.group_id] / activation_by_group[low_group.group_id]
    return InteractionValidationCheck(
        check_id="clarification_alignment",
        passed=high_rate >= low_rate,
        actual=round(high_rate - low_rate, 4),
        expected=">= 0.0",
        message="groups with higher trust baselines should accept clarification at least as often",
    )


def _check_verbosity_alignment(
    *,
    group_summaries,
    conversation: list[ConversationEntry],
) -> InteractionValidationCheck | None:
    message_entries = [entry for entry in conversation if entry.action_type in {"post", "reply"}]
    if len(group_summaries) < 2 or not message_entries:
        return None

    lengths_by_group = Counter()
    counts_by_group = Counter()
    for entry in message_entries:
        lengths_by_group[entry.group_id] += len(entry.rendered_text)
        counts_by_group[entry.group_id] += 1

    if len(counts_by_group) < 2:
        return None

    high_group = max(group_summaries.values(), key=lambda summary: summary.mean_verbosity)
    low_group = min(group_summaries.values(), key=lambda summary: summary.mean_verbosity)
    if counts_by_group[high_group.group_id] == 0 or counts_by_group[low_group.group_id] == 0:
        return None
    high_avg = lengths_by_group[high_group.group_id] / counts_by_group[high_group.group_id]
    low_avg = lengths_by_group[low_group.group_id] / counts_by_group[low_group.group_id]
    return InteractionValidationCheck(
        check_id="verbosity_alignment",
        passed=high_avg >= low_avg,
        actual=round(high_avg - low_avg, 2),
        expected=">= 0.0",
        message="groups with higher verbosity should emit at least as much text",
    )


def _check_rumor_alignment(
    *,
    group_summaries,
    activation_by_group: Counter,
    reactions: list[ReactionEvent],
) -> InteractionValidationCheck | None:
    rumor_amplification = Counter()
    for reaction in reactions:
        if reaction.reaction_kind == "amplify" and reaction.narrative_token in {"burden_unfair", "future_distrust"}:
            rumor_amplification[reaction.group_id] += 1
    if not rumor_amplification or len(group_summaries) < 2:
        return None

    high_group = max(group_summaries.values(), key=lambda summary: summary.mean_rumor_susceptibility)
    low_group = min(group_summaries.values(), key=lambda summary: summary.mean_rumor_susceptibility)
    if activation_by_group[high_group.group_id] == 0 or activation_by_group[low_group.group_id] == 0:
        return None
    high_rate = rumor_amplification[high_group.group_id] / activation_by_group[high_group.group_id]
    low_rate = rumor_amplification[low_group.group_id] / activation_by_group[low_group.group_id]
    return InteractionValidationCheck(
        check_id="rumor_amplification_alignment",
        passed=high_rate >= low_rate,
        actual=round(high_rate - low_rate, 4),
        expected=">= 0.0",
        message="groups with higher rumor susceptibility should amplify rumor at least as often",
    )


def _scenario_has_correction_signal(scenario: Scenario) -> bool:
    return any(
        intervention.kind.value in {"clarification", "fact_check"}
        for intervention in scenario.simulation.interventions
    )


def _scenario_has_rumor_signal(scenario: Scenario) -> bool:
    return any(
        intervention.kind.value == "rumor"
        for intervention in scenario.simulation.interventions
    )
